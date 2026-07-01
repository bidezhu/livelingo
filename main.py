#!/usr/bin/env python3
import sys
import os
import signal
import queue
import threading
import tkinter as tk

from config import load_config, save_config
from system_audio_capture import CombinedAudioCapture
from live_translate_engine import DualLiveTranslateEngine
from subtitle_ui import SubtitleUI
from device_selector import DeviceSelector
from settings_panel import SettingsPanel


def show_busy_window(parent, title, message):
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry("360x140")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.configure(bg="#f4f7fb")
    try:
        win.transient(parent)
    except tk.TclError:
        pass

    frame = tk.Frame(win, bg="#f4f7fb", padx=20, pady=18)
    frame.pack(fill="both", expand=True)
    tk.Label(
        frame,
        text=title,
        bg="#f4f7fb",
        fg="#102a43",
        font=("Helvetica", 15, "bold"),
    ).pack(anchor="w")
    tk.Label(
        frame,
        text=message,
        bg="#f4f7fb",
        fg="#627d98",
        font=("Helvetica", 12),
        wraplength=310,
        justify="left",
    ).pack(anchor="w", pady=(10, 0))
    win.update_idletasks()
    if parent:
        x = parent.winfo_rootx() + max(20, (parent.winfo_width() - 360) // 2)
        y = parent.winfo_rooty() + max(20, (parent.winfo_height() - 140) // 2)
        win.geometry(f"+{x}+{y}")
    return win


def start_subtitle_app(cfg, audio, asr, device_id, capture_mode="microphone"):
    settings_state = {"window": None}
    device_state = {"busy": False}

    def restart_mic(parent=None, on_done=None):
        nonlocal device_id, capture_mode, audio
        if device_state["busy"]:
            ui.update_status("音频来源窗口已在处理...")
            return

        parent_win = parent or ui.root
        device_state["busy"] = True
        work_queue = queue.Queue()
        loading_win = show_busy_window(parent_win, "音频来源", "正在读取麦克风和系统音频设备...")
        ui.update_status("正在读取音频设备...")

        def finish(success=False):
            device_state["busy"] = False
            if on_done:
                on_done(success)

        def close_window(win):
            if win and win.winfo_exists():
                win.destroy()

        def load_devices():
            devices = CombinedAudioCapture.list_all_devices(timeout=1.5)
            work_queue.put(("devices", devices))

        def poll_devices():
            try:
                kind, payload = work_queue.get_nowait()
            except queue.Empty:
                if loading_win.winfo_exists():
                    ui.root.after(100, poll_devices)
                else:
                    finish(False)
                return

            close_window(loading_win)
            if kind != "devices" or not payload:
                ui.update_status("错误: 未找到可用音频设备")
                finish(False)
                return

            selector = DeviceSelector(payload, current_id=device_id)
            result = selector.show(parent=parent_win)
            if result and len(result) == 3:
                new_id, new_name, new_mode = result
            else:
                new_id, new_name, new_mode = None, None, None

            if new_id is None:
                ui.update_status("已取消切换音频来源")
                finish(False)
                return

            switch_win = show_busy_window(parent_win, "切换音频来源", "正在重启音频流和实时同传引擎...")
            ui.update_status("正在切换音频来源...")

            def switch_device():
                try:
                    old_audio = audio
                    old_audio.stop()
                    asr.stop()
                    new_audio = CombinedAudioCapture(sample_rate=cfg.get("sample_rate", 16000))
                    new_audio.start(device_id=new_id, capture_mode=new_mode)
                    asr.start(new_audio.audio_queue)
                    work_queue.put(("switched", (new_audio, new_id, new_name, new_mode)))
                except Exception as exc:
                    work_queue.put(("switch_error", str(exc)))

            def poll_switch():
                nonlocal device_id, capture_mode, audio
                try:
                    kind, payload = work_queue.get_nowait()
                except queue.Empty:
                    if switch_win.winfo_exists():
                        ui.root.after(100, poll_switch)
                    else:
                        finish(False)
                    return

                close_window(switch_win)
                if kind == "switch_error":
                    ui.update_status(f"错误: 音频切换失败 {payload[:40]}")
                    finish(False)
                    return

                new_audio, selected_id, selected_name, selected_mode = payload
                audio = new_audio
                device_id = selected_id
                capture_mode = selected_mode
                cfg["device_id"] = selected_id
                cfg["device_name"] = selected_name
                cfg["capture_mode"] = selected_mode
                save_config(cfg)

                mode_text = {"microphone": "麦克风", "system": "系统音频", "both": "麦克风+系统音频"}
                ui.update_status(f"已切换: {selected_name} ({mode_text.get(selected_mode, selected_mode)})")
                finish(True)

            threading.Thread(target=switch_device, daemon=True).start()
            ui.root.after(100, poll_switch)

        threading.Thread(target=load_devices, daemon=True).start()
        ui.root.after(100, poll_devices)

    def on_settings():
        existing = settings_state.get("window")
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return
        panel = SettingsPanel(cfg, on_apply=apply_settings, on_device_change=restart_mic)
        settings_state["window"] = panel.show(parent=ui.root)

    def apply_settings(new_cfg):
        restart_keys = {"api_key", "hot_words", "livetranslate_model", "language_mode"}
        needs_engine_restart = any(cfg.get(k) != new_cfg.get(k) for k in restart_keys)
        cfg.update(new_cfg)
        save_config(new_cfg)
        if hasattr(asr, "update_settings"):
            asr.update_settings(new_cfg)
        if needs_engine_restart:
            asr.stop()
            asr.start(audio.audio_queue)
        ui.apply_settings(new_cfg)
        ui.update_status("设置已更新" + ("，同传引擎已重启" if needs_engine_restart else ""))

    ui = SubtitleUI(cfg, on_device_change=restart_mic, on_settings=on_settings)

    # 启动音频捕获
    if isinstance(audio, CombinedAudioCapture):
        audio.start(device_id=device_id, capture_mode=capture_mode)
    else:
        audio.start()

    # 启动翻译引擎
    asr.start(audio.audio_queue)
    mode_text = {"microphone": "麦克风", "system": "系统音频", "both": "麦克风+系统音频"}
    mode_desc = mode_text.get(capture_mode, capture_mode)
    ui.update_status(f"就绪 - 实时同传模式 ({mode_desc})")

    signal.signal(signal.SIGINT, lambda s, f: ui.root.destroy())

    ui.poll_results(asr.result_queue, queue.Queue())
    ui.run()

    audio.stop()
    asr.stop()


def main():
    cfg = load_config()

    print("=" * 50)
    print("  LiveLingo - 中英双语实时字幕")
    print("=" * 50)

    api_key = cfg.get("api_key", "")
    capture_mode = cfg.get("capture_mode", "microphone")

    print("[..] 初始化实时同传引擎...")
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
    print("[OK] 实时同传引擎就绪")

    # 获取所有可用设备
    all_devices = CombinedAudioCapture.list_all_devices()
    device_id = None

    if cfg.get("device_id") is not None:
        for d in all_devices:
            if d["id"] == cfg["device_id"]:
                device_id = cfg["device_id"]
                break

    if device_id is None:
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
                    save_config(cfg)
                    break
        if device_id is None and all_devices:
            device_id = all_devices[0]["id"]

    print(f"[INFO] 使用设备: {device_id}, 捕获模式: {capture_mode}")

    audio = CombinedAudioCapture(sample_rate=cfg.get("sample_rate", 16000))
    start_subtitle_app(cfg, audio, asr, device_id, capture_mode)


if __name__ == "__main__":
    main()
