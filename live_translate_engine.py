import base64
import json
import os
import queue
import re
import threading
import time

import numpy as np


SENTENCE_END_RE = re.compile(r"[。！？!?]+|(?<=[A-Za-z0-9])\.(?=\s|$)")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_LETTER_RE = re.compile(r"[A-Za-z]")
ASCII_WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def count_sentences(text):
    text = normalize_text(text)
    if not text:
        return 0
    return len(SENTENCE_END_RE.findall(text))


def has_cjk(text):
    return bool(CJK_RE.search(text or ""))


def normalize_language(language):
    language = (language or "").lower()
    if language in {"zh", "zh-cn", "cmn", "yue", "chinese", "中文"}:
        return "zh"
    if language.startswith("zh"):
        return "zh"
    if language in {"en", "eng", "english", "英语"}:
        return "en"
    if language.startswith("en"):
        return "en"
    return language


def language_stats(text):
    text = text or ""
    return (
        len(CJK_RE.findall(text)),
        len(LATIN_LETTER_RE.findall(text)),
        len(ASCII_WORD_RE.findall(text)),
    )


def language_from_text(text):
    cjk_chars, latin_letters, english_words = language_stats(text)
    if not cjk_chars and not latin_letters:
        return ""
    if cjk_chars >= 2 and cjk_chars >= max(latin_letters * 0.35, 2):
        return "zh"
    if english_words >= 2 and latin_letters >= max(cjk_chars * 2.5, 4):
        return "en"
    if cjk_chars and cjk_chars >= latin_letters:
        return "zh"
    if latin_letters:
        return "en"
    return "zh" if cjk_chars else ""


def text_matches_language(text, expected_language):
    expected_language = normalize_language(expected_language)
    cjk_chars, latin_letters, english_words = language_stats(text)
    if not cjk_chars and not latin_letters:
        return True
    if expected_language == "zh":
        if not cjk_chars:
            return False
        return cjk_chars >= 2 and cjk_chars >= max(latin_letters * 0.25, 2)
    if expected_language == "en":
        if not latin_letters or not english_words:
            return False
        if cjk_chars >= 2 and cjk_chars > latin_letters * 0.45:
            return False
        return latin_letters >= 2
    return True


def normalize_language_mode(mode):
    mode = normalize_text(mode).lower()
    if mode in {"zh", "chinese", "zh_cn", "zh-cn", "中文", "中文为主", "zh_to_en"}:
        return "zh"
    if mode in {"en", "english", "英语", "英文", "英文为主", "en_to_zh"}:
        return "en"
    return "auto"


def language_mode_label(mode):
    mode = normalize_language_mode(mode)
    return {"auto": "智能中英互译", "zh": "中文发言为主", "en": "英文发言为主"}[mode]


def reverse_hot_words(hot_words):
    reversed_words = {}
    for source, target in (hot_words or {}).items():
        source = normalize_text(source)
        target = normalize_text(target)
        if source and target:
            reversed_words[target] = source
    return reversed_words


class LiveTranslateEngine:
    """One qwen3.5-livetranslate realtime session direction."""

    def __init__(
        self,
        api_key=None,
        source_language="zh",
        target_language="en",
        hot_words=None,
        sample_rate=16000,
        result_queue=None,
        model="qwen3.5-livetranslate-flash-realtime",
        segment_sentences=3,
        max_segment_seconds=20.0,
        min_segment_seconds=3.0,
        silence_timeout=1.2,
        voice_threshold=0.003,
        **kwargs,
    ):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.source_language = normalize_language(source_language) or source_language
        self.target_language = normalize_language(target_language) or target_language
        self.hot_words = hot_words or {}
        self.sample_rate = sample_rate
        self.result_queue = result_queue or queue.Queue()
        self.model = model
        self.api_url = f"wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model={self.model}"
        self.segment_sentences = max(1, int(segment_sentences or 3))
        self.max_segment_seconds = float(max_segment_seconds or 20.0)
        self.min_segment_seconds = float(min_segment_seconds or 3.0)
        self.silence_timeout = float(silence_timeout or 1.2)
        self.voice_threshold = float(voice_threshold or 0.003)

        self._thread = None
        self._running = False
        self._audio_queue = None
        self._ws = None
        self._ws_thread = None
        self._connected = False
        self._session_finished = threading.Event()
        self._finish_requested = threading.Event()
        self._state_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._websocket_generation = 0
        self._last_transcript = ""
        self._last_transcript_language = ""
        self._last_translation = ""
        self._last_emit_key = None
        self._last_partial_key = None
        self._segment_started_at = None
        self._audio_sent_samples = 0
        self._reconnect_after = 0.0
        self._reconnect_delay = 2.0

    @property
    def direction(self):
        return f"{self.source_language}->{self.target_language}"

    def update_settings(self, cfg):
        if cfg.get("api_key") is not None:
            self.api_key = cfg.get("api_key")
        if cfg.get("livetranslate_model"):
            self.model = cfg.get("livetranslate_model")
            self.api_url = f"wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model={self.model}"
        self.segment_sentences = max(1, int(cfg.get("segment_sentences", self.segment_sentences)))
        self.max_segment_seconds = float(cfg.get("max_segment_seconds", self.max_segment_seconds))
        self.min_segment_seconds = float(cfg.get("min_segment_seconds", self.min_segment_seconds))
        self.silence_timeout = float(cfg.get("silence_timeout", self.silence_timeout))
        self.voice_threshold = float(cfg.get("voice_threshold", self.voice_threshold))

    def _build_session_update(self):
        translation = {"language": self.target_language}
        if self.hot_words:
            translation["corpus"] = {"phrases": self.hot_words}

        return {
            "event_id": f"cfg_{self.direction}_{int(time.time() * 1000)}",
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "sample_rate": self.sample_rate,
                "input_audio_format": "pcm",
                "input_audio_transcription": {
                    "model": "qwen3-asr-flash-realtime",
                    "language": self.source_language,
                },
                "translation": translation,
            },
        }

    def _reset_session_state(self):
        with self._state_lock:
            self._last_transcript = ""
            self._last_transcript_language = ""
            self._last_translation = ""
        self._last_partial_key = None
        self._session_finished.clear()
        self._finish_requested.clear()
        self._segment_started_at = None
        self._audio_sent_samples = 0

    def _on_open(self, ws):
        self._connected = True
        self._reconnect_delay = 2.0
        print(f"[LiveTranslate {self.direction}] connected ({self.model})", flush=True)
        ws.send(json.dumps(self._build_session_update(), ensure_ascii=False))

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except Exception as exc:
            print(f"[LiveTranslate {self.direction}] bad message: {exc}", flush=True)
            return

        event_type = data.get("type")
        if event_type == "conversation.item.input_audio_transcription.text":
            self._handle_transcript_delta(data)
        elif event_type == "conversation.item.input_audio_transcription.completed":
            self._handle_transcript_done(data)
        elif event_type == "response.text.text":
            self._handle_translation_delta(data)
        elif event_type in {"response.text.done", "response.audio_transcript.done"}:
            self._handle_translation_done(data)
        elif event_type == "response.done":
            self._emit_result()
        elif event_type == "session.finished":
            self._session_finished.set()
        elif event_type == "error":
            error = data.get("error") or {}
            message = error.get("message") or str(error) or "unknown error"
            print(f"[LiveTranslate {self.direction}] error: {message}", flush=True)
            self._note_service_error(message)
            self.result_queue.put({"type": "error", "text": f"{self.direction}: {message}"})

    def _note_service_error(self, message):
        self._finish_requested.set()
        self._session_finished.set()
        text = str(message or "").lower()
        if "rate limit" in text or "too many" in text:
            delay = min(max(self._reconnect_delay * 1.8, 6.0), 30.0)
            self._reconnect_delay = delay
            self._reconnect_after = time.time() + delay
            print(f"[LiveTranslate {self.direction}] reconnect paused {delay:.0f}s by rate limit", flush=True)
        elif "session already" in text or "already started" in text:
            self._reconnect_after = max(self._reconnect_after, time.time() + 2.0)

    def _sleep_for_backoff(self):
        while self._running:
            remaining = self._reconnect_after - time.time()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.25))

    def _handle_transcript_delta(self, data):
        text = normalize_text((data.get("text") or "") + (data.get("stash") or ""))
        language = normalize_language(data.get("language"))
        if text:
            with self._state_lock:
                self._last_transcript = text
                self._last_transcript_language = language or self._last_transcript_language
            self._emit_partial()

            enough_sentences = count_sentences(text) >= self.segment_sentences
            enough_time = self._segment_elapsed() >= self.min_segment_seconds
            if enough_sentences and enough_time:
                print(
                    f"[LiveTranslate {self.direction}] segment requested by sentence count",
                    flush=True,
                )
                self._finish_requested.set()

    def _handle_transcript_done(self, data):
        transcript = normalize_text(data.get("transcript") or data.get("text") or "")
        language = normalize_language(data.get("language")) or language_from_text(transcript)
        if transcript:
            with self._state_lock:
                self._last_transcript = transcript
                self._last_transcript_language = language
            print(f"[Transcript {self.direction}] {transcript[:80]}", flush=True)
            self._emit_partial()
            self._emit_result()

    def _handle_translation_delta(self, data):
        text = normalize_text((data.get("text") or "") + (data.get("stash") or ""))
        if text:
            with self._state_lock:
                self._last_translation = text
            self._emit_partial()

    def _handle_translation_done(self, data):
        text = normalize_text(data.get("text") or data.get("transcript") or "")
        if text:
            with self._state_lock:
                self._last_translation = text
        self._emit_partial()
        self._emit_result()

    def _language_matches_direction(self, transcript, language):
        if not transcript:
            return True
        if not text_matches_language(transcript, self.source_language):
            return False
        detected = normalize_language(language)
        if detected and detected != self.source_language:
            text_detected = language_from_text(transcript)
            return text_detected == self.source_language
        return True

    def _compose_bilingual(self, transcript, translation):
        if self.source_language == "zh":
            cn_text = transcript
            en_text = translation
        else:
            cn_text = translation
            en_text = transcript

        if not cn_text and self.target_language == "zh":
            cn_text = translation
        if not en_text and self.target_language == "en":
            en_text = translation
        return cn_text, en_text

    def _emit_partial(self):
        with self._state_lock:
            transcript = normalize_text(self._last_transcript)
            language = self._last_transcript_language
            translation = normalize_text(self._last_translation)

        if not transcript and not translation:
            return
        if transcript and not self._language_matches_direction(transcript, language):
            return

        cn_text, en_text = self._compose_bilingual(transcript, translation)
        partial_key = (self.direction, cn_text, en_text)
        if partial_key == self._last_partial_key:
            return
        self._last_partial_key = partial_key

        self.result_queue.put(
            {
                "type": "partial",
                "source_language": self.source_language,
                "target_language": self.target_language,
                "direction": self.direction,
                "source_text": transcript,
                "translated_text": translation,
                "cn_text": cn_text,
                "en_text": en_text,
            }
        )

    def _emit_result(self):
        with self._state_lock:
            transcript = normalize_text(self._last_transcript)
            language = self._last_transcript_language
            translation = normalize_text(self._last_translation)

        if not transcript or not translation:
            return

        if transcript and not self._language_matches_direction(transcript, language):
            print(
                f"[LiveTranslate {self.direction}] ignored mismatched transcript ({language_from_text(transcript) or normalize_language(language)})",
                flush=True,
            )
            return

        emit_key = (self.direction, transcript, translation)
        if emit_key == self._last_emit_key:
            return
        self._last_emit_key = emit_key

        cn_text, en_text = self._compose_bilingual(transcript, translation)

        self.result_queue.put(
            {
                "type": "final",
                "source_language": self.source_language,
                "target_language": self.target_language,
                "direction": self.direction,
                "source_text": transcript,
                "translated_text": translation,
                "cn_text": cn_text,
                "en_text": en_text,
            }
        )
        print(f"[Bilingual {self.direction}] CN={cn_text[:40]} | EN={en_text[:40]}", flush=True)

    def _on_error(self, ws, error):
        print(f"[LiveTranslate {self.direction}] websocket error: {error}", flush=True)
        self._note_service_error(error)
        self.result_queue.put({"type": "error", "text": f"{self.direction}: {error}"})

    def _on_close(self, ws, code, msg):
        self._connected = False
        self._session_finished.set()
        print(f"[LiveTranslate {self.direction}] closed ({code})", flush=True)

    def _send_audio_chunk(self, audio_data):
        if not self._connected or not self._ws:
            return False
        try:
            self._ws.send(
                json.dumps(
                    {
                        "event_id": f"a_{self.direction}_{int(time.time() * 1000)}",
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(audio_data).decode(),
                    }
                )
            )
            self._audio_sent_samples += len(audio_data) // 2
            if self._segment_started_at is None:
                self._segment_started_at = time.time()
            return True
        except Exception as exc:
            print(f"[LiveTranslate {self.direction}] audio send failed: {exc}", flush=True)
            return False

    def _send_session_finish(self):
        if not self._connected or not self._ws:
            return
        try:
            self._ws.send(
                json.dumps(
                    {
                        "event_id": f"f_{self.direction}_{int(time.time() * 1000)}",
                        "type": "session.finish",
                    }
                )
            )
        except Exception as exc:
            print(f"[LiveTranslate {self.direction}] finish send failed: {exc}", flush=True)

    def _segment_elapsed(self):
        if self._segment_started_at is None:
            return 0.0
        return time.time() - self._segment_started_at

    def _max_segment_reached(self):
        if self._segment_started_at is None:
            return False
        return self._segment_elapsed() >= self.max_segment_seconds

    def _next_websocket_generation(self):
        with self._lifecycle_lock:
            self._websocket_generation += 1
            return self._websocket_generation

    def _is_current_websocket(self, generation):
        with self._lifecycle_lock:
            return generation == self._websocket_generation

    def _invalidate_websocket(self):
        with self._lifecycle_lock:
            self._websocket_generation += 1

    def _close_websocket(self, send_finish=False, invalidate=False):
        ws = self._ws
        ws_thread = self._ws_thread
        if send_finish and self._connected and ws:
            self._send_session_finish()
            time.sleep(0.2)
        if invalidate:
            self._invalidate_websocket()
        self._connected = False
        if ws:
            try:
                ws.close()
            except Exception:
                pass
        if ws_thread and ws_thread.is_alive() and ws_thread is not threading.current_thread():
            ws_thread.join(timeout=1.5)
        if self._ws is ws:
            self._ws = None
        if self._ws_thread is ws_thread:
            self._ws_thread = None

    def _start_websocket(self):
        import websocket

        generation = self._next_websocket_generation()

        def on_open(ws):
            if self._is_current_websocket(generation):
                self._on_open(ws)

        def on_message(ws, message):
            if self._is_current_websocket(generation):
                self._on_message(ws, message)

        def on_error(ws, error):
            if self._is_current_websocket(generation):
                self._on_error(ws, error)

        def on_close(ws, code, msg):
            if self._is_current_websocket(generation):
                self._on_close(ws, code, msg)

        headers = [f"Authorization: Bearer {self.api_key}"]
        self._ws = websocket.WebSocketApp(
            self.api_url,
            header=headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        self._ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._ws_thread.start()

        for _ in range(80):
            if self._connected:
                return True
            if not self._running:
                return False
            time.sleep(0.1)
        return False

    def start(self, audio_queue):
        if self._running:
            self.stop()
        self._audio_queue = audio_queue
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._finish_requested.set()
        self._close_websocket(send_finish=True, invalidate=True)
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def reset_cache(self):
        with self._state_lock:
            self._last_transcript = ""
            self._last_transcript_language = ""
            self._last_translation = ""
        self._last_emit_key = None
        self._last_partial_key = None

    def _process_loop(self):
        while self._running:
            self._sleep_for_backoff()
            if not self._running:
                break
            self._reset_session_state()
            try:
                if not self._start_websocket():
                    time.sleep(1)
                    continue
                self._run_audio_session()
            except Exception as exc:
                print(f"[LiveTranslate {self.direction}] loop error: {exc}", flush=True)
                time.sleep(1)
            finally:
                self._close_websocket(invalidate=True)

    def _run_audio_session(self):
        buffer = np.array([], dtype=np.float32)
        chunk_samples = int(self.sample_rate * 0.1)
        min_segment_samples = int(self.sample_rate * self.min_segment_seconds)
        last_voice_time = None
        active_segment = False

        while self._running and self._connected:
            try:
                audio = self._audio_queue.get(timeout=0.2)
            except queue.Empty:
                audio = None

            if audio is None:
                if active_segment and self._finish_requested.is_set():
                    break
                continue

            audio_np = audio if isinstance(audio, np.ndarray) else np.array(audio, dtype=np.float32)
            if audio_np.size == 0:
                continue

            rms = float(np.sqrt(np.mean(audio_np ** 2)))
            has_voice = rms > self.voice_threshold

            if not active_segment and not has_voice:
                continue

            if has_voice:
                active_segment = True
                last_voice_time = time.time()

            max_amp = float(np.max(np.abs(audio_np)))
            if 0 < max_amp < 0.5:
                audio_np = audio_np * min(0.8 / max_amp, 20.0)

            buffer = np.concatenate([buffer, audio_np])
            while len(buffer) >= chunk_samples:
                chunk = buffer[:chunk_samples]
                buffer = buffer[chunk_samples:]
                pcm = (chunk * 32767).clip(-32768, 32767).astype(np.int16).tobytes()
                self._send_audio_chunk(pcm)

            if not active_segment:
                continue

            enough_audio = self._audio_sent_samples >= min_segment_samples
            silence_reached = (
                enough_audio
                and last_voice_time is not None
                and (time.time() - last_voice_time) >= self.silence_timeout
            )

            if self._finish_requested.is_set() and enough_audio:
                break
            if silence_reached:
                print(f"[LiveTranslate {self.direction}] segment requested by silence", flush=True)
                break
            if self._max_segment_reached():
                print(f"[LiveTranslate {self.direction}] segment requested by max seconds", flush=True)
                break

        if buffer.size:
            pcm = (buffer * 32767).clip(-32768, 32767).astype(np.int16).tobytes()
            self._send_audio_chunk(pcm)

        if active_segment and self._connected:
            self._send_session_finish()
            self._session_finished.wait(timeout=6)


class DualLiveTranslateEngine:
    """Bidirectional Chinese/English realtime translation using two model sessions."""

    def __init__(self, api_key=None, hot_words=None, sample_rate=16000, **kwargs):
        self.result_queue = queue.Queue()
        self.sample_rate = sample_rate
        self.language_mode = normalize_language_mode(kwargs.get("language_mode", "auto"))
        self._running = False
        self._audio_queue = None
        self._fanout_thread = None
        self._zh_audio_queue = queue.Queue(maxsize=120)
        self._en_audio_queue = queue.Queue(maxsize=120)

        common = {
            "api_key": api_key,
            "sample_rate": sample_rate,
            "result_queue": self.result_queue,
            "model": kwargs.get("model", "qwen3.5-livetranslate-flash-realtime"),
            "segment_sentences": kwargs.get("segment_sentences", 3),
            "max_segment_seconds": kwargs.get("max_segment_seconds", 20.0),
            "min_segment_seconds": kwargs.get("min_segment_seconds", 3.0),
            "silence_timeout": kwargs.get("silence_timeout", 1.2),
            "voice_threshold": kwargs.get("voice_threshold", 0.003),
        }

        self.zh_to_en = LiveTranslateEngine(
            source_language="zh",
            target_language="en",
            hot_words=hot_words,
            **common,
        )
        self.en_to_zh = LiveTranslateEngine(
            source_language="en",
            target_language="zh",
            hot_words=reverse_hot_words(hot_words),
            **common,
        )

    def update_settings(self, cfg):
        hot_words = cfg.get("hot_words", {})
        self.language_mode = normalize_language_mode(cfg.get("language_mode", self.language_mode))
        self.zh_to_en.hot_words = hot_words
        self.en_to_zh.hot_words = reverse_hot_words(hot_words)
        for engine in (self.zh_to_en, self.en_to_zh):
            engine.update_settings(cfg)

    def _active_pairs(self):
        if self.language_mode == "zh":
            return [(self.zh_to_en, self._zh_audio_queue)]
        if self.language_mode == "en":
            return [(self.en_to_zh, self._en_audio_queue)]
        return [
            (self.zh_to_en, self._zh_audio_queue),
            (self.en_to_zh, self._en_audio_queue),
        ]

    def start(self, audio_queue):
        if self._running:
            self.stop()
        self._audio_queue = audio_queue
        self._drain_queue(self._zh_audio_queue)
        self._drain_queue(self._en_audio_queue)
        self._running = True
        print(f"[LiveTranslate dual] language mode: {language_mode_label(self.language_mode)}", flush=True)
        for engine, audio_target in self._active_pairs():
            engine.start(audio_target)
        self._fanout_thread = threading.Thread(target=self._fanout_loop, daemon=True)
        self._fanout_thread.start()

    def stop(self):
        self._running = False
        if self._fanout_thread:
            self._fanout_thread.join(timeout=2)
            self._fanout_thread = None
        self.zh_to_en.stop()
        self.en_to_zh.stop()

    def reset_cache(self):
        self.zh_to_en.reset_cache()
        self.en_to_zh.reset_cache()
        self._drain_queue(self.result_queue)

    def _fanout_loop(self):
        while self._running:
            try:
                audio = self._audio_queue.get(timeout=0.3)
            except queue.Empty:
                continue
            if audio is None:
                continue
            for engine, audio_target in self._active_pairs():
                audio_item = np.copy(audio) if engine is self.en_to_zh and isinstance(audio, np.ndarray) else audio
                self._put_latest(audio_target, audio_item)

    @staticmethod
    def _put_latest(target_queue, item):
        try:
            target_queue.put_nowait(item)
        except queue.Full:
            try:
                target_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                target_queue.put_nowait(item)
            except queue.Full:
                pass

    @staticmethod
    def _drain_queue(target_queue):
        try:
            while True:
                target_queue.get_nowait()
        except queue.Empty:
            pass
