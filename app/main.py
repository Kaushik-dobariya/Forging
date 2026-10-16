import os
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

import time
from contextlib import asynccontextmanager
from typing import Callable
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, Response
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
    logger.info(f"Upload directory initialized: {upload_dir}")

    # 3. Verify database connectivity & bootstrap initial super admin and seed data
    if check_db_connection():
        logger.info("Database connectivity established successfully.")
        db = SessionLocal()
        try:
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
    # MIDDLEWARE: Security Headers & Request Telemetry
    # --------------------------------------------------------------------------
    @app.middleware("http")
    async def security_and_logging_middleware(request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        response = await call_next(request)

        # Enforce industrial security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        duration_ms = (time.perf_counter() - start_time) * 1000
        # Don't flood logs with static asset queries in production
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
    app.include_router(web_router)
    app.include_router(admin_router)
    app.include_router(api_router)

    return app


app = create_app()
