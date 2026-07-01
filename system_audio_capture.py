import queue
import threading
import numpy as np


def _run_with_timeout(label, timeout, target):
    result = {"value": []}

    def worker():
        try:
            result["value"] = target() or []
        except Exception as exc:
            print(f"[AudioDevices] {label} 枚举失败: {exc}", flush=True)
            result["value"] = []

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print(f"[AudioDevices] {label} 枚举超时，先使用已获取的设备", flush=True)
        return []
    return result["value"]


class SystemAudioCapture:
    """捕获系统音频（电脑播放的声音）"""

    def __init__(self, sample_rate=16000, chunk_duration=0.6):
        self.sample_rate = sample_rate
        self.chunk_samples = int(sample_rate * chunk_duration)
        self.audio_queue = queue.Queue()
        self._running = False
        self._thread = None

    @staticmethod
    def is_available():
        """检查系统音频捕获是否可用"""
        try:
            import soundcard
            return True
        except ImportError:
            return False

    @staticmethod
    def _virtual_system_sources():
        import soundcard

        keywords = (
            "blackhole",
            "soundflower",
            "loopback",
            "qsaudio",
            "system audio",
            "steam streaming speakers",
            "virtual",
        )
        sources = []
        microphones = soundcard.all_microphones(include_loopback=True)
        for mic in microphones:
            name = getattr(mic, "name", "")
            if any(keyword in name.lower() for keyword in keywords):
                sources.append(mic)
        return sources

    @staticmethod
    def list_loopback_devices(timeout=2.0):
        """列出可用的系统音频回录设备。macOS 需要 BlackHole/Loopback 等虚拟输入。"""
        def collect():
            devices = []
            sources = SystemAudioCapture._virtual_system_sources()
            for i, source in enumerate(sources):
                devices.append({
                    "id": i,
                    "name": f"🔊 {source.name} (系统音频)",
                    "soundcard_id": getattr(source, "id", i),
                    "channels": getattr(source, "channels", 1),
                    "sample_rate": 16000,
                    "type": "system"
                })
            return devices

        return _run_with_timeout("系统音频", timeout, collect)

    def start(self, speaker_index=0):
        """开始捕获系统音频"""
        if self._running:
            return
        self._running = True
        self._speaker_index = speaker_index
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止捕获"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _capture_loop(self):
        """音频捕获循环"""
        try:
            sources = self._virtual_system_sources()
            if self._speaker_index >= len(sources):
                print("[SystemAudio] 未找到可用系统音频虚拟输入，请安装或选择 BlackHole/Loopback", flush=True)
                return

            source = sources[self._speaker_index]
            print(f"[SystemAudio] 开始捕获: {source.name}", flush=True)

            with source.recorder(samplerate=self.sample_rate, channels=1) as mic:
                while self._running:
                    data = mic.record(numframes=self.chunk_samples)
                    if data is not None and len(data) > 0:
                        # 转换为单声道 float32
                        audio = data[:, 0].astype(np.float32)
                        self.audio_queue.put(audio)

        except ImportError:
            print("[SystemAudio] soundcard 库未安装", flush=True)
        except Exception as e:
            print(f"[SystemAudio] 错误: {e}", flush=True)


class CombinedAudioCapture:
    """同时捕获麦克风和系统音频"""

    def __init__(self, sample_rate=16000, chunk_duration=0.6):
        self.sample_rate = sample_rate
        self.chunk_samples = int(sample_rate * chunk_duration)
        self.audio_queue = queue.Queue()
        self._running = False

        # 麦克风捕获
        self._mic_capture = None
        self._mic_thread = None

        # 系统音频捕获
        self._system_capture = None
        self._system_thread = None

    @staticmethod
    def list_all_devices(timeout=2.0):
        """列出所有可用的音频输入设备"""
        def collect_microphones():
            devices = []
            import sounddevice as sd
            sd_devices = sd.query_devices()
            for i, d in enumerate(sd_devices):
                if d["max_input_channels"] > 0:
                    devices.append({
                        "id": i,
                        "name": f"🎤 {d['name']}",
                        "channels": d["max_input_channels"],
                        "sample_rate": d["default_samplerate"],
                        "type": "microphone"
                    })
            return devices

        devices = []
        devices.extend(_run_with_timeout("麦克风", timeout, collect_microphones))
        devices.extend(SystemAudioCapture.list_loopback_devices(timeout=timeout))

        return devices

    def start(self, device_id=None, capture_mode="microphone"):
        """
        开始音频捕获

        Args:
            device_id: 设备 ID（麦克风 ID 或扬声器索引）
            capture_mode: 捕获模式 ("microphone", "system", "both")
        """
        if self._running:
            return

        self._running = True
        self._capture_mode = capture_mode

        if capture_mode in ("microphone", "both"):
            self._start_microphone(device_id)

        if capture_mode in ("system", "both"):
            speaker_index = device_id if capture_mode == "system" else 0
            self._start_system_audio(speaker_index)

    def _start_microphone(self, device_id):
        """启动麦克风捕获"""
        import sounddevice as sd
        import numpy as np

        self._audio_count = 0

        def mic_callback(indata, frames, time_info, status):
            if status:
                print(f"[AudioCapture] 麦克风状态: {status}", flush=True)
            audio = indata[:, 0].copy()
            self.audio_queue.put(audio)
            self._audio_count += 1
            if self._audio_count % 100 == 0:
                max_amp = np.max(np.abs(audio))
                print(f"[AudioCapture] 已捕获 {self._audio_count} 块, 最大振幅: {max_amp:.4f}", flush=True)

        kwargs = {
            "samplerate": self.sample_rate,
            "channels": 1,
            "dtype": "float32",
            "blocksize": self.chunk_samples,
            "callback": mic_callback,
        }
        if device_id is not None and isinstance(device_id, int):
            kwargs["device"] = device_id

        try:
            self._mic_stream = sd.InputStream(**kwargs)
            self._mic_stream.start()
            print(f"[AudioCapture] 麦克风已启动 (设备ID: {device_id})", flush=True)
        except Exception as e:
            print(f"[AudioCapture] 麦克风启动失败: {e}", flush=True)

    def _start_system_audio(self, speaker_index=0):
        """启动系统音频捕获"""
        self._system_capture = SystemAudioCapture(
            sample_rate=self.sample_rate,
            chunk_duration=self.chunk_samples / self.sample_rate
        )
        self._system_capture.start(speaker_index)
        print("[AudioCapture] 系统音频捕获已启动", flush=True)

    def stop(self):
        """停止所有音频捕获"""
        self._running = False

        if hasattr(self, '_mic_stream') and self._mic_stream:
            self._mic_stream.stop()
            self._mic_stream.close()
            self._mic_stream = None

        if self._system_capture:
            self._system_capture.stop()
            self._system_capture = None

    def get_chunk(self, timeout=1.0):
        """获取音频块"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
