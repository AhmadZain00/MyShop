"""Tests for user management: create, list, reset, delete, forced password change."""
import pytest

from app.services.auth_service import AuthService
from app.services.security import verify_password


@pytest.fixture()
def auth():
    return AuthService()


def test_create_and_authenticate_user(auth):
    uid = auth.create_user("ahmed", "TempPass123", "employee")
    assert uid is not None
    u = auth.authenticate("ahmed", "TempPass123")
    assert u is not None
    assert u["role"] == "employee"
    # Temporary password must force a change at next login.
    assert u["must_change_password"] is True


def test_duplicate_username_rejected(auth):
    auth.create_user("sara", "TempPass123", "employee")
    with pytest.raises(ValueError):
        auth.create_user("sara", "AnotherPass1", "employee")


def test_short_password_rejected(auth):
    with pytest.raises(ValueError):
        auth.create_user("omar", "short", "employee")


def test_list_users_returns_plain_dicts(auth):
    auth.create_user("khaled", "TempPass123", "employee")
    users = auth.list_users()
    assert all(isinstance(u, dict) for u in users)
    names = {u["username"] for u in users}
    assert "khaled" in names


def test_reset_password_sets_flag_for_employee(auth):
    uid = auth.create_user("mona", "TempPass123", "employee")
    auth.reset_password(uid, "NewTemp456")
    u = auth.authenticate("mona", "NewTemp456")
    assert u is not None
    assert u["must_change_password"] is True
    # Old password no longer works.
    assert auth.authenticate("mona", "TempPass123") is None


def test_reset_password_keeps_admin_flag_false(auth):
    # A newly created admin is not forced to change their password on reset.
    uid = auth.create_user("manager", "TempPass123", "admin",
                           must_change_password=False)
    auth.reset_password(uid, "NewTemp456")
    u = auth.authenticate("manager", "NewTemp456")
    assert u["must_change_password"] is False


def test_set_new_password_after_reset_clears_flag(auth):
    uid = auth.create_user("youssef", "TempPass123", "employee")
    assert auth.authenticate("youssef", "TempPass123")["must_change_password"]
    auth.set_new_password_after_reset(uid, "FinalPass789")
    u = auth.authenticate("youssef", "FinalPass789")
    assert u["must_change_password"] is False
    # No longer pending, so the bypass path must now refuse to work.
    with pytest.raises(ValueError):
        auth.set_new_password_after_reset(uid, "Hacked1234")


def test_change_password_requires_correct_old(auth):
    uid = auth.create_user("laila", "TempPass123", "employee")
    with pytest.raises(ValueError):
        auth.change_password(uid, "WrongOld123", "FinalPass789")
    auth.change_password(uid, "TempPass123", "FinalPass789")
    assert auth.authenticate("laila", "FinalPass789") is not None


def test_cannot_delete_last_admin(auth):
    # Create a fresh admin pair, remove every other admin (acting as boss2),
    # then prove the truly last remaining admin cannot be deleted.
    a1 = auth.create_user("boss1", "TempPass123", "admin", must_change_password=False)
    a2 = auth.create_user("boss2", "TempPass123", "admin", must_change_password=False)
    auth.delete_user(a1, acting_user_id=a2)
    for u in auth.list_users():
        if u["role"] == "admin" and u["id"] != a2:
            auth.delete_user(u["id"], acting_user_id=a2)
    with pytest.raises(ValueError):
        auth.delete_user(a2, acting_user_id=a2 + 1000)


def test_cannot_delete_self(auth):
    me = auth.list_users()[0]
    with pytest.raises(ValueError):
        auth.delete_user(me["id"], acting_user_id=me["id"])


def test_delete_employee_ok(auth):
    uid = auth.create_user("tariq", "TempPass123", "employee")
    admin_id = next(u["id"] for u in auth.list_users() if u["role"] == "admin")
    auth.delete_user(uid, admin_id)
    assert auth.authenticate("tariq", "TempPass123") is None


def test_admin_created_with_false_flag_not_forced(auth):
    uid = auth.create_user("chief", "TempPass123", "admin",
                           must_change_password=False)
    u = auth.authenticate("chief", "TempPass123")
    assert u is not None
    assert u["must_change_password"] is False
