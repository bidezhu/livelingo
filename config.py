import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "sample_rate": 16000,
    "chunk_size": [0, 10, 5],
    "encoder_chunk_look_back": 4,
    "decoder_chunk_look_back": 1,
    "asr_model": "paraformer-zh-streaming",
    "punc_model": "ct-punc",
    "ollama_model": "qwen3.5:9b",
    "ollama_url": "http://localhost:11434",
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
