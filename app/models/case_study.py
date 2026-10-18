import json
from typing import List, Dict, Any
from sqlalchemy import Column, String, Text, Integer
from app.core.database import Base


class CaseStudy(Base):
    """
    Case study model showcasing precision engineering challenges, metallurgical solutions,
    forging parameters, quality certifications, and customer outcomes.
    """
    __tablename__ = "case_studies"

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    featured_image = Column(String(500), nullable=True)
    client_industry = Column(String(255), nullable=False)
    client_challenge = Column(Text, nullable=False)
    engineering_approach = Column(Text, nullable=False)
    material = Column(String(255), nullable=False)
    forging_process = Column(String(255), nullable=False)
    machining = Column(Text, nullable=True)
    quality_requirements = Column(Text, nullable=True)
    result = Column(Text, nullable=False)
    gallery_json = Column(Text, nullable=True)      # Stored as JSON array of image URLs
    downloads_json = Column(Text, nullable=True)    # Stored as JSON array of download links/titles
    cta_text = Column(String(255), default="Request an Engineering Consultation", nullable=False)
    cta_link = Column(String(255), default="/request-a-quote", nullable=False)

    # SEO & Display
    seo_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    status = Column(String(50), default="published", nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    def get_gallery_list(self) -> List[str]:
        if not self.gallery_json:
            return []
        try:
            items = json.loads(self.gallery_json)
            return items if isinstance(items, list) else []
        except Exception:
            return []

    def get_downloads_list(self) -> List[Dict[str, str]]:
        if not self.downloads_json:
            return []
        try:
            items = json.loads(self.downloads_json)
            return items if isinstance(items, list) else []
        except Exception:
            return []

    def __repr__(self) -> str:
        return f"<CaseStudy id={self.id} slug='{self.slug}' client='{self.client_industry}'>"
