import math
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.redirect import URLRedirect
from app.services.redirect_service import redirect_service

router = APIRouter(prefix="/redirects", tags=["Admin Redirects"])


@router.get("", response_class=HTMLResponse, summary="List URL Redirects")
async def admin_redirects_list(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    test_path: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    items, total = redirect_service.list_redirects(
        db, search=search, page=page, per_page=per_page
    )
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    # Optional test redirect result
    test_result = None
    if test_path:
        resolved = redirect_service.resolve_redirect(db, test_path)
        if resolved:
            test_result = {
                "source": test_path,
                "target": resolved[0],
                "status_code": resolved[1],
            }
        else:
            test_result = {
                "source": test_path,
                "target": None,
                "status_code": None,
            }

    return templates.TemplateResponse(
        request=request,
        name="admin/redirects/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "search": search or "",
            "test_path": test_path or "",
            "test_result": test_result,
            "active_page": "redirects",
            "active_subpage": "redirects_list",
        },
    )


@router.get("/create", response_class=HTMLResponse, summary="Create Redirect Form")
async def admin_redirect_create_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/redirects/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "item": None,
            "active_page": "redirects",
            "active_subpage": "redirects_create",
        },
    )


@router.post("/create", summary="Save New Redirect")
async def admin_redirect_create_post(
    request: Request,
    source_path: str = Form(...),
    target_path: str = Form(...),
    status_code: int = Form(301),
    notes: Optional[str] = Form(None),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    redirect_rule, error_msg = redirect_service.create_redirect(
        db,
        source_path=source_path,
        target_path=target_path,
        status_code=status_code,
        notes=notes,
        is_active=is_active,
    )
    if error_msg:
        return templates.TemplateResponse(
            request=request,
            name="admin/redirects/form.html",
            context={
                "request": request,
                "current_user": current_user,
                "item": None,
                "form_data": {
                    "source_path": source_path,
                    "target_path": target_path,
                    "status_code": status_code,
                    "notes": notes,
                    "is_active": is_active,
                },
                "error": error_msg,
                "active_page": "redirects",
                "active_subpage": "redirects_create",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return RedirectResponse(url="/admin/redirects?created=1", status_code=status.HTTP_302_FOUND)


@router.get("/{redirect_id}/edit", response_class=HTMLResponse, summary="Edit Redirect Form")
async def admin_redirect_edit_view(
    redirect_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = redirect_service.get_redirect_by_id(db, redirect_id)
    if not item:
        raise HTTPException(status_code=404, detail="Redirect rule not found.")

    return templates.TemplateResponse(
        request=request,
        name="admin/redirects/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "item": item,
            "active_page": "redirects",
            "active_subpage": "redirects_edit",
        },
    )


@router.post("/{redirect_id}/edit", summary="Update Redirect")
async def admin_redirect_edit_post(
    redirect_id: int,
    request: Request,
    source_path: str = Form(...),
    target_path: str = Form(...),
    status_code: int = Form(301),
    notes: Optional[str] = Form(None),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    redirect_rule, error_msg = redirect_service.update_redirect(
        db,
        redirect_id=redirect_id,
        source_path=source_path,
        target_path=target_path,
        status_code=status_code,
        notes=notes,
        is_active=is_active,
    )
    if error_msg:
        item = redirect_service.get_redirect_by_id(db, redirect_id)
        return templates.TemplateResponse(
            request=request,
            name="admin/redirects/form.html",
            context={
                "request": request,
                "current_user": current_user,
                "item": item,
                "form_data": {
                    "source_path": source_path,
                    "target_path": target_path,
                    "status_code": status_code,
                    "notes": notes,
                    "is_active": is_active,
                },
                "error": error_msg,
                "active_page": "redirects",
                "active_subpage": "redirects_edit",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return RedirectResponse(url="/admin/redirects?updated=1", status_code=status.HTTP_302_FOUND)


@router.post("/{redirect_id}/toggle", summary="Toggle Redirect Status")
async def admin_redirect_toggle_post(
    redirect_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    redirect_service.toggle_redirect(db, redirect_id)
    return RedirectResponse(url="/admin/redirects?toggled=1", status_code=status.HTTP_302_FOUND)


@router.post("/{redirect_id}/delete", summary="Delete Redirect Rule")
async def admin_redirect_delete_post(
    redirect_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    redirect_service.delete_redirect(db, redirect_id)
    return RedirectResponse(url="/admin/redirects?deleted=1", status_code=status.HTTP_302_FOUND)
