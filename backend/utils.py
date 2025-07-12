import logging
from logging.handlers import RotatingFileHandler
import os
from .config import load_config


def setup_logging():
    # Initialize basic logging early so warnings during configuration loading
    # are captured. It will be reconfigured with handlers once the config is
    # available.
    logging.basicConfig(level=logging.INFO)

    os.makedirs("logs", exist_ok=True)
    cfg = load_config()
    max_bytes = cfg.get("log_max_bytes", 1_000_000)
    backup_count = cfg.get("log_backup_count", 3)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                os.path.join("logs", "backend.log"),
                maxBytes=max_bytes,
                backupCount=backup_count,
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )
