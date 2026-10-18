import io
import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient

from app.models.blog import BlogPost, BlogCategory, BlogPostStatus
from app.models.case_study import CaseStudy
from app.models.faq import FAQ, generate_faq_schema_ld
from app.models.download import DownloadResource, DownloadCategory, DownloadVisibility
from app.models.lead import ContactLead, QuoteRequest, LeadStatus
from app.models.setting import SiteSetting, SocialLink, SocialPlatform
from app.services.settings_service import SettingsService, WhatsAppConfig
from app.services.upload_service import upload_service
from app.services.email_service import email_service
from app.services.spam_protection import (
    generate_public_csrf_token,
    validate_public_csrf_token,
    validate_honeypot,
    validate_email_address,
)


# ==============================================================================
# 1. Contact Form & Anti-Spam Tests
# ==============================================================================

def test_contact_form_validation_and_lead_storage(client: TestClient, db):
    """Test contact form submission stores lead in database with 'New' status."""
    token = generate_public_csrf_token()

    form_data = {
        "csrf_token": token,
        "name": "Marcus Aurelius",
        "company": "Imperial Engineering Ltd",
        "email": "m.aurelius@imperial.com",
        "phone": "+44 20 7946 0912",
        "country": "United Kingdom",
        "message": "We require heavy forged shaft prototypes for naval propulsion systems.",
        "website_url_check": "",  # Empty honeypot
    }

    response = client.post("/contact", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    assert "Inquiry Submitted Successfully" in response.text

    # Verify persistence
    lead = db.query(ContactLead).filter(ContactLead.email == "m.aurelius@imperial.com").first()
    assert lead is not None
    assert lead.name == "Marcus Aurelius"
    assert lead.company == "Imperial Engineering Ltd"
    assert lead.country == "United Kingdom"
    assert lead.status == LeadStatus.NEW
    assert "naval propulsion" in lead.message


def test_contact_form_required_fields_and_email_validation(client: TestClient, db):
    """Test validation errors for missing fields and malformed email."""
    token = generate_public_csrf_token()

    # Missing Name & Email
    bad_data = {
        "csrf_token": token,
        "name": "",
        "company": "Acme",
        "email": "",
        "message": "Short note",
        "website_url_check": "",
    }
    resp = client.post("/contact", data=bad_data)
    assert resp.status_code == 200
    assert "Full name, corporate email, and message details are required" in resp.text

    # Invalid email format
    invalid_email_data = {
        "csrf_token": token,
        "name": "John Doe",
        "company": "Acme",
        "email": "not-an-email-address",
        "message": "Testing invalid email format.",
        "website_url_check": "",
    }
    resp2 = client.post("/contact", data=invalid_email_data)
    assert resp2.status_code == 200
    assert "valid corporate email address" in resp2.text


def test_contact_form_honeypot_spam_rejection(client: TestClient, db):
    """Test honeypot traps spam bots and refuses storage."""
    token = generate_public_csrf_token()
    initial_count = db.query(ContactLead).count()

    spam_data = {
        "csrf_token": token,
        "name": "Bot Spammer",
        "company": "Spam Corp",
        "email": "bot@spamcorp.com",
        "message": "Buy cheap watches online now!",
        "website_url_check": "http://spambot-link.com",  # Honeypot filled!
    }

    resp = client.post("/contact", data=spam_data)
    assert resp.status_code == 200
    assert "Inquiry Submitted Successfully" in resp.text  # Friendly deception

    # No record should be stored in database
    final_count = db.query(ContactLead).count()
    assert final_count == initial_count


# ==============================================================================
# 2. Quote Request (RFQ) & Upload Security Tests
# ==============================================================================

def test_quote_request_creation_and_cad_upload(client: TestClient, db):
    """Test RFQ submission with CAD attachment persists in database with 'New' status."""
    token = generate_public_csrf_token()

    # Create dummy STEP CAD content
    cad_content = b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Forged Turbine Blade'),'2;1');\nENDSEC;\nEND-ISO-10303-21;\n"
    file_payload = ("turbine_blade_v3.step", io.BytesIO(cad_content), "application/octet-stream")

    rfq_data = {
        "csrf_token": token,
        "name": "Dr. Sarah Connor",
        "company": "Cyberdyne Aerospace",
        "email": "s.connor@cyberdyne.com",
        "phone": "+1 310 555 0199",
        "country": "United States",
        "product": "Titanium Turbine Disk",
        "material": "Ti-6Al-4V Grade 5",
        "quantity": "250 units",
        "required_delivery": "Q4 2026",
        "requirement": "Ultrasonic C-Scan Class A inspection per AMS 2631.",
        "website_url_check": "",
    }

    response = client.post(
        "/request-a-quote",
        data=rfq_data,
        files={"drawing_file": file_payload},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "RFQ Received Successfully" in response.text

    # Verify database persistence
    quote = db.query(QuoteRequest).filter(QuoteRequest.email == "s.connor@cyberdyne.com").first()
    assert quote is not None
    assert quote.name == "Dr. Sarah Connor"
    assert quote.product == "Titanium Turbine Disk"
    assert quote.material == "Ti-6Al-4V Grade 5"
    assert quote.status == LeadStatus.NEW
    assert quote.drawing_file is not None
    assert "turbine_blade_v3" in quote.drawing_file


def test_quote_request_dangerous_file_rejection(client: TestClient, db):
    """Test upload security blocks executable scripts (.exe, .sh, .py, etc.)."""
    token = generate_public_csrf_token()

    # Malicious script pretending to be a drawing
    malicious_bytes = b"import os; os.system('malicious')"
    file_payload = ("exploit.py", io.BytesIO(malicious_bytes), "text/x-python")

    rfq_data = {
        "csrf_token": token,
        "name": "Hacker",
        "company": "Evil Corp",
        "email": "hacker@evil.com",
        "website_url_check": "",
    }

    response = client.post(
        "/request-a-quote",
        data=rfq_data,
        files={"drawing_file": file_payload},
    )
    assert response.status_code == 200
    assert "File type .py is strictly prohibited for security reasons" in response.text


def test_upload_service_format_validation():
    """Unit test upload_service CAD formats and blocked dangerous extensions."""
    # Allowed CAD/Drawing formats
    allowed_exts = [".pdf", ".dwg", ".dxf", ".step", ".stp", ".iges", ".igs", ".png", ".jpg", ".zip"]
    for ext in allowed_exts:
        valid, msg = upload_service.validate_drawing_file(f"drawing{ext}", 1024, "application/octet-stream")
        assert valid is True, f"Failed for {ext}: {msg}"

    # Dangerous extensions
    dangerous_exts = [".exe", ".bat", ".cmd", ".sh", ".php", ".py", ".js", ".vbs", ".msi"]
    for ext in dangerous_exts:
        valid, msg = upload_service.validate_drawing_file(f"virus{ext}", 1024, "application/octet-stream")
        assert valid is False
        assert "strictly prohibited" in msg


# ==============================================================================
# 3. Lead Management Pipeline & Status Transition Tests
# ==============================================================================

def test_contact_lead_lifecycle_status_transitions(db):
    """Test full status pipeline: New -> Contacted -> Qualified -> Quotation Sent -> Won -> Lost."""
    lead = ContactLead(
        name="Elena Rostova",
        company="Nordic Energy AS",
        email="elena@nordicenergy.no",
        message="Request for valve bodies",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()

    pipeline = [
        LeadStatus.CONTACTED,
        LeadStatus.QUALIFIED,
        LeadStatus.QUOTATION_SENT,
        LeadStatus.WON,
        LeadStatus.LOST,
    ]

    for status in pipeline:
        lead.status = status
        lead.notes = f"Transitioned to {status.value}"
        db.commit()
        refreshed = db.query(ContactLead).filter(ContactLead.id == lead.id).first()
        assert refreshed.status == status
        assert f"Transitioned to {status.value}" in refreshed.notes


def test_quote_request_lifecycle_status_transitions(db):
    """Test quote request status updates and notes persistence."""
    quote = QuoteRequest(
        name="Vikram Patel",
        company="Indus Heavy Machinery",
        email="v.patel@indusheavy.in",
        product="Forged Crane Hooks",
        material="35CrMo4",
        status=LeadStatus.NEW,
    )
    db.add(quote)
    db.commit()

    quote.status = LeadStatus.QUOTATION_SENT
    quote.notes = "Quotation Q-2026-089 sent at $14,200 per lot."
    db.commit()

    refreshed = db.query(QuoteRequest).filter(QuoteRequest.id == quote.id).first()
    assert refreshed.status == LeadStatus.QUOTATION_SENT
    assert "Q-2026-089" in refreshed.notes


# ==============================================================================
# 4. WhatsApp CTA Engine Tests (Never Hardcoded)
# ==============================================================================

def test_whatsapp_cta_dynamic_generation_and_normalization():
    """Test phone number normalization, custom message URL encoding, and placement."""
    # Test normalization of messy formats
    raw_numbers = [
        ("+1 (555) 438-2900", "15554382900"),
        ("91 98765 43210", "919876543210"),
        ("+44-20-7946-0912", "442079460912"),
    ]

    for raw, expected_clean in raw_numbers:
        cfg = WhatsAppConfig(phone_number=raw, is_enabled=True)
        url = cfg.generate_cta()
        assert f"https://wa.me/{expected_clean}" in url

    # Test custom contextual messages
    cfg = WhatsAppConfig(phone_number="+1 555 438 2900", is_enabled=True)
    custom_url = cfg.generate_cta("Inquiring about Titanium Discs")
    assert "https://wa.me/15554382900?text=Inquiring%20about%20Titanium%20Discs" in custom_url

    # Test disabled configuration
    cfg_disabled = WhatsAppConfig(phone_number="+1 555 438 2900", is_enabled=False)
    assert cfg_disabled.generate_cta() == ""


def test_whatsapp_placement_toggles():
    """Test placement switches (header, floating, product, quote, footer, contact)."""
    cfg = WhatsAppConfig(
        phone_number="+1 555 438 2900",
        is_enabled=True,
        allow_header=True,
        allow_floating=False,
        allow_product_page=True,
        allow_quote_page=False,
    )
    assert cfg.allow_header is True
    assert cfg.allow_floating is False
    assert cfg.allow_product_page is True
    assert cfg.allow_quote_page is False


# ==============================================================================
# 5. Blog Publishing & Schema Tests
# ==============================================================================

def test_blog_post_reading_time_and_schema():
    """Test blog reading time calculation and Schema.org Article JSON-LD structure."""
    content = " ".join(["metallurgy"] * 450)  # ~450 words = ~3 min at 200 wpm
    post = BlogPost(
        title="Fatigue Resistance in Closed-Die Forgings",
        slug="fatigue-resistance-closed-die",
        author="Dr. Alan Vance",
        category=BlogCategory.FORGING_TECHNOLOGY,
        excerpt="An analysis of cyclic loading.",
        content=content,
        status=BlogPostStatus.PUBLISHED,
        published_at=datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    # Reading time calculation
    assert post.reading_time_minutes >= 2

    # Schema JSON-LD structure
    schema = post.generate_schema_ld("https://forgingplant.com")
    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "TechArticle"
    assert schema["headline"] == "Fatigue Resistance in Closed-Die Forgings"
    assert schema["author"]["name"] == "Dr. Alan Vance"
    assert schema["articleSection"] == "Forging Technology"


def test_blog_visibility_states(client: TestClient, db):
    """Test draft, scheduled, and archived posts are hidden from public blog."""
    # Create one draft and one published post
    draft_post = BlogPost(
        title="Unpublished Internal Metallurgy Draft",
        slug="unpublished-internal-draft",
        author="Staff",
        category=BlogCategory.ENGINEERING,
        excerpt="Secret draft",
        content="Confidential",
        status=BlogPostStatus.DRAFT,
    )
    published_post = BlogPost(
        title="Public Open-Die Innovations",
        slug="public-open-die-innovations",
        author="Staff",
        category=BlogCategory.FORGING_TECHNOLOGY,
        excerpt="Published technical article",
        content="Public content",
        status=BlogPostStatus.PUBLISHED,
        published_at=datetime.now(timezone.utc),
    )
    db.add(draft_post)
    db.add(published_post)
    db.commit()

    # Public listing should show published post, NOT draft
    resp = client.get("/blog")
    assert resp.status_code == 200
    assert "Public Open-Die Innovations" in resp.text
    assert "Unpublished Internal Metallurgy Draft" not in resp.text

    # Direct detail access for draft should return 404
    draft_resp = client.get("/blog/unpublished-internal-draft")
    assert draft_resp.status_code == 404


# ==============================================================================
# 6. Reusable FAQ & Schema Tests
# ==============================================================================

def test_faq_assignment_and_schema_ld():
    """Test FAQ category assignment and automatic FAQPage JSON-LD schema generation."""
    import json
    faq1 = FAQ(
        question="What is the maximum forging weight capacity?",
        answer="Our hydraulic presses forge open-die components up to 35,000 kg.",
        category="Technical Specifications",
        related_entity="capabilities",
        is_active=True,
    )
    faq2 = FAQ(
        question="Which NDT testing methods are performed in-house?",
        answer="We perform Ultrasonic (UT), Magnetic Particle (MPI), and Liquid Penetrant (LPI).",
        category="Quality & Metallurgy",
        related_entity="quality",
        is_active=True,
    )

    schema_str = generate_faq_schema_ld([faq1, faq2])
    schema = json.loads(schema_str)
    assert schema["@context"] == "https://schema.org"
    assert schema["@type"] == "FAQPage"
    assert len(schema["mainEntity"]) == 2

    q1 = schema["mainEntity"][0]
    assert q1["@type"] == "Question"
    assert "maximum forging weight capacity" in q1["name"]
    assert "35,000 kg" in q1["acceptedAnswer"]["text"]


# ==============================================================================
# 7. Downloads Management & Download Counter Tests
# ==============================================================================

def test_download_resource_visibility_and_counter(client: TestClient, db):
    """Test public download access and automatic download count increment."""
    res = DownloadResource(
        title="Master Forging Tolerance Guide 2026",
        description="Dimensional tolerances per DIN 7526.",
        file_path="/static/downloads/sample_tolerance_guide.pdf",
        file_name="tolerance_guide.pdf",
        file_type="pdf",
        file_size=2048576,  # ~2.0 MB
        category=DownloadCategory.TECHNICAL_DOCUMENT,
        visibility=DownloadVisibility.PUBLIC,
        download_count=10,
        is_active=True,
    )
    db.add(res)
    db.commit()

    assert res.formatted_size == "2.0 MB"

    # Access file download endpoint
    resp = client.get(f"/downloads/{res.id}/file", follow_redirects=False)
    assert resp.status_code == 307  # Redirects to file path

    # Check counter increment
    db.refresh(res)
    assert res.download_count == 11


# ==============================================================================
# 8. Email Service Abstraction & Notification Dispatch Tests
# ==============================================================================

def test_email_service_notification_dispatch():
    """Test abstract email service notification capturing and HTML template generation."""
    email_service.clear_sent_buffer()

    # Dispatch contact submission notification
    email_service.send_contact_notification(
        name="Arthur Dent",
        email="arthur@guide.org",
        company="Hitchhiker Industries",
        phone="+44 123456",
        country="UK",
        message="Inquiring about deep space titanium brackets.",
    )

    # Dispatch user auto-acknowledgment
    email_service.send_user_acknowledgment(
        to_email="arthur@guide.org",
        name="Arthur Dent",
        submission_type="General Contact Inquiry",
    )

    # Dispatch quote notification
    email_service.send_quote_notification(
        name="Ford Prefect",
        email="ford@betelgeuse.com",
        company="Sub-Etha Dynamics",
        product="Starship Flange",
        material="Inconel 625",
        quantity="500 pcs",
        drawing_file="/uploads/drawings/flange_drawing.dwg",
        requirement="Cryogenic testing at -196C.",
    )

    messages = email_service.get_sent_messages()
    assert len(messages) == 3

    # Check contact notification
    contact_msg = messages[0]
    assert "Arthur Dent" in contact_msg["subject"]
    assert "Hitchhiker Industries" in contact_msg["html_body"]

    # Check user acknowledgment
    ack_msg = messages[1]
    assert ack_msg["to_email"] == "arthur@guide.org"
    assert "Thank You for Contacting Us" in ack_msg["subject"]

    # Check quote notification
    quote_msg = messages[2]
    assert "Ford Prefect" in quote_msg["subject"]
    assert "Sub-Etha Dynamics" in quote_msg["html_body"]
    assert "flange_drawing.dwg" in quote_msg["html_body"]
