from pathlib import Path
from datetime import datetime
import shutil, sqlite3
from app.config import db_path, backups_dir
from app.database.connection import validate_database

def backup_to(destination=None):
    src = db_path()
    if destination is None:
        destination = backups_dir() / f"backup_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(src)
    try:
        out = sqlite3.connect(destination)
        with out:
            con.backup(out)
        out.close()
    finally:
        con.close()
    return destination

def restore_from(source):
    source = Path(source)
    ok, msg = validate_database(source)
    if not ok:
        raise ValueError(msg)
    backup_to()
    target = db_path()
    tmp = target.with_suffix(".restore.tmp")
    shutil.copy2(source, tmp)
    tmp.replace(target)
    return target
