import json
import os
from dataclasses import dataclass, field, asdict

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".transpic")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class AppConfig:
    api_endpoint: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    target_language: str = "中文"
    hotkey: str = "alt+shift+t"
    window_x: int = 100
    window_y: int = 100


def load_config() -> AppConfig:
    if not os.path.exists(CONFIG_FILE):
        return AppConfig()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AppConfig(**{k: v for k, v in data.items() if k in AppConfig.__dataclass_fields__})
    except (json.JSONDecodeError, IOError):
        return AppConfig()


def save_config(config: AppConfig):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2, ensure_ascii=False)
