import io
import re
import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.product import Product, ProductCategory
from app.models.infrastructure import Equipment
from app.models.quality import Certification
from app.models.blog import BlogPost, BlogPostStatus
from app.models.redirect import URLRedirect
from app.models.setting import SiteSetting
from app.models.media import MediaAsset
from app.services.seo_service import seo_service, slugify
from app.services.sitemap_service import sitemap_service
from app.services.redirect_service import redirect_service
from app.services.media_service import media_service
from app.services.seo_audit_service import seo_audit_service
from app.services.upload_service import upload_service


# ==============================================================================
# Helper to authenticate client
# ==============================================================================

def login_superadmin(client: TestClient, superadmin_user: User):
    resp = client.post(
        "/admin/login",
        data={
            "email": superadmin_user.email,
            "password": "SuperSecret@123",
            "next": "/admin",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302


# ==============================================================================
# 1. UNAUTHORIZED ADMIN ACCESS TESTS
# ==============================================================================

def test_unauthorized_admin_access_redirects_to_login(client):
    """Verifies unauthenticated visitors cannot access administrative routes."""
    protected_urls = [
        "/admin",
        "/admin/products",
        "/admin/media",
        "/admin/redirects",
        "/admin/seo/audit",
        "/admin/settings/seo",
    ]
    for url in protected_urls:
        # Browser request with Accept: text/html receives redirect
        resp_browser = client.get(url, headers={"Accept": "text/html"}, follow_redirects=False)
        assert resp_browser.status_code in (302, 307), f"Expected redirect for {url}, got {resp_browser.status_code}"
        assert "/admin/login" in resp_browser.headers["Location"], f"Expected redirect to login for {url}"

        # API/direct client request returns 401 or redirect
        resp_api = client.get(url, follow_redirects=False)
        assert resp_api.status_code in (401, 302, 307), f"Expected 401 or redirect for {url}, got {resp_api.status_code}"


# ==============================================================================
# 2. MALFORMED UPLOADS & FILE SECURITY TESTS
# ==============================================================================

def test_malformed_upload_executable_rejected(client, superadmin_user):
    """Verifies that executable and script uploads are strictly rejected."""
    login_superadmin(client, superadmin_user)

    dangerous_files = [
        ("malware.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload"),
        ("exploit.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh"),
        ("script.ps1", b"Write-Host 'hack'", "text/plain"),
        ("payload.jar", b"PK\x03\x04", "application/java-archive"),
    ]

    for filename, content, mime in dangerous_files:
        resp = client.post(
            "/admin/media/upload",
            files={"file": (filename, content, mime)},
            data={"seo_filename": "test-exploit", "alt_text": "Exploit"},
            follow_redirects=False,
        )
        # Should redirect back with error or fail validation
        assert resp.status_code == 302
        assert "error" in resp.headers.get("Location", "")


def test_upload_service_null_byte_rejection():
    """Verifies that null-byte injections are rejected by upload_service."""
    with pytest.raises(Exception) as excinfo:
        upload_service.validate_image_file(
            upload_file=type("DummyUpload", (), {"filename": "exploit.png\x00.exe", "content_type": "image/png"})(),
            content=b"dummycontent",
        )
    assert "null" in str(excinfo.value.detail).lower() or "dangerous" in str(excinfo.value.detail).lower()


def test_upload_service_path_traversal_prevention():
    """Verifies that directory traversal attacks in filenames are stopped."""
    with pytest.raises(Exception) as excinfo:
        upload_service.validate_image_file(
            upload_file=type("DummyUpload", (), {"filename": "../../../../etc/shadow.png", "content_type": "image/png"})(),
            content=b"dummycontent",
        )
    assert "traversal" in str(excinfo.value.detail).lower()


# ==============================================================================
# 3. DUPLICATE SLUG GENERATION & HANDLING TESTS
# ==============================================================================

def test_ensure_unique_slug(db: Session):
    """Verifies that duplicate slugs automatically append numbered increments."""
    # Create first product
    slug1 = seo_service.ensure_unique_slug(db, Product, "Turbine Shaft", "turbine-shaft")
    assert slug1 == "turbine-shaft"

    p1 = Product(
        name="Turbine Shaft",
        slug=slug1,
        short_description="High-precision turbine shaft",
        status="published",
    )
    db.add(p1)
    db.commit()

    # Create second product with identical name
    slug2 = seo_service.ensure_unique_slug(db, Product, "Turbine Shaft", "turbine-shaft")
    assert slug2 == "turbine-shaft-2"

    p2 = Product(
        name="Turbine Shaft",
        slug=slug2,
        short_description="Another turbine shaft",
        status="published",
    )

    db.add(p2)
    db.commit()

    # Create third product
    slug3 = seo_service.ensure_unique_slug(db, Product, "Turbine Shaft", "turbine-shaft")
    assert slug3 == "turbine-shaft-3"


# ==============================================================================
# 4. REDIRECT LOOPS & CYCLE DETECTION TESTS
# ==============================================================================

def test_redirect_loop_prevention(db: Session):
    """Verifies that self-redirects and cyclic redirect loops are prevented."""
    # Self-redirect attempt
    rule_self, err_self = redirect_service.create_redirect(db, "/old-page", "/old-page", 301)
    assert rule_self is None
    assert "self-redirect" in err_self.lower()

    # Create rule A -> B
    rule1, err1 = redirect_service.create_redirect(db, "/page-a", "/page-b", 301)
    assert rule1 is not None and rule1.id is not None

    # Attempt rule B -> A (direct cycle)
    rule_cycle, err_cycle = redirect_service.create_redirect(db, "/page-b", "/page-a", 301)
    assert rule_cycle is None
    assert "cycle" in err_cycle.lower() or "loop" in err_cycle.lower()

    # Attempt 3-step cycle: A -> B -> C, then C -> A
    rule2, err2 = redirect_service.create_redirect(db, "/page-b", "/page-c", 301)
    assert rule2 is not None

    rule_cycle3, err_cycle3 = redirect_service.create_redirect(db, "/page-c", "/page-a", 301)
    assert rule_cycle3 is None
    assert "cycle" in err_cycle3.lower() or "loop" in err_cycle3.lower()



def test_redirect_middleware_execution(client, db: Session):
    """Verifies that the redirect middleware intercepts requests and issues HTTP 301/302."""
    redirect_service.create_redirect(db, "/legacy-catalog", "/products", 301)

    resp = client.get("/legacy-catalog", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["Location"] == "/products"


# ==============================================================================
# 5. SITEMAP GENERATION TESTS
# ==============================================================================

def test_sitemap_xml_generation(client, db: Session):
    """Verifies dynamic /sitemap.xml generation, valid XML format, and exclusion rules."""
    # Ensure a product exists
    p = db.query(Product).first()
    if not p:
        p = Product(name="Aerospace Impeller", slug="aerospace-impeller", short_description="Test", status="published")
        db.add(p)
        db.commit()


    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "xml" in resp.headers.get("content-type", "")

    content = resp.text
    assert "<urlset" in content
    assert "http://www.sitemaps.org/schemas/sitemap/0.9" in content
    assert "<loc>" in content
    assert "</urlset>" in content

    # Should contain public routes
    assert "/products" in content
    assert "/capabilities" in content

    # Should NEVER expose admin or private paths
    assert "/admin" not in content
    assert "/api" not in content


# ==============================================================================
# 6. ROBOTS.TXT TESTS
# ==============================================================================

def test_robots_txt_default_and_custom(client, db: Session):
    """Verifies /robots.txt disallows admin paths and references the sitemap."""
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "User-agent: *" in resp.text
    assert "Disallow: /admin/" in resp.text
    assert "Sitemap:" in resp.text

    # Test CMS custom configuration
    custom_robots = "User-agent: *\nDisallow: /admin/\nDisallow: /private/\n\nSitemap: https://custom.com/sitemap.xml\n"
    setting = db.query(SiteSetting).filter(SiteSetting.key == "seo_robots_txt").first()
    if not setting:
        setting = SiteSetting(key="seo_robots_txt", value=custom_robots, group="seo")
        db.add(setting)
    else:
        setting.value = custom_robots
    db.commit()

    resp_custom = client.get("/robots.txt")
    assert resp_custom.status_code == 200
    assert "Disallow: /private/" in resp_custom.text
    assert "https://custom.com/sitemap.xml" in resp_custom.text


# ==============================================================================
# 7. STRUCTURED DATA (JSON-LD) TESTS
# ==============================================================================

def test_json_ld_schema_generation(db: Session):
    """Verifies dynamic JSON-LD schema generation for all required schema types."""
    base_url = "https://forgingcms.com"

    # Organization
    org_schema = seo_service.generate_json_ld("organization", base_url=base_url)
    assert org_schema["@context"] == "https://schema.org"
    assert org_schema["@type"] == "Organization"
    assert "name" in org_schema
    assert "url" in org_schema

    # LocalBusiness
    local_schema = seo_service.generate_json_ld("local_business", base_url=base_url)
    assert local_schema["@type"] == "LocalBusiness"
    assert "address" in local_schema

    # Product
    test_prod = Product(
        name="Precision Forged Flange",
        slug="precision-forged-flange",
        short_description="Carbon steel forged flange",
        meta_title="Precision Forged Flange - High Pressure",
        meta_description="Heavy industrial forged flanges for petrochemical piping.",
        status="published",
    )

    prod_schema = seo_service.generate_json_ld("product", base_url=base_url, entity=test_prod)
    assert prod_schema["@type"] == "Product"
    assert prod_schema["name"] == "Precision Forged Flange"
    assert prod_schema["description"] == "Carbon steel forged flange"
    assert prod_schema["offers"]["@type"] == "Offer"

    # Article
    test_post = BlogPost(
        title="Metallurgy Breakthrough in 2026",
        slug="metallurgy-breakthrough-2026",
        excerpt="Advances in isothermal forging.",
        content="Comprehensive metallurgical testing confirms improved tensile strength.",
        status=BlogPostStatus.PUBLISHED.value,
    )
    article_schema = seo_service.generate_json_ld("article", base_url=base_url, entity=test_post)
    assert article_schema["@type"] == "BlogPosting"
    assert article_schema["headline"] == "Metallurgy Breakthrough in 2026"


    # BreadcrumbList
    crumbs = [("Home", "/"), ("Products", "/products"), ("Flanges", "/products/flanges")]
    crumb_schema = seo_service.generate_json_ld("breadcrumb", base_url=base_url, breadcrumb_items=crumbs)
    assert crumb_schema["@type"] == "BreadcrumbList"
    assert len(crumb_schema["itemListElement"]) == 3

    # FAQPage
    faqs = [{"question": "What is closed-die forging?", "answer": "A precision shaping process."}]
    faq_schema = seo_service.generate_json_ld("faq", faq_items=faqs)
    assert faq_schema["@type"] == "FAQPage"
    assert len(faq_schema["mainEntity"]) == 1

    # WebPage
    web_schema = seo_service.generate_json_ld("webpage", base_url=base_url, page_title="About Us", page_description="About FORGE", canonical_url=f"{base_url}/about")
    assert web_schema["@type"] == "WebPage"
    assert web_schema["name"] == "About Us"


# ==============================================================================
# 8. CANONICAL URLS & META TAGS ON PUBLIC PAGES
# ==============================================================================

def test_canonical_and_meta_tags_rendered_in_html(client, db: Session):
    """Verifies that public HTML templates render canonical links, OpenGraph, and Twitter tags."""
    resp = client.get("/about")
    assert resp.status_code == 200
    html = resp.text

    # Canonical
    assert '<link rel="canonical"' in html
    assert 'href="http://testserver/about"' in html or 'href="https://' in html

    # OpenGraph & Twitter
    assert 'property="og:title"' in html
    assert 'property="og:description"' in html
    assert 'name="twitter:card"' in html

    # Robots meta tag
    assert 'name="robots"' in html
    assert 'content="index, follow' in html


def test_url_normalization_middleware(client):
    """Verifies uppercase URLs or trailing slashes are cleanly normalized."""
    # Uppercase URL should redirect to lowercase
    resp = client.get("/ABOUT", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["Location"].endswith("/about")

    # Trailing slash normalization
    resp_slash = client.get("/about/", follow_redirects=False)
    assert resp_slash.status_code == 301
    assert resp_slash.headers["Location"].endswith("/about")



# ==============================================================================
# 9. HTTP SECURITY HEADERS AUDIT
# ==============================================================================

def test_http_security_headers(client):
    """Verifies that security headers (CSP, X-Frame-Options, X-Content-Type-Options, etc.) are present."""
    resp = client.get("/")
    assert resp.status_code == 200

    headers = resp.headers
    assert "x-frame-options" in headers
    assert headers["x-frame-options"].upper() in ("DENY", "SAMEORIGIN")

    assert "x-content-type-options" in headers
    assert headers["x-content-type-options"] == "nosniff"

    assert "referrer-policy" in headers
    assert "content-security-policy" in headers
    csp = headers["content-security-policy"]
    assert "default-src" in csp


# ==============================================================================
# 10. AUTOMATED SEO AUDIT ENGINE TEST
# ==============================================================================

def test_seo_audit_service_execution(client, superadmin_user, db: Session):
    """Verifies the automated SEO audit execution, JSON output, and scoring."""
    report = seo_audit_service.run_full_audit(db)
    assert "score" in report
    assert 0 <= report["score"] <= 100
    assert "total_entities_checked" in report
    assert "total_issues" in report
    assert "structured_data_validated" in report
    assert report["structured_data_validated"] > 0

    # Test via Admin View
    login_superadmin(client, superadmin_user)
    resp_view = client.get("/admin/seo/audit")
    assert resp_view.status_code == 200
    assert "Automated SEO & Structured Data Audit" in resp_view.text

    # Test via Admin JSON Endpoint
    resp_json = client.get("/admin/seo/audit/json")
    assert resp_json.status_code == 200
    data = resp_json.json()
    assert "score" in data
    assert "issues" in data
