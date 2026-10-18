from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.download import DownloadResource, DownloadCategory, DownloadVisibility
from app.models.product import Product
from app.models.capability import Capability
from app.services.upload_service import upload_service


router = APIRouter(prefix="/downloads", tags=["Admin Downloads"])


@router.get("", response_class=HTMLResponse, summary="Downloads List")
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_downloads_list(
    request: Request,
    cat: Optional[str] = None,
    vis: Optional[str] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DownloadResource)
    if cat:
        query = query.filter(DownloadResource.category == cat)
    if vis:
        query = query.filter(DownloadResource.visibility == vis)
    if q:
        query = query.filter(DownloadResource.title.ilike(f"%{q}%") | DownloadResource.description.ilike(f"%{q}%"))

    items = query.order_by(DownloadResource.display_order.asc(), DownloadResource.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/downloads/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "items": items,
            "cat": cat,
            "vis": vis,
            "q": q,
            "categories": [c.value for c in DownloadCategory],
            "visibilities": [v.value for v in DownloadVisibility],
            "active_page": "downloads",
        },
    )


@router.get("/create", response_class=HTMLResponse, summary="Upload Resource Form")
async def admin_download_create_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    products = db.query(Product).order_by(Product.name.asc()).all()
    capabilities = db.query(Capability).order_by(Capability.title.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/downloads/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "item": None,
            "categories": [c.value for c in DownloadCategory],
            "visibilities": [v.value for v in DownloadVisibility],
            "products": products,
            "capabilities": capabilities,
            "active_page": "downloads",
            "is_edit": False,
        },
    )


@router.post("/create", response_class=HTMLResponse, summary="Create Resource")
async def admin_download_create_post(
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form(DownloadCategory.BROCHURE.value),
    visibility: str = Form(DownloadVisibility.PUBLIC.value),
    related_product_id: Optional[int] = Form(None),
    related_capability_id: Optional[int] = Form(None),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    resource_file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not resource_file or not resource_file.filename:
        raise HTTPException(status_code=400, detail="A file upload is required.")

    # Save uploaded file
    try:
        rel_url, disk_path = upload_service.save_upload(resource_file, subfolder="downloads", is_resource=True)
    except Exception as exc:
        logger.error(f"Resource upload failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))

    ext = Path(resource_file.filename).suffix.upper().replace(".", "")
    file_size = 0
    try:
        file_size = Path(disk_path).stat().st_size
    except Exception:
        pass

    resource = DownloadResource(
        title=title.strip(),
        description=description.strip() if description else None,
        file_path=rel_url,
        file_type=ext or "PDF",
        file_size_bytes=file_size,
        category=category,
        related_product_id=related_product_id if related_product_id and related_product_id > 0 else None,
        related_capability_id=related_capability_id if related_capability_id and related_capability_id > 0 else None,
        visibility=visibility,
        display_order=display_order,
        is_active=is_active,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    logger.info(f"Created download resource #{resource.id} '{resource.title}' ({resource.file_type})")

    return RedirectResponse(url="/admin/downloads", status_code=status.HTTP_302_FOUND)


@router.get("/{item_id}/edit", response_class=HTMLResponse, summary="Edit Resource Form")
async def admin_download_edit_view(
    item_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(DownloadResource).filter(DownloadResource.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Resource not found")

    products = db.query(Product).order_by(Product.name.asc()).all()
    capabilities = db.query(Capability).order_by(Capability.title.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/downloads/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "item": item,
            "categories": [c.value for c in DownloadCategory],
            "visibilities": [v.value for v in DownloadVisibility],
            "products": products,
            "capabilities": capabilities,
            "active_page": "downloads",
            "is_edit": True,
        },
    )


@router.post("/{item_id}/edit", response_class=HTMLResponse, summary="Update Resource")
async def admin_download_edit_post(
    item_id: int,
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form(...),
    visibility: str = Form(...),
    related_product_id: Optional[int] = Form(None),
    related_capability_id: Optional[int] = Form(None),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    resource_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(DownloadResource).filter(DownloadResource.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Resource not found")

    if resource_file and resource_file.filename:
        try:
            rel_url, disk_path = upload_service.save_upload(resource_file, subfolder="downloads", is_resource=True)
            item.file_path = rel_url
            item.file_type = Path(resource_file.filename).suffix.upper().replace(".", "")
            item.file_size_bytes = Path(disk_path).stat().st_size
        except Exception as exc:
            logger.error(f"Resource file update failed: {exc}")

    item.title = title.strip()
    item.description = description.strip() if description else None
    item.category = category
    item.visibility = visibility
    item.related_product_id = related_product_id if related_product_id and related_product_id > 0 else None
    item.related_capability_id = related_capability_id if related_capability_id and related_capability_id > 0 else None
    item.display_order = display_order
    item.is_active = is_active

    db.commit()
    logger.info(f"Updated download resource #{item.id}")

    return RedirectResponse(url="/admin/downloads", status_code=status.HTTP_302_FOUND)


@router.post("/{item_id}/delete", summary="Delete Resource")
async def admin_download_delete(
    item_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(DownloadResource).filter(DownloadResource.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
        logger.info(f"Deleted download resource #{item_id}")
    return RedirectResponse(url="/admin/downloads", status_code=status.HTTP_302_FOUND)
