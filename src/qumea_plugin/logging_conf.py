import logging
import os
from logging.handlers import RotatingFileHandler
from .config import get_settings

def setup_logging():
    settings = get_settings()

    log_dir = settings.log_dir
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, settings.log_file)

    logger = logging.getLogger()
    logger.setLevel(settings.log_level.upper())

    # Verhindert doppelte Handler
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # File Rotation
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setFormatter(formatter)

    # Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)