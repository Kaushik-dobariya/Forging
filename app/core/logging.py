import logging
import re
import sys
from typing import Any
from app.core.config import settings


SENSITIVE_PATTERNS = [
    re.compile(r'(password["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE),
    re.compile(r'(secret["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE),
    re.compile(r'(token["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE),
    re.compile(r'(authorization["\']?\s*[:=]\s*["\']?Bearer\s+)([^"\s]+)', re.IGNORECASE),
    re.compile(r'(cookie["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE),
]


class SanitizedFormatter(logging.Formatter):
    """
    Custom log formatter that scrubs sensitive fields like passwords, tokens,
    and secrets from all log output.
    """

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(r'\1[REDACTED]\3' if r'\3' in pattern.pattern else r'\1[REDACTED]', sanitized)
        return sanitized


def setup_logging() -> None:
    """Configures structured, sanitized logging for the entire application."""
    log_level = logging.DEBUG if settings.APP_DEBUG else logging.INFO

    formatter = SanitizedFormatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on reload
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.APP_DEBUG else logging.INFO)


logger = logging.getLogger("forging_cms")
