"""Pydantic v2 request/response contracts for the Data Integration API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ColumnProfileSchema(BaseModel):
    """Profiling metrics for a normalized dataset column."""

    column_name: str
    original_name: str
    inferred_type: str
    non_null_count: int
    missing_count: int
    missing_rate: float
    type_error_count: int
    distinct_count: int


class RejectedRowSchema(BaseModel):
    """Explicit validation failure details for a rejected source row."""

    row_number: int
    reasons: list[str]
    raw_content: dict[str, Any]


class QualityReportSchema(BaseModel):
    """Comprehensive quality metrics and scoring methodology for an import."""

    completeness_rate: float
    validity_rate: float
    uniqueness_rate: float
    type_consistency_rate: float
    overall_score: float
    records_received: int
    records_valid: int
    records_rejected: int
    duplicates_found: int
    missing_values_count: int
    formatting_issues_count: int
    methodology: str
    column_profiles: list[ColumnProfileSchema]


class FilePreviewResponse(BaseModel):
    """Response returned by file preview & validation before import confirmation."""

    original_filename: str
    file_type: str
    file_size_bytes: int
    available_sheets: list[str]
    selected_sheet: str | None
    columns: list[str]
    original_columns: list[str]
    column_mapping: dict[str, str]
    records_received: int
    records_valid: int
    records_rejected: int
    duplicates_found: int
    missing_values_count: int
    formatting_issues: list[str]
    rejected_rows: list[RejectedRowSchema]
    rejected_rows_truncated: bool = False
    sample_rows: list[dict[str, Any]]
    quality_report: QualityReportSchema


class DataSourceSummary(BaseModel):
    """Summary representation of a persisted data source."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    file_type: str
    original_filename: str
    sheet_name: str | None
    status: str
    record_count: int
    created_at: datetime
    updated_at: datetime
    latest_quality_score: float | None = None


class DataSourceStats(BaseModel):
    """Aggregated operational statistics for a single data source."""

    total_records: int
    duplicate_records: int
    distinct_records: int
    total_import_jobs: int
    first_imported_at: datetime | None
    last_imported_at: datetime | None


class ImportJobSummary(BaseModel):
    """Summary of an import job execution."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    data_source_id: UUID
    data_source_name: str | None = None
    started_at: datetime
    completed_at: datetime | None
    status: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    sheet_name: str | None
    records_received: int
    records_valid: int
    records_rejected: int
    duplicates_found: int
    missing_values_count: int
    quality_score: float | None = None
    error_messages: list[str] = Field(default_factory=list)


class ImportJobDetail(ImportJobSummary):
    """Detailed import job record including serialized quality breakdown."""

    quality_summary: dict[str, Any] = Field(default_factory=dict)


class DataSourceDetail(DataSourceSummary):
    """Detailed data source view with inferred schema, stats, and job history."""

    schema_metadata: dict[str, Any] = Field(default_factory=dict)
    stats: DataSourceStats
    recent_jobs: list[ImportJobSummary]


class PaginatedDataSourcesResponse(BaseModel):
    """Paginated collection of data sources."""

    items: list[DataSourceSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedImportJobsResponse(BaseModel):
    """Paginated collection of import jobs."""

    items: list[ImportJobSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class ImportExecutionResponse(BaseModel):
    """Response returned upon confirming and persisting an import."""

    data_source: DataSourceSummary
    import_job: ImportJobDetail
    quality_report: QualityReportSchema
    rejected_rows: list[RejectedRowSchema]


class ImportedRecordSummary(BaseModel):
    """Row summary returned inside paginated data explorer responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    data_source_id: UUID
    import_job_id: UUID
    row_number: int
    content: dict[str, Any]
    is_duplicate: bool
    validation_warnings: list[str]
    imported_at: datetime


class ImportedRecordDetail(ImportedRecordSummary):
    """Full record inspection payload including original raw input."""

    raw_content: dict[str, Any]


class PaginatedRecordsResponse(BaseModel):
    """Paginated collection of imported records for a data source."""

    items: list[ImportedRecordSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    columns: list[str]


class DataManagementOverviewResponse(BaseModel):
    """Global summary metrics for the Data Management overview dashboard."""

    total_data_sources: int
    total_records: int
    total_import_jobs: int
    average_quality_score: float
    average_completeness_rate: float
    total_duplicates_found: int
    total_records_rejected: int
    recent_import_jobs: list[ImportJobSummary]
