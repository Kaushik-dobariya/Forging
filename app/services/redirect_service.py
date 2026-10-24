from typing import Optional, List, Tuple, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.models.redirect import URLRedirect
from app.core.logging import logger


class RedirectService:
    """
    Manages permanent (301) and temporary (302) HTTP redirects with
    cycle detection to prevent redirect loops.
    """

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalizes URL paths: ensures leading slash, trims trailing slash, lowercase."""
        if not path:
            return "/"
        clean = path.strip().lower()
        if not clean.startswith("/"):
            clean = f"/{clean}"
        if len(clean) > 1 and clean.endswith("/"):
            clean = clean.rstrip("/")
        return clean

    def check_redirect_loop(
        self,
        db: Session,
        source_path: str,
        target_path: str,
        current_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        Detects whether adding/updating a redirect rule creates a self-loop or cyclical loop.
        Returns: (has_loop: bool, error_message: str)
        """
        src = self.normalize_path(source_path)
        tgt = self.normalize_path(target_path)

        # 1. Immediate self-redirect check
        if src == tgt:
            return True, f"Self-redirect loop detected: Source and target URLs are identical ('{src}')."

        # 2. Build redirect graph from existing active redirects
        query = db.query(URLRedirect).filter(URLRedirect.is_active == True)
        if current_id is not None:
            query = query.filter(URLRedirect.id != current_id)
        existing_rules = query.all()

        graph: Dict[str, str] = {self.normalize_path(r.source_path): self.normalize_path(r.target_path) for r in existing_rules}

        # Add proposed redirect
        graph[src] = tgt

        # Traverse graph starting from target to verify it doesn't lead back to source
        curr = tgt
        visited: Set[str] = {src}
        hops = 0
        max_hops = 20

        while curr in graph and hops < max_hops:
            hops += 1
            if curr == src or curr in visited:
                return True, f"Cyclical redirect loop detected: '{src}' eventually redirects back to '{curr}'."
            visited.add(curr)
            curr = graph[curr]

        return False, ""

    def resolve_redirect(self, db: Session, path: str, max_hops: int = 5) -> Optional[Tuple[str, int]]:
        """
        Resolves a URL through active redirect rules up to max_hops.
        Returns: (terminal_target_path, status_code) or None if no redirect matches.
        """
        clean = self.normalize_path(path)
        first_rule = (
            db.query(URLRedirect)
            .filter(
                URLRedirect.source_path == clean,
                URLRedirect.is_active == True,
            )
            .first()
        )
        if not first_rule:
            return None

        current_target = self.normalize_path(first_rule.target_path)
        status_code = first_rule.status_code or 301
        visited: Set[str] = {clean}
        hops = 1

        while hops < max_hops:
            next_rule = (
                db.query(URLRedirect)
                .filter(
                    URLRedirect.source_path == current_target,
                    URLRedirect.is_active == True,
                )
                .first()
            )
            if not next_rule:
                break

            visited.add(current_target)
            next_target = self.normalize_path(next_rule.target_path)

            if next_target in visited:
                logger.warning(f"Prevented redirect cycle at runtime: '{clean}' -> '{current_target}'")
                break

            current_target = next_target
            status_code = next_rule.status_code or 301
            hops += 1

        return current_target, status_code

    def list_redirects(
        self,
        db: Session,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[URLRedirect], int]:
        query = db.query(URLRedirect)
        if is_active is not None:
            query = query.filter(URLRedirect.is_active == is_active)
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    URLRedirect.source_path.ilike(s),
                    URLRedirect.target_path.ilike(s),
                    URLRedirect.notes.ilike(s),
                )
            )

        total = query.count()
        items = (
            query.order_by(URLRedirect.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def get_redirect_by_id(self, db: Session, redirect_id: int) -> Optional[URLRedirect]:
        return db.query(URLRedirect).filter(URLRedirect.id == redirect_id).first()

    def create_redirect(
        self,
        db: Session,
        source_path: str,
        target_path: str,
        status_code: int = 301,
        notes: Optional[str] = None,
        is_active: bool = True,
    ) -> Tuple[Optional[URLRedirect], Optional[str]]:
        src = self.normalize_path(source_path)
        tgt = self.normalize_path(target_path)

        if status_code not in (301, 302):
            status_code = 301

        # Loop check
        has_loop, msg = self.check_redirect_loop(db, src, tgt)
        if has_loop:
            return None, msg

        # Existing rule with same source check
        existing = db.query(URLRedirect).filter(URLRedirect.source_path == src).first()
        if existing:
            existing.target_path = tgt
            existing.status_code = status_code
            existing.notes = notes
            existing.is_active = is_active
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated existing redirect for {src} -> {tgt} ({status_code})")
            return existing, None

        redirect = URLRedirect(
            source_path=src,
            target_path=tgt,
            status_code=status_code,
            notes=notes,
            is_active=is_active,
        )
        db.add(redirect)
        db.commit()
        db.refresh(redirect)
        logger.info(f"Created new URL redirect: {src} -> {tgt} ({status_code})")
        return redirect, None

    def update_redirect(
        self,
        db: Session,
        redirect_id: int,
        source_path: str,
        target_path: str,
        status_code: int = 301,
        notes: Optional[str] = None,
        is_active: bool = True,
    ) -> Tuple[Optional[URLRedirect], Optional[str]]:
        redirect = self.get_redirect_by_id(db, redirect_id)
        if not redirect:
            return None, "Redirect rule not found."

        src = self.normalize_path(source_path)
        tgt = self.normalize_path(target_path)

        if status_code not in (301, 302):
            status_code = 301

        has_loop, msg = self.check_redirect_loop(db, src, tgt, current_id=redirect_id)
        if has_loop:
            return None, msg

        # Check duplicate source
        conflict = (
            db.query(URLRedirect)
            .filter(URLRedirect.source_path == src, URLRedirect.id != redirect_id)
            .first()
        )
        if conflict:
            return None, f"Another redirect rule already exists for source path '{src}'."

        redirect.source_path = src
        redirect.target_path = tgt
        redirect.status_code = status_code
        redirect.notes = notes
        redirect.is_active = is_active

        db.commit()
        db.refresh(redirect)
        logger.info(f"Updated URL redirect id={redirect_id}: {src} -> {tgt} ({status_code})")
        return redirect, None

    def delete_redirect(self, db: Session, redirect_id: int) -> bool:
        redirect = self.get_redirect_by_id(db, redirect_id)
        if not redirect:
            return False
        db.delete(redirect)
        db.commit()
        logger.info(f"Deleted URL redirect id={redirect_id}")
        return True

    def toggle_redirect(self, db: Session, redirect_id: int) -> Optional[bool]:
        redirect = self.get_redirect_by_id(db, redirect_id)
        if not redirect:
            return None
        redirect.is_active = not redirect.is_active
        db.commit()
        logger.info(f"Toggled URL redirect id={redirect_id} to {redirect.is_active}")
        return redirect.is_active


redirect_service = RedirectService()
