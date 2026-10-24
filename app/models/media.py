from sqlalchemy import Column, String, Integer, Text, DateTime
from app.core.database import Base


class MediaAsset(Base):
    """
    Enterprise Media Asset library model supporting SEO metadata,
    optimized modern formats (WebP), and responsive thumbnails.
    """
    __tablename__ = "media_assets"

    filename = Column(String(255), nullable=False)
    seo_filename = Column(String(255), nullable=False, index=True)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)        # e.g. /uploads/media/crankshaft_abc123.jpg
    webp_path = Column(String(500), nullable=True)         # e.g. /uploads/media/crankshaft_abc123.webp
    thumbnail_path = Column(String(500), nullable=True)    # e.g. /uploads/media/thumb_crankshaft_abc123.webp
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # SEO & Accessibility Attributes
    alt_text = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    caption = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="general", nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<MediaAsset id={self.id} seo_filename='{self.seo_filename}'>"
