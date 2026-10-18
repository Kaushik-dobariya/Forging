import json
from typing import List, Dict, Any
from sqlalchemy import Column, String, Text, Integer, Boolean
from app.core.database import Base


class FAQ(Base):
    """
    Reusable FAQ model for assigning FAQs to pages, products, capabilities,
    industries, quality sections, or blog articles.
    """
    __tablename__ = "faqs"

    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), default="General", nullable=False)  # General, Forging, Quality, Materials, Ordering
    related_entity = Column(String(100), default="homepage", nullable=False)  # homepage, products, capabilities, industries, quality, blog, contact, etc.
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def to_schema_dict(self) -> Dict[str, Any]:
        """Returns JSON-LD Question item representation."""
        return {
            "@type": "Question",
            "name": self.question,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": self.answer,
            },
        }

    def __repr__(self) -> str:
        return f"<FAQ id={self.id} category='{self.category}' entity='{self.related_entity}'>"


def generate_faq_schema_ld(faqs: List[FAQ]) -> str:
    """
    Generates automatic Schema.org FAQPage JSON-LD structured data.
    """
    active_faqs = [faq for faq in faqs if faq.is_active]
    if not active_faqs:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [faq.to_schema_dict() for faq in active_faqs],
    }
    return json.dumps(data, indent=2)
