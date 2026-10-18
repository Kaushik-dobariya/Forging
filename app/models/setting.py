import enum
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Text, Boolean, Integer
from app.core.database import Base


class SocialPlatform(str, enum.Enum):
    LINKEDIN = "LinkedIn"
    INSTAGRAM = "Instagram"
    FACEBOOK = "Facebook"
    YOUTUBE = "YouTube"
    X = "X"
    GOOGLE_BUSINESS = "Google Business"
    CUSTOM = "Custom"


class SiteSetting(Base):
    """
    Key-value system configuration for dynamic contact information, WhatsApp CTA,
    company details, business hours, and department contacts.
    """
    __tablename__ = "site_settings"

    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    group = Column(String(50), default="general", nullable=False)  # contact, whatsapp, general, company, email, footer, seo

    def __repr__(self) -> str:
        return f"<SiteSetting key='{self.key}' group='{self.group}'>"


class SocialLink(Base):
    """
    Corporate social media profiles and channels.
    """
    __tablename__ = "social_links"

    platform = Column(String(50), nullable=False)
    url = Column(String(500), nullable=False)
    icon = Column(String(100), nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    open_in_new_tab = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<SocialLink platform='{self.platform}' enabled={self.is_enabled}>"
