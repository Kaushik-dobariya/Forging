from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.associations import (
    product_capability_association,
    capability_equipment_association,
    capability_material_association,
    capability_industry_association,
)


class Capability(Base):
    """
    Industrial forging, heat treatment, machining, and engineering capabilities.
    """
    __tablename__ = "capabilities"

    title = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    short_description = Column(Text, nullable=True)
    detailed_description = Column(Text, nullable=True)

    hero_image = Column(String(255), nullable=True)
    gallery_json = Column(Text, nullable=True)  # JSON-encoded array of image paths

    process = Column(Text, nullable=True)
    equipment_description = Column(Text, nullable=True)
    materials_description = Column(Text, nullable=True)
    dimensions = Column(String(150), nullable=True)
    capacity = Column(String(150), nullable=True)
    technical_specifications = Column(Text, nullable=True)
    applications = Column(Text, nullable=True)
    faqs_json = Column(Text, nullable=True)  # JSON-encoded array of {question, answer}

    # SEO metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(255), nullable=True)

    display_order = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="published", nullable=False, index=True)

    # Relationships
    products = relationship("Product", secondary=product_capability_association, back_populates="capabilities")
    equipment = relationship("Equipment", secondary=capability_equipment_association, back_populates="capabilities")
    materials = relationship("Material", secondary=capability_material_association, back_populates="capabilities")
    industries = relationship("Industry", secondary=capability_industry_association, back_populates="capabilities")

    def __repr__(self) -> str:
        return f"<Capability id={self.id} slug='{self.slug}'>"
