import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "bot.log")

# Max 5 MB per file, keep 3 backups
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3

FORMATTER = logging.Formatter(
    "[%(asctime)s] %(levelname)-8s %(name)-20s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _setup_root_logger() -> None:
    """Configure the root logger once at import time."""
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers on reload
    if root.handlers:
        return

    # --- Rotating file handler ---
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(FORMATTER)
    root.addHandler(file_handler)

    # --- Console handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(FORMATTER)
    root.addHandler(console_handler)


# Run setup on first import
_setup_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger. Usage: ``logger = get_logger(__name__)``."""
    return logging.getLogger(name)
