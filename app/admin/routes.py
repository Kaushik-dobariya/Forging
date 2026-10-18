import re
from typing import Optional
from urllib.parse import urlparse
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import auth_service
from app.admin.dependencies import get_current_admin
from app.repositories.user_repository import user_repository
from app.core.security import (
    verify_session_token,
    validate_csrf_token,
    verify_password,
    hash_password,
    validate_password_strength,
)
from app.core.config import settings
from app.core.templates import templates
from app.core.logging import logger


router = APIRouter(prefix="/admin", tags=["Super Admin"])


def is_safe_redirect_url(target: str) -> bool:
    """Protects against open redirect attacks by ensuring redirect target is internal."""
    if not target or not target.startswith("/"):
        return False
    if target.startswith("//"):
        return False
    parsed = urlparse(target)
    return not bool(parsed.netloc)


@router.get("/login", response_class=HTMLResponse, summary="Admin Login View")
async def admin_login_view(
    request: Request,
    next: str = "/admin",
    db: Session = Depends(get_db),
):
    """Renders the administrative authentication screen or redirects if already authenticated."""
    user = auth_service.get_current_user_from_cookie(db, request)
    if user and user.is_active:
        return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"request": request, "next": next},
    )


@router.post("/login", response_class=HTMLResponse, summary="Process Admin Login")
async def admin_login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/admin"),
    db: Session = Depends(get_db),
):
    """Processes administrative login submission."""
    user, error_msg = auth_service.authenticate_admin(db, email, password)

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={
                "request": request,
                "email": email,
                "next": next,
                "error": error_msg,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Safe redirect check
    redirect_target = next if is_safe_redirect_url(next) else "/admin"
    response = RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)
    auth_service.create_admin_session(response, user)
    return response


@router.post("/logout", summary="Admin Logout POST")
async def admin_logout(
    request: Request,
    csrf_token: Optional[str] = Form(None),
):
    """Terminates admin session and clears cookies with CSRF validation."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    session_id = None
    if token:
        payload = verify_session_token(token)
        if payload and "session_id" in payload:
            session_id = payload["session_id"]

    # If CSRF token is provided in form or header, validate it
    header_csrf = request.headers.get("X-CSRF-Token")
    submitted_csrf = csrf_token or header_csrf
    if submitted_csrf and session_id:
        if not validate_csrf_token(session_id, submitted_csrf):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing CSRF token.",
            )

    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    auth_service.terminate_admin_session(response, session_id=session_id)
    return response


@router.get("/logout", summary="Admin Logout GET Blocked", include_in_schema=False)
async def admin_logout_get():
    """Rejects GET logout to prevent CSRF via GET navigation."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="GET logout is not permitted. Please submit a POST request.",
    )


@router.get("/profile", response_class=HTMLResponse, summary="Admin Profile View")
async def admin_profile_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    """Renders the administrative profile view."""
    return templates.TemplateResponse(
        request=request,
        name="admin/profile.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_page": "profile",
        },
    )


@router.post("/profile", response_class=HTMLResponse, summary="Update Admin Profile")
async def admin_profile_post(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    csrf_token: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Processes administrative profile updates with validation and CSRF enforcement."""
    # 1. CSRF validation
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    payload = verify_session_token(token) if token else None
    session_id = payload.get("session_id") if payload else None
    if not session_id or not csrf_token or not validate_csrf_token(session_id, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token.",
        )

    clean_name = full_name.strip()
    clean_email = email.strip().lower()

    # 2. Server-side validation
    if len(clean_name) < 2 or len(clean_name) > 150:
        return templates.TemplateResponse(
            request=request,
            name="admin/profile.html",
            context={
                "request": request,
                "current_user": current_user,
                "active_page": "profile",
                "error": "Full name must be between 2 and 150 characters.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_pattern, clean_email):
        return templates.TemplateResponse(
            request=request,
            name="admin/profile.html",
            context={
                "request": request,
                "current_user": current_user,
                "active_page": "profile",
                "error": "Please enter a valid email address.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Uniqueness check for email
    existing_user = user_repository.get_by_email(db, clean_email)
    if existing_user and existing_user.id != current_user.id:
        return templates.TemplateResponse(
            request=request,
            name="admin/profile.html",
            context={
                "request": request,
                "current_user": current_user,
                "active_page": "profile",
                "error": "Email address is already in use by another account.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 4. Persistence of permitted fields only (roles/permissions cannot be updated)
    updated_user = user_repository.update_profile(db, current_user, clean_name, clean_email)

    response = templates.TemplateResponse(
        request=request,
        name="admin/profile.html",
        context={
            "request": request,
            "current_user": updated_user,
            "active_page": "profile",
            "success": "Your profile has been updated successfully.",
        },
    )
    # Refresh session cookie with updated email
    auth_service.create_admin_session(response, updated_user)
    return response


@router.get("/change-password", response_class=HTMLResponse, summary="Admin Change Password View")
async def admin_change_password_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    """Renders the administrative change password interface."""
    return templates.TemplateResponse(
        request=request,
        name="admin/change_password.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_page": "change_password",
        },
    )


@router.post("/change-password", response_class=HTMLResponse, summary="Process Admin Password Change")
async def admin_change_password_post(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Processes administrative password change with policy verification and session invalidation."""
    # 1. CSRF validation
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    payload = verify_session_token(token) if token else None
    session_id = payload.get("session_id") if payload else None
    if not session_id or not csrf_token or not validate_csrf_token(session_id, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token.",
        )

    # 2. Verify current password
    if not verify_password(current_password, current_user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="admin/change_password.html",
            context={
                "request": request,
                "current_user": current_user,
                "active_page": "change_password",
                "error": "Current password is incorrect.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Reject reuse of current password
    if verify_password(new_password, current_user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="admin/change_password.html",
            context={
                "request": request,
                "current_user": current_user,
                "active_page": "change_password",
                "error": "New password cannot be the same as your current password.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 4. Check confirmation match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="admin/change_password.html",
            context={
                "request": request,
                "current_user": current_user,
                "active_page": "change_password",
                "error": "New password and confirmation password do not match.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 5. Password policy enforcement
    is_valid, msg = validate_password_strength(new_password)
    if not is_valid:
        return templates.TemplateResponse(
            request=request,
            name="admin/change_password.html",
            context={
                "request": request,
                "current_user": current_user,
                "active_page": "change_password",
                "error": msg,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 6. Hash new password & update
    new_hash = hash_password(new_password)
    updated_user = user_repository.update_password(db, current_user, new_hash)

    # 7. Render success response and issue fresh session cookie for the current session.
    # (All other active sessions having the old pwd_hash_prefix become immediately invalid).
    response = templates.TemplateResponse(
        request=request,
        name="admin/change_password.html",
        context={
            "request": request,
            "current_user": updated_user,
            "active_page": "change_password",
            "success": "Your password has been changed successfully. Other active sessions have been invalidated.",
        },
    )
    auth_service.create_admin_session(response, updated_user)
    return response


from app.models.product import Product, ProductCategory
from app.models.capability import Capability
from app.models.industry import Industry
from app.models.infrastructure import Facility, Equipment
from app.models.material import Material
from app.models.quality import Certification
from app.models.blog import BlogPost
from app.models.case_study import CaseStudy
from app.models.faq import FAQ
from app.models.download import DownloadResource
from app.models.lead import ContactLead, QuoteRequest, LeadStatus
from app.admin.products_admin import router as products_router
from app.admin.capabilities_admin import router as capabilities_router
from app.admin.industries_admin import router as industries_router
from app.admin.infrastructure_admin import router as infrastructure_router
from app.admin.materials_admin import router as materials_router
from app.admin.quality_admin import router as quality_router
from app.admin.blog_admin import router as blog_router
from app.admin.case_studies_admin import router as case_studies_router
from app.admin.faqs_admin import router as faqs_router
from app.admin.downloads_admin import router as downloads_router
from app.admin.leads_admin import router as leads_router
from app.admin.settings_admin import router as settings_router


@router.get("", response_class=HTMLResponse, summary="Super Admin Dashboard")
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Renders the Super Admin console overview dashboard."""
    counts = {
        "products": db.query(Product).count(),
        "categories": db.query(ProductCategory).count(),
        "capabilities": db.query(Capability).count(),
        "industries": db.query(Industry).count(),
        "facilities": db.query(Facility).count(),
        "equipment": db.query(Equipment).count(),
        "materials": db.query(Material).count(),
        "certifications": db.query(Certification).count(),
        "blog_posts": db.query(BlogPost).count(),
        "case_studies": db.query(CaseStudy).count(),
        "faqs": db.query(FAQ).count(),
        "downloads": db.query(DownloadResource).count(),
        "contact_leads": db.query(ContactLead).count(),
        "quote_requests": db.query(QuoteRequest).count(),
        "new_leads": db.query(ContactLead).filter(ContactLead.status == LeadStatus.NEW.value).count()
        + db.query(QuoteRequest).filter(QuoteRequest.status == LeadStatus.NEW.value).count(),
    }
    recent_products = db.query(Product).order_by(Product.id.desc()).limit(5).all()
    recent_leads = db.query(ContactLead).order_by(ContactLead.id.desc()).limit(5).all()
    recent_quotes = db.query(QuoteRequest).order_by(QuoteRequest.id.desc()).limit(5).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "request": request,
            "current_user": current_user,
            "counts": counts,
            "recent_products": recent_products,
            "recent_leads": recent_leads,
            "recent_quotes": recent_quotes,
            "active_page": "dashboard",
        },
    )


# Mount all CMS Module Routers
router.include_router(products_router)
router.include_router(capabilities_router)
router.include_router(industries_router)
router.include_router(infrastructure_router)
router.include_router(materials_router)
router.include_router(quality_router)
router.include_router(blog_router)
router.include_router(case_studies_router)
router.include_router(faqs_router)
router.include_router(downloads_router)
router.include_router(leads_router)
router.include_router(settings_router)


