from sqlalchemy import select
from app.database.connection import SessionLocal
from app.database.models import User
from app.services.security import hash_password, verify_password

class AuthService:
    def has_users(self):
        with SessionLocal() as s:
            return s.scalar(select(User.id).limit(1)) is not None
    def create_admin(self, password):
        with SessionLocal.begin() as s:
            s.add(User(username="admin", password_hash=hash_password(password),
                       role="admin", must_change_password=False))
    def authenticate(self, username, password):
        with SessionLocal() as s:
            u=s.scalar(select(User).where(User.username==username))
            if u and verify_password(password,u.password_hash):
                return {"id":u.id,"username":u.username,"role":u.role}
            return None
