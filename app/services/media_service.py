import io
import os
import uuid
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from fastapi import UploadFile, HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.logging import logger
from app.models.media import MediaAsset
from app.services.upload_service import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_MIMES,
    DANGEROUS_EXTENSIONS,
    upload_service,
)
from app.services.seo_service import slugify


class MediaService:
    """
    Service for managing the Enterprise Image Media Library, Image SEO metadata,
    and automatic generation of modern responsive image formats (WebP) & thumbnails.
    """

    def __init__(self, upload_dir: Optional[Path] = None):
        self.upload_dir = upload_dir or (settings.resolved_upload_dir / "media")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def list_media(
        self,
        db: Session,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 24,
    ) -> Tuple[List[MediaAsset], int]:
        query = db.query(MediaAsset)
        if category and category != "all":
            query = query.filter(MediaAsset.category == category)
        if search:
            s = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    MediaAsset.seo_filename.ilike(s),
                    MediaAsset.alt_text.ilike(s),
                    MediaAsset.title.ilike(s),
                    MediaAsset.caption.ilike(s),
                    MediaAsset.description.ilike(s),
                )
            )

        total = query.count()
        items = (
            query.order_by(MediaAsset.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def get_media_by_id(self, db: Session, media_id: int) -> Optional[MediaAsset]:
        return db.query(MediaAsset).filter(MediaAsset.id == media_id).first()

    def process_and_save_image(
        self,
        db: Session,
        upload_file: UploadFile,
        seo_filename: Optional[str] = None,
        alt_text: Optional[str] = None,
        title: Optional[str] = None,
        caption: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "general",
    ) -> MediaAsset:
        """
        Validates, generates modern WebP and thumbnail variants, and records MediaAsset with SEO metadata.
        """
        content = upload_file.file.read()
        upload_service.validate_file_size(len(content))
        upload_service.validate_image_file(upload_file, content)

        original_filename = upload_file.filename or "image.jpg"
        ext = Path(original_filename).suffix.lower()

        # Generate SEO-friendly slug for the filename
        base_slug = slugify(seo_filename) if seo_filename else slugify(Path(original_filename).stem)
        if not base_slug:
            base_slug = "forged-component"

        unique_suffix = uuid.uuid4().hex[:8]
        stored_main_name = f"{base_slug}_{unique_suffix}{ext}"
        stored_webp_name = f"{base_slug}_{unique_suffix}.webp"
        stored_thumb_name = f"thumb_{base_slug}_{unique_suffix}.webp"

        main_path = self.upload_dir / stored_main_name
        webp_path = self.upload_dir / stored_webp_name
        thumb_path = self.upload_dir / stored_thumb_name

        # Save main file
        with open(main_path, "wb") as f:
            f.write(content)

        width, height = None, None
        has_webp = False
        has_thumb = False

        if ext != ".svg":
            try:
                # Open with Pillow to get dimensions and convert to WebP
                img = Image.open(io.BytesIO(content))
                width, height = img.size

                # Convert to RGB if needed (e.g. RGBA for PNG preserves transparency, WebP supports RGBA)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.mode else "RGB")

                # Generate optimized WebP
                img.save(webp_path, "WEBP", quality=85, optimize=True)
                has_webp = True

                # Generate responsive thumbnail (max 300x300)
                thumb = img.copy()
                thumb.thumbnail((300, 300), Image.Resampling.LANCZOS)
                thumb.save(thumb_path, "WEBP", quality=80)
                has_thumb = True

            except Exception as exc:
                logger.warning(f"Could not generate modern WebP/thumbnail for {original_filename}: {exc}")

        media = MediaAsset(
            filename=stored_main_name,
            seo_filename=base_slug,
            original_name=original_filename,
            file_path=f"/uploads/media/{stored_main_name}",
            webp_path=f"/uploads/media/{stored_webp_name}" if has_webp else None,
            thumbnail_path=f"/uploads/media/{stored_thumb_name}" if has_thumb else None,
            mime_type=upload_file.content_type or "image/jpeg",
            file_size=len(content),
            width=width,
            height=height,
            alt_text=alt_text or base_slug.replace("-", " ").title(),
            title=title or base_slug.replace("-", " ").title(),
            caption=caption,
            description=description,
            category=category or "general",
        )

        db.add(media)
        db.commit()
        db.refresh(media)
        logger.info(f"Saved media asset id={media.id} seo_filename='{media.seo_filename}' with WebP={has_webp}")
        return media

    def update_metadata(
        self,
        db: Session,
        media_id: int,
        seo_filename: Optional[str] = None,
        alt_text: Optional[str] = None,
        title: Optional[str] = None,
        caption: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Optional[MediaAsset]:
        media = self.get_media_by_id(db, media_id)
        if not media:
            return None

        if seo_filename:
            media.seo_filename = slugify(seo_filename)
        if alt_text is not None:
            media.alt_text = alt_text.strip()
        if title is not None:
            media.title = title.strip()
        if caption is not None:
            media.caption = caption.strip()
        if description is not None:
            media.description = description.strip()
        if category:
            media.category = category.strip()

        db.commit()
        db.refresh(media)
        logger.info(f"Updated metadata for media asset id={media.id}")
        return media

    def delete_media(self, db: Session, media_id: int) -> bool:
        media = self.get_media_by_id(db, media_id)
        if not media:
            return False

        # Attempt removing files from disk
        for p in [media.file_path, media.webp_path, media.thumbnail_path]:
            if p and p.startswith("/uploads/media/"):
                fname = p.replace("/uploads/media/", "")
                fpath = self.upload_dir / fname
                if fpath.exists():
                    try:
                        fpath.unlink()
                    except Exception as exc:
                        logger.warning(f"Failed to remove media file {fpath}: {exc}")

        db.delete(media)
        db.commit()
        logger.info(f"Deleted media asset id={media_id}")
        return True


media_service = MediaService()
