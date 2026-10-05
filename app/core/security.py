import re
import secrets
import hmac
import hashlib
from typing import Optional, Tuple, Dict, Any
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import bcrypt
from app.core.config import settings
from app.core.logging import logger


# Brute-force lockout thresholds
MAX_FAILED_LOGIN_ATTEMPTS: int = 5
LOCKOUT_DURATION_MINUTES: int = 15

# Session serializer
_serializer = URLSafeTimedSerializer(secret_key=settings.SECRET_KEY, salt="forging-admin-session-salt")


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with a randomized salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash in constant time."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as exc:
        logger.warning(f"Password verification error: {exc}")
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validates password strength according to industrial security requirements:
    - Minimum 8 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one digit or special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9\W_]", password):
        return False, "Password must contain at least one digit or special character."
    return True, ""


def create_session_token(payload: Dict[str, Any]) -> str:
    """Creates a cryptographically signed, tamper-proof session token."""
    return _serializer.dumps(payload)


def verify_session_token(token: str, max_age: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Verifies and unpacks a signed session token.
    Enforces maximum age expiration (defaulting to settings.SESSION_MAX_AGE_SECONDS).
    """
    if not token:
        return None
    effective_max_age = max_age if max_age is not None else settings.SESSION_MAX_AGE_SECONDS
    try:
        data = _serializer.loads(token, max_age=effective_max_age)
        return data
    except (BadSignature, SignatureExpired) as exc:
        logger.debug(f"Invalid or expired session token: {exc}")
        return None


def generate_csrf_token(session_id: str) -> str:
    """
    Generates a deterministic yet cryptographically bound CSRF token for a given session.
    """
    key = settings.SECRET_KEY.encode("utf-8")
    msg = f"csrf:{session_id}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def validate_csrf_token(session_id: str, csrf_token: str) -> bool:
    """Validates an incoming CSRF token against the session using constant-time comparison."""
    if not session_id or not csrf_token:
        return False
    expected = generate_csrf_token(session_id)
    return secrets.compare_digest(expected, csrf_token)
