import re
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.templates import templates
from app.core.logging import logger
from app.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.blog import BlogPost, BlogCategory, BlogPostStatus
from app.services.upload_service import upload_service


router = APIRouter(prefix="/blog", tags=["Admin Blog"])


def slugify(text: str) -> str:
    """Generates URL-friendly slug from string."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


@router.get("", response_class=HTMLResponse, summary="Blog Articles List")
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_blog_list(
    request: Request,
    q: Optional[str] = None,
    cat: Optional[str] = None,
    st: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(BlogPost)
    if q:
        query = query.filter(BlogPost.title.ilike(f"%{q}%") | BlogPost.tags.ilike(f"%{q}%"))
    if cat:
        query = query.filter(BlogPost.category == cat)
    if st:
        query = query.filter(BlogPost.status == st)

    posts = query.order_by(BlogPost.publish_date.desc(), BlogPost.id.desc()).all()

    counts = {
        "total": db.query(BlogPost).count(),
        "published": db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.PUBLISHED.value).count(),
        "draft": db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.DRAFT.value).count(),
        "scheduled": db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.SCHEDULED.value).count(),
        "archived": db.query(BlogPost).filter(BlogPost.status == BlogPostStatus.ARCHIVED.value).count(),
    }

    return templates.TemplateResponse(
        request=request,
        name="admin/blog/list.html",
        context={
            "request": request,
            "current_user": current_user,
            "posts": posts,
            "counts": counts,
            "q": q,
            "cat": cat,
            "st": st,
            "categories": [c.value for c in BlogCategory],
            "statuses": [s.value for s in BlogPostStatus],
            "active_page": "blog",
        },
    )


@router.get("/create", response_class=HTMLResponse, summary="New Article Form")
async def admin_blog_create_view(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    return templates.TemplateResponse(
        request=request,
        name="admin/blog/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "post": None,
            "categories": [c.value for c in BlogCategory],
            "statuses": [s.value for s in BlogPostStatus],
            "active_page": "blog",
            "is_edit": False,
        },
    )


@router.post("/create", response_class=HTMLResponse, summary="Create Article")
async def admin_blog_create_post(
    request: Request,
    title: str = Form(...),
    slug: Optional[str] = Form(None),
    author: str = Form("Forging Engineering Team"),
    category: str = Form(BlogCategory.FORGING_TECHNOLOGY.value),
    excerpt: str = Form(...),
    content: str = Form(...),
    tags: Optional[str] = Form(None),
    publish_date: Optional[str] = Form(None),
    status_val: str = Form("draft"),
    seo_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    canonical_url: Optional[str] = Form(None),
    og_image: Optional[str] = Form(None),
    schema_config: Optional[str] = Form(None),
    reading_time: int = Form(5),
    featured_image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_slug = slugify(slug) if slug and slug.strip() else slugify(title)
    if not clean_slug:
        clean_slug = f"article-{int(datetime.now().timestamp())}"

    # Check slug uniqueness
    existing = db.query(BlogPost).filter(BlogPost.slug == clean_slug).first()
    if existing:
        clean_slug = f"{clean_slug}-{int(datetime.now().timestamp())}"

    featured_image_url = None
    if featured_image_file and featured_image_file.filename:
        try:
            rel_url, _ = upload_service.save_upload(featured_image_file, subfolder="blog", is_image=True)
            featured_image_url = rel_url
        except Exception as exc:
            logger.warning(f"Featured image upload failed: {exc}")

    # Parse publish date
    parsed_date = datetime.now(timezone.utc)
    if publish_date:
        try:
            parsed_date = datetime.fromisoformat(publish_date)
        except Exception:
            pass

    post = BlogPost(
        title=title.strip(),
        slug=clean_slug,
        featured_image=featured_image_url,
        author=author.strip(),
        category=category,
        excerpt=excerpt.strip(),
        content=content.strip(),
        tags=tags.strip() if tags else None,
        publish_date=parsed_date,
        status=status_val,
        seo_title=seo_title.strip() if seo_title else title.strip(),
        meta_description=meta_description.strip() if meta_description else excerpt.strip()[:160],
        canonical_url=canonical_url.strip() if canonical_url else None,
        og_image=og_image.strip() if og_image else featured_image_url,
        schema_config=schema_config.strip() if schema_config else None,
        reading_time_minutes=max(1, reading_time),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    logger.info(f"Created blog post #{post.id} '{post.title}' [{post.status}]")

    return RedirectResponse(url="/admin/blog", status_code=status.HTTP_302_FOUND)


@router.get("/{post_id}/edit", response_class=HTMLResponse, summary="Edit Article Form")
async def admin_blog_edit_view(
    post_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")

    return templates.TemplateResponse(
        request=request,
        name="admin/blog/form.html",
        context={
            "request": request,
            "current_user": current_user,
            "post": post,
            "categories": [c.value for c in BlogCategory],
            "statuses": [s.value for s in BlogPostStatus],
            "active_page": "blog",
            "is_edit": True,
        },
    )


@router.post("/{post_id}/edit", response_class=HTMLResponse, summary="Update Article")
async def admin_blog_edit_post(
    post_id: int,
    request: Request,
    title: str = Form(...),
    slug: Optional[str] = Form(None),
    author: str = Form(...),
    category: str = Form(...),
    excerpt: str = Form(...),
    content: str = Form(...),
    tags: Optional[str] = Form(None),
    publish_date: Optional[str] = Form(None),
    status_val: str = Form(...),
    seo_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    canonical_url: Optional[str] = Form(None),
    og_image: Optional[str] = Form(None),
    schema_config: Optional[str] = Form(None),
    reading_time: int = Form(5),
    featured_image_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")

    clean_slug = slugify(slug) if slug and slug.strip() else slugify(title)
    existing = db.query(BlogPost).filter(BlogPost.slug == clean_slug, BlogPost.id != post_id).first()
    if existing:
        clean_slug = f"{clean_slug}-{post_id}"

    if featured_image_file and featured_image_file.filename:
        try:
            rel_url, _ = upload_service.save_upload(featured_image_file, subfolder="blog", is_image=True)
            post.featured_image = rel_url
        except Exception as exc:
            logger.warning(f"Featured image update failed: {exc}")

    if publish_date:
        try:
            post.publish_date = datetime.fromisoformat(publish_date)
        except Exception:
            pass

    post.title = title.strip()
    post.slug = clean_slug
    post.author = author.strip()
    post.category = category
    post.excerpt = excerpt.strip()
    post.content = content.strip()
    post.tags = tags.strip() if tags else None
    post.status = status_val
    post.seo_title = seo_title.strip() if seo_title else title.strip()
    post.meta_description = meta_description.strip() if meta_description else excerpt.strip()[:160]
    post.canonical_url = canonical_url.strip() if canonical_url else None
    if og_image:
        post.og_image = og_image.strip()
    post.schema_config = schema_config.strip() if schema_config else None
    post.reading_time_minutes = max(1, reading_time)

    db.commit()
    logger.info(f"Updated blog post #{post.id} '{post.title}'")

    return RedirectResponse(url="/admin/blog", status_code=status.HTTP_302_FOUND)


@router.post("/{post_id}/delete", summary="Delete Article")
async def admin_blog_delete(
    post_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if post:
        db.delete(post)
        db.commit()
        logger.info(f"Deleted blog post #{post_id}")
    return RedirectResponse(url="/admin/blog", status_code=status.HTTP_302_FOUND)
