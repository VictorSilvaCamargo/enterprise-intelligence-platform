"""Application service coordinating ETL execution, transactions, and queries."""

from __future__ import annotations

import logging
import math
from dataclasses import asdict
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import BadRequestError, NotFoundError, UnprocessableEntityError
from app.modules.data_integration.extractors import ExtractorRegistry, default_extractor_registry
from app.modules.data_integration.models import DataSource, ImportedRecord, ImportJob
from app.modules.data_integration.pipeline import ETLPipeline, PipelineResult
from app.modules.data_integration.quality import QualityReport
from app.modules.data_integration.repository import (
    DataSourceRepository,
    ImportedRecordRepository,
    ImportJobRepository,
)
from app.modules.data_integration.schemas import (
    ColumnProfileSchema,
    DataManagementOverviewResponse,
    DataSourceDetail,
    DataSourceStats,
    DataSourceSummary,
    FilePreviewResponse,
    ImportedRecordDetail,
    ImportedRecordSummary,
    ImportExecutionResponse,
    ImportJobDetail,
    ImportJobSummary,
    PaginatedDataSourcesResponse,
    PaginatedImportJobsResponse,
    PaginatedRecordsResponse,
    QualityReportSchema,
    RejectedRowSchema,
)

logger = logging.getLogger(__name__)

MAX_PREVIEW_REJECTED_ROWS = 50
MAX_STORED_JOB_ERRORS = 25


def _quality_report_to_schema(report: QualityReport) -> QualityReportSchema:
    return QualityReportSchema(
        completeness_rate=report.completeness_rate,
        validity_rate=report.validity_rate,
        uniqueness_rate=report.uniqueness_rate,
        type_consistency_rate=report.type_consistency_rate,
        overall_score=report.overall_score,
        records_received=report.records_received,
        records_valid=report.records_valid,
        records_rejected=report.records_rejected,
        duplicates_found=report.duplicates_found,
        missing_values_count=report.missing_values_count,
        formatting_issues_count=report.formatting_issues_count,
        methodology=report.methodology,
        column_profiles=[
            ColumnProfileSchema(**asdict(profile)) for profile in report.column_profiles
        ],
    )


def _job_to_summary(job: ImportJob, data_source_name: str | None = None) -> ImportJobSummary:
    raw_score = job.quality_summary.get("overall_score") if job.quality_summary else None
    quality_score = float(raw_score) if isinstance(raw_score, (int, float)) else None
    return ImportJobSummary(
        id=job.id,
        data_source_id=job.data_source_id,
        data_source_name=data_source_name,
        started_at=job.started_at,
        completed_at=job.completed_at,
        status=job.status,
        original_filename=job.original_filename,
        file_type=job.file_type,
        file_size_bytes=job.file_size_bytes,
        sheet_name=job.sheet_name,
        records_received=job.records_received,
        records_valid=job.records_valid,
        records_rejected=job.records_rejected,
        duplicates_found=job.duplicates_found,
        missing_values_count=job.missing_values_count,
        quality_score=quality_score,
        error_messages=list(job.error_messages or []),
    )


def _parse_date_boundary(value: str | None, *, is_end: bool) -> datetime | None:
    """Parse an ISO date (YYYY-MM-DD) or ISO datetime string into UTC datetime."""
    if value is None or not value.strip():
        return None
    raw = value.strip()
    try:
        if "T" in raw or " " in raw:
            parsed_dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed_dt.tzinfo is None:
                return parsed_dt.replace(tzinfo=UTC)
            return parsed_dt.astimezone(UTC)
        parsed_date = date.fromisoformat(raw)
        boundary_time = time.max if is_end else time.min
        return datetime.combine(parsed_date, boundary_time, tzinfo=UTC)
    except ValueError as exc:
        raise BadRequestError(
            f"Invalid date filter '{raw}'. Expected ISO format YYYY-MM-DD or ISO datetime."
        ) from exc


def _total_pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if total > 0 else 1


class DataIntegrationService:
    """Coordinates ETL processing, persistence, and querying for Data Management."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        extractors: ExtractorRegistry | None = None,
        pipeline: ETLPipeline | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._extractors = extractors or default_extractor_registry
        self._pipeline = pipeline or ETLPipeline()
        self._sources = DataSourceRepository(session)
        self._jobs = ImportJobRepository(session)
        self._records = ImportedRecordRepository(session)

    def _run_etl(
        self,
        *,
        filename: str | None,
        content: bytes,
        sheet_name: str | None,
    ) -> PipelineResult:
        clean_sheet = sheet_name.strip() if sheet_name and sheet_name.strip() else None
        dataset = self._extractors.extract(
            filename=filename,
            content=content,
            max_size_bytes=self._settings.max_upload_size_bytes,
            sheet_name=clean_sheet,
        )
        return self._pipeline.process(dataset)

    async def preview_file(
        self,
        *,
        filename: str | None,
        content: bytes,
        sheet_name: str | None = None,
    ) -> FilePreviewResponse:
        """Extract, clean, validate, and profile an uploaded file without persisting."""
        result = self._run_etl(filename=filename, content=content, sheet_name=sheet_name)
        logger.info(
            "Preview processed: file=%s type=%s received=%d valid=%d rejected=%d duplicates=%d",
            result.original_filename,
            result.file_type,
            result.records_received,
            result.records_valid,
            result.records_rejected,
            result.duplicates_found,
        )
        sample_limit = self._settings.preview_sample_rows
        rejected_schemas = [
            RejectedRowSchema(
                row_number=item.row_number,
                reasons=item.reasons,
                raw_content=item.raw_content,
            )
            for item in result.rejected_rows[:MAX_PREVIEW_REJECTED_ROWS]
        ]

        return FilePreviewResponse(
            original_filename=result.original_filename,
            file_type=result.file_type,
            file_size_bytes=result.file_size_bytes,
            available_sheets=result.available_sheets,
            selected_sheet=result.selected_sheet,
            columns=result.columns,
            original_columns=result.original_columns,
            column_mapping=result.column_mapping,
            records_received=result.records_received,
            records_valid=result.records_valid,
            records_rejected=result.records_rejected,
            duplicates_found=result.duplicates_found,
            missing_values_count=result.missing_values_count,
            formatting_issues=result.formatting_issues,
            rejected_rows=rejected_schemas,
            rejected_rows_truncated=len(result.rejected_rows) > MAX_PREVIEW_REJECTED_ROWS,
            sample_rows=[rec.content for rec in result.valid_records[:sample_limit]],
            quality_report=_quality_report_to_schema(result.quality_report),
        )

    async def import_file(
        self,
        *,
        filename: str | None,
        content: bytes,
        name: str | None = None,
        sheet_name: str | None = None,
        skip_duplicates: bool = False,
    ) -> ImportExecutionResponse:
        """Execute ETL pipeline and atomically persist source, job, and imported records."""
        started_at = datetime.now(UTC)
        result = self._run_etl(filename=filename, content=content, sheet_name=sheet_name)

        if result.records_valid == 0:
            raise UnprocessableEntityError(
                "Import aborted: zero valid records remained after ETL validation.",
                error_code="NO_VALID_RECORDS",
                details={
                    "records_received": result.records_received,
                    "records_rejected": result.records_rejected,
                },
            )

        records_to_persist = (
            [rec for rec in result.valid_records if not rec.is_duplicate]
            if skip_duplicates
            else result.valid_records
        )

        if not records_to_persist:
            raise UnprocessableEntityError(
                "Import aborted: all valid records were filtered out by duplicate exclusion.",
                error_code="NO_RECORDS_TO_PERSIST",
            )

        resolved_name = (
            name.strip()
            if name and name.strip()
            else Path(result.original_filename).stem.replace("_", " ").strip() or "Unnamed Source"
        )
        if len(resolved_name) > 255:
            resolved_name = resolved_name[:255]

        quality_schema = _quality_report_to_schema(result.quality_report)
        quality_payload = quality_schema.model_dump(mode="json")

        error_messages: list[str] = []
        if result.rejected_rows:
            for item in result.rejected_rows[:MAX_STORED_JOB_ERRORS]:
                error_messages.append(f"Row {item.row_number}: {'; '.join(item.reasons)}")
            if len(result.rejected_rows) > MAX_STORED_JOB_ERRORS:
                remaining = len(result.rejected_rows) - MAX_STORED_JOB_ERRORS
                error_messages.append(f"... and {remaining} additional rejected row(s).")
        if result.duplicates_found > 0:
            if skip_duplicates:
                error_messages.append(
                    f"Skipped {result.duplicates_found} duplicate record(s) per import option."
                )
            else:
                error_messages.append(
                    f"Detected {result.duplicates_found} duplicate record(s) (flagged in records)."
                )

        has_warnings = bool(
            result.records_rejected > 0
            or result.duplicates_found > 0
            or result.formatting_issues
            or result.missing_values_count > 0
        )
        job_status = "completed_with_warnings" if has_warnings else "completed"

        schema_metadata: dict[str, Any] = {
            "columns": result.columns,
            "original_columns": result.original_columns,
            "column_mapping": result.column_mapping,
            "column_types": {
                profile.column_name: profile.inferred_type
                for profile in result.quality_report.column_profiles
            },
            "formatting_issues": result.formatting_issues,
        }

        try:
            data_source = DataSource(
                name=resolved_name,
                file_type=result.file_type,
                original_filename=result.original_filename,
                sheet_name=result.selected_sheet,
                status="active",
                schema_metadata=schema_metadata,
                record_count=len(records_to_persist),
            )
            self._session.add(data_source)
            await self._session.flush()

            completed_at = datetime.now(UTC)
            import_job = ImportJob(
                data_source_id=data_source.id,
                started_at=started_at,
                completed_at=completed_at,
                status=job_status,
                original_filename=result.original_filename,
                file_type=result.file_type,
                file_size_bytes=result.file_size_bytes,
                sheet_name=result.selected_sheet,
                records_received=result.records_received,
                records_valid=result.records_valid,
                records_rejected=result.records_rejected,
                duplicates_found=result.duplicates_found,
                missing_values_count=result.missing_values_count,
                quality_summary=quality_payload,
                error_messages=error_messages,
            )
            self._session.add(import_job)
            await self._session.flush()

            record_entities = [
                ImportedRecord(
                    data_source_id=data_source.id,
                    import_job_id=import_job.id,
                    row_number=rec.row_number,
                    content=rec.content,
                    raw_content=rec.raw_content,
                    is_duplicate=rec.is_duplicate,
                    validation_warnings=rec.validation_warnings,
                    imported_at=completed_at,
                )
                for rec in records_to_persist
            ]
            self._session.add_all(record_entities)
            await self._session.commit()
            await self._session.refresh(data_source)
            await self._session.refresh(import_job)
        except Exception:
            await self._session.rollback()
            logger.exception(
                "Database transaction failed during import of %s",
                result.original_filename,
            )
            raise

        logger.info(
            "Import persisted: source_id=%s job_id=%s file=%s persisted=%d rejected=%d score=%.2f",
            data_source.id,
            import_job.id,
            result.original_filename,
            len(records_to_persist),
            result.records_rejected,
            quality_schema.overall_score,
        )

        source_summary = DataSourceSummary(
            id=data_source.id,
            name=data_source.name,
            file_type=data_source.file_type,
            original_filename=data_source.original_filename,
            sheet_name=data_source.sheet_name,
            status=data_source.status,
            record_count=data_source.record_count,
            created_at=data_source.created_at,
            updated_at=data_source.updated_at,
            latest_quality_score=quality_schema.overall_score,
        )
        job_detail = ImportJobDetail(
            **_job_to_summary(import_job, data_source.name).model_dump(),
            quality_summary=import_job.quality_summary,
        )
        rejected_schemas = [
            RejectedRowSchema(
                row_number=item.row_number,
                reasons=item.reasons,
                raw_content=item.raw_content,
            )
            for item in result.rejected_rows[:MAX_PREVIEW_REJECTED_ROWS]
        ]

        return ImportExecutionResponse(
            data_source=source_summary,
            import_job=job_detail,
            quality_report=quality_schema,
            rejected_rows=rejected_schemas,
        )

    async def list_data_sources(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        file_type: str | None = None,
        status: str | None = None,
    ) -> PaginatedDataSourcesResponse:
        """Return paginated list of registered data sources."""
        rows, total = await self._sources.list_paginated(
            page=page,
            page_size=page_size,
            search=search,
            file_type=file_type,
            status=status,
        )
        items = [
            DataSourceSummary(
                id=ds.id,
                name=ds.name,
                file_type=ds.file_type,
                original_filename=ds.original_filename,
                sheet_name=ds.sheet_name,
                status=ds.status,
                record_count=ds.record_count,
                created_at=ds.created_at,
                updated_at=ds.updated_at,
                latest_quality_score=score,
            )
            for ds, score in rows
        ]
        return PaginatedDataSourcesResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=_total_pages(total, page_size),
        )

    async def get_data_source(self, data_source_id: UUID) -> DataSourceDetail:
        """Return detailed metadata, operational statistics, and recent jobs for a source."""
        ds = await self._sources.get_by_id(data_source_id)
        if ds is None:
            raise NotFoundError(f"Data source '{data_source_id}' was not found.")

        stats_dict = await self._records.get_source_stats(data_source_id)
        recent_job_rows = await self._jobs.list_for_source(data_source_id, limit=10)
        latest_score = await self._sources.get_latest_quality_score(data_source_id)

        return DataSourceDetail(
            id=ds.id,
            name=ds.name,
            file_type=ds.file_type,
            original_filename=ds.original_filename,
            sheet_name=ds.sheet_name,
            status=ds.status,
            record_count=ds.record_count,
            created_at=ds.created_at,
            updated_at=ds.updated_at,
            latest_quality_score=latest_score,
            schema_metadata=dict(ds.schema_metadata or {}),
            stats=DataSourceStats(**stats_dict),
            recent_jobs=[_job_to_summary(job, ds_name) for job, ds_name in recent_job_rows],
        )

    async def get_quality_report(self, data_source_id: UUID) -> QualityReportSchema:
        """Return the latest quality report computed for a data source."""
        ds = await self._sources.get_by_id(data_source_id)
        if ds is None:
            raise NotFoundError(f"Data source '{data_source_id}' was not found.")

        latest_job = await self._jobs.get_latest_for_source(data_source_id)
        if latest_job is None or not latest_job.quality_summary:
            raise NotFoundError(f"No quality report available for data source '{data_source_id}'.")

        return QualityReportSchema.model_validate(latest_job.quality_summary)

    async def list_records(
        self,
        *,
        data_source_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        field_name: str | None = None,
        field_value: str | None = None,
        include_duplicates: bool = True,
    ) -> PaginatedRecordsResponse:
        """Query imported records with pagination, text search, date range, and field filters."""
        ds = await self._sources.get_by_id(data_source_id)
        if ds is None:
            raise NotFoundError(f"Data source '{data_source_id}' was not found.")

        parsed_from = _parse_date_boundary(date_from, is_end=False)
        parsed_to = _parse_date_boundary(date_to, is_end=True)
        if parsed_from and parsed_to and parsed_from > parsed_to:
            raise BadRequestError("'date_from' cannot be later than 'date_to'.")

        records, total = await self._records.list_paginated(
            data_source_id=data_source_id,
            page=page,
            page_size=page_size,
            search=search,
            date_from=parsed_from,
            date_to=parsed_to,
            field_name=field_name,
            field_value=field_value,
            include_duplicates=include_duplicates,
        )

        columns_raw = ds.schema_metadata.get("columns", []) if ds.schema_metadata else []
        columns = [str(col) for col in columns_raw] if isinstance(columns_raw, list) else []

        return PaginatedRecordsResponse(
            items=[ImportedRecordSummary.model_validate(rec) for rec in records],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=_total_pages(total, page_size),
            columns=columns,
        )

    async def get_record(self, data_source_id: UUID, record_id: UUID) -> ImportedRecordDetail:
        """Return full record details including original raw_content for auditing."""
        record = await self._records.get_by_id(data_source_id, record_id)
        if record is None:
            raise NotFoundError(
                f"Record '{record_id}' was not found in data source '{data_source_id}'."
            )
        return ImportedRecordDetail.model_validate(record)

    async def list_import_jobs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        data_source_id: UUID | None = None,
        status: str | None = None,
    ) -> PaginatedImportJobsResponse:
        """Return paginated import execution history."""
        rows, total = await self._jobs.list_paginated(
            page=page,
            page_size=page_size,
            data_source_id=data_source_id,
            status=status,
        )
        return PaginatedImportJobsResponse(
            items=[_job_to_summary(job, ds_name) for job, ds_name in rows],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=_total_pages(total, page_size),
        )

    async def get_import_job(self, job_id: UUID) -> ImportJobDetail:
        """Return full details of a single import job execution."""
        row = await self._jobs.get_by_id_with_source_name(job_id)
        if row is None:
            raise NotFoundError(f"Import job '{job_id}' was not found.")
        job, ds_name = row
        return ImportJobDetail(
            **_job_to_summary(job, ds_name).model_dump(),
            quality_summary=dict(job.quality_summary or {}),
        )

    async def get_overview(self) -> DataManagementOverviewResponse:
        """Return aggregate KPIs and recent jobs for the Data Management overview."""
        aggregates = await self._jobs.get_overview_aggregates()
        recent_rows, _ = await self._jobs.list_paginated(page=1, page_size=5)
        return DataManagementOverviewResponse(
            **aggregates,
            recent_import_jobs=[_job_to_summary(job, ds_name) for job, ds_name in recent_rows],
        )
