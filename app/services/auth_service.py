import uuid
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Response, Request
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.repositories.user_repository import user_repository
from app.core.security import (
    hash_password,
    verify_password,
    create_session_token,
    verify_session_token,
    validate_password_strength,
    MAX_FAILED_LOGIN_ATTEMPTS,
    LOCKOUT_DURATION_MINUTES,
)
from app.core.config import settings
from app.core.logging import logger


class AuthService:
    """Service encapsulating all administrative authentication and session business logic."""

    def __init__(self):
        self._revoked_session_ids = set()

    def revoke_session(self, session_id: Optional[str]) -> None:
        """Revokes a session ID so it cannot be used again."""
        if session_id:
            self._revoked_session_ids.add(session_id)

    def is_session_revoked(self, session_id: Optional[str]) -> bool:
        """Checks if a session ID has been explicitly revoked."""
        if not session_id:
            return False
        return session_id in self._revoked_session_ids

    def authenticate_admin(
        self,
        db: Session,
        email: str,
        password: str,
    ) -> Tuple[Optional[User], str]:
        user = user_repository.get_by_email(db, email)
        if not user:
            logger.warning("Authentication failed: user not found")
            return None, "Invalid email or password."

        if not user.is_active:
            logger.warning(f"Authentication rejected: inactive account for user {user.id}")
            return None, "Your account has been deactivated. Please contact an administrator."

        if user.is_locked():
            logger.warning(f"Authentication blocked: locked account for user {user.id}")
            return None, f"Account is temporarily locked due to failed attempts. Please try again in {LOCKOUT_DURATION_MINUTES} minutes."

        if not verify_password(password, user.hashed_password):
            user_repository.record_failed_attempt(
                db,
                user,
                max_attempts=MAX_FAILED_LOGIN_ATTEMPTS,
                lockout_minutes=LOCKOUT_DURATION_MINUTES,
            )
            attempts_left = max(0, MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts)
            if attempts_left == 0:
                return None, f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes due to multiple failed login attempts."
            return None, f"Invalid email or password. {attempts_left} attempt(s) remaining."

        # Successful authentication
        user_repository.reset_failed_attempts(db, user)
        logger.info(f"Admin authenticated successfully: user id {user.id}")
        return user, ""

    def create_admin_session(self, response: Response, user: User) -> str:
        """Issues an encrypted, secure session cookie for the authenticated admin."""
        session_id = str(uuid.uuid4())
        payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "is_superuser": user.is_superuser,
            "session_id": session_id,
            "pwd_hash_prefix": user.hashed_password[:10] if user.hashed_password else "",
        }
        token = create_session_token(payload)

        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=token,
            max_age=settings.SESSION_MAX_AGE_SECONDS,
            expires=settings.SESSION_MAX_AGE_SECONDS,
            path="/",
            domain=None,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )
        return session_id

    def terminate_admin_session(self, response: Response, session_id: Optional[str] = None) -> None:
        """Clears the admin session cookie and records session revocation."""
        if session_id:
            self.revoke_session(session_id)
        response.delete_cookie(
            key=settings.SESSION_COOKIE_NAME,
            path="/",
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )

    def get_current_user_from_cookie(
        self,
        db: Session,
        request: Request,
    ) -> Optional[User]:
        token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if not token:
            return None

        payload = verify_session_token(token, max_age=settings.SESSION_MAX_AGE_SECONDS)
        if not payload or "user_id" not in payload:
            return None

        session_id = payload.get("session_id")
        if self.is_session_revoked(session_id):
            return None

        user = user_repository.get_by_id(db, payload["user_id"])
        if not user or not user.is_active:
            return None

        # Invalidate tokens signed with previous password hash if password changed
        token_pwd_prefix = payload.get("pwd_hash_prefix")
        if token_pwd_prefix and user.hashed_password and token_pwd_prefix != user.hashed_password[:10]:
            logger.info(f"Session token invalidated due to password change for user {user.id}")
            return None

        return user

    def bootstrap_superadmin(
        self,
        db: Session,
        email: Optional[str] = None,
        password: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> Optional[User]:
        """Bootstraps the initial Super Admin account if no superadmin exists."""
        target_email = email or settings.FIRST_SUPERADMIN_EMAIL
        target_password = password or settings.FIRST_SUPERADMIN_PASSWORD
        target_name = full_name or settings.FIRST_SUPERADMIN_NAME

        if not target_email or not target_password:
            return None

        existing_user = user_repository.get_by_email(db, target_email)
        if existing_user:
            return existing_user

        # Check if any superadmin already exists
        if user_repository.count_superadmins(db) > 0 and email is None:
            # Already bootstrapped with another superadmin
            return None

        is_valid, msg = validate_password_strength(target_password)
        if not is_valid:
            logger.warning(f"Super admin password warning: {msg}")

        hashed = hash_password(target_password)
        user_in = UserCreate(
            email=target_email,
            password=target_password,
            full_name=target_name,
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
        created = user_repository.create(db, user_in, hashed, is_superuser=True)
        logger.info(f"Bootstrapped superadmin account: {created.email}")
        return created


auth_service = AuthService()
