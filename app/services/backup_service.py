from pathlib import Path
from datetime import datetime
import shutil, sqlite3
from app.config import backups_dir
from app.database import connection as dbconn
from app.database.connection import validate_database

def backup_to(destination=None):
    src = dbconn.db_path()
    if destination is None:
        destination = backups_dir() / f"backup_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Use the SQLite online backup API so WAL checkpoints are included.
    con = sqlite3.connect(src)
    try:
        out = sqlite3.connect(destination)
        try:
            with out:
                con.backup(out)
        finally:
            out.close()
    finally:
        con.close()
    return destination

def _replace_database(source):
    """Replace the active database file with *source* atomically.

    On Windows an open SQLite handle locks the file, so every pooled
    connection must be disposed before the file can be replaced.
    A safety backup is taken first so the operation is always reversible.
    """
    backup_to()
    dbconn.close_all_connections()
    target = dbconn.db_path()
    tmp = target.with_suffix(".restore.tmp")
    shutil.copy2(source, tmp)
    try:
        tmp.replace(target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    # Re-create the engine/sessionmaker bound to the (replaced) database file.
    dbconn.reset_engine_for_path()

def restore_from(source):
    source = Path(source)
    ok, msg = validate_database(source)
    if not ok:
        raise ValueError(msg)
    _replace_database(source)
    return dbconn.db_path()

def import_database_file(source):
    """Kept as a public alias for compatibility with earlier versions."""
    restore_from(source)
    return dbconn.db_path()
