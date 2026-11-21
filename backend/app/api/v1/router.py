"""Versioned /api/v1 router serving as the extension boundary for domain modules."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.modules.data_integration.router import router as data_integration_router

settings = get_settings()

v1_router = APIRouter(prefix=settings.api_v1_prefix)
v1_router.include_router(data_integration_router, tags=["Data Integration"])
