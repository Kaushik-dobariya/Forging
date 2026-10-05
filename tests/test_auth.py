import pytest
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_session_token,
    verify_session_token,
)
from app.core.config import settings
from app.models.user import User


def test_password_hashing():
    """Verifies that bcrypt hashing creates valid and verifiable hashes."""
    pwd = "IndustrialPassword@2026"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword@123", hashed) is False


def test_password_strength_validator():
    """Verifies password strength enforcement."""
    is_valid, msg = validate_password_strength("short")
    assert is_valid is False

    is_valid, msg = validate_password_strength("alllowercase123!")
    assert is_valid is False

    is_valid, msg = validate_password_strength("ALLUPPERCASE123!")
    assert is_valid is False

    is_valid, msg = validate_password_strength("ValidPass@12345")
    assert is_valid is True
    assert msg == ""


def test_session_token_cryptography():
    """Verifies signed session token generation and tamper detection."""
    payload = {"user_id": 42, "role": "super_admin", "session_id": "test-uuid"}
    token = create_session_token(payload)
    assert token is not None

    decoded = verify_session_token(token)
    assert decoded["user_id"] == 42
    assert decoded["role"] == "super_admin"

    tampered_token = token + "corrupt"
    assert verify_session_token(tampered_token) is None


def test_protected_admin_route_redirects_unauthenticated(client):
    """Verifies that accessing /admin without a session redirects to login."""
    response = client.get("/admin", headers={"Accept": "text/html"}, follow_redirects=False)
    assert response.status_code == 307
    assert "/admin/login" in response.headers["Location"]


def test_admin_login_success_and_dashboard_access(client, superadmin_user):
    """Verifies full authentication flow: login form post, cookie issuance, and dashboard render."""
    response = client.post(
        "/admin/login",
        data={
            "email": "supertest@forgingcms.com",
            "password": "SuperSecret@123",
            "next": "/admin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin"

    # Verify session cookie was set
    cookie_header = response.headers.get("set-cookie", "")
    assert settings.SESSION_COOKIE_NAME in cookie_header
    assert "HttpOnly" in cookie_header

    # Follow redirect to dashboard with the cookie
    dash_response = client.get("/admin", headers={"Accept": "text/html"})
    assert dash_response.status_code == 200
    assert "Welcome back" in dash_response.text
    assert "Test Super Admin" in dash_response.text


def test_admin_login_invalid_credentials(client, superadmin_user):
    """Verifies error handling and HTTP 400 on incorrect password."""
    response = client.post(
        "/admin/login",
        data={
            "email": "supertest@forgingcms.com",
            "password": "IncorrectPassword@999",
            "next": "/admin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Invalid email or password" in response.text


def test_admin_logout(client, superadmin_user):
    """Verifies that logout clears the session cookie and prevents subsequent dashboard access."""
    # 1. Login
    login_resp = client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 302

    # 2. Logout
    logout_resp = client.post("/admin/logout", follow_redirects=False)
    assert logout_resp.status_code == 302
    assert "/admin/login" in logout_resp.headers["Location"]

    # 3. Accessing /admin now should redirect to login
    dash_resp = client.get("/admin", headers={"Accept": "text/html"}, follow_redirects=False)
    assert dash_resp.status_code == 307
    assert "/admin/login" in dash_resp.headers["Location"]


def test_account_lockout_after_max_attempts(client, db, superadmin_user):
    """Verifies that 5 failed attempts trigger an account lockout."""
    # Reset attempts first
    superadmin_user.failed_login_attempts = 0
    superadmin_user.locked_until = None
    db.commit()

    for attempt in range(4):
        resp = client.post(
            "/admin/login",
            data={"email": "supertest@forgingcms.com", "password": "WrongPassword@1"},
        )
        assert resp.status_code == 400
        assert "attempt(s) remaining" in resp.text

    # 5th attempt locks the account
    resp5 = client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "WrongPassword@1"},
    )
    assert resp5.status_code == 400
    assert "Account locked" in resp5.text

    # 6th attempt even with correct password is now blocked by lockout
    resp6 = client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
    )
    assert resp6.status_code == 400
    assert "temporarily locked" in resp6.text
