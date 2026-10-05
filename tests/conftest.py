"""Isolate every test from the real user database.

Without this fixture, importing app.database.connection creates the module-level
engine bound to the real %LOCALAPPDATA%\\MyShop\\data\\shop.db, and any test that
writes through SessionLocal would modify real user data.
"""
import pytest

from app.database import connection as dbconn
from app.database.models import Base


@pytest.fixture(scope="session", autouse=True)
def isolated_database(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_shop.db"
    dbconn.reset_engine_for_path_for_tests(db_file)
    Base.metadata.create_all(dbconn.engine)
    yield db_file
    dbconn.engine.dispose()
    dbconn.reset_engine_for_path()
