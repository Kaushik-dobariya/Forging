import json
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.capability import Capability
from app.models.product import Product
from app.models.industry import Industry
from app.models.material import Material
from app.models.infrastructure import Equipment
from app.admin.dependencies import get_current_admin
from app.core.templates import templates
from app.utils.slug import get_unique_slug
from app.services.upload_service import upload_service
from app.core.logging import logger

router = APIRouter(prefix="/capabilities", tags=["Admin - Capabilities"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def list_capabilities(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    capabilities = db.query(Capability).order_by(Capability.display_order.asc(), Capability.id.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/capabilities/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "capabilities": capabilities,
            "active_page": "capabilities",
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_capability_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    products = db.query(Product).order_by(Product.name.asc()).all()
    industries = db.query(Industry).order_by(Industry.name.asc()).all()
    materials = db.query(Material).order_by(Material.name.asc()).all()
    equipment = db.query(Equipment).order_by(Equipment.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/capabilities/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "capability": None,
            "products": products,
            "industries": industries,
            "materials": materials,
            "equipment": equipment,
            "active_page": "capabilities",
        },
    )


@router.post("/create")
async def create_capability_post(
    title: str = Form(...),
    slug: Optional[str] = Form(None),
    short_description: Optional[str] = Form(None),
    detailed_description: Optional[str] = Form(None),
    process: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    capacity: Optional[str] = Form(None),
    technical_specifications: Optional[str] = Form(None),
    applications: Optional[str] = Form(None),
    faq_questions: List[str] = Form([]),
    faq_answers: List[str] = Form([]),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    product_ids: List[int] = Form([]),
    industry_ids: List[int] = Form([]),
    material_ids: List[int] = Form([]),
    equipment_ids: List[int] = Form([]),
    hero_image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_slug = get_unique_slug(db, Capability, slug or title)
    hero_image_url = None
    if hero_image_file and hero_image_file.filename:
        try:
            hero_image_url, _ = upload_service.save_upload(hero_image_file, subfolder="capabilities", is_image=True)
        except Exception as exc:
            logger.warning(f"Capability hero image upload failed: {exc}")

    faqs = []
    for q, a in zip(faq_questions, faq_answers):
        if q.strip() and a.strip():
            faqs.append({"question": q.strip(), "answer": a.strip()})

    capability = Capability(
        title=title.strip(),
        slug=clean_slug,
        short_description=short_description,
        detailed_description=detailed_description,
        hero_image=hero_image_url,
        process=process,
        dimensions=dimensions,
        capacity=capacity,
        technical_specifications=technical_specifications,
        applications=applications,
        faqs_json=json.dumps(faqs) if faqs else None,
        meta_title=meta_title or title,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        display_order=display_order,
        status=status,
    )

    if product_ids:
        capability.products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    if industry_ids:
        capability.industries = db.query(Industry).filter(Industry.id.in_(industry_ids)).all()
    if material_ids:
        capability.materials = db.query(Material).filter(Material.id.in_(material_ids)).all()
    if equipment_ids:
        capability.equipment = db.query(Equipment).filter(Equipment.id.in_(equipment_ids)).all()

    db.add(capability)
    db.commit()
    return RedirectResponse(url="/admin/capabilities?msg=created", status_code=status.HTTP_302_FOUND)


@router.get("/{cap_id}/edit", response_class=HTMLResponse)
async def edit_capability_form(
    cap_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    capability = db.query(Capability).filter(Capability.id == cap_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")

    products = db.query(Product).order_by(Product.name.asc()).all()
    industries = db.query(Industry).order_by(Industry.name.asc()).all()
    materials = db.query(Material).order_by(Material.name.asc()).all()
    equipment = db.query(Equipment).order_by(Equipment.name.asc()).all()

    faqs = []
    if capability.faqs_json:
        try:
            faqs = json.loads(capability.faqs_json)
        except Exception:
            faqs = []

    return templates.TemplateResponse(
        request=request,
        name="admin/capabilities/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "capability": capability,
            "faqs": faqs,
            "products": products,
            "industries": industries,
            "materials": materials,
            "equipment": equipment,
            "active_page": "capabilities",
        },
    )


@router.post("/{cap_id}/edit")
async def edit_capability_post(
    cap_id: int,
    title: str = Form(...),
    slug: str = Form(...),
    short_description: Optional[str] = Form(None),
    detailed_description: Optional[str] = Form(None),
    process: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    capacity: Optional[str] = Form(None),
    technical_specifications: Optional[str] = Form(None),
    applications: Optional[str] = Form(None),
    faq_questions: List[str] = Form([]),
    faq_answers: List[str] = Form([]),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    product_ids: List[int] = Form([]),
    industry_ids: List[int] = Form([]),
    material_ids: List[int] = Form([]),
    equipment_ids: List[int] = Form([]),
    hero_image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    capability = db.query(Capability).filter(Capability.id == cap_id).first()
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")

    clean_slug = get_unique_slug(db, Capability, slug or title, current_id=cap_id)

    if hero_image_file and hero_image_file.filename:
        try:
            hero_image_url, _ = upload_service.save_upload(hero_image_file, subfolder="capabilities", is_image=True)
            capability.hero_image = hero_image_url
        except Exception as exc:
            logger.warning(f"Capability hero image upload failed: {exc}")

    faqs = []
    for q, a in zip(faq_questions, faq_answers):
        if q.strip() and a.strip():
            faqs.append({"question": q.strip(), "answer": a.strip()})

    capability.title = title.strip()
    capability.slug = clean_slug
    capability.short_description = short_description
    capability.detailed_description = detailed_description
    capability.process = process
    capability.dimensions = dimensions
    capability.capacity = capacity
    capability.technical_specifications = technical_specifications
    capability.applications = applications
    capability.faqs_json = json.dumps(faqs) if faqs else None
    capability.meta_title = meta_title or title
    capability.meta_description = meta_description
    capability.meta_keywords = meta_keywords
    capability.display_order = display_order
    capability.status = status

    capability.products = db.query(Product).filter(Product.id.in_(product_ids)).all() if product_ids else []
    capability.industries = db.query(Industry).filter(Industry.id.in_(industry_ids)).all() if industry_ids else []
    capability.materials = db.query(Material).filter(Material.id.in_(material_ids)).all() if material_ids else []
    capability.equipment = db.query(Equipment).filter(Equipment.id.in_(equipment_ids)).all() if equipment_ids else []

    db.commit()
    return RedirectResponse(url="/admin/capabilities?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/{cap_id}/delete")
async def delete_capability(
    cap_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cap = db.query(Capability).filter(Capability.id == cap_id).first()
    if cap:
        db.delete(cap)
        db.commit()
    return RedirectResponse(url="/admin/capabilities?msg=deleted", status_code=status.HTTP_302_FOUND)
