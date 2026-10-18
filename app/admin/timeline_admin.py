from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.timeline import TimelineMilestone
from app.services.upload_service import upload_service

router = APIRouter(prefix="/timeline", tags=["Admin Company History Timeline"])


@router.get("", response_class=HTMLResponse, summary="List Timeline Milestones")
async def admin_timeline_list(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    milestones = db.query(TimelineMilestone).order_by(TimelineMilestone.display_order.asc(), TimelineMilestone.id.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/timeline/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "milestones": milestones,
            "active_page": "timeline",
        },
    )


@router.get("/create", response_class=HTMLResponse, summary="Create Timeline Milestone Form")
async def admin_timeline_create_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    next_order = db.query(TimelineMilestone).count() + 1
    return templates.TemplateResponse(
        request=request,
        name="admin/timeline/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "milestone": None,
            "next_order": next_order,
            "active_page": "timeline",
        },
    )


@router.post("/create", summary="Save Timeline Milestone")
async def admin_timeline_create_post(
    request: Request,
    year: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    supporting_info: Optional[str] = Form(None),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    img_path = image_url.strip() if image_url else None
    if image_file and image_file.filename:
        try:
            rel_url, _ = upload_service.save_upload(image_file, subfolder="timeline", is_drawing=False)
            img_path = rel_url
        except Exception as exc:
            logger.error(f"Failed to upload timeline image: {exc}")

    milestone = TimelineMilestone(
        year=year.strip(),
        title=title.strip(),
        description=description.strip(),
        image=img_path,
        supporting_info=supporting_info.strip() if supporting_info else None,
        display_order=display_order,
        is_active=is_active,
    )
    db.add(milestone)
    db.commit()
    logger.info(f"Created TimelineMilestone id={milestone.id} year={milestone.year}")
    return RedirectResponse(url="/admin/timeline?created=1", status_code=status.HTTP_302_FOUND)


@router.get("/{milestone_id}/edit", response_class=HTMLResponse, summary="Edit Timeline Milestone Form")
async def admin_timeline_edit_view(
    milestone_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    milestone = db.query(TimelineMilestone).filter(TimelineMilestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    return templates.TemplateResponse(
        request=request,
        name="admin/timeline/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "milestone": milestone,
            "next_order": milestone.display_order,
            "active_page": "timeline",
        },
    )


@router.post("/{milestone_id}/edit", summary="Update Timeline Milestone")
async def admin_timeline_edit_post(
    milestone_id: int,
    request: Request,
    year: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    image_url: Optional[str] = Form(None),
    image_file: Optional[UploadFile] = File(None),
    supporting_info: Optional[str] = Form(None),
    display_order: int = Form(0),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    milestone = db.query(TimelineMilestone).filter(TimelineMilestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if image_file and image_file.filename:
        try:
            rel_url, _ = upload_service.save_upload(image_file, subfolder="timeline", is_drawing=False)
            milestone.image = rel_url
        except Exception as exc:
            logger.error(f"Failed to upload timeline image: {exc}")
    elif image_url is not None:
        milestone.image = image_url.strip() if image_url.strip() else None

    milestone.year = year.strip()
    milestone.title = title.strip()
    milestone.description = description.strip()
    milestone.supporting_info = supporting_info.strip() if supporting_info else None
    milestone.display_order = display_order
    milestone.is_active = is_active

    db.commit()
    logger.info(f"Updated TimelineMilestone id={milestone.id}")
    return RedirectResponse(url="/admin/timeline?updated=1", status_code=status.HTTP_302_FOUND)


@router.post("/{milestone_id}/toggle", summary="Toggle Milestone Active Status")
async def admin_timeline_toggle(
    milestone_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    milestone = db.query(TimelineMilestone).filter(TimelineMilestone.id == milestone_id).first()
    if milestone:
        milestone.is_active = not milestone.is_active
        db.commit()
    return RedirectResponse(url="/admin/timeline?toggled=1", status_code=status.HTTP_302_FOUND)


@router.post("/{milestone_id}/delete", summary="Delete Milestone")
async def admin_timeline_delete(
    milestone_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    milestone = db.query(TimelineMilestone).filter(TimelineMilestone.id == milestone_id).first()
    if milestone:
        db.delete(milestone)
        db.commit()
        logger.info(f"Deleted TimelineMilestone id={milestone_id}")
    return RedirectResponse(url="/admin/timeline?deleted=1", status_code=status.HTTP_302_FOUND)
