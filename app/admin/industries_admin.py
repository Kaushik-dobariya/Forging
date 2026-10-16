from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.industry import Industry
from app.models.product import Product
from app.models.capability import Capability
from app.admin.dependencies import get_current_admin
from app.core.templates import templates
from app.utils.slug import get_unique_slug
from app.services.upload_service import upload_service
from app.core.logging import logger

router = APIRouter(prefix="/industries", tags=["Admin - Industries"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def list_industries(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    industries = db.query(Industry).order_by(Industry.display_order.asc(), Industry.id.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/industries/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "industries": industries,
            "active_page": "industries",
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_industry_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    products = db.query(Product).order_by(Product.name.asc()).all()
    capabilities = db.query(Capability).order_by(Capability.title.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/industries/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "industry": None,
            "products": products,
            "capabilities": capabilities,
            "active_page": "industries",
        },
    )


@router.post("/create")
async def create_industry_post(
    name: str = Form(...),
    slug: Optional[str] = Form(None),
    short_description: Optional[str] = Form(None),
    detailed_description: Optional[str] = Form(None),
    key_components: Optional[str] = Form(None),
    icon_image: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    product_ids: List[int] = Form([]),
    capability_ids: List[int] = Form([]),
    hero_image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_slug = get_unique_slug(db, Industry, slug or name)
    hero_image_url = None
    if hero_image_file and hero_image_file.filename:
        try:
            hero_image_url, _ = upload_service.save_upload(hero_image_file, subfolder="industries", is_image=True)
        except Exception as exc:
            logger.warning(f"Industry hero image upload failed: {exc}")

    ind = Industry(
        name=name.strip(),
        slug=clean_slug,
        short_description=short_description,
        detailed_description=detailed_description,
        key_components=key_components,
        icon_image=icon_image,
        hero_image=hero_image_url,
        meta_title=meta_title or name,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        display_order=display_order,
        status=status,
    )

    if product_ids:
        ind.products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    if capability_ids:
        ind.capabilities = db.query(Capability).filter(Capability.id.in_(capability_ids)).all()

    db.add(ind)
    db.commit()
    return RedirectResponse(url="/admin/industries?msg=created", status_code=status.HTTP_302_FOUND)


@router.get("/{ind_id}/edit", response_class=HTMLResponse)
async def edit_industry_form(
    ind_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    ind = db.query(Industry).filter(Industry.id == ind_id).first()
    if not ind:
        raise HTTPException(status_code=404, detail="Industry not found")

    products = db.query(Product).order_by(Product.name.asc()).all()
    capabilities = db.query(Capability).order_by(Capability.title.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/industries/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "industry": ind,
            "products": products,
            "capabilities": capabilities,
            "active_page": "industries",
        },
    )


@router.post("/{ind_id}/edit")
async def edit_industry_post(
    ind_id: int,
    name: str = Form(...),
    slug: str = Form(...),
    short_description: Optional[str] = Form(None),
    detailed_description: Optional[str] = Form(None),
    key_components: Optional[str] = Form(None),
    icon_image: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    product_ids: List[int] = Form([]),
    capability_ids: List[int] = Form([]),
    hero_image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    ind = db.query(Industry).filter(Industry.id == ind_id).first()
    if not ind:
        raise HTTPException(status_code=404, detail="Industry not found")

    clean_slug = get_unique_slug(db, Industry, slug or name, current_id=ind_id)

    if hero_image_file and hero_image_file.filename:
        try:
            hero_image_url, _ = upload_service.save_upload(hero_image_file, subfolder="industries", is_image=True)
            ind.hero_image = hero_image_url
        except Exception as exc:
            logger.warning(f"Industry hero image upload failed: {exc}")

    ind.name = name.strip()
    ind.slug = clean_slug
    ind.short_description = short_description
    ind.detailed_description = detailed_description
    ind.key_components = key_components
    ind.icon_image = icon_image
    ind.meta_title = meta_title or name
    ind.meta_description = meta_description
    ind.meta_keywords = meta_keywords
    ind.display_order = display_order
    ind.status = status

    ind.products = db.query(Product).filter(Product.id.in_(product_ids)).all() if product_ids else []
    ind.capabilities = db.query(Capability).filter(Capability.id.in_(capability_ids)).all() if capability_ids else []

    db.commit()
    return RedirectResponse(url="/admin/industries?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/{ind_id}/delete")
async def delete_industry(
    ind_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    ind = db.query(Industry).filter(Industry.id == ind_id).first()
    if ind:
        db.delete(ind)
        db.commit()
    return RedirectResponse(url="/admin/industries?msg=deleted", status_code=status.HTTP_302_FOUND)
