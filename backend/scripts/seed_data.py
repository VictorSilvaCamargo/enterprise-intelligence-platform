"""Idempotent database seed script importing synthetic Stage 2 datasets."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.database import DatabaseManager
from app.core.logging import configure_logging
from app.modules.data_integration.repository import DataSourceRepository
from app.modules.data_integration.service import DataIntegrationService

logger = logging.getLogger(__name__)


def _resolve_samples_dir() -> Path:
    """Locate data/samples across local repository execution and Docker container mounts."""
    candidates = [
        Path("/app/data/samples"),
        Path(__file__).resolve().parents[2] / "data" / "samples",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate 'data/samples'. Run scripts.generate_sample_data first."
    )


async def seed_sample_data() -> None:
    """Import default synthetic datasets if they are not yet registered in PostgreSQL."""
    settings = get_settings()
    configure_logging(settings.log_level)
    samples_dir = _resolve_samples_dir()

    seed_specs: list[tuple[str, Path, str | None]] = [
        ("Enterprise Sales 2026 (CSV)", samples_dir / "enterprise_sales_2026.csv", None),
        (
            "Enterprise Operations — Sales Orders (XLSX)",
            samples_dir / "enterprise_operations_2026.xlsx",
            "Sales_Orders",
        ),
        ("Enterprise Customers 2026 (JSON)", samples_dir / "enterprise_customers_2026.json", None),
    ]

    db_manager = DatabaseManager(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        connect_timeout=settings.db_connect_timeout,
    )

    try:
        async for session in db_manager.session():
            source_repo = DataSourceRepository(session)
            service = DataIntegrationService(session=session, settings=settings)

            for source_name, file_path, sheet_name in seed_specs:
                existing = await source_repo.get_by_name(source_name)
                if existing is not None:
                    logger.info("Skipping already seeded data source: %s", source_name)
                    continue

                content = file_path.read_bytes()
                result = await service.import_file(
                    filename=file_path.name,
                    content=content,
                    name=source_name,
                    sheet_name=sheet_name,
                    skip_duplicates=False,
                )
                logger.info(
                    "Seeded '%s': %d persisted records (quality score=%.2f)",
                    result.data_source.name,
                    result.data_source.record_count,
                    result.quality_report.overall_score,
                )
            break
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(seed_sample_data())
