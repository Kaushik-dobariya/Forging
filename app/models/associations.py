from sqlalchemy import Table, Column, Integer, ForeignKey
from app.core.database import Base

# Products <-> Capabilities
product_capability_association = Table(
    "product_capability_association",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("capability_id", Integer, ForeignKey("capabilities.id", ondelete="CASCADE"), primary_key=True),
)

# Products <-> Industries
product_industry_association = Table(
    "product_industry_association",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industries.id", ondelete="CASCADE"), primary_key=True),
)

# Products <-> Materials
product_material_association = Table(
    "product_material_association",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", Integer, ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True),
)

# Products <-> Equipment
product_equipment_association = Table(
    "product_equipment_association",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("equipment_id", Integer, ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True),
)

# Capabilities <-> Equipment
capability_equipment_association = Table(
    "capability_equipment_association",
    Base.metadata,
    Column("capability_id", Integer, ForeignKey("capabilities.id", ondelete="CASCADE"), primary_key=True),
    Column("equipment_id", Integer, ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True),
)

# Capabilities <-> Materials
capability_material_association = Table(
    "capability_material_association",
    Base.metadata,
    Column("capability_id", Integer, ForeignKey("capabilities.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", Integer, ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True),
)

# Capabilities <-> Industries
capability_industry_association = Table(
    "capability_industry_association",
    Base.metadata,
    Column("capability_id", Integer, ForeignKey("capabilities.id", ondelete="CASCADE"), primary_key=True),
    Column("industry_id", Integer, ForeignKey("industries.id", ondelete="CASCADE"), primary_key=True),
)

# Products <-> Related Products (Self-referential M2M)
product_related_association = Table(
    "product_related_association",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("related_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)
