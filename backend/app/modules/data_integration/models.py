"""SQLAlchemy persistence models for the Data Integration module."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DataSource(Base, TimestampMixin):
    """Registered enterprise data source created from an imported dataset."""

    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint("file_type IN ('csv', 'xlsx', 'json')", name="valid_file_type"),
        CheckConstraint("status IN ('active', 'archived', 'failed')", name="valid_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    schema_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    import_jobs: Mapped[list[ImportJob]] = relationship(
        back_populates="data_source",
        cascade="all, delete-orphan",
        order_by="ImportJob.started_at.desc()",
    )
    records: Mapped[list[ImportedRecord]] = relationship(
        back_populates="data_source",
        cascade="all, delete-orphan",
    )


class ImportJob(Base):
    """Execution audit record for a file ingestion and ETL validation run."""

    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'completed_with_warnings', 'failed')",
            name="valid_job_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_valid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_values_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_messages: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    data_source: Mapped[DataSource] = relationship(back_populates="import_jobs")
    records: Mapped[list[ImportedRecord]] = relationship(
        back_populates="import_job",
        cascade="all, delete-orphan",
    )


class ImportedRecord(Base):
    """Normalized enterprise record persisted with original raw traceability."""

    __tablename__ = "imported_records"
    __table_args__ = (
        Index("ix_imported_records_source_imported_at", "data_source_id", "imported_at"),
        Index("ix_imported_records_content_gin", "content", postgresql_using="gin"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    data_source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    import_job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    raw_content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    data_source: Mapped[DataSource] = relationship(back_populates="records")
    import_job: Mapped[ImportJob] = relationship(back_populates="records")
