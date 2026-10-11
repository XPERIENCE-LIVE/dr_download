import logging
from logging.handlers import RotatingFileHandler
import os
import re
from .config import load_config


def redact_sensitive_text(value: str) -> str:
    value = re.sub(r"https?://[^\s]+", "[URL]", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s]+(?:[\\/][^\s]*)?",
        "[PRIVATE_PATH]",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"\b(token|cookie|authorization)\s*[:=]\s*[^\s]+",
        r"\1=[REDACTED]",
        value,
        flags=re.IGNORECASE,
    )


class RedactingFormatter(logging.Formatter):
    def format(self, record):
        return redact_sensitive_text(super().format(record))


def setup_logging():
    # Initialize basic logging early so warnings during configuration loading
    # are captured. It will be reconfigured with handlers once the config is
    # available.
    logging.basicConfig(level=logging.INFO)

    data_dir = os.getenv("DR_DOWNLOAD_DATA_DIR") or os.path.dirname(__file__)
    log_dir = os.path.join(data_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    cfg = load_config()
    max_bytes = cfg.get("log_max_bytes", 1_000_000)
    backup_count = cfg.get("log_backup_count", 3)

    formatter = RedactingFormatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "backend.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    stream_handler = logging.StreamHandler()
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler],
        force=True,
    )
