import json
import re
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.case_study import CaseStudy
from app.services.upload_service import upload_service


router = APIRouter(prefix="/case-studies", tags=["Admin Case Studies"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


@router.get("", response_class=HTMLResponse, summary="Case Studies List")
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_case_studies_list(
    request: Request,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(CaseStudy)
    if q:
        query = query.filter(CaseStudy.title.ilike(f"%{q}%") | CaseStudy.client_industry.ilike(f"%{q}%"))

    case_studies = query.order_by(CaseStudy.display_order.asc(), CaseStudy.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/case_studies/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "case_studies": case_studies,
            "q": q,
            "active_page": "case_studies",
        },
    )


@router.get("/create", response_class=HTMLResponse, summary="New Case Study Form")
async def admin_case_study_create_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/case_studies/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "item": None,
            "active_page": "case_studies",
            "is_edit": False,
        },
    )


@router.post("/create", response_class=HTMLResponse, summary="Create Case Study")
async def admin_case_study_create_post(
    request: Request,
    title: str = Form(...),
    slug: Optional[str] = Form(None),
    client_industry: str = Form(...),
    client_challenge: str = Form(...),
    engineering_approach: str = Form(...),
    material: str = Form(...),
    forging_process: str = Form(...),
    machining: Optional[str] = Form(None),
    quality_requirements: Optional[str] = Form(None),
    result: str = Form(...),
    cta_text: str = Form("Request an Engineering Consultation"),
    cta_link: str = Form("/request-a-quote"),
    seo_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    status_val: str = Form("published"),
    display_order: int = Form(0),
    gallery_raw: Optional[str] = Form(None),
    downloads_raw: Optional[str] = Form(None),
    featured_image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_slug = slugify(slug) if slug and slug.strip() else slugify(title)
    if not clean_slug:
        clean_slug = f"case-study-{int(request.state.time() if hasattr(request.state, 'time') else 1)}"

    existing = db.query(CaseStudy).filter(CaseStudy.slug == clean_slug).first()
    if existing:
        clean_slug = f"{clean_slug}-new"

    featured_image_url = None
    if featured_image_file and featured_image_file.filename:
        try:
            rel_url, _ = upload_service.save_upload(featured_image_file, subfolder="case_studies", is_image=True)
            featured_image_url = rel_url
        except Exception as exc:
            logger.warning(f"Featured image upload failed: {exc}")

    # Process gallery JSON (convert comma or newline separated image links to JSON if needed)
    gallery_json = None
    if gallery_raw and gallery_raw.strip():
        try:
            # check if valid JSON already
            json.loads(gallery_raw)
            gallery_json = gallery_raw.strip()
        except Exception:
            lines = [l.strip() for l in gallery_raw.strip().splitlines() if l.strip()]
            gallery_json = json.dumps(lines)

    downloads_json = None
    if downloads_raw and downloads_raw.strip():
        try:
            json.loads(downloads_raw)
            downloads_json = downloads_raw.strip()
        except Exception:
            lines = [l.strip() for l in downloads_raw.strip().splitlines() if l.strip()]
            downloads_json = json.dumps([{"title": "Technical Drawing", "url": l} for l in lines])

    case_study = CaseStudy(
        title=title.strip(),
        slug=clean_slug,
        featured_image=featured_image_url,
        client_industry=client_industry.strip(),
        client_challenge=client_challenge.strip(),
        engineering_approach=engineering_approach.strip(),
        material=material.strip(),
        forging_process=forging_process.strip(),
        machining=machining.strip() if machining else None,
        quality_requirements=quality_requirements.strip() if quality_requirements else None,
        result=result.strip(),
        gallery_json=gallery_json,
        downloads_json=downloads_json,
        cta_text=cta_text.strip(),
        cta_link=cta_link.strip(),
        seo_title=seo_title.strip() if seo_title else title.strip(),
        meta_description=meta_description.strip() if meta_description else client_challenge.strip()[:160],
        status=status_val,
        display_order=display_order,
    )
    db.add(case_study)
    db.commit()
    db.refresh(case_study)
    logger.info(f"Created case study #{case_study.id} '{case_study.title}'")

    return RedirectResponse(url="/admin/case-studies", status_code=status.HTTP_302_FOUND)


@router.get("/{item_id}/edit", response_class=HTMLResponse, summary="Edit Case Study")
async def admin_case_study_edit_view(
    item_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(CaseStudy).filter(CaseStudy.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Case study not found")

    return templates.TemplateResponse(
        request=request,
        name="admin/case_studies/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "item": item,
            "active_page": "case_studies",
            "is_edit": True,
        },
    )


@router.post("/{item_id}/edit", response_class=HTMLResponse, summary="Update Case Study")
async def admin_case_study_edit_post(
    item_id: int,
    request: Request,
    title: str = Form(...),
    slug: Optional[str] = Form(None),
    client_industry: str = Form(...),
    client_challenge: str = Form(...),
    engineering_approach: str = Form(...),
    material: str = Form(...),
    forging_process: str = Form(...),
    machining: Optional[str] = Form(None),
    quality_requirements: Optional[str] = Form(None),
    result: str = Form(...),
    cta_text: str = Form("Request an Engineering Consultation"),
    cta_link: str = Form("/request-a-quote"),
    seo_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    status_val: str = Form("published"),
    display_order: int = Form(0),
    gallery_raw: Optional[str] = Form(None),
    downloads_raw: Optional[str] = Form(None),
    featured_image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(CaseStudy).filter(CaseStudy.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Case study not found")

    clean_slug = slugify(slug) if slug and slug.strip() else slugify(title)
    existing = db.query(CaseStudy).filter(CaseStudy.slug == clean_slug, CaseStudy.id != item_id).first()
    if existing:
        clean_slug = f"{clean_slug}-{item_id}"

    if featured_image_file and featured_image_file.filename:
        try:
            rel_url, _ = upload_service.save_upload(featured_image_file, subfolder="case_studies", is_image=True)
            item.featured_image = rel_url
        except Exception as exc:
            logger.warning(f"Featured image update failed: {exc}")

    if gallery_raw is not None:
        try:
            json.loads(gallery_raw)
            item.gallery_json = gallery_raw.strip() if gallery_raw.strip() else None
        except Exception:
            lines = [l.strip() for l in gallery_raw.strip().splitlines() if l.strip()]
            item.gallery_json = json.dumps(lines) if lines else None

    if downloads_raw is not None:
        try:
            json.loads(downloads_raw)
            item.downloads_json = downloads_raw.strip() if downloads_raw.strip() else None
        except Exception:
            lines = [l.strip() for l in downloads_raw.strip().splitlines() if l.strip()]
            item.downloads_json = json.dumps([{"title": "Technical Document", "url": l} for l in lines]) if lines else None

    item.title = title.strip()
    item.slug = clean_slug
    item.client_industry = client_industry.strip()
    item.client_challenge = client_challenge.strip()
    item.engineering_approach = engineering_approach.strip()
    item.material = material.strip()
    item.forging_process = forging_process.strip()
    item.machining = machining.strip() if machining else None
    item.quality_requirements = quality_requirements.strip() if quality_requirements else None
    item.result = result.strip()
    item.cta_text = cta_text.strip()
    item.cta_link = cta_link.strip()
    item.seo_title = seo_title.strip() if seo_title else title.strip()
    item.meta_description = meta_description.strip() if meta_description else client_challenge.strip()[:160]
    item.status = status_val
    item.display_order = display_order

    db.commit()
    logger.info(f"Updated case study #{item.id} '{item.title}'")

    return RedirectResponse(url="/admin/case-studies", status_code=status.HTTP_302_FOUND)


@router.post("/{item_id}/delete", summary="Delete Case Study")
async def admin_case_study_delete(
    item_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    item = db.query(CaseStudy).filter(CaseStudy.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
        logger.info(f"Deleted case study #{item_id}")
    return RedirectResponse(url="/admin/case-studies", status_code=status.HTTP_302_FOUND)
