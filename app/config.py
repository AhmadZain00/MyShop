from pathlib import Path
import sys
import os

APP_NAME = "MyShop"
APP_VERSION = "1.1.0"
SCHEMA_VERSION = 1

def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]

def data_root() -> Path:
    portable = base_dir() / "portable.flag"
    if portable.exists():
        return base_dir()
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME

def ensure_dirs():
    root = data_root()
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "backups").mkdir(parents=True, exist_ok=True)
    (root / "exports").mkdir(parents=True, exist_ok=True)
    return root

def db_path() -> Path:
    return ensure_dirs() / "data" / "shop.db"

def backups_dir() -> Path:
    return ensure_dirs() / "backups"
