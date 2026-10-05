from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import auth_service
from app.core.permissions import is_admin, is_superadmin
from app.core.security import validate_csrf_token, verify_session_token
from app.core.config import settings


def get_current_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that enforces admin authentication.
    Redirects browser requests to /admin/login if unauthenticated,
    or raises HTTP 401 for API requests.
    """
    user = auth_service.get_current_user_from_cookie(db, request)
    accept_header = request.headers.get("accept", "")
    is_html_request = "text/html" in accept_header

    if not user or not user.is_active:
        if is_html_request:
            # Browser navigation redirect
            login_url = f"/admin/login?next={request.url.path}"
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": login_url},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    if not is_admin(user):
        if is_html_request:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You lack administrative permissions to access this area.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden.",
        )

    return user


def get_current_superadmin(
    current_user: User = Depends(get_current_admin),
) -> User:
    """Dependency that enforces super admin access only."""
    if not is_superadmin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Administrator access required.",
        )
    return current_user


async def verify_csrf(request: Request) -> None:
    """
    Validates CSRF token on mutating requests (POST, PUT, DELETE, PATCH).
    Extracts token from form data or X-CSRF-Token header.
    """
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return

    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        # Not an authenticated session or login attempt
        return

    payload = verify_session_token(token)
    if not payload or "session_id" not in payload:
        return

    session_id = payload["session_id"]
    csrf_token = request.headers.get("X-CSRF-Token")

    if not csrf_token and request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        form_data = await request.form()
        csrf_token = form_data.get("csrf_token")

    if not csrf_token or not validate_csrf_token(session_id, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token.",
        )
