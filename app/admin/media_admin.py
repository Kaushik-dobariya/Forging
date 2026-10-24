import math
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.media import MediaAsset
from app.services.media_service import media_service

router = APIRouter(prefix="/media", tags=["Admin Media Library"])


@router.get("", response_class=HTMLResponse, summary="Media Library Overview")
async def admin_media_list(
    request: Request,
    page: int = 1,
    per_page: int = 24,
    category: Optional[str] = "all",
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Renders the Enterprise Media Library with responsive modern WebP previews and SEO attributes."""
    items, total = media_service.list_media(
        db, category=category, search=search, page=page, per_page=per_page
    )
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    # Gather category choices and media metrics
    categories = [
        "all", "general", "products", "facilities", "equipment", 
        "materials", "certifications", "blog", "case_studies"
    ]
    
    total_assets = db.query(MediaAsset).count()
    webp_count = db.query(MediaAsset).filter(MediaAsset.webp_path.isnot(None)).count()
    
    return templates.TemplateResponse(
        request=request,
        name="admin/media/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "category": category,
            "categories": categories,
            "search": search or "",
            "total_assets": total_assets,
            "webp_count": webp_count,
            "active_page": "media",
        },
    )


@router.post("/upload", summary="Upload Image to Media Library")
async def admin_media_upload(
    request: Request,
    file: UploadFile = File(...),
    seo_filename: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: str = Form("general"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Uploads and optimizes image into standard and modern WebP formats with full SEO attributes."""
    try:
        media = media_service.process_and_save_image(
            db=db,
            upload_file=file,
            seo_filename=seo_filename,
            alt_text=alt_text,
            title=title,
            caption=caption,
            description=description,
            category=category,
        )
        # Check if requested as JSON (e.g. from TinyMCE or async upload modal)
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(
                content={
                    "status": "success",
                    "id": media.id,
                    "url": media.file_path,
                    "webp_url": media.webp_path,
                    "thumb_url": media.thumbnail_path,
                    "alt_text": media.alt_text,
                    "title": media.title,
                }
            )
        return RedirectResponse(url="/admin/media?msg=uploaded", status_code=status.HTTP_302_FOUND)
    except HTTPException as exc:
        logger.warning(f"Media upload failed: {exc.detail}")
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
        return RedirectResponse(url=f"/admin/media?error={exc.detail}", status_code=status.HTTP_302_FOUND)
    except Exception as exc:
        logger.error(f"Unexpected media upload error: {exc}", exc_info=True)
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(status_code=400, content={"error": str(exc)})
        return RedirectResponse(url="/admin/media?error=upload_failed", status_code=status.HTTP_302_FOUND)


@router.get("/{media_id}/json", response_class=JSONResponse, summary="Get Media Asset Details")
async def admin_media_get_json(
    media_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Returns JSON details of a media asset for editing modals."""
    media = media_service.get_media_by_id(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media asset not found")
    return {
        "id": media.id,
        "seo_filename": media.seo_filename,
        "file_path": media.file_path,
        "webp_path": media.webp_path,
        "thumbnail_path": media.thumbnail_path,
        "mime_type": media.mime_type,
        "file_size": media.file_size,
        "width": media.width,
        "height": media.height,
        "alt_text": media.alt_text,
        "title": media.title,
        "caption": media.caption,
        "description": media.description,
        "category": media.category,
    }


@router.post("/{media_id}/edit", summary="Update Media SEO Metadata")
async def admin_media_edit(
    media_id: int,
    request: Request,
    seo_filename: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Updates SEO filename, alt text, title, caption, and description of an existing media item."""
    media = media_service.update_metadata(
        db=db,
        media_id=media_id,
        seo_filename=seo_filename,
        alt_text=alt_text,
        title=title,
        caption=caption,
        description=description,
        category=category,
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media asset not found")
    
    return RedirectResponse(url="/admin/media?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/{media_id}/delete", summary="Delete Media Asset")
async def admin_media_delete(
    media_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Deletes media item and associated modern format variants from storage."""
    deleted = media_service.delete_media(db, media_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Media asset not found")
    return RedirectResponse(url="/admin/media?msg=deleted", status_code=status.HTTP_302_FOUND)
