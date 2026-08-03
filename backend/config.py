import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_PATH = DATA_DIR / "app_settings.json"
STYLE_PROFILE_PATH = DATA_DIR / "style_profile.json"


def load_settings() -> dict:
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def save_settings(settings: dict):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


def load_style_profile() -> dict:
    with open(STYLE_PROFILE_PATH) as f:
        return json.load(f)


def save_style_profile(profile: dict):
    with open(STYLE_PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)


def get_imessage_db_path() -> Path:
    settings = load_settings()
    raw = settings.get("imessage_db_path", "~/Library/Messages/chat.db")
    return Path(os.path.expanduser(raw))


def get_export_folder() -> Path:
    settings = load_settings()
    raw = settings.get("export_folder_path", "./backend/data/exports")
    p = Path(raw)
    if not p.is_absolute():
        p = BASE_DIR / raw.lstrip("./backend/").lstrip("./")
        p = DATA_DIR / "exports"
    p.mkdir(parents=True, exist_ok=True)
    return p
