import os
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.hero_slide import HeroSlide
from app.services.upload_service import upload_service

router = APIRouter(prefix="/hero-slides", tags=["Admin Hero Slider"])


@router.get("", response_class=HTMLResponse, summary="List Hero Slides")
async def admin_hero_slides_list(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    slides = db.query(HeroSlide).order_by(HeroSlide.display_order.asc(), HeroSlide.id.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/hero/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "slides": slides,
            "active_page": "hero_slides",
        },
    )


@router.get("/create", response_class=HTMLResponse, summary="New Hero Slide Form")
async def admin_hero_slide_create_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    next_order = db.query(HeroSlide).count() + 1
    return templates.TemplateResponse(
        request=request,
        name="admin/hero/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "slide": None,
            "next_order": next_order,
            "active_page": "hero_slides",
        },
    )


def _parse_opacity(val: Optional[str]) -> int:
    if val is None or str(val).strip() == "":
        return 65
    try:
        f = float(val)
        if f <= 1.0:
            return max(0, min(100, int(f * 100)))
        return max(0, min(100, int(f)))
    except (ValueError, TypeError):
        return 65


def _parse_order(val: Optional[str]) -> int:
    if val is None or str(val).strip() == "":
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


@router.post("/create", summary="Save New Hero Slide")
async def admin_hero_slide_create_post(
    request: Request,
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    eyebrow: Optional[str] = Form(None),
    background_image_url: Optional[str] = Form(None),
    background_image: Optional[UploadFile] = File(None),
    background_image_file: Optional[UploadFile] = File(None),
    primary_cta_label: Optional[str] = Form(None),
    primary_cta_url: Optional[str] = Form(None),
    secondary_cta_label: Optional[str] = Form(None),
    secondary_cta_url: Optional[str] = Form(None),
    text_align: Optional[str] = Form(None),
    text_alignment: Optional[str] = Form(None),
    overlay_opacity: Optional[str] = Form("65"),
    display_order: Optional[str] = Form("0"),
    is_active: Optional[str] = Form(None),
    image_alt: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    upload_file = background_image if (background_image and background_image.filename) else background_image_file
    bg_img = background_image_url.strip() if background_image_url and background_image_url.strip() else "/static/images/hero_slide_1.webp"

    # Handle image upload if provided
    if upload_file and upload_file.filename:
        try:
            rel_url, _ = upload_service.save_upload(upload_file, subfolder="hero", is_drawing=False)
            bg_img = rel_url
        except Exception as exc:
            logger.error(f"Failed to upload slide image: {exc}")
            next_order = db.query(HeroSlide).count() + 1
            return templates.TemplateResponse(
                request=request,
                name="admin/hero/form.html",
                context={
                    "request": request,
                    "current_user": current_user,
                    "slide": None,
                    "next_order": next_order,
                    "active_page": "hero_slides",
                    "error": f"Image upload failed: {str(exc)}",
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    chosen_align = text_align or text_alignment or "left"
    chosen_alt = image_alt or alt_text or title.strip()
    active_flag = True if is_active in ("1", "on", "true", "True", True) else False

    slide = HeroSlide(
        title=title.strip(),
        subtitle=subtitle.strip() if subtitle else None,
        eyebrow=eyebrow.strip() if eyebrow else None,
        background_image=bg_img,
        primary_cta_label=primary_cta_label.strip() if primary_cta_label else None,
        primary_cta_url=primary_cta_url.strip() if primary_cta_url else None,
        secondary_cta_label=secondary_cta_label.strip() if secondary_cta_label else None,
        secondary_cta_url=secondary_cta_url.strip() if secondary_cta_url else None,
        text_align=chosen_align,
        overlay_opacity=_parse_opacity(overlay_opacity),
        display_order=_parse_order(display_order),
        is_active=active_flag,
        image_alt=chosen_alt.strip(),
    )
    db.add(slide)
    db.commit()
    logger.info(f"Created HeroSlide id={slide.id}")
    return RedirectResponse(url="/admin/hero-slides?created=1", status_code=status.HTTP_302_FOUND)


@router.get("/{slide_id}/edit", response_class=HTMLResponse, summary="Edit Hero Slide Form")
async def admin_hero_slide_edit_view(
    slide_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    slide = db.query(HeroSlide).filter(HeroSlide.id == slide_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    return templates.TemplateResponse(
        request=request,
        name="admin/hero/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "slide": slide,
            "next_order": slide.display_order,
            "active_page": "hero_slides",
        },
    )


@router.post("/{slide_id}/edit", summary="Update Hero Slide")
async def admin_hero_slide_edit_post(
    slide_id: int,
    request: Request,
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    eyebrow: Optional[str] = Form(None),
    background_image_url: Optional[str] = Form(None),
    background_image: Optional[UploadFile] = File(None),
    background_image_file: Optional[UploadFile] = File(None),
    primary_cta_label: Optional[str] = Form(None),
    primary_cta_url: Optional[str] = Form(None),
    secondary_cta_label: Optional[str] = Form(None),
    secondary_cta_url: Optional[str] = Form(None),
    text_align: Optional[str] = Form(None),
    text_alignment: Optional[str] = Form(None),
    overlay_opacity: Optional[str] = Form("65"),
    display_order: Optional[str] = Form("0"),
    is_active: Optional[str] = Form(None),
    image_alt: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    slide = db.query(HeroSlide).filter(HeroSlide.id == slide_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")

    upload_file = background_image if (background_image and background_image.filename) else background_image_file
    if upload_file and upload_file.filename:
        try:
            rel_url, _ = upload_service.save_upload(upload_file, subfolder="hero", is_drawing=False)
            slide.background_image = rel_url
        except Exception as exc:
            logger.error(f"Failed to upload slide image: {exc}")
            return templates.TemplateResponse(
                request=request,
                name="admin/hero/form.html",
                context={
                    "request": request,
                    "current_user": current_user,
                    "slide": slide,
                    "next_order": slide.display_order,
                    "active_page": "hero_slides",
                    "error": f"Image upload failed: {str(exc)}",
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    elif background_image_url and background_image_url.strip():
        slide.background_image = background_image_url.strip()

    chosen_align = text_align or text_alignment or slide.text_align or "left"
    chosen_alt = image_alt or alt_text or slide.image_alt or title.strip()
    active_flag = True if is_active in ("1", "on", "true", "True", True) else False

    slide.title = title.strip()
    slide.subtitle = subtitle.strip() if subtitle else None
    slide.eyebrow = eyebrow.strip() if eyebrow else None
    slide.primary_cta_label = primary_cta_label.strip() if primary_cta_label else None
    slide.primary_cta_url = primary_cta_url.strip() if primary_cta_url else None
    slide.secondary_cta_label = secondary_cta_label.strip() if secondary_cta_label else None
    slide.secondary_cta_url = secondary_cta_url.strip() if secondary_cta_url else None
    slide.text_align = chosen_align
    slide.overlay_opacity = _parse_opacity(overlay_opacity)
    slide.display_order = _parse_order(display_order)
    slide.is_active = active_flag
    slide.image_alt = chosen_alt.strip()

    db.commit()
    logger.info(f"Updated HeroSlide id={slide.id}")
    return RedirectResponse(url="/admin/hero-slides?updated=1", status_code=status.HTTP_302_FOUND)



@router.post("/{slide_id}/toggle", summary="Toggle Hero Slide Active Status")
async def admin_hero_slide_toggle(
    slide_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    slide = db.query(HeroSlide).filter(HeroSlide.id == slide_id).first()
    if slide:
        slide.is_active = not slide.is_active
        db.commit()
    return RedirectResponse(url="/admin/hero-slides?toggled=1", status_code=status.HTTP_302_FOUND)


@router.post("/{slide_id}/delete", summary="Delete Hero Slide")
async def admin_hero_slide_delete(
    slide_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    slide = db.query(HeroSlide).filter(HeroSlide.id == slide_id).first()
    if slide:
        db.delete(slide)
        db.commit()
        logger.info(f"Deleted HeroSlide id={slide_id}")
    return RedirectResponse(url="/admin/hero-slides?deleted=1", status_code=status.HTTP_302_FOUND)
