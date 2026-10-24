from typing import Optional
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.services.seo_audit_service import seo_audit_service

router = APIRouter(prefix="/seo", tags=["Admin SEO Engine"])


@router.get("/audit", response_class=HTMLResponse, summary="Automated SEO Health & Validation Audit")
async def admin_seo_audit_view(
    request: Request,
    severity: Optional[str] = "all",
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Runs systematic automated validation checks for duplicate titles, missing descriptions,
    missing canonicals, duplicate slugs, missing alt texts, broken links, and JSON-LD validity.
    """
    base_url = str(request.base_url).rstrip("/")
    report = seo_audit_service.run_full_audit(db, base_url=base_url)

    # Filter issues if severity selected
    filtered_issues = report["issues"]
    if severity and severity != "all":
        filtered_issues = [i for i in report["issues"] if i["severity"] == severity]

    return templates.TemplateResponse(
        request=request,
        name="admin/seo/audit.html",
        context={
            "request": request,
            "current_user": current_user,
            "report": report,
            "issues": filtered_issues,
            "selected_severity": severity,
            "active_page": "settings",
            "active_subpage": "seo_audit",
        },
    )


@router.get("/audit/json", response_class=JSONResponse, summary="Get SEO Audit JSON Data")
async def admin_seo_audit_json(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Returns the full SEO audit report as JSON for programmatic inspection or external tools."""
    base_url = str(request.base_url).rstrip("/")
    report = seo_audit_service.run_full_audit(db, base_url=base_url)
    return report
