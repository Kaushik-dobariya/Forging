from app.core.database import Base
from app.models.user import User, UserRole
from app.models.associations import (
    product_capability_association,
    product_industry_association,
    product_material_association,
    product_equipment_association,
    capability_equipment_association,
    capability_material_association,
    capability_industry_association,
    product_related_association,
)
from app.models.product import (
    MeasurementUnit,
    ProductCategory,
    Product,
    ProductImage,
    ProductSpecification,
)
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.infrastructure import Facility, InfrastructureGallery, Equipment
from app.models.material import Material
from app.models.quality import QualitySection, Certification

# Phase 4 models
from app.models.blog import BlogPost, BlogCategory, BlogPostStatus
from app.models.case_study import CaseStudy
from app.models.faq import FAQ, generate_faq_schema_ld
from app.models.download import DownloadResource, DownloadCategory, DownloadVisibility
from app.models.lead import ContactLead, QuoteRequest, LeadStatus
from app.models.setting import SiteSetting, SocialLink, SocialPlatform

__all__ = [
    "Base",
    "User",
    "UserRole",
    "MeasurementUnit",
    "ProductCategory",
    "Product",
    "ProductImage",
    "ProductSpecification",
    "Capability",
    "Industry",
    "Facility",
    "InfrastructureGallery",
    "Equipment",
    "Material",
    "QualitySection",
    "Certification",
    "product_capability_association",
    "product_industry_association",
    "product_material_association",
    "product_equipment_association",
    "capability_equipment_association",
    "capability_material_association",
    "capability_industry_association",
    "product_related_association",
    # Phase 4
    "BlogPost",
    "BlogCategory",
    "BlogPostStatus",
    "CaseStudy",
    "FAQ",
    "generate_faq_schema_ld",
    "DownloadResource",
    "DownloadCategory",
    "DownloadVisibility",
    "ContactLead",
    "QuoteRequest",
    "LeadStatus",
    "SiteSetting",
    "SocialLink",
    "SocialPlatform",
]
