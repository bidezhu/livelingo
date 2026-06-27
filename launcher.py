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
    log("正在安装 Ollama...")
    try:
        r = subprocess.run(
            ["/bin/bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
            capture_output=True, text=True, timeout=300
        )
        if r.returncode == 0:
            log("Ollama 安装完成")
            return True
        log(f"Ollama 安装失败: {r.stderr[:200]}")
        return False
    except Exception as e:
        log(f"Ollama 安装异常: {e}")
        return False


def start_ollama():
    log("启动 Ollama 服务...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(15):
        time.sleep(1)
        running, _ = check_ollama_running()
        if running:
            log("Ollama 服务已启动")
            return True
    log("Ollama 启动超时")
    return False


def pull_model():
    log(f"下载翻译模型 {OLLAMA_MODEL} (约6.6GB)...")
    proc = subprocess.Popen(
        ["ollama", "pull", OLLAMA_MODEL],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in proc.stdout:
        line = line.strip()
        if line:
            log(f"  {line}")
    proc.wait()
    if proc.returncode == 0:
        log("翻译模型下载完成")
        return True
    log("翻译模型下载失败")
    return False


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
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("LiveLingo", msg)
        root.destroy()
    except Exception:
        log(msg)


def setup():
    if not check_ollama_binary():
        ok = install_ollama()
        if not ok:
            show_error("Ollama 安装失败。\n\n请手动安装:\n  brew install ollama\n或从 https://ollama.com 下载")
            return False

    running, models = check_ollama_running()
    if not running:
        ok = start_ollama()
        if not ok:
            show_error("Ollama 启动失败。\n\n请手动运行:\n  ollama serve")
            return False
        running, models = check_ollama_running()

    if not check_model(models):
        ok = pull_model()
        if not ok:
            show_error(f"模型下载失败。\n\n请手动运行:\n  ollama pull {OLLAMA_MODEL}")
            return False

    return True


def main():
    if not setup():
        sys.exit(1)

    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    sys.path.insert(0, base_dir)
    from main import main as app_main
    app_main()


if __name__ == "__main__":
    main()
