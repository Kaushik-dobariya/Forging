from pathlib import Path
from datetime import datetime, timezone
from fastapi import Request
from fastapi.templating import Jinja2Templates
from app.core.config import settings, BASE_DIR
from app.core.security import generate_csrf_token, verify_session_token


TEMPLATES_DIR = BASE_DIR / "app" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Register Global Context Variables
templates.env.globals["app_name"] = settings.APP_NAME
templates.env.globals["app_env"] = settings.APP_ENV
templates.env.globals["app_debug"] = settings.APP_DEBUG
templates.env.globals["site_url"] = settings.SITE_URL
templates.env.globals["session_cookie_name"] = settings.SESSION_COOKIE_NAME
templates.env.globals["session_max_age"] = settings.SESSION_MAX_AGE_SECONDS
templates.env.globals["max_upload_size"] = settings.MAX_UPLOAD_SIZE
templates.env.globals["now"] = lambda: datetime.now(timezone.utc)


def get_csrf_token(request: Request) -> str:
    """Helper to retrieve or generate CSRF token for the current user session."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        return ""
    payload = verify_session_token(token)
    if not payload or "session_id" not in payload:
        return ""
    return generate_csrf_token(payload["session_id"])


templates.env.globals["get_csrf_token"] = get_csrf_token
