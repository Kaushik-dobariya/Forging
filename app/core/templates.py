from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import Request
from fastapi.templating import Jinja2Templates
from app.core.config import settings, BASE_DIR
from app.core.security import generate_csrf_token, verify_session_token
from app.services.spam_protection import generate_public_csrf_token
from app.core.database import SessionLocal


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
templates.env.globals["app_version"] = getattr(settings, "APP_VERSION", "1.0.0")
templates.env.globals["now"] = lambda: datetime.now(timezone.utc)


def get_csrf_token(request: Optional[Request] = None) -> str:
    """Helper to retrieve or generate CSRF token for the current user session."""
    if not request:
        return generate_public_csrf_token("anon")
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        client_ip = request.client.host if request.client else "anon"
        return generate_public_csrf_token(client_ip)
    payload = verify_session_token(token)
    if not payload or "session_id" not in payload:
        client_ip = request.client.host if request.client else "anon"
        return generate_public_csrf_token(client_ip)
    return generate_csrf_token(payload["session_id"])


def get_public_csrf_token(request: Optional[Request] = None) -> str:
    """Helper to generate signed CSRF token for public forms."""
    client_ip = "anon"
    if request and request.client:
        client_ip = request.client.host
    return generate_public_csrf_token(client_ip)


def get_header_menu() -> List[Any]:
    """Retrieves enabled header navigation items with submenus dynamically."""
    try:
        from app.services.menu_service import menu_service
        db = SessionLocal()
        try:
            return menu_service.get_menu_tree(db, location="header", enabled_only=True)
        finally:
            db.close()
    except Exception:
        return []


def get_footer_menu() -> List[Any]:
    """Retrieves enabled footer navigation items dynamically."""
    try:
        from app.services.menu_service import menu_service
        db = SessionLocal()
        try:
            return menu_service.get_menu_tree(db, location="footer", enabled_only=True)
        finally:
            db.close()
    except Exception:
        return []


def get_footer_cms_pages() -> List[Any]:
    """Retrieves published CMS pages configured for footer visibility."""
    try:
        from app.models.page import CMSPage, PageStatus
        db = SessionLocal()
        try:
            return (
                db.query(CMSPage)
                .filter(CMSPage.status == PageStatus.PUBLISHED.value, CMSPage.footer_visibility == True)
                .order_by(CMSPage.display_order.asc(), CMSPage.title.asc())
                .all()
            )
        finally:
            db.close()
    except Exception:
        return []


def get_social_links() -> List[Any]:
    """Retrieves enabled corporate social links dynamically."""
    try:
        from app.services.settings_service import settings_service
        db = SessionLocal()
        try:
            return settings_service.get_social_links(db, enabled_only=True)
        finally:
            db.close()
    except Exception:
        return []


def get_whatsapp_config() -> Any:
    """Retrieves dynamic WhatsApp configuration and CTA generator."""
    try:
        from app.services.settings_service import settings_service
        db = SessionLocal()
        try:
            return settings_service.get_whatsapp_config(db)
        finally:
            db.close()
    except Exception:
        from app.services.settings_service import WhatsAppConfig
        return WhatsAppConfig()


def get_site_settings() -> Dict[str, str]:
    """Retrieves general site settings (company name, version, attribution)."""
    try:
        from app.services.settings_service import settings_service
        db = SessionLocal()
        try:
            return settings_service.get_general_settings(db)
        finally:
            db.close()
    except Exception:
        return {
            "general_website_name": "FORGE Precision Engineering Ltd.",
            "general_company_name": "FORGE Precision Engineering Ltd.",
            "general_app_version": "1.0.0",
            "general_footer_developer_attribution": "Developed by Cubeon Technologies",
            "general_developer_website_url": "https://www.cubeontechs.com/",
            "general_copyright_text": "© 2026 FORGE Precision Engineering Ltd. All rights reserved.",
        }


def get_theme_settings() -> Dict[str, str]:
    """Retrieves active public website theme settings."""
    try:
        from app.services.theme_service import theme_service
        db = SessionLocal()
        try:
            return theme_service.get_public_theme(db)
        finally:
            db.close()
    except Exception:
        from app.services.theme_service import DEFAULT_PUBLIC_THEME
        return dict(DEFAULT_PUBLIC_THEME)


def get_dynamic_theme_css() -> str:
    """Generates dynamic CSS custom properties for public website."""
    try:
        from app.services.theme_service import theme_service
        db = SessionLocal()
        try:
            return theme_service.generate_public_css(db)
        finally:
            db.close()
    except Exception:
        return ""


def get_admin_theme_settings() -> Dict[str, str]:
    """Retrieves active admin panel appearance settings."""
    try:
        from app.services.theme_service import theme_service
        db = SessionLocal()
        try:
            return theme_service.get_admin_theme(db)
        finally:
            db.close()
    except Exception:
        from app.services.theme_service import DEFAULT_ADMIN_THEME
        return dict(DEFAULT_ADMIN_THEME)


def get_dynamic_admin_theme_css() -> str:
    """Generates dynamic CSS custom properties for admin panel."""
    try:
        from app.services.theme_service import theme_service
        db = SessionLocal()
        try:
            return theme_service.generate_admin_css(db)
        finally:
            db.close()
    except Exception:
        return ""


templates.env.globals["get_csrf_token"] = get_csrf_token
templates.env.globals["get_public_csrf_token"] = get_public_csrf_token
templates.env.globals["get_header_menu"] = get_header_menu
templates.env.globals["get_footer_menu"] = get_footer_menu
templates.env.globals["get_footer_cms_pages"] = get_footer_cms_pages
templates.env.globals["get_social_links"] = get_social_links
templates.env.globals["get_whatsapp_config"] = get_whatsapp_config
templates.env.globals["get_site_settings"] = get_site_settings
templates.env.globals["get_theme_settings"] = get_theme_settings
templates.env.globals["get_dynamic_theme_css"] = get_dynamic_theme_css
templates.env.globals["get_admin_theme_settings"] = get_admin_theme_settings
templates.env.globals["get_dynamic_admin_theme_css"] = get_dynamic_admin_theme_css

