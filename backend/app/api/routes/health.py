"""Liveness and dependency readiness HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.core.database import DatabaseManager
from app.core.redis import RedisManager
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services.health import HealthService

router = APIRouter(tags=["Health"])


def get_health_service(request: Request) -> HealthService:
    """Resolve a HealthService wired to application-managed infrastructure managers."""
    settings: Settings = request.app.state.settings
    db_manager: DatabaseManager = request.app.state.db_manager
    redis_manager: RedisManager = request.app.state.redis_manager
    return HealthService(
        settings=settings,
        db_manager=db_manager,
        redis_manager=redis_manager,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service liveness probe",
    description="Verify that the FastAPI process is running and able to respond to HTTP requests.",
)
async def health_check(
    service: HealthService = Depends(get_health_service),  # noqa: B008
) -> HealthResponse:
    """Return service liveness without querying external dependencies."""
    return service.get_liveness()


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "One or more backing dependencies are unavailable.",
        }
    },
    summary="Service readiness probe",
    description="Verify connectivity to PostgreSQL and Redis backing services.",
)
async def readiness_check(
    service: HealthService = Depends(get_health_service),  # noqa: B008
) -> JSONResponse:
    """Verify PostgreSQL and Redis availability and report readiness status."""
    payload, is_ready = await service.get_readiness()
    http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=payload.model_dump(mode="json"))
