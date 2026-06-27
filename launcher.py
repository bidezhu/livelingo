#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil
import time
import json
import threading


OLLAMA_MODEL = "qwen3.5:9b"


def log(msg):
    print(f"[LiveLingo] {msg}", flush=True)


def check_ollama_binary():
    return shutil.which("ollama") is not None


def check_ollama_running():
    try:
        r = subprocess.run(
            ["curl", "-s", "--max-time", "3", "http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            return True, data.get("models", [])
    except Exception:
        pass
    return False, []


def install_ollama():
    log("安装 Ollama...")
    try:
        r = subprocess.run(
            ["/bin/bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
            capture_output=True, text=True, timeout=300
        )
        return r.returncode == 0
    except Exception:
        return False


def start_ollama():
    log("启动 Ollama...")
    subprocess.Popen(["ollama", "serve"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(15):
        time.sleep(1)
        running, _ = check_ollama_running()
        if running:
            return True
    return False


def pull_model():
    log(f"下载模型 {OLLAMA_MODEL}...")
    proc = subprocess.Popen(
        ["ollama", "pull", OLLAMA_MODEL],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in proc.stdout:
        if line.strip():
            log(f"  {line.strip()}")
    proc.wait()
    return proc.returncode == 0


def check_model(models):
    for m in models:
        name = m.get("name", "") if isinstance(m, dict) else str(m)
        if OLLAMA_MODEL in name:
            return True
    return False


def ensure_environment():
    if not check_ollama_binary():
        if not install_ollama():
            return "Ollama 安装失败，请手动安装:\nbrew install ollama 或从 ollama.com 下载"

    running, models = check_ollama_running()
    if not running:
        if not start_ollama():
            return "Ollama 启动失败，请手动运行:\nollama serve"
        running, models = check_ollama_running()

    if not check_model(models):
        if not pull_model():
            return f"模型下载失败，请手动运行:\nollama pull {OLLAMA_MODEL}"

    return None


def main():
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

    app_state = {"done": False, "error": None, "cfg": None}

    def bg_setup():
        try:
            err = ensure_environment()
            if err:
                app_state["error"] = err
                return

            from config import load_config
            from translator import Translator
            from asr_engine import ASREngine

            cfg = load_config()
            app_state["cfg"] = cfg

            base_url = cfg["ollama_url"].rstrip("/")
            for suffix in ["/v1/chat/completions", "/api/chat"]:
                base_url = base_url.replace(suffix, "")
            cfg["_translator"] = Translator(model=cfg["ollama_model"], base_url=base_url)

            root.after(0, lambda: label.config(text="加载语音识别模型..."))
            root.update_idletasks()

            cfg["_asr"] = ASREngine(
                model_name=cfg["asr_model"],
                chunk_size=cfg["chunk_size"],
                encoder_chunk_look_back=cfg["encoder_chunk_look_back"],
                decoder_chunk_look_back=cfg["decoder_chunk_look_back"],
                punc_model=cfg.get("punc_model", "ct-punc"),
            )
            cfg["_asr"].silence_timeout = cfg.get("silence_timeout", 1.5)
            cfg["_asr"].load_model()

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

        cfg = app_state["cfg"]
        translator = cfg.pop("_translator")
        asr = cfg.pop("_asr")

        from audio_capture import AudioCapture
        from subtitle_ui import SubtitleUI
        from device_selector import DeviceSelector
        from settings_panel import SettingsPanel
        from config import save_config

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

        audio = AudioCapture(sample_rate=cfg["sample_rate"], device_id=device_id)

        root.destroy()

        from main import start_subtitle_app
        start_subtitle_app(cfg, audio, asr, translator, device_id)

    root.after(500, poll_ready)
    root.mainloop()


if __name__ == "__main__":
    main()
