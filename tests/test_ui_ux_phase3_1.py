import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product, ProductCategory
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.material import Material
from app.models.quality import Certification
from app.core.config import settings


def login_superadmin(client: TestClient) -> None:
    """Helper to log in as superadmin."""
    login_resp = client.post(
        "/admin/login",
        data={"email": "supertest@forgingcms.com", "password": "SuperSecret@123"},
        follow_redirects=True,
    )
    assert login_resp.status_code == 200


# ==============================================================================
# SITEMAP & ROBOTS.TXT TESTS
# ==============================================================================

def test_sitemap_xml_structure_and_routes(client: TestClient, db: Session):
    """Verifies that /sitemap.xml is valid XML, includes published content, and excludes admin routes."""
    # Seed a published category and product
    cat = ProductCategory(name="Heavy Closed Die", slug="heavy-closed-die", is_active=True, display_order=1)
    db.add(cat)
    db.commit()
    db.refresh(cat)

    prod_pub = Product(
        name="Precision Forged Flange",
        slug="precision-forged-flange",
        category_id=cat.id,
        status="published",
        display_order=1,
    )
    prod_draft = Product(
        name="Experimental Draft Gear",
        slug="experimental-draft-gear",
        category_id=cat.id,
        status="draft",
        display_order=2,
    )
    db.add_all([prod_pub, prod_draft])
    db.commit()

    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]

    xml_text = resp.text
    assert "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" in xml_text
    
    # Must include core public pages
    assert "<loc>" in xml_text
    assert "/products</loc>" in xml_text
    assert "/capabilities</loc>" in xml_text
    assert "/industries</loc>" in xml_text
    assert "/infrastructure</loc>" in xml_text
    assert "/materials</loc>" in xml_text
    assert "/quality</loc>" in xml_text
    assert "/certifications</loc>" in xml_text

    # Must include published category & product
    assert f"/products/{cat.slug}</loc>" in xml_text
    assert f"/products/{cat.slug}/{prod_pub.slug}</loc>" in xml_text

    # Must EXCLUDE draft product
    assert prod_draft.slug not in xml_text

    # Must EXCLUDE admin routes
    assert "/admin" not in xml_text
    assert "/admin/login" not in xml_text


def test_robots_txt_directives(client: TestClient):
    """Verifies robots.txt disallows admin routes and includes valid sitemap link."""
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]

    body = resp.text
    assert "User-agent: *" in body
    assert "Disallow: /admin/" in body
    assert "Sitemap:" in body
    assert "/sitemap.xml" in body


# ==============================================================================
# ADMIN UI / UX, SIDEBAR & BREADCRUMBS TESTS
# ==============================================================================

def test_admin_dashboard_ui_ux(client: TestClient, superadmin_user):
    """Verifies modernized dashboard header, breadcrumbs, metric cards, and runtime diagnostics."""
    login_superadmin(client)
    resp = client.get("/admin")
    assert resp.status_code == 200
    html = resp.text

    # Reusable sidebar elements
    assert "admin-sidebar" in html
    assert "btn-sidebar-toggle" in html
    assert "FORGING CMS" in html

    # Breadcrumbs
    assert "admin-breadcrumbs" in html
    assert "Dashboard" in html

    # Metrics grid & Metric cards
    assert "metrics-grid" in html
    assert "metric-card" in html
    assert "Manage Catalog" in html
    assert "Manage Categories" in html

    # Runtime diagnostics
    assert "System Environment & Runtime Diagnostics" in html

    # Accessible modal
    assert 'id="deleteConfirmModal"' in html
    assert 'role="dialog"' in html


def test_admin_modules_breadcrumbs_and_headers(client: TestClient, superadmin_user):
    """Verifies that all admin modules render consistent breadcrumbs, page headers, and delete triggers."""
    login_superadmin(client)

    module_routes = [
        ("/admin/products", "Products Catalog"),
        ("/admin/categories", "Product Categories"),
        ("/admin/specifications", "Measurement Units"),
        ("/admin/capabilities", "Manufacturing Capabilities"),
        ("/admin/industries", "Industries"),
        ("/admin/infrastructure/facilities", "Plant"),
        ("/admin/infrastructure/equipment", "Equipment"),
        ("/admin/infrastructure/gallery", "Gallery"),
        ("/admin/materials", "Materials"),
        ("/admin/quality", "Quality Assurance"),
        ("/admin/certifications", "Certifications"),
    ]

    for route, expected_title in module_routes:
        resp = client.get(route)
        assert resp.status_code == 200, f"Route {route} failed with status {resp.status_code}"
        html = resp.text

        # Verify page header
        assert 'class="page-header"' in html, f"Route {route} missing .page-header"

        # Verify breadcrumbs
        assert 'class="admin-breadcrumbs"' in html, f"Route {route} missing .admin-breadcrumbs"
        assert "Admin" in html

        # Verify page title
        assert 'class="page-title"' in html, f"Route {route} missing .page-title"
        assert expected_title in html, f"Route {route} missing expected title {expected_title}"
