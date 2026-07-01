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
            from live_translate_engine import DualLiveTranslateEngine

            cfg = load_config()
            api_key = cfg.get("api_key", "")

            if not api_key:
                app_state["error"] = "no_api_key"
                return

            root.after(0, lambda: label.config(text="连接实时同传服务..."))
            asr = DualLiveTranslateEngine(
                api_key=api_key,
                hot_words=cfg.get("hot_words", {}),
                sample_rate=cfg.get("sample_rate", 16000),
                model=cfg.get("livetranslate_model", "qwen3.5-livetranslate-flash-realtime"),
                segment_sentences=cfg.get("segment_sentences", 3),
                max_segment_seconds=cfg.get("max_segment_seconds", 20.0),
                min_segment_seconds=cfg.get("min_segment_seconds", 3.0),
                silence_timeout=cfg.get("silence_timeout", 1.2),
                voice_threshold=cfg.get("voice_threshold", 0.003),
                language_mode=cfg.get("language_mode", "auto"),
            )

            app_state["data"] = {"cfg": cfg, "asr": asr}
            app_state["done"] = True
        except Exception as e:
            app_state["error"] = str(e)

    threading.Thread(target=bg_setup, daemon=True).start()

    def poll_ready():
        if app_state["error"] == "no_api_key":
            from config import load_config, save_config
            from settings_panel import SettingsPanel

            cfg = load_config()

            def on_key_saved(new_cfg):
                save_config(new_cfg)
                app_state["error"] = None
                label.config(text="重新启动中...")
                root.update()
                threading.Thread(target=bg_setup, daemon=True).start()
                root.after(1000, poll_ready)

            label.config(text="首次使用，请配置 API Key")
            root.update()
            panel = SettingsPanel(cfg, on_apply=on_key_saved)
            panel.show(parent=root)
            if app_state["error"] == "no_api_key":
                root.destroy()
            return
        elif app_state["error"]:
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
        capture_mode = cfg.get("capture_mode", "microphone")

        from system_audio_capture import CombinedAudioCapture

        # 获取所有可用设备
        all_devices = CombinedAudioCapture.list_all_devices()
        device_id = None

        if cfg.get("device_id") is not None:
            # 检查保存的设备是否仍然可用
            for d in all_devices:
                if d["id"] == cfg["device_id"]:
                    device_id = cfg["device_id"]
                    break

        if device_id is None:
            # 自动选择默认设备
            skip = {"blackhole", "steam streaming", "soundflower", "virtual"}
            for d in all_devices:
                name_lower = d["name"].lower()
                if any(s in name_lower for s in skip):
                    continue
                if d.get("type") == "microphone":
                    if "麦克风" in d["name"] or "microphone" in name_lower or "macbook" in name_lower:
                        device_id = d["id"]
                        cfg["device_id"] = d["id"]
                        cfg["device_name"] = d["name"]
                        break
            if device_id is None and all_devices:
                device_id = all_devices[0]["id"]

        audio = CombinedAudioCapture(sample_rate=cfg.get("sample_rate", 16000))

        root.destroy()

        from main import start_subtitle_app
        start_subtitle_app(cfg, audio, asr, device_id, capture_mode)

    root.after(500, poll_ready)
    root.mainloop()


if __name__ == "__main__":
    main()
