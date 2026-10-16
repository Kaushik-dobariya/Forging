import io
import json
import pytest
from fastapi import UploadFile, HTTPException
from starlette.datastructures import Headers

from app.models.product import (
    MeasurementUnit,
    ProductCategory,
    Product,
    ProductImage,
    ProductSpecification,
)
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.infrastructure import Facility, Equipment, InfrastructureGallery
from app.models.material import Material
from app.models.quality import QualitySection, Certification
from app.utils.slug import get_unique_slug
from app.services.seed_service import seed_cms_data
from app.services.upload_service import upload_service


# ==============================================================================
# 1. MEASUREMENT SYSTEM TESTS
# ==============================================================================

def test_measurement_units_crud(db):
    """
    Verifies creation, querying, and dynamic expansion of measurement units
    for weight, length, capacity, and custom engineering parameters.
    """
    # Ensure or create units for various types
    for name, sym, utype, order in [
        ("Metric Ton (MT)", "MT", "weight", 1),
        ("Millimeter", "mm", "length", 2),
        ("Kilonewton", "kN", "capacity", 3),
        ("Custom Force Unit", "CFU", "force", 4),
    ]:
        if not db.query(MeasurementUnit).filter(MeasurementUnit.symbol == sym).first():
            db.add(MeasurementUnit(name=name, symbol=sym, unit_type=utype, display_order=order))
    db.commit()

    # Query by unit_type
    weights = db.query(MeasurementUnit).filter(MeasurementUnit.unit_type == "weight").all()
    assert any(u.symbol == "MT" for u in weights)

    lengths = db.query(MeasurementUnit).filter(MeasurementUnit.unit_type == "length").all()
    assert any(u.symbol == "mm" for u in lengths)

    capacities = db.query(MeasurementUnit).filter(MeasurementUnit.unit_type == "capacity").all()
    assert any(u.symbol == "kN" for u in capacities)

    # Verify Super Admin can add custom units
    force_units = db.query(MeasurementUnit).filter(MeasurementUnit.unit_type == "force").all()
    assert len(force_units) >= 1
    assert any(u.symbol == "CFU" for u in force_units)


# ==============================================================================
# 2. PRODUCT CATEGORIES & SLUG UNIQUENESS TESTS
# ==============================================================================

def test_product_categories_crud_and_slugs(db):
    """
    Verifies category creation, display order sorting, and duplicate slug prevention.
    """
    # 1. Create first category
    slug1 = get_unique_slug(db, ProductCategory, "Flanges & Rings")
    assert slug1 == "flanges-rings"

    cat1 = ProductCategory(
        name="Flanges & Rings",
        slug=slug1,
        description="Heavy industrial forged flanges and rolled rings.",
        display_order=10,
        is_active=True,
    )
    db.add(cat1)
    db.commit()
    db.refresh(cat1)
    assert cat1.id is not None

    # 2. Verify duplicate name generates unique slug with -2 suffix
    slug2 = get_unique_slug(db, ProductCategory, "Flanges & Rings")
    assert slug2 == "flanges-rings-2"

    cat2 = ProductCategory(
        name="Flanges & Rings",
        slug=slug2,
        description="Second duplicate line.",
        display_order=20,
        is_active=True,
    )
    db.add(cat2)
    db.commit()

    # Verify editing same entity preserves its slug
    slug1_preserved = get_unique_slug(db, ProductCategory, "Flanges & Rings", current_id=cat1.id)
    assert slug1_preserved == "flanges-rings"

    # Query ordering
    ordered_cats = db.query(ProductCategory).order_by(ProductCategory.display_order.asc()).all()
    assert ordered_cats[0].display_order <= ordered_cats[1].display_order


# ==============================================================================
# 3. PRODUCTS & FLEXIBLE SPECIFICATIONS ARCHITECTURE TESTS
# ==============================================================================

def test_products_crud_and_flexible_specs(db):
    """
    Verifies full product creation with specifications (name, value, unit, display_order),
    images, and comprehensive technical fields.
    """
    cat = ProductCategory(
        name="Shafts & Rotors",
        slug="shafts-rotors",
        is_active=True,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)

    prod_slug = get_unique_slug(db, Product, "Forged Turbine Shaft")
    assert prod_slug == "forged-turbine-shaft"

    product = Product(
        name="Forged Turbine Shaft",
        slug=prod_slug,
        category_id=cat.id,
        short_description="Precision step shaft forged for power generation turbines.",
        detailed_description="Manufactured under 4000 MT open-die press with strict ultrasonic cleanliness.",
        applications="Power Generation, Heavy Turbomachinery",
        material="42CrMo4 / AISI 4140 Alloy Steel",
        weight_range="500 kg - 12,000 kg",
        dimensions="Max OD 900 mm x Length 6,500 mm",
        manufacturing_process="Open Die Ingot Forging, Heat Treatment, Rough CNC Turning",
        forging_capacity="Up to 15 MT single-piece ingot",
        heat_treatment="Quenched & Tempered (Q+T), Stress Relieved",
        machining="Rough turned or finish CNC machined to Ra 0.8",
        surface_finish="Anti-rust oiled / painted",
        testing="100% Ultrasonic Testing (UT), Magnetic Particle (MPI), Spectro Chemistry",
        meta_title="Forged Turbine Rotor Shafts | 4140 Alloy Steel",
        meta_description="Heavy forged turbine shafts up to 12 MT with complete EN 10204 3.1 inspection certification.",
        status="published",
        display_order=1,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Add flexible specifications: Weight | 5 | kg, Length | 250 | mm, Capacity | 500 | MT
    spec1 = ProductSpecification(product_id=product.id, name="Weight", value="5000", unit="kg", display_order=1)
    spec2 = ProductSpecification(product_id=product.id, name="Length", value="6500", unit="mm", display_order=2)
    spec3 = ProductSpecification(product_id=product.id, name="Forging Capacity", value="4000", unit="MT", display_order=3)
    spec4 = ProductSpecification(product_id=product.id, name="Tensile Strength", value="850 - 1000", unit="MPa", display_order=4)

    # Add gallery image
    img1 = ProductImage(product_id=product.id, image_url="/static/images/turbine_shaft.webp", is_primary=True, display_order=1)

    db.add_all([spec1, spec2, spec3, spec4, img1])
    db.commit()
    db.refresh(product)

    # Verify specs persisted and ordered
    assert len(product.specifications) == 4
    sorted_specs = sorted(product.specifications, key=lambda s: s.display_order)
    assert sorted_specs[0].name == "Weight"
    assert sorted_specs[0].value == "5000"
    assert sorted_specs[0].unit == "kg"
    assert sorted_specs[1].name == "Length"
    assert sorted_specs[1].unit == "mm"
    assert sorted_specs[2].name == "Forging Capacity"
    assert sorted_specs[2].unit == "MT"

    # Verify images
    assert len(product.images) == 1
    assert product.images[0].is_primary is True

    # Test duplicate product slug generation
    prod_slug2 = get_unique_slug(db, Product, "Forged Turbine Shaft")
    assert prod_slug2 == "forged-turbine-shaft-2"


# ==============================================================================
# 4. RELATIONSHIPS & ASSOCIATION TABLES TESTS
# ==============================================================================

def test_many_to_many_relationships(db):
    """
    Verifies many-to-many relationship mappings:
    Products <-> Capabilities
    Products <-> Industries
    Products <-> Materials
    Products <-> Equipment
    Capabilities <-> Equipment
    Capabilities <-> Materials
    Industries <-> Products
    Industries <-> Capabilities
    Products <-> Related Products
    """
    # Create Entities with isolated slugs
    cat = db.query(ProductCategory).filter(ProductCategory.slug == "heavy-rings-rel").first()
    if not cat:
        cat = ProductCategory(name="Heavy Rings Rel", slug="heavy-rings-rel")
        db.add(cat)

    cap = db.query(Capability).filter(Capability.slug == "ring-rolling-rel").first()
    if not cap:
        cap = Capability(title="Ring Rolling Rel", slug="ring-rolling-rel", capacity="OD 3500 mm")
        db.add(cap)

    ind = db.query(Industry).filter(Industry.slug == "oil-gas-rel").first()
    if not ind:
        ind = Industry(name="Oil & Gas Rel", slug="oil-gas-rel", short_description="Subsea and wellhead components.")
        db.add(ind)

    mat = db.query(Material).filter(Material.slug == "alloy-steel-4140-rel").first()
    if not mat:
        mat = Material(name="Alloy Steel 4140 Rel", slug="alloy-steel-4140-rel", grade="AISI 4140")
        db.add(mat)

    eq = db.query(Equipment).filter(Equipment.name == "3500mm CNC Ring Rolling Mill Rel").first()
    if not eq:
        eq = Equipment(name="3500mm CNC Ring Rolling Mill Rel", category="Mechanical Press", capacity="3500 mm OD")
        db.add(eq)
    
    prod1 = db.query(Product).filter(Product.slug == "forged-wellhead-ring-rel").first()
    if not prod1:
        prod1 = Product(name="Forged Wellhead Ring Rel", slug="forged-wellhead-ring-rel", category=cat)
        db.add(prod1)

    prod2 = db.query(Product).filter(Product.slug == "blind-flange-24-inch-rel").first()
    if not prod2:
        prod2 = Product(name="Blind Flange 24-inch Rel", slug="blind-flange-24-inch-rel", category=cat)
        db.add(prod2)

    db.commit()

    # Link relationships
    if cap not in prod1.capabilities: prod1.capabilities.append(cap)
    if ind not in prod1.industries: prod1.industries.append(ind)
    if mat not in prod1.materials: prod1.materials.append(mat)
    if eq not in prod1.equipment: prod1.equipment.append(eq)
    if prod2 not in prod1.related_products: prod1.related_products.append(prod2)

    if eq not in cap.equipment: cap.equipment.append(eq)
    if mat not in cap.materials: cap.materials.append(mat)
    if ind not in cap.industries: cap.industries.append(ind)

    db.commit()
    db.refresh(prod1)
    db.refresh(cap)
    db.refresh(ind)
    db.refresh(mat)
    db.refresh(eq)

    # 1. Product reciprocals
    assert cap in prod1.capabilities
    assert ind in prod1.industries
    assert mat in prod1.materials
    assert eq in prod1.equipment
    assert prod2 in prod1.related_products

    # 2. Capability reciprocals
    assert prod1 in cap.products
    assert eq in cap.equipment
    assert mat in cap.materials
    assert ind in cap.industries

    # 3. Industry reciprocals
    assert prod1 in ind.products
    assert cap in ind.capabilities

    # 4. Material reciprocals
    assert prod1 in mat.products
    assert cap in mat.capabilities

    # 5. Equipment reciprocals
    assert prod1 in eq.products
    assert cap in eq.capabilities


# ==============================================================================
# 5. CAPABILITIES, INFRASTRUCTURE, MATERIALS, QUALITY CRUD TESTS
# ==============================================================================

def test_capabilities_and_faqs(db):
    """Verifies capability model with JSON FAQs and engineering envelope."""
    faqs_data = [
        {"question": "What is the maximum piece weight?", "answer": "Up to 15 MT single-piece forging."},
        {"question": "What heat treatment can be provided?", "answer": "Normalizing, Annealing, and Quench & Tempering."},
    ]
    cap = Capability(
        title="Open Die Forging",
        slug="open-die-forging-test",
        short_description="Heavy open-die forging.",
        detailed_description="Detailed manufacturing method with custom tooling.",
        capacity="15 MT",
        dimensions="12,000 mm Length",
        process="Billet Pre-heat -> Hydraulic Press Cogging -> Annealing",
        faqs_json=json.dumps(faqs_data),
        status="published",
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)

    parsed_faqs = json.loads(cap.faqs_json)
    assert len(parsed_faqs) == 2
    assert parsed_faqs[0]["question"] == "What is the maximum piece weight?"


def test_infrastructure_facilities_and_equipment(db):
    """Verifies facilities, machinery equipment, and infrastructure gallery."""
    fac = Facility(
        name="Forge Shop Unit 1",
        category="Forging Shop",
        capacity="25,000 MT / annum",
        specifications="Housing 4000 MT & 2500 MT hydraulic presses.",
        status="published",
    )
    eq = Equipment(
        name="4000 MT Hydraulic Open Die Press",
        category="Hydraulic Press",
        manufacturer="Schuler",
        model="HP-4000-OD",
        capacity="4000 MT",
        pdf_url="/uploads/brochures/press_4000mt.pdf",
        status="published",
    )
    gallery = InfrastructureGallery(
        title="Plant Aerial View",
        image_url="/static/images/facility_aerial.webp",
        caption="120,000 sq ft covered manufacturing area.",
        is_active=True,
    )
    db.add_all([fac, eq, gallery])
    db.commit()
    db.refresh(fac)
    db.refresh(eq)

    assert fac.id is not None
    assert eq.manufacturer == "Schuler"
    assert eq.pdf_url == "/uploads/brochures/press_4000mt.pdf"


def test_quality_sections_and_certifications(db):
    """Verifies modular quality sections and certification records."""
    sec = QualitySection(
        section_key="testing_facilities",
        title="Metallurgical Testing Laboratories",
        subtitle="In-house NABL Accredited Laboratory",
        content="Equipped with optical emission spectrometer, 1000 kN UTM tensile tester, and Charpy impact tester.",
        is_active=True,
    )
    cert = Certification(
        certificate_name="ISO 9001:2015",
        issuing_organization="TUV NORD",
        certificate_number="04 100 2026 8991",
        issue_date="2024-01-15",
        expiry_date="2027-01-14",
        certificate_image="/uploads/certifications/iso9001.webp",
        certificate_pdf="/uploads/certifications/iso9001.pdf",
        status="published",
    )
    db.add_all([sec, cert])
    db.commit()
    db.refresh(sec)
    db.refresh(cert)

    assert sec.section_key == "testing_facilities"
    assert cert.issuing_organization == "TUV NORD"
    assert cert.certificate_pdf == "/uploads/certifications/iso9001.pdf"


# ==============================================================================
# 6. UPLOAD SERVICE SECURITY & PDF VALIDATION TESTS
# ==============================================================================

def test_pdf_upload_validation_service():
    """
    Verifies that upload_service.validate_document_file strictly enforces
    .pdf extension, application/pdf MIME type, and %PDF- magic byte signature.
    """
    # 1. Valid PDF bytes
    valid_pdf_content = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    valid_file = UploadFile(
        file=io.BytesIO(valid_pdf_content),
        filename="datasheet.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    # validate_document_file expects (upload_file, content)
    upload_service.validate_document_file(valid_file, valid_pdf_content)

    # 2. Invalid extension
    invalid_ext = UploadFile(
        file=io.BytesIO(valid_pdf_content),
        filename="malicious.exe",
        headers=Headers({"content-type": "application/pdf"}),
    )
    with pytest.raises(HTTPException) as exc1:
        upload_service.validate_document_file(invalid_ext, valid_pdf_content)
    assert exc1.value.status_code == 400
    assert "Unsupported document extension" in exc1.value.detail

    # 3. Spoofed magic bytes
    fake_content = b"MZ\x90\x00\x03\x00\x00\x00FAKE_EXECUTABLE_CONTENT"
    fake_pdf = UploadFile(
        file=io.BytesIO(fake_content),
        filename="spoofed.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    with pytest.raises(HTTPException) as exc2:
        upload_service.validate_document_file(fake_pdf, fake_content)
    assert exc2.value.status_code == 400
    assert "Invalid or corrupt PDF" in exc2.value.detail


# ==============================================================================
# 7. PUBLIC ROUTES & SEO RENDERING TESTS
# ==============================================================================

def test_public_cms_routes_rendering(client, db):
    """
    Seeds initial engineering data and tests all public Jinja pages:
    /products
    /products/{category}
    /products/{category}/{product}
    /capabilities
    /capabilities/{slug}
    /industries
    /industries/{slug}
    /infrastructure
    /materials
    /materials/{slug}
    /quality
    /certifications
    """
    # Seed database
    seed_cms_data(db)

    # 1. /products index
    resp_prods = client.get("/products")
    assert resp_prods.status_code == 200
    assert "Precision Engineered Components" in resp_prods.text
    assert "Forged Heavy-Duty Crankshaft" in resp_prods.text or "Heavy Industrial Forged Components" in resp_prods.text

    # 2. /products/{category}
    resp_cat = client.get("/products/closed-die-forgings")
    assert resp_cat.status_code == 200
    assert "Closed Die Forgings" in resp_cat.text

    # 3. /products/{category}/{product} (Canonical match)
    resp_prod_detail = client.get("/products/closed-die-forgings/forged-heavy-duty-crankshaft")
    assert resp_prod_detail.status_code == 200
    assert "Forged Heavy-Duty Crankshaft" in resp_prod_detail.text
    assert "Key Manufacturing Parameters" in resp_prod_detail.text or "Technical Parameter Breakdown" in resp_prod_detail.text
    # Verify specification rows rendered
    assert "Weight" in resp_prod_detail.text
    assert "kg" in resp_prod_detail.text

    # 4. Canonical SEO mismatch prevention: wrong category slug returns 404
    resp_wrong_cat = client.get("/products/open-die-forgings/forged-heavy-duty-crankshaft")
    assert resp_wrong_cat.status_code == 404

    # 5. /capabilities index
    resp_caps = client.get("/capabilities")
    assert resp_caps.status_code == 200
    assert "Capabilities" in resp_caps.text
    assert "Open Die Forging" in resp_caps.text

    # 6. /capabilities/{slug}
    resp_cap_detail = client.get("/capabilities/open-die-forging")
    assert resp_cap_detail.status_code == 200
    assert "Open Die Forging" in resp_cap_detail.text
    assert "Capability Envelope" in resp_cap_detail.text
    assert "Frequently Asked Questions" in resp_cap_detail.text

    # 7. /industries index
    resp_ind = client.get("/industries")
    assert resp_ind.status_code == 200
    assert "Target Industries" in resp_ind.text
    assert "Oil & Gas" in resp_ind.text or "Oil &amp; Gas" in resp_ind.text

    # 8. /industries/{slug}
    resp_ind_detail = client.get("/industries/oil-gas")
    assert resp_ind_detail.status_code == 200
    assert "Oil & Gas" in resp_ind_detail.text or "Oil &amp; Gas" in resp_ind_detail.text
    assert "Critical Components Manufactured" in resp_ind_detail.text

    # 9. /infrastructure
    resp_infra = client.get("/infrastructure")
    assert resp_infra.status_code == 200
    assert "Machinery Fleet" in resp_infra.text or "Infrastructure" in resp_infra.text
    assert "Hydraulic Press" in resp_infra.text

    # 10. /materials index
    resp_mat = client.get("/materials")
    assert resp_mat.status_code == 200
    assert "Material Grades" in resp_mat.text
    assert "Alloy Steel" in resp_mat.text or "Carbon Steel" in resp_mat.text

    # 11. /materials/{slug}
    resp_mat_detail = client.get("/materials/alloy-steel")
    assert resp_mat_detail.status_code == 200
    assert "Alloy Steel" in resp_mat_detail.text
    assert "Chemical Summary" in resp_mat_detail.text

    # 12. /quality
    resp_quality = client.get("/quality")
    assert resp_quality.status_code == 200
    assert "Quality Assurance" in resp_quality.text
    assert "6-Stage Quality Assurance Lifecycle" in resp_quality.text

    # 13. /certifications
    resp_certs = client.get("/certifications")
    assert resp_certs.status_code == 200
    assert "Certifications" in resp_certs.text
    assert "ISO 9001:2015" in resp_certs.text
    assert "Download PDF" in resp_certs.text or "View Certificate" in resp_certs.text


# ==============================================================================
# 8. ADMIN UI NAVIGATION & CRUD ENDPOINTS TESTS
# ==============================================================================

def test_admin_cms_views_and_crud(client, db, superadmin_user):
    """
    Verifies Super Admin control panel navigation and creation forms across all Phase 3 modules:
    - Products
    - Categories
    - Measurement Units
    - Capabilities
    - Industries
    - Infrastructure Facilities & Equipment
    - Materials
    - Quality & Testing
    - Certifications
    """
    # Reset lockout in case earlier tests locked the account
    superadmin_user.failed_login_attempts = 0
    superadmin_user.locked_until = None
    db.commit()

    # 1. Login as Super Admin
    login_resp = client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 302

    # 2. Check Admin views return 200
    admin_routes = [
        "/admin/products",
        "/admin/products/create",
        "/admin/products/categories",
        "/admin/products/categories/create",
        "/admin/products/units",
        "/admin/products/units/create",
        "/admin/capabilities",
        "/admin/capabilities/create",
        "/admin/industries",
        "/admin/industries/create",
        "/admin/infrastructure/facilities",
        "/admin/infrastructure/facilities/create",
        "/admin/infrastructure/equipment",
        "/admin/infrastructure/equipment/create",
        "/admin/infrastructure/gallery",
        "/admin/materials",
        "/admin/materials/create",
        "/admin/quality",
        "/admin/quality/testing",
        "/admin/certifications",
        "/admin/certifications/create",
    ]

    for route in admin_routes:
        resp = client.get(route)
        assert resp.status_code == 200, f"Route {route} failed with status {resp.status_code}"

    # 3. Test Admin creation of Measurement Unit
    unit_create_resp = client.post(
        "/admin/products/units/create",
        data={
            "name": "Megapascal",
            "symbol": "MPa_admin_test",
            "unit_type": "pressure",
            "display_order": 99,
        },
        follow_redirects=False,
    )
    assert unit_create_resp.status_code == 302
    assert "/admin/specifications" in unit_create_resp.headers["Location"] or "/admin/products/units" in unit_create_resp.headers["Location"]

    # Verify unit in DB
    created_unit = db.query(MeasurementUnit).filter(MeasurementUnit.symbol == "MPa_admin_test").first()
    assert created_unit is not None
    assert created_unit.unit_type == "pressure"

    # 4. Test Admin creation of Product Category
    cat_create_resp = client.post(
        "/admin/products/categories/create",
        data={
            "name": "Custom Die Blocks",
            "slug": "",  # Auto-generate slug
            "short_description": "Machined and tempered die blocks for drop forging.",
            "display_order": 5,
            "status": "published",
        },
        follow_redirects=False,
    )
    assert cat_create_resp.status_code == 302
    assert "/admin/categories" in cat_create_resp.headers["Location"] or "/admin/products/categories" in cat_create_resp.headers["Location"]

    created_cat = db.query(ProductCategory).filter(ProductCategory.slug == "custom-die-blocks").first()
    assert created_cat is not None
    assert created_cat.name == "Custom Die Blocks"
