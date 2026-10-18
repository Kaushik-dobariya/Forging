import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import APIRouter, Request, Depends, HTTPException, status, Response, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.config import settings
from app.models.product import Product, ProductCategory, ProductSpecification, ProductImage
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.infrastructure import Facility, Equipment, InfrastructureGallery
from app.models.material import Material
from app.models.quality import QualitySection, Certification

# Phase 4 and 5 models and services
from app.models.blog import BlogPost, BlogCategory, BlogPostStatus
from app.models.case_study import CaseStudy
from app.models.faq import FAQ, generate_faq_schema_ld
from app.models.download import DownloadResource, DownloadCategory, DownloadVisibility
from app.models.lead import ContactLead, QuoteRequest, LeadStatus
from app.models.setting import SiteSetting, SocialLink
from app.models.page import CMSPage, PageStatus
from app.models.redirect import URLRedirect
from app.models.hero_slide import HeroSlide
from app.models.timeline import TimelineMilestone
from app.services.settings_service import settings_service
from app.services.email_service import email_service
from app.services.upload_service import upload_service
from app.services.page_service import page_service
from app.services.auth_service import auth_service
from app.services.spam_protection import (
    rate_limiter,
    validate_honeypot,
    validate_public_csrf_token,
    validate_email_address,
    sanitize_input_text,
    generate_public_csrf_token,
)

router = APIRouter(tags=["Public Web"])


# ==============================================================================
# HOMEPAGE
# ==============================================================================

@router.get("/", response_class=HTMLResponse, summary="Public Homepage")
async def index_view(request: Request, db: Session = Depends(get_db)):
    """Renders the public corporate website homepage with dynamic CMS data."""
    hero_slides = db.query(HeroSlide).filter(HeroSlide.is_active == True).order_by(HeroSlide.display_order.asc(), HeroSlide.id.asc()).all()
    capabilities = db.query(Capability).filter(Capability.status == "published").order_by(Capability.display_order.asc()).limit(6).all()
    industries = db.query(Industry).filter(Industry.status == "published").order_by(Industry.display_order.asc()).limit(6).all()
    featured_products = db.query(Product).filter(Product.status == "published").order_by(Product.display_order.asc()).limit(4).all()
    certifications = db.query(Certification).filter(Certification.status == "published").order_by(Certification.display_order.asc()).limit(4).all()
    facilities = db.query(Facility).filter(Facility.status == "published").order_by(Facility.display_order.asc()).limit(3).all()

    # Dynamic marketing and resource data
    faqs = db.query(FAQ).filter(FAQ.related_entity.in_(["homepage", "general"]), FAQ.is_active == True).order_by(FAQ.display_order.asc()).limit(6).all()
    faq_schema_ld = generate_faq_schema_ld(faqs)
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)
    recent_posts = db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.PUBLISHED.value).order_by(BlogPost.publish_date.desc()).limit(3).all()
    featured_case_studies = db.query(CaseStudy).filter(CaseStudy.status == "published").order_by(CaseStudy.display_order.asc()).limit(3).all()

    return templates.TemplateResponse(
        request=request,
        name="public/index.html",
        context={
            "request": request,
            "hero_slides": hero_slides,
            "capabilities": capabilities,
            "industries": industries,
            "featured_products": featured_products,
            "certifications": certifications,
            "facilities": facilities,
            "faqs": faqs,
            "faq_schema_ld": faq_schema_ld,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "recent_posts": recent_posts,
            "featured_case_studies": featured_case_studies,
        },
    )


# ==============================================================================
# ABOUT US & COMPANY HISTORY
# ==============================================================================

@router.get("/about", response_class=HTMLResponse, summary="Public About Us")
@router.get("/about-us", response_class=HTMLResponse, include_in_schema=False)
async def public_about_view(request: Request, db: Session = Depends(get_db)):
    """
    Renders dedicated industrial About Us page with structured engineering sections,
    overview, vision, mission, core values, leadership, manufacturing philosophy,
    infrastructure preview, certifications, and milestone preview.
    """
    cms_page = page_service.get_page_by_slug(db, "about") or page_service.get_page_by_slug(db, "about-us")
    certifications = db.query(Certification).filter(Certification.status == "published").order_by(Certification.display_order.asc()).limit(6).all()
    facilities = db.query(Facility).filter(Facility.status == "published").order_by(Facility.display_order.asc()).limit(3).all()
    equipment_sample = db.query(Equipment).filter(Equipment.status == "published").order_by(Equipment.display_order.asc()).limit(4).all()
    milestones_preview = db.query(TimelineMilestone).filter(TimelineMilestone.is_active == True).order_by(TimelineMilestone.display_order.asc(), TimelineMilestone.year.asc()).limit(4).all()
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)

    return templates.TemplateResponse(
        request=request,
        name="public/about.html",
        context={
            "request": request,
            "cms_page": cms_page,
            "certifications": certifications,
            "facilities": facilities,
            "equipment_sample": equipment_sample,
            "milestones_preview": milestones_preview,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "page_title": "About Us | Heavy Forging & Precision Engineering Leaders",
            "meta_description": "Learn about our precision forging legacy, cutting-edge hydraulic press plant, metallurgical laboratory, ISO certifications, and leadership team.",
        },
    )


@router.get("/company-history", response_class=HTMLResponse, summary="Company History Timeline")
async def public_company_history_view(request: Request, db: Session = Depends(get_db)):
    """
    Renders the company history milestone timeline: /company-history
    """
    milestones = db.query(TimelineMilestone).filter(TimelineMilestone.is_active == True).order_by(TimelineMilestone.display_order.asc(), TimelineMilestone.year.asc()).all()
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)

    return templates.TemplateResponse(
        request=request,
        name="public/company_history.html",
        context={
            "request": request,
            "milestones": milestones,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "page_title": "Our Engineering Heritage & Timeline | 30+ Years of Forging Excellence",
            "meta_description": "Explore the milestones, capacity expansions, press shop commissioning, and global exports shaping our metallurgical manufacturing journey.",
        },
    )


# ==============================================================================
# MACHINERY & FLEET ROUTE
# ==============================================================================

@router.get("/machinery", response_class=HTMLResponse, summary="Machinery & Equipment Fleet")
async def public_machinery_view(request: Request, db: Session = Depends(get_db)):
    """
    Renders detailed machinery and equipment fleet catalog: /machinery
    """
    equipment_list = db.query(Equipment).filter(Equipment.status == "published").order_by(Equipment.display_order.asc()).all()
    facilities = db.query(Facility).filter(Facility.status == "published").order_by(Facility.display_order.asc()).all()
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)

    return templates.TemplateResponse(
        request=request,
        name="public/machinery.html",
        context={
            "request": request,
            "equipment_list": equipment_list,
            "facilities": facilities,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "page_title": "Machinery & Equipment Fleet | Heavy Hydraulic Presses & CNC Centers",
            "meta_description": "Complete equipment list: closed die hammers, open die hydraulic presses up to 4000T, 5-axis CNC machining centers, and heat treating furnaces.",
        },
    )


# ==============================================================================
# FAQS KNOWLEDGEBASE ROUTE
# ==============================================================================

@router.get("/faqs", response_class=HTMLResponse, summary="Frequently Asked Questions")
async def public_faqs_view(request: Request, db: Session = Depends(get_db)):
    """
    Renders standalone technical and commercial FAQ knowledgebase: /faqs
    """
    faqs = db.query(FAQ).filter(FAQ.is_active == True).order_by(FAQ.display_order.asc()).all()
    faq_schema_ld = generate_faq_schema_ld(faqs)
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)

    return templates.TemplateResponse(
        request=request,
        name="public/faqs.html",
        context={
            "request": request,
            "faqs": faqs,
            "faq_schema_ld": faq_schema_ld,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "page_title": "Forging Technical & Commercial FAQs | Customer Knowledgebase",
            "meta_description": "Answers to common questions regarding forging tolerances, lead times, tooling development, MOQ, test certificates, and export logistics.",
        },
    )




# ==============================================================================
# PRODUCTS ROUTES
# ==============================================================================

@router.get("/products", response_class=HTMLResponse, summary="Products Catalog")
async def public_products_list(
    request: Request,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Renders product catalog index: /products
    """
    query = db.query(Product).filter(Product.status == "published")
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    products = query.order_by(Product.display_order.asc(), Product.id.desc()).all()
    categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).order_by(ProductCategory.display_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="public/products/list.html",
        context={
            "request": request,
            "products": products,
            "categories": categories,
            "active_category": None,
            "q": q,
            "page_title": "Industrial Forgings & Precision Engineered Components Catalog",
            "meta_description": "Explore our certified forged components: closed-die crankshafts, seamless rolled rings, open-die shafts, and precision machined components.",
        },
    )


@router.get("/products/{category_slug}", response_class=HTMLResponse, summary="Category Products")
async def public_category_products(
    category_slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders category-filtered product catalog: /products/{category}
    """
    category = db.query(ProductCategory).filter(
        ProductCategory.slug == category_slug,
        ProductCategory.is_active == True,
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Product category not found")

    products = db.query(Product).filter(
        Product.category_id == category.id,
        Product.status == "published",
    ).order_by(Product.display_order.asc()).all()

    categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).order_by(ProductCategory.display_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="public/products/category.html",
        context={
            "request": request,
            "category": category,
            "products": products,
            "categories": categories,
            "active_category": category,
            "page_title": category.meta_title or f"{category.name} Catalog",
            "meta_description": category.meta_description or category.description,
        },
    )


@router.get("/products/{category_slug}/{product_slug}", response_class=HTMLResponse, summary="Product Detail")
async def public_product_detail(
    category_slug: str,
    product_slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders canonical product detail: /products/{category}/{product}
    Enforces strict SEO URL matching.
    """
    product = db.query(Product).filter(
        Product.slug == product_slug,
        Product.status == "published",
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Enforce canonical category slug check
    expected_category_slug = product.category.slug if product.category else "all"
    if category_slug != expected_category_slug:
        raise HTTPException(status_code=404, detail="Product not found in this category")

    return templates.TemplateResponse(
        request=request,
        name="public/products/detail.html",
        context={
            "request": request,
            "product": product,
            "page_title": product.meta_title or f"{product.name} | Technical Specifications",
            "meta_description": product.meta_description or product.short_description,
        },
    )


# ==============================================================================
# CAPABILITIES ROUTES
# ==============================================================================

@router.get("/capabilities", response_class=HTMLResponse, summary="Capabilities Index")
async def public_capabilities_list(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders capabilities overview: /capabilities
    """
    capabilities = db.query(Capability).filter(
        Capability.status == "published"
    ).order_by(Capability.display_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="public/capabilities/list.html",
        context={
            "request": request,
            "capabilities": capabilities,
            "page_title": "Forging, Ring Rolling & Machining Engineering Capabilities",
            "meta_description": "Our comprehensive manufacturing capabilities: open die forging up to 15 MT, closed die forging, CNC ring rolling, 5-axis machining, and heat treatment.",
        },
    )


@router.get("/capabilities/{slug}", response_class=HTMLResponse, summary="Capability Detail")
async def public_capability_detail(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders dedicated capability page: /capabilities/{slug}
    """
    capability = db.query(Capability).filter(
        Capability.slug == slug,
        Capability.status == "published",
    ).first()

    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")

    faqs = []
    if capability.faqs_json:
        try:
            faqs = json.loads(capability.faqs_json)
        except Exception:
            faqs = []

    return templates.TemplateResponse(
        request=request,
        name="public/capabilities/detail.html",
        context={
            "request": request,
            "capability": capability,
            "faqs": faqs,
            "page_title": capability.meta_title or f"{capability.title} | Manufacturing Services",
            "meta_description": capability.meta_description or capability.short_description,
        },
    )


# ==============================================================================
# INDUSTRIES ROUTES
# ==============================================================================

@router.get("/industries", response_class=HTMLResponse, summary="Industries Index")
async def public_industries_list(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders industries overview: /industries
    """
    industries = db.query(Industry).filter(
        Industry.status == "published"
    ).order_by(Industry.display_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="public/industries/list.html",
        context={
            "request": request,
            "industries": industries,
            "page_title": "Target Industries & Mission-Critical Sectors Served",
            "meta_description": "High-integrity forged components engineered for automotive, oil & gas, railways, power generation, defence, and heavy industrial machinery.",
        },
    )


@router.get("/industries/{slug}", response_class=HTMLResponse, summary="Industry Detail")
async def public_industry_detail(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders dedicated industry landing page: /industries/{slug}
    """
    industry = db.query(Industry).filter(
        Industry.slug == slug,
        Industry.status == "published",
    ).first()

    if not industry:
        raise HTTPException(status_code=404, detail="Industry not found")

    return templates.TemplateResponse(
        request=request,
        name="public/industries/detail.html",
        context={
            "request": request,
            "industry": industry,
            "page_title": industry.meta_title or f"{industry.name} Forged Components & Engineering",
            "meta_description": industry.meta_description or industry.short_description,
        },
    )


# ==============================================================================
# INFRASTRUCTURE ROUTE
# ==============================================================================

@router.get("/infrastructure", response_class=HTMLResponse, summary="Infrastructure & Facilities")
async def public_infrastructure(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders infrastructure, plant facilities, equipment, and gallery: /infrastructure
    """
    facilities = db.query(Facility).filter(Facility.status == "published").order_by(Facility.display_order.asc()).all()
    equipment_list = db.query(Equipment).filter(Equipment.status == "published").order_by(Equipment.display_order.asc()).all()
    gallery_items = db.query(InfrastructureGallery).filter(InfrastructureGallery.is_active == True).order_by(InfrastructureGallery.display_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="public/infrastructure/index.html",
        context={
            "request": request,
            "facilities": facilities,
            "equipment_list": equipment_list,
            "gallery_items": gallery_items,
            "page_title": "Manufacturing Infrastructure, Forge Shop & Machinery Fleet",
            "meta_description": "Tour our 120,000 sq ft advanced manufacturing plant: 4000 MT hydraulic presses, CNC machining centers, and NABL testing lab.",
        },
    )


# ==============================================================================
# MATERIALS ROUTES
# ==============================================================================

@router.get("/materials", response_class=HTMLResponse, summary="Materials Index")
async def public_materials_list(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders materials overview: /materials
    """
    materials = db.query(Material).filter(Material.status == "published").order_by(Material.display_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="public/materials/list.html",
        context={
            "request": request,
            "materials": materials,
            "page_title": "Forging Steels & Metallurgy Grades | Chemical & Mechanical Properties",
            "meta_description": "Carbon steel, alloy steel (4140, 4340, EN24), stainless steel (316L, Duplex), and superalloys for precision forging.",
        },
    )


@router.get("/materials/{slug}", response_class=HTMLResponse, summary="Material Detail")
async def public_material_detail(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders dedicated material grade page: /materials/{slug}
    """
    material = db.query(Material).filter(
        Material.slug == slug,
        Material.status == "published",
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    return templates.TemplateResponse(
        request=request,
        name="public/materials/detail.html",
        context={
            "request": request,
            "material": material,
            "page_title": material.meta_title or f"{material.name} ({material.grade}) Forging Grade",
            "meta_description": material.meta_description or material.description,
        },
    )


# ==============================================================================
# QUALITY & TESTING ROUTE
# ==============================================================================

@router.get("/quality", response_class=HTMLResponse, summary="Quality System")
async def public_quality(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders quality policy, QMS, inspection, testing facilities, traceability, and QA gates: /quality
    """
    sections = db.query(QualitySection).filter(QualitySection.is_active == True).order_by(QualitySection.display_order.asc()).all()
    testing_equipment = db.query(Equipment).filter(
        Equipment.category.in_(["Spectrometer", "UT Machine", "Testing Equipment"]),
        Equipment.status == "published",
    ).all()
    certifications = db.query(Certification).filter(Certification.status == "published").order_by(Certification.display_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="public/quality/index.html",
        context={
            "request": request,
            "sections": sections,
            "testing_equipment": testing_equipment,
            "certifications": certifications,
            "page_title": "Quality Assurance, Metallurgical Testing & NDT Inspection",
            "meta_description": "Zero-defect quality assurance: ISO 9001:2015, IATF 16949, 100% ultrasonic testing, optical spectrometry, and material traceability.",
        },
    )


# ==============================================================================
# CERTIFICATIONS ROUTE
# ==============================================================================

@router.get("/certifications", response_class=HTMLResponse, summary="Certifications & Accreditations")
async def public_certifications(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Renders official certifications with view certificate & download PDF: /certifications
    """
    certifications = db.query(Certification).filter(
        Certification.status == "published"
    ).order_by(Certification.display_order.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="public/certifications/index.html",
        context={
            "request": request,
            "certifications": certifications,
            "page_title": "ISO 9001, IATF 16949 & PED 2014/68/EU Certifications",
            "meta_description": "View and download our international manufacturing quality certifications: ISO 9001:2015, IATF 16949, AS9100D, and PED 2014/68/EU.",
        },
    )


# ==============================================================================
# BLOG ROUTES
# ==============================================================================

@router.get("/blog", response_class=HTMLResponse, summary="Blog & Articles")
async def public_blog_list(
    request: Request,
    cat: Optional[str] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    query = db.query(BlogPost).filter(
        BlogPost.status == BlogPostStatus.PUBLISHED.value,
        BlogPost.publish_date <= now,
    )
    if cat:
        query = query.filter(BlogPost.category == cat)
    if tag:
        query = query.filter(BlogPost.tags.ilike(f"%{tag}%"))
    if q:
        query = query.filter(BlogPost.title.ilike(f"%{q}%") | BlogPost.content.ilike(f"%{q}%"))

    posts = query.order_by(BlogPost.publish_date.desc()).all()
    featured_post = posts[0] if posts else None
    regular_posts = posts[1:] if len(posts) > 1 else []

    all_published = db.query(BlogPost).filter(
        BlogPost.status == BlogPostStatus.PUBLISHED.value,
        BlogPost.publish_date <= now,
    ).all()
    categories_data = []
    for c in BlogCategory:
        count = sum(1 for p in all_published if p.category == c.value)
        categories_data.append({"name": c.value, "count": count})

    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)

    return templates.TemplateResponse(
        request=request,
        name="public/blog/list.html",
        context={
            "request": request,
            "posts": posts,
            "featured_post": featured_post,
            "regular_posts": regular_posts,
            "categories": categories_data,
            "active_category": cat,
            "current_category": cat,
            "active_tag": tag,
            "q": q,
            "page": 1,
            "total_pages": 1,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "page_title": "Forging Technology & Precision Manufacturing Insights",
            "meta_description": "Industry insights, engineering metallurgy, closed-die forging breakthroughs, and company news.",
        },
    )


@router.get("/blog/{slug}", response_class=HTMLResponse, summary="Blog Article Detail")
async def public_blog_detail(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    post = db.query(BlogPost).filter(BlogPost.slug == slug).first()
    if not post:
        raise HTTPException(status_code=404, detail="Article not found")

    if not post.is_visible_publicly():
        from app.services.auth_service import auth_service
        admin_user = auth_service.get_current_user_from_cookie(db, request)
        if not admin_user:
            raise HTTPException(status_code=404, detail="Article not found or scheduled")

    related_posts = db.query(BlogPost).filter(
        BlogPost.id != post.id,
        BlogPost.category == post.category,
        BlogPost.status == BlogPostStatus.PUBLISHED.value,
    ).order_by(BlogPost.publish_date.desc()).limit(3).all()

    schema_ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.seo_title or post.title,
        "description": post.meta_description or post.excerpt,
        "author": {
            "@type": "Organization",
            "name": post.author,
        },
        "publisher": {
            "@type": "Organization",
            "name": settings.APP_NAME,
        },
        "datePublished": post.publish_date.isoformat() if post.publish_date else "",
        "articleSection": post.category,
    }
    if post.featured_image:
        schema_ld["image"] = f"{settings.SITE_URL}{post.featured_image}" if post.featured_image.startswith("/") else post.featured_image

    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)
    whatsapp_article_cta = whatsapp_cfg.generate_cta(
        f"Hello, I was reading your article '{post.title}' and would like to ask a technical question."
    )

    return templates.TemplateResponse(
        request=request,
        name="public/blog/detail.html",
        context={
            "request": request,
            "post": post,
            "related_posts": related_posts,
            "schema_ld_json": json.dumps(schema_ld, indent=2),
            "whatsapp_cfg": whatsapp_cfg,
            "whatsapp_article_cta": whatsapp_article_cta,
            "social_links": social_links,
            "page_title": post.seo_title or f"{post.title} | {settings.APP_NAME}",
            "meta_description": post.meta_description or post.excerpt,
        },
    )


# ==============================================================================
# CASE STUDIES ROUTES
# ==============================================================================

@router.get("/case-studies", response_class=HTMLResponse, summary="Case Studies")
async def public_case_studies_list(
    request: Request,
    ind: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(CaseStudy).filter(CaseStudy.status == "published")
    if ind:
        query = query.filter(CaseStudy.client_industry.ilike(f"%{ind}%"))
    if q:
        query = query.filter(
            CaseStudy.title.ilike(f"%{q}%")
            | CaseStudy.material.ilike(f"%{q}%")
            | CaseStudy.client_challenge.ilike(f"%{q}%")
        )

    case_studies = query.order_by(CaseStudy.display_order.asc(), CaseStudy.id.desc()).all()
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)

    return templates.TemplateResponse(
        request=request,
        name="public/case_studies/list.html",
        context={
            "request": request,
            "case_studies": case_studies,
            "ind": ind,
            "q": q,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "page_title": "Forging Engineering Case Studies & Metallurgical Solutions",
            "meta_description": "Real-world engineering challenges solved: aerospace turbine forgings, high-strength railway axles, and subsea oilfield components.",
        },
    )


@router.get("/case-studies/{slug}", response_class=HTMLResponse, summary="Case Study Detail")
async def public_case_study_detail(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    case_study = db.query(CaseStudy).filter(CaseStudy.slug == slug, CaseStudy.status == "published").first()
    if not case_study:
        raise HTTPException(status_code=404, detail="Case study not found")

    related_case_studies = db.query(CaseStudy).filter(
        CaseStudy.id != case_study.id,
        CaseStudy.status == "published",
    ).order_by(CaseStudy.display_order.asc()).limit(3).all()

    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    whatsapp_case_cta = whatsapp_cfg.generate_cta(
        f"Hello, I am reviewing your case study '{case_study.title}' and have a similar engineering requirement."
    )

    return templates.TemplateResponse(
        request=request,
        name="public/case_studies/detail.html",
        context={
            "request": request,
            "case_study": case_study,
            "gallery_items": case_study.get_gallery_list(),
            "downloads_items": case_study.get_downloads_list(),
            "related_case_studies": related_case_studies,
            "whatsapp_cfg": whatsapp_cfg,
            "whatsapp_case_cta": whatsapp_case_cta,
            "page_title": case_study.seo_title or f"{case_study.title} | Case Study",
            "meta_description": case_study.meta_description or case_study.client_challenge[:160],
        },
    )


# ==============================================================================
# DOWNLOADS LIBRARY ROUTES
# ==============================================================================

@router.get("/downloads", response_class=HTMLResponse, summary="Technical Resource Library")
async def public_downloads_list(
    request: Request,
    cat: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(DownloadResource).filter(
        DownloadResource.is_active == True,
        DownloadResource.visibility.in_(["public", "gated"]),
    )
    if cat:
        query = query.filter(DownloadResource.category == cat)
    if q:
        query = query.filter(
            DownloadResource.title.ilike(f"%{q}%")
            | DownloadResource.description.ilike(f"%{q}%")
        )

    resources = query.order_by(DownloadResource.display_order.asc(), DownloadResource.id.desc()).all()
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)

    return templates.TemplateResponse(
        request=request,
        name="public/downloads/list.html",
        context={
            "request": request,
            "resources": resources,
            "cat": cat,
            "q": q,
            "categories": [c.value for c in DownloadCategory],
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "page_title": "Technical Downloads, Catalogs & Certification Library",
            "meta_description": "Download forging brochures, material specification sheets, product drawing templates, and ISO/IATF quality certificates.",
        },
    )


@router.get("/downloads/{resource_id}/file", summary="Download Resource File")
async def public_download_file(
    resource_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    resource = db.query(DownloadResource).filter(
        DownloadResource.id == resource_id,
        DownloadResource.is_active == True,
    ).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    resource.download_count += 1
    db.commit()

    if resource.file_path.startswith("/uploads/"):
        disk_path = settings.resolved_upload_dir / resource.file_path.replace("/uploads/", "")
        if disk_path.exists():
            return FileResponse(
                path=str(disk_path),
                filename=Path(resource.file_path).name,
                media_type="application/octet-stream",
            )

    return RedirectResponse(url=resource.file_path, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


# ==============================================================================
# CONTACT PAGE & SECURE CONTACT FORM
# ==============================================================================

@router.get("/contact", response_class=HTMLResponse, summary="Contact Page")
async def public_contact_view(
    request: Request,
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    contact_info = settings_service.get_contact_info(db)
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)
    faqs = db.query(FAQ).filter(
        FAQ.related_entity.in_(["contact", "general"]),
        FAQ.is_active == True,
    ).order_by(FAQ.display_order.asc()).all()
    faq_schema_ld = generate_faq_schema_ld(faqs)

    client_ip = request.client.host if request.client else "anon"
    csrf_token = generate_public_csrf_token(client_ip)

    return templates.TemplateResponse(
        request=request,
        name="public/contact.html",
        context={
            "request": request,
            "contact_info": contact_info,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "faqs": faqs,
            "faq_schema_ld": faq_schema_ld,
            "csrf_token": csrf_token,
            "success": False,
            "error": None,
            "form_data": {},
            "page_title": "Contact Engineering & Factory Operations | Forging Platform",
            "meta_description": "Connect with our precision forging plant, metallurgical engineers, sales specialists, and quality control departments.",
        },
    )


@router.post("/contact", response_class=HTMLResponse, summary="Submit Contact Form")
async def public_contact_post(
    request: Request,
    name: str = Form(""),
    company: Optional[str] = Form(None),
    email: str = Form(""),
    phone: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    message: str = Form(""),
    website_url_check: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "anon"
    contact_info = settings_service.get_contact_info(db)
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)
    faqs = db.query(FAQ).filter(FAQ.related_entity.in_(["contact", "general"]), FAQ.is_active == True).all()

    form_data = {
        "name": name,
        "company": company,
        "email": email,
        "phone": phone,
        "country": country,
        "message": message,
    }

    if not validate_honeypot({"website_url_check": website_url_check}):
        return templates.TemplateResponse(
            request=request,
            name="public/contact.html",
            context={
                "request": request,
                "contact_info": contact_info,
                "whatsapp_cfg": whatsapp_cfg,
                "social_links": social_links,
                "faqs": faqs,
                "faq_schema_ld": generate_faq_schema_ld(faqs),
                "csrf_token": generate_public_csrf_token(client_ip),
                "success": True,
                "form_data": {},
            },
        )

    if rate_limiter.is_rate_limited(client_ip):
        return templates.TemplateResponse(
            request=request,
            name="public/contact.html",
            context={
                "request": request,
                "contact_info": contact_info,
                "whatsapp_cfg": whatsapp_cfg,
                "social_links": social_links,
                "faqs": faqs,
                "faq_schema_ld": generate_faq_schema_ld(faqs),
                "csrf_token": generate_public_csrf_token(client_ip),
                "success": False,
                "error": "Too many submissions detected. Please wait a few minutes before trying again.",
                "form_data": form_data,
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    clean_name = sanitize_input_text(name, 150)
    clean_email = email.strip()
    clean_message = sanitize_input_text(message, 5000)

    if not clean_name or not clean_email or not clean_message:
        return templates.TemplateResponse(
            request=request,
            name="public/contact.html",
            context={
                "request": request,
                "contact_info": contact_info,
                "whatsapp_cfg": whatsapp_cfg,
                "social_links": social_links,
                "faqs": faqs,
                "faq_schema_ld": generate_faq_schema_ld(faqs),
                "csrf_token": generate_public_csrf_token(client_ip),
                "success": False,
                "error": "Full name, corporate email, and message details are required.",
                "form_data": form_data,
            },
            status_code=status.HTTP_200_OK,
        )

    if not validate_email_address(clean_email):
        return templates.TemplateResponse(
            request=request,
            name="public/contact.html",
            context={
                "request": request,
                "contact_info": contact_info,
                "whatsapp_cfg": whatsapp_cfg,
                "social_links": social_links,
                "faqs": faqs,
                "faq_schema_ld": generate_faq_schema_ld(faqs),
                "csrf_token": generate_public_csrf_token(client_ip),
                "success": False,
                "error": "Please provide a valid corporate email address.",
                "form_data": form_data,
            },
            status_code=status.HTTP_200_OK,
        )

    lead = ContactLead(
        name=clean_name,
        company=sanitize_input_text(company, 150) if company else None,
        email=clean_email,
        phone=sanitize_input_text(phone, 50) if phone else None,
        country=sanitize_input_text(country, 100) if country else None,
        message=clean_message,
        source="contact_page",
        client_ip=client_ip,
        status=LeadStatus.NEW.value,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    rate_limiter.record_request(client_ip)

    email_service.send_contact_notification(lead)
    email_service.send_contact_acknowledgment(lead)

    return templates.TemplateResponse(
        request=request,
        name="public/contact.html",
        context={
            "request": request,
            "contact_info": contact_info,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "faqs": faqs,
            "faq_schema_ld": generate_faq_schema_ld(faqs),
            "csrf_token": generate_public_csrf_token(client_ip),
            "success": True,
            "error": None,
            "form_data": {},
            "submitted_name": clean_name,
        },
    )


# ==============================================================================
# REQUEST A QUOTE (RFQ) WITH DRAWING UPLOAD
# ==============================================================================

@router.get("/request-a-quote", response_class=HTMLResponse, summary="Request a Quote View")
@router.get("/request-quote", response_class=HTMLResponse, include_in_schema=False)
async def public_quote_view(
    request: Request,
    product: Optional[str] = None,
    material: Optional[str] = None,
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)
    faqs = db.query(FAQ).filter(
        FAQ.related_entity.in_(["products", "capabilities", "general"]),
        FAQ.is_active == True,
    ).order_by(FAQ.display_order.asc()).limit(6).all()

    client_ip = request.client.host if request.client else "anon"
    csrf_token = generate_public_csrf_token(client_ip)

    return templates.TemplateResponse(
        request=request,
        name="public/quote.html",
        context={
            "request": request,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "faqs": faqs,
            "faq_schema_ld": generate_faq_schema_ld(faqs),
            "csrf_token": csrf_token,
            "preset_product": product or "",
            "preset_material": material or "",
            "success": False,
            "error": None,
            "form_data": {},
            "page_title": "Request a Forging Quotation & Engineering Estimate",
            "meta_description": "Submit engineering 2D/3D drawings for immediate manufacturability review, tooling estimates, and commercial pricing.",
        },
    )


@router.post("/request-a-quote", response_class=HTMLResponse, summary="Submit Quote Request")
@router.post("/request-quote", response_class=HTMLResponse, include_in_schema=False)
async def public_quote_post(

    request: Request,
    name: str = Form(""),
    company: str = Form(""),
    email: str = Form(""),
    phone: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    product_component: Optional[str] = Form(None),
    product: Optional[str] = Form(None),
    material: Optional[str] = Form(None),
    quantity: Optional[str] = Form(None),
    required_delivery: Optional[str] = Form(None),
    additional_requirements: Optional[str] = Form(None),
    requirement: Optional[str] = Form(None),
    drawing_upload: Optional[UploadFile] = File(None),
    drawing_file: Optional[UploadFile] = File(None),
    website_url_check: Optional[str] = Form(None),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "anon"
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_links = settings_service.get_social_links(db)
    faqs = db.query(FAQ).filter(FAQ.related_entity.in_(["products", "capabilities", "general"]), FAQ.is_active == True).all()

    eff_product = product if product is not None else product_component
    eff_requirement = requirement if requirement is not None else additional_requirements
    eff_drawing = drawing_file if (drawing_file and drawing_file.filename) else drawing_upload

    form_data = {
        "name": name,
        "company": company,
        "email": email,
        "phone": phone,
        "country": country,
        "product_component": eff_product,
        "product": eff_product,
        "material": material,
        "quantity": quantity,
        "required_delivery": required_delivery,
        "additional_requirements": eff_requirement,
        "requirement": eff_requirement,
    }

    if not validate_honeypot({"website_url_check": website_url_check}):
        return templates.TemplateResponse(
            request=request,
            name="public/quote.html",
            context={
                "request": request,
                "whatsapp_cfg": whatsapp_cfg,
                "social_links": social_links,
                "faqs": faqs,
                "faq_schema_ld": generate_faq_schema_ld(faqs),
                "csrf_token": generate_public_csrf_token(client_ip),
                "success": True,
                "form_data": {},
            },
        )

    if rate_limiter.is_rate_limited(client_ip):
        return templates.TemplateResponse(
            request=request,
            name="public/quote.html",
            context={
                "request": request,
                "whatsapp_cfg": whatsapp_cfg,
                "social_links": social_links,
                "faqs": faqs,
                "faq_schema_ld": generate_faq_schema_ld(faqs),
                "csrf_token": generate_public_csrf_token(client_ip),
                "success": False,
                "error": "Rate limit exceeded. Please wait a few minutes before submitting again.",
                "form_data": form_data,
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    clean_name = sanitize_input_text(name, 150)
    clean_company = sanitize_input_text(company, 150)
    clean_email = email.strip()

    if not clean_name or not clean_company or not clean_email:
        return templates.TemplateResponse(
            request=request,
            name="public/quote.html",
            context={
                "request": request,
                "whatsapp_cfg": whatsapp_cfg,
                "social_links": social_links,
                "faqs": faqs,
                "faq_schema_ld": generate_faq_schema_ld(faqs),
                "csrf_token": generate_public_csrf_token(client_ip),
                "success": False,
                "error": "Name, Company, and Email are required fields.",
                "form_data": form_data,
            },
            status_code=status.HTTP_200_OK,
        )

    if not validate_email_address(clean_email):
        return templates.TemplateResponse(
            request=request,
            name="public/quote.html",
            context={
                "request": request,
                "whatsapp_cfg": whatsapp_cfg,
                "social_links": social_links,
                "faqs": faqs,
                "faq_schema_ld": generate_faq_schema_ld(faqs),
                "csrf_token": generate_public_csrf_token(client_ip),
                "success": False,
                "error": "Please provide a valid corporate email address.",
                "form_data": form_data,
            },
            status_code=status.HTTP_200_OK,
        )

    drawing_rel_url = None
    if eff_drawing and eff_drawing.filename:
        try:
            rel_url, _ = upload_service.save_upload(
                eff_drawing,
                subfolder="drawings",
                is_drawing=True,
            )
            drawing_rel_url = rel_url
        except HTTPException as exc:
            return templates.TemplateResponse(
                request=request,
                name="public/quote.html",
                context={
                    "request": request,
                    "whatsapp_cfg": whatsapp_cfg,
                    "social_links": social_links,
                    "faqs": faqs,
                    "faq_schema_ld": generate_faq_schema_ld(faqs),
                    "csrf_token": generate_public_csrf_token(client_ip),
                    "success": False,
                    "error": exc.detail,
                    "form_data": form_data,
                },
                status_code=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.error(f"Quote drawing upload error: {exc}")
            return templates.TemplateResponse(
                request=request,
                name="public/quote.html",
                context={
                    "request": request,
                    "whatsapp_cfg": whatsapp_cfg,
                    "social_links": social_links,
                    "faqs": faqs,
                    "faq_schema_ld": generate_faq_schema_ld(faqs),
                    "csrf_token": generate_public_csrf_token(client_ip),
                    "success": False,
                    "error": "Failed to process drawing file upload. Please verify file format and size.",
                    "form_data": form_data,
                },
                status_code=status.HTTP_200_OK,
            )

    quote = QuoteRequest(
        customer_name=clean_name,
        company=clean_company,
        email=clean_email,
        phone=sanitize_input_text(phone, 50) if phone else None,
        country=sanitize_input_text(country, 100) if country else None,
        product_component=sanitize_input_text(eff_product, 200) if eff_product else None,
        material=sanitize_input_text(material, 150) if material else None,
        quantity=sanitize_input_text(quantity, 100) if quantity else None,
        required_delivery=sanitize_input_text(required_delivery, 100) if required_delivery else None,
        drawing_file=drawing_rel_url,
        additional_requirements=sanitize_input_text(eff_requirement, 5000) if eff_requirement else None,
        source="request_quote_page",
        client_ip=client_ip,
        status=LeadStatus.NEW.value,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)

    rate_limiter.record_request(client_ip)

    email_service.send_quote_notification(quote)
    email_service.send_quote_acknowledgment(quote)

    return templates.TemplateResponse(
        request=request,
        name="public/quote.html",
        context={
            "request": request,
            "whatsapp_cfg": whatsapp_cfg,
            "social_links": social_links,
            "faqs": faqs,
            "faq_schema_ld": generate_faq_schema_ld(faqs),
            "csrf_token": generate_public_csrf_token(client_ip),
            "success": True,
            "error": None,
            "form_data": {},
            "submitted_quote_id": quote.id,
            "submitted_company": quote.company,
        },
    )


# ==============================================================================
# SEO: SITEMAP & ROBOTS.TXT
# ==============================================================================

@router.get("/sitemap.xml", summary="Public XML Sitemap")
async def sitemap_xml(request: Request, db: Session = Depends(get_db)):
    """
    Generates dynamic XML sitemap compliant with sitemaps.org schema.
    Includes only published public content, deduplicated, excluding admin and authentication pages.
    """
    base_url = settings.SITE_URL.rstrip("/") if settings.SITE_URL else str(request.base_url).rstrip("/")
    
    static_pages = [
        {"loc": f"{base_url}/", "changefreq": "weekly", "priority": "1.0"},
        {"loc": f"{base_url}/products", "changefreq": "daily", "priority": "0.9"},
        {"loc": f"{base_url}/capabilities", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{base_url}/industries", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{base_url}/infrastructure", "changefreq": "monthly", "priority": "0.8"},
        {"loc": f"{base_url}/materials", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{base_url}/quality", "changefreq": "monthly", "priority": "0.8"},
        {"loc": f"{base_url}/certifications", "changefreq": "monthly", "priority": "0.8"},
        {"loc": f"{base_url}/blog", "changefreq": "daily", "priority": "0.8"},
        {"loc": f"{base_url}/case-studies", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{base_url}/downloads", "changefreq": "weekly", "priority": "0.7"},
        {"loc": f"{base_url}/contact", "changefreq": "monthly", "priority": "0.8"},
        {"loc": f"{base_url}/request-a-quote", "changefreq": "weekly", "priority": "0.9"},
    ]
    
    seen_urls = set()
    entries = []
    
    for page in static_pages:
        if page["loc"] not in seen_urls:
            seen_urls.add(page["loc"])
            entries.append(page)
            
    # Active Categories
    categories = db.query(ProductCategory).filter(ProductCategory.is_active == True).all()
    for cat in categories:
        loc = f"{base_url}/products/{cat.slug}"
        if loc not in seen_urls:
            seen_urls.add(loc)
            entries.append({
                "loc": loc,
                "changefreq": "weekly",
                "priority": "0.8",
                "lastmod": cat.updated_at.strftime("%Y-%m-%d") if hasattr(cat, "updated_at") and cat.updated_at else None,
            })

    # Published Products
    products = db.query(Product).filter(Product.status == "published").all()
    for prod in products:
        cat_slug = prod.category.slug if prod.category else "general"
        loc = f"{base_url}/products/{cat_slug}/{prod.slug}"
        if loc not in seen_urls:
            seen_urls.add(loc)
            lastmod = None
            if hasattr(prod, "updated_at") and prod.updated_at:
                lastmod = prod.updated_at.strftime("%Y-%m-%d")
            elif hasattr(prod, "created_at") and prod.created_at:
                lastmod = prod.created_at.strftime("%Y-%m-%d")
            entries.append({
                "loc": loc,
                "changefreq": "weekly",
                "priority": "0.7",
                "lastmod": lastmod,
            })

    # Published Capabilities
    capabilities = db.query(Capability).filter(Capability.status == "published").all()
    for cap in capabilities:
        loc = f"{base_url}/capabilities/{cap.slug}"
        if loc not in seen_urls:
            seen_urls.add(loc)
            lastmod = None
            if hasattr(cap, "updated_at") and cap.updated_at:
                lastmod = cap.updated_at.strftime("%Y-%m-%d")
            entries.append({
                "loc": loc,
                "changefreq": "monthly",
                "priority": "0.7",
                "lastmod": lastmod,
            })
            
    # Published Industries
    industries = db.query(Industry).filter(Industry.status == "published").all()
    for ind in industries:
        loc = f"{base_url}/industries/{ind.slug}"
        if loc not in seen_urls:
            seen_urls.add(loc)
            lastmod = None
            if hasattr(ind, "updated_at") and ind.updated_at:
                lastmod = ind.updated_at.strftime("%Y-%m-%d")
            entries.append({
                "loc": loc,
                "changefreq": "monthly",
                "priority": "0.7",
                "lastmod": lastmod,
            })
            
    # Published Materials
    materials = db.query(Material).filter(Material.status == "published").all()
    for mat in materials:
        loc = f"{base_url}/materials/{mat.slug}"
        if loc not in seen_urls:
            seen_urls.add(loc)
            lastmod = None
            if hasattr(mat, "updated_at") and mat.updated_at:
                lastmod = mat.updated_at.strftime("%Y-%m-%d")
            entries.append({
                "loc": loc,
                "changefreq": "monthly",
                "priority": "0.7",
                "lastmod": lastmod,
            })

    # Published Blog Posts
    now = datetime.now(timezone.utc)
    blog_posts = db.query(BlogPost).filter(
        BlogPost.status == BlogPostStatus.PUBLISHED.value,
        BlogPost.publish_date <= now,
    ).all()
    for post in blog_posts:
        loc = f"{base_url}/blog/{post.slug}"
        if loc not in seen_urls:
            seen_urls.add(loc)
            lastmod = post.updated_at.strftime("%Y-%m-%d") if hasattr(post, "updated_at") and post.updated_at else None
            entries.append({
                "loc": loc,
                "changefreq": "weekly",
                "priority": "0.7",
                "lastmod": lastmod,
            })

    # Published Case Studies
    case_studies = db.query(CaseStudy).filter(CaseStudy.status == "published").all()
    for cs in case_studies:
        loc = f"{base_url}/case-studies/{cs.slug}"
        if loc not in seen_urls:
            seen_urls.add(loc)
            lastmod = cs.updated_at.strftime("%Y-%m-%d") if hasattr(cs, "updated_at") and cs.updated_at else None
            entries.append({
                "loc": loc,
                "changefreq": "monthly",
                "priority": "0.7",
                "lastmod": lastmod,
            })

    # Published Dynamic CMS Pages
    cms_pages = page_service.get_all_published_pages(db)
    for p in cms_pages:
        loc = f"{base_url}{p.url_path}"
        if loc not in seen_urls:
            seen_urls.add(loc)
            lastmod = p.updated_at.strftime("%Y-%m-%d") if p.updated_at else None
            entries.append({
                "loc": loc,
                "changefreq": "weekly",
                "priority": "0.8",
                "lastmod": lastmod,
            })

    # Build XML
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for e in entries:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{e['loc']}</loc>")
        if e.get("lastmod"):
            xml_lines.append(f"    <lastmod>{e['lastmod']}</lastmod>")
        if e.get("changefreq"):
            xml_lines.append(f"    <changefreq>{e['changefreq']}</changefreq>")
        if e.get("priority"):
            xml_lines.append(f"    <priority>{e['priority']}</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")

    return Response(content="\n".join(xml_lines), media_type="application/xml")


@router.get("/robots.txt", summary="Robots.txt Specification")
async def robots_txt(request: Request):
    """
    Renders robots.txt directives, disallowing admin areas and pointing to sitemap.xml.
    """
    base_url = settings.SITE_URL.rstrip("/") if settings.SITE_URL else str(request.base_url).rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /static/uploads/private/",
        "",
        f"Sitemap: {base_url}/sitemap.xml",
        "",
    ]
    return Response(content="\n".join(lines), media_type="text/plain")


# ==============================================================================
# DYNAMIC CMS PAGES & 301 REDIRECTS CATCH-ALL ROUTE
# ==============================================================================

@router.get("/{slug:path}", response_class=HTMLResponse, summary="Dynamic CMS Page & 301 Redirect Resolver")
async def dynamic_page_view(
    slug: str,
    request: Request,
    preview: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Resolves dynamic CMS pages by hierarchical slug (/about-us, /about-us/company-profile),
    executes permanent 301 redirects for legacy URLs, and handles draft previews for admins.
    """
    clean_slug = slug.strip("/")

    # 1. Attempt CMS Page Lookup
    page_item = page_service.get_page_by_slug(db, clean_slug, include_draft=True)
    if page_item:
        if not page_item.is_published:
            # Only authenticated admins may view draft pages
            user = auth_service.get_current_user_from_cookie(db, request)
            if not user or not user.is_active:
                raise HTTPException(status_code=404, detail="Page not found.")

        return templates.TemplateResponse(
            request=request,
            name="public/pages/detail.html",
            context={
                "request": request,
                "page": page_item,
                "is_preview": bool(preview),
            },
        )

    # 2. Attempt Permanent 301 Redirect Resolution
    redirect_rule = page_service.resolve_redirect(db, clean_slug)
    if redirect_rule:
        target_path = redirect_rule.target_path
        if not target_path.startswith("/"):
            target_path = f"/{target_path}"
        return RedirectResponse(
            url=target_path,
            status_code=redirect_rule.status_code or 301,
        )

    # 3. Not Found
    raise HTTPException(status_code=404, detail="Page not found.")



