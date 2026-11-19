"""Tests for FastAPI startup, configuration, OpenAPI docs, CORS, and error handling."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.modules import PLANNED_MODULES


def test_openapi_and_docs_available(client: TestClient) -> None:
    """OpenAPI schema and Swagger UI should be exposed and include health routes."""
    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == 200
    schema = openapi_resp.json()
    assert schema["info"]["title"] == "Enterprise Intelligence Platform"
    assert "/health" in schema["paths"]
    assert "/health/ready" in schema["paths"]

    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200


def test_cors_allows_configured_origin(client: TestClient) -> None:
    """CORS preflight should authorize configured frontend origins."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_app_error_and_unhandled_exceptions_are_sanitized(
    app_instance: FastAPI,
    client: TestClient,
) -> None:
    """Known AppError and unexpected exceptions must return sanitized ErrorResponse JSON."""

    @app_instance.get("/_test/app-error")
    async def raise_app_error() -> None:
        raise ServiceUnavailableError("Downstream dependency offline.")

    @app_instance.get("/_test/unexpected-error")
    async def raise_unexpected() -> None:
        raise RuntimeError("postgresql://user:super_secret_password@db:5432/eip")

    app_error_resp = client.get("/_test/app-error", headers={"X-Request-ID": "req-err-1"})
    assert app_error_resp.status_code == 503
    body = app_error_resp.json()
    assert body["error_code"] == "SERVICE_UNAVAILABLE"
    assert body["message"] == "Downstream dependency offline."
    assert body["request_id"] == "req-err-1"

    unexpected_resp = client.get("/_test/unexpected-error", headers={"X-Request-ID": "req-err-2"})
    assert unexpected_resp.status_code == 500
    unexpected_body = unexpected_resp.json()
    assert unexpected_body["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "super_secret_password" not in unexpected_resp.text
    assert unexpected_body["request_id"] == "req-err-2"


def test_settings_parses_comma_separated_cors_and_module_registry() -> None:
    """Settings should parse CSV CORS origins and expose planned module boundaries."""
    settings = Settings(
        _env_file=None,
        cors_origins="http://localhost:5173, https://app.example.com",
    )
    assert settings.cors_origins == ["http://localhost:5173", "https://app.example.com"]
    assert settings.safe_database_target == "localhost:5432/eip_db"
    assert settings.safe_redis_target == "localhost:6379/0"

    module_keys = {module.key for module in PLANNED_MODULES}
    assert module_keys == {
        "data_integration",
        "ai_knowledge_hub",
        "ai_agents",
        "business_intelligence",
        "workflow_automation",
    }
