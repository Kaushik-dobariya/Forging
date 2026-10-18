import os
import re
import uuid
from pathlib import Path
from typing import Tuple, List, Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image
from app.core.config import settings
from app.core.logging import logger


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/svg+xml",
}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf"}
ALLOWED_DOCUMENT_MIMES = {"application/pdf"}

# Engineering drawings & CAD models allowed for Request-a-Quote
ALLOWED_DRAWING_EXTENSIONS = {
    ".pdf",
    ".dwg",
    ".dxf",
    ".step",
    ".stp",
    ".iges",
    ".igs",
    ".png",
    ".jpg",
    ".jpeg",
    ".zip",
}

# Downloadable technical library resources
ALLOWED_RESOURCE_EXTENSIONS = {
    ".pdf",
    ".dwg",
    ".dxf",
    ".step",
    ".stp",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
}

DANGEROUS_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".php",
    ".py",
    ".js",
    ".vbs",
    ".dll",
    ".msi",
    ".html",
    ".htm",
    ".phtml",
    ".cgi",
    ".pl",
}


def sanitize_filename(filename: str) -> str:
    """Strips unsafe path traversal characters and normalizes file basename."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^\w\.-]", "_", base)
    return clean[:100]


class UploadService:
    """Service handling validation, sanitization, and persistence of uploaded files."""

    def __init__(self, upload_dir: Optional[Path] = None):
        self.upload_dir = upload_dir or settings.resolved_upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_file_size(self, file_size: int) -> None:
        """Enforces configured max upload size limit."""
        if file_size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_mb:.1f}MB.",
            )

    def validate_image_file(self, upload_file: UploadFile, content: bytes) -> None:
        """Validates MIME type, file extension, and image payload integrity using Pillow."""
        ext = Path(upload_file.filename or "").suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}",
            )

        mime = upload_file.content_type
        if mime and mime.lower() not in ALLOWED_IMAGE_MIMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported MIME type '{mime}'.",
            )

        # For raster images, verify payload integrity via Pillow
        if ext != ".svg":
            try:
                import io
                image = Image.open(io.BytesIO(content))
                image.verify()
            except Exception as exc:
                logger.warning(f"Corrupt or invalid image upload: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or corrupt image content.",
                )

    def validate_document_file(self, upload_file: UploadFile, content: bytes) -> None:
        """Validates MIME type, file extension, and PDF header signature."""
        ext = Path(upload_file.filename or "").suffix.lower()
        if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported document extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}",
            )

        mime = upload_file.content_type
        if mime and mime.lower() not in ALLOWED_DOCUMENT_MIMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported document MIME type '{mime}'.",
            )

        # Validate PDF magic bytes (%PDF-)
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupt PDF file signature.",
            )

    def validate_drawing_file(
        self,
        file_or_name: Any,
        content_or_size: Any = b"",
        content_type: Optional[str] = None,
    ) -> Any:
        """
        Validates engineering drawing/CAD upload for Request-a-Quote.
        Supports both:
        - (upload_file: UploadFile, content: bytes) -> raises HTTPException on error
        - (filename: str, file_size: int, content_type: str) -> returns (is_valid: bool, message: str)
        """
        if isinstance(file_or_name, str):
            filename = file_or_name
            file_size = content_or_size if isinstance(content_or_size, int) else 0
            ext = Path(filename or "").suffix.lower()

            if ext in DANGEROUS_EXTENSIONS:
                return False, f"File type {ext} is strictly prohibited for security reasons."

            if ext not in ALLOWED_DRAWING_EXTENSIONS:
                return False, f"Unsupported drawing format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_DRAWING_EXTENSIONS))}"

            if file_size > settings.MAX_UPLOAD_SIZE:
                return False, f"File size {file_size} exceeds maximum limit."

            return True, "Valid CAD/drawing file."

        # Otherwise treated as (UploadFile, bytes)
        upload_file: UploadFile = file_or_name
        content: bytes = content_or_size if isinstance(content_or_size, bytes) else b""
        ext = Path(upload_file.filename or "").suffix.lower()

        if ext in DANGEROUS_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {ext} is strictly prohibited for security reasons.",
            )

        if ext not in ALLOWED_DRAWING_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported drawing format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_DRAWING_EXTENSIONS))}",
            )

        # If PDF, verify header signature
        if ext == ".pdf" and not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupt PDF drawing file.",
            )

        # If raster image, verify via Pillow
        if ext in {".png", ".jpg", ".jpeg"}:
            try:
                import io
                image = Image.open(io.BytesIO(content))
                image.verify()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or corrupt image file.",
                )


    def validate_resource_file(self, upload_file: UploadFile, content: bytes) -> None:
        """Validates download resource file for technical library."""
        ext = Path(upload_file.filename or "").suffix.lower()
        if ext in DANGEROUS_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Forbidden file extension '{ext}'.",
            )

        if ext not in ALLOWED_RESOURCE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported resource format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_RESOURCE_EXTENSIONS))}",
            )

    def save_upload(
        self,
        upload_file: UploadFile,
        subfolder: str = "general",
        is_image: bool = True,
        is_drawing: bool = False,
        is_resource: bool = False,
    ) -> Tuple[str, str]:
        """
        Saves uploaded file securely under uploads/{subfolder}/.
        Returns a tuple: (relative_url, absolute_disk_path).
        """
        content = upload_file.file.read()
        self.validate_file_size(len(content))

        if is_drawing:
            self.validate_drawing_file(upload_file, content)
        elif is_resource:
            self.validate_resource_file(upload_file, content)
        elif is_image:
            self.validate_image_file(upload_file, content)
        else:
            self.validate_document_file(upload_file, content)

        clean_name = sanitize_filename(upload_file.filename or "upload.bin")
        ext = Path(clean_name).suffix
        stem = Path(clean_name).stem
        unique_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"

        target_dir = self.upload_dir / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / unique_name

        with open(file_path, "wb") as f:
            f.write(content)

        relative_url = f"/uploads/{subfolder}/{unique_name}"
        logger.info(f"File uploaded securely: {relative_url}")
        return relative_url, str(file_path)


upload_service = UploadService()
