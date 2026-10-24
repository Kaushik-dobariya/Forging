from sqlalchemy import Column, String, Integer, Text, Boolean
from app.core.database import Base


class QualitySection(Base):
    """
    Modular Quality Management & Testing System sections:
    - Quality Policy
    - Quality Management System (QMS)
    - Inspection & Non-Destructive Testing
    - Testing Facilities & Metallurgy Labs
    - Material & Process Traceability
    - Quality Standards & Compliance
    - Quality Assurance Lifecycle Process
    """
    __tablename__ = "quality_sections"

    section_key = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    icon_or_image = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<QualitySection key='{self.section_key}' title='{self.title}'>"


class Certification(Base):
    """
    Industrial certifications, accreditations, and audit approvals
    (ISO 9001:2015, IATF 16949, AS9100D, PED, AD 2000-Merkblatt).
    """
    __tablename__ = "certifications"

    certificate_name = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, index=True, nullable=True)
    issuing_organization = Column(String(150), nullable=True)
    certificate_number = Column(String(100), nullable=True)
    issue_date = Column(String(50), nullable=True)
    expiry_date = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)

    certificate_image = Column(String(255), nullable=True)
    certificate_pdf = Column(String(255), nullable=True)

    # SEO metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)

    display_order = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="published", nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Certification id={self.id} name='{self.certificate_name}'>"
