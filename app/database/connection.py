import sqlite3

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.config import SCHEMA_VERSION, db_path
from app.database.models import Base

def engine_for(path=None):
    path = path or db_path()
    engine = create_engine(
        f"sqlite:///{path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()
    return engine

engine = engine_for()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

def close_all_connections():
    """Dispose all pooled connections (required on Windows before file replace)."""
    engine.dispose()

def reset_engine_for_path():
    """Re-bind the module-level engine/SessionLocal after a DB file replace.

    The file path is unchanged, so a fresh engine reopens the new file.
    """
    global engine, SessionLocal
    engine = engine_for()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

def reset_engine_for_path_for_tests(path):
    """Rebind the engine to an explicit path (test isolation only)."""
    global engine, SessionLocal
    engine = engine_for(path)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

def initialize_database():
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT OR IGNORE INTO app_meta(key, value) VALUES ('schema_version', '1')"
        ))
        conn.execute(text(
            "INSERT OR IGNORE INTO app_meta(key, value) VALUES ('app_version', '1.1.0')"
        ))

def validate_database(path):
    required = {"users", "categories", "products", "price_history", "stock_movements", "app_meta"}
    con = None
    try:
        con = sqlite3.connect(path)
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required.issubset(tables):
            return False, "قاعدة البيانات لا تحتوي على الجداول المطلوبة."
        row = con.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone()
        if not row or int(row[0]) > SCHEMA_VERSION:
            return False, "إصدار قاعدة البيانات أحدث من إصدار البرنامج."
        result = con.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            return False, "فشل فحص سلامة SQLite."
        return True, "قاعدة البيانات صالحة."
    except Exception as exc:
        return False, f"ملف قاعدة البيانات غير صالح: {exc}"
    finally:
        if con is not None:
            con.close()
