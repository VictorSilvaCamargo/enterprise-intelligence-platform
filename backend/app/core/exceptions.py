"""Domain-neutral exception hierarchy and global FastAPI exception handlers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error mapped deterministically to HTTP JSON responses."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "APPLICATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


class ServiceUnavailableError(AppError):
    """Raised when a required external dependency is unreachable."""

    def __init__(self, message: str = "Dependent service unavailable.") -> None:
        super().__init__(
            message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
        )


class ConfigurationError(AppError):
    """Raised when runtime configuration is missing or invalid."""

    def __init__(self, message: str = "Invalid application configuration.") -> None:
        super().__init__(
            message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CONFIGURATION_ERROR",
        )


def _resolve_request_id(request: Request) -> str:
    state_request_id = getattr(request.state, "request_id", None)
    if isinstance(state_request_id, str) and state_request_id:
        return state_request_id
    return request_id_ctx.get()


def _build_error_response(
    *,
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    req_id = _resolve_request_id(request)
    payload = ErrorResponse(
        error_code=error_code,
        message=message,
        request_id=req_id,
        timestamp=datetime.now(UTC),
        details=details,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers={"X-Request-ID": req_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach sanitized global exception handlers to the FastAPI instance."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("Application error [%s]: %s", exc.error_code, exc.message)
        return _build_error_response(
            request=request,
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("Request validation failed with %d error(s)", len(exc.errors()))
        sanitized_errors = [
            {
                "loc": list(err.get("loc", ())),
                "msg": str(err.get("msg", "Invalid input")),
                "type": str(err.get("type", "value_error")),
            }
            for err in exc.errors()
        ]
        return _build_error_response(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="VALIDATION_ERROR",
            message="Request validation failed.",
            details={"errors": sanitized_errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _build_error_response(
            request=request,
            status_code=exc.status_code,
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, _exc: Exception) -> JSONResponse:
        # Log full traceback internally while shielding external callers from internals.
        req_id = _resolve_request_id(request)
        token = request_id_ctx.set(req_id)
        try:
            logger.exception("Unhandled server exception")
        finally:
            request_id_ctx.reset(token)
        return _build_error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal error occurred.",
        )
