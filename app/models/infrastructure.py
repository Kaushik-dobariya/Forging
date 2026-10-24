from sqlalchemy import Column, String, Integer, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.associations import (
    product_equipment_association,
    capability_equipment_association,
)


class Facility(Base):
    """
    Manufacturing facilities, plants, and workshop areas.
    """
    __tablename__ = "facilities"

    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=True)  # Forge Shop, Heat Treatment, Machining, Lab
    description = Column(Text, nullable=True)
    capacity = Column(String(150), nullable=True)
    specifications = Column(Text, nullable=True)
    image = Column(String(255), nullable=True)
    gallery_json = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="published", nullable=False)

    def __repr__(self) -> str:
        return f"<Facility id={self.id} name='{self.name}'>"


class InfrastructureGallery(Base):
    """
    Curated infrastructure photo and media gallery showcase.
    """
    __tablename__ = "infrastructure_gallery"

    title = Column(String(200), nullable=False)
    category = Column(String(100), nullable=True)  # Heavy Machinery, Shop Floor, Quality Lab
    image_url = Column(String(255), nullable=False)
    caption = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<InfrastructureGallery id={self.id} title='{self.title}'>"


class Equipment(Base):
    """
    Manufacturing machinery & equipment (Hydraulic Presses, CNC VMCs, Furnaces, Spectrometers, UT Machines).
    """
    __tablename__ = "equipment"

    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=True, index=True)
    manufacturer = Column(String(150), nullable=True)
    model = Column(String(100), nullable=True)
    capacity = Column(String(150), nullable=True)
    specifications = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    slug = Column(String(220), unique=True, index=True, nullable=True)
    image = Column(String(255), nullable=True)
    gallery_json = Column(Text, nullable=True)
    pdf_url = Column(String(255), nullable=True)
    status = Column(String(50), default="published", nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    # SEO metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)

    # Relationships
    products = relationship("Product", secondary=product_equipment_association, back_populates="equipment")
    capabilities = relationship("Capability", secondary=capability_equipment_association, back_populates="equipment")

    def __repr__(self) -> str:
        return f"<Equipment id={self.id} name='{self.name}'>"
