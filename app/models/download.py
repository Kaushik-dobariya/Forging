import enum
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class DownloadCategory(str, enum.Enum):
    BROCHURE = "brochure"
    TECHNICAL_DOCUMENT = "technical document"
    PRODUCT_DRAWING = "product drawing"
    CERTIFICATE = "certificate"
    CATALOG = "catalog"
    PDF = "PDF"
    OTHER = "other document"


class DownloadVisibility(str, enum.Enum):
    PUBLIC = "public"
    GATED = "gated"
    PRIVATE = "private"


class DownloadResource(Base):
    """
    Downloadable asset and technical documentation repository.
    Supports brochures, technical documents, drawings, catalogs, and certificates.
    """
    __tablename__ = "download_resources"

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), default="PDF", nullable=False)  # PDF, DWG, STEP, ZIP, etc.
    file_size_bytes = Column(Integer, default=0, nullable=False)
    category = Column(String(100), default=DownloadCategory.BROCHURE.value, nullable=False)
    related_product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    related_capability_id = Column(Integer, ForeignKey("capabilities.id", ondelete="SET NULL"), nullable=True)
    visibility = Column(String(50), default=DownloadVisibility.PUBLIC.value, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)

    # Relationships
    product = relationship("Product", foreign_keys=[related_product_id])
    capability = relationship("Capability", foreign_keys=[related_capability_id])

    def __init__(self, **kwargs):
        if "file_name" in kwargs:
            fn = kwargs.pop("file_name")
            if "file_path" not in kwargs:
                kwargs["file_path"] = f"/uploads/downloads/{fn}"
        if "file_size" in kwargs and "file_size_bytes" not in kwargs:
            kwargs["file_size_bytes"] = kwargs.pop("file_size")
        if "file" in kwargs and "file_path" not in kwargs:
            kwargs["file_path"] = kwargs.pop("file")
        super().__init__(**kwargs)

    @property
    def file_name(self) -> str:
        return self.file_path.split("/")[-1] if self.file_path else ""

    @file_name.setter
    def file_name(self, value: str):
        if not self.file_path:
            self.file_path = f"/uploads/downloads/{value}"

    @property
    def file_size(self) -> int:
        return self.file_size_bytes

    @file_size.setter
    def file_size(self, value: int):
        self.file_size_bytes = value

    @property
    def file(self) -> str:
        return self.file_path

    @file.setter
    def file(self, value: str):
        self.file_path = value

    @property
    def formatted_size(self) -> str:
        """Returns human-readable file size."""
        if self.file_size_bytes < 1024:
            return f"{self.file_size_bytes} B"
        elif self.file_size_bytes < 1024 * 1024:
            return f"{self.file_size_bytes / 1024:.1f} KB"
        else:
            return f"{self.file_size_bytes / (1024 * 1024):.1f} MB"

    def __repr__(self) -> str:
        return f"<DownloadResource id={self.id} title='{self.title}' category='{self.category}'>"

