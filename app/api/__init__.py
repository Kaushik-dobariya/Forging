from fastapi import APIRouter
from app.api.v1.routes import api_v1_router

api_router = APIRouter(prefix="/api")
api_router.include_router(api_v1_router)

__all__ = ["api_router"]
