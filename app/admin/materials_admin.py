from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.material import Material
from app.models.product import Product
from app.models.capability import Capability
from app.admin.dependencies import get_current_admin
from app.core.templates import templates
from app.utils.slug import get_unique_slug
from app.services.upload_service import upload_service
from app.core.logging import logger

router = APIRouter(prefix="/materials", tags=["Admin - Materials"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def list_materials(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    materials = db.query(Material).order_by(Material.display_order.asc(), Material.id.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/materials/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "materials": materials,
            "active_page": "materials",
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_material_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/materials/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "material": None,
            "active_page": "materials",
        },
    )


@router.post("/create")
async def create_material_post(
    name: str = Form(...),
    slug: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    standard: Optional[str] = Form(None),
    chemical_composition: Optional[str] = Form(None),
    mechanical_properties: Optional[str] = Form(None),
    applications: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    image_file: Optional[UploadFile] = File(None),
    doc_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_slug = get_unique_slug(db, Material, slug or name)
    image_url = None
    if image_file and image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(image_file, subfolder="materials", is_image=True)
        except Exception as exc:
            logger.warning(f"Material image upload failed: {exc}")

    doc_url = None
    if doc_file and doc_file.filename:
        try:
            doc_url, _ = upload_service.save_upload(doc_file, subfolder="material_docs", is_image=False)
        except Exception as exc:
            logger.warning(f"Material document upload failed: {exc}")

    mat = Material(
        name=name.strip(),
        slug=clean_slug,
        grade=grade,
        standard=standard,
        chemical_composition=chemical_composition,
        mechanical_properties=mechanical_properties,
        applications=applications,
        description=description,
        image=image_url,
        documents_url=doc_url,
        meta_title=meta_title or name,
        meta_description=meta_description,
        meta_keywords=meta_keywords,
        display_order=display_order,
        status=status,
    )
    db.add(mat)
    db.commit()
    return RedirectResponse(url="/admin/materials?msg=created", status_code=status.HTTP_302_FOUND)


@router.get("/{mat_id}/edit", response_class=HTMLResponse)
async def edit_material_form(
    mat_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    mat = db.query(Material).filter(Material.id == mat_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/materials/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "material": mat,
            "active_page": "materials",
        },
    )


@router.post("/{mat_id}/edit")
async def edit_material_post(
    mat_id: int,
    name: str = Form(...),
    slug: str = Form(...),
    grade: Optional[str] = Form(None),
    standard: Optional[str] = Form(None),
    chemical_composition: Optional[str] = Form(None),
    mechanical_properties: Optional[str] = Form(None),
    applications: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    meta_keywords: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    image_file: Optional[UploadFile] = File(None),
    doc_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    mat = db.query(Material).filter(Material.id == mat_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")

    clean_slug = get_unique_slug(db, Material, slug or name, current_id=mat_id)

    if image_file and image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(image_file, subfolder="materials", is_image=True)
            mat.image = image_url
        except Exception as exc:
            logger.warning(f"Material image upload failed: {exc}")

    if doc_file and doc_file.filename:
        try:
            doc_url, _ = upload_service.save_upload(doc_file, subfolder="material_docs", is_image=False)
            mat.documents_url = doc_url
        except Exception as exc:
            logger.warning(f"Material document upload failed: {exc}")

    mat.name = name.strip()
    mat.slug = clean_slug
    mat.grade = grade
    mat.standard = standard
    mat.chemical_composition = chemical_composition
    mat.mechanical_properties = mechanical_properties
    mat.applications = applications
    mat.description = description
    mat.meta_title = meta_title or name
    mat.meta_description = meta_description
    mat.meta_keywords = meta_keywords
    mat.display_order = display_order
    mat.status = status

    db.commit()
    return RedirectResponse(url="/admin/materials?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/{mat_id}/delete")
async def delete_material(
    mat_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    mat = db.query(Material).filter(Material.id == mat_id).first()
    if mat:
        db.delete(mat)
        db.commit()
    return RedirectResponse(url="/admin/materials?msg=deleted", status_code=status.HTTP_302_FOUND)
