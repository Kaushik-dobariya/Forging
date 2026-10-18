import json
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.setting import SiteSetting, SocialLink, SocialPlatform
from app.services.settings_service import settings_service


router = APIRouter(prefix="/settings", tags=["Admin Settings"])


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
    # Validate departments JSON
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
    whatsapp_default_message: str = Form(...),
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
    settings_service.set_setting(db, "whatsapp_default_message", whatsapp_default_message.strip(), "Default WhatsApp Message", "whatsapp")
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
    display_order: int = Form(0),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if link_id and link_id > 0:
        link = db.query(SocialLink).filter(SocialLink.id == link_id).first()
        if link:
            link.platform = platform.strip()
            link.url = url.strip()
            link.icon = icon.strip() if icon else platform.lower()
            link.is_enabled = is_enabled
            link.display_order = display_order
    else:
        link = SocialLink(
            platform=platform.strip(),
            url=url.strip(),
            icon=icon.strip() if icon else platform.lower(),
            is_enabled=is_enabled,
            display_order=display_order,
        )
        db.add(link)

    db.commit()
    logger.info(f"Saved social link for {platform}")
    return RedirectResponse(url="/admin/settings/social", status_code=status.HTTP_302_FOUND)


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
    return RedirectResponse(url="/admin/settings/social", status_code=status.HTTP_302_FOUND)


@router.post("/social/{link_id}/delete", summary="Delete Social Link")
async def admin_social_delete(
    link_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    link = db.query(SocialLink).filter(SocialLink.id == link_id).first()
    if link:
        db.delete(link)
        db.commit()
        logger.info(f"Deleted social link #{link_id}")
    return RedirectResponse(url="/admin/settings/social", status_code=status.HTTP_302_FOUND)
