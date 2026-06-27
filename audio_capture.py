import queue
import threading
import numpy as np
import sounddevice as sd


class AudioCapture:
    def __init__(self, sample_rate=16000, device_id=None, chunk_duration=0.6):
        self.sample_rate = sample_rate
        self.device_id = device_id
        self.chunk_samples = int(sample_rate * chunk_duration)
        self.audio_queue = queue.Queue()
        self._stream = None
        self._running = False

    @staticmethod
    def list_input_devices():
        devices = sd.query_devices()
        input_devices = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                input_devices.append({
                    "id": i,
                    "name": d["name"],
                    "channels": d["max_input_channels"],
                    "sample_rate": d["default_samplerate"],
                })
        return input_devices

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            pass
        audio = indata[:, 0].copy()
        self.audio_queue.put(audio)

    def start(self):
        if self._running:
            return
        self._running = True
        kwargs = {
            "samplerate": self.sample_rate,
            "channels": 1,
            "dtype": "float32",
            "blocksize": self.chunk_samples,
            "callback": self._audio_callback,
        }
        if self.device_id is not None:
            kwargs["device"] = self.device_id
        self._stream = sd.InputStream(**kwargs)
        self._stream.start()

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_chunk(self, timeout=1.0):
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
