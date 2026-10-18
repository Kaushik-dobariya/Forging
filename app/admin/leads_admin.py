from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.lead import ContactLead, QuoteRequest, LeadStatus


router = APIRouter(prefix="/leads", tags=["Admin Leads"])


# ==============================================================================
# CONTACT LEADS
# ==============================================================================

@router.get("/contact", response_class=HTMLResponse, summary="Contact Leads List")
async def admin_contact_leads_list(
    request: Request,
    st: Optional[str] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(ContactLead)
    if st:
        query = query.filter(ContactLead.status == st)
    if q:
        query = query.filter(
            ContactLead.name.ilike(f"%{q}%")
            | ContactLead.email.ilike(f"%{q}%")
            | ContactLead.company.ilike(f"%{q}%")
        )

    leads = query.order_by(ContactLead.id.desc()).all()

    counts = {
        "all": db.query(ContactLead).count(),
        "new": db.query(ContactLead).filter(ContactLead.status == LeadStatus.NEW.value).count(),
        "contacted": db.query(ContactLead).filter(ContactLead.status == LeadStatus.CONTACTED.value).count(),
        "qualified": db.query(ContactLead).filter(ContactLead.status == LeadStatus.QUALIFIED.value).count(),
        "quotation_sent": db.query(ContactLead).filter(ContactLead.status == LeadStatus.QUOTATION_SENT.value).count(),
        "won": db.query(ContactLead).filter(ContactLead.status == LeadStatus.WON.value).count(),
        "lost": db.query(ContactLead).filter(ContactLead.status == LeadStatus.LOST.value).count(),
    }

    return templates.TemplateResponse(
        request=request,
        name="admin/leads/contact_list.html",
        context={
            "request": request,
            "current_user": current_user,
            "leads": leads,
            "counts": counts,
            "st": st,
            "q": q,
            "statuses": [s.value for s in LeadStatus],
            "active_page": "leads",
            "active_subpage": "contact_leads",
        },
    )


@router.get("/contact/{lead_id}", response_class=HTMLResponse, summary="Contact Lead Details")
async def admin_contact_lead_detail(
    lead_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lead = db.query(ContactLead).filter(ContactLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Contact lead not found")

    return templates.TemplateResponse(
        request=request,
        name="admin/leads/contact_detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "lead": lead,
            "statuses": [s.value for s in LeadStatus],
            "active_page": "leads",
            "active_subpage": "contact_leads",
        },
    )


@router.post("/contact/{lead_id}/update", summary="Update Contact Lead Status & Notes")
async def admin_contact_lead_update(
    lead_id: int,
    request: Request,
    status_val: str = Form(...),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lead = db.query(ContactLead).filter(ContactLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Contact lead not found")

    old_status = lead.status
    lead.status = status_val
    lead.notes = notes.strip() if notes else None
    db.commit()
    logger.info(f"Updated ContactLead #{lead.id} status: {old_status} -> {status_val}")

    return RedirectResponse(url=f"/admin/leads/contact/{lead_id}", status_code=status.HTTP_302_FOUND)


@router.post("/contact/{lead_id}/delete", summary="Delete Contact Lead")
async def admin_contact_lead_delete(
    lead_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lead = db.query(ContactLead).filter(ContactLead.id == lead_id).first()
    if lead:
        db.delete(lead)
        db.commit()
        logger.info(f"Deleted ContactLead #{lead_id}")
    return RedirectResponse(url="/admin/leads/contact", status_code=status.HTTP_302_FOUND)


# ==============================================================================
# QUOTE REQUESTS
# ==============================================================================

@router.get("/quotes", response_class=HTMLResponse, summary="Quote Requests List")
async def admin_quote_requests_list(
    request: Request,
    st: Optional[str] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(QuoteRequest)
    if st:
        query = query.filter(QuoteRequest.status == st)
    if q:
        query = query.filter(
            QuoteRequest.customer_name.ilike(f"%{q}%")
            | QuoteRequest.company.ilike(f"%{q}%")
            | QuoteRequest.email.ilike(f"%{q}%")
            | QuoteRequest.product_component.ilike(f"%{q}%")
        )

    quotes = query.order_by(QuoteRequest.id.desc()).all()

    counts = {
        "all": db.query(QuoteRequest).count(),
        "new": db.query(QuoteRequest).filter(QuoteRequest.status == LeadStatus.NEW.value).count(),
        "contacted": db.query(QuoteRequest).filter(QuoteRequest.status == LeadStatus.CONTACTED.value).count(),
        "qualified": db.query(QuoteRequest).filter(QuoteRequest.status == LeadStatus.QUALIFIED.value).count(),
        "quotation_sent": db.query(QuoteRequest).filter(QuoteRequest.status == LeadStatus.QUOTATION_SENT.value).count(),
        "won": db.query(QuoteRequest).filter(QuoteRequest.status == LeadStatus.WON.value).count(),
        "lost": db.query(QuoteRequest).filter(QuoteRequest.status == LeadStatus.LOST.value).count(),
    }

    return templates.TemplateResponse(
        request=request,
        name="admin/leads/quote_list.html",
        context={
            "request": request,
            "current_user": current_user,
            "quotes": quotes,
            "counts": counts,
            "st": st,
            "q": q,
            "statuses": [s.value for s in LeadStatus],
            "active_page": "leads",
            "active_subpage": "quote_requests",
        },
    )


@router.get("/quotes/{quote_id}", response_class=HTMLResponse, summary="Quote Request Details")
async def admin_quote_request_detail(
    quote_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quote = db.query(QuoteRequest).filter(QuoteRequest.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote request not found")

    return templates.TemplateResponse(
        request=request,
        name="admin/leads/quote_detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "quote": quote,
            "statuses": [s.value for s in LeadStatus],
            "active_page": "leads",
            "active_subpage": "quote_requests",
        },
    )


@router.post("/quotes/{quote_id}/update", summary="Update Quote Request Status & Notes")
async def admin_quote_request_update(
    quote_id: int,
    request: Request,
    status_val: str = Form(...),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quote = db.query(QuoteRequest).filter(QuoteRequest.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote request not found")

    old_status = quote.status
    quote.status = status_val
    quote.notes = notes.strip() if notes else None
    db.commit()
    logger.info(f"Updated QuoteRequest #{quote.id} status: {old_status} -> {status_val}")

    return RedirectResponse(url=f"/admin/leads/quotes/{quote_id}", status_code=status.HTTP_302_FOUND)


@router.post("/quotes/{quote_id}/delete", summary="Delete Quote Request")
async def admin_quote_request_delete(
    quote_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quote = db.query(QuoteRequest).filter(QuoteRequest.id == quote_id).first()
    if quote:
        db.delete(quote)
        db.commit()
        logger.info(f"Deleted QuoteRequest #{quote_id}")
    return RedirectResponse(url="/admin/leads/quotes", status_code=status.HTTP_302_FOUND)
