from urllib.parse import urlparse
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import auth_service
from app.admin.dependencies import get_current_admin
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
@router.get("/logout", summary="Admin Logout GET")
async def admin_logout(request: Request):
    """Terminates admin session and clears cookies."""
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    auth_service.terminate_admin_session(response)
    return response


@router.get("", response_class=HTMLResponse, summary="Super Admin Dashboard")
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    """Renders the Super Admin console overview dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "request": request,
            "current_user": current_user,
        },
    )
