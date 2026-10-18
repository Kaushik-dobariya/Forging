import json
import re
import urllib.parse
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.setting import SiteSetting, SocialLink, SocialPlatform
from app.models.page import CMSPage, PageStatus
from app.core.config import settings as app_cfg
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
    ("whatsapp_country_code", "+91", "WhatsApp Phone Country Code", "whatsapp"),
    ("whatsapp_number", "+91 98765 43210", "WhatsApp Phone Number with Country Code", "whatsapp"),
    ("whatsapp_label", "Chat on WhatsApp", "WhatsApp Display Label", "whatsapp"),
    ("whatsapp_default_message", "Hello, I am interested in your precision forging and machining capabilities.", "Default WhatsApp message text", "whatsapp"),
    ("whatsapp_position", "floating", "WhatsApp Button Position / Display Location", "whatsapp"),
    ("whatsapp_allow_header", "true", "Show WhatsApp CTA in header", "whatsapp"),
    ("whatsapp_allow_floating", "true", "Show WhatsApp floating button", "whatsapp"),
    ("whatsapp_allow_product", "true", "Show WhatsApp button on product pages", "whatsapp"),
    ("whatsapp_allow_quote", "true", "Show WhatsApp button on quote page", "whatsapp"),
    ("whatsapp_allow_footer", "true", "Show WhatsApp link in footer", "whatsapp"),
    ("whatsapp_allow_contact", "true", "Show WhatsApp block on contact page", "whatsapp"),

    # General Settings
    ("general_website_name", "FORGE Precision Engineering Ltd.", "Website Name", "general"),
    ("general_company_name", "FORGE Precision Engineering Ltd.", "Company Name", "general"),
    ("general_logo_url", "/static/images/logo.png", "Header Logo URL", "general"),
    ("general_favicon_url", "/static/favicon.ico", "Favicon URL", "general"),
    ("general_default_contact_email", "sales@forgingcms.com", "Default Contact Email", "general"),
    ("general_meta_title", "FORGE Precision Engineering — Industrial Forging Solutions", "Default Meta Title", "general"),
    ("general_meta_description", "Leading manufacturer of closed-die forgings, precision machined components, and heavy engineering solutions.", "Default Meta Description", "general"),
    ("general_app_version", "1.0.0", "Application Version", "general"),
    ("general_copyright_text", "© 2026 FORGE Precision Engineering Ltd. All rights reserved.", "Copyright Notice", "general"),
    ("general_footer_developer_attribution", "Developed by Cubeon Technologies", "Footer Developer Attribution", "general"),
    ("general_developer_website_url", "https://www.cubeontechs.com/", "Developer Website URL", "general"),

    # Email Settings
    ("email_contact_receiving", "sales@forgingcms.com", "Receiving email address for contact and inquiries", "email"),
    ("email_sender_name", "FORGE Industrial Forging", "Default sender display name", "email"),
    ("email_from_address", "notifications@forgingcms.com", "Default From email address", "email"),
    ("email_reply_to", "sales@forgingcms.com", "Reply-To email address", "email"),
    ("email_smtp_host", "smtp.gmail.com", "SMTP Host server", "email"),
    ("email_smtp_port", "587", "SMTP Port (587 for TLS, 465 for SSL)", "email"),
    ("email_smtp_username", "", "SMTP Username", "email"),
    ("email_smtp_password", "", "SMTP Password or App Credential", "email"),
    ("email_smtp_encryption", "tls", "SMTP Encryption (tls, ssl, none)", "email"),
    ("email_notifications_enabled", "true", "Enable or disable outbound email dispatch", "email"),
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
        country_code: str = "+91",
        label: str = "Chat on WhatsApp",
        default_message: str = "",
        position: str = "floating",
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
        self.country_code = country_code
        self.label = label
        self.position = position
        self.raw_number = phone_number if phone_number is not None else raw_number
        self.phone_number = self.raw_number
        raw_str = (self.raw_number or "").strip()
        clean_country = re.sub(r"[^\d]", "", self.country_code or "")
        clean_num = re.sub(r"[^\d]", "", raw_str)
        if raw_str.startswith("+") or not clean_country or clean_num.startswith(clean_country):
            self.clean_number = clean_num
        else:
            self.clean_number = f"{clean_country}{clean_num}"
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
    """Manages CMS site settings, dynamic WhatsApp parameters, social channels, and email configuration."""

    PASSWORD_MASK = "••••••••"

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
        country_code = group.get("whatsapp_country_code", "+91")
        label = group.get("whatsapp_label", "Chat on WhatsApp")
        position = group.get("whatsapp_position", "floating")
        default_message = group.get(
            "whatsapp_default_message",
            "Hello, I am interested in your precision forging and machining capabilities.",
        )
        return WhatsAppConfig(
            enabled=enabled,
            raw_number=raw_number,
            country_code=country_code,
            label=label,
            position=position,
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

    def get_social_link_by_id(self, db: Session, link_id: int) -> Optional[SocialLink]:
        return db.query(SocialLink).filter(SocialLink.id == link_id).first()

    def save_social_link(self, db: Session, data: Dict[str, Any], link_id: Optional[int] = None) -> SocialLink:
        if link_id:
            link = self.get_social_link_by_id(db, link_id)
            if not link:
                raise ValueError("Social link not found.")
        else:
            link = SocialLink()
            db.add(link)

        link.platform = data.get("platform", link.platform or "Other")
        link.url = data.get("url", link.url or "")
        link.icon = data.get("icon", link.icon or "globe")
        link.display_order = int(data.get("display_order", link.display_order or 0))
        link.is_enabled = bool(data.get("is_enabled", True))
        link.open_in_new_tab = bool(data.get("open_in_new_tab", True))

        db.commit()
        db.refresh(link)
        return link

    def delete_social_link(self, db: Session, link_id: int) -> bool:
        link = self.get_social_link_by_id(db, link_id)
        if not link:
            return False
        db.delete(link)
        db.commit()
        return True

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

    def get_general_settings(self, db: Session) -> Dict[str, str]:
        defaults = {
            "general_website_name": "FORGE Precision Engineering Ltd.",
            "general_company_name": "FORGE Precision Engineering Ltd.",
            "general_logo_url": "/static/images/logo.png",
            "general_favicon_url": "/static/favicon.ico",
            "general_default_contact_email": "sales@forgingcms.com",
            "general_meta_title": "FORGE Precision Engineering — Industrial Forging Solutions",
            "general_meta_description": "Leading manufacturer of closed-die forgings, precision machined components, and heavy engineering solutions.",
            "general_app_version": app_cfg.APP_VERSION,
            "general_copyright_text": "© 2026 FORGE Precision Engineering Ltd. All rights reserved.",
            "general_footer_developer_attribution": "Developed by Cubeon Technologies",
            "general_developer_website_url": "https://www.cubeontechs.com/",
        }
        group = self.get_settings_by_group(db, "general")
        for k, v in defaults.items():
            if k not in group:
                group[k] = v
        return group

    def get_email_config(self, db: Session, mask_password: bool = True) -> Dict[str, Any]:
        """
        Retrieves dynamic email and SMTP configuration.
        Masks password when requested for frontend and administrative display.
        """
        group = self.get_settings_by_group(db, "email")
        password = group.get("email_smtp_password", "")
        masked_pwd = self.PASSWORD_MASK if password else ""

        return {
            "email_contact_receiving": group.get("email_contact_receiving", "sales@forgingcms.com"),
            "email_sender_name": group.get("email_sender_name", "FORGE Industrial Forging"),
            "email_from_address": group.get("email_from_address", "notifications@forgingcms.com"),
            "email_reply_to": group.get("email_reply_to", "sales@forgingcms.com"),
            "email_smtp_host": group.get("email_smtp_host", "smtp.gmail.com"),
            "email_smtp_port": int(group.get("email_smtp_port", "587")),
            "email_smtp_username": group.get("email_smtp_username", ""),
            "email_smtp_password": masked_pwd if mask_password else password,
            "email_smtp_encryption": group.get("email_smtp_encryption", "tls").lower(),
            "email_notifications_enabled": group.get("email_notifications_enabled", "true").lower() == "true",
            "is_password_set": bool(password),
        }

    def update_email_config(self, db: Session, data: Dict[str, Any]) -> None:
        """
        Updates email configuration while safely preserving password if masked or unchanged.
        """
        keys = [
            ("email_contact_receiving", "email"),
            ("email_sender_name", "email"),
            ("email_from_address", "email"),
            ("email_reply_to", "email"),
            ("email_smtp_host", "email"),
            ("email_smtp_port", "email"),
            ("email_smtp_username", "email"),
            ("email_smtp_encryption", "email"),
            ("email_notifications_enabled", "email"),
        ]
        for key, grp in keys:
            if key in data:
                self.set_setting(db, key, str(data[key]), group=grp)

        new_password = data.get("email_smtp_password", "").strip()
        # Only overwrite password if user provided a new non-masked password
        if new_password and new_password != self.PASSWORD_MASK:
            self.set_setting(db, "email_smtp_password", new_password, group="email")

    def seed_defaults(self, db: Session) -> None:
        """Seeds default settings, social links, CMS pages, and menus."""
        for key, val, desc, grp in DEFAULT_SETTINGS:
            if not db.query(SiteSetting).filter(SiteSetting.key == key).first():
                db.add(SiteSetting(key=key, value=val, description=desc, group=grp))

        for plat, url, icon, enabled, order in DEFAULT_SOCIAL_LINKS:
            if not db.query(SocialLink).filter(SocialLink.platform == plat).first():
                db.add(SocialLink(platform=plat, url=url, icon=icon, is_enabled=enabled, display_order=order, open_in_new_tab=True))

        db.commit()

        # Seed initial dynamic CMS pages if none exist
        if db.query(CMSPage).count() == 0:
            about_page = CMSPage(
                title="About Us",
                slug="about-us",
                menu_display_name="About Us",
                content="<h2>Welcome to FORGE Precision Engineering</h2><p>Since 1988, FORGE Precision Engineering has been a premier manufacturer of high-integrity closed-die forgings and precision machined assemblies for global automotive, aerospace, oil & gas, and heavy machinery industries.</p><p>Equipped with modern hydraulic and pneumatic forging press lines ranging from 1,000T to 6,300T, automated heat-treatment facilities, and state-of-the-art CNC machine shops, we deliver mission-critical forged components with world-class metallurgical properties and dimensional tolerances.</p>",
                status=PageStatus.PUBLISHED.value,
                display_order=1,
                meta_title="About Us — FORGE Precision Engineering",
                meta_description="Learn about FORGE Precision Engineering: over 35 years of engineering excellence, world-class forging presses, and global delivery.",
                menu_visibility=True,
                footer_visibility=True,
            )
            db.add(about_page)
            db.flush()

            child_pages = [
                (
                    "Company Profile",
                    "about-us/company-profile",
                    "<h3>Company Profile & Overview</h3><p>Founded as an engineering workshop in 1988, FORGE has evolved into a global supplier delivering over 45,000 metric tons of precision forgings annually. We operate two advanced manufacturing facilities in Gujarat, India, serving Fortune 500 OEMs across North America, Europe, and Asia-Pacific.</p>",
                    1,
                ),
                (
                    "Vision & Mission",
                    "about-us/vision-mission",
                    "<h3>Our Vision & Mission</h3><p><strong>Vision:</strong> To be the most trusted global engineering partner in closed die forging and precision machined components, recognized for relentless innovation, sustainable metallurgy, and zero-defect quality.</p><p><strong>Mission:</strong> Deliver superior component performance through continuous technological advancement, lean manufacturing, and customer-first engineering collaboration.</p>",
                    2,
                ),
                (
                    "Quality Policy",
                    "about-us/quality-policy",
                    "<h3>Quality Assurance & Management Policy</h3><p>At FORGE, quality is an uncompromised commitment. Operating under ISO 9001:2015, IATF 16949:2016, and AS9100D certifications, our in-house metallurgical and NDT testing laboratories verify chemical composition, mechanical microstructure, and dimensional precision at every manufacturing stage.</p>",
                    3,
                ),
            ]

            for c_title, c_slug, c_content, c_order in child_pages:
                c_page = CMSPage(
                    title=c_title,
                    slug=c_slug,
                    menu_display_name=c_title,
                    content=c_content,
                    parent_id=about_page.id,
                    status=PageStatus.PUBLISHED.value,
                    display_order=c_order,
                    meta_title=f"{c_title} — FORGE Precision Engineering",
                    meta_description=f"Discover {c_title} at FORGE Precision Engineering. World-class industrial forging and manufacturing excellence.",
                    menu_visibility=True,
                    footer_visibility=True,
                )
                db.add(c_page)

            db.commit()
            logger.info("Default CMS pages successfully seeded.")

        # Seed menus via menu_service
        from app.services.menu_service import menu_service
        menu_service.seed_default_menus(db)


settings_service = SettingsService()
