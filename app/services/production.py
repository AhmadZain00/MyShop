import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config import APP_NAME, data_root, base_dir

def logs_root():
    p = data_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p

def configure_logging() -> logging.Logger:
    logger = logging.getLogger(APP_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        logs_root() / "myshop.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(handler)
    return logger

def production_checks():
    """Runtime diagnostics for scripts/validate_production.py and support."""
    root = base_dir()
    data = data_root()
    data.mkdir(parents=True, exist_ok=True)
    return {
        "app_root": str(root),
        "data_root": str(data),
        "portable": (root / "portable.flag").exists(),
        "writable_data": os.access(data, os.W_OK),
        "logs_root": str(logs_root()),
    }
