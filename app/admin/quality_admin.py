from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.quality import QualitySection, Certification
from app.models.infrastructure import Equipment, Facility
from app.admin.dependencies import get_current_admin
from app.core.templates import templates
from app.services.upload_service import upload_service
from app.core.logging import logger

router = APIRouter(tags=["Admin - Quality & Certifications"])


# ==============================================================================
# QUALITY SECTIONS
# ==============================================================================

@router.get("/quality", response_class=HTMLResponse)
async def list_quality_sections(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    sections = db.query(QualitySection).order_by(QualitySection.display_order.asc(), QualitySection.id.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/quality/sections_list.html",
        context={
            "request": request,
            "current_user": current_user,
            "sections": sections,
            "active_page": "quality",
            "active_subpage": "quality_policy",
        },
    )


@router.get("/quality/{section_id}/edit", response_class=HTMLResponse)
async def edit_quality_section_form(
    section_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    section = db.query(QualitySection).filter(QualitySection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Quality section not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/quality/section_form.html",
        context={
            "request": request,
            "current_user": current_user,
            "section": section,
            "active_page": "quality",
            "active_subpage": "quality_policy",
        },
    )


@router.post("/quality/{section_id}/edit")
async def edit_quality_section_post(
    section_id: int,
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    content: str = Form(...),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    section = db.query(QualitySection).filter(QualitySection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Quality section not found")

    section.title = title.strip()
    section.subtitle = subtitle
    section.content = content.strip()
    section.display_order = display_order
    section.is_active = is_active

    db.commit()
    return RedirectResponse(url="/admin/quality?msg=updated", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# QUALITY TESTING LAB OVERVIEW
# ==============================================================================

@router.get("/quality/testing", response_class=HTMLResponse)
async def testing_lab_overview(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    testing_equipment = db.query(Equipment).filter(
        Equipment.category.in_(["Spectrometer", "UT Machine", "Testing Equipment"])
    ).all()
    lab_facility = db.query(Facility).filter(Facility.category == "Metallurgical Lab").first()
    testing_section = db.query(QualitySection).filter(QualitySection.section_key == "testing").first()

    return templates.TemplateResponse(
        request=request,
        name="admin/quality/testing.html",
        context={
            "request": request,
            "current_user": current_user,
            "testing_equipment": testing_equipment,
            "lab_facility": lab_facility,
            "testing_section": testing_section,
            "active_page": "quality",
            "active_subpage": "testing",
        },
    )


# ==============================================================================
# CERTIFICATIONS CRUD
# ==============================================================================

@router.get("/certifications", response_class=HTMLResponse)
async def list_certifications(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    certifications = db.query(Certification).order_by(Certification.display_order.asc(), Certification.id.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/certifications/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "certifications": certifications,
            "active_page": "quality",
            "active_subpage": "certifications",
        },
    )


@router.get("/certifications/create", response_class=HTMLResponse)
async def create_certification_form(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/certifications/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "certification": None,
            "active_page": "quality",
            "active_subpage": "certifications",
        },
    )


@router.post("/certifications/create")
async def create_certification_post(
    certificate_name: str = Form(...),
    issuing_organization: Optional[str] = Form(None),
    certificate_number: Optional[str] = Form(None),
    issue_date: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    cert_image_file: Optional[UploadFile] = File(None),
    cert_pdf_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    image_url = None
    if cert_image_file and cert_image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(cert_image_file, subfolder="certifications", is_image=True)
        except Exception as exc:
            logger.warning(f"Certificate image upload failed: {exc}")

    pdf_url = None
    if cert_pdf_file and cert_pdf_file.filename:
        try:
            pdf_url, _ = upload_service.save_upload(cert_pdf_file, subfolder="certifications_docs", is_image=False)
        except Exception as exc:
            logger.warning(f"Certificate PDF upload failed: {exc}")

    cert = Certification(
        certificate_name=certificate_name.strip(),
        issuing_organization=issuing_organization,
        certificate_number=certificate_number,
        issue_date=issue_date,
        expiry_date=expiry_date,
        description=description,
        certificate_image=image_url,
        certificate_pdf=pdf_url,
        display_order=display_order,
        status=status,
    )
    db.add(cert)
    db.commit()
    return RedirectResponse(url="/admin/certifications?msg=created", status_code=status.HTTP_302_FOUND)


@router.get("/certifications/{cert_id}/edit", response_class=HTMLResponse)
async def edit_certification_form(
    cert_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cert = db.query(Certification).filter(Certification.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    return templates.TemplateResponse(
        request=request,
        name="admin/certifications/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "certification": cert,
            "active_page": "quality",
            "active_subpage": "certifications",
        },
    )


@router.post("/certifications/{cert_id}/edit")
async def edit_certification_post(
    cert_id: int,
    certificate_name: str = Form(...),
    issuing_organization: Optional[str] = Form(None),
    certificate_number: Optional[str] = Form(None),
    issue_date: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    display_order: int = Form(0),
    status: str = Form("published"),
    cert_image_file: Optional[UploadFile] = File(None),
    cert_pdf_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cert = db.query(Certification).filter(Certification.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    if cert_image_file and cert_image_file.filename:
        try:
            image_url, _ = upload_service.save_upload(cert_image_file, subfolder="certifications", is_image=True)
            cert.certificate_image = image_url
        except Exception as exc:
            logger.warning(f"Certificate image upload failed: {exc}")

    if cert_pdf_file and cert_pdf_file.filename:
        try:
            pdf_url, _ = upload_service.save_upload(cert_pdf_file, subfolder="certifications_docs", is_image=False)
            cert.certificate_pdf = pdf_url
        except Exception as exc:
            logger.warning(f"Certificate PDF upload failed: {exc}")

    cert.certificate_name = certificate_name.strip()
    cert.issuing_organization = issuing_organization
    cert.certificate_number = certificate_number
    cert.issue_date = issue_date
    cert.expiry_date = expiry_date
    cert.description = description
    cert.display_order = display_order
    cert.status = status

    db.commit()
    return RedirectResponse(url="/admin/certifications?msg=updated", status_code=status.HTTP_302_FOUND)


@router.post("/certifications/{cert_id}/delete")
async def delete_certification(
    cert_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cert = db.query(Certification).filter(Certification.id == cert_id).first()
    if cert:
        db.delete(cert)
        db.commit()
    return RedirectResponse(url="/admin/certifications?msg=deleted", status_code=status.HTTP_302_FOUND)
