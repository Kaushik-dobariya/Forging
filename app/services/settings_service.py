import json
import re
import urllib.parse
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.setting import SiteSetting, SocialLink, SocialPlatform
from app.core.logging import logger


DEFAULT_SETTINGS = [
    # Contact settings
    ("contact_company_name", "FORGE Precision Engineering Ltd.", "Company Name", "contact"),
    ("contact_address", "Plot 42-45, Heavy Industrial Area, Phase II, Rajkot, Gujarat 360024, India", "Corporate & Plant Address", "contact"),
    ("contact_phone", "+91 281 234 5678", "Primary Phone Number", "contact"),
    ("contact_secondary_phone", "+91 281 234 5679", "Secondary Phone Number", "contact"),
    ("contact_email", "sales@forgingcms.com", "Primary Inquiries Email", "contact"),
    ("contact_support_email", "engineering@forgingcms.com", "Technical Support Email", "contact"),
    ("contact_business_hours", "Monday – Saturday: 08:30 AM – 06:30 PM IST (Plant operates 24/7 in 3 shifts)", "Business & Office Hours", "contact"),
    ("contact_maps_embed_url", "https://maps.google.com/maps?q=Rajkot+Industrial+Area&t=&z=13&ie=UTF8&iwloc=&output=embed", "Google Maps Embed URL", "contact"),
    ("contact_departments_json", json.dumps([
        {"name": "Sales & New Quotations", "email": "rfq@forgingcms.com", "phone": "+91 281 234 5680"},
        {"name": "Metallurgy & Technical Engineering", "email": "engineering@forgingcms.com", "phone": "+91 281 234 5681"},
        {"name": "Quality Assurance & Certifications", "email": "quality@forgingcms.com", "phone": "+91 281 234 5682"},
        {"name": "Export Logistics & Supply Chain", "email": "exports@forgingcms.com", "phone": "+91 281 234 5683"},
    ]), "Corporate Departments List", "contact"),

    # WhatsApp settings
    ("whatsapp_enabled", "true", "Enable or disable global WhatsApp CTA", "whatsapp"),
    ("whatsapp_number", "+91 98765 43210", "WhatsApp Phone Number with Country Code", "whatsapp"),
    ("whatsapp_default_message", "Hello, I am interested in your precision forging and machining capabilities.", "Default WhatsApp message text", "whatsapp"),
    ("whatsapp_allow_header", "true", "Show WhatsApp CTA in header", "whatsapp"),
    ("whatsapp_allow_floating", "true", "Show WhatsApp floating button", "whatsapp"),
    ("whatsapp_allow_product", "true", "Show WhatsApp button on product pages", "whatsapp"),
    ("whatsapp_allow_quote", "true", "Show WhatsApp button on quote page", "whatsapp"),
    ("whatsapp_allow_footer", "true", "Show WhatsApp link in footer", "whatsapp"),
    ("whatsapp_allow_contact", "true", "Show WhatsApp block on contact page", "whatsapp"),
]

DEFAULT_SOCIAL_LINKS = [
    (SocialPlatform.LINKEDIN.value, "https://www.linkedin.com/company/industrial-forging", "linkedin", True, 1),
    (SocialPlatform.FACEBOOK.value, "https://www.facebook.com/industrialforging", "facebook", True, 2),
    (SocialPlatform.X.value, "https://x.com/forging_ind", "twitter", True, 3),
    (SocialPlatform.YOUTUBE.value, "https://www.youtube.com/@industrialforging", "youtube", True, 4),
    (SocialPlatform.INSTAGRAM.value, "https://www.instagram.com/precision_forging", "instagram", True, 5),
    (SocialPlatform.GOOGLE_BUSINESS.value, "https://g.page/industrialforging", "map-pin", True, 6),
]


class WhatsAppConfig:
    """Encapsulates dynamic WhatsApp configuration and CTA generator."""

    def __init__(
        self,
        enabled: bool = True,
        raw_number: str = "",
        default_message: str = "",
        allow_header: bool = True,
        allow_floating: bool = True,
        allow_product: bool = True,
        allow_quote: bool = True,
        allow_footer: bool = True,
        allow_contact: bool = True,
        phone_number: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        allow_product_page: Optional[bool] = None,
        allow_quote_page: Optional[bool] = None,
        allow_contact_page: Optional[bool] = None,
    ):
        self.enabled = is_enabled if is_enabled is not None else enabled
        self.is_enabled = self.enabled
        self.raw_number = phone_number if phone_number is not None else raw_number
        self.phone_number = self.raw_number
        self.clean_number = re.sub(r"[^\d]", "", self.raw_number or "")
        self.default_message = default_message
        self.allow_header = allow_header
        self.allow_floating = allow_floating
        self.allow_product = allow_product_page if allow_product_page is not None else allow_product
        self.allow_product_page = self.allow_product
        self.allow_quote = allow_quote_page if allow_quote_page is not None else allow_quote
        self.allow_quote_page = self.allow_quote
        self.allow_footer = allow_footer
        self.allow_contact = allow_contact_page if allow_contact_page is not None else allow_contact
        self.allow_contact_page = self.allow_contact

    def generate_cta(self, custom_message: Optional[str] = None) -> str:
        """
        Dynamically generates WhatsApp wa.me link with URL-encoded message.
        Returns empty string if WhatsApp is disabled or number is missing.
        """
        if not self.enabled or not self.clean_number:
            return ""
        msg = custom_message if custom_message is not None else self.default_message
        if msg:
            encoded = urllib.parse.quote(msg.strip())
            return f"https://wa.me/{self.clean_number}?text={encoded}"
        return f"https://wa.me/{self.clean_number}"


class SettingsService:
    """Manages CMS site settings, dynamic WhatsApp parameters, and social channels."""

    def get_setting(self, db: Session, key: str, default: str = "") -> str:
        setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
        if setting and setting.value is not None:
            return setting.value
        return default

    def set_setting(self, db: Session, key: str, value: str, description: str = "", group: str = "general") -> SiteSetting:
        setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.group = group
        else:
            setting = SiteSetting(key=key, value=value, description=description, group=group)
            db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

    def get_settings_by_group(self, db: Session, group: str) -> Dict[str, str]:
        settings = db.query(SiteSetting).filter(SiteSetting.group == group).all()
        return {s.key: s.value for s in settings}

    def get_whatsapp_config(self, db: Session) -> WhatsAppConfig:
        """Loads and returns dynamic WhatsApp configuration."""
        group = self.get_settings_by_group(db, "whatsapp")
        enabled = group.get("whatsapp_enabled", "true").lower() == "true"
        raw_number = group.get("whatsapp_number", "+91 98765 43210")
        default_message = group.get(
            "whatsapp_default_message",
            "Hello, I am interested in your precision forging and machining capabilities.",
        )
        return WhatsAppConfig(
            enabled=enabled,
            raw_number=raw_number,
            default_message=default_message,
            allow_header=group.get("whatsapp_allow_header", "true").lower() == "true",
            allow_floating=group.get("whatsapp_allow_floating", "true").lower() == "true",
            allow_product=group.get("whatsapp_allow_product", "true").lower() == "true",
            allow_quote=group.get("whatsapp_allow_quote", "true").lower() == "true",
            allow_footer=group.get("whatsapp_allow_footer", "true").lower() == "true",
            allow_contact=group.get("whatsapp_allow_contact", "true").lower() == "true",
        )

    def get_social_links(self, db: Session, enabled_only: bool = True) -> List[SocialLink]:
        query = db.query(SocialLink)
        if enabled_only:
            query = query.filter(SocialLink.is_enabled == True)
        return query.order_by(SocialLink.display_order.asc(), SocialLink.id.asc()).all()

    def get_contact_info(self, db: Session) -> Dict[str, Any]:
        """Returns structured dictionary of CMS contact information."""
        group = self.get_settings_by_group(db, "contact")
        departments = []
        try:
            raw_deps = group.get("contact_departments_json")
            if raw_deps:
                departments = json.loads(raw_deps)
        except Exception:
            departments = []

        return {
            "company_name": group.get("contact_company_name", "FORGE Precision Engineering Ltd."),
            "address": group.get("contact_address", "Plot 42-45, Heavy Industrial Area, Rajkot, Gujarat, India"),
            "phone": group.get("contact_phone", "+91 281 234 5678"),
            "secondary_phone": group.get("contact_secondary_phone", "+91 281 234 5679"),
            "email": group.get("contact_email", "sales@forgingcms.com"),
            "support_email": group.get("contact_support_email", "engineering@forgingcms.com"),
            "business_hours": group.get("contact_business_hours", "Mon – Sat: 08:30 AM – 06:30 PM IST"),
            "maps_embed_url": group.get("contact_maps_embed_url", ""),
            "departments": departments,
        }

    def seed_defaults(self, db: Session) -> None:
        """Seeds default settings and social links if table is empty."""
        for key, val, desc, grp in DEFAULT_SETTINGS:
            if not db.query(SiteSetting).filter(SiteSetting.key == key).first():
                db.add(SiteSetting(key=key, value=val, description=desc, group=grp))

        for plat, url, icon, enabled, order in DEFAULT_SOCIAL_LINKS:
            if not db.query(SocialLink).filter(SocialLink.platform == plat).first():
                db.add(SocialLink(platform=plat, url=url, icon=icon, is_enabled=enabled, display_order=order))

        db.commit()


settings_service = SettingsService()
