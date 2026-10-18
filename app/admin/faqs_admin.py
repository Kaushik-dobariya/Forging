from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.faq import FAQ


router = APIRouter(prefix="/faqs", tags=["Admin FAQs"])

ENTITY_OPTIONS = [
    "homepage",
    "products",
    "capabilities",
    "industries",
    "infrastructure",
    "materials",
    "quality",
    "certifications",
    "blog",
    "contact",
    "general",
]

CATEGORY_OPTIONS = [
    "General Forging",
    "Technical Specifications",
    "Quality & Metallurgy",
    "Tooling & Lead Times",
    "Machining & Tolerances",
    "Ordering & Logistics",
]


@router.get("", response_class=HTMLResponse, summary="FAQs List")
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_faqs_list(
    request: Request,
    entity: Optional[str] = None,
    cat: Optional[str] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(FAQ)
    if entity:
        query = query.filter(FAQ.related_entity == entity)
    if cat:
        query = query.filter(FAQ.category == cat)
    if q:
        query = query.filter(FAQ.question.ilike(f"%{q}%") | FAQ.answer.ilike(f"%{q}%"))

    faqs = query.order_by(FAQ.display_order.asc(), FAQ.id.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/faqs/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "faqs": faqs,
            "entity": entity,
            "cat": cat,
            "q": q,
            "entity_options": ENTITY_OPTIONS,
            "category_options": CATEGORY_OPTIONS,
            "active_page": "faqs",
        },
    )


@router.get("/create", response_class=HTMLResponse, summary="New FAQ Form")
async def admin_faq_create_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/faqs/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "faq": None,
            "entity_options": ENTITY_OPTIONS,
            "category_options": CATEGORY_OPTIONS,
            "active_page": "faqs",
            "is_edit": False,
        },
    )


@router.post("/create", response_class=HTMLResponse, summary="Create FAQ")
async def admin_faq_create_post(
    request: Request,
    question: str = Form(...),
    answer: str = Form(...),
    category: str = Form("General Forging"),
    related_entity: str = Form("homepage"),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    faq = FAQ(
        question=question.strip(),
        answer=answer.strip(),
        category=category.strip(),
        related_entity=related_entity.strip(),
        display_order=display_order,
        is_active=is_active,
    )
    db.add(faq)
    db.commit()
    db.refresh(faq)
    logger.info(f"Created FAQ #{faq.id} for '{faq.related_entity}'")

    return RedirectResponse(url="/admin/faqs", status_code=status.HTTP_302_FOUND)


@router.get("/{faq_id}/edit", response_class=HTMLResponse, summary="Edit FAQ Form")
async def admin_faq_edit_view(
    faq_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    return templates.TemplateResponse(
        request=request,
        name="admin/faqs/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "faq": faq,
            "entity_options": ENTITY_OPTIONS,
            "category_options": CATEGORY_OPTIONS,
            "active_page": "faqs",
            "is_edit": True,
        },
    )


@router.post("/{faq_id}/edit", response_class=HTMLResponse, summary="Update FAQ")
async def admin_faq_edit_post(
    faq_id: int,
    request: Request,
    question: str = Form(...),
    answer: str = Form(...),
    category: str = Form(...),
    related_entity: str = Form(...),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    faq.question = question.strip()
    faq.answer = answer.strip()
    faq.category = category.strip()
    faq.related_entity = related_entity.strip()
    faq.display_order = display_order
    faq.is_active = is_active

    db.commit()
    logger.info(f"Updated FAQ #{faq.id}")

    return RedirectResponse(url="/admin/faqs", status_code=status.HTTP_302_FOUND)


@router.post("/{faq_id}/delete", summary="Delete FAQ")
async def admin_faq_delete(
    faq_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if faq:
        db.delete(faq)
        db.commit()
        logger.info(f"Deleted FAQ #{faq_id}")
    return RedirectResponse(url="/admin/faqs", status_code=status.HTTP_302_FOUND)
