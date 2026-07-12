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

DEFAULT_CONFIG = {
    "vault_dir": str(Path.home() / "Documents" / "obsidian_plugin" / "temp_vault"),
    "repositories": []
}

def load_config():
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return DEFAULT_CONFIG.copy()

def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def get_vault_dir() -> Path:
    config = load_config()
    return Path(config.get("vault_dir", DEFAULT_CONFIG["vault_dir"]))

def get_analytics_dir() -> Path:
    d = DATA_DIR / "analytics"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_activities_dir() -> Path:
    d = DATA_DIR / "activities"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_github_dir() -> Path:
    d = DATA_DIR / "github"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_command_logs_dir() -> Path:
    return Path.home() / ".command_logs"
