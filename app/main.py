import sys
from PySide6 import QtWidgets, QtCore
from app.config import APP_NAME, APP_VERSION, db_path
from app.database.connection import initialize_database
from app.database.migrations import migrate
from app.services.auth_service import AuthService
from app.ui.dialogs import LoginDialog, FirstRunDialog
from app.ui.main_window import MainWindow

def main():
    initialize_database()
    migrate()
    app=QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setLayoutDirection(QtCore.Qt.RightToLeft)
    auth=AuthService()
    if not auth.has_users():
        d=FirstRunDialog(auth)
        if d.exec()!=QtWidgets.QDialog.Accepted:
            return
    login=LoginDialog(auth)
    if login.exec()!=QtWidgets.QDialog.Accepted:
        return
    w=MainWindow(login.result_user)
    w.show()
    sys.exit(app.exec())
