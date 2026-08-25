from PySide6 import QtWidgets, QtCore

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, auth_service, parent=None):
        super().__init__(parent); self.auth = auth_service
        self.setWindowTitle("تسجيل الدخول"); self.setMinimumWidth(360)
        lay = QtWidgets.QFormLayout(self)
        self.user = QtWidgets.QLineEdit("admin")
        self.password = QtWidgets.QLineEdit(); self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        lay.addRow("اسم المستخدم:", self.user); lay.addRow("كلمة المرور:", self.password)
        btn = QtWidgets.QPushButton("دخول"); btn.clicked.connect(self.accept_login); lay.addRow(btn)
        self.result_user = None
    def accept_login(self):
        u = self.auth.authenticate(self.user.text().strip(), self.password.text())
        if not u:
            QtWidgets.QMessageBox.warning(self, "خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة.")
            return
        self.result_user = u; self.accept()

class FirstRunDialog(QtWidgets.QDialog):
    def __init__(self, auth_service, parent=None):
        super().__init__(parent); self.auth=auth_service
        self.setWindowTitle("الإعداد الأول"); self.setMinimumWidth(420)
        lay=QtWidgets.QFormLayout(self)
        self.password=QtWidgets.QLineEdit(); self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm=QtWidgets.QLineEdit(); self.confirm.setEchoMode(QtWidgets.QLineEdit.Password)
        lay.addRow("كلمة مرور المدير:", self.password); lay.addRow("تأكيد كلمة المرور:", self.confirm)
        b=QtWidgets.QPushButton("إنشاء المدير"); b.clicked.connect(self.create); lay.addRow(b)
    def create(self):
        if len(self.password.text()) < 8:
            QtWidgets.QMessageBox.warning(self,"خطأ","كلمة المرور يجب أن تكون 8 أحرف على الأقل."); return
        if self.password.text()!=self.confirm.text():
            QtWidgets.QMessageBox.warning(self,"خطأ","كلمتا المرور غير متطابقتين."); return
        self.auth.create_admin(self.password.text()); self.accept()
