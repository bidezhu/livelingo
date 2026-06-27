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


def get_device_id(cfg):
    devices = AudioCapture.list_input_devices()
    if not devices:
        print("[!] 未找到音频输入设备，使用系统默认")
        return None

    saved_id = cfg.get("device_id")
    if saved_id is not None and any(d["id"] == saved_id for d in devices):
        print(f"[OK] 使用已保存设备: {cfg.get('device_name', saved_id)}")
        return saved_id

    for d in devices:
        if "麦克风" in d["name"] or "microphone" in d["name"].lower():
            print(f"[OK] 自动选择: {d['name']}")
            return d["id"]

    print(f"[OK] 使用: {devices[0]['name']}")
    return devices[0]["id"]


def main():
    cfg = load_config()

    print("=" * 50)
    print("  LiveLingo - 本地离线中英双语实时字幕")
    print("=" * 50)

    translator = check_ollama(cfg)
    device_id = get_device_id(cfg)

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

    audio = AudioCapture(sample_rate=cfg["sample_rate"], device_id=device_id)

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
    print("[OK] 系统就绪！")
    print("     Cmd+Q 退出 | Cmd+↑/↓ 移动 | Cmd+H 隐藏 | Cmd+, 设置")

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
