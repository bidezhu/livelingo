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


def show_error(msg):
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("LiveLingo", msg)
        r.destroy()
    except Exception:
        log(msg)


def setup():
    if not check_ollama_binary():
        if not install_ollama():
            show_error("Ollama 安装失败\n\n请手动安装:\n  brew install ollama\n或从 https://ollama.com 下载")
            return False

    running, models = check_ollama_running()
    if not running:
        if not start_ollama():
            show_error("Ollama 启动失败\n\n请手动运行: ollama serve")
            return False
        running, models = check_ollama_running()

    if not check_model(models):
        if not pull_model():
            show_error(f"模型下载失败\n\n请手动运行:\n  ollama pull {OLLAMA_MODEL}")
            return False

    return True


def show_loading(callback):
    import tkinter as tk

    root = tk.Tk()
    root.title("LiveLingo")
    root.geometry("360x100")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    label = tk.Label(root, text="正在启动，请稍候...", font=("Helvetica", 14), pady=30)
    label.pack(fill="both", expand=True)

    def run_setup():
        ok = setup()
        if ok:
            root.after(0, lambda: label.config(text="加载模型中..."))
            root.after(100, lambda: callback(root))
        else:
            root.after(0, root.destroy)

    threading.Thread(target=run_setup, daemon=True).start()
    root.mainloop()


def launch_app(loading_root):
    loading_root.destroy()

    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    sys.path.insert(0, base_dir)
    from main import main as app_main
    app_main()


def main():
    show_loading(launch_app)


if __name__ == "__main__":
    main()
