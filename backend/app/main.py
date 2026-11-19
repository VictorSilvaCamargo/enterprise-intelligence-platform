"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, request_id_ctx
from app.core.redis import RedisManager

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "Starting %s v%s (env=%s, pg=%s, redis=%s)",
            resolved_settings.app_name,
            resolved_settings.app_version,
            resolved_settings.app_env,
            resolved_settings.safe_database_target,
            resolved_settings.safe_redis_target,
        )
        db_manager = DatabaseManager(
            resolved_settings.database_url,
            pool_size=resolved_settings.db_pool_size,
            max_overflow=resolved_settings.db_max_overflow,
            connect_timeout=resolved_settings.db_connect_timeout,
            echo=resolved_settings.debug,
        )
        redis_manager = RedisManager(
            host=resolved_settings.redis_host,
            port=resolved_settings.redis_port,
            db=resolved_settings.redis_db,
            password=resolved_settings.redis_password,
            redis_url=resolved_settings.redis_url_override,
            socket_timeout=resolved_settings.redis_socket_timeout,
        )
        application.state.settings = resolved_settings
        application.state.db_manager = db_manager
        application.state.redis_manager = redis_manager

        try:
            yield
        finally:
            await redis_manager.close()
            await db_manager.close()
            logger.info("Shutdown complete for %s", resolved_settings.app_name)

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "Modular enterprise platform foundation providing centralized configuration, "
            "health/readiness probes, PostgreSQL and Redis connectivity, and extension "
            "boundaries for future intelligence and automation modules."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def attach_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        req_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = req_id
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)

    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
