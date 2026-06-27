import threading
import queue
import numpy as np


class ASREngine:
    def __init__(self, model_name="paraformer-zh-streaming", chunk_size=None,
                 encoder_chunk_look_back=4, decoder_chunk_look_back=1,
                 punc_model="ct-punc"):
        self.model_name = model_name
        self.punc_model = punc_model
        self.chunk_size = chunk_size or [0, 10, 5]
        self.encoder_chunk_look_back = encoder_chunk_look_back
        self.decoder_chunk_look_back = decoder_chunk_look_back
        self._model = None
        self._punc_model = None
        self._cache = {}
        self.result_queue = queue.Queue()
        self._thread = None
        self._running = False
        self._audio_queue = None
        self.silence_timeout = 1.5

    def load_model(self):
        from funasr import AutoModel
        self._model = AutoModel(model=self.model_name)
        try:
            self._punc_model = AutoModel(model=self.punc_model)
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

    def reset_cache(self):
        self._cache = {}

    def recognize_chunk(self, audio_chunk, is_final=False):
        res = self._model.generate(
            input=audio_chunk,
            cache=self._cache,
            is_final=is_final,
            chunk_size=self.chunk_size,
            encoder_chunk_look_back=self.encoder_chunk_look_back,
            decoder_chunk_look_back=self.decoder_chunk_look_back,
        )
        text = ""
        if res and len(res) > 0 and "text" in res[0]:
            text = res[0]["text"]
        return text

    def start(self, audio_queue):
        self._audio_queue = audio_queue
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _process_loop(self):
        import time
        last_has_text_time = time.time()
        accumulated_text = ""

        while self._running:
            timeout = self.silence_timeout
            try:
                audio = self._audio_queue.get(timeout=0.3)
            except queue.Empty:
                if accumulated_text and (time.time() - last_has_text_time > timeout):
                    try:
                        final_text = self.recognize_chunk(np.zeros(960, dtype=np.float32), is_final=True)
                        if final_text:
                            accumulated_text += final_text
                    except Exception:
                        pass
                    punc_text = self.add_punctuation(accumulated_text)
                    self.result_queue.put({"type": "final", "text": punc_text})
                    accumulated_text = ""
                    self.reset_cache()
                continue

            if audio is None:
                continue

            audio_np = audio if isinstance(audio, np.ndarray) else np.array(audio, dtype=np.float32)

            try:
                text = self.recognize_chunk(audio_np, is_final=False)
            except Exception as e:
                self.result_queue.put({"type": "error", "text": str(e)})
                continue

            if text:
                last_has_text_time = time.time()
                accumulated_text += text
                self.result_queue.put({"type": "partial", "text": accumulated_text})
            else:
                if accumulated_text and (time.time() - last_has_text_time > timeout):
                    try:
                        final_text = self.recognize_chunk(np.zeros(960, dtype=np.float32), is_final=True)
                        if final_text:
                            accumulated_text += final_text
                    except Exception:
                        pass
                    punc_text = self.add_punctuation(accumulated_text)
                    self.result_queue.put({"type": "final", "text": punc_text})
                    accumulated_text = ""
                    self.reset_cache()
