from PySide6 import QtWidgets, QtCore

MIN_PASSWORD_LEN = 8


def _valid_password_pair(dialog, password_edit, confirm_edit, old_edit=None):
    """Shared validation for password dialogs. Returns the new password text."""
    password = password_edit.text()
    if len(password) < MIN_PASSWORD_LEN:
        QtWidgets.QMessageBox.warning(
            dialog, "خطأ",
            f"كلمة المرور يجب أن تكون {MIN_PASSWORD_LEN} أحرف على الأقل.")
        return None
    if password != confirm_edit.text():
        QtWidgets.QMessageBox.warning(dialog, "خطأ", "كلمتا المرور غير متطابقتين.")
        return None
    if old_edit is not None and password == old_edit.text():
        QtWidgets.QMessageBox.warning(
            dialog, "خطأ", "كلمة المرور الجديدة يجب أن تختلف عن الحالية.")
        return None
    return password


class ChangePasswordDialog(QtWidgets.QDialog):
    """User changes their own password (old password required)."""
    def __init__(self, user_id, auth_service, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.auth = auth_service
        self.setWindowTitle("تغيير كلمة المرور"); self.setMinimumWidth(420)
        lay = QtWidgets.QFormLayout(self)
        self.old_password = QtWidgets.QLineEdit()
        self.old_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm = QtWidgets.QLineEdit()
        self.confirm.setEchoMode(QtWidgets.QLineEdit.Password)
        lay.addRow("كلمة المرور الحالية:", self.old_password)
        lay.addRow("كلمة المرور الجديدة:", self.password)
        lay.addRow("تأكيد كلمة المرور:", self.confirm)
        b = QtWidgets.QPushButton("تغيير كلمة المرور")
        b.clicked.connect(self.change)
        lay.addRow(b)

    def change(self):
        new = _valid_password_pair(self, self.password, self.confirm, self.old_password)
        if new is None:
            return
        try:
            self.auth.change_password(self.user_id, self.old_password.text(), new)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "خطأ", str(e))
            return
        QtWidgets.QMessageBox.information(self, "تم", "تم تغيير كلمة المرور بنجاح.")
        self.accept()


class ForcedChangePasswordDialog(QtWidgets.QDialog):
    """Shown at login when must_change_password is set; cannot be skipped."""
    def __init__(self, user_id, auth_service, username, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.auth = auth_service
        self.setWindowTitle("تغيير إجباري لكلمة المرور")
        self.setMinimumWidth(440)
        lay = QtWidgets.QVBoxLayout(self)
        notice = QtWidgets.QLabel(
            f"مرحبًا {username}،\n\n"
            "كلمة مرورك مؤقتة وتم تعيينها من قبل المدير.\n"
            "يجب تعيين كلمة مرور جديدة قبل المتابعة.")
        lay.addWidget(notice)
        form = QtWidgets.QFormLayout()
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm = QtWidgets.QLineEdit()
        self.confirm.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("كلمة المرور الجديدة:", self.password)
        form.addRow("تأكيد كلمة المرور:", self.confirm)
        lay.addLayout(form)
        b = QtWidgets.QPushButton("تعيين كلمة المرور")
        b.clicked.connect(self.change)
        lay.addWidget(b)

    # Block closing via the X button so the user cannot skip the change.
    def reject(self):
        QtWidgets.QMessageBox.warning(
            self, "مطلوب",
            "يجب تعيين كلمة مرور جديدة قبل المتابعة.")

    def change(self):
        new = _valid_password_pair(self, self.password, self.confirm)
        if new is None:
            return
        try:
            # The user already proved their identity by logging in with the
            # temporary password, so no old-password re-check is needed here.
            self.auth.set_new_password_after_reset(self.user_id, new)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "خطأ", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "تم", "تم تعيين كلمة المرور. يمكنك المتابعة.")
        self.accept()


class UserDialog(QtWidgets.QDialog):
    """Admin creates a new user account."""
    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth = auth_service
        self.setWindowTitle("إضافة مستخدم"); self.setMinimumWidth(420)
        lay = QtWidgets.QFormLayout(self)
        self.username = QtWidgets.QLineEdit()
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm = QtWidgets.QLineEdit()
        self.confirm.setEchoMode(QtWidgets.QLineEdit.Password)
        self.role = QtWidgets.QComboBox()
        self.role.addItem("موظف", "employee")
        self.role.addItem("مدير", "admin")
        lay.addRow("اسم المستخدم:", self.username)
        lay.addRow("كلمة المرور المؤقتة:", self.password)
        lay.addRow("تأكيد كلمة المرور:", self.confirm)
        lay.addRow("الدور:", self.role)
        bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)

    def save(self):
        username = self.username.text().strip()
        if not username:
            QtWidgets.QMessageBox.warning(self, "خطأ", "اسم المستخدم مطلوب.")
            return
        new = _valid_password_pair(self, self.password, self.confirm)
        if new is None:
            return
        try:
            self.auth.create_user(username, new, self.role.currentData(),
                                  must_change_password=True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "خطأ", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "تم",
            f"تم إنشاء المستخدم '{username}'.\n"
            "سيُطلب منه تعيين كلمة مرور جديدة عند أول تسجيل دخول.")
        self.accept()


class ResetPasswordDialog(QtWidgets.QDialog):
    """Admin resets another user's password to a temporary value."""
    def __init__(self, user_id, username, auth_service, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.auth = auth_service
        self.setWindowTitle("إعادة تعيين كلمة المرور")
        self.setMinimumWidth(420)
        lay = QtWidgets.QFormLayout(self)
        info = QtWidgets.QLabel(f"إعادة تعيين كلمة مرور المستخدم: {username}")
        lay.addRow(info)
        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm = QtWidgets.QLineEdit()
        self.confirm.setEchoMode(QtWidgets.QLineEdit.Password)
        lay.addRow("كلمة المرور المؤقتة:", self.password)
        lay.addRow("تأكيد كلمة المرور:", self.confirm)
        bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)

    def save(self):
        new = _valid_password_pair(self, self.password, self.confirm)
        if new is None:
            return
        try:
            self.auth.reset_password(self.user_id, new)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "خطأ", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "تم",
            "تم إعادة تعيين كلمة المرور.\n"
            "سيُطلب من المستخدم تعيين كلمة مرور جديدة عند تسجيل الدخول التالي.")
        self.accept()

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

