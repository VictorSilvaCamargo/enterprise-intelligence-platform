"""Tests for liveness (/health) and readiness (/health/ready) endpoints."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import FakeProbeManager


def test_liveness_health_endpoint(client: TestClient) -> None:
    """GET /health should return 200 OK with service metadata and request ID header."""
    response = client.get("/health", headers={"X-Request-ID": "trace-health-001"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "trace-health-001"

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "Enterprise Intelligence Platform"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] == "test"
    assert "timestamp" in payload


def test_readiness_endpoint_returns_200_when_dependencies_up(client: TestClient) -> None:
    """GET /health/ready should return 200 ready when PostgreSQL and Redis are up."""
    response = client.get("/health/ready")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["dependencies"]["postgresql"]["status"] == "up"
    assert payload["dependencies"]["postgresql"]["detail"] == "Connected"
    assert payload["dependencies"]["redis"]["status"] == "up"
    assert payload["dependencies"]["redis"]["detail"] == "Connected"


def test_readiness_endpoint_returns_503_when_postgres_down(
    app_instance: FastAPI,
    client: TestClient,
) -> None:
    """GET /health/ready should return 503 degraded when PostgreSQL is unavailable."""
    app_instance.state.db_manager = FakeProbeManager(
        healthy=False,
        latency_ms=3001.0,
        detail="Connection failed (TimeoutError)",
    )
    response = client.get("/health/ready")
    assert response.status_code == 503

    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["postgresql"]["status"] == "down"
    assert payload["dependencies"]["redis"]["status"] == "up"


def test_readiness_endpoint_returns_503_when_redis_down(
    app_instance: FastAPI,
    client: TestClient,
) -> None:
    """GET /health/ready should return 503 degraded when Redis is unavailable."""
    app_instance.state.redis_manager = FakeProbeManager(
        healthy=False,
        latency_ms=3001.0,
        detail="Connection failed (ConnectionError)",
    )
    response = client.get("/health/ready")
    assert response.status_code == 503

    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["postgresql"]["status"] == "up"
    assert payload["dependencies"]["redis"]["status"] == "down"
