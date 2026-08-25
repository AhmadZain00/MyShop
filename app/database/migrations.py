from sqlalchemy import text
from app.database.connection import engine

CURRENT_SCHEMA = 1

def migrate():
    with engine.begin() as conn:
        row = conn.execute(text(
            "SELECT value FROM app_meta WHERE key='schema_version'"
        )).fetchone()
        if not row:
            return
        version = int(row[0])
        # Future migrations should be added here as explicit version steps.
        if version > CURRENT_SCHEMA:
            raise RuntimeError("قاعدة البيانات أحدث من البرنامج.")
