"""Versioned /api/v1 router serving as the extension boundary for domain modules."""

from fastapi import APIRouter

from app.core.config import get_settings

settings = get_settings()

# Stage 1 intentionally leaves /api/v1 empty. Future modules (Data Integration,
# AI Knowledge Hub, AI Agents, Business Intelligence, Workflow Automation)
# mount their routers here via app.modules.register_module_router().
v1_router = APIRouter(prefix=settings.api_v1_prefix)
