"""Shared pytest fixtures for backend startup and healthcheck tests."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@dataclass
class FakeProbeManager:
    """Deterministic stub replacing DatabaseManager / RedisManager in unit tests."""

    healthy: bool = True
    latency_ms: float = 1.25
    detail: str = "Connected"

    async def check_health(self) -> tuple[bool, float, str]:
        return self.healthy, self.latency_ms, self.detail

    async def close(self) -> None:
        return None


@pytest.fixture
def test_settings() -> Settings:
    """Create isolated test settings decoupled from external hosts."""
    return Settings(
        app_name="Enterprise Intelligence Platform",
        app_version="0.1.0",
        app_env="test",
        log_level="WARNING",
        cors_origins=["http://localhost:5173"],
    )


@pytest.fixture
def app_instance(test_settings: Settings) -> FastAPI:
    """Create a FastAPI app configured for test execution."""
    return create_app(test_settings)


@pytest.fixture
def client(app_instance: FastAPI) -> Iterator[TestClient]:
    """Provide a TestClient with fake healthy database and Redis managers."""
    with TestClient(app_instance, raise_server_exceptions=False) as test_client:
        app_instance.state.db_manager = FakeProbeManager(healthy=True, latency_ms=1.1)
        app_instance.state.redis_manager = FakeProbeManager(healthy=True, latency_ms=0.7)
        yield test_client
