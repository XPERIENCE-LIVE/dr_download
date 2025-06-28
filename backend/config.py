import json
import os

# Config file stored alongside this module
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# Migrate config from old location if it exists in the repository root
LEGACY_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config.json"
)
if not os.path.exists(CONFIG_FILE) and os.path.exists(LEGACY_CONFIG):
    os.replace(LEGACY_CONFIG, CONFIG_FILE)
DEFAULT_CONFIG = {
    "theme": "dark",
    "default_format": "video",
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
