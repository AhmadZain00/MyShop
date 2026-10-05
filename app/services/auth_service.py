from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import connection as dbconn
from app.database.models import User
from app.services.security import hash_password, verify_password

MIN_PASSWORD_LEN = 8

class AuthService:
    def has_users(self):
        with dbconn.SessionLocal() as s:
            return s.scalar(select(User.id).limit(1)) is not None

    def create_admin(self, password):
        with dbconn.SessionLocal.begin() as s:
            s.add(User(username="admin", password_hash=hash_password(password),
                       role="admin", must_change_password=False))

    def authenticate(self, username, password):
        with dbconn.SessionLocal() as s:
            u=s.scalar(select(User).where(User.username==username))
            if u and verify_password(password,u.password_hash):
                return {"id":u.id,"username":u.username,"role":u.role,
                        "must_change_password":u.must_change_password}
            return None

    # ---------------- User management (admin) ----------------

    def list_users(self):
        with dbconn.SessionLocal() as s:
            users = s.scalars(select(User).order_by(User.id)).all()
            # Detach plain dicts so the UI never holds live ORM objects.
            return [{"id": u.id, "username": u.username, "role": u.role,
                     "must_change_password": u.must_change_password,
                     "created_at": u.created_at} for u in users]

    def create_user(self, username, password, role="employee",
                    must_change_password=True):
        username = (username or "").strip()
        if not username:
            raise ValueError("اسم المستخدم مطلوب.")
        if len(password) < MIN_PASSWORD_LEN:
            raise ValueError(f"كلمة المرور يجب أن تكون {MIN_PASSWORD_LEN} أحرف على الأقل.")
        if role not in ("admin", "employee"):
            raise ValueError("الدور غير صالح.")
        with dbconn.SessionLocal.begin() as s:
            exists = s.scalar(select(User).where(User.username == username))
            if exists:
                raise ValueError("اسم المستخدم موجود بالفعل.")
            u = User(username=username, password_hash=hash_password(password),
                     role=role, must_change_password=must_change_password)
            s.add(u)
            try:
                s.flush()
            except IntegrityError as exc:
                raise ValueError("اسم المستخدم موجود بالفعل.") from exc
            return u.id

    def reset_password(self, user_id, new_password):
        if len(new_password) < MIN_PASSWORD_LEN:
            raise ValueError(f"كلمة المرور يجب أن تكون {MIN_PASSWORD_LEN} أحرف على الأقل.")
        with dbconn.SessionLocal.begin() as s:
            u = s.get(User, user_id)
            if not u:
                raise ValueError("المستخدم غير موجود.")
            u.password_hash = hash_password(new_password)
            if u.role != "admin":
                u.must_change_password = True

    def set_must_change_password(self, user_id, flag):
        with dbconn.SessionLocal.begin() as s:
            u = s.get(User, user_id)
            if not u:
                raise ValueError("المستخدم غير موجود.")
            u.must_change_password = flag

    def delete_user(self, user_id, acting_user_id):
        if user_id == acting_user_id:
            raise ValueError("لا يمكنك حذف حسابك الحالي.")
        with dbconn.SessionLocal.begin() as s:
            u = s.get(User, user_id)
            if not u:
                raise ValueError("المستخدم غير موجود.")
            if u.role == "admin":
                admins = s.scalar(select(User.id).where(User.role == "admin").limit(1))
                other_admin = s.scalar(
                    select(User.id).where(User.role == "admin", User.id != user_id).limit(1))
                if not other_admin:
                    raise ValueError("لا يمكن حذف آخر مدير في النظام.")
            s.delete(u)

    def set_new_password_after_reset(self, user_id, new_password):
        """Set the final password after a successful temp-password login.

        Only succeeds while the must_change_password flag is still set, so
        it cannot be used to bypass the old-password check.
        """
        if len(new_password) < MIN_PASSWORD_LEN:
            raise ValueError(f"كلمة المرور يجب أن تكون {MIN_PASSWORD_LEN} أحرف على الأقل.")
        with dbconn.SessionLocal.begin() as s:
            u = s.get(User, user_id)
            if not u:
                raise ValueError("المستخدم غير موجود.")
            if not u.must_change_password:
                raise ValueError("لا يوجد تغيير إجباري معلق لهذا الحساب.")
            u.password_hash = hash_password(new_password)
            u.must_change_password = False

    def change_password(self, user_id, old_password, new_password):
        if len(new_password) < MIN_PASSWORD_LEN:
            raise ValueError(f"كلمة المرور يجب أن تكون {MIN_PASSWORD_LEN} أحرف على الأقل.")
        with dbconn.SessionLocal.begin() as s:
            u = s.get(User, user_id)
            if not u:
                raise ValueError("المستخدم غير موجود.")
            if not verify_password(old_password, u.password_hash):
                raise ValueError("كلمة المرور الحالية غير صحيحة.")
            if old_password == new_password:
                raise ValueError("كلمة المرور الجديدة يجب أن تختلف عن الحالية.")
            u.password_hash = hash_password(new_password)
            u.must_change_password = False
