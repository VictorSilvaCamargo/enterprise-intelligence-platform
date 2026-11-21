"""FastAPI REST endpoints for Stage 2 Data Integration and Analysis."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.modules.data_integration.schemas import (
    DataManagementOverviewResponse,
    DataSourceDetail,
    FilePreviewResponse,
    ImportedRecordDetail,
    ImportExecutionResponse,
    ImportJobDetail,
    PaginatedDataSourcesResponse,
    PaginatedImportJobsResponse,
    PaginatedRecordsResponse,
    QualityReportSchema,
)
from app.modules.data_integration.service import DataIntegrationService

router = APIRouter()


def get_app_settings(request: Request) -> Settings:
    """Resolve runtime Settings from FastAPI application state."""
    state_settings = getattr(request.app.state, "settings", None)
    if isinstance(state_settings, Settings):
        return state_settings
    return get_settings()


def get_data_integration_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> DataIntegrationService:
    """Provide a request-scoped DataIntegrationService instance."""
    return DataIntegrationService(session=session, settings=settings)


ServiceDep = Annotated[DataIntegrationService, Depends(get_data_integration_service)]


@router.post(
    "/data-sources/preview",
    response_model=FilePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview and validate an uploaded data file",
    description=(
        "Extracts CSV, XLSX, or JSON content, normalizes column names, cleans whitespace, "
        "infers types, detects duplicates/missing values, and returns a validation preview "
        "without persisting records to PostgreSQL."
    ),
)
async def preview_data_source(
    service: ServiceDep,
    file: Annotated[UploadFile, File(description="CSV, XLSX, or JSON file to preview")],
    sheet_name: Annotated[
        str | None,
        Form(description="Optional Excel worksheet name when uploading multi-sheet XLSX files"),
    ] = None,
) -> FilePreviewResponse:
    """Preview and validate an uploaded dataset prior to import confirmation."""
    content = await file.read()
    return await service.preview_file(
        filename=file.filename,
        content=content,
        sheet_name=sheet_name,
    )


@router.post(
    "/data-sources/import",
    response_model=ImportExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm and execute dataset import",
    description=(
        "Runs the full ETL pipeline on the uploaded file and atomically persists the DataSource, "
        "ImportJob, and validated ImportedRecord rows in PostgreSQL."
    ),
)
async def import_data_source(
    service: ServiceDep,
    file: Annotated[UploadFile, File(description="CSV, XLSX, or JSON file to import")],
    name: Annotated[
        str | None,
        Form(description="Optional human-readable data source name"),
    ] = None,
    sheet_name: Annotated[
        str | None,
        Form(description="Optional Excel worksheet name for XLSX workbooks"),
    ] = None,
    skip_duplicates: Annotated[
        bool,
        Form(description="When true, duplicate records are excluded from persisted rows"),
    ] = False,
) -> ImportExecutionResponse:
    """Confirm and persist an uploaded dataset into PostgreSQL."""
    content = await file.read()
    return await service.import_file(
        filename=file.filename,
        content=content,
        name=name,
        sheet_name=sheet_name,
        skip_duplicates=skip_duplicates,
    )


@router.get(
    "/data-sources",
    response_model=PaginatedDataSourcesResponse,
    summary="List registered data sources",
)
async def list_data_sources(
    service: ServiceDep,
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    search: Annotated[str | None, Query(description="Search by source or file name")] = None,
    file_type: Annotated[str | None, Query(description="Filter by csv, xlsx, or json")] = None,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by source status")
    ] = None,
) -> PaginatedDataSourcesResponse:
    """List data sources with pagination and optional search/format filters."""
    return await service.list_data_sources(
        page=page,
        page_size=page_size,
        search=search,
        file_type=file_type,
        status=status_filter,
    )


@router.get(
    "/data-sources/{data_source_id}",
    response_model=DataSourceDetail,
    summary="Get data source details and operational statistics",
)
async def get_data_source(
    data_source_id: UUID,
    service: ServiceDep,
) -> DataSourceDetail:
    """Retrieve metadata, statistics, and recent import jobs for a data source."""
    return await service.get_data_source(data_source_id)


@router.get(
    "/data-sources/{data_source_id}/records",
    response_model=PaginatedRecordsResponse,
    summary="Explore paginated imported records for a data source",
)
async def list_data_source_records(
    data_source_id: UUID,
    service: ServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[
        str | None, Query(description="Case-insensitive text search across fields")
    ] = None,
    date_from: Annotated[
        str | None, Query(description="Filter records imported on or after ISO date/datetime")
    ] = None,
    date_to: Annotated[
        str | None, Query(description="Filter records imported on or before ISO date/datetime")
    ] = None,
    field_name: Annotated[str | None, Query(description="Normalized field key to filter")] = None,
    field_value: Annotated[str | None, Query(description="Value substring for field_name")] = None,
    include_duplicates: Annotated[
        bool, Query(description="Include records flagged as duplicates")
    ] = True,
) -> PaginatedRecordsResponse:
    """Query imported records with pagination, search, period, and dynamic field filters."""
    return await service.list_records(
        data_source_id=data_source_id,
        page=page,
        page_size=page_size,
        search=search,
        date_from=date_from,
        date_to=date_to,
        field_name=field_name,
        field_value=field_value,
        include_duplicates=include_duplicates,
    )


@router.get(
    "/data-sources/{data_source_id}/records/{record_id}",
    response_model=ImportedRecordDetail,
    summary="Inspect a single imported record with raw traceability",
)
async def get_data_source_record(
    data_source_id: UUID,
    record_id: UUID,
    service: ServiceDep,
) -> ImportedRecordDetail:
    """Retrieve cleaned and original raw content for a single imported record."""
    return await service.get_record(data_source_id, record_id)


@router.get(
    "/data-sources/{data_source_id}/quality",
    response_model=QualityReportSchema,
    summary="Get data quality report for a data source",
)
async def get_data_source_quality(
    data_source_id: UUID,
    service: ServiceDep,
) -> QualityReportSchema:
    """Return data quality indicators and column profiling for a data source."""
    return await service.get_quality_report(data_source_id)


@router.get(
    "/import-jobs",
    response_model=PaginatedImportJobsResponse,
    summary="List import execution history",
)
async def list_import_jobs(
    service: ServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    data_source_id: Annotated[UUID | None, Query(description="Filter jobs by data source")] = None,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter jobs by execution status")
    ] = None,
) -> PaginatedImportJobsResponse:
    """List paginated import jobs ordered by most recent execution."""
    return await service.list_import_jobs(
        page=page,
        page_size=page_size,
        data_source_id=data_source_id,
        status=status_filter,
    )


@router.get(
    "/import-jobs/{job_id}",
    response_model=ImportJobDetail,
    summary="Get import job execution details",
)
async def get_import_job(
    job_id: UUID,
    service: ServiceDep,
) -> ImportJobDetail:
    """Retrieve complete execution details and quality summary for an import job."""
    return await service.get_import_job(job_id)


@router.get(
    "/data-management/overview",
    response_model=DataManagementOverviewResponse,
    summary="Get global Data Management summary KPIs",
)
async def get_data_management_overview(
    service: ServiceDep,
) -> DataManagementOverviewResponse:
    """Return aggregated counts, average quality scores, and recent import jobs."""
    return await service.get_overview()
