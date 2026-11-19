"""Health and readiness orchestration service."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.core.config import Settings
from app.core.database import DatabaseManager
from app.core.redis import RedisManager
from app.schemas.health import DependencyStatus, HealthResponse, ReadinessResponse


class HealthService:
    """Computes application liveness and external dependency readiness."""

    def __init__(
        self,
        settings: Settings,
        db_manager: DatabaseManager,
        redis_manager: RedisManager,
    ) -> None:
        self._settings = settings
        self._db_manager = db_manager
        self._redis_manager = redis_manager

    def get_liveness(self) -> HealthResponse:
        """Return lightweight process liveness metadata."""
        return HealthResponse(
            status="ok",
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.app_env,
            timestamp=datetime.now(UTC),
        )

    async def get_readiness(self) -> tuple[ReadinessResponse, bool]:
        """Concurrently verify PostgreSQL and Redis connectivity."""
        pg_result, redis_result = await asyncio.gather(
            self._db_manager.check_health(),
            self._redis_manager.check_health(),
        )

        pg_ok, pg_latency, pg_detail = pg_result
        redis_ok, redis_latency, redis_detail = redis_result
        all_ready = pg_ok and redis_ok

        response = ReadinessResponse(
            status="ready" if all_ready else "degraded",
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.app_env,
            timestamp=datetime.now(UTC),
            dependencies={
                "postgresql": DependencyStatus(
                    status="up" if pg_ok else "down",
                    latency_ms=pg_latency,
                    detail=pg_detail,
                ),
                "redis": DependencyStatus(
                    status="up" if redis_ok else "down",
                    latency_ms=redis_latency,
                    detail=redis_detail,
                ),
            },
        )
        return response, all_ready
