from fastapi import APIRouter, Depends
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserResponse
from app.admin.dependencies import get_current_admin


api_v1_router = APIRouter(prefix="/v1", tags=["API v1"])


@api_v1_router.get("/health", summary="API v1 Health Endpoint")
async def api_health():
    """Returns the operational status of the API."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }


@api_v1_router.get("/auth/me", response_model=UserResponse, summary="Get Current Admin Profile")
async def get_my_profile(current_user: User = Depends(get_current_admin)):
    """Returns the profile of the currently authenticated administrator."""
    return current_user
