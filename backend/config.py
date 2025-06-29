import json
import os
import logging

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
    # Maximum log file size in bytes before rotation
    "log_max_bytes": 1_000_000,
    # Number of rotated log files to keep
    "log_backup_count": 3,
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        # Inject any missing keys from the default configuration
        merged = {**DEFAULT_CONFIG, **data}
        if merged != data:
            save_config(merged)
        return merged
    except Exception as exc:
        logging.warning(
            "Failed to load config file %s: %s; using defaults", CONFIG_FILE, exc
        )
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
