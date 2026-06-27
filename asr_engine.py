import threading
import queue
import numpy as np


class ASREngine:
    def __init__(self, model_name="iic/SenseVoiceSmall", vad_model="fsmn-vad",
                 punc_model="ct-punc", chunk_size=None,
                 encoder_chunk_look_back=4, decoder_chunk_look_back=1):
        self.model_name = model_name
        self.vad_model = vad_model
        self.punc_model = punc_model
        self._model = None
        self._punc_model = None
        self.result_queue = queue.Queue()
        self._thread = None
        self._running = False
        self._audio_queue = None
        self.silence_timeout = 1.5

    def load_model(self):
        from funasr import AutoModel
        self._model = AutoModel(
            model=self.model_name,
            vad_model=self.vad_model,
            device="cpu",
        )
        try:
            self._punc_model = AutoModel(model=self.punc_model, device="cpu")
        except Exception:
            self._punc_model = None

    def add_punctuation(self, text):
        if not text or not self._punc_model:
            return text
        try:
            res = self._punc_model.generate(input=text)
            if res and len(res) > 0 and "text" in res[0]:
                return res[0]["text"]
        except Exception:
            pass
        return text

    def recognize(self, audio_np):
        res = self._model.generate(
            input=audio_np,
            batch_size_s=300,
        )
        text = ""
        if res and len(res) > 0:
            raw = res[0].get("text", "")
            import re
            text = re.sub(r'<\|[^|]*\|>', '', raw).strip()
        return text

    def start(self, audio_queue):
        self._audio_queue = audio_queue
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def reset_cache(self):
        pass

    def _process_loop(self):
        import time
        buffer = np.array([], dtype=np.float32)
        last_voice_time = time.time()
        min_buffer_samples = 16000 * 1
        max_buffer_samples = 16000 * 15

        while self._running:
            try:
                audio = self._audio_queue.get(timeout=0.3)
            except queue.Empty:
                if len(buffer) >= min_buffer_samples and (time.time() - last_voice_time > self.silence_timeout):
                    try:
                        text = self.recognize(buffer)
                        if text:
                            punc_text = self.add_punctuation(text)
                            self.result_queue.put({"type": "final", "text": punc_text})
                    except Exception as e:
                        self.result_queue.put({"type": "error", "text": str(e)})
                    buffer = np.array([], dtype=np.float32)
                continue

            if audio is None:
                continue

            audio_np = audio if isinstance(audio, np.ndarray) else np.array(audio, dtype=np.float32)
            buffer = np.concatenate([buffer, audio_np])

            rms = np.sqrt(np.mean(audio_np ** 2))
            if rms > 0.01:
                last_voice_time = time.time()
                if len(buffer) > min_buffer_samples:
                    self.result_queue.put({"type": "partial", "text": "[正在听...]"})

            if len(buffer) >= max_buffer_samples or (len(buffer) >= min_buffer_samples and time.time() - last_voice_time > self.silence_timeout):
                try:
                    text = self.recognize(buffer)
                    if text:
                        punc_text = self.add_punctuation(text)
                        self.result_queue.put({"type": "final", "text": punc_text})
                except Exception as e:
                    self.result_queue.put({"type": "error", "text": str(e)})
                buffer = np.array([], dtype=np.float32)
