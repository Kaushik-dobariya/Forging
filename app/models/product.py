from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.associations import (
    product_capability_association,
    product_industry_association,
    product_material_association,
    product_equipment_association,
    product_related_association,
)


class MeasurementUnit(Base):
    """
    Configurable measurement unit system for weight, length, capacity, etc.
    Super Admin can add custom units dynamically.
    """
    __tablename__ = "measurement_units"

    name = Column(String(100), nullable=False)
    symbol = Column(String(30), nullable=False, unique=True, index=True)
    unit_type = Column(String(50), nullable=False, index=True)  # weight, length, capacity, etc.
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<MeasurementUnit {self.symbol} ({self.unit_type})>"


class ProductCategory(Base):
    """
    Categorization structure for precision forged components.
    """
    __tablename__ = "product_categories"

    name = Column(String(150), nullable=False)
    slug = Column(String(160), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    image = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # SEO metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(255), nullable=True)

    # Relationships
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ProductCategory id={self.id} slug='{self.slug}'>"


class Product(Base):
    """
    Core industrial forged product item with full manufacturing & engineering attributes.
    """
    __tablename__ = "products"

    name = Column(String(200), nullable=False, index=True)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True)

    # Descriptions & Overview
    short_description = Column(Text, nullable=True)
    detailed_description = Column(Text, nullable=True)
    applications = Column(Text, nullable=True)

    # Engineering & Manufacturing Capabilities
    material = Column(String(255), nullable=True)
    weight_range = Column(String(100), nullable=True)
    dimensions = Column(String(150), nullable=True)
    manufacturing_process = Column(String(255), nullable=True)
    forging_capacity = Column(String(100), nullable=True)
    heat_treatment = Column(String(255), nullable=True)
    machining = Column(String(255), nullable=True)
    surface_finish = Column(String(255), nullable=True)
    testing = Column(Text, nullable=True)
    technical_specifications = Column(Text, nullable=True)

    # Media & Downloads
    featured_image = Column(String(255), nullable=True)
    downloads = Column(String(255), nullable=True)

    # SEO Metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    meta_keywords = Column(String(255), nullable=True)

    # Administration
    status = Column(String(50), default="published", nullable=False, index=True)
    display_order = Column(Integer, default=0, nullable=False)

    # Relationships
    category = relationship("ProductCategory", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.display_order")
    specifications = relationship("ProductSpecification", back_populates="product", cascade="all, delete-orphan", order_by="ProductSpecification.display_order")

    capabilities = relationship("Capability", secondary=product_capability_association, back_populates="products")
    industries = relationship("Industry", secondary=product_industry_association, back_populates="products")
    materials = relationship("Material", secondary=product_material_association, back_populates="products")
    equipment = relationship("Equipment", secondary=product_equipment_association, back_populates="products")

    related_products = relationship(
        "Product",
        secondary=product_related_association,
        primaryjoin="Product.id==product_related_association.c.product_id",
        secondaryjoin="Product.id==product_related_association.c.related_id",
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} slug='{self.slug}'>"


class ProductImage(Base):
    """
    Gallery images associated with a product.
    """
    __tablename__ = "product_images"

    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String(255), nullable=False)
    alt_text = Column(String(255), nullable=True)
    caption = Column(String(255), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="images")


class ProductSpecification(Base):
    """
    Flexible technical specifications table (name, value, unit, display_order).
    """
    __tablename__ = "product_specifications"

    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    value = Column(String(150), nullable=False)
    unit = Column(String(50), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="specifications")

    def __repr__(self) -> str:
        return f"<ProductSpecification {self.name}: {self.value} {self.unit or ''}>"
