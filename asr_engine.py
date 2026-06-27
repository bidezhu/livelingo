import threading
import queue
import numpy as np
import io
import wave
import base64
import json
import re


def numpy_to_wav_base64(audio_np, sample_rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        pcm = (audio_np * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class ASREngine:
    def __init__(self, api_key=None, base_url="https://api.xiaomimimo.com/v1",
                 model="mimo-v2.5-asr", sample_rate=16000,
                 punc_model=None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.sample_rate = sample_rate
        self.result_queue = queue.Queue()
        self._thread = None
        self._running = False
        self._audio_queue = None
        self.silence_timeout = 1.5
        self._client = None
        self._punc_model_name = punc_model
        self._punc_model = None

    def load_model(self):
        from openai import OpenAI
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        if self._punc_model_name:
            try:
                from funasr import AutoModel
                self._punc_model = AutoModel(model=self._punc_model_name, device="cpu")
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
        audio_b64 = numpy_to_wav_base64(audio_np, self.sample_rate)
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/wav;base64,{audio_b64}"
                            }
                        }
                    ]
                }
            ],
            extra_body={
                "asr_options": {
                    "language": "auto"
                }
            },
            stream=False,
        )
        text = completion.choices[0].message.content
        if text:
            text = re.sub(r'<\|[^|]*\|>', '', text).strip()
        return text or ""

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
        min_buffer_samples = self.sample_rate * 1
        max_buffer_samples = self.sample_rate * 15

        while self._running:
            try:
                audio = self._audio_queue.get(timeout=0.3)
            except queue.Empty:
                if len(buffer) >= min_buffer_samples and (time.time() - last_voice_time > self.silence_timeout):
                    self._flush_buffer(buffer)
                    buffer = np.array([], dtype=np.float32)
                continue

            if audio is None:
                continue

            audio_np = audio if isinstance(audio, np.ndarray) else np.array(audio, dtype=np.float32)
            buffer = np.concatenate([buffer, audio_np])

            rms = np.sqrt(np.mean(audio_np ** 2))
            if rms > 0.01:
                last_voice_time = time.time()

            if len(buffer) >= max_buffer_samples or (len(buffer) >= min_buffer_samples and time.time() - last_voice_time > self.silence_timeout):
                self._flush_buffer(buffer)
                buffer = np.array([], dtype=np.float32)

    def _flush_buffer(self, buffer):
        if len(buffer) < self.sample_rate * 0.5:
            return
        try:
            text = self.recognize(buffer)
            if text:
                self.result_queue.put({"type": "final", "text": text})
        except Exception as e:
            self.result_queue.put({"type": "error", "text": str(e)})
