import logging
import os
from pathlib import Path

# Ensure logs directory exists
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "system.log"

def get_logger(name: str):
    """
    Returns a configured logger instance.
    Writes to logs/system.log and also to Console (Standard Output).
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent adding multiple handlers if get_logger is called repeatedly
    if logger.hasHandlers():
        return logger

    # 1. File Handler (The Record)
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger
