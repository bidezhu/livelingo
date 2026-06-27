import threading
import queue
import numpy as np
import io
import wave
import base64
import re
import os


FILLER_PATTERNS = [
    r'^(嗯+|啊+|额+|呃+|哦+|嗯哼+|哈+)+[，,。.！!？?]*$',
    r'^(uh+|um+|er+|ah+|oh+|hmm+|mm+)+[,.!?]*$',
    r'^(那个|就是|然后|怎么说呢|就是说|对吧|是吧|你知道)+[，,。.]*$',
    r'^(you know|like|I mean|well|so|right|basically)+[,!.]*$',
    r'^[，,。.！!？?\s]+$',
]


def is_filler(text):
    text = text.strip()
    if not text or len(text) <= 1:
        return True
    for pattern in FILLER_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    return False


class ASREngine:
    def __init__(self, api_key=None, base_url=None, model="fun-asr-realtime",
                 sample_rate=16000, **kwargs):
        self.api_key = api_key
        self.model = model
        self.sample_rate = sample_rate
        self.result_queue = queue.Queue()
        self._thread = None
        self._running = False
        self._audio_queue = None
        self.silence_timeout = 1.5
        self.voice_threshold = 0.02
        self._recognition = None
        self._callback = None

    def load_model(self):
        import dashscope
        dashscope.api_key = self.api_key
        dashscope.base_websocket_api_url = 'wss://dashscope.aliyuncs.com/api-ws/v1/inference'

    def _create_recognition(self):
        from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

        engine = self

        class ASRCallback(RecognitionCallback):
            def on_event(self, result):
                sentence = result.get_sentence()
                if sentence and 'text' in sentence:
                    text = sentence['text']
                    if RecognitionResult.is_sentence_end(sentence):
                        if text and not is_filler(text):
                            engine.result_queue.put({"type": "final", "text": text})
                    else:
                        if text and not is_filler(text):
                            engine.result_queue.put({"type": "partial", "text": text})

            def on_complete(self):
                pass

            def on_error(self, result):
                engine.result_queue.put({"type": "error", "text": str(result.message)})

        self._callback = ASRCallback()
        self._recognition = Recognition(
            model=self.model,
            format='pcm',
            sample_rate=self.sample_rate,
            semantic_punctuation_enabled=False,
            callback=self._callback,
        )

    def start(self, audio_queue):
        self._audio_queue = audio_queue
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._recognition:
            try:
                self._recognition.stop()
            except Exception:
                pass

    def reset_cache(self):
        pass

    def _process_loop(self):
        import time

        while self._running:
            self._create_recognition()
            try:
                self._recognition.start()
            except Exception as e:
                self.result_queue.put({"type": "error", "text": f"连接失败: {e}"})
                time.sleep(3)
                continue

            buffer = np.array([], dtype=np.float32)
            last_voice_time = time.time()
            min_buffer_samples = self.sample_rate * 0.5

            while self._running:
                try:
                    audio = self._audio_queue.get(timeout=0.3)
                except queue.Empty:
                    if len(buffer) >= min_buffer_samples and (time.time() - last_voice_time > self.silence_timeout):
                        if len(buffer) > 0:
                            pcm = (buffer * 32767).astype(np.int16).tobytes()
                            try:
                                self._recognition.send_audio_frame(pcm)
                            except Exception:
                                pass
                            try:
                                self._recognition.stop()
                            except Exception:
                                pass
                            buffer = np.array([], dtype=np.float32)
                            time.sleep(0.5)
                            break
                    continue

                if audio is None:
                    continue

                audio_np = audio if isinstance(audio, np.ndarray) else np.array(audio, dtype=np.float32)
                buffer = np.concatenate([buffer, audio_np])

                rms = np.sqrt(np.mean(audio_np ** 2))
                if rms > self.voice_threshold:
                    last_voice_time = time.time()

                chunk_samples = int(self.sample_rate * 0.1)
                while len(buffer) >= chunk_samples:
                    chunk = buffer[:chunk_samples]
                    buffer = buffer[chunk_samples:]
                    pcm = (chunk * 32767).astype(np.int16).tobytes()
                    try:
                        self._recognition.send_audio_frame(pcm)
                    except Exception:
                        break

            try:
                self._recognition.getDuplexApi().close(1000, "bye")
            except Exception:
                pass
