import math
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.page import CMSPage, PageStatus
from app.services.page_service import page_service
from app.services.upload_service import upload_service


router = APIRouter(prefix="/pages", tags=["Admin Pages Management"])


@router.get("", response_class=HTMLResponse, summary="List CMS Pages")
async def admin_pages_list(
    request: Request,
    page: int = 1,
    per_page: int = 15,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    parent_id: Optional[int] = None,
    sort_by: str = "display_order",
    sort_order: str = "asc",
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    pages, total = page_service.list_pages(
        db,
        status=status_filter if status_filter and status_filter != "all" else None,
        search=search,
        parent_id=parent_id,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    # Fetch root pages for filter dropdown
    root_pages = db.query(CMSPage).filter(CMSPage.parent_id.is_(None)).order_by(CMSPage.title.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/pages/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "pages": pages,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "status_filter": status_filter or "all",
            "search": search or "",
            "parent_id": parent_id,
            "root_pages": root_pages,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "active_page": "pages",
            "active_subpage": "pages_list",
            "PageStatus": PageStatus,
        },
    )


@router.get("/create", response_class=HTMLResponse, summary="New CMS Page Form")
async def admin_page_create_view(
    request: Request,
    parent_id: Optional[int] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    # Fetch potential parents
    potential_parents = db.query(CMSPage).order_by(CMSPage.title.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/pages/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "page_item": None,
            "potential_parents": potential_parents,
            "default_parent_id": parent_id,
            "active_page": "pages",
            "active_subpage": "pages_create",
            "PageStatus": PageStatus,
        },
    )


@router.post("/create", summary="Save New CMS Page")
async def admin_page_create_post(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    form = await request.form()
    title = str(form.get("title", "")).strip()
    slug = str(form.get("slug", "")).strip() or None
    content = str(form.get("content", ""))
    parent_id_val = form.get("parent_id")
    parent_id = int(parent_id_val) if parent_id_val and str(parent_id_val).isdigit() else None
    menu_display_name = str(form.get("menu_display_name", "")).strip() or None
    menu_visibility = str(form.get("menu_visibility", "")).lower() in ("true", "1", "on", "yes")
    footer_visibility = str(form.get("footer_visibility", "")).lower() in ("true", "1", "on", "yes")
    display_order_val = form.get("display_order", 0)
    try:
        display_order = int(display_order_val)
    except (ValueError, TypeError):
        display_order = 0
    page_status = str(form.get("page_status", PageStatus.PUBLISHED.value))
    meta_title = str(form.get("meta_title", "")).strip() or None
    meta_description = str(form.get("meta_description", "")).strip() or None
    meta_keywords = str(form.get("meta_keywords", "")).strip() or None
    canonical_url = str(form.get("canonical_url", "")).strip() or None
    og_title = str(form.get("og_title", "")).strip() or None
    og_description = str(form.get("og_description", "")).strip() or None
    featured_image_url = str(form.get("featured_image_url", "")).strip() or None
    og_image_url = str(form.get("og_image_url", "")).strip() or None

    # Handle optional image uploads
    featured_image = featured_image_url
    featured_image_file = form.get("featured_image_file")
    if featured_image_file and hasattr(featured_image_file, "filename") and featured_image_file.filename:
        try:
            up_path = await upload_service.save_file(featured_image_file, subfolder="pages")
            featured_image = up_path
        except Exception as e:
            logger.warning(f"Featured image upload failed: {e}")

    og_image = og_image_url
    og_image_file = form.get("og_image_file")
    if og_image_file and hasattr(og_image_file, "filename") and og_image_file.filename:
        try:
            up_path = await upload_service.save_file(og_image_file, subfolder="pages")
            og_image = up_path
        except Exception as e:
            logger.warning(f"OG image upload failed: {e}")

    data = {
        "title": title,
        "slug": slug or "",
        "content": content,
        "parent_id": parent_id if parent_id and parent_id > 0 else None,
        "menu_display_name": menu_display_name or title,
        "menu_visibility": menu_visibility,
        "footer_visibility": footer_visibility,
        "display_order": display_order,
        "status": page_status,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "meta_keywords": meta_keywords,
        "canonical_url": canonical_url,
        "og_title": og_title,
        "og_description": og_description,
        "featured_image": featured_image,
        "og_image": og_image,
    }

    try:
        new_page = page_service.create_page(db, data)
        return RedirectResponse(
            url=f"/admin/pages?created=1",
            status_code=status.HTTP_302_FOUND,
        )
    except ValueError as val_err:
        potential_parents = db.query(CMSPage).order_by(CMSPage.title.asc()).all()
        return templates.TemplateResponse(
            request=request,
            name="admin/pages/form.html",
            context={
                "request": request,
                "current_user": current_user,
                "page_item": None,
                "potential_parents": potential_parents,
                "default_parent_id": parent_id,
                "form_data": data,
                "error_message": str(val_err),
                "active_page": "pages",
                "active_subpage": "pages_create",
                "PageStatus": PageStatus,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/{page_id}/edit", response_class=HTMLResponse, summary="Edit CMS Page Form")
async def admin_page_edit_view(
    page_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    page_item = page_service.get_page_by_id(db, page_id)
    if not page_item:
        raise HTTPException(status_code=404, detail="Page not found.")

    # Exclude self from potential parents to prevent loops
    potential_parents = (
        db.query(CMSPage)
        .filter(CMSPage.id != page_id)
        .order_by(CMSPage.title.asc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/pages/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "page_item": page_item,
            "potential_parents": potential_parents,
            "active_page": "pages",
            "active_subpage": "pages_edit",
            "PageStatus": PageStatus,
        },
    )


@router.post("/{page_id}/edit", summary="Save CMS Page Changes")
async def admin_page_edit_post(
    page_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    page_item = page_service.get_page_by_id(db, page_id)
    if not page_item:
        raise HTTPException(status_code=404, detail="Page not found.")

    form = await request.form()
    title = str(form.get("title", "")).strip()
    slug = str(form.get("slug", "")).strip() or None
    content = str(form.get("content", ""))
    parent_id_val = form.get("parent_id")
    parent_id = int(parent_id_val) if parent_id_val and str(parent_id_val).isdigit() else None
    menu_display_name = str(form.get("menu_display_name", "")).strip() or None
    menu_visibility = str(form.get("menu_visibility", "")).lower() in ("true", "1", "on", "yes")
    footer_visibility = str(form.get("footer_visibility", "")).lower() in ("true", "1", "on", "yes")
    display_order_val = form.get("display_order", 0)
    try:
        display_order = int(display_order_val)
    except (ValueError, TypeError):
        display_order = 0
    page_status = str(form.get("page_status", PageStatus.PUBLISHED.value))
    meta_title = str(form.get("meta_title", "")).strip() or None
    meta_description = str(form.get("meta_description", "")).strip() or None
    meta_keywords = str(form.get("meta_keywords", "")).strip() or None
    canonical_url = str(form.get("canonical_url", "")).strip() or None
    og_title = str(form.get("og_title", "")).strip() or None
    og_description = str(form.get("og_description", "")).strip() or None
    featured_image_url = str(form.get("featured_image_url", "")).strip() or None
    og_image_url = str(form.get("og_image_url", "")).strip() or None
    create_redirect = str(form.get("create_redirect", "")).lower() in ("true", "1", "on", "yes")

    featured_image = featured_image_url if featured_image_url is not None else page_item.featured_image
    featured_image_file = form.get("featured_image_file")
    if featured_image_file and hasattr(featured_image_file, "filename") and featured_image_file.filename:
        try:
            up_path = await upload_service.save_file(featured_image_file, subfolder="pages")
            featured_image = up_path
        except Exception as e:
            logger.warning(f"Featured image upload failed: {e}")

    og_image = og_image_url if og_image_url is not None else page_item.og_image
    og_image_file = form.get("og_image_file")
    if og_image_file and hasattr(og_image_file, "filename") and og_image_file.filename:
        try:
            up_path = await upload_service.save_file(og_image_file, subfolder="pages")
            og_image = up_path
        except Exception as e:
            logger.warning(f"OG image upload failed: {e}")

    data = {
        "title": title,
        "slug": slug or "",
        "content": content,
        "parent_id": parent_id if parent_id and parent_id > 0 else None,
        "menu_display_name": menu_display_name or title,
        "menu_visibility": menu_visibility,
        "footer_visibility": footer_visibility,
        "display_order": display_order,
        "status": page_status,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "meta_keywords": meta_keywords,
        "canonical_url": canonical_url,
        "og_title": og_title,
        "og_description": og_description,
        "featured_image": featured_image,
        "og_image": og_image,
    }

    try:
        updated_page = page_service.update_page(db, page_id, data, create_redirect_on_slug_change=create_redirect)
        return RedirectResponse(
            url=f"/admin/pages?updated=1",
            status_code=status.HTTP_302_FOUND,
        )
    except ValueError as val_err:
        potential_parents = (
            db.query(CMSPage)
            .filter(CMSPage.id != page_id)
            .order_by(CMSPage.title.asc())
            .all()
        )
        return templates.TemplateResponse(
            request=request,
            name="admin/pages/form.html",
            context={
                "request": request,
                "current_user": current_user,
                "page_item": page_item,
                "potential_parents": potential_parents,
                "form_data": data,
                "error_message": str(val_err),
                "active_page": "pages",
                "active_subpage": "pages_edit",
                "PageStatus": PageStatus,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.post("/{page_id}/toggle-status", summary="Toggle Page Published/Draft Status")
async def admin_page_toggle_status(
    page_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    page_item = page_service.get_page_by_id(db, page_id)
    if page_item:
        new_status = (
            PageStatus.DRAFT.value
            if page_item.status == PageStatus.PUBLISHED.value
            else PageStatus.PUBLISHED.value
        )
        page_item.status = new_status
        db.commit()
        logger.info(f"Toggled status of page #{page_id} to {new_status}")
    return RedirectResponse(url="/admin/pages?status_updated=1", status_code=status.HTTP_302_FOUND)


@router.post("/{page_id}/delete", summary="Delete CMS Page")
async def admin_page_delete(
    page_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    success, message = page_service.delete_page(db, page_id)
    if not success:
        import urllib.parse
        encoded_err = urllib.parse.quote(message)
        return RedirectResponse(
            url=f"/admin/pages?error={encoded_err}",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(url="/admin/pages?deleted=1", status_code=status.HTTP_302_FOUND)
