from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base


class HeroSlide(Base):
    """
    CMS-driven hero slide for the public homepage carousel.
    Supports industrial photography, custom text alignment, overlay opacity, and dual CTAs.
    """
    __tablename__ = "hero_slides"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    subtitle = Column(Text, nullable=True)
    eyebrow = Column(String(150), nullable=True)
    background_image = Column(String(500), nullable=False)
    foreground_image = Column(String(500), nullable=True)
    primary_cta_label = Column(String(100), nullable=True)
    primary_cta_url = Column(String(500), nullable=True)
    secondary_cta_label = Column(String(100), nullable=True)
    secondary_cta_url = Column(String(500), nullable=True)
    text_align = Column(String(20), default="left", nullable=False)  # left, center, right
    overlay_opacity = Column(Integer, default=65, nullable=False)    # 0 to 100
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    image_alt = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def background_image_url(self) -> str:
        return self.background_image

    @property
    def text_alignment(self) -> str:
        return self.text_align

    @property
    def alt_text(self) -> str:
        return self.image_alt or self.title

    @property
    def overlay_opacity_decimal(self) -> float:
        if self.overlay_opacity is None:
            return 0.65
        return self.overlay_opacity / 100.0 if self.overlay_opacity > 1 else float(self.overlay_opacity)

    def __repr__(self) -> str:
        return f"<HeroSlide id={self.id} title='{self.title[:30]}' active={self.is_active}>"

