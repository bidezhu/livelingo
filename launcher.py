#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil
import time
import json
import urllib.request
import tkinter as tk
from tkinter import messagebox


OLLAMA_MODEL = "qwen3.5:9b"


def show_progress(msg):
    root = tk.Tk()
    root.title("LiveLingo")
    root.geometry("400x120")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    label = tk.Label(root, text=msg, font=("Helvetica", 13), wraplength=380, pady=20)
    label.pack(fill="both", expand=True)
    root.update()
    return root, label


def check_ollama_binary():
    return shutil.which("ollama") is not None


def check_ollama_running():
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "3", "http://localhost:11434/api/tags"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            return True, data.get("models", [])
    except Exception:
        pass
    return False, []


def install_ollama():
    root, label = show_progress("正在安装 Ollama，请稍候...\n\n首次安装可能需要几分钟")
    root.update()

    try:
        r = subprocess.run(
            ["/bin/bash", "-c",
             'curl -fsSL https://ollama.com/install.sh | sh'],
            capture_output=True, text=True, timeout=300
        )
        root.destroy()
        if r.returncode == 0:
            return True
        else:
            root2, _ = show_progress(f"Ollama 安装失败:\n{r.stderr[:200]}")
            root2.after(5000, root2.destroy)
            root2.mainloop()
            return False
    except Exception as e:
        root.destroy()
        root2, _ = show_progress(f"Ollama 安装异常:\n{str(e)[:200]}")
        root2.after(5000, root2.destroy)
        root2.mainloop()
        return False


def start_ollama():
    subprocess.Popen(["ollama", "serve"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(10):
        time.sleep(1)
        running, _ = check_ollama_running()
        if running:
            return True
    return False


def pull_model():
    root, label = show_progress(f"正在下载翻译模型 {OLLAMA_MODEL}...\n\n约 6.6GB，首次需要几分钟")
    root.update()

    proc = subprocess.Popen(
        ["ollama", "pull", OLLAMA_MODEL],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    for line in proc.stdout:
        line = line.strip()
        if line:
            label.config(text=f"正在下载翻译模型 {OLLAMA_MODEL}...\n\n{line}")
            root.update()

    proc.wait()
    root.destroy()
    return proc.returncode == 0


def check_model(models):
    for m in models:
        name = m.get("name", "") if isinstance(m, dict) else str(m)
        if OLLAMA_MODEL in name:
            return True
    return False


def setup_and_launch():
    if not check_ollama_binary():
        root, label = show_progress("首次使用，正在自动安装 Ollama...\n\n可能需要几分钟，请耐心等待")
        root.update()
        ok = install_ollama()
        root.destroy()
        if not ok:
            sys.exit(1)

    running, models = check_ollama_running()
    if not running:
        root, label = show_progress("正在启动 Ollama 服务...")
        root.update()
        ok = start_ollama()
        root.destroy()
        if not ok:
            root2, _ = show_progress("Ollama 启动失败，请手动运行:\n  ollama serve")
            root2.after(5000, root2.destroy)
            root2.mainloop()
            sys.exit(1)
        running, models = check_ollama_running()

    if not check_model(models):
        ok = pull_model()
        if not ok:
            root, _ = show_progress("模型下载失败，请手动运行:\n  ollama pull " + OLLAMA_MODEL)
            root.after(5000, root.destroy)
            root.mainloop()
            sys.exit(1)


def main():
    setup_and_launch()

    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    sys.path.insert(0, base_dir)
    from main import main as app_main
    app_main()


if __name__ == "__main__":
    main()
