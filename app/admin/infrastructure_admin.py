from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.infrastructure import Facility, Equipment, InfrastructureGallery
from app.models.product import Product
from app.models.capability import Capability
from app.admin.dependencies import get_current_admin
from app.core.templates import templates
from app.services.upload_service import upload_service
from app.core.logging import logger

router = APIRouter(prefix="/infrastructure", tags=["Admin - Infrastructure"])


# ==============================================================================
# FACILITIES
# ==============================================================================

@router.get("/facilities", response_class=HTMLResponse)
async def list_facilities(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    facilities = db.query(Facility).order_by(Facility.display_order.asc(), Facility.id.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/infrastructure/facilities_list.html",
        context={
            "request": request,
            "current_user": current_user,
            "facilities": facilities,
            "active_page": "infrastructure",
            "active_subpage": "facilities",
        },
    )


@router.get("/facilities/create", response_class=HTMLResponse)
async def create_facility_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/infrastructure/facility_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "facility": None,
            "active_page": "infrastructure",
            "active_subpage": "facilities",
        },
    )


@router.post("/facilities/create")
async def create_facility_post(
    name: str = Form(...),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    capacity: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    image_url = None
    if image_file and image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(image_file, subfolder="facilities", is_image=True)
        except Exception as exc:
            logger.warning(f"Facility image upload failed: {exc}")

    fac = Facility(
        name=name.strip(),
        category=category,
        description=description,
        capacity=capacity,
        specifications=specifications,
        image=image_url,
        display_order=display_order,
        status=status,
    )
    db.add(fac)
    db.commit()
    return RedirectResponse(url="/admin/infrastructure/facilities?msg=created", status_code=status.HTTP_302_FOUND)


@router.get("/facilities/{fac_id}/edit", response_class=HTMLResponse)
async def edit_facility_form(
    fac_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    fac = db.query(Facility).filter(Facility.id == fac_id).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Facility not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/infrastructure/facility_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "facility": fac,
            "active_page": "infrastructure",
            "active_subpage": "facilities",
        },
    )


@router.post("/facilities/{fac_id}/edit")
async def edit_facility_post(
    fac_id: int,
    name: str = Form(...),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    capacity: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    fac = db.query(Facility).filter(Facility.id == fac_id).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Facility not found")

    if image_file and image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(image_file, subfolder="facilities", is_image=True)
            fac.image = image_url
        except Exception as exc:
            logger.warning(f"Facility image upload failed: {exc}")

    fac.name = name.strip()
    fac.category = category
    fac.description = description
    fac.capacity = capacity
    fac.specifications = specifications
    fac.display_order = display_order
    fac.status = status

    db.commit()
    return RedirectResponse(url="/admin/infrastructure/facilities?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/facilities/{fac_id}/delete")
async def delete_facility(
    fac_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    fac = db.query(Facility).filter(Facility.id == fac_id).first()
    if fac:
        db.delete(fac)
        db.commit()
    return RedirectResponse(url="/admin/infrastructure/facilities?msg=deleted", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# EQUIPMENT / MACHINERY
# ==============================================================================

@router.get("/equipment", response_class=HTMLResponse)
async def list_equipment(
    request: Request,
    category_filter: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Equipment)
    if category_filter:
        query = query.filter(Equipment.category == category_filter)
    equipment_list = query.order_by(Equipment.display_order.asc(), Equipment.id.asc()).all()

    categories = [
        "Hydraulic Press", "Mechanical Press", "Drop Hammer", "CNC Turning",
        "CNC VMC", "Heat Treatment Furnace", "Spectrometer", "UT Machine", "Testing Equipment"
    ]

    return templates.TemplateResponse(
        request=request,
        name="admin/infrastructure/equipment_list.html",
        context={
            "request": request,
            "current_user": current_user,
            "equipment_list": equipment_list,
            "categories": categories,
            "category_filter": category_filter,
            "active_page": "infrastructure",
            "active_subpage": "equipment",
        },
    )


@router.get("/equipment/create", response_class=HTMLResponse)
async def create_equipment_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    categories = [
        "Hydraulic Press", "Mechanical Press", "Drop Hammer", "CNC Turning",
        "CNC VMC", "Heat Treatment Furnace", "Spectrometer", "UT Machine", "Testing Equipment"
    ]
    return templates.TemplateResponse(
        request=request,
        name="admin/infrastructure/equipment_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "equipment": None,
            "categories": categories,
            "active_page": "infrastructure",
            "active_subpage": "equipment",
        },
    )


@router.post("/equipment/create")
async def create_equipment_post(
    name: str = Form(...),
    category: Optional[str] = Form(None),
    manufacturer: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    capacity: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    image_file: Optional[UploadFile] = File(None),
    pdf_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    image_url = None
    if image_file and image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(image_file, subfolder="equipment", is_image=True)
        except Exception as exc:
            logger.warning(f"Equipment image upload failed: {exc}")

    pdf_url = None
    if pdf_file and pdf_file.filename:
        try:
            pdf_url, _ = upload_service.save_upload(pdf_file, subfolder="equipment_docs", is_image=False)
        except Exception as exc:
            logger.warning(f"Equipment PDF upload failed: {exc}")

    eq = Equipment(
        name=name.strip(),
        category=category,
        manufacturer=manufacturer,
        model=model,
        capacity=capacity,
        specifications=specifications,
        description=description,
        image=image_url,
        pdf_url=pdf_url,
        display_order=display_order,
        status=status,
    )
    db.add(eq)
    db.commit()
    return RedirectResponse(url="/admin/infrastructure/equipment?msg=created", status_code=status.HTTP_302_FOUND)


@router.get("/equipment/{eq_id}/edit", response_class=HTMLResponse)
async def edit_equipment_form(
    eq_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    eq = db.query(Equipment).filter(Equipment.id == eq_id).first()
    if not eq:
        raise HTTPException(status_code=404, detail="Equipment not found")

    categories = [
        "Hydraulic Press", "Mechanical Press", "Drop Hammer", "CNC Turning",
        "CNC VMC", "Heat Treatment Furnace", "Spectrometer", "UT Machine", "Testing Equipment"
    ]

    return templates.TemplateResponse(
        request=request,
        name="admin/infrastructure/equipment_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "equipment": eq,
            "categories": categories,
            "active_page": "infrastructure",
            "active_subpage": "equipment",
        },
    )


@router.post("/equipment/{eq_id}/edit")
async def edit_equipment_post(
    eq_id: int,
    name: str = Form(...),
    category: Optional[str] = Form(None),
    manufacturer: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    capacity: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    image_file: Optional[UploadFile] = File(None),
    pdf_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    eq = db.query(Equipment).filter(Equipment.id == eq_id).first()
    if not eq:
        raise HTTPException(status_code=404, detail="Equipment not found")

    if image_file and image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(image_file, subfolder="equipment", is_image=True)
            eq.image = image_url
        except Exception as exc:
            logger.warning(f"Equipment image upload failed: {exc}")

    if pdf_file and pdf_file.filename:
        try:
            pdf_url, _ = upload_service.save_upload(pdf_file, subfolder="equipment_docs", is_image=False)
            eq.pdf_url = pdf_url
        except Exception as exc:
            logger.warning(f"Equipment PDF upload failed: {exc}")

    eq.name = name.strip()
    eq.category = category
    eq.manufacturer = manufacturer
    eq.model = model
    eq.capacity = capacity
    eq.specifications = specifications
    eq.description = description
    eq.display_order = display_order
    eq.status = status

    db.commit()
    return RedirectResponse(url="/admin/infrastructure/equipment?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/equipment/{eq_id}/delete")
async def delete_equipment(
    eq_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    eq = db.query(Equipment).filter(Equipment.id == eq_id).first()
    if eq:
        db.delete(eq)
        db.commit()
    return RedirectResponse(url="/admin/infrastructure/equipment?msg=deleted", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# INFRASTRUCTURE GALLERY
# ==============================================================================

@router.get("/gallery", response_class=HTMLResponse)
async def list_gallery(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    items = db.query(InfrastructureGallery).order_by(InfrastructureGallery.display_order.asc(), InfrastructureGallery.id.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/infrastructure/gallery_list.html",
        context={
            "request": request,
            "current_user": current_user,
            "items": items,
            "active_page": "infrastructure",
            "active_subpage": "gallery",
        },
    )


@router.post("/gallery/create")
async def create_gallery_post(
    title: str = Form(...),
    category: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    image_file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        url, _ = upload_service.save_upload(image_file, subfolder="gallery", is_image=True)
        item = InfrastructureGallery(
            title=title.strip(),
            category=category,
            caption=caption,
            image_url=url,
            display_order=display_order,
            is_active=is_active,
        )
        db.add(item)
        db.commit()
    except Exception as exc:
        logger.warning(f"Gallery upload failed: {exc}")

    return RedirectResponse(url="/admin/infrastructure/gallery?msg=created", status_code=status.HTTP_302_FOUND)


@router.post("/gallery/{item_id}/delete")
async def delete_gallery_item(
    item_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(InfrastructureGallery).filter(InfrastructureGallery.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin/infrastructure/gallery?msg=deleted", status_code=status.HTTP_302_FOUND)
