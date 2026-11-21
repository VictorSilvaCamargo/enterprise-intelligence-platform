"""Extensible file extraction layer supporting CSV, XLSX, and JSON uploads."""

from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from app.core.exceptions import (
    BadRequestError,
    PayloadTooLargeError,
    UnprocessableEntityError,
)


def _to_json_safe(value: Any) -> Any:
    """Convert spreadsheet/Python native values into JSON-serializable primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _deduplicate_raw_headers(raw_headers: list[str]) -> tuple[list[str], list[str]]:
    """Ensure raw header keys are non-empty and unique before row dict construction."""
    seen: dict[str, int] = {}
    unique_headers: list[str] = []
    warnings: list[str] = []

    for index, header in enumerate(raw_headers):
        display_name = header if header.strip() else f"__empty_col_{index + 1}"
        count = seen.get(display_name, 0) + 1
        seen[display_name] = count
        if count > 1:
            suffixed = f"{display_name} ({count})"
            warnings.append(
                f"Duplicate raw column header '{header}' at position {index + 1} "
                f"disambiguated before normalization."
            )
            unique_headers.append(suffixed)
        else:
            unique_headers.append(display_name)

    return unique_headers, warnings


@dataclass(slots=True)
class ExtractedDataset:
    """Normalized intermediate structure returned by all file extractors."""

    file_type: str
    original_filename: str
    file_size_bytes: int
    columns: list[str]
    rows: list[dict[str, Any]]
    available_sheets: list[str] = field(default_factory=list)
    selected_sheet: str | None = None
    parse_warnings: list[str] = field(default_factory=list)


class BaseFileExtractor(ABC):
    """Contract for format-specific file extractors."""

    file_type: str
    supported_extensions: tuple[str, ...]

    @abstractmethod
    def extract(
        self,
        content: bytes,
        filename: str,
        *,
        sheet_name: str | None = None,
    ) -> ExtractedDataset:
        """Parse raw uploaded bytes into an ExtractedDataset."""


class CsvExtractor(BaseFileExtractor):
    """Extractor for UTF-8 / Latin-1 CSV files with delimiter auto-detection."""

    file_type = "csv"
    supported_extensions = (".csv",)

    @staticmethod
    def _decode_bytes(content: bytes) -> tuple[str, list[str]]:
        warnings: list[str] = []
        try:
            return content.decode("utf-8-sig"), warnings
        except UnicodeDecodeError:
            warnings.append("CSV file was not UTF-8 encoded; decoded using latin-1 fallback.")
            return content.decode("latin-1"), warnings

    @staticmethod
    def _detect_delimiter(text: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        first_non_empty = next((line for line in text.splitlines() if line.strip()), "")
        if not first_non_empty:
            return ",", warnings
        comma_count = first_non_empty.count(",")
        semicolon_count = first_non_empty.count(";")
        if semicolon_count > comma_count and semicolon_count > 0:
            warnings.append("Detected semicolon (';') delimiter in CSV file.")
            return ";", warnings
        return ",", warnings

    def extract(
        self,
        content: bytes,
        filename: str,
        *,
        sheet_name: str | None = None,
    ) -> ExtractedDataset:
        del sheet_name  # CSV files do not have multiple sheets.
        text, warnings = self._decode_bytes(content)
        if not text.strip():
            raise UnprocessableEntityError("CSV file is empty or contains only whitespace.")

        delimiter, delimiter_warnings = self._detect_delimiter(text)
        warnings.extend(delimiter_warnings)

        try:
            reader = csv.reader(StringIO(text), delimiter=delimiter)
            all_rows = list(reader)
        except csv.Error as exc:
            raise UnprocessableEntityError(f"Malformed CSV content: {exc}") from exc

        if not all_rows:
            raise UnprocessableEntityError("CSV file contains no header row.")

        raw_headers = [str(cell) for cell in all_rows[0]]
        if not any(cell.strip() for cell in raw_headers):
            raise UnprocessableEntityError("CSV header row is empty.")

        data_rows = all_rows[1:]
        if not data_rows:
            raise UnprocessableEntityError("CSV file contains headers but no data records.")

        unique_headers, header_warnings = _deduplicate_raw_headers(raw_headers)
        warnings.extend(header_warnings)

        rows: list[dict[str, Any]] = []
        expected_cols = len(unique_headers)
        ragged_rows = 0

        for raw_row in data_rows:
            if len(raw_row) > expected_cols:
                raise UnprocessableEntityError(
                    f"CSV structure error: found {len(raw_row)} columns in a data row, "
                    f"expected {expected_cols}."
                )
            if len(raw_row) < expected_cols and len(raw_row) > 0:
                ragged_rows += 1
            padded = list(raw_row) + [""] * (expected_cols - len(raw_row))
            rows.append(dict(zip(unique_headers, padded, strict=True)))

        if ragged_rows > 0:
            warnings.append(
                f"{ragged_rows} row(s) had fewer columns than the header "
                "and were padded as missing."
            )

        return ExtractedDataset(
            file_type=self.file_type,
            original_filename=filename,
            file_size_bytes=len(content),
            columns=unique_headers,
            rows=rows,
            parse_warnings=warnings,
        )


class XlsxExtractor(BaseFileExtractor):
    """Extractor for Microsoft Excel (.xlsx) workbooks with multi-sheet selection."""

    file_type = "xlsx"
    supported_extensions = (".xlsx",)

    def extract(
        self,
        content: bytes,
        filename: str,
        *,
        sheet_name: str | None = None,
    ) -> ExtractedDataset:
        try:
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        except (InvalidFileException, BadZipFile, OSError, KeyError, ValueError) as exc:
            raise UnprocessableEntityError(
                "Invalid or corrupted XLSX file. Ensure the file is a valid Excel workbook."
            ) from exc

        try:
            available_sheets = list(workbook.sheetnames)
            if not available_sheets:
                raise UnprocessableEntityError("XLSX workbook contains no worksheets.")

            if sheet_name is not None:
                if sheet_name not in available_sheets:
                    raise BadRequestError(
                        f"Worksheet '{sheet_name}' does not exist in workbook.",
                        details={"available_sheets": available_sheets},
                    )
                selected_sheet = sheet_name
            else:
                selected_sheet = available_sheets[0]

            worksheet = workbook[selected_sheet]
            raw_matrix = [list(row) for row in worksheet.iter_rows(values_only=True)]
        finally:
            workbook.close()

        if not raw_matrix:
            raise UnprocessableEntityError(f"Worksheet '{selected_sheet}' is empty.")

        raw_header_row = raw_matrix[0]
        while raw_header_row and raw_header_row[-1] is None:
            raw_header_row.pop()

        if not raw_header_row or not any(
            cell is not None and str(cell).strip() for cell in raw_header_row
        ):
            raise UnprocessableEntityError(
                f"Worksheet '{selected_sheet}' does not have a valid header row."
            )

        data_matrix = raw_matrix[1:]
        if not data_matrix:
            raise UnprocessableEntityError(
                f"Worksheet '{selected_sheet}' contains headers but no data records."
            )

        raw_headers = ["" if cell is None else str(cell) for cell in raw_header_row]
        unique_headers, warnings = _deduplicate_raw_headers(raw_headers)
        col_count = len(unique_headers)

        rows: list[dict[str, Any]] = []
        extra_cell_rows = 0
        for row_values in data_matrix:
            if len(row_values) > col_count and any(
                cell is not None for cell in row_values[col_count:]
            ):
                extra_cell_rows += 1
            sliced = list(row_values[:col_count])
            if len(sliced) < col_count:
                sliced.extend([None] * (col_count - len(sliced)))
            safe_values = [_to_json_safe(val) for val in sliced]
            rows.append(dict(zip(unique_headers, safe_values, strict=True)))

        if extra_cell_rows > 0:
            warnings.append(
                f"{extra_cell_rows} row(s) contained values beyond the header column range; "
                "extra unmapped cells were ignored."
            )

        return ExtractedDataset(
            file_type=self.file_type,
            original_filename=filename,
            file_size_bytes=len(content),
            columns=unique_headers,
            rows=rows,
            available_sheets=available_sheets,
            selected_sheet=selected_sheet,
            parse_warnings=warnings,
        )


class JsonExtractor(BaseFileExtractor):
    """Extractor for JSON arrays of objects or wrapped record collections."""

    file_type = "json"
    supported_extensions = (".json",)
    _WRAPPER_KEYS = ("records", "data", "items")

    def extract(
        self,
        content: bytes,
        filename: str,
        *,
        sheet_name: str | None = None,
    ) -> ExtractedDataset:
        del sheet_name
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UnprocessableEntityError("JSON file must be UTF-8 encoded.") from exc

        if not text.strip():
            raise UnprocessableEntityError("JSON file is empty.")

        try:
            payload: Any = json.loads(text)
        except json.JSONDecodeError as exc:
            raise UnprocessableEntityError(
                f"Invalid JSON syntax at line {exc.lineno}, column {exc.colno}: {exc.msg}."
            ) from exc

        warnings: list[str] = []
        records_obj: Any = payload
        if isinstance(payload, dict):
            matched_key = next(
                (key for key in self._WRAPPER_KEYS if isinstance(payload.get(key), list)),
                None,
            )
            if matched_key is None:
                raise UnprocessableEntityError(
                    "JSON object must contain a list under 'records', 'data', or 'items', "
                    "or the root must be a JSON array of objects."
                )
            records_obj = payload[matched_key]
            warnings.append(f"Extracted records from top-level JSON key '{matched_key}'.")

        if not isinstance(records_obj, list):
            raise UnprocessableEntityError(
                "JSON payload must be an array of record objects or an object "
                "wrapping a record list."
            )

        if not records_obj:
            raise UnprocessableEntityError("JSON dataset contains zero records.")

        if not all(isinstance(item, dict) for item in records_obj):
            raise UnprocessableEntityError(
                "Every item in the JSON array must be a key-value JSON object."
            )

        ordered_columns: list[str] = []
        seen_columns: set[str] = set()
        for item in records_obj:
            for key in item:
                key_str = str(key)
                if key_str not in seen_columns:
                    seen_columns.add(key_str)
                    ordered_columns.append(key_str)

        if not ordered_columns:
            raise UnprocessableEntityError("JSON record objects contain no fields.")

        rows: list[dict[str, Any]] = []
        for item in records_obj:
            row_dict = {
                col: _to_json_safe(item[col]) if col in item else None for col in ordered_columns
            }
            rows.append(row_dict)

        return ExtractedDataset(
            file_type=self.file_type,
            original_filename=filename,
            file_size_bytes=len(content),
            columns=ordered_columns,
            rows=rows,
            parse_warnings=warnings,
        )


class ExtractorRegistry:
    """Registry mapping allowed file extensions to format extractors."""

    def __init__(self, extractors: list[BaseFileExtractor] | None = None) -> None:
        registered = extractors or [CsvExtractor(), XlsxExtractor(), JsonExtractor()]
        self._by_extension: dict[str, BaseFileExtractor] = {}
        for extractor in registered:
            for ext in extractor.supported_extensions:
                self._by_extension[ext.lower()] = extractor

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        """Return all registered lowercase file extensions."""
        return tuple(sorted(self._by_extension.keys()))

    def register(self, extractor: BaseFileExtractor) -> None:
        """Register a new file extractor dynamically for future data source formats."""
        for ext in extractor.supported_extensions:
            self._by_extension[ext.lower()] = extractor

    def extract(
        self,
        *,
        filename: str | None,
        content: bytes,
        max_size_bytes: int,
        sheet_name: str | None = None,
    ) -> ExtractedDataset:
        """Validate upload constraints and dispatch to the matching extractor."""
        safe_name = (filename or "").strip()
        if not safe_name:
            raise BadRequestError("A valid filename is required for upload.")

        extension = Path(safe_name).suffix.lower()
        extractor = self._by_extension.get(extension)
        if extractor is None:
            raise BadRequestError(
                f"Unsupported file format '{extension or 'unknown'}'. "
                f"Allowed formats: {', '.join(self.supported_extensions)}.",
                error_code="UNSUPPORTED_FILE_FORMAT",
                details={"allowed_extensions": list(self.supported_extensions)},
            )

        if len(content) > max_size_bytes:
            max_mb = round(max_size_bytes / (1024 * 1024), 2)
            raise PayloadTooLargeError(
                f"File '{safe_name}' ({len(content)} bytes) exceeds the {max_mb} MB limit.",
                details={"max_size_bytes": max_size_bytes, "received_bytes": len(content)},
            )

        if len(content) == 0:
            raise UnprocessableEntityError(f"Uploaded file '{safe_name}' is empty (0 bytes).")

        return extractor.extract(content, safe_name, sheet_name=sheet_name)


default_extractor_registry = ExtractorRegistry()
