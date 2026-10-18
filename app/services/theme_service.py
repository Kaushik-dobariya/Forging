import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.setting import SiteSetting
from app.core.logging import logger

HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
FONT_SIZE_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?(?:px|rem|em|%)?$")
LINE_HEIGHT_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?(?:px|rem|em|%)?$")
LETTER_SPACING_PATTERN = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?(?:px|rem|em)?$|^normal$")
SAFE_FONT_PATTERN = re.compile(r"^[a-zA-Z0-9\s,\'\"\-_]+$")


DEFAULT_PUBLIC_THEME: Dict[str, str] = {
    # 2.1 Colors
    "theme_color_primary": "#17212B",
    "theme_color_secondary": "#28323C",
    "theme_color_accent": "#B7793F",
    "theme_color_background": "#F5F4F0",
    "theme_color_section_bg": "#FFFFFF",
    "theme_color_card_surface": "#FFFFFF",
    "theme_color_text_primary": "#17212B",
    "theme_color_text_secondary": "#5B6470",
    "theme_color_heading": "#17212B",
    "theme_color_link": "#B7793F",
    "theme_color_link_hover": "#965F2D",
    "theme_color_button_bg": "#B7793F",
    "theme_color_button_text": "#FFFFFF",
    "theme_color_button_hover": "#965F2D",
    "theme_color_border": "#D9DDE1",
    "theme_color_header_bg": "#17212B",
    "theme_color_header_text": "#FFFFFF",
    "theme_color_header_link": "#F5F4F0",
    "theme_color_footer_bg": "#17212B",
    "theme_color_footer_heading": "#FFFFFF",
    "theme_color_footer_text": "#8E9BA8",
    "theme_color_footer_link": "#B7793F",
    "theme_color_footer_link_hover": "#FFFFFF",
    "theme_color_form_bg": "#FFFFFF",
    "theme_color_form_border": "#D9DDE1",
    "theme_color_input_text": "#17212B",
    "theme_color_input_placeholder": "#8E9BA8",

    # 2.2 Typography (Aptos Default)
    "theme_font_family_base": "Aptos, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif",
    "theme_font_family_heading": "Aptos, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif",
    "theme_font_family_body": "Aptos, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif",
    "theme_font_size_base": "16px",
    "theme_font_size_small": "14px",
    "theme_font_size_medium": "16px",
    "theme_font_size_large": "18px",
    "theme_font_size_h1": "2.75rem",
    "theme_font_size_h2": "2.15rem",
    "theme_font_size_h3": "1.65rem",
    "theme_font_size_h4": "1.35rem",
    "theme_font_size_h5": "1.15rem",
    "theme_font_size_h6": "1.0rem",
    "theme_font_size_paragraph": "1rem",
    "theme_font_size_nav": "0.925rem",
    "theme_font_size_button": "0.9rem",
    "theme_font_size_footer": "0.875rem",
    "theme_line_height": "1.6",
    "theme_font_weight_normal": "400",
    "theme_font_weight_heading": "700",
    "theme_letter_spacing": "-0.01em",
}

DEFAULT_ADMIN_THEME: Dict[str, str] = {
    "admin_theme_primary_color": "#111827",
    "admin_theme_sidebar_bg": "#111827",
    "admin_theme_sidebar_text": "#94A3B8",
    "admin_theme_sidebar_active_bg": "#1F2937",
    "admin_theme_sidebar_active_text": "#FFFFFF",
    "admin_theme_topbar_bg": "#FFFFFF",
    "admin_theme_topbar_text": "#0F172A",
    "admin_theme_content_bg": "#F8FAFC",
    "admin_theme_card_bg": "#FFFFFF",
    "admin_theme_border_color": "#E2E8F0",
    "admin_theme_button_primary_bg": "#B7793F",
    "admin_theme_button_text": "#FFFFFF",
    "admin_theme_accent_color": "#B7793F",
    "admin_theme_font_family": "Aptos, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif",
    "admin_theme_base_font_size": "15px",
}


class ThemeService:
    """
    Centralized theme management service for public website and independent admin panel appearance.
    Provides database persistence, sanitization against XSS/injection, and dynamic CSS generation.
    """

    def validate_color(self, val: str, fallback: str) -> str:
        """Validates that a color string is a valid hex color code."""
        if not val:
            return fallback
        clean = val.strip()
        if HEX_COLOR_PATTERN.match(clean):
            return clean
        return fallback

    def validate_font_family(self, val: str, fallback: str) -> str:
        """Validates that a font family declaration is safe from injection."""
        if not val:
            return fallback
        clean = val.strip()
        if SAFE_FONT_PATTERN.match(clean) and len(clean) < 150:
            return clean
        return fallback

    def validate_dimension(self, val: str, fallback: str) -> str:
        """Validates a CSS size/dimension value (e.g. 16px, 1.5rem)."""
        if not val:
            return fallback
        clean = val.strip().lower()
        if FONT_SIZE_PATTERN.match(clean):
            return clean
        return fallback

    def get_public_theme(self, db: Session) -> Dict[str, str]:
        """Retrieves active public website theme settings merged with defaults."""
        theme = dict(DEFAULT_PUBLIC_THEME)
        try:
            settings_rows = db.query(SiteSetting).filter(SiteSetting.group == "theme").all()
            for row in settings_rows:
                if row.key in theme and row.value is not None:
                    theme[row.key] = row.value
        except Exception as exc:
            logger.error(f"Error loading public theme settings: {exc}")
        return theme

    def save_public_theme(self, db: Session, form_data: Dict[str, Any]) -> Dict[str, str]:
        """Saves and validates public website theme settings to the database."""
        current = self.get_public_theme(db)
        for key in DEFAULT_PUBLIC_THEME:
            if key in form_data:
                raw_val = str(form_data[key]).strip()
                # Apply validation based on key prefix/name
                if "color" in key:
                    clean_val = self.validate_color(raw_val, DEFAULT_PUBLIC_THEME[key])
                elif "font_family" in key:
                    clean_val = self.validate_font_family(raw_val, DEFAULT_PUBLIC_THEME[key])
                elif "font_size" in key:
                    clean_val = self.validate_dimension(raw_val, DEFAULT_PUBLIC_THEME[key])
                elif "line_height" in key:
                    clean_val = raw_val if LINE_HEIGHT_PATTERN.match(raw_val) else DEFAULT_PUBLIC_THEME[key]
                elif "letter_spacing" in key:
                    clean_val = raw_val if LETTER_SPACING_PATTERN.match(raw_val) else DEFAULT_PUBLIC_THEME[key]
                elif "weight" in key:
                    clean_val = raw_val if raw_val.isdigit() and 100 <= int(raw_val) <= 900 else DEFAULT_PUBLIC_THEME[key]
                else:
                    clean_val = raw_val[:100]

                # Update or create SiteSetting
                setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
                if setting:
                    setting.value = clean_val
                    setting.group = "theme"
                else:
                    db.add(SiteSetting(key=key, value=clean_val, description=f"Theme: {key}", group="theme"))
                current[key] = clean_val

        db.commit()
        logger.info("Saved public website theme customization.")
        return current

    def reset_public_theme(self, db: Session) -> Dict[str, str]:
        """Resets all public website theme settings to factory default values."""
        try:
            db.query(SiteSetting).filter(SiteSetting.group == "theme").delete()
            db.commit()
            logger.info("Reset public website theme to defaults.")
        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to reset public theme: {exc}")
        return dict(DEFAULT_PUBLIC_THEME)

    def get_admin_theme(self, db: Session) -> Dict[str, str]:
        """Retrieves independent admin panel appearance settings merged with defaults."""
        admin_theme = dict(DEFAULT_ADMIN_THEME)
        try:
            settings_rows = db.query(SiteSetting).filter(SiteSetting.group == "admin_theme").all()
            for row in settings_rows:
                if row.key in admin_theme and row.value is not None:
                    admin_theme[row.key] = row.value
        except Exception as exc:
            logger.error(f"Error loading admin appearance settings: {exc}")
        return admin_theme

    def save_admin_theme(self, db: Session, form_data: Dict[str, Any]) -> Dict[str, str]:
        """Saves independent admin panel appearance settings."""
        current = self.get_admin_theme(db)
        for key in DEFAULT_ADMIN_THEME:
            if key in form_data:
                raw_val = str(form_data[key]).strip()
                if "color" in key or "bg" in key or "text" in key:
                    clean_val = self.validate_color(raw_val, DEFAULT_ADMIN_THEME[key])
                elif "font_family" in key:
                    clean_val = self.validate_font_family(raw_val, DEFAULT_ADMIN_THEME[key])
                elif "size" in key:
                    clean_val = self.validate_dimension(raw_val, DEFAULT_ADMIN_THEME[key])
                else:
                    clean_val = raw_val[:100]

                setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
                if setting:
                    setting.value = clean_val
                    setting.group = "admin_theme"
                else:
                    db.add(SiteSetting(key=key, value=clean_val, description=f"Admin: {key}", group="admin_theme"))
                current[key] = clean_val

        db.commit()
        logger.info("Saved admin panel appearance customization.")
        return current

    def reset_admin_theme(self, db: Session) -> Dict[str, str]:
        """Resets admin panel appearance to default values."""
        try:
            db.query(SiteSetting).filter(SiteSetting.group == "admin_theme").delete()
            db.commit()
            logger.info("Reset admin appearance to defaults.")
        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to reset admin theme: {exc}")
        return dict(DEFAULT_ADMIN_THEME)

    def generate_public_css(self, db: Session) -> str:
        """
        Generates dynamic CSS custom properties for public website rendering.
        Overrides default tokens without requiring source-file modifications.
        """
        theme = self.get_public_theme(db)
        return f"""
/* Generated Dynamic Theme Tokens - Forging CMS */
:root {{
  --color-primary: {theme['theme_color_primary']};
  --color-primary-light: {theme['theme_color_secondary']};
  --color-secondary: {theme['theme_color_secondary']};
  --color-accent: {theme['theme_color_accent']};
  --color-accent-light: {theme['theme_color_button_hover']};
  --color-accent-dark: {theme['theme_color_link_hover']};
  --color-accent-glow: rgba(183, 121, 63, 0.2);

  --color-background: {theme['theme_color_background']};
  --color-surface: {theme['theme_color_card_surface']};
  --color-surface-subtle: {theme['theme_color_background']};
  --color-surface-elevated: {theme['theme_color_card_surface']};
  --section-bg-alternate: {theme['theme_color_section_bg']};

  --color-text: {theme['theme_color_text_primary']};
  --color-text-muted: {theme['theme_color_text_secondary']};
  --color-heading: {theme['theme_color_heading']};
  --color-border: {theme['theme_color_border']};
  --color-border-subtle: {theme['theme_color_border']};

  --theme-link: {theme['theme_color_link']};
  --theme-link-hover: {theme['theme_color_link_hover']};
  --theme-btn-bg: {theme['theme_color_button_bg']};
  --theme-btn-text: {theme['theme_color_button_text']};
  --theme-btn-hover: {theme['theme_color_button_hover']};

  --theme-header-bg: {theme['theme_color_header_bg']};
  --theme-header-text: {theme['theme_color_header_text']};
  --theme-header-link: {theme['theme_color_header_link']};

  --theme-footer-bg: {theme['theme_color_footer_bg']};
  --theme-footer-heading: {theme['theme_color_footer_heading']};
  --theme-footer-text: {theme['theme_color_footer_text']};
  --theme-footer-link: {theme['theme_color_footer_link']};
  --theme-footer-link-hover: {theme['theme_color_footer_link_hover']};

  --theme-form-bg: {theme['theme_color_form_bg']};
  --theme-form-border: {theme['theme_color_form_border']};
  --theme-input-text: {theme['theme_color_input_text']};
  --theme-input-placeholder: {theme['theme_color_input_placeholder']};

  --font-family-base: {theme['theme_font_family_base']};
  --font-family-heading: {theme['theme_font_family_heading']};
  --font-family-body: {theme['theme_font_family_body']};
  --font-sans: var(--font-family-base);
  --font-heading: var(--font-family-heading);
  --font-body: var(--font-family-body);

  --font-size-base: {theme['theme_font_size_base']};
  --font-size-small: {theme['theme_font_size_small']};
  --font-size-medium: {theme['theme_font_size_medium']};
  --font-size-large: {theme['theme_font_size_large']};
  --font-size-h1: {theme['theme_font_size_h1']};
  --font-size-h2: {theme['theme_font_size_h2']};
  --font-size-h3: {theme['theme_font_size_h3']};
  --font-size-h4: {theme['theme_font_size_h4']};
  --font-size-h5: {theme['theme_font_size_h5']};
  --font-size-h6: {theme['theme_font_size_h6']};
  --font-size-paragraph: {theme['theme_font_size_paragraph']};
  --font-size-nav: {theme['theme_font_size_nav']};
  --font-size-button: {theme['theme_font_size_button']};
  --font-size-footer: {theme['theme_font_size_footer']};
  --line-height-base: {theme['theme_line_height']};
  --letter-spacing-base: {theme['theme_letter_spacing']};
}}

body {{
  font-family: var(--font-family-base) !important;
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
  letter-spacing: var(--letter-spacing-base);
  color: var(--color-text);
  background-color: var(--color-background);
}}

h1, h2, h3, h4, h5, h6, .hero-title, .page-title, .section-title {{
  font-family: var(--font-family-heading) !important;
  color: var(--color-heading);
}}

h1, .hero-title {{ font-size: var(--font-size-h1); }}
h2, .page-title, .section-title {{ font-size: var(--font-size-h2); }}
h3 {{ font-size: var(--font-size-h3); }}
h4 {{ font-size: var(--font-size-h4); }}
h5 {{ font-size: var(--font-size-h5); }}
h6 {{ font-size: var(--font-size-h6); }}

p, .page-subtitle, .feature-desc {{
  font-size: var(--font-size-paragraph);
}}

.site-header {{
  background-color: var(--theme-header-bg) !important;
}}

.site-header .brand-logo,
.site-header .nav-link {{
  color: var(--theme-header-link) !important;
  font-size: var(--font-size-nav);
}}

.site-header .nav-link:hover {{
  color: var(--color-accent) !important;
}}

.site-footer {{
  background-color: var(--theme-footer-bg) !important;
  color: var(--theme-footer-text) !important;
  font-size: var(--font-size-footer);
}}

.site-footer .footer-heading {{
  color: var(--theme-footer-heading) !important;
}}

.site-footer a {{
  color: var(--theme-footer-link) !important;
}}

.site-footer a:hover {{
  color: var(--theme-footer-link-hover) !important;
}}

.btn-accent, .btn-primary {{
  background-color: var(--theme-btn-bg) !important;
  color: var(--theme-btn-text) !important;
  border-color: var(--theme-btn-bg) !important;
  font-size: var(--font-size-button);
}}

.btn-accent:hover, .btn-primary:hover {{
  background-color: var(--theme-btn-hover) !important;
  border-color: var(--theme-btn-hover) !important;
}}

.form-control, .form-select, input[type="text"], input[type="email"], textarea {{
  background-color: var(--theme-form-bg) !important;
  border-color: var(--theme-form-border) !important;
  color: var(--theme-input-text) !important;
}}

.form-control::placeholder, textarea::placeholder {{
  color: var(--theme-input-placeholder) !important;
}}
"""

    def generate_admin_css(self, db: Session) -> str:
        """
        Generates dynamic CSS custom properties for independent admin panel appearance.
        """
        adm = self.get_admin_theme(db)
        return f"""
/* Generated Dynamic Admin Appearance - Forging CMS */
:root {{
  --admin-sidebar-bg: {adm['admin_theme_sidebar_bg']};
  --admin-sidebar-surface: {adm['admin_theme_sidebar_active_bg']};
  --admin-sidebar-border: {adm['admin_theme_border_color']};
  --admin-sidebar-text: {adm['admin_theme_sidebar_text']};
  --admin-sidebar-text-hover: #FFFFFF;
  --admin-sidebar-text-active: {adm['admin_theme_sidebar_active_text']};
  --admin-sidebar-accent: {adm['admin_theme_accent_color']};

  --admin-topbar-bg: {adm['admin_theme_topbar_bg']};
  --admin-text-primary: {adm['admin_theme_topbar_text']};

  --admin-bg: {adm['admin_theme_content_bg']};
  --admin-surface: {adm['admin_theme_card_bg']};
  --admin-surface-elevated: {adm['admin_theme_card_bg']};
  --admin-border: {adm['admin_theme_border_color']};
  --admin-accent: {adm['admin_theme_accent_color']};
  --admin-accent-hover: {adm['admin_theme_button_primary_bg']};

  --admin-btn-primary-bg: {adm['admin_theme_button_primary_bg']};
  --admin-btn-primary-text: {adm['admin_theme_button_text']};

  --font-sans: {adm['admin_theme_font_family']} !important;
  --font-family-base: {adm['admin_theme_font_family']} !important;
  --font-family-heading: {adm['admin_theme_font_family']} !important;
  --admin-base-font-size: {adm['admin_theme_base_font_size']};
}}

.admin-layout, .admin-sidebar, .admin-main, .admin-card, .table, body {{
  font-family: var(--font-sans) !important;
  font-size: var(--admin-base-font-size);
}}

.admin-sidebar {{
  background-color: var(--admin-sidebar-bg) !important;
}}

.admin-nav-link {{
  color: var(--admin-sidebar-text) !important;
}}

.admin-nav-link.active, .admin-nav-link:hover {{
  background-color: var(--admin-sidebar-surface) !important;
  color: var(--admin-sidebar-text-active) !important;
}}

.admin-header {{
  background-color: var(--admin-topbar-bg) !important;
}}

.admin-main {{
  background-color: var(--admin-bg) !important;
}}

.admin-card {{
  background-color: var(--admin-surface) !important;
  border-color: var(--admin-border) !important;
}}

.btn-primary, .btn-accent {{
  background-color: var(--admin-btn-primary-bg) !important;
  color: var(--admin-btn-primary-text) !important;
  border-color: var(--admin-btn-primary-bg) !important;
}}
"""


theme_service = ThemeService()
