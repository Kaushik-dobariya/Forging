import json
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.core.config import settings as app_cfg
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.setting import SiteSetting, SocialLink, SocialPlatform
from app.services.settings_service import settings_service
from app.services.email_service import email_service


router = APIRouter(prefix="/settings", tags=["Admin Settings"])


# ==============================================================================
# SETTINGS CENTRAL DASHBOARD
# ==============================================================================

@router.get("", response_class=HTMLResponse, summary="Settings Central Hub")
async def admin_settings_hub(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    general_settings = settings_service.get_general_settings(db)
    email_cfg = settings_service.get_email_config(db)
    whatsapp_cfg = settings_service.get_whatsapp_config(db)
    social_count = db.query(SocialLink).count()

    return templates.TemplateResponse(
        request=request,
        name="admin/settings/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "general": general_settings,
            "email_cfg": email_cfg,
            "whatsapp_cfg": whatsapp_cfg,
            "social_count": social_count,
            "active_page": "settings",
            "active_subpage": "settings_hub",
        },
    )


# ==============================================================================
# GENERAL SETTINGS
# ==============================================================================

@router.get("/general", response_class=HTMLResponse, summary="General Site Settings")
async def admin_general_settings_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    general = settings_service.get_general_settings(db)

    return templates.TemplateResponse(
        request=request,
        name="admin/settings/general.html",
        context={
            "request": request,
            "current_user": current_user,
            "general": general,
            "active_page": "settings",
            "active_subpage": "settings_general",
        },
    )


@router.post("/general", summary="Save General Settings")
async def admin_general_settings_save(
    request: Request,
    website_name: str = Form(...),
    company_name: str = Form(...),
    logo_url: Optional[str] = Form(None),
    favicon_url: Optional[str] = Form(None),
    default_contact_email: str = Form(...),
    app_version: str = Form(...),
    copyright_text: str = Form(...),
    developer_attribution: str = Form("Developed by Cubeon Technologies"),
    developer_website_url: str = Form("https://www.cubeontechs.com/"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.set_setting(db, "general_website_name", website_name.strip(), "Website Name", "general")
    settings_service.set_setting(db, "general_company_name", company_name.strip(), "Company Name", "general")
    settings_service.set_setting(db, "general_logo_url", logo_url.strip() if logo_url else "/static/images/logo.png", "Logo URL", "general")
    settings_service.set_setting(db, "general_favicon_url", favicon_url.strip() if favicon_url else "/static/favicon.ico", "Favicon URL", "general")
    settings_service.set_setting(db, "general_default_contact_email", default_contact_email.strip(), "Default Contact Email", "general")
    settings_service.set_setting(db, "general_app_version", app_version.strip(), "Application Version", "general")
    settings_service.set_setting(db, "general_copyright_text", copyright_text.strip(), "Copyright Text", "general")
    settings_service.set_setting(db, "general_footer_developer_attribution", developer_attribution.strip(), "Footer Developer Attribution", "general")
    settings_service.set_setting(db, "general_developer_website_url", developer_website_url.strip(), "Developer Website URL", "general")

    logger.info("Updated general site settings.")
    return RedirectResponse(url="/admin/settings/general?saved=1", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# EMAIL CONFIGURATION & TEST EMAIL
# ==============================================================================

@router.get("/email", response_class=HTMLResponse, summary="Email Configuration")
async def admin_email_settings_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    cfg = settings_service.get_email_config(db, mask_password=True)

    return templates.TemplateResponse(
        request=request,
        name="admin/settings/email.html",
        context={
            "request": request,
            "current_user": current_user,
            "cfg": cfg,
            "active_page": "settings",
            "active_subpage": "settings_email",
        },
    )


@router.post("/email", summary="Save Email Configuration")
async def admin_email_settings_save(
    request: Request,
    contact_receiving: str = Form(...),
    sender_name: str = Form(...),
    from_address: str = Form(...),
    reply_to: str = Form(...),
    smtp_host: str = Form(...),
    smtp_port: int = Form(587),
    smtp_username: Optional[str] = Form(""),
    smtp_password: Optional[str] = Form(""),
    smtp_encryption: str = Form("tls"),
    notifications_enabled: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = {
        "email_contact_receiving": contact_receiving.strip(),
        "email_sender_name": sender_name.strip(),
        "email_from_address": from_address.strip(),
        "email_reply_to": reply_to.strip(),
        "email_smtp_host": smtp_host.strip(),
        "email_smtp_port": smtp_port,
        "email_smtp_username": smtp_username.strip() if smtp_username else "",
        "email_smtp_password": smtp_password.strip() if smtp_password else "",
        "email_smtp_encryption": smtp_encryption.strip().lower(),
        "email_notifications_enabled": "true" if notifications_enabled else "false",
    }
    settings_service.update_email_config(db, data)
    logger.info("Updated email configuration settings.")
    return RedirectResponse(url="/admin/settings/email?saved=1", status_code=status.HTTP_302_FOUND)


@router.post("/email/test", summary="Send Test Email")
async def admin_email_send_test(
    request: Request,
    test_email: str = Form(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    success, message = email_service.send_test_email(test_email.strip(), db=db)
    import urllib.parse
    encoded_msg = urllib.parse.quote(message)
    if success:
        return RedirectResponse(url=f"/admin/settings/email?test_success={encoded_msg}", status_code=status.HTTP_302_FOUND)
    else:
        return RedirectResponse(url=f"/admin/settings/email?test_error={encoded_msg}", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# FOOTER SETTINGS
# ==============================================================================

@router.get("/footer", response_class=HTMLResponse, summary="Footer Settings")
async def admin_footer_settings_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    general = settings_service.get_general_settings(db)

    return templates.TemplateResponse(
        request=request,
        name="admin/settings/footer.html",
        context={
            "request": request,
            "current_user": current_user,
            "general": general,
            "active_page": "settings",
            "active_subpage": "settings_footer",
        },
    )


@router.post("/footer", summary="Save Footer Settings")
async def admin_footer_settings_save(
    request: Request,
    app_version: str = Form(...),
    copyright_text: str = Form(...),
    developer_attribution: str = Form("Developed by Cubeon Technologies"),
    developer_website_url: str = Form("https://www.cubeontechs.com/"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.set_setting(db, "general_app_version", app_version.strip(), "Application Version", "general")
    settings_service.set_setting(db, "general_copyright_text", copyright_text.strip(), "Copyright Notice", "general")
    settings_service.set_setting(db, "general_footer_developer_attribution", developer_attribution.strip(), "Developer Attribution", "general")
    settings_service.set_setting(db, "general_developer_website_url", developer_website_url.strip(), "Developer Website URL", "general")

    logger.info("Updated footer settings.")
    return RedirectResponse(url="/admin/settings/footer?saved=1", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# SEO DEFAULTS
# ==============================================================================

@router.get("/seo", response_class=HTMLResponse, summary="SEO Default Settings")
async def admin_seo_settings_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    general = settings_service.get_general_settings(db)

    return templates.TemplateResponse(
        request=request,
        name="admin/settings/seo.html",
        context={
            "request": request,
            "current_user": current_user,
            "general": general,
            "active_page": "settings",
            "active_subpage": "settings_seo",
        },
    )


@router.post("/seo", summary="Save SEO Default Settings")
async def admin_seo_settings_save(
    request: Request,
    default_meta_title: str = Form(...),
    default_meta_description: str = Form(...),
    default_meta_keywords: Optional[str] = Form(None),
    default_og_image: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.set_setting(db, "general_meta_title", default_meta_title.strip(), "Default Meta Title", "general")
    settings_service.set_setting(db, "general_meta_description", default_meta_description.strip(), "Default Meta Description", "general")
    settings_service.set_setting(db, "general_meta_keywords", default_meta_keywords.strip() if default_meta_keywords else "", "Default Meta Keywords", "general")
    settings_service.set_setting(db, "general_og_image", default_og_image.strip() if default_og_image else "", "Default OG Image URL", "general")

    logger.info("Updated global SEO default settings.")
    return RedirectResponse(url="/admin/settings/seo?saved=1", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# CONTACT SETTINGS
# ==============================================================================

@router.get("/contact", response_class=HTMLResponse, summary="Contact Page Settings")
async def admin_contact_settings_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    contact_info = settings_service.get_contact_info(db)
    group = settings_service.get_settings_by_group(db, "contact")

    return templates.TemplateResponse(
        request=request,
        name="admin/settings/contact.html",
        context={
            "request": request,
            "current_user": current_user,
            "contact_info": contact_info,
            "raw_departments": group.get("contact_departments_json", "[]"),
            "active_page": "settings",
            "active_subpage": "settings_contact",
        },
    )


@router.post("/contact", summary="Save Contact Page Settings")
async def admin_contact_settings_save(
    request: Request,
    company_name: str = Form(...),
    address: str = Form(...),
    phone: str = Form(...),
    secondary_phone: Optional[str] = Form(None),
    email: str = Form(...),
    support_email: Optional[str] = Form(None),
    business_hours: str = Form(...),
    maps_embed_url: Optional[str] = Form(None),
    departments_json: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_deps_json = "[]"
    if departments_json and departments_json.strip():
        try:
            json.loads(departments_json.strip())
            clean_deps_json = departments_json.strip()
        except Exception:
            clean_deps_json = "[]"

    settings_service.set_setting(db, "contact_company_name", company_name.strip(), "Company Name", "contact")
    settings_service.set_setting(db, "contact_address", address.strip(), "Corporate & Plant Address", "contact")
    settings_service.set_setting(db, "contact_phone", phone.strip(), "Primary Phone Number", "contact")
    settings_service.set_setting(db, "contact_secondary_phone", secondary_phone.strip() if secondary_phone else "", "Secondary Phone", "contact")
    settings_service.set_setting(db, "contact_email", email.strip(), "Primary Email", "contact")
    settings_service.set_setting(db, "contact_support_email", support_email.strip() if support_email else "", "Technical Support Email", "contact")
    settings_service.set_setting(db, "contact_business_hours", business_hours.strip(), "Business Hours", "contact")
    settings_service.set_setting(db, "contact_maps_embed_url", maps_embed_url.strip() if maps_embed_url else "", "Google Maps Embed URL", "contact")
    settings_service.set_setting(db, "contact_departments_json", clean_deps_json, "Corporate Departments List", "contact")

    logger.info("Updated contact settings.")
    return RedirectResponse(url="/admin/settings/contact?saved=1", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# WHATSAPP SETTINGS
# ==============================================================================

@router.get("/whatsapp", response_class=HTMLResponse, summary="WhatsApp CTA Settings")
async def admin_whatsapp_settings_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    whatsapp_cfg = settings_service.get_whatsapp_config(db)

    return templates.TemplateResponse(
        request=request,
        name="admin/settings/whatsapp.html",
        context={
            "request": request,
            "current_user": current_user,
            "cfg": whatsapp_cfg,
            "active_page": "settings",
            "active_subpage": "settings_whatsapp",
        },
    )


@router.post("/whatsapp", summary="Save WhatsApp CTA Settings")
async def admin_whatsapp_settings_save(
    request: Request,
    whatsapp_number: str = Form(...),
    whatsapp_country_code: Optional[str] = Form("+91"),
    whatsapp_label: Optional[str] = Form("Chat on WhatsApp"),
    whatsapp_default_message: str = Form(...),
    whatsapp_position: str = Form("floating"),
    whatsapp_enabled: bool = Form(False),
    whatsapp_allow_header: bool = Form(False),
    whatsapp_allow_floating: bool = Form(False),
    whatsapp_allow_product: bool = Form(False),
    whatsapp_allow_quote: bool = Form(False),
    whatsapp_allow_footer: bool = Form(False),
    whatsapp_allow_contact: bool = Form(False),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.set_setting(db, "whatsapp_enabled", "true" if whatsapp_enabled else "false", "Enable global WhatsApp CTA", "whatsapp")
    settings_service.set_setting(db, "whatsapp_number", whatsapp_number.strip(), "WhatsApp Phone Number", "whatsapp")
    settings_service.set_setting(db, "whatsapp_country_code", whatsapp_country_code.strip() if whatsapp_country_code else "+91", "WhatsApp Country Code", "whatsapp")
    settings_service.set_setting(db, "whatsapp_label", whatsapp_label.strip() if whatsapp_label else "Chat on WhatsApp", "WhatsApp Button Label", "whatsapp")
    settings_service.set_setting(db, "whatsapp_default_message", whatsapp_default_message.strip(), "Default WhatsApp Message", "whatsapp")
    settings_service.set_setting(db, "whatsapp_position", whatsapp_position.strip() if whatsapp_position else "floating", "Button Position", "whatsapp")
    settings_service.set_setting(db, "whatsapp_allow_header", "true" if whatsapp_allow_header else "false", "Header placement", "whatsapp")
    settings_service.set_setting(db, "whatsapp_allow_floating", "true" if whatsapp_allow_floating else "false", "Floating button placement", "whatsapp")
    settings_service.set_setting(db, "whatsapp_allow_product", "true" if whatsapp_allow_product else "false", "Product page placement", "whatsapp")
    settings_service.set_setting(db, "whatsapp_allow_quote", "true" if whatsapp_allow_quote else "false", "Quote page placement", "whatsapp")
    settings_service.set_setting(db, "whatsapp_allow_footer", "true" if whatsapp_allow_footer else "false", "Footer placement", "whatsapp")
    settings_service.set_setting(db, "whatsapp_allow_contact", "true" if whatsapp_allow_contact else "false", "Contact page placement", "whatsapp")

    logger.info("Updated WhatsApp CTA settings.")
    return RedirectResponse(url="/admin/settings/whatsapp?saved=1", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# SOCIAL MEDIA LINKS
# ==============================================================================

@router.get("/social", response_class=HTMLResponse, summary="Social Links Management")
async def admin_social_settings_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.seed_defaults(db)
    social_links = db.query(SocialLink).order_by(SocialLink.display_order.asc(), SocialLink.id.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/settings/social.html",
        context={
            "request": request,
            "current_user": current_user,
            "social_links": social_links,
            "platforms": [p.value for p in SocialPlatform],
            "active_page": "settings",
            "active_subpage": "settings_social",
        },
    )


@router.post("/social/save", summary="Add or Update Social Link")
async def admin_social_save(
    request: Request,
    link_id: Optional[int] = Form(None),
    platform: str = Form(...),
    url: str = Form(...),
    icon: Optional[str] = Form(None),
    is_enabled: bool = Form(True),
    open_in_new_tab: bool = Form(True),
    display_order: int = Form(0),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = {
        "platform": platform.strip(),
        "url": url.strip(),
        "icon": icon.strip() if icon else platform.lower(),
        "is_enabled": is_enabled,
        "open_in_new_tab": open_in_new_tab,
        "display_order": display_order,
    }
    settings_service.save_social_link(db, data, link_id=link_id if link_id and link_id > 0 else None)
    logger.info(f"Saved social link for {platform}")
    return RedirectResponse(url="/admin/settings/social?saved=1", status_code=status.HTTP_302_FOUND)


@router.post("/social/{link_id}/toggle", summary="Toggle Social Link Status")
async def admin_social_toggle(
    link_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    link = db.query(SocialLink).filter(SocialLink.id == link_id).first()
    if link:
        link.is_enabled = not link.is_enabled
        db.commit()
    return RedirectResponse(url="/admin/settings/social?toggled=1", status_code=status.HTTP_302_FOUND)


@router.post("/social/{link_id}/delete", summary="Delete Social Link")
async def admin_social_delete(
    link_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    settings_service.delete_social_link(db, link_id)
    return RedirectResponse(url="/admin/settings/social?deleted=1", status_code=status.HTTP_302_FOUND)
