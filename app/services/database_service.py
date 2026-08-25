from pathlib import Path
import shutil
import sqlite3
from datetime import datetime
from app.config import db_path
from app.database.connection import validate_database
from app.services.backup_service import backup_to
from app.database.connection import engine, SessionLocal, initialize_database

def inspect_database(path):
    ok, msg = validate_database(path)
    if not ok:
        raise ValueError(msg)
    import sqlite3
    con = sqlite3.connect(path)
    products = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    categories = con.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    con.close()
    return {"products":products, "categories":categories}

def import_database(source):
    source = Path(source)
    info = inspect_database(source)
    backup_to()
    target = db_path()
    tmp = target.with_suffix(".import.tmp")
    src_con = sqlite3.connect(source)
    dst_con = sqlite3.connect(tmp)
    try:
        with dst_con:
            src_con.backup(dst_con)
    finally:
        src_con.close(); dst_con.close()
    tmp.replace(target)
    return info
