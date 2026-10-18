import re
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from app.models.page import CMSPage, PageStatus
from app.models.redirect import URLRedirect
from app.models.menu import MenuItem
from app.core.logging import logger


class PageService:
    """Service layer for CMS dynamic pages, SEO configuration, and URL redirects."""

    @staticmethod
    def slugify(text: str) -> str:
        """Converts arbitrary text into a URL-friendly slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        return text.strip("-")

    def normalize_slug(self, slug: str, parent: Optional[CMSPage] = None) -> str:
        """
        Normalizes a slug: removes leading/trailing slashes, cleans invalid chars,
        and ensures proper hierarchical nesting if parent is set and slug is relative.
        """
        raw_slug = slug.strip("/").strip()
        if not raw_slug:
            return ""
        
        # Clean path segments
        segments = [self.slugify(s) for s in raw_slug.split("/") if s.strip()]
        cleaned = "/".join(segments)

        # If parent exists and cleaned does not already start with parent's slug
        if parent:
            parent_clean = parent.slug.strip("/")
            if not cleaned.startswith(parent_clean):
                cleaned = f"{parent_clean}/{cleaned}"

        return cleaned

    def get_page_by_id(self, db: Session, page_id: int) -> Optional[CMSPage]:
        return db.query(CMSPage).filter(CMSPage.id == page_id).first()

    def get_page_by_slug(self, db: Session, slug: str, include_draft: bool = False) -> Optional[CMSPage]:
        clean_slug = slug.strip("/")
        query = db.query(CMSPage).filter(
            or_(
                CMSPage.slug == clean_slug,
                CMSPage.slug == f"/{clean_slug}",
            )
        )
        if not include_draft:
            query = query.filter(CMSPage.status == PageStatus.PUBLISHED.value)
        return query.first()

    def is_slug_unique(self, db: Session, slug: str, exclude_id: Optional[int] = None) -> bool:
        clean_slug = slug.strip("/")
        query = db.query(CMSPage).filter(
            or_(
                CMSPage.slug == clean_slug,
                CMSPage.slug == f"/{clean_slug}",
            )
        )
        if exclude_id:
            query = query.filter(CMSPage.id != exclude_id)
        return query.first() is None

    def list_pages(
        self,
        db: Session,
        status: Optional[str] = None,
        search: Optional[str] = None,
        parent_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "display_order",
        sort_order: str = "asc",
    ) -> Tuple[List[CMSPage], int]:
        query = db.query(CMSPage)

        if status:
            query = query.filter(CMSPage.status == status)

        if parent_id is not None:
            if parent_id == 0:
                query = query.filter(CMSPage.parent_id.is_(None))
            else:
                query = query.filter(CMSPage.parent_id == parent_id)

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    CMSPage.title.ilike(s),
                    CMSPage.slug.ilike(s),
                    CMSPage.content.ilike(s),
                    CMSPage.menu_display_name.ilike(s),
                )
            )

        total = query.count()

        # Sorting
        order_col = getattr(CMSPage, sort_by, CMSPage.display_order)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(order_col), desc(CMSPage.id))
        else:
            query = query.order_by(asc(order_col), asc(CMSPage.id))

        offset = max(0, (page - 1) * per_page)
        pages = query.offset(offset).limit(per_page).all()
        return pages, total

    def create_page(self, db: Session, data: Dict[str, Any]) -> CMSPage:
        title = data.get("title", "").strip()
        if not title:
            raise ValueError("Page Title is required.")

        parent_id = data.get("parent_id")
        parent = self.get_page_by_id(db, parent_id) if parent_id else None

        raw_slug = data.get("slug", "").strip()
        if not raw_slug:
            raw_slug = self.slugify(title)

        slug = self.normalize_slug(raw_slug, parent=parent)
        if not slug:
            slug = self.slugify(title)

        if not self.is_slug_unique(db, slug):
            raise ValueError(f"The URL slug '{slug}' is already in use by another page.")

        page = CMSPage(
            title=title,
            slug=slug,
            content=data.get("content", ""),
            featured_image=data.get("featured_image"),
            parent_id=parent_id if parent else None,
            menu_display_name=data.get("menu_display_name") or title,
            menu_visibility=bool(data.get("menu_visibility", True)),
            footer_visibility=bool(data.get("footer_visibility", False)),
            display_order=int(data.get("display_order", 0)),
            status=data.get("status", PageStatus.PUBLISHED.value),
            meta_title=data.get("meta_title"),
            meta_description=data.get("meta_description"),
            meta_keywords=data.get("meta_keywords"),
            canonical_url=data.get("canonical_url"),
            og_title=data.get("og_title"),
            og_description=data.get("og_description"),
            og_image=data.get("og_image"),
        )
        db.add(page)
        db.commit()
        db.refresh(page)
        logger.info(f"Created CMSPage id={page.id} slug='{page.slug}'")
        return page

    def update_page(
        self,
        db: Session,
        page_id: int,
        data: Dict[str, Any],
        create_redirect_on_slug_change: bool = True,
    ) -> CMSPage:
        page = self.get_page_by_id(db, page_id)
        if not page:
            raise ValueError("Page not found.")

        old_slug = page.slug
        old_status = page.status

        parent_id = data.get("parent_id")
        parent = self.get_page_by_id(db, parent_id) if parent_id else None

        # Prevent circular parent references
        if parent_id and parent_id == page_id:
            raise ValueError("A page cannot be its own parent.")

        raw_slug = data.get("slug", "").strip()
        if not raw_slug:
            raw_slug = self.slugify(data.get("title", page.title))

        new_slug = self.normalize_slug(raw_slug, parent=parent)
        if not new_slug:
            new_slug = old_slug

        if not self.is_slug_unique(db, new_slug, exclude_id=page_id):
            raise ValueError(f"The URL slug '{new_slug}' is already in use by another page.")

        # Check for slug change on a previously published page
        if (
            create_redirect_on_slug_change
            and old_status == PageStatus.PUBLISHED.value
            and old_slug != new_slug
        ):
            self.create_redirect(
                db,
                source_path=f"/{old_slug.strip('/')}",
                target_path=f"/{new_slug.strip('/')}",
                status_code=301,
            )

        page.title = data.get("title", page.title).strip()
        page.slug = new_slug
        page.content = data.get("content", page.content)
        if "featured_image" in data:
            page.featured_image = data.get("featured_image")
        page.parent_id = parent_id if parent else None
        page.menu_display_name = data.get("menu_display_name", page.menu_display_name)
        if "menu_visibility" in data:
            page.menu_visibility = bool(data["menu_visibility"])
        if "footer_visibility" in data:
            page.footer_visibility = bool(data["footer_visibility"])
        if "display_order" in data:
            page.display_order = int(data["display_order"])
        if "status" in data:
            page.status = data["status"]
        if "meta_title" in data:
            page.meta_title = data["meta_title"]
        if "meta_description" in data:
            page.meta_description = data["meta_description"]
        if "meta_keywords" in data:
            page.meta_keywords = data["meta_keywords"]
        if "canonical_url" in data:
            page.canonical_url = data["canonical_url"]
        if "og_title" in data:
            page.og_title = data["og_title"]
        if "og_description" in data:
            page.og_description = data["og_description"]
        if "og_image" in data:
            page.og_image = data["og_image"]

        db.commit()
        db.refresh(page)
        logger.info(f"Updated CMSPage id={page.id} slug='{page.slug}'")
        return page

    def delete_page(self, db: Session, page_id: int) -> Tuple[bool, str]:
        page = self.get_page_by_id(db, page_id)
        if not page:
            return False, "Page not found."

        # Check for child pages
        children_count = db.query(CMSPage).filter(CMSPage.parent_id == page_id).count()
        if children_count > 0:
            return (
                False,
                f"Cannot delete page '{page.title}' because it has {children_count} dependent sub-page(s). Please reassign or delete them first.",
            )

        # Nullify any linked menu items
        db.query(MenuItem).filter(MenuItem.page_id == page_id).update({"page_id": None})

        db.delete(page)
        db.commit()
        logger.info(f"Deleted CMSPage id={page_id}")
        return True, "Page deleted successfully."

    def get_all_published_pages(self, db: Session) -> List[CMSPage]:
        """Returns all published CMS pages for sitemap and navigation."""
        return (
            db.query(CMSPage)
            .filter(CMSPage.status == PageStatus.PUBLISHED.value)
            .order_by(CMSPage.display_order.asc(), CMSPage.title.asc())
            .all()
        )

    def create_redirect(
        self, db: Session, source_path: str, target_path: str, status_code: int = 301
    ) -> URLRedirect:
        source_clean = f"/{source_path.strip('/')}"
        target_clean = f"/{target_path.strip('/')}"
        
        # Don't redirect to self
        if source_clean == target_clean:
            return None

        existing = (
            db.query(URLRedirect).filter(URLRedirect.source_path == source_clean).first()
        )
        if existing:
            existing.target_path = target_clean
            existing.status_code = status_code
            redirect = existing
        else:
            redirect = URLRedirect(
                source_path=source_clean,
                target_path=target_clean,
                status_code=status_code,
            )
            db.add(redirect)
        db.commit()
        db.refresh(redirect)
        logger.info(f"Recorded URL redirect: {source_clean} -> {target_clean} ({status_code})")
        return redirect

    def resolve_redirect(self, db: Session, path: str) -> Optional[URLRedirect]:
        clean = f"/{path.strip('/')}"
        return (
            db.query(URLRedirect)
            .filter(
                or_(
                    URLRedirect.source_path == clean,
                    URLRedirect.source_path == path.strip("/"),
                )
            )
            .first()
        )


page_service = PageService()
