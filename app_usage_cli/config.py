import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    base_dir = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    CONFIG_DIR = base_dir / "app_usage"
    DATA_DIR = base_dir / "app_usage"
else:
    CONFIG_DIR = Path.home() / ".config" / "app_usage"
    DATA_DIR = Path.home() / ".local" / "share" / "app_usage"

CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")  # write-then-rename: the GUI and the daemon both save this file
    tmp.write_text(json.dumps(cfg, indent=2))
    try:
        tmp.chmod(0o600)  # holds the device token
    except OSError:
        pass
    os.replace(tmp, CONFIG_FILE)


def get_analytics_dir() -> Path:
    d = DATA_DIR / "analytics"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_activities_dir() -> Path:
    d = DATA_DIR / "activities"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_command_logs_dir() -> Path:
    return DATA_DIR / ".command_logs"
