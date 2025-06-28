import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                os.path.join("logs", "backend.log"),
                maxBytes=1_000_000,
                backupCount=3,
            ),
            logging.StreamHandler(),
        ],
    )
