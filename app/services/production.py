
from pathlib import Path
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

APP_NAME = "MyShop"

def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]

def data_root() -> Path:
    portable = app_root() / "portable.flag"
    if portable.exists():
        return app_root() / "data"
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / "AppData" / "Local"
    return base / APP_NAME

def logs_root() -> Path:
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
    root = app_root()
    data = data_root()
    data.mkdir(parents=True, exist_ok=True)
    return {
        "app_root": str(root),
        "data_root": str(data),
        "portable": (root / "portable.flag").exists(),
        "writable_data": os.access(data, os.W_OK),
        "logs_root": str(logs_root()),
    }
