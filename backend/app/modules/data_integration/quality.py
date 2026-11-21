"""Transparent data quality scoring and profiling calculations."""

from __future__ import annotations

from dataclasses import dataclass

QUALITY_METHODOLOGY = (
    "Weighted quality index (0-100): "
    "35% Completeness (non-null cells across non-empty rows) + "
    "30% Validity (valid rows / received rows) + "
    "20% Uniqueness (distinct valid rows / valid rows) + "
    "15% Type Consistency (cells matching inferred column type / evaluated non-null cells)."
)


@dataclass(slots=True)
class ColumnProfile:
    """Quality and type metadata for a single normalized column."""

    column_name: str
    original_name: str
    inferred_type: str
    non_null_count: int
    missing_count: int
    missing_rate: float
    type_error_count: int
    distinct_count: int


@dataclass(slots=True)
class QualityReport:
    """Aggregated data quality metrics computed for an import or preview."""

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
    column_profiles: list[ColumnProfile]


def compute_quality_report(
    *,
    records_received: int,
    records_valid: int,
    records_rejected: int,
    duplicates_found: int,
    missing_values_count: int,
    formatting_issues_count: int,
    evaluated_cells: int,
    type_errors_count: int,
    column_profiles: list[ColumnProfile],
) -> QualityReport:
    """Compute documented data quality dimensions and weighted overall score."""
    total_valid_cells = records_valid * len(column_profiles)
    if total_valid_cells > 0:
        completeness_rate = round(
            max(0.0, (total_valid_cells - missing_values_count) / total_valid_cells) * 100.0,
            2,
        )
    else:
        completeness_rate = 0.0

    validity_rate = (
        round((records_valid / records_received) * 100.0, 2) if records_received > 0 else 0.0
    )

    uniqueness_rate = (
        round(max(0.0, (records_valid - duplicates_found) / records_valid) * 100.0, 2)
        if records_valid > 0
        else 0.0
    )

    if evaluated_cells > 0:
        type_consistency_rate = round(
            max(0.0, (evaluated_cells - type_errors_count) / evaluated_cells) * 100.0,
            2,
        )
    else:
        type_consistency_rate = 100.0 if records_received > 0 else 0.0

    overall_score = round(
        0.35 * completeness_rate
        + 0.30 * validity_rate
        + 0.20 * uniqueness_rate
        + 0.15 * type_consistency_rate,
        2,
    )

    return QualityReport(
        completeness_rate=completeness_rate,
        validity_rate=validity_rate,
        uniqueness_rate=uniqueness_rate,
        type_consistency_rate=type_consistency_rate,
        overall_score=overall_score,
        records_received=records_received,
        records_valid=records_valid,
        records_rejected=records_rejected,
        duplicates_found=duplicates_found,
        missing_values_count=missing_values_count,
        formatting_issues_count=formatting_issues_count,
        methodology=QUALITY_METHODOLOGY,
        column_profiles=column_profiles,
    )
