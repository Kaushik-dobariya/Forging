from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.associations import (
    product_industry_association,
    capability_industry_association,
)


class Industry(Base):
    """
    Sectors and markets served by precision forged components (Automotive, Aerospace, Oil & Gas, etc.)
    """
    __tablename__ = "industries"

    name = Column(String(150), nullable=False)
    slug = Column(String(170), unique=True, index=True, nullable=False)
    short_description = Column(Text, nullable=True)
    detailed_description = Column(Text, nullable=True)

    hero_image = Column(String(255), nullable=True)
    icon_image = Column(String(255), nullable=True)
    key_components = Column(Text, nullable=True)
    gallery_json = Column(Text, nullable=True)

    # SEO metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(255), nullable=True)

    display_order = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="published", nullable=False, index=True)

    # Relationships
    products = relationship("Product", secondary=product_industry_association, back_populates="industries")
    capabilities = relationship("Capability", secondary=capability_industry_association, back_populates="industries")

    def __repr__(self) -> str:
        return f"<Industry id={self.id} slug='{self.slug}'>"
