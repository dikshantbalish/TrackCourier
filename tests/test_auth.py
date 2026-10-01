import hashlib

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.database.connection import SessionLocal
from app.models.admin import AdminUser
from app.services.authentication import verify_password


def test_production_requires_secure_session_cookie():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            session_secret="test-only-session-secret-that-is-at-least-32-characters",
            environment="production",
            session_cookie_secure=False,
        )


def test_cors_rejects_wildcard_origins():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            session_secret="test-only-session-secret-that-is-at-least-32-characters",
            cors_origins="*",
        )


def test_invalid_login_does_not_echo_password(client):
    password = "private-input-" + "x" * 129
    response = client.post(
        "/api/auth/login",
        json={"username": "operator", "password": password},
    )

    assert response.status_code == 422
    assert password not in response.text
    assert '"input"' not in response.text


def test_legacy_pbkdf2_admin_hash_is_upgraded_after_login(client):
    password = "legacy-admin-password-for-test"
    salt = "legacy-test-salt"
    iterations = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    legacy_hash = f"pbkdf2:sha256:{iterations}${salt}${digest}"
    with SessionLocal() as database:
        admin = AdminUser(username="legacy-operator", password_hash=legacy_hash)
        database.add(admin)
        database.commit()

    response = client.post(
        "/api/auth/login",
        json={"username": "legacy-operator", "password": password},
    )

    assert response.status_code == 200
    with SessionLocal() as database:
        admin = database.query(AdminUser).filter_by(username="legacy-operator").one()
        assert admin.password_hash.startswith("$argon2id$")
        assert verify_password(password, admin.password_hash)


def test_admin_routes_require_authentication(client):
    assert client.get("/api/admin/shipments").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_login_session_and_logout(client, admin_account):
    wrong_password = client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "incorrect-password"},
    )
    assert wrong_password.status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"username": " OPERATOR ", "password": "a-test-password-with-12-chars"},
    )
    assert login.status_code == 200
    assert login.json() == {"authenticated": True, "username": "operator"}
    assert "sbc_admin_session" in client.cookies
    set_cookie = login.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "secure" not in set_cookie

    current_admin = client.get("/api/auth/me")
    assert current_admin.status_code == 200
    assert "password_hash" not in current_admin.json()

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    with SessionLocal() as database:
        stored_admin = database.get(AdminUser, admin_account.id)
        assert stored_admin is not None
        assert stored_admin.password_hash != "a-test-password-with-12-chars"
        assert verify_password("a-test-password-with-12-chars", stored_admin.password_hash)


def test_mutation_from_untrusted_origin_is_rejected(client):
    response = client.post(
        "/api/auth/logout",
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403
