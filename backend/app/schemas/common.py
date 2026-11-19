"""Shared Pydantic schemas used across error handling and base API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized, sanitized API error envelope."""

    error_code: str = Field(..., examples=["SERVICE_UNAVAILABLE"])
    message: str = Field(..., examples=["Dependent service unavailable."])
    request_id: str = Field(..., examples=["b1e23c9d-7f2a-4c62-95c1-443a98b18a0f"])
    timestamp: datetime
    details: dict[str, Any] | None = None
