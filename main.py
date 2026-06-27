#!/usr/bin/env python3
import sys
import os
import signal
import threading
import queue

from config import load_config, save_config
from audio_capture import AudioCapture
from asr_engine import ASREngine
from translator import Translator
from subtitle_ui import SubtitleUI
from device_selector import DeviceSelector
from settings_panel import SettingsPanel


def check_ollama(cfg):
    base_url = cfg["ollama_url"].rstrip("/")
    if "/v1/chat/completions" in base_url:
        base_url = base_url.replace("/v1/chat/completions", "")
    if "/api/chat" in base_url:
        base_url = base_url.replace("/api/chat", "")
    t = Translator(model=cfg["ollama_model"], base_url=base_url)
    if not t.check_available():
        print("错误: Ollama 服务未运行或模型未拉取。")
        print("请先运行: ollama serve &")
        print(f"然后运行: ollama pull {cfg['ollama_model']}")
        sys.exit(1)
    print(f"[OK] Ollama 模型 {cfg['ollama_model']} 就绪")
    return t


def select_device(cfg):
    devices = AudioCapture.list_input_devices()
    if not devices:
        print("错误: 未找到音频输入设备")
        sys.exit(1)

    if cfg.get("device_id") is not None:
        found = any(d["id"] == cfg["device_id"] for d in devices)
        if found:
            print(f"[OK] 使用已保存设备: {cfg.get('device_name', cfg['device_id'])}")
            return cfg["device_id"]

    selector = DeviceSelector(devices, current_id=cfg.get("device_id"))
    device_id, device_name = selector.show()

    if device_id is None:
        if len(devices) == 1:
            device_id = devices[0]["id"]
            device_name = devices[0]["name"]
        else:
            print("未选择设备，使用系统默认")
            return None

    cfg["device_id"] = device_id
    cfg["device_name"] = device_name
    save_config(cfg)
    print(f"[OK] 选择设备: {device_name}")
    return device_id


def main():
    cfg = load_config()

    print("=" * 50)
    print("  Live Subtitle - 本地离线中英双语实时字幕")
    print("=" * 50)

    translator = check_ollama(cfg)
    device_id = select_device(cfg)

    print("[..] 加载 ASR 模型 (首次可能需要下载)...")
    asr = ASREngine(
        model_name=cfg["asr_model"],
        chunk_size=cfg["chunk_size"],
        encoder_chunk_look_back=cfg["encoder_chunk_look_back"],
        decoder_chunk_look_back=cfg["decoder_chunk_look_back"],
        punc_model=cfg.get("punc_model", "ct-punc"),
    )
    asr.silence_timeout = cfg.get("silence_timeout", 1.5)
    asr.load_model()
    print("[OK] ASR 模型加载完成")

    audio = AudioCapture(
        sample_rate=cfg["sample_rate"],
        device_id=device_id,
    )

    def restart_mic():
        nonlocal device_id
        audio.stop()
        devices = AudioCapture.list_input_devices()
        selector = DeviceSelector(devices, current_id=device_id)
        new_id, new_name = selector.show(parent=ui.root)
        if new_id is not None:
            device_id = new_id
            cfg["device_id"] = new_id
            cfg["device_name"] = new_name
            save_config(cfg)
            audio.device_id = new_id
            ui.update_status(f"已切换: {new_name}")
        audio.start()
        asr.reset_cache()

    def on_asr_final(text):
        translator.submit(text)

    def on_settings():
        panel = SettingsPanel(cfg, on_apply=apply_settings)
        panel.show(parent=ui.root)

    def apply_settings(new_cfg):
        save_config(new_cfg)
        asr.silence_timeout = new_cfg.get("silence_timeout", 1.5)
        ui.apply_settings(new_cfg)
        ui.update_status("设置已更新")

    ui = SubtitleUI(cfg, on_device_change=restart_mic,
                    on_asr_final=on_asr_final, on_settings=on_settings)

    print("[..] 启动音频采集...")
    audio.start()
    asr.start(audio.audio_queue)
    translator.start()
    print("[OK] 系统就绪，开始说话吧！")
    print("     Cmd+Q 退出 | Cmd+↑/↓ 调整位置 | Cmd+H 隐藏 | Cmd+, 设置")

    ui.update_status("就绪 - 请开始说话")

    signal.signal(signal.SIGINT, lambda s, f: ui.root.destroy())

    ui.poll_results(asr.result_queue, translator.result_queue)
    ui.run()

    print("\n正在停止...")
    audio.stop()
    asr.stop()
    translator.stop()
    print("已退出。")


if __name__ == "__main__":
    main()
