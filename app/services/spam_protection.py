import re
import time
from collections import defaultdict
from typing import Dict, List, Optional
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.core.config import settings
from app.core.logging import logger


_public_csrf_serializer = URLSafeTimedSerializer(
    secret_key=settings.SECRET_KEY, salt="forging-public-form-csrf-salt"
)


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter per client IP address.
    Prevents form flooding and brute-force submission attacks.
    """

    def __init__(self, max_requests: int = 15, window_seconds: int = 300):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = defaultdict(list)

    def is_rate_limited(self, client_ip: str) -> bool:
        """Checks if the client IP has exceeded the allowed request threshold."""
        if not client_ip:
            return False

        now = time.time()
        cutoff = now - self.window_seconds

        # Prune old timestamps
        timestamps = [t for t in self._history[client_ip] if t > cutoff]
        self._history[client_ip] = timestamps

        if len(timestamps) >= self.max_requests:
            logger.warning(
                f"Rate limit triggered for IP: {client_ip} ({len(timestamps)} requests in {self.window_seconds}s)"
            )
            return True

        return False

    def record_request(self, client_ip: str) -> None:
        """Records a successful request timestamp for the client IP."""
        if client_ip:
            self._history[client_ip].append(time.time())

    def clear(self) -> None:
        """Clears all tracking history (useful for testing)."""
        self._history.clear()


rate_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=300)


def generate_public_csrf_token(client_ip: str = "anon") -> str:
    """Generates a timed, signed CSRF token for public forms (contact, quote)."""
    return _public_csrf_serializer.dumps({"ip": client_ip, "t": time.time()})


def validate_public_csrf_token(token: str, max_age: int = 7200) -> bool:
    """
    Validates the public form CSRF token.
    Allows submission within 2 hours of page load.
    """
    if not token:
        return False
    try:
        data = _public_csrf_serializer.loads(token, max_age=max_age)
        return isinstance(data, dict) and "t" in data
    except (BadSignature, SignatureExpired) as exc:
        logger.debug(f"Invalid public CSRF token: {exc}")
        return False


def validate_honeypot(form_data: dict, honeypot_field: str = "website_url_check") -> bool:
    """
    Validates honeypot field.
    Returns True if valid (clean/human submission), False if filled (bot).
    """
    val = form_data.get(honeypot_field)
    if val and str(val).strip():
        logger.warning(f"Bot detected via honeypot field '{honeypot_field}': value='{val}'")
        return False
    return True


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_address(email: str) -> bool:
    """Validates email format syntax."""
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def sanitize_input_text(text: Optional[str], max_length: int = 5000) -> str:
    """Sanitizes text, strips dangerous script tags, and enforces length bounds."""
    if not text:
        return ""
    clean = text.strip()
    clean = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", clean, flags=re.DOTALL | re.IGNORECASE)
    return clean[:max_length]


class CaptchaVerifier:
    """
    Pluggable CAPTCHA verification foundation (e.g. Cloudflare Turnstile, Google reCAPTCHA).
    Defaults to pass-through in development/standard mode.
    """

    def __init__(self, enabled: bool = False, secret_key: str = ""):
        self.enabled = enabled
        self.secret_key = secret_key

    def verify(self, captcha_response: Optional[str], client_ip: Optional[str] = None) -> bool:
        if not self.enabled:
            return True
        if not captcha_response:
            return False
        # Pluggable HTTP post verification logic for Turnstile or reCAPTCHA
        return True


captcha_verifier = CaptchaVerifier(enabled=False)
