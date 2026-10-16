from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.associations import (
    product_material_association,
    capability_material_association,
)


class Material(Base):
    """
    Forging materials, alloys, chemical compositions, and mechanical property grades.
    """
    __tablename__ = "materials"

    name = Column(String(150), nullable=False)
    slug = Column(String(170), unique=True, index=True, nullable=False)
    grade = Column(String(150), nullable=True)
    standard = Column(String(150), nullable=True)  # ASTM, EN, DIN, IS, JIS

    chemical_composition = Column(Text, nullable=True)
    mechanical_properties = Column(Text, nullable=True)
    applications = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    image = Column(String(255), nullable=True)
    documents_url = Column(String(255), nullable=True)

    # SEO metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(255), nullable=True)

    display_order = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="published", nullable=False, index=True)

    # Relationships
    products = relationship("Product", secondary=product_material_association, back_populates="materials")
    capabilities = relationship("Capability", secondary=capability_material_association, back_populates="materials")

    def __repr__(self) -> str:
        return f"<Material id={self.id} slug='{self.slug}'>"
