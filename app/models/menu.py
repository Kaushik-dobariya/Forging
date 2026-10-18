import enum
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.core.database import Base


class MenuLocation(str, enum.Enum):
    HEADER = "header"
    FOOTER = "footer"


class MenuItem(Base):
    """
    Dynamic navigation menu item for website header and footer menus.
    Supports multi-level submenus, custom URLs, CMS page binding,
    display ordering, open in new tab, and visibility toggles.
    """
    __tablename__ = "menu_items"

    title = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    page_id = Column(Integer, ForeignKey("cms_pages.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=True)
    location = Column(String(50), default=MenuLocation.HEADER.value, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    target = Column(String(20), default="_self", nullable=False)  # _self or _blank

    # Relationships
    page = relationship("CMSPage", foreign_keys=[page_id], lazy="joined")
    parent = relationship(
        "MenuItem",
        remote_side="MenuItem.id",
        foreign_keys=[parent_id],
        backref=backref("children", cascade="all, delete-orphan", order_by="MenuItem.display_order.asc()"),
    )

    @property
    def effective_url(self) -> str:
        """Returns linked CMS page URL if bound, otherwise custom URL."""
        try:
            if self.page_id and self.page:
                return self.page.url_path
        except Exception:
            pass
        return self.url or "#"

    @property
    def is_external(self) -> bool:
        return self.url.startswith("http://") or self.url.startswith("https://")

    def __repr__(self) -> str:
        return f"<MenuItem id={self.id} title='{self.title}' url='{self.url}' location='{self.location}'>"
