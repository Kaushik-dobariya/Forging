from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.menu import MenuItem, MenuLocation
from app.models.page import CMSPage
from app.services.menu_service import menu_service


router = APIRouter(prefix="/menus", tags=["Admin Navigation Menus"])


@router.get("", response_class=HTMLResponse, summary="Navigation Menus Management")
async def admin_menus_view(
    request: Request,
    location: str = "header",
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    menu_service.seed_default_menus(db)
    
    header_tree = menu_service.get_menu_tree(db, location="header", enabled_only=False)
    footer_tree = menu_service.get_menu_tree(db, location="footer", enabled_only=False)
    
    # CMS pages for dropdown linking
    cms_pages = db.query(CMSPage).order_by(CMSPage.title.asc()).all()
    
    # Root header and footer items for parent selector
    root_header_items = db.query(MenuItem).filter(MenuItem.location == "header", MenuItem.parent_id.is_(None)).all()
    root_footer_items = db.query(MenuItem).filter(MenuItem.location == "footer", MenuItem.parent_id.is_(None)).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/menus/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_location": location,
            "header_tree": header_tree,
            "footer_tree": footer_tree,
            "cms_pages": cms_pages,
            "root_header_items": root_header_items,
            "root_footer_items": root_footer_items,
            "active_page": "menus",
            "active_subpage": "menus_list",
            "MenuLocation": MenuLocation,
        },
    )


@router.post("/create", summary="Create New Menu Item")
async def admin_menu_create(
    request: Request,
    title: str = Form(...),
    url: Optional[str] = Form(None),
    page_id: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    location: str = Form(MenuLocation.HEADER.value),
    display_order: int = Form(0),
    is_enabled: bool = Form(True),
    target: str = Form("_self"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = {
        "title": title,
        "url": url or "",
        "page_id": page_id,
        "parent_id": parent_id,
        "location": location,
        "display_order": display_order,
        "is_enabled": is_enabled,
        "target": target,
    }
    try:
        menu_service.create_menu_item(db, data)
        return RedirectResponse(
            url=f"/admin/menus?location={location}&created=1",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        logger.error(f"Error creating menu item: {exc}")
        return RedirectResponse(
            url=f"/admin/menus?location={location}&error=1",
            status_code=status.HTTP_302_FOUND,
        )


@router.post("/{item_id}/edit", summary="Update Menu Item")
async def admin_menu_edit(
    item_id: int,
    request: Request,
    title: str = Form(...),
    url: Optional[str] = Form(None),
    page_id: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    location: str = Form(MenuLocation.HEADER.value),
    display_order: int = Form(0),
    is_enabled: bool = Form(True),
    target: str = Form("_self"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = {
        "title": title,
        "url": url or "",
        "page_id": page_id,
        "parent_id": parent_id,
        "location": location,
        "display_order": display_order,
        "is_enabled": is_enabled,
        "target": target,
    }
    try:
        menu_service.update_menu_item(db, item_id, data)
        return RedirectResponse(
            url=f"/admin/menus?location={location}&updated=1",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        logger.error(f"Error updating menu item #{item_id}: {exc}")
        return RedirectResponse(
            url=f"/admin/menus?location={location}&error=1",
            status_code=status.HTTP_302_FOUND,
        )


@router.post("/{item_id}/toggle", summary="Toggle Menu Item Enabled/Disabled")
async def admin_menu_toggle(
    item_id: int,
    request: Request,
    location: str = Form("header"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = menu_service.get_item_by_id(db, item_id)
    if item:
        item.is_enabled = not item.is_enabled
        db.commit()
    return RedirectResponse(
        url=f"/admin/menus?location={location}&status_updated=1",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{item_id}/delete", summary="Delete Menu Item")
async def admin_menu_delete(
    item_id: int,
    request: Request,
    location: str = Form("header"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    menu_service.delete_menu_item(db, item_id)
    return RedirectResponse(
        url=f"/admin/menus?location={location}&deleted=1",
        status_code=status.HTTP_302_FOUND,
    )
