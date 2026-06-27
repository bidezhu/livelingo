import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "mimo_api_key": "",
    "mimo_base_url": "https://api.xiaomimimo.com/v1",
    "mimo_asr_model": "mimo-v2.5-asr",
    "mimo_chat_model": "mimo-v2.5",
    "sample_rate": 16000,
    "font_size_cn": 28,
    "font_size_en": 20,
    "max_subtitle_lines": 4,
    "window_height": 220,
    "bg_color": "#1a1a1a",
    "text_color_cn": "#FFFFFF",
    "text_color_en": "#BBBBBB",
    "text_color_partial": "#888888",
    "device_id": None,
    "device_name": None,
    "silence_timeout": 1.5,
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg.update(saved)
        except Exception:
            pass
    return cfg


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
