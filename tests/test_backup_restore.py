"""Backup/restore round-trip tests.

The restore path replaces the live SQLite file while the app engine holds
pooled connections — on Windows this used to fail with WinError 5
(Access denied). These tests pin that regression.
"""
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text

from app.database import connection as dbconn
from app.database.models import Base, Product
from app.services import backup_service
from app.config import backups_dir as real_backups_dir
from app.config import db_path as real_db_path


@pytest.fixture()
def temp_db(tmp_path, isolated_database):
    """Point the whole app engine machinery at a temporary database file."""
    db_file = tmp_path / "shop.db"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(dbconn, "db_path", lambda: db_file)
    monkeypatch.setattr("app.services.backup_service.backups_dir", lambda: tmp_path / "backups")

    dbconn.reset_engine_for_path_for_tests(db_file)
    Base.metadata.create_all(dbconn.engine)
    with dbconn.engine.begin() as conn:
        conn.execute(text(
            "INSERT OR IGNORE INTO app_meta(key, value) VALUES ('schema_version', '1')"
        ))

    yield db_file

    dbconn.engine.dispose()
    monkeypatch.undo()
    # Rebind to the session-isolated test database, never the real one.
    dbconn.reset_engine_for_path_for_tests(isolated_database)


def _add_product(name, barcode):
    with dbconn.SessionLocal.begin() as s:
        s.add(Product(name=name, barcode=barcode,
                      sale_price=Decimal("10"), quantity=1))


def _product_count():
    with dbconn.SessionLocal() as s:
        return s.query(Product).count()


def test_restore_replaces_live_database(temp_db, tmp_path):
    _add_product("A", "111")
    assert _product_count() == 1

    backup_file = tmp_path / "backup.db"
    backup_service.backup_to(backup_file)

    # Modify the live database after the backup was taken.
    _add_product("B", "222")
    assert _product_count() == 2

    # Regression: this used to raise WinError 5 on Windows because the
    # engine still held an open connection to the database file.
    backup_service.restore_from(backup_file)

    # The restored state is visible through the re-created engine.
    assert _product_count() == 1
    with dbconn.SessionLocal() as s:
        p = s.query(Product).one()
        assert p.name == "A"
        assert p.barcode == "111"


def test_restore_rejects_invalid_file(temp_db, tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"not a database")
    with pytest.raises(ValueError):
        backup_service.restore_from(bad)


def test_import_database_reports_counts(temp_db, tmp_path):
    from app.services.database_service import inspect_database, import_database

    _add_product("A", "111")
    source = tmp_path / "other.db"
    backup_service.backup_to(source)

    _add_product("B", "222")
    info = inspect_database(source)
    assert info == {"products": 1, "categories": 0}

    import_database(source)
    assert _product_count() == 1
