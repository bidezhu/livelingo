#!/usr/bin/env python3
import sys
import os
import signal

from config import load_config, save_config
from audio_capture import AudioCapture
from asr_engine import ASREngine
from translator import Translator
from subtitle_ui import SubtitleUI
from device_selector import DeviceSelector
from settings_panel import SettingsPanel


def start_subtitle_app(cfg, audio, asr, translator, device_id):
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
        print(f"[ASR最终] {text[:50]}", flush=True)
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

    audio.start()
    asr.start(audio.audio_queue)
    translator.start()

    ui.update_status("就绪 - 请开始说话")

    signal.signal(signal.SIGINT, lambda s, f: ui.root.destroy())

    ui.poll_results(asr.result_queue, translator.result_queue)
    ui.run()

    audio.stop()
    asr.stop()
    translator.stop()


def main():
    cfg = load_config()

    print("=" * 50)
    print("  LiveLingo - 本地离线中英双语实时字幕")
    print("=" * 50)

    api_key = cfg.get("mimo_api_key", "")
    base_url = cfg.get("mimo_base_url", "https://api.xiaomimimo.com/v1")

    print("[..] 初始化 MiMo ASR...")
    asr = ASREngine(
        api_key=api_key,
        base_url=base_url,
        model=cfg.get("mimo_asr_model", "mimo-v2.5-asr"),
        sample_rate=cfg.get("sample_rate", 16000),
    )
    asr.silence_timeout = cfg.get("silence_timeout", 1.5)
    asr.load_model()
    print("[OK] ASR 就绪")

    print("[..] 初始化 MiMo 翻译...")
    translator = Translator(
        api_key=api_key,
        base_url=base_url,
        model=cfg.get("mimo_chat_model", "mimo-v2.5"),
    )
    translator.load()
    print("[OK] 翻译就绪")

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
    start_subtitle_app(cfg, audio, asr, translator, device_id)


if __name__ == "__main__":
    main()
