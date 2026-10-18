import re
import pytest
from app.core.config import settings
from app.core.security import hash_password, verify_password, generate_csrf_token, verify_session_token
from app.models.user import User, UserRole
from app.services.auth_service import auth_service


def extract_csrf_token(html_text: str) -> str:
    """Helper to extract CSRF token from HTML form input."""
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_text)
    if not match:
        match = re.search(r'value="([^"]+)"\s+name="csrf_token"', html_text)
    return match.group(1) if match else ""


# ==============================================================================
# 1. SIGN IN TESTS
# ==============================================================================

def test_admin_signin_success_and_cookie_security(client, superadmin_user):
    """Verifies successful administrator sign-in, secure cookies, and redirection."""
    resp = client.post(
        "/admin/login",
        data={
            "email": "supertest@forgingcms.com",
            "password": "SuperSecret@123",
            "next": "/admin",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/admin"

    # Verify cookie attributes
    cookie_header = resp.headers.get("set-cookie", "")
    assert settings.SESSION_COOKIE_NAME in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/" in cookie_header


def test_admin_signin_failures_generic_error(client, superadmin_user):
    """Verifies that sign-in rejects incorrect credentials safely without user enumeration."""
    # 1. Non-existent email
    resp_unknown = client.post(
        "/admin/login",
        data={"email": "nonexistent_admin@forgingcms.com", "password": "RandomPassword@999"},
        follow_redirects=False,
    )
    assert resp_unknown.status_code == 400
    assert "Invalid email or password" in resp_unknown.text

    # 2. Existing user, incorrect password
    resp_wrong = client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "WrongPassword@999"},
        follow_redirects=False,
    )
    assert resp_wrong.status_code == 400
    assert "Invalid email or password" in resp_wrong.text


def test_admin_signin_inactive_account(client, db, superadmin_user):
    """Verifies that deactivated accounts are prevented from authenticating."""
    superadmin_user.is_active = False
    db.commit()

    try:
        resp = client.post(
            "/admin/login",
            data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
            follow_redirects=False,
        )
        assert resp.status_code == 400
        assert "deactivated" in resp.text
    finally:
        superadmin_user.is_active = True
        db.commit()


def test_unauthenticated_access_redirects_to_login(client):
    """Verifies that unauthenticated access to protected admin pages redirects to login with next parameter."""
    for path in ["/admin", "/admin/profile", "/admin/change-password"]:
        resp = client.get(path, headers={"Accept": "text/html"}, follow_redirects=False)
        assert resp.status_code == 307
        assert "/admin/login" in resp.headers["Location"]
        assert f"next={path}" in resp.headers["Location"]


def test_authenticated_user_visiting_login_redirects_to_dashboard(client, superadmin_user):
    """Verifies that already-authenticated users reaching /admin/login are redirected to dashboard."""
    # Login first
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    # Visit login view
    resp = client.get("/admin/login", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/admin"


# ==============================================================================
# 2. ADMIN HEADER & ACCOUNT DROPDOWN TESTS
# ==============================================================================

def test_admin_header_account_dropdown_renders_user_details(client, superadmin_user):
    """Verifies that the admin header includes avatar initials, display name, role badge, chevron, and menu items."""
    # Login
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    dash_resp = client.get("/admin", headers={"Accept": "text/html"})
    assert dash_resp.status_code == 200

    html = dash_resp.text
    # 1. Actual display name rendered
    assert "Test Super Admin" in html

    # 2. Role badge
    assert "SUPER ADMIN" in html

    # 3. Avatar initials: "TA" (Test Admin)
    assert "TA" in html

    # 4. Account menu buttons and links
    assert 'id="adminAccountDropdownBtn"' in html
    assert 'id="adminAccountMenu"' in html
    assert 'href="/admin/profile"' in html
    assert 'href="/admin/change-password"' in html
    assert 'action="/admin/logout"' in html
    assert 'name="csrf_token"' in html

    # 5. Must NOT display a Sign In action for authenticated user
    assert "Sign In" not in html


# ==============================================================================
# 3. MY PROFILE TESTS
# ==============================================================================

def test_admin_profile_view_authenticated(client, superadmin_user):
    """Verifies authenticated access to the administrator profile view."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    resp = client.get("/admin/profile", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    html = resp.text

    assert "My Profile" in html
    assert "Test Super Admin" in html
    assert "supertest@forgingcms.com" in html
    assert "SUPER ADMIN" in html
    assert "Active" in html
    assert 'name="csrf_token"' in html


def test_admin_profile_successful_update(client, db, superadmin_user):
    """Verifies that an administrator can update their full name and email."""
    # 1. Login
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    # 2. Get profile page and extract CSRF token
    profile_page = client.get("/admin/profile")
    csrf_token = extract_csrf_token(profile_page.text)
    assert csrf_token != ""

    # 3. Update profile
    resp = client.post(
        "/admin/profile",
        data={
            "full_name": "Updated Super Admin",
            "email": "updated_super@forgingcms.com",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert "Your profile has been updated successfully" in resp.text

    # 4. Verify in DB
    db.refresh(superadmin_user)
    assert superadmin_user.full_name == "Updated Super Admin"
    assert superadmin_user.email == "updated_super@forgingcms.com"

    # Restore email for subsequent tests
    superadmin_user.full_name = "Test Super Admin"
    superadmin_user.email = "supertest@forgingcms.com"
    db.commit()


def test_admin_profile_duplicate_email_rejected(client, db, superadmin_user):
    """Verifies that profile email update rejects email in use by another account."""
    # Create second administrator
    second_user = User(
        email="secondadmin@forgingcms.com",
        hashed_password=hash_password("SecondAdmin@123"),
        full_name="Second Admin",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db.add(second_user)
    db.commit()

    # Login as superadmin
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    profile_page = client.get("/admin/profile")
    csrf_token = extract_csrf_token(profile_page.text)

    # Attempt to take second_user's email
    resp = client.post(
        "/admin/profile",
        data={
            "full_name": "Test Super Admin",
            "email": "secondadmin@forgingcms.com",
            "csrf_token": csrf_token,
        },
    )
    assert resp.status_code == 400
    assert "already in use by another account" in resp.text

    # Verify db was NOT modified
    db.refresh(superadmin_user)
    assert superadmin_user.email == "supertest@forgingcms.com"


def test_admin_profile_invalid_input_validation(client, superadmin_user):
    """Verifies server-side validation on short full names and invalid email formatting."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    profile_page = client.get("/admin/profile")
    csrf_token = extract_csrf_token(profile_page.text)

    # Name too short
    resp_short = client.post(
        "/admin/profile",
        data={"full_name": "A", "email": "valid@forgingcms.com", "csrf_token": csrf_token},
    )
    assert resp_short.status_code == 400
    assert "between 2 and 150 characters" in resp_short.text

    # Invalid email
    resp_email = client.post(
        "/admin/profile",
        data={"full_name": "Valid Name", "email": "not-an-email", "csrf_token": csrf_token},
    )
    assert resp_email.status_code == 400
    assert "valid email address" in resp_email.text


def test_admin_profile_role_tampering_prevented(client, db):
    """Verifies that an administrator cannot escalate or modify their own role via profile POST."""
    editor_user = db.query(User).filter(User.email == "editor@forgingcms.com").first()
    if not editor_user:
        editor_user = User(
            email="editor@forgingcms.com",
            hashed_password=hash_password("EditorPass@123"),
            full_name="Standard Editor",
            role=UserRole.ADMIN.value,
            is_active=True,
            is_superuser=False,
        )
        db.add(editor_user)
        db.commit()
        db.refresh(editor_user)

    # Login as editor
    client.post(
        "/admin/login",
        data={"email": "editor@forgingcms.com", "password": "EditorPass@123"},
        follow_redirects=False,
    )

    profile_page = client.get("/admin/profile")
    csrf_token = extract_csrf_token(profile_page.text)

    # Submit malicious role modification payload
    resp = client.post(
        "/admin/profile",
        data={
            "full_name": "Standard Editor",
            "email": "editor@forgingcms.com",
            "role": "super_admin",
            "is_superuser": "true",
            "csrf_token": csrf_token,
        },
    )
    assert resp.status_code == 200

    # Verify role remained strictly unchanged in database
    db.refresh(editor_user)
    assert editor_user.role == UserRole.ADMIN.value
    assert editor_user.is_superuser is False


def test_admin_profile_csrf_protection(client, superadmin_user):
    """Verifies that profile update rejects requests with missing or invalid CSRF tokens."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    # 1. Missing CSRF
    resp_missing = client.post(
        "/admin/profile",
        data={"full_name": "Test Super Admin", "email": "supertest@forgingcms.com"},
    )
    assert resp_missing.status_code == 403

    # 2. Invalid CSRF
    resp_invalid = client.post(
        "/admin/profile",
        data={
            "full_name": "Test Super Admin",
            "email": "supertest@forgingcms.com",
            "csrf_token": "tampered-csrf-token",
        },
    )
    assert resp_invalid.status_code == 403


# ==============================================================================
# 4. CHANGE PASSWORD TESTS
# ==============================================================================

def test_change_password_view_authenticated(client, superadmin_user):
    """Verifies authenticated access to the change password interface."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    resp = client.get("/admin/change-password", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    html = resp.text
    assert "Change Password" in html
    assert "Current Password" in html
    assert "New Password" in html
    assert "Confirm New Password" in html
    assert "Password Security Policy" in html
    assert 'name="csrf_token"' in html


def test_change_password_current_password_incorrect(client, superadmin_user):
    """Verifies that an incorrect current password is rejected."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    pwd_page = client.get("/admin/change-password")
    csrf_token = extract_csrf_token(pwd_page.text)

    resp = client.post(
        "/admin/change-password",
        data={
            "current_password": "WrongCurrentPassword@1",
            "new_password": "BrandNewPassword@2026",
            "confirm_password": "BrandNewPassword@2026",
            "csrf_token": csrf_token,
        },
    )
    assert resp.status_code == 400
    assert "Current password is incorrect" in resp.text


def test_change_password_reuse_rejection(client, superadmin_user):
    """Verifies that reusing the current password is rejected."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    pwd_page = client.get("/admin/change-password")
    csrf_token = extract_csrf_token(pwd_page.text)

    resp = client.post(
        "/admin/change-password",
        data={
            "current_password": "SuperSecret@123",
            "new_password": "SuperSecret@123",
            "confirm_password": "SuperSecret@123",
            "csrf_token": csrf_token,
        },
    )
    assert resp.status_code == 400
    assert "cannot be the same as your current password" in resp.text


def test_change_password_mismatch_rejection(client, superadmin_user):
    """Verifies that mismatched confirmation password is rejected."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    pwd_page = client.get("/admin/change-password")
    csrf_token = extract_csrf_token(pwd_page.text)

    resp = client.post(
        "/admin/change-password",
        data={
            "current_password": "SuperSecret@123",
            "new_password": "BrandNewPassword@2026",
            "confirm_password": "DifferentPassword@2026",
            "csrf_token": csrf_token,
        },
    )
    assert resp.status_code == 400
    assert "do not match" in resp.text


def test_change_password_weak_policy_rejection(client, superadmin_user):
    """Verifies that passwords failing complexity requirements are rejected."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    pwd_page = client.get("/admin/change-password")
    csrf_token = extract_csrf_token(pwd_page.text)

    # 1. Too short
    resp_short = client.post(
        "/admin/change-password",
        data={
            "current_password": "SuperSecret@123",
            "new_password": "Short@1",
            "confirm_password": "Short@1",
            "csrf_token": csrf_token,
        },
    )
    assert resp_short.status_code == 400
    assert "at least 8 characters" in resp_short.text

    # 2. No uppercase
    resp_no_upper = client.post(
        "/admin/change-password",
        data={
            "current_password": "SuperSecret@123",
            "new_password": "alllowercase@123",
            "confirm_password": "alllowercase@123",
            "csrf_token": csrf_token,
        },
    )
    assert resp_no_upper.status_code == 400
    assert "uppercase letter" in resp_no_upper.text


def test_change_password_success_and_session_invalidation(client, db, superadmin_user):
    """Verifies successful password change, bcrypt hashing, current session preservation, and invalidation of other sessions."""
    # 1. Login to establish primary session
    login_resp = client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )
    old_cookie_token = client.cookies.get(settings.SESSION_COOKIE_NAME)
    assert old_cookie_token is not None

    # 2. Extract CSRF token
    pwd_page = client.get("/admin/change-password")
    csrf_token = extract_csrf_token(pwd_page.text)

    new_password = "BrandNewIndustrialPass@2026"

    # 3. Submit valid password change
    change_resp = client.post(
        "/admin/change-password",
        data={
            "current_password": "SuperSecret@123",
            "new_password": new_password,
            "confirm_password": new_password,
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    assert change_resp.status_code == 200
    assert "Your password has been changed successfully" in change_resp.text

    # 4. Verify password in DB is bcrypt-hashed and verified
    db.refresh(superadmin_user)
    assert verify_password(new_password, superadmin_user.hashed_password) is True
    assert new_password not in change_resp.text
    assert superadmin_user.hashed_password not in change_resp.text

    # 5. Current session remains authenticated with fresh cookie
    dash_resp = client.get("/admin", headers={"Accept": "text/html"})
    assert dash_resp.status_code == 200

    # 6. Verify that an old/other session token (from before password change) is now invalidated
    client.cookies.set(settings.SESSION_COOKIE_NAME, old_cookie_token)
    stale_resp = client.get("/admin", headers={"Accept": "text/html"}, follow_redirects=False)
    assert stale_resp.status_code == 307
    assert "/admin/login" in stale_resp.headers["Location"]

    # Restore original password for clean teardown
    superadmin_user.hashed_password = hash_password("SuperSecret@123")
    db.commit()


# ==============================================================================
# 5. SIGN OUT & SESSION INVALIDATION TESTS
# ==============================================================================

def test_admin_logout_post_with_csrf_invalidates_session(client, superadmin_user):
    """Verifies that POST logout with CSRF clears cookie, invalidates session token on server, and blocks access."""
    # 1. Login
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )
    session_token = client.cookies.get(settings.SESSION_COOKIE_NAME)
    assert session_token is not None

    # 2. Extract CSRF token from dashboard
    dash_resp = client.get("/admin")
    csrf_token = extract_csrf_token(dash_resp.text)
    assert csrf_token != ""

    # 3. Perform POST logout
    logout_resp = client.post(
        "/admin/logout",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert logout_resp.status_code == 302
    assert "/admin/login" in logout_resp.headers["Location"]

    # 4. Access without cookie redirects to login
    dash_unauth = client.get("/admin", headers={"Accept": "text/html"}, follow_redirects=False)
    assert dash_unauth.status_code == 307

    # 5. Replaying the invalidated session token is blocked on server
    client.cookies.set(settings.SESSION_COOKIE_NAME, session_token)
    replay_resp = client.get("/admin", headers={"Accept": "text/html"}, follow_redirects=False)
    assert replay_resp.status_code == 307
    assert "/admin/login" in replay_resp.headers["Location"]


def test_admin_logout_rejects_unprotected_get(client, superadmin_user):
    """Verifies that GET /admin/logout is blocked with HTTP 405 Method Not Allowed."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    get_logout_resp = client.get("/admin/logout", follow_redirects=False)
    assert get_logout_resp.status_code == 405


def test_admin_logout_rejects_invalid_csrf(client, superadmin_user):
    """Verifies that POST /admin/logout with invalid CSRF token is rejected with HTTP 403."""
    client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )

    resp = client.post(
        "/admin/logout",
        data={"csrf_token": "tampered-token"},
        follow_redirects=False,
    )
    assert resp.status_code == 403
