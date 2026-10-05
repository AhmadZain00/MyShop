import sys
from sqlalchemy import text
from PySide6 import QtWidgets, QtCore
from app.config import APP_NAME, APP_VERSION
from app.database import connection as dbconn
from app.database.migrations import CURRENT_SCHEMA, migrate
from app.services.auth_service import AuthService
from app.services.production import configure_logging
from app.ui.dialogs import LoginDialog, FirstRunDialog, ForcedChangePasswordDialog
from app.ui.main_window import MainWindow

def _sync_meta():
    """Keep app_meta in step with the running build (single source: config.py)."""
    with dbconn.engine.begin() as conn:
        conn.execute(text(
            "UPDATE app_meta SET value = :v WHERE key = 'app_version'"
        ), {"v": APP_VERSION})
        conn.execute(text(
            "UPDATE app_meta SET value = :v WHERE key = 'schema_version'"
        ), {"v": str(CURRENT_SCHEMA)})

def main():
    logger = configure_logging()
    # Log any uncaught exception instead of dying silently in windowed mode.
    def _excepthook(exc_type, exc, tb):
        logger.exception("Uncaught exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = _excepthook

    dbconn.initialize_database()
    migrate()
    _sync_meta()
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setLayoutDirection(QtCore.Qt.RightToLeft)
    auth = AuthService()
    if not auth.has_users():
        d = FirstRunDialog(auth)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
    login = LoginDialog(auth)
    if login.exec() != QtWidgets.QDialog.Accepted:
        return
    user = login.result_user
    # A temporary password set by the admin must be replaced before continuing.
    if user.get("must_change_password"):
        forced = ForcedChangePasswordDialog(user["id"], auth, user["username"])
        if forced.exec() != QtWidgets.QDialog.Accepted:
            return
        user["must_change_password"] = False
    w = MainWindow(user)
    w.show()
    sys.exit(app.exec())
