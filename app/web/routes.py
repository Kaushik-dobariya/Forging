import json
from typing import Optional, List, Dict
from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse
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

router = APIRouter(tags=["Public Web"])


# ==============================================================================
# HOMEPAGE
# ==============================================================================

@router.get("/", response_class=HTMLResponse, summary="Public Homepage")
async def index_view(request: Request, db: Session = Depends(get_db)):
    """Renders the public corporate website homepage with dynamic CMS data."""
    capabilities = db.query(Capability).filter(Capability.status == "published").order_by(Capability.display_order.asc()).limit(6).all()
    industries = db.query(Industry).filter(Industry.status == "published").order_by(Industry.display_order.asc()).limit(6).all()
    featured_products = db.query(Product).filter(Product.status == "published").order_by(Product.display_order.asc()).limit(4).all()
    certifications = db.query(Certification).filter(Certification.status == "published").order_by(Certification.display_order.asc()).limit(4).all()

    return templates.TemplateResponse(
        request=request,
        name="public/index.html",
        context={
            "request": request,
            "capabilities": capabilities,
            "industries": industries,
            "featured_products": featured_products,
            "certifications": certifications,
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
# SEO: SITEMAP & ROBOTS.TXT
# ==============================================================================

@router.get("/sitemap.xml", summary="Public XML Sitemap")
async def sitemap_xml(request: Request, db: Session = Depends(get_db)):
    """
    Generates dynamic XML sitemap compliant with sitemaps.org schema.
    Includes only published public content, deduplicated, excluding admin and authentication pages.
    """
    base_url = settings.SITE_URL.rstrip("/") if settings.SITE_URL else str(request.base_url).rstrip("/")
    
    # Priority & Changefreq mapping for core static landing pages
    static_pages = [
        {"loc": f"{base_url}/", "changefreq": "weekly", "priority": "1.0"},
        {"loc": f"{base_url}/products", "changefreq": "daily", "priority": "0.9"},
        {"loc": f"{base_url}/capabilities", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{base_url}/industries", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{base_url}/infrastructure", "changefreq": "monthly", "priority": "0.8"},
        {"loc": f"{base_url}/materials", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{base_url}/quality", "changefreq": "monthly", "priority": "0.8"},
        {"loc": f"{base_url}/certifications", "changefreq": "monthly", "priority": "0.8"},
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

