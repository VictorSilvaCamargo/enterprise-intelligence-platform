"""Pydantic response schemas for liveness and readiness healthcheck endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    """Connectivity report for a single backend infrastructure dependency."""

    status: Literal["up", "down"]
    latency_ms: float = Field(..., ge=0.0, examples=[1.42])
    detail: str = Field(..., examples=["Connected"])


class HealthResponse(BaseModel):
    """Liveness response verifying that the FastAPI process is serving traffic."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str
    timestamp: datetime


class ReadinessResponse(BaseModel):
    """Readiness response reporting status of PostgreSQL and Redis dependencies."""

    status: Literal["ready", "degraded"]
    service: str
    version: str
    environment: str
    timestamp: datetime
    dependencies: dict[str, DependencyStatus]
