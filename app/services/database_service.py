import sqlite3
from pathlib import Path
from app.database.connection import validate_database
from app.services.backup_service import _replace_database

def inspect_database(path):
    ok, msg = validate_database(path)
    if not ok:
        raise ValueError(msg)
    con = sqlite3.connect(path)
    try:
        products = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        categories = con.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    finally:
        con.close()
    return {"products": products, "categories": categories}

def import_database(source):
    source = Path(source)
    info = inspect_database(source)
    _replace_database(source)
    return info
