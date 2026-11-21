"""ETL transformation, normalization, type validation, and duplicate detection pipeline."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.modules.data_integration.extractors import ExtractedDataset
from app.modules.data_integration.quality import (
    ColumnProfile,
    QualityReport,
    compute_quality_report,
)

NULL_SENTINELS = frozenset({"", "null", "none", "n/a", "na", "nan", "nil", "-"})
BOOL_TRUE = frozenset({"true"})
BOOL_FALSE = frozenset({"false"})
CURRENCY_PREFIX_RE = re.compile(r"^(?:US\$|R\$|EUR|BRL|USD|\$|€|£)\s*", re.IGNORECASE)
INT_RE = re.compile(r"^[+-]?\d+$")
US_NUMBER_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?$")
EU_NUMBER_RE = re.compile(r"^[+-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?$")
COMMA_DECIMAL_RE = re.compile(r"^[+-]?\d+,\d+$")
PLAIN_FLOAT_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")

DATE_FORMATS: tuple[tuple[str, str], ...] = (
    ("%Y-%m-%d", "iso_date"),
    ("%Y/%m/%d", "slash_ymd"),
    ("%d/%m/%Y", "slash_dmy"),
    ("%m/%d/%Y", "slash_mdy"),
    ("%d-%m-%Y", "dash_dmy"),
    ("%Y-%m-%d %H:%M:%S", "iso_datetime"),
)


@dataclass(slots=True)
class ProcessedRecord:
    """Validated record ready for persistence with raw traceability."""

    row_number: int
    content: dict[str, Any]
    raw_content: dict[str, Any]
    is_duplicate: bool
    validation_warnings: list[str]


@dataclass(slots=True)
class RejectedRowDetail:
    """Explicit rejection record explaining why a row failed validation."""

    row_number: int
    reasons: list[str]
    raw_content: dict[str, Any]


@dataclass(slots=True)
class PipelineResult:
    """Full output of the ETL pipeline before database persistence."""

    file_type: str
    original_filename: str
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
    valid_records: list[ProcessedRecord]
    rejected_rows: list[RejectedRowDetail]
    quality_report: QualityReport


def normalize_column_name(raw_name: str, index: int, seen: set[str]) -> str:
    """Normalize an arbitrary header string into a deterministic snake_case identifier."""
    trimmed = raw_name.strip()
    if trimmed.startswith("__empty_col_"):
        trimmed = ""

    decomposed = unicodedata.normalize("NFKD", trimmed)
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", ascii_text)
    snake = re.sub(r"[^a-zA-Z0-9]+", "_", camel_spaced).strip("_").lower()

    base = snake if snake else f"column_{index + 1}"
    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}_{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def _clean_cell_value(value: Any) -> tuple[Any, bool]:
    """Normalize whitespace and convert null sentinels to None.

    Returns (cleaned_value, was_whitespace_reformatted).
    """
    if value is None:
        return None, False
    if isinstance(value, bool):
        return value, False
    if isinstance(value, float) and math.isnan(value):
        return None, False
    if isinstance(value, (int, float)):
        return value, False
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True), False

    raw_str = str(value)
    collapsed = re.sub(r"\s+", " ", raw_str).strip()
    if collapsed.lower() in NULL_SENTINELS:
        return None, False
    return collapsed, collapsed != raw_str


def _try_parse_bool(value: Any) -> tuple[bool, bool | None]:
    if isinstance(value, bool):
        return True, value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in BOOL_TRUE:
            return True, True
        if lowered in BOOL_FALSE:
            return True, False
    return False, None


def _try_parse_int(value: Any) -> tuple[bool, int | None, bool]:
    if isinstance(value, bool):
        return False, None, False
    if isinstance(value, int):
        return True, value, False
    if isinstance(value, float):
        if value.is_integer():
            return True, int(value), False
        return False, None, False
    if isinstance(value, str) and INT_RE.match(value):
        return True, int(value), False
    return False, None, False


def _try_parse_float(value: Any) -> tuple[bool, float | None, bool]:
    if isinstance(value, bool):
        return False, None, False
    if isinstance(value, (int, float)):
        return True, float(value), False
    if not isinstance(value, str):
        return False, None, False

    stripped_currency = CURRENCY_PREFIX_RE.sub("", value).strip()
    reformatted = stripped_currency != value

    if PLAIN_FLOAT_RE.match(stripped_currency):
        return True, float(stripped_currency), reformatted
    if US_NUMBER_RE.match(stripped_currency):
        return True, float(stripped_currency.replace(",", "")), True
    if EU_NUMBER_RE.match(stripped_currency):
        normalized = stripped_currency.replace(".", "").replace(",", ".")
        return True, float(normalized), True
    if COMMA_DECIMAL_RE.match(stripped_currency):
        return True, float(stripped_currency.replace(",", ".")), True
    return False, None, False


def _try_parse_date(value: Any) -> tuple[bool, str | None, str | None]:
    """Attempt parsing a date value into ISO YYYY-MM-DD, returning (ok, iso_str, format_tag)."""
    if isinstance(value, datetime):
        return True, value.date().isoformat(), "iso_datetime"
    if isinstance(value, date):
        return True, value.isoformat(), "iso_date"
    if not isinstance(value, str):
        return False, None, None

    candidate = value.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", candidate):
        try:
            parsed_dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return True, parsed_dt.date().isoformat(), "iso_datetime"
        except ValueError:
            return False, None, None

    for fmt, tag in DATE_FORMATS:
        try:
            parsed = datetime.strptime(candidate, fmt)
            return True, parsed.date().isoformat(), tag
        except ValueError:
            continue
    return False, None, None


def _infer_column_type(values: list[Any]) -> str:
    """Infer the dominant column type when >= 60% of non-null values match."""
    non_null = [v for v in values if v is not None]
    total = len(non_null)
    if total == 0:
        return "string"

    bool_matches = sum(1 for v in non_null if _try_parse_bool(v)[0])
    if bool_matches / total >= 0.6:
        return "boolean"

    int_matches = sum(1 for v in non_null if _try_parse_int(v)[0])
    float_results = [_try_parse_float(v) for v in non_null]
    float_matches = sum(1 for ok, _, _ in float_results if ok)
    has_fractional = any(
        ok and num is not None and not float(num).is_integer() for ok, num, _ in float_results
    )

    if int_matches / total >= 0.6 and not has_fractional:
        return "integer"
    if float_matches / total >= 0.6:
        return "float"

    date_matches = sum(1 for v in non_null if _try_parse_date(v)[0])
    if date_matches / total >= 0.6:
        return "date"

    return "string"


def _coerce_value(value: Any, target_type: str) -> tuple[bool, Any, str | None, str | None]:
    """Convert a cleaned value according to the column's inferred type.

    Returns (is_valid, coerced_value, warning_note, date_format_tag).
    """
    if value is None:
        return True, None, None, None

    if target_type == "boolean":
        ok, parsed_bool = _try_parse_bool(value)
        return (True, parsed_bool, None, None) if ok else (False, value, None, None)

    if target_type == "integer":
        ok, parsed_int, reformatted = _try_parse_int(value)
        note = "Normalized integer formatting" if ok and reformatted else None
        return (True, parsed_int, note, None) if ok else (False, value, None, None)

    if target_type == "float":
        ok, parsed_float, reformatted = _try_parse_float(value)
        note = "Normalized numeric/currency formatting" if ok and reformatted else None
        return (True, parsed_float, note, None) if ok else (False, value, None, None)

    if target_type == "date":
        ok, parsed_date, date_tag = _try_parse_date(value)
        note = "Normalized date to ISO YYYY-MM-DD" if ok and date_tag != "iso_date" else None
        return (True, parsed_date, note, date_tag) if ok else (False, value, None, None)

    return True, str(value), None, None


class ETLPipeline:
    """Orchestrates column normalization, cleaning, validation, deduplication, and profiling."""

    def process(self, dataset: ExtractedDataset) -> PipelineResult:
        """Transform and validate an ExtractedDataset without discarding rows silently."""
        seen_columns: set[str] = set()
        column_mapping: dict[str, str] = {}
        normalized_columns: list[str] = []
        formatting_issues: list[str] = list(dataset.parse_warnings)

        for idx, orig_col in enumerate(dataset.columns):
            norm_col = normalize_column_name(orig_col, idx, seen_columns)
            column_mapping[orig_col] = norm_col
            normalized_columns.append(norm_col)
            clean_orig = "" if orig_col.startswith("__empty_col_") else orig_col
            if clean_orig != norm_col:
                formatting_issues.append(
                    f"Column header '{clean_orig or '(blank)'}' normalized to '{norm_col}'."
                )

        # Clean rows and reject completely empty rows while preserving raw content.
        cleaned_rows: list[tuple[int, dict[str, Any], dict[str, Any], int]] = []
        rejected_rows: list[RejectedRowDetail] = []
        whitespace_cleanups = 0

        for idx, raw_row in enumerate(dataset.rows, start=1):
            cleaned_dict: dict[str, Any] = {}
            row_ws_count = 0
            for orig_col, norm_col in zip(dataset.columns, normalized_columns, strict=True):
                cleaned_val, ws_changed = _clean_cell_value(raw_row.get(orig_col))
                cleaned_dict[norm_col] = cleaned_val
                if ws_changed:
                    row_ws_count += 1

            if all(val is None for val in cleaned_dict.values()):
                rejected_rows.append(
                    RejectedRowDetail(
                        row_number=idx,
                        reasons=["Empty row with no values."],
                        raw_content=dict(raw_row),
                    )
                )
                continue

            whitespace_cleanups += row_ws_count
            cleaned_rows.append((idx, cleaned_dict, dict(raw_row), row_ws_count))

        if whitespace_cleanups > 0:
            formatting_issues.append(
                f"Trimmed/collapsed extraneous whitespace in {whitespace_cleanups} cell(s)."
            )

        # Infer column types across non-empty rows.
        inferred_types: dict[str, str] = {}
        for norm_col in normalized_columns:
            col_values = [row_dict[norm_col] for _, row_dict, _, _ in cleaned_rows]
            inferred_types[norm_col] = _infer_column_type(col_values)

        # Validate & coerce values per row, tracking type errors & date format consistency.
        type_error_counts: dict[str, int] = {col: 0 for col in normalized_columns}
        date_tags_per_col: dict[str, set[str]] = {col: set() for col in normalized_columns}
        evaluated_cells = 0
        total_type_errors = 0
        reformatted_cells = 0

        candidate_valid: list[tuple[int, dict[str, Any], dict[str, Any], list[str]]] = []

        for row_num, cleaned_dict, raw_row, row_ws_count in cleaned_rows:
            row_errors: list[str] = []
            row_warnings: list[str] = []
            if row_ws_count > 0:
                row_warnings.append(f"Cleaned extraneous whitespace in {row_ws_count} field(s).")

            coerced_dict: dict[str, Any] = {}
            for norm_col in normalized_columns:
                val = cleaned_dict[norm_col]
                target_type = inferred_types[norm_col]
                if val is not None:
                    evaluated_cells += 1
                ok, coerced_val, note, date_tag = _coerce_value(val, target_type)
                if not ok:
                    type_error_counts[norm_col] += 1
                    total_type_errors += 1
                    row_errors.append(f"Column '{norm_col}' expected {target_type}, got {val!r}.")
                else:
                    coerced_dict[norm_col] = coerced_val
                    if note is not None:
                        reformatted_cells += 1
                        if note not in row_warnings:
                            row_warnings.append(note)
                    if date_tag is not None:
                        date_tags_per_col[norm_col].add(date_tag)

            if row_errors:
                rejected_rows.append(
                    RejectedRowDetail(
                        row_number=row_num,
                        reasons=row_errors,
                        raw_content=raw_row,
                    )
                )
            else:
                candidate_valid.append((row_num, coerced_dict, raw_row, row_warnings))

        for norm_col, tags in date_tags_per_col.items():
            if len(tags) > 1:
                tags_display = ", ".join(sorted(tags))
                formatting_issues.append(
                    f"Column '{norm_col}' contained mixed date formats ({tags_display}); "
                    "normalized to ISO YYYY-MM-DD."
                )
        if reformatted_cells > 0:
            formatting_issues.append(
                f"Standardized formatting in {reformatted_cells} numeric/date cell(s)."
            )

        # Detect duplicates among valid records and count missing values.
        seen_fingerprints: set[str] = set()
        valid_records: list[ProcessedRecord] = []
        duplicates_found = 0
        missing_values_count = 0

        for row_num, coerced_dict, raw_row, row_warnings in candidate_valid:
            missing_cols = [col for col, val in coerced_dict.items() if val is None]
            missing_values_count += len(missing_cols)
            if missing_cols:
                row_warnings.append(f"Missing values in: {', '.join(missing_cols)}.")

            fingerprint = json.dumps(coerced_dict, sort_keys=True, ensure_ascii=False, default=str)
            is_duplicate = fingerprint in seen_fingerprints
            if is_duplicate:
                duplicates_found += 1
                row_warnings.append("Duplicate record content detected.")
            else:
                seen_fingerprints.add(fingerprint)

            valid_records.append(
                ProcessedRecord(
                    row_number=row_num,
                    content=coerced_dict,
                    raw_content=raw_row,
                    is_duplicate=is_duplicate,
                    validation_warnings=row_warnings,
                )
            )

        # Build column profiles from validated records (or all rows if none valid).
        reverse_mapping = {norm: orig for orig, norm in column_mapping.items()}
        column_profiles: list[ColumnProfile] = []
        total_valid = len(valid_records)
        for norm_col in normalized_columns:
            col_vals = [rec.content[norm_col] for rec in valid_records]
            missing_col_count = sum(1 for v in col_vals if v is None)
            non_null_vals = [v for v in col_vals if v is not None]
            non_null_count = len(non_null_vals)
            distinct_count = len(
                {
                    json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)
                    for v in non_null_vals
                }
            )
            missing_rate = (
                round((missing_col_count / total_valid) * 100.0, 2) if total_valid > 0 else 0.0
            )
            orig_display = reverse_mapping[norm_col]
            if orig_display.startswith("__empty_col_"):
                orig_display = "(blank)"
            column_profiles.append(
                ColumnProfile(
                    column_name=norm_col,
                    original_name=orig_display,
                    inferred_type=inferred_types[norm_col],
                    non_null_count=non_null_count,
                    missing_count=missing_col_count,
                    missing_rate=missing_rate,
                    type_error_count=type_error_counts[norm_col],
                    distinct_count=distinct_count,
                )
            )

        records_received = len(dataset.rows)
        records_rejected = len(rejected_rows)
        rejected_rows.sort(key=lambda item: item.row_number)

        quality_report = compute_quality_report(
            records_received=records_received,
            records_valid=total_valid,
            records_rejected=records_rejected,
            duplicates_found=duplicates_found,
            missing_values_count=missing_values_count,
            formatting_issues_count=(
                len(formatting_issues) + whitespace_cleanups + reformatted_cells
            ),
            evaluated_cells=evaluated_cells,
            type_errors_count=total_type_errors,
            column_profiles=column_profiles,
        )

        return PipelineResult(
            file_type=dataset.file_type,
            original_filename=dataset.original_filename,
            file_size_bytes=dataset.file_size_bytes,
            available_sheets=dataset.available_sheets,
            selected_sheet=dataset.selected_sheet,
            columns=normalized_columns,
            original_columns=dataset.columns,
            column_mapping=column_mapping,
            records_received=records_received,
            records_valid=total_valid,
            records_rejected=records_rejected,
            duplicates_found=duplicates_found,
            missing_values_count=missing_values_count,
            formatting_issues=formatting_issues,
            valid_records=valid_records,
            rejected_rows=rejected_rows,
            quality_report=quality_report,
        )
