"""Unit tests for file extractors, ETL pipeline transformations, and quality scoring."""

from __future__ import annotations

import json
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.core.exceptions import (
    BadRequestError,
    PayloadTooLargeError,
    UnprocessableEntityError,
)
from app.modules.data_integration.extractors import ExtractorRegistry
from app.modules.data_integration.pipeline import ETLPipeline, normalize_column_name


def _make_xlsx_bytes(sheets: dict[str, list[list[object]]]) -> bytes:
    wb = Workbook()
    first = True
    for sheet_name, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet(title=sheet_name)
        if first and ws is not None:
            ws.title = sheet_name
            first = False
        if ws is not None:
            for row in rows:
                ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def test_normalize_column_name_handles_accents_camelcase_blanks_and_duplicates() -> None:
    seen: set[str] = set()
    assert normalize_column_name("  Customer Name ", 0, seen) == "customer_name"
    assert normalize_column_name("Preço Unitário (R$)", 1, seen) == "preco_unitario_r"
    assert normalize_column_name("annualContractUsd", 2, seen) == "annual_contract_usd"
    assert normalize_column_name("   ", 3, seen) == "column_4"
    assert normalize_column_name("Customer Name", 4, seen) == "customer_name_2"


def test_extractor_validates_extension_empty_and_oversized_files() -> None:
    registry = ExtractorRegistry()

    with pytest.raises(BadRequestError):
        registry.extract(filename="notes.txt", content=b"hello", max_size_bytes=1024)

    with pytest.raises(BadRequestError):
        registry.extract(filename="   ", content=b"a,b\n1,2", max_size_bytes=1024)

    with pytest.raises(PayloadTooLargeError):
        registry.extract(filename="data.csv", content=b"x" * 2048, max_size_bytes=1024)

    with pytest.raises(UnprocessableEntityError):
        registry.extract(filename="empty.csv", content=b"", max_size_bytes=1024)


def test_csv_semicolon_delimiter_and_latin1_fallback() -> None:
    registry = ExtractorRegistry()
    csv_bytes = "Nome;Cidade;Valor\nJosé;São Paulo;100,50\nMaria;Rio;200,00\n".encode("latin-1")

    dataset = registry.extract(filename="vendas.csv", content=csv_bytes, max_size_bytes=1024 * 1024)
    assert dataset.file_type == "csv"
    assert len(dataset.rows) == 2
    assert any("latin-1" in w for w in dataset.parse_warnings)
    assert any("semicolon" in w for w in dataset.parse_warnings)

    result = ETLPipeline().process(dataset)
    assert result.records_valid == 2
    assert result.valid_records[0].content["valor"] == 100.5


def test_xlsx_multi_sheet_selection_and_invalid_sheet_error() -> None:
    registry = ExtractorRegistry()
    xlsx_bytes = _make_xlsx_bytes(
        {
            "Orders": [["Order ID", "Amount"], ["O-1", 100], ["O-2", 200]],
            "Inventory": [["SKU", "Qty"], ["SKU-1", 15], ["SKU-2", 30]],
        }
    )

    default_ds = registry.extract(
        filename="ops.xlsx", content=xlsx_bytes, max_size_bytes=1024 * 1024
    )
    assert default_ds.available_sheets == ["Orders", "Inventory"]
    assert default_ds.selected_sheet == "Orders"
    assert default_ds.rows[0]["Order ID"] == "O-1"

    second_ds = registry.extract(
        filename="ops.xlsx",
        content=xlsx_bytes,
        max_size_bytes=1024 * 1024,
        sheet_name="Inventory",
    )
    assert second_ds.selected_sheet == "Inventory"
    assert second_ds.rows[0]["SKU"] == "SKU-1"

    with pytest.raises(BadRequestError) as exc_info:
        registry.extract(
            filename="ops.xlsx",
            content=xlsx_bytes,
            max_size_bytes=1024 * 1024,
            sheet_name="NonExistent",
        )
    assert exc_info.value.details == {"available_sheets": ["Orders", "Inventory"]}


def test_json_wrapped_records_and_invalid_structures() -> None:
    registry = ExtractorRegistry()

    wrapped = json.dumps(
        {"records": [{"accountId": "A1", "isStrategic": True, "revenue": 1500.5}]}
    ).encode("utf-8")
    ds = registry.extract(filename="accounts.json", content=wrapped, max_size_bytes=1024 * 1024)
    result = ETLPipeline().process(ds)
    assert result.columns == ["account_id", "is_strategic", "revenue"]
    assert result.valid_records[0].content["is_strategic"] is True

    with pytest.raises(UnprocessableEntityError):
        registry.extract(
            filename="bad.json",
            content=b'{"not_records": "hello"}',
            max_size_bytes=1024 * 1024,
        )

    with pytest.raises(UnprocessableEntityError):
        registry.extract(
            filename="broken.json", content=b"{invalid json", max_size_bytes=1024 * 1024
        )


def test_pipeline_cleaning_type_validation_duplicates_and_quality_math() -> None:
    registry = ExtractorRegistry()
    csv_payload = (
        b"Order ID,Order Date ,Customer Name,Unit Price ($),Quantity\n"
        b'ORD-1,2026-05-01,  Acme   Corp ,"$1,200.50",2\n'
        b"ORD-2,15/05/2026,Northwind,250.00,4\n"
        b"ORD-3,2026-05-03,N/A,100.00,1\n"
        b"ORD-4,2026-05-04,Bad Numeric,NOT_A_NUMBER,3\n"
        b",,,,\n"
        b"ORD-1,2026-05-01,Acme Corp,$1200.50,2\n"
    )

    dataset = registry.extract(
        filename="orders.csv", content=csv_payload, max_size_bytes=1024 * 1024
    )
    result = ETLPipeline().process(dataset)

    assert result.records_received == 6
    assert result.records_valid == 4
    assert result.records_rejected == 2
    assert result.duplicates_found == 1
    assert result.missing_values_count == 1

    # Verify rejected rows preserve reasons and raw_content without silent discard.
    rejected_by_row = {item.row_number: item for item in result.rejected_rows}
    assert 4 in rejected_by_row
    assert any("float" in reason for reason in rejected_by_row[4].reasons)
    assert rejected_by_row[4].raw_content["Unit Price ($)"] == "NOT_A_NUMBER"
    assert 5 in rejected_by_row
    assert "Empty row" in rejected_by_row[5].reasons[0]

    # Verify cleaning, ISO date normalization, currency parsing, and duplicate flag.
    assert result.valid_records[0].content == {
        "order_id": "ORD-1",
        "order_date": "2026-05-01",
        "customer_name": "Acme Corp",
        "unit_price": 1200.5,
        "quantity": 2,
    }
    assert result.valid_records[0].raw_content["Customer Name"] == "  Acme   Corp "
    assert result.valid_records[1].content["order_date"] == "2026-05-15"
    assert result.valid_records[2].content["customer_name"] is None
    assert result.valid_records[3].is_duplicate is True

    # Verify exact quality scoring math.
    q = result.quality_report
    # Valid cells: 4 rows * 5 cols = 20; 1 missing -> completeness = 19/20 = 95.0%
    assert q.completeness_rate == 95.0
    # Validity: 4 / 6 = 66.67%
    assert q.validity_rate == 66.67
    # Uniqueness: (4 - 1) / 4 = 75.0%
    assert q.uniqueness_rate == 75.0
    # Evaluated non-null cells across non-empty rows: 24 cells, 1 type error -> 23/24 = 95.83%
    assert q.type_consistency_rate == 95.83
    expected_score = round(0.35 * 95.0 + 0.30 * 66.67 + 0.20 * 75.0 + 0.15 * 95.83, 2)
    assert q.overall_score == expected_score
