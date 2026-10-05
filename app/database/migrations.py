from sqlalchemy import text
from app.config import SCHEMA_VERSION
from app.database import connection as dbconn

CURRENT_SCHEMA = SCHEMA_VERSION

def migrate():
    with dbconn.engine.begin() as conn:
        row = conn.execute(text(
            "SELECT value FROM app_meta WHERE key='schema_version'"
        )).fetchone()
        if not row:
            return
        version = int(row[0])
        # Future migrations should be added here as explicit version steps.
        if version > CURRENT_SCHEMA:
            raise RuntimeError("قاعدة البيانات أحدث من البرنامج.")
        if version < 2:
            # v1 -> v2: sales table for daily sales recording. create_all in
            # initialize_database normally creates it; the IF NOT EXISTS keeps
            # direct migrate() calls safe too.
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER NOT NULL PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
                    quantity NUMERIC(12, 3) NOT NULL,
                    unit_price NUMERIC(12, 2) NOT NULL,
                    total NUMERIC(12, 2) NOT NULL,
                    sold_at DATETIME NOT NULL,
                    sold_by INTEGER REFERENCES users (id) ON DELETE SET NULL
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_sales_sold_at ON sales (sold_at)"
            ))
            conn.execute(text(
                "UPDATE app_meta SET value = '2' WHERE key = 'schema_version'"
            ))
