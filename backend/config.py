import json
import os
import shutil

# Packaged apps write to Electron's userData; development keeps compatibility.
_CONFIGURED_DATA_DIR = os.getenv("DR_DOWNLOAD_DATA_DIR")
CONFIG_FILE = os.path.join(
    _CONFIGURED_DATA_DIR or os.path.dirname(__file__), "config.json"
)

# Migrate config from old location if it exists in the repository root
LEGACY_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config.json"
)
if _CONFIGURED_DATA_DIR:
    os.makedirs(_CONFIGURED_DATA_DIR, exist_ok=True)
    packaged_legacy = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(CONFIG_FILE) and os.path.exists(packaged_legacy):
        shutil.copy2(packaged_legacy, CONFIG_FILE)
elif not os.path.exists(CONFIG_FILE) and os.path.exists(LEGACY_CONFIG):
    os.replace(LEGACY_CONFIG, CONFIG_FILE)
DEFAULT_CONFIG = {
    "theme": "dark",
    "default_format": "video",
    "language": "es",
    "cookie_source": "edge",
    "cookie_consent": False,
    "notifications": True,
    "output_dir": "",
    "auto_update_engine": True,
    "auto_update_app": True,
    # Number of worker threads for downloads
    "worker_threads": 1,
    # Maximum log file size in bytes before rotation
    "log_max_bytes": 1_000_000,
    # Number of rotated log files to keep
    "log_backup_count": 3,
}


class ConfigError(RuntimeError):
    """The persisted configuration cannot be used safely."""


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("the root value must be an object")
        # Inject any missing keys from the default configuration
        merged = {**DEFAULT_CONFIG, **data}
        if merged != data:
            save_config(merged)
        return merged
    except Exception as exc:
        raise ConfigError(
            f"configuration file is invalid: {CONFIG_FILE}"
        ) from exc


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
