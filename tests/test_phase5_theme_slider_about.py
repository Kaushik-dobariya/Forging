import re
import pytest
from starlette.testclient import TestClient
from app.models.hero_slide import HeroSlide
from app.models.timeline import TimelineMilestone
from app.models.setting import SiteSetting
from app.services.theme_service import theme_service


def extract_csrf(html_text: str) -> str:
    """Helper to extract CSRF token from HTML forms."""
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_text)
    if not match:
        match = re.search(r'value="([^"]+)"\s+name="csrf_token"', html_text)
    return match.group(1) if match else ""


def login_admin(client: TestClient, superadmin_user) -> None:
    """Authenticates the test client as superadmin."""
    client.post(
        "/admin/login",
        data={
            "email": superadmin_user.email,
            "password": "SuperSecret@123",
        },
        follow_redirects=True,
    )


def test_public_about_routes(client: TestClient):
    """Verifies that /about and /about-us both return 200 and render industrial engineering sections."""
    for path in ["/about", "/about-us"]:
        res = client.get(path)
        assert res.status_code == 200
        content = res.text
        # Check core section headlines
        assert "About Us" in content or "About Our Company" in content
        assert "Vision" in content
        assert "Mission" in content
        assert "Core Values" in content
        assert "Leadership" in content
        assert "Manufacturing Process" in content or "Engineering" in content
        assert "Request a Quote" in content or "Request a Quotation" in content


def test_public_company_history_route(client: TestClient):
    """Verifies that /company-history renders the interactive timeline and milestones."""
    res = client.get("/company-history")
    assert res.status_code == 200
    content = res.text
    assert "Three Decades of Metallurgical Mastery" in content or "Journey" in content or "Timeline" in content
    assert "1994" in content  # Seeded founding milestone
    assert "2018" in content  # Seeded 4,000 MT milestone


def test_public_machinery_and_faqs_routes(client: TestClient):
    """Verifies /machinery and /faqs public routes render correctly."""
    machinery_res = client.get("/machinery")
    assert machinery_res.status_code == 200
    assert "Machinery" in machinery_res.text or "Fleet" in machinery_res.text

    faqs_res = client.get("/faqs")
    assert faqs_res.status_code == 200
    assert "Frequently Asked Questions" in faqs_res.text


def test_public_homepage_hero_slider(client: TestClient, db):
    """Verifies that published hero slides render on the homepage."""
    res = client.get("/")
    assert res.status_code == 200
    content = res.text
    assert "cms-hero-slider" in content or "hero-slide" in content
    assert "Precision Forged for Performance" in content or "Built Around Your Engineering Requirements" in content


def test_request_quote_alias(client: TestClient):
    """Verifies that /request-quote works as an alias for /request-a-quote."""
    res = client.get("/request-quote")
    assert res.status_code == 200
    assert "Request a Forging Quotation" in res.text or "RFQ" in res.text


def test_admin_theme_settings_flow(client: TestClient, superadmin_user, db):
    """Tests GET, POST update, and RESET for Website Theme settings."""
    login_admin(client, superadmin_user)

    # 1. GET theme settings
    res = client.get("/admin/settings/theme")
    assert res.status_code == 200
    assert "Website Theme" in res.text
    csrf = extract_csrf(res.text)

    # 2. POST update custom primary color
    post_res = client.post(
        "/admin/settings/theme",
        data={
            "theme_color_primary": "#123456",
            "theme_color_secondary": "#234567",
            "theme_color_accent": "#c08040",
            "theme_font_family_base": "Aptos, sans-serif",
            "theme_font_family_heading": "Aptos, sans-serif",
            "csrf_token": csrf,
        },
        follow_redirects=True,
    )
    assert post_res.status_code == 200

    # 3. Verify CSS generator produces updated color
    css = theme_service.generate_public_css(db)
    assert "#123456" in css

    # 4. RESET theme
    reset_res = client.post(
        "/admin/settings/theme/reset",
        data={"csrf_token": csrf},
        follow_redirects=True,
    )
    assert reset_res.status_code == 200
    css_after_reset = theme_service.generate_public_css(db)
    assert "#17212B" in css_after_reset


def test_admin_appearance_settings_flow(client: TestClient, superadmin_user, db):
    """Tests GET, POST update, and RESET for Admin Appearance settings."""
    login_admin(client, superadmin_user)

    # 1. GET admin appearance
    res = client.get("/admin/settings/appearance")
    assert res.status_code == 200
    assert "Admin Panel Appearance" in res.text
    csrf = extract_csrf(res.text)

    # 2. POST update custom admin sidebar color
    post_res = client.post(
        "/admin/settings/appearance",
        data={
            "admin_theme_sidebar_bg": "#0d141c",
            "admin_theme_sidebar_text": "#e2e8f0",
            "admin_theme_font_family": "Aptos, sans-serif",
            "csrf_token": csrf,
        },
        follow_redirects=True,
    )
    assert post_res.status_code == 200

    # 3. Verify admin CSS generator produces updated color
    admin_css = theme_service.generate_admin_css(db)
    assert "#0d141c" in admin_css

    # 4. RESET admin appearance
    reset_res = client.post(
        "/admin/settings/appearance/reset",
        data={"csrf_token": csrf},
        follow_redirects=True,
    )
    assert reset_res.status_code == 200
    admin_css_after_reset = theme_service.generate_admin_css(db)
    assert "#111827" in admin_css_after_reset


def test_admin_hero_slides_crud(client: TestClient, superadmin_user, db):
    """Tests Hero Slide CRUD operations in admin panel."""
    login_admin(client, superadmin_user)

    # 1. List slides
    res = client.get("/admin/hero-slides")
    assert res.status_code == 200
    assert "Homepage Hero Slider" in res.text

    # 2. Create slide with multipart/form-data
    create_res = client.post(
        "/admin/hero-slides/create",
        data={
            "title": "Automated 4000 MT Forging Line",
            "subtitle": "High-volume structural manufacturing for tier-1 OEMs",
            "eyebrow": "ROBOTIC CELL COMMISSIONED",
            "primary_cta_label": "View Specs",
            "primary_cta_url": "/infrastructure",
            "secondary_cta_label": "Request RFQ",
            "secondary_cta_url": "/request-quote",
            "text_align": "left",
            "overlay_opacity": "60",
            "display_order": "99",
            "is_active": "true",
            "image_alt": "Robotic cell forging alloy steel",
        },
        files={"dummy_empty": ("", b"")},
        follow_redirects=True,
    )
    assert create_res.status_code == 200
    new_slide = db.query(HeroSlide).filter(HeroSlide.title == "Automated 4000 MT Forging Line").first()
    assert new_slide is not None
    assert new_slide.eyebrow == "ROBOTIC CELL COMMISSIONED"

    # 3. Toggle slide
    toggle_res = client.post(
        f"/admin/hero-slides/{new_slide.id}/toggle",
        follow_redirects=True,
    )
    assert toggle_res.status_code == 200
    db.refresh(new_slide)
    assert new_slide.is_active is False

    # 4. Delete slide
    del_res = client.post(
        f"/admin/hero-slides/{new_slide.id}/delete",
        follow_redirects=True,
    )
    assert del_res.status_code == 200
    deleted_slide = db.query(HeroSlide).filter(HeroSlide.id == new_slide.id).first()
    assert deleted_slide is None


def test_admin_timeline_crud(client: TestClient, superadmin_user, db):
    """Tests Company History Timeline CRUD operations in admin panel."""
    login_admin(client, superadmin_user)

    # 1. List timeline
    res = client.get("/admin/timeline")
    assert res.status_code == 200
    assert "Company History Milestones" in res.text

    # 2. Create milestone with multipart/form-data
    create_res = client.post(
        "/admin/timeline/create",
        data={
            "year": "2026",
            "title": "Solar Powered Forge Line Integration",
            "description": "5 MW rooftop solar installation reducing factory carbon intensity by 40%.",
            "supporting_info": "SUSTAINABILITY",
            "display_order": "10",
            "is_active": "true",
        },
        files={"dummy_empty": ("", b"")},
        follow_redirects=True,
    )
    assert create_res.status_code == 200
    milestone = db.query(TimelineMilestone).filter(TimelineMilestone.year == "2026").first()
    assert milestone is not None
    assert milestone.supporting_info == "SUSTAINABILITY"

    # 3. Toggle milestone
    toggle_res = client.post(
        f"/admin/timeline/{milestone.id}/toggle",
        follow_redirects=True,
    )
    assert toggle_res.status_code == 200
    db.refresh(milestone)
    assert milestone.is_active is False

    # 4. Delete milestone
    del_res = client.post(
        f"/admin/timeline/{milestone.id}/delete",
        follow_redirects=True,
    )
    assert del_res.status_code == 200
    deleted_m = db.query(TimelineMilestone).filter(TimelineMilestone.id == milestone.id).first()
    assert deleted_m is None
