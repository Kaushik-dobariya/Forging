import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.core.database import Base


class PageStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class CMSPage(Base):
    """
    Dynamic CMS Page model for custom company pages, policy documentation,
    and hierarchical content (e.g. /about-us, /about-us/company-profile).
    """
    __tablename__ = "cms_pages"

    # Core Content Fields
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    featured_image = Column(String(500), nullable=True)

    # Hierarchy
    parent_id = Column(Integer, ForeignKey("cms_pages.id", ondelete="SET NULL"), nullable=True)

    # Navigation & Placement Settings
    menu_display_name = Column(String(100), nullable=True)
    menu_visibility = Column(Boolean, default=True, nullable=False)
    footer_visibility = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default=PageStatus.PUBLISHED.value, nullable=False)

    # SEO Metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    meta_keywords = Column(String(255), nullable=True)
    canonical_url = Column(String(500), nullable=True)

    # Open Graph Metadata
    og_title = Column(String(255), nullable=True)
    og_description = Column(Text, nullable=True)
    og_image = Column(String(500), nullable=True)

    # Self-referencing Parent/Child Relationship
    parent = relationship(
        "CMSPage",
        remote_side="CMSPage.id",
        backref=backref("children", order_by="CMSPage.display_order.asc()"),
    )

    @property
    def is_published(self) -> bool:
        return self.status == PageStatus.PUBLISHED.value

    @property
    def url_path(self) -> str:
        clean = (self.slug or "").strip("/")
        return f"/{clean}"

    @property
    def effective_menu_title(self) -> str:
        return self.menu_display_name or self.title

    @property
    def effective_meta_title(self) -> str:
        return self.meta_title or self.title

    @property
    def effective_meta_description(self) -> str:
        if self.meta_description:
            return self.meta_description
        # Truncate content preview if meta description is empty
        plain_text = (self.content or "").replace("<p>", " ").replace("</p>", " ")
        import re
        clean_text = re.sub(r"<[^>]+>", "", plain_text).strip()
        return clean_text[:160] if clean_text else self.title

    def __repr__(self) -> str:
        return f"<CMSPage id={self.id} slug='{self.slug}' status='{self.status}'>"
