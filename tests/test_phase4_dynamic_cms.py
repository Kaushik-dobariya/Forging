import re
import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.page import CMSPage, PageStatus
from app.models.menu import MenuItem, MenuLocation
from app.models.redirect import URLRedirect
from app.models.setting import SiteSetting, SocialLink, SocialPlatform
from app.services.page_service import page_service
from app.services.menu_service import menu_service
from app.services.settings_service import settings_service
from app.services.email_service import email_service
from app.core.security import generate_csrf_token


def extract_csrf(html_text: str) -> str:
    """Helper to extract CSRF token from HTML forms."""
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_text)
    if not match:
        match = re.search(r'value="([^"]+)"\s+name="csrf_token"', html_text)
    return match.group(1) if match else ""


def login_admin(client: TestClient) -> None:
    """Authenticates the test client as superadmin."""
    client.post(
        "/admin/login",
        data={
            "email": "supertest@forgingcms.com",
            "password": "SuperSecret@123",
        },
        follow_redirects=True,
    )


# ==============================================================================
# 1. PUBLIC ABOUT US MENU & DYNAMIC SUBMENU TESTS
# ==============================================================================

def test_about_us_menu_rendered_dynamically_in_header(client: TestClient, db: Session):
    """Verifies that the About Us navigation menu and its child items appear in header."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "About Us" in resp.text
    # Verify child links from database seeding
    assert "/about-us/company-profile" in resp.text
    assert "/about-us/vision-mission" in resp.text
    assert "/about-us/quality-policy" in resp.text


def test_about_us_cms_pages_accessible_at_configured_urls(client: TestClient, db: Session):
    """Verifies that the initial About Us parent and child CMS pages load with rich content."""
    # Parent /about-us
    resp_parent = client.get("/about-us")
    assert resp_parent.status_code == 200
    assert "About Our Industrial Forging Heritage" in resp_parent.text or "About Us" in resp_parent.text
    assert "Corporate Overview &amp; Core Identity" in resp_parent.text or "Corporate Overview & Core Identity" in resp_parent.text or "Corporate Overview" in resp_parent.text

    # Child /about-us/company-profile
    resp_child = client.get("/about-us/company-profile")
    assert resp_child.status_code == 200
    assert "Company Profile" in resp_child.text
    assert "Heavy Forging Manufacturing Leadership" in resp_child.text or "Company Profile" in resp_child.text


# ==============================================================================
# 2. DYNAMIC PAGE MANAGEMENT (ADMIN CRUD & PREVIEW)
# ==============================================================================

def test_admin_create_publish_and_view_dynamic_page(client: TestClient, db: Session, superadmin_user):
    """Verifies that an administrator can dynamically create a page, publish it, and load it."""
    login_admin(client)

    # 1. Fetch form to get CSRF
    form_resp = client.get("/admin/pages/create")
    assert form_resp.status_code == 200
    csrf = extract_csrf(form_resp.text)

    # 2. Create and publish new page
    page_data = {
        "csrf_token": csrf,
        "title": "Aerospace Forging Standards & Nadcap Accreditations",
        "slug": "aerospace-forging-standards",
        "content": "<p>Complete compliance with AS9100D and Nadcap heat treating standards for jet turbine discs.</p>",
        "menu_display_name": "Aerospace Standards",
        "menu_visibility": "true",
        "footer_visibility": "true",
        "display_order": "10",
        "page_status": "published",
        "meta_title": "Aerospace Forging Standards & Accreditations | FORGE",
        "meta_description": "Nadcap and AS9100D certified closed-die precision titanium and nickel alloy forging capabilities.",
        "meta_keywords": "aerospace forging, Nadcap, AS9100D, titanium forging",
        "canonical_url": "https://forging.example.com/aerospace-forging-standards",
        "og_title": "Aerospace Forging Standards",
        "og_description": "Nadcap certified turbine disc manufacturing.",
    }

    create_resp = client.post("/admin/pages/create", data=page_data, follow_redirects=True)
    assert create_resp.status_code == 200
    assert ("created=1" in str(create_resp.url)) or ("created successfully" in create_resp.text.lower())

    # 3. Verify public page loads at configured URL
    pub_resp = client.get("/aerospace-forging-standards")
    assert pub_resp.status_code == 200
    assert "Aerospace Forging Standards" in pub_resp.text
    assert "AS9100D and Nadcap heat treating standards" in pub_resp.text
    assert "canonical" in pub_resp.text
    assert "https://forging.example.com/aerospace-forging-standards" in pub_resp.text


def test_page_slug_change_creates_301_redirect(client: TestClient, db: Session, superadmin_user):
    """Verifies that changing a published page slug automatically creates a permanent 301 redirect."""
    login_admin(client)

    # 1. Create initial page
    page = page_service.create_page(
        db,
        {
            "title": "Legacy Metallurgical Testing Protocols",
            "slug": "legacy-testing-protocols",
            "content": "<p>Ultrasonic and magnetic particle non-destructive examination details.</p>",
            "status": "published",
        },
    )

    # Verify initial URL works
    initial_resp = client.get("/legacy-testing-protocols")
    assert initial_resp.status_code == 200

    # 2. Edit page to new slug with 301 redirect checked
    edit_resp = client.get(f"/admin/pages/{page.id}/edit")
    csrf = extract_csrf(edit_resp.text)

    update_data = {
        "csrf_token": csrf,
        "title": "Modern Metallurgical Testing Protocols",
        "slug": "modern-testing-protocols",
        "content": "<p>Updated ultrasonic testing standards conforming to EN 10228-3.</p>",
        "page_status": "published",
        "menu_visibility": "true",
        "create_redirect": "true",
    }
    update_resp = client.post(f"/admin/pages/{page.id}/edit", data=update_data, follow_redirects=True)
    assert update_resp.status_code == 200
    assert ("updated=1" in str(update_resp.url)) or ("updated successfully" in update_resp.text.lower())

    # 3. Test that old URL returns 301 redirect
    redirect_resp = client.get("/legacy-testing-protocols", follow_redirects=False)
    assert redirect_resp.status_code == 301
    assert redirect_resp.headers["Location"] == "/modern-testing-protocols"

    # 4. Test that following redirect loads the updated page
    final_resp = client.get("/legacy-testing-protocols", follow_redirects=True)
    assert final_resp.status_code == 200
    assert "Modern Metallurgical Testing Protocols" in final_resp.text


def test_draft_page_public_404_and_admin_preview(client: TestClient, db: Session, superadmin_user):
    """Verifies draft pages are inaccessible publicly (404) but previewable by admins."""
    # 1. Create a draft page
    page = page_service.create_page(
        db,
        {
            "title": "Confidential Defense Nuclear Forging Spec",
            "slug": "confidential-defense-spec",
            "content": "<p>Classified submarine propulsor shaft forging parameters.</p>",
            "status": "draft",
        },
    )

    # 2. Public anonymous visitor gets 404
    anon_client = TestClient(client.app)
    anon_resp = anon_client.get("/confidential-defense-spec")
    assert anon_resp.status_code == 404

    # 3. Authenticated admin can view draft via preview mode
    login_admin(client)
    admin_preview_resp = client.get("/confidential-defense-spec?preview=1")
    assert admin_preview_resp.status_code == 200
    assert "Draft Preview Mode" in admin_preview_resp.text or "preview" in admin_preview_resp.text.lower()
    assert "Confidential Defense Nuclear Forging Spec" in admin_preview_resp.text


def test_page_deletion_prevents_accidental_loss_of_children(client: TestClient, db: Session, superadmin_user):
    """Verifies that pages with dependent child pages cannot be deleted until children are handled."""
    login_admin(client)

    # Create parent and child
    parent = page_service.create_page(
        db,
        {"title": "Parent Research Division", "slug": "parent-research", "content": "<p>Parent</p>", "status": "published"}
    )
    child = page_service.create_page(
        db,
        {"title": "Child Advanced Labs", "slug": "parent-research/advanced-labs", "content": "<p>Child</p>", "parent_id": parent.id, "status": "published"}
    )

    # Attempt to delete parent via POST
    csrf = generate_csrf_token(superadmin_user.id)
    del_resp = client.post(f"/admin/pages/{parent.id}/delete", data={"csrf_token": csrf}, follow_redirects=True)
    assert del_resp.status_code == 200
    assert "Cannot delete page" in del_resp.text
    assert "dependent sub-page" in del_resp.text

    # Parent must still exist
    assert db.query(CMSPage).filter(CMSPage.id == parent.id).first() is not None

    # Delete child first
    client.post(f"/admin/pages/{child.id}/delete", data={"csrf_token": csrf}, follow_redirects=True)
    # Now parent deletion succeeds
    del_parent_resp = client.post(f"/admin/pages/{parent.id}/delete", data={"csrf_token": csrf}, follow_redirects=True)
    assert ("deleted=1" in str(del_parent_resp.url)) or ("deleted successfully" in del_parent_resp.text.lower())
    assert db.query(CMSPage).filter(CMSPage.id == parent.id).first() is None


# ==============================================================================
# 3. NAVIGATION MENU MANAGEMENT
# ==============================================================================

def test_menu_management_crud_and_ordering(client: TestClient, db: Session, superadmin_user):
    """Verifies admin menu management: create, toggle, and delete."""
    login_admin(client)

    csrf = generate_csrf_token(superadmin_user.id)

    # Create new header menu item
    create_data = {
        "csrf_token": csrf,
        "title": "Global Exports",
        "url": "https://export.example.com",
        "location": "header",
        "display_order": "99",
        "target": "_blank",
        "is_enabled": "true",
    }
    resp = client.post("/admin/menus/create", data=create_data, follow_redirects=True)
    assert resp.status_code == 200
    assert "Menu item created successfully" in resp.text

    # Verify menu item in DB
    item = db.query(MenuItem).filter(MenuItem.title == "Global Exports").first()
    assert item is not None
    assert item.target == "_blank"
    assert item.is_external is True

    # Toggle status
    toggle_resp = client.post(f"/admin/menus/{item.id}/toggle", data={"csrf_token": csrf}, follow_redirects=True)
    assert toggle_resp.status_code == 200
    db.refresh(item)
    assert item.is_enabled is False

    # Delete menu item
    del_resp = client.post(f"/admin/menus/{item.id}/delete", data={"csrf_token": csrf}, follow_redirects=True)
    assert del_resp.status_code == 200
    assert db.query(MenuItem).filter(MenuItem.id == item.id).first() is None


# ==============================================================================
# 4. EMAIL CONFIGURATION & TEST EMAIL
# ==============================================================================

def test_email_configuration_update_and_test_dispatch(client: TestClient, db: Session, superadmin_user):
    """Verifies email settings management, credential masking, and test email handler."""
    login_admin(client)

    csrf = generate_csrf_token(superadmin_user.id)

    # 1. Update SMTP Settings
    email_data = {
        "csrf_token": csrf,
        "contact_receiving": "inquiries@forgeprecision.com",
        "sender_name": "FORGE Industrial Systems",
        "from_address": "notifications@forgeprecision.com",
        "reply_to": "support@forgeprecision.com",
        "smtp_host": "smtp.mailgun.org",
        "smtp_port": 587,
        "smtp_username": "postmaster@forgeprecision.com",
        "smtp_password": "NewSecretSMTPPassword@2026",
        "smtp_encryption": "tls",
        "notifications_enabled": "true",
    }
    resp = client.post("/admin/settings/email", data=email_data, follow_redirects=True)
    assert resp.status_code == 200
    assert "saved=1" in str(resp.url) or "Email settings saved" in resp.text

    # Verify settings persisted in DB
    email_cfg = settings_service.get_email_config(db)
    assert email_cfg["email_contact_receiving"] == "inquiries@forgeprecision.com"
    assert email_cfg["email_from_address"] == "notifications@forgeprecision.com"
    assert email_cfg["email_smtp_host"] == "smtp.mailgun.org"
    raw_cfg = settings_service.get_email_config(db, mask_password=False)
    assert raw_cfg["email_smtp_password"] == "NewSecretSMTPPassword@2026"

    # Password should NOT be exposed in GET HTML form
    get_resp = client.get("/admin/settings/email")
    assert "NewSecretSMTPPassword@2026" not in get_resp.text
    assert "••••••••" in get_resp.text

    # 2. Test Email Action (invalid host will catch and report actionable message, not crash)
    test_resp = client.post(
        "/admin/settings/email/test",
        data={"csrf_token": csrf, "test_email": "test-analyst@example.com"},
        follow_redirects=True,
    )
    assert test_resp.status_code == 200
    # Either successfully dispatched (if mock/sandbox) or clear actionable warning
    assert ("test_success" in str(test_resp.url)) or ("test_error" in str(test_resp.url)) or ("test email" in test_resp.text.lower())


# ==============================================================================
# 5. WHATSAPP CONFIGURATION
# ==============================================================================

def test_whatsapp_configuration_and_dynamic_cta(client: TestClient, db: Session, superadmin_user):
    """Verifies WhatsApp settings update and dynamic public button rendering."""
    login_admin(client)
    csrf = generate_csrf_token(superadmin_user.id)

    # Update WhatsApp config
    wa_data = {
        "csrf_token": csrf,
        "whatsapp_country_code": "+44",
        "whatsapp_number": "7911123456",
        "whatsapp_label": "Chat with Engineering Lead",
        "whatsapp_default_message": "Hello, I require technical specs for custom forging dies.",
        "whatsapp_position": "floating",
        "whatsapp_enabled": "true",
        "whatsapp_allow_floating": "true",
    }
    resp = client.post("/admin/settings/whatsapp", data=wa_data, follow_redirects=True)
    assert resp.status_code == 200
    assert "saved=1" in str(resp.url) or "WhatsApp settings saved" in resp.text

    # Check public website has dynamic WhatsApp CTA
    pub_resp = client.get("/")
    assert pub_resp.status_code == 200
    assert "447911123456" in pub_resp.text
    assert "Chat with Engineering Lead" in pub_resp.text


# ==============================================================================
# 6. SOCIAL MEDIA MANAGEMENT
# ==============================================================================

def test_social_media_link_management(client: TestClient, db: Session, superadmin_user):
    """Verifies social media CRUD with open_in_new_tab and public rendering."""
    login_admin(client)
    csrf = generate_csrf_token(superadmin_user.id)

    # Create new social link
    social_data = {
        "csrf_token": csrf,
        "platform": "X",
        "url": "https://x.com/ForgePrecision",
        "icon": "ri-twitter-x-line",
        "display_order": 3,
        "open_in_new_tab": "true",
        "is_enabled": "true",
    }
    resp = client.post("/admin/settings/social/save", data=social_data, follow_redirects=True)
    assert resp.status_code == 200
    assert "saved=1" in str(resp.url) or "Social media link added" in resp.text

    # Verify link exists and renders in public footer with rel="noopener noreferrer"
    pub_resp = client.get("/")
    assert "https://x.com/ForgePrecision" in pub_resp.text
    assert 'target="_blank"' in pub_resp.text
    assert "noopener noreferrer" in pub_resp.text


# ==============================================================================
# 7. FOOTER REQUIREMENTS
# ==============================================================================

def test_footer_version_cubeon_attribution_and_no_api_health(client: TestClient):
    """
    Verifies that:
    1. Version 1.0.0 is displayed.
    2. 'Developed by Cubeon Technologies' links to https://www.cubeontechs.com/ with target='_blank' and rel='noopener noreferrer'.
    3. API Health Status label/indicator/link is completely removed from public footer.
    """
    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.text

    # 1. Version
    assert "Version 1.0.0" in text

    # 2. Developer Attribution
    assert "Developed by" in text
    assert "Cubeon Technologies" in text
    assert 'href="https://www.cubeontechs.com/"' in text
    assert 'target="_blank"' in text
    assert 'rel="noopener noreferrer"' in text

    # 3. Ensure API Health Status is NOT in the public footer
    assert "API Health Status" not in text
    assert "api-health" not in text
    # Verify the backend health endpoint still functions as required
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"


# ==============================================================================
# 8. SITEMAP.XML INCLUDES PUBLISHED PAGES AND EXCLUDES DRAFTS
# ==============================================================================

def test_sitemap_xml_includes_published_and_excludes_drafts(client: TestClient, db: Session):
    """Verifies that /sitemap.xml contains published CMS pages but excludes drafts."""
    # Ensure a published page and a draft page exist
    pub_page = page_service.create_page(
        db,
        {"title": "Published Precision Capabilities", "slug": "published-precision-cap", "content": "<p>Published</p>", "status": "published"}
    )
    draft_page = page_service.create_page(
        db,
        {"title": "Draft Internal Strategy", "slug": "draft-internal-strategy", "content": "<p>Draft</p>", "status": "draft"}
    )

    sitemap_resp = client.get("/sitemap.xml")
    assert sitemap_resp.status_code == 200
    assert "xml" in sitemap_resp.headers["content-type"]
    xml_content = sitemap_resp.text

    # Published pages must be in sitemap
    assert "/about-us" in xml_content
    assert "/about-us/company-profile" in xml_content
    assert "/published-precision-cap" in xml_content

    # Draft page must NOT be in sitemap
    assert "/draft-internal-strategy" not in xml_content


# ==============================================================================
# 9. ACCESS CONTROL FOR ADMIN SETTINGS & PAGES
# ==============================================================================

def test_admin_routes_require_authentication(client: TestClient):
    """Verifies that unauthorized requests to admin pages and settings are denied."""
    unauth_client = TestClient(client.app)

    protected_routes = [
        "/admin/pages",
        "/admin/pages/create",
        "/admin/menus",
        "/admin/settings",
        "/admin/settings/general",
        "/admin/settings/email",
        "/admin/settings/whatsapp",
        "/admin/settings/social",
        "/admin/settings/footer",
        "/admin/settings/seo",
    ]

    for route in protected_routes:
        # Request with HTML accept header to verify browser redirect or 401
        resp = unauth_client.get(route, headers={"Accept": "text/html"}, follow_redirects=False)
        assert resp.status_code in (302, 307, 401)
        if resp.status_code in (302, 307):
            assert "/admin/login" in resp.headers.get("Location", "")
