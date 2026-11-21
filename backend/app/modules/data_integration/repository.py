"""Async SQLAlchemy repositories for DataSource, ImportJob, and ImportedRecord."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Float, Text, case, cast, func, select

from app.modules.data_integration.models import DataSource, ImportedRecord, ImportJob
from app.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    """Persistence queries for registered data sources."""

    model = DataSource

    async def get_by_id(self, data_source_id: UUID) -> DataSource | None:
        """Fetch a single data source by primary key."""
        stmt = select(DataSource).where(DataSource.id == data_source_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> DataSource | None:
        """Fetch the first data source matching an exact name."""
        stmt = select(DataSource).where(DataSource.name == name).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        file_type: str | None = None,
        status: str | None = None,
    ) -> tuple[list[tuple[DataSource, float | None]], int]:
        """Return paginated data sources paired with their latest job quality score."""
        latest_score_subq = (
            select(ImportJob.quality_summary["overall_score"].astext.cast(Float))
            .where(ImportJob.data_source_id == DataSource.id)
            .order_by(ImportJob.started_at.desc())
            .limit(1)
            .correlate(DataSource)
            .scalar_subquery()
        )

        filters: list[Any] = []
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                DataSource.name.ilike(pattern) | DataSource.original_filename.ilike(pattern)
            )
        if file_type:
            filters.append(DataSource.file_type == file_type.lower())
        if status:
            filters.append(DataSource.status == status.lower())

        count_stmt = select(func.count(DataSource.id)).where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(DataSource, latest_score_subq.label("latest_quality_score"))
            .where(*filters)
            .order_by(DataSource.created_at.desc(), DataSource.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.session.execute(stmt)).all()
        items: list[tuple[DataSource, float | None]] = [
            (row[0], float(row[1]) if row[1] is not None else None) for row in rows
        ]
        return items, total

    async def get_latest_quality_score(self, data_source_id: UUID) -> float | None:
        """Fetch the latest overall quality score recorded for a data source."""
        stmt = (
            select(ImportJob.quality_summary["overall_score"].astext.cast(Float))
            .where(ImportJob.data_source_id == data_source_id)
            .order_by(ImportJob.started_at.desc())
            .limit(1)
        )
        score = (await self.session.execute(stmt)).scalar_one_or_none()
        return float(score) if score is not None else None


class ImportJobRepository(BaseRepository[ImportJob]):
    """Persistence queries for import job executions and global metrics."""

    model = ImportJob

    async def get_by_id_with_source_name(self, job_id: UUID) -> tuple[ImportJob, str | None] | None:
        """Fetch an import job joined with its owning data source name."""
        stmt = (
            select(ImportJob, DataSource.name)
            .join(DataSource, DataSource.id == ImportJob.data_source_id)
            .where(ImportJob.id == job_id)
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        return row[0], row[1]

    async def get_latest_for_source(self, data_source_id: UUID) -> ImportJob | None:
        """Return the most recent import job executed for a data source."""
        stmt = (
            select(ImportJob)
            .where(ImportJob.data_source_id == data_source_id)
            .order_by(ImportJob.started_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_source(
        self, data_source_id: UUID, *, limit: int = 10
    ) -> list[tuple[ImportJob, str]]:
        """Return recent import jobs for a specific data source."""
        stmt = (
            select(ImportJob, DataSource.name)
            .join(DataSource, DataSource.id == ImportJob.data_source_id)
            .where(ImportJob.data_source_id == data_source_id)
            .order_by(ImportJob.started_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows]

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        data_source_id: UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[tuple[ImportJob, str]], int]:
        """Return paginated import jobs filtered optionally by source or status."""
        filters: list[Any] = []
        if data_source_id is not None:
            filters.append(ImportJob.data_source_id == data_source_id)
        if status:
            filters.append(ImportJob.status == status.lower())

        count_stmt = select(func.count(ImportJob.id)).where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(ImportJob, DataSource.name)
            .join(DataSource, DataSource.id == ImportJob.data_source_id)
            .where(*filters)
            .order_by(ImportJob.started_at.desc(), ImportJob.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(row[0], row[1]) for row in rows], total

    async def get_overview_aggregates(self) -> dict[str, Any]:
        """Compute global Data Management overview metrics directly in PostgreSQL."""
        ds_stats_stmt = select(
            func.count(DataSource.id),
            func.coalesce(func.sum(DataSource.record_count), 0),
        )
        ds_row = (await self.session.execute(ds_stats_stmt)).one()

        job_stats_stmt = select(
            func.count(ImportJob.id),
            func.coalesce(
                func.avg(ImportJob.quality_summary["overall_score"].astext.cast(Float)),
                0.0,
            ),
            func.coalesce(
                func.avg(ImportJob.quality_summary["completeness_rate"].astext.cast(Float)),
                0.0,
            ),
            func.coalesce(func.sum(ImportJob.duplicates_found), 0),
            func.coalesce(func.sum(ImportJob.records_rejected), 0),
        )
        job_row = (await self.session.execute(job_stats_stmt)).one()

        return {
            "total_data_sources": int(ds_row[0]),
            "total_records": int(ds_row[1]),
            "total_import_jobs": int(job_row[0]),
            "average_quality_score": round(float(job_row[1]), 2),
            "average_completeness_rate": round(float(job_row[2]), 2),
            "total_duplicates_found": int(job_row[3]),
            "total_records_rejected": int(job_row[4]),
        }


class ImportedRecordRepository(BaseRepository[ImportedRecord]):
    """Persistence and JSONB search/filter queries for imported records."""

    model = ImportedRecord

    async def get_by_id(
        self,
        data_source_id: UUID,
        record_id: UUID,
    ) -> ImportedRecord | None:
        """Fetch a single imported record scoped to its parent data source."""
        stmt = select(ImportedRecord).where(
            ImportedRecord.id == record_id,
            ImportedRecord.data_source_id == data_source_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        data_source_id: UUID,
        page: int,
        page_size: int,
        search: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        field_name: str | None = None,
        field_value: str | None = None,
        include_duplicates: bool = True,
    ) -> tuple[list[ImportedRecord], int]:
        """Query imported records with pagination, text search, date range, and JSONB filters."""
        filters: list[Any] = [ImportedRecord.data_source_id == data_source_id]

        if not include_duplicates:
            filters.append(ImportedRecord.is_duplicate.is_(False))
        if date_from is not None:
            filters.append(ImportedRecord.imported_at >= date_from)
        if date_to is not None:
            filters.append(ImportedRecord.imported_at <= date_to)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            filters.append(cast(ImportedRecord.content, Text).ilike(pattern))
        if field_name and field_name.strip():
            clean_field = field_name.strip()
            if field_value is not None and field_value.strip():
                filters.append(
                    ImportedRecord.content[clean_field].astext.ilike(f"%{field_value.strip()}%")
                )
            else:
                filters.append(ImportedRecord.content.has_key(clean_field))

        count_stmt = select(func.count(ImportedRecord.id)).where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(ImportedRecord)
            .where(*filters)
            .order_by(ImportedRecord.row_number.asc(), ImportedRecord.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        records = list((await self.session.execute(stmt)).scalars().all())
        return records, total

    async def get_source_stats(self, data_source_id: UUID) -> dict[str, Any]:
        """Compute record and job aggregate statistics for a single data source."""
        rec_stmt = select(
            func.count(ImportedRecord.id),
            func.coalesce(
                func.sum(case((ImportedRecord.is_duplicate.is_(True), 1), else_=0)),
                0,
            ),
            func.min(ImportedRecord.imported_at),
            func.max(ImportedRecord.imported_at),
        ).where(ImportedRecord.data_source_id == data_source_id)
        rec_row = (await self.session.execute(rec_stmt)).one()

        job_count_stmt = select(func.count(ImportJob.id)).where(
            ImportJob.data_source_id == data_source_id
        )
        job_count = int((await self.session.execute(job_count_stmt)).scalar_one())

        total_records = int(rec_row[0])
        duplicate_records = int(rec_row[1])
        return {
            "total_records": total_records,
            "duplicate_records": duplicate_records,
            "distinct_records": max(0, total_records - duplicate_records),
            "total_import_jobs": job_count,
            "first_imported_at": rec_row[2],
            "last_imported_at": rec_row[3],
        }
