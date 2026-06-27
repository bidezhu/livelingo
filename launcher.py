#!/usr/bin/env python3
import sys
import os
import subprocess
import shutil
import tkinter as tk
from tkinter import messagebox


def check_ollama():
    ollama = shutil.which("ollama")
    if not ollama:
        return False, "未安装 Ollama"
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "3", "http://localhost:11434/api/tags"],
                           capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            return False, "Ollama 服务未运行"
        import json
        data = json.loads(r.stdout)
        models = [m["name"] for m in data.get("models", [])]
        if not any("qwen3.5" in m for m in models):
            return False, f"翻译模型未下载，当前模型: {models}"
    except Exception as e:
        return False, f"检查 Ollama 失败: {e}"
    return True, "OK"


def show_error(title, msg):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, msg)
    root.destroy()


def show_setup_guide():
    root = tk.Tk()
    root.withdraw()
    msg = (
        "首次使用需要安装 Ollama 和翻译模型：\n\n"
        "1. 安装 Ollama:\n"
        "   打开终端运行: brew install ollama\n"
        "   或从 https://ollama.com 下载安装\n\n"
        "2. 启动 Ollama:\n"
        "   ollama serve\n\n"
        "3. 下载翻译模型:\n"
        "   ollama pull qwen3.5:9b\n\n"
        "完成后重新启动本应用。"
    )
    messagebox.showinfo("环境配置指南", msg)
    root.destroy()


def start_ollama():
    try:
        subprocess.Popen(["ollama", "serve"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time
        time.sleep(3)
    except Exception:
        pass


def main():
    ok, reason = check_ollama()
    if not ok:
        if "未安装" in reason:
            show_setup_guide()
            sys.exit(1)
        else:
            start_ollama()
            ok, reason = check_ollama()
            if not ok:
                show_error("Ollama 错误", f"{reason}\n\n请先在终端运行:\n  ollama serve\n  ollama pull qwen3.5:9b")
                sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = script_dir

    sys.path.insert(0, base_dir)
    from main import main as app_main
    app_main()


if __name__ == "__main__":
    main()
