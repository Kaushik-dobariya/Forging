import os
import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly as python app/main.py
_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

import time
from contextlib import asynccontextmanager
from typing import Callable
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings, BASE_DIR
from app.core.database import SessionLocal, check_db_connection
from app.core.logging import setup_logging, logger
from app.core.templates import templates
from app.services.auth_service import auth_service
from app.web.routes import router as web_router
from app.admin.routes import router as admin_router
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager handling startup and shutdown events."""
    # 1. Initialize structured logging
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in '{settings.APP_ENV}' mode...")

    # 2. Ensure upload directories exist
    upload_dir = settings.resolved_upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / "general").mkdir(parents=True, exist_ok=True)
    (upload_dir / "media").mkdir(parents=True, exist_ok=True)
    (upload_dir / "drawings").mkdir(parents=True, exist_ok=True)
    (upload_dir / "documents").mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directories initialized: {upload_dir}")

    # 3. Verify database connectivity & bootstrap initial super admin, schema & seed data
    if check_db_connection():
        logger.info("Database connectivity established successfully.")
        from app.core.database import Base, engine
        import app.models  # Ensure all model tables are registered
        Base.metadata.create_all(bind=engine)

        db = SessionLocal()
        try:
            from sqlalchemy import text
            from app.services.seo_service import slugify
            from app.models.infrastructure import Equipment
            from app.models.quality import Certification

            # SQLite dynamic schema upgrades for Phase 6 columns
            if settings.is_sqlite:
                for tbl, new_cols in [
                    ("users", [("avatar_url", "VARCHAR(500)")]),
                    ("equipment", [("slug", "VARCHAR(220)"), ("meta_title", "VARCHAR(255)"), ("meta_description", "VARCHAR(500)")]),
                    ("certifications", [("slug", "VARCHAR(220)"), ("meta_title", "VARCHAR(255)"), ("meta_description", "VARCHAR(500)")]),
                    ("url_redirects", [("notes", "VARCHAR(255)"), ("is_active", "BOOLEAN DEFAULT 1")]),
                ]:
                    try:
                        table_check = db.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")).scalar()
                        if table_check:
                            existing_cols = [r[1] for r in db.execute(text(f"PRAGMA table_info({tbl})")).fetchall()]
                            for col_name, col_type in new_cols:
                                if col_name not in existing_cols:
                                    db.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col_name} {col_type}"))
                                    db.commit()
                    except Exception as mig_err:
                        db.rollback()
                        logger.warning(f"Schema check for {tbl} skipped: {mig_err}")

            # Backfill equipment slugs if missing
            try:
                eqs = db.query(Equipment).filter((Equipment.slug.is_(None)) | (Equipment.slug == "")).all()
                for eq in eqs:
                    eq.slug = slugify(eq.name)
                # Backfill certification slugs if missing
                certs = db.query(Certification).filter((Certification.slug.is_(None)) | (Certification.slug == "")).all()
                for c in certs:
                    c.slug = slugify(c.certificate_name)
                db.commit()
            except Exception as slug_err:
                db.rollback()
                logger.warning(f"Slug backfill skipped: {slug_err}")

            auth_service.bootstrap_superadmin(db)
            from app.services.seed_service import seed_cms_data
            seed_cms_data(db)
        finally:
            db.close()

    else:
        logger.error("WARNING: Initial database connectivity check failed! Check DATABASE_URL.")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """Application factory for the Forging CMS platform."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Modular Industrial Forging CMS, Corporate Web Platform & Precision Engineering Catalog",
        version="1.0.0",
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url="/redoc" if settings.APP_DEBUG else None,
        lifespan=lifespan,
    )

    # --------------------------------------------------------------------------
    # MIDDLEWARE 1: URL Normalization & Dynamic 301/302 Redirect Interceptor
    # --------------------------------------------------------------------------
    @app.middleware("http")
    async def url_normalization_and_redirect_middleware(request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method

        # Skip static assets, uploads, and admin/system APIs from normalization
        bypass_prefixes = ("/static", "/uploads", "/admin", "/api", "/docs", "/redoc", "/health", "/favicon.ico")
        is_bypass = any(path.startswith(prefix) for prefix in bypass_prefixes)

        if not is_bypass and method in ("GET", "HEAD"):
            # 1. Check dynamic redirects from RedirectService / URLRedirect table
            db = SessionLocal()
            try:
                from app.services.redirect_service import redirect_service
                redirect_res = redirect_service.resolve_redirect(db, path)
                if redirect_res:
                    target_url, status_code = redirect_res
                    if request.url.query:
                        target_url = f"{target_url}?{request.url.query}"
                    return RedirectResponse(url=target_url, status_code=status_code)
            except Exception as red_err:
                logger.warning(f"Redirect resolution check failed: {red_err}")
            finally:
                db.close()

            # 2. Lowercase URL enforcement
            if any(c.isupper() for c in path):
                lower_path = path.lower()
                query_suffix = f"?{request.url.query}" if request.url.query else ""
                return RedirectResponse(
                    url=f"{lower_path}{query_suffix}",
                    status_code=status.HTTP_301_MOVED_PERMANENTLY,
                )

            # 3. Trailing slash normalization (strip trailing slash if length > 1)
            if len(path) > 1 and path.endswith("/"):
                clean_path = path.rstrip("/")
                query_suffix = f"?{request.url.query}" if request.url.query else ""
                return RedirectResponse(
                    url=f"{clean_path}{query_suffix}",
                    status_code=status.HTTP_301_MOVED_PERMANENTLY,
                )

        return await call_next(request)

    # --------------------------------------------------------------------------
    # MIDDLEWARE 2: Enterprise Security Headers, CSP & Telemetry
    # --------------------------------------------------------------------------
    @app.middleware("http")
    async def security_and_logging_middleware(request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        # Enforce industrial HTTP security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content-Security-Policy configured for industrial web app without breaking assets
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net",
            "img-src 'self' data: blob: https:",
            "connect-src 'self'",
            "frame-ancestors 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # HSTS in production or HTTPS
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Static asset caching headers
        if request.url.path.startswith("/static") or request.url.path.startswith("/uploads"):
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"

        duration_ms = (time.perf_counter() - start_time) * 1000
        if not request.url.path.startswith("/static"):
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)"
            )

        return response

    # --------------------------------------------------------------------------
    # EXCEPTION HANDLERS: Consistent 404, 403, 422, 500
    # --------------------------------------------------------------------------
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        accept_header = request.headers.get("accept", "")
        is_html = "text/html" in accept_header
        path = request.url.path

        if is_html:
            is_admin_area = path.startswith("/admin")
            if exc.status_code == 404:
                template_name = "admin/errors/404.html" if is_admin_area else "public/errors/404.html"
                return templates.TemplateResponse(
                    request=request,
                    name=template_name,
                    context={"request": request},
                    status_code=404,
                )
            elif exc.status_code == 403:
                template_name = "admin/errors/403.html" if is_admin_area else "public/errors/403.html"
                return templates.TemplateResponse(
                    request=request,
                    name=template_name,
                    context={"request": request},
                    status_code=403,
                )
            elif exc.status_code >= 500:
                template_name = "admin/errors/500.html" if is_admin_area else "public/errors/500.html"
                return templates.TemplateResponse(
                    request=request,
                    name=template_name,
                    context={"request": request},
                    status_code=exc.status_code,
                )

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=dict(exc.headers or {}),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            return HTMLResponse(
                content="<h2 style='font-family:sans-serif;'>422 Unprocessable Submission</h2><p>Form submission validation failed.</p>",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception during {request.method} {request.url.path}: {exc}")
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            template_name = "admin/errors/500.html" if request.url.path.startswith("/admin") else "public/errors/500.html"
            return templates.TemplateResponse(
                request=request,
                name=template_name,
                context={"request": request},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    # --------------------------------------------------------------------------
    # STATIC FILES & MEDIA UPLOADS
    # --------------------------------------------------------------------------
    static_dir = BASE_DIR / "app" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    uploads_dir = settings.resolved_upload_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    # --------------------------------------------------------------------------
    # HEALTH CHECK ROUTE
    # --------------------------------------------------------------------------
    @app.get("/health", tags=["Health"], summary="System Health Check")
    async def health_check():
        """Returns standard health status for load balancers and uptime monitoring."""
        db_healthy = check_db_connection()
        return {
            "status": "ok" if db_healthy else "degraded",
            "database": "connected" if db_healthy else "disconnected",
            "app": settings.APP_NAME,
            "environment": settings.APP_ENV,
        }

    # --------------------------------------------------------------------------
    # MOUNT ROUTERS
    # --------------------------------------------------------------------------
    app.include_router(api_router)
    app.include_router(admin_router)
    app.include_router(web_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  FORGING CMS & PRECISION ENGINEERING PLATFORM")
    print("=" * 60)
    print("  Public Website:  http://127.0.0.1:8000  (or http://localhost:8000)")
    print("  Admin Portal:    http://127.0.0.1:8000/admin")
    print("  Admin Login:     http://127.0.0.1:8000/admin/login")
    print("  Default Admin:   admin@forgingcms.com / Admin@123456")
    print("=" * 60 + "\n", flush=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

