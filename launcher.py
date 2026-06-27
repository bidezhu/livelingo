#!/usr/bin/env python3
import sys
import os
import threading


def log(msg):
    print(f"[LiveLingo] {msg}", flush=True)


def setup_path():
    for p in ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", os.path.expanduser("~/.local/bin")]:
        if p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p + ":" + os.environ.get("PATH", "")
    if "TCL_LIBRARY" not in os.environ:
        import glob
        python_base = os.path.dirname(os.path.dirname(sys.executable))
        tcl_candidates = glob.glob(os.path.join(python_base, "lib", "tcl*"))
        if tcl_candidates:
            os.environ["TCL_LIBRARY"] = tcl_candidates[0]
        tk_candidates = glob.glob(os.path.join(python_base, "lib", "tk*"))
        if tk_candidates:
            os.environ["TK_LIBRARY"] = tk_candidates[0]


def main():
    setup_path()

    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, base_dir)

    import tkinter as tk

    root = tk.Tk()
    root.title("LiveLingo")
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.geometry(f"420x140+{screen_w//2-210}+{screen_h//2-70}")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg="#1a1a1a")

    label = tk.Label(root, text="正在启动 LiveLingo...", font=("Helvetica", 15),
                     bg="#1a1a1a", fg="#ffffff", pady=40)
    label.pack(fill="both", expand=True)
    root.update()

    app_state = {"done": False, "error": None, "data": None}

    def bg_setup():
        try:
            from config import load_config
            from asr_engine import ASREngine
            from translator import Translator

            cfg = load_config()
            api_key = cfg.get("api_key", "")

            if not api_key:
                app_state["error"] = "未配置 API Key\n请在设置中填入"
                return

            root.after(0, lambda: label.config(text="连接 ASR 服务..."))

            asr = ASREngine(
                api_key=api_key,
                model=cfg.get("asr_model", "fun-asr-realtime"),
                sample_rate=cfg.get("sample_rate", 16000),
            )
            asr.silence_timeout = cfg.get("silence_timeout", 1.5)
            asr.load_model()

            root.after(0, lambda: label.config(text="连接翻译服务..."))
            translator = Translator(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model=cfg.get("translate_model", "qwen-plus"),
            )
            translator.load()

            app_state["data"] = {"cfg": cfg, "asr": asr, "translator": translator}
            app_state["done"] = True
        except Exception as e:
            app_state["error"] = str(e)

    threading.Thread(target=bg_setup, daemon=True).start()

    def poll_ready():
        if app_state["error"]:
            label.config(text=f"启动失败:\n{app_state['error']}")
            return

        if not app_state["done"]:
            root.after(200, poll_ready)
            return

        label.config(text="启动中...")
        root.update()

        data = app_state["data"]
        cfg = data["cfg"]
        asr = data["asr"]
        translator = data["translator"]

        from audio_capture import AudioCapture

        devices = AudioCapture.list_input_devices()
        device_id = None
        if cfg.get("device_id") is not None and any(d["id"] == cfg["device_id"] for d in devices):
            device_id = cfg["device_id"]
        else:
            for d in devices:
                if "麦克风" in d["name"] or "microphone" in d["name"].lower():
                    device_id = d["id"]
                    break
            if device_id is None and devices:
                device_id = devices[0]["id"]

        audio = AudioCapture(sample_rate=cfg.get("sample_rate", 16000), device_id=device_id)

        root.destroy()

        from main import start_subtitle_app
        start_subtitle_app(cfg, audio, asr, translator, device_id)

    root.after(500, poll_ready)
    root.mainloop()


if __name__ == "__main__":
    main()
