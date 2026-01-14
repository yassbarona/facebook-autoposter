"""
Logging utilities for Facebook Auto-Poster
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import get_config


def setup_logger(name: str = "fbposter") -> logging.Logger:
    """Set up application logger"""
    config = get_config()

    logger = logging.getLogger(name)
    log_level = config.get('logging.level', 'INFO')
    logger.setLevel(getattr(logging, log_level))

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler
    log_file = Path(config.get('logging.file', 'data/logs/fbposter.log'))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.get('logging.max_bytes', 10485760),
        backupCount=config.get('logging.backup_count', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger instance"""
    if name:
        return logging.getLogger(f"fbposter.{name}")
    return logging.getLogger("fbposter")
