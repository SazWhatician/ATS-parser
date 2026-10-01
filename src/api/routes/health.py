"""Health and diagnostics route."""

from fastapi import APIRouter
from src.core.config import settings

router = APIRouter()


@router.get("/health", tags=["system"])
async def health_check():
    """Returns system status, active engine mode, and service details."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "author": settings.author,
        "engine_mode": settings.active_engine_mode,
        "has_llm_key": settings.has_llm_key,
        "supported_formats": settings.allowed_extensions,
    }
