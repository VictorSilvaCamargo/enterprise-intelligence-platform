"""Integration tests for Stage 2 Data Integration API backed by PostgreSQL."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from io import BytesIO

import asyncpg
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy.engine import URL

from app.core.config import Settings
from app.core.database import DatabaseManager
from app.main import create_app
from app.models.base import Base
from app.modules.data_integration import models as _models  # noqa: F401
from tests.conftest import FakeProbeManager


def _build_test_pg_settings() -> Settings:
    pg_host = os.environ.get("TEST_POSTGRES_HOST", "localhost")
    pg_port = int(os.environ.get("TEST_POSTGRES_PORT", "5432"))
    pg_user = os.environ.get("POSTGRES_USER", "eip_user")
    pg_password = os.environ.get("POSTGRES_PASSWORD", "change_me_local_dev_only")
    pg_db = os.environ.get("TEST_POSTGRES_DB", "eip_test_db")

    return Settings(
        _env_file=None,
        app_name="Enterprise Intelligence Platform",
        app_version="0.2.0",
        app_env="test",
        log_level="WARNING",
        postgres_host=pg_host,
        postgres_port=pg_port,
        postgres_user=pg_user,
        postgres_password=pg_password,
        postgres_db=pg_db,
        max_upload_size_mb=1,
        preview_sample_rows=10,
    )


async def _ensure_test_database_exists(settings: Settings) -> None:
    conn = await asyncpg.connect(
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.postgres_db,
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{settings.postgres_db}"')
    finally:
        await conn.close()


def _make_xlsx_bytes() -> bytes:
    wb = Workbook()
    ws1 = wb.active
    assert ws1 is not None
    ws1.title = "Sales"
    ws1.append(["Order ID", "Order Date", "Amount"])
    ws1.append(["X-001", "2026-06-01", 150.0])
    ws1.append(["X-002", "2026-06-02", 275.5])

    ws2 = wb.create_sheet(title="Inventory")
    ws2.append(["SKU", "Stock"])
    ws2.append(["SKU-10", 40])
    ws2.append(["SKU-20", 85])

    buf = BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


@pytest_asyncio.fixture
async def pg_client() -> AsyncIterator[AsyncClient]:
    """Provide an AsyncClient wired to a clean, isolated PostgreSQL test database."""
    settings = _build_test_pg_settings()
    await _ensure_test_database_exists(settings)

    db_url = URL.create(
        drivername="postgresql+asyncpg",
        username=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    ).render_as_string(hide_password=False)

    db_manager = DatabaseManager(db_url, pool_size=2, max_overflow=2)
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    app: FastAPI = create_app(settings)
    app.state.settings = settings
    app.state.db_manager = db_manager
    app.state.redis_manager = FakeProbeManager(healthy=True, latency_ms=0.5)

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        await db_manager.close()


async def test_preview_and_import_csv_xlsx_json_end_to_end(pg_client: AsyncClient) -> None:
    csv_bytes = (
        b"Order ID,Order Date,Customer Name ,Region,Amount\n"
        b"ORD-1,2026-05-01,  Acme   Labs ,North America,100.50\n"
        b"ORD-2,2026-05-02,Meridian,Europe,250.00\n"
        b"ORD-1,2026-05-01,Acme Labs,North America,100.50\n"
        b"ORD-3,2026-05-03,Solstice,,bad_amount\n"
    )

    # 1. Preview CSV
    preview_resp = await pg_client.post(
        "/api/v1/data-sources/preview",
        files={"file": ("sales.csv", csv_bytes, "text/csv")},
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["file_type"] == "csv"
    assert preview["records_received"] == 4
    assert preview["records_valid"] == 3
    assert preview["records_rejected"] == 1
    assert preview["duplicates_found"] == 1
    assert preview["columns"] == ["order_id", "order_date", "customer_name", "region", "amount"]
    assert len(preview["sample_rows"]) == 3

    # Verify preview did not persist anything
    sources_before = await pg_client.get("/api/v1/data-sources")
    assert sources_before.status_code == 200
    assert sources_before.json()["total"] == 0

    # 2. Import CSV with skip_duplicates=true
    import_csv_resp = await pg_client.post(
        "/api/v1/data-sources/import",
        data={"name": "Q2 Sales CSV", "skip_duplicates": "true"},
        files={"file": ("sales.csv", csv_bytes, "text/csv")},
    )
    assert import_csv_resp.status_code == 201
    csv_imported = import_csv_resp.json()
    csv_source_id = csv_imported["data_source"]["id"]
    csv_job_id = csv_imported["import_job"]["id"]
    assert csv_imported["data_source"]["record_count"] == 2
    assert csv_imported["import_job"]["status"] == "completed_with_warnings"
    assert csv_imported["import_job"]["records_rejected"] == 1

    # 3. Preview and import XLSX second sheet
    xlsx_bytes = _make_xlsx_bytes()
    xlsx_preview_resp = await pg_client.post(
        "/api/v1/data-sources/preview",
        data={"sheet_name": "Inventory"},
        files={
            "file": (
                "ops.xlsx",
                xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert xlsx_preview_resp.status_code == 200
    assert xlsx_preview_resp.json()["available_sheets"] == ["Sales", "Inventory"]
    assert xlsx_preview_resp.json()["selected_sheet"] == "Inventory"

    xlsx_import_resp = await pg_client.post(
        "/api/v1/data-sources/import",
        data={"name": "Inventory Sheet", "sheet_name": "Inventory"},
        files={
            "file": (
                "ops.xlsx",
                xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert xlsx_import_resp.status_code == 201
    assert xlsx_import_resp.json()["data_source"]["sheet_name"] == "Inventory"
    assert xlsx_import_resp.json()["data_source"]["record_count"] == 2

    # 4. Import JSON
    json_bytes = json.dumps(
        [
            {"accountId": "ACC-1", "company": "SynthCorp", "tier": "Enterprise"},
            {"accountId": "ACC-2", "company": "Horizon Mock", "tier": "Growth"},
            {"accountId": "ACC-1", "company": "SynthCorp", "tier": "Enterprise"},
        ]
    ).encode("utf-8")
    json_import_resp = await pg_client.post(
        "/api/v1/data-sources/import",
        data={"name": "Customer Accounts", "skip_duplicates": "false"},
        files={"file": ("customers.json", json_bytes, "application/json")},
    )
    assert json_import_resp.status_code == 201
    json_source_id = json_import_resp.json()["data_source"]["id"]
    assert json_import_resp.json()["data_source"]["record_count"] == 3

    # 5. Pagination, search, and file_type filter on data sources
    page1 = await pg_client.get("/api/v1/data-sources", params={"page": 1, "page_size": 2})
    assert page1.status_code == 200
    assert page1.json()["total"] == 3
    assert page1.json()["total_pages"] == 2
    assert len(page1.json()["items"]) == 2

    filtered = await pg_client.get("/api/v1/data-sources", params={"file_type": "xlsx"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["name"] == "Inventory Sheet"

    # 6. Source detail & quality endpoint
    detail_resp = await pg_client.get(f"/api/v1/data-sources/{csv_source_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["stats"]["total_records"] == 2
    assert len(detail_resp.json()["recent_jobs"]) == 1

    quality_resp = await pg_client.get(f"/api/v1/data-sources/{csv_source_id}/quality")
    assert quality_resp.status_code == 200
    assert quality_resp.json()["records_rejected"] == 1

    # 7. Records query: pagination, text search, dynamic JSONB field filter, and raw traceability
    records_resp = await pg_client.get(
        f"/api/v1/data-sources/{csv_source_id}/records",
        params={"field_name": "customer_name", "field_value": "Acme"},
    )
    assert records_resp.status_code == 200
    records_data = records_resp.json()
    assert records_data["total"] == 1
    record_id = records_data["items"][0]["id"]
    assert records_data["items"][0]["content"]["customer_name"] == "Acme Labs"

    record_detail = await pg_client.get(
        f"/api/v1/data-sources/{csv_source_id}/records/{record_id}"
    )
    assert record_detail.status_code == 200
    assert record_detail.json()["raw_content"]["Customer Name "] == "  Acme   Labs "

    # Duplicate exclusion filter on JSON source
    non_dup = await pg_client.get(
        f"/api/v1/data-sources/{json_source_id}/records",
        params={"include_duplicates": "false"},
    )
    assert non_dup.status_code == 200
    assert non_dup.json()["total"] == 2

    # Text search and date range filtering on CSV source
    search_resp = await pg_client.get(
        f"/api/v1/data-sources/{csv_source_id}/records",
        params={"search": "Meridian", "date_from": "2020-01-01", "date_to": "2035-12-31"},
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] == 1

    future_resp = await pg_client.get(
        f"/api/v1/data-sources/{csv_source_id}/records",
        params={"date_from": "2099-01-01"},
    )
    assert future_resp.status_code == 200
    assert future_resp.json()["total"] == 0

    bad_date = await pg_client.get(
        f"/api/v1/data-sources/{csv_source_id}/records",
        params={"date_from": "not-a-date"},
    )
    assert bad_date.status_code == 400

    # 8. Import jobs & overview endpoints
    jobs_resp = await pg_client.get("/api/v1/import-jobs", params={"page": 1, "page_size": 2})
    assert jobs_resp.status_code == 200
    assert jobs_resp.json()["total"] == 3

    job_detail_resp = await pg_client.get(f"/api/v1/import-jobs/{csv_job_id}")
    assert job_detail_resp.status_code == 200
    assert job_detail_resp.json()["records_received"] == 4

    overview_resp = await pg_client.get("/api/v1/data-management/overview")
    assert overview_resp.status_code == 200
    overview = overview_resp.json()
    assert overview["total_data_sources"] == 3
    assert overview["total_records"] == 7
    assert overview["total_import_jobs"] == 3
    assert overview["average_quality_score"] > 0


async def test_api_error_handling_for_invalid_uploads_and_missing_resources(
    pg_client: AsyncClient,
) -> None:
    bad_ext = await pg_client.post(
        "/api/v1/data-sources/preview",
        files={"file": ("script.exe", b"MZ", "application/octet-stream")},
    )
    assert bad_ext.status_code == 400
    assert bad_ext.json()["error_code"] == "UNSUPPORTED_FILE_FORMAT"

    oversized = await pg_client.post(
        "/api/v1/data-sources/preview",
        files={"file": ("huge.csv", b"a,b\n" + b"1,2\n" * 300000, "text/csv")},
    )
    assert oversized.status_code == 413
    assert oversized.json()["error_code"] == "PAYLOAD_TOO_LARGE"

    empty_resp = await pg_client.post(
        "/api/v1/data-sources/preview",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert empty_resp.status_code == 422

    missing_source = await pg_client.get(
        "/api/v1/data-sources/00000000-0000-0000-0000-000000000000"
    )
    assert missing_source.status_code == 404
    assert missing_source.json()["error_code"] == "NOT_FOUND"
