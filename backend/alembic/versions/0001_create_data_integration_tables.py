"""Create data_sources, import_jobs, and imported_records tables.

Revision ID: 0001_data_integration
Revises:
Create Date: 2026-11-21 16:15:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_data_integration"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("schema_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "file_type IN ('csv', 'xlsx', 'json')",
            name=op.f("ck_data_sources_valid_file_type"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'failed')",
            name=op.f("ck_data_sources_valid_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_sources")),
    )
    op.create_index(op.f("ix_data_sources_name"), "data_sources", ["name"], unique=False)
    op.create_index(op.f("ix_data_sources_status"), "data_sources", ["status"], unique=False)

    op.create_table(
        "import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_valid", sa.Integer(), nullable=False),
        sa.Column("records_rejected", sa.Integer(), nullable=False),
        sa.Column("duplicates_found", sa.Integer(), nullable=False),
        sa.Column("missing_values_count", sa.Integer(), nullable=False),
        sa.Column("quality_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_messages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'completed_with_warnings', 'failed')",
            name=op.f("ck_import_jobs_valid_job_status"),
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_sources.id"],
            name=op.f("fk_import_jobs_data_source_id_data_sources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_jobs")),
    )
    op.create_index(
        op.f("ix_import_jobs_data_source_id"), "import_jobs", ["data_source_id"], unique=False
    )
    op.create_index(op.f("ix_import_jobs_status"), "import_jobs", ["status"], unique=False)

    op.create_table(
        "imported_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False),
        sa.Column("validation_warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_sources.id"],
            name=op.f("fk_imported_records_data_source_id_data_sources"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["import_job_id"],
            ["import_jobs.id"],
            name=op.f("fk_imported_records_import_job_id_import_jobs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imported_records")),
    )
    op.create_index(
        op.f("ix_imported_records_data_source_id"),
        "imported_records",
        ["data_source_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_imported_records_import_job_id"),
        "imported_records",
        ["import_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_imported_records_imported_at"),
        "imported_records",
        ["imported_at"],
        unique=False,
    )
    op.create_index(
        "ix_imported_records_source_imported_at",
        "imported_records",
        ["data_source_id", "imported_at"],
        unique=False,
    )
    op.create_index(
        "ix_imported_records_content_gin",
        "imported_records",
        ["content"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_imported_records_content_gin", table_name="imported_records", postgresql_using="gin"
    )
    op.drop_index("ix_imported_records_source_imported_at", table_name="imported_records")
    op.drop_index(op.f("ix_imported_records_imported_at"), table_name="imported_records")
    op.drop_index(op.f("ix_imported_records_import_job_id"), table_name="imported_records")
    op.drop_index(op.f("ix_imported_records_data_source_id"), table_name="imported_records")
    op.drop_table("imported_records")

    op.drop_index(op.f("ix_import_jobs_status"), table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_data_source_id"), table_name="import_jobs")
    op.drop_table("import_jobs")

    op.drop_index(op.f("ix_data_sources_status"), table_name="data_sources")
    op.drop_index(op.f("ix_data_sources_name"), table_name="data_sources")
    op.drop_table("data_sources")
