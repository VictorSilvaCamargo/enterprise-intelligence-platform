# Synthetic Sample Datasets — Stage 2

All files in this directory are **100% synthetic, fictional B2B datasets** created strictly for development, automated testing, and portfolio demonstration of the Enterprise Intelligence Platform.

- **Generator Script:** `backend/scripts/generate_sample_data.py` (deterministic `random.Random(42)`)
- **License / Provenance:** Original synthetic data generated locally; free of third-party license restrictions
- **Privacy Guarantee:** Contains **zero real personal data (PII)**, real customer records, or confidential business figures. All company names and identifiers are clearly marked as fictional/synthetic.

## Primary Datasets

| File | Format | Records | Purpose & Intentional Characteristics |
|---|---|---|---|
| `enterprise_sales_2026.csv` | CSV | 60 rows | Fictional B2B order transactions with trailing column whitespace (`Customer Name `), cell spacing inconsistencies, 2 duplicate rows, missing regions, `"N/A"` status sentinel, and mixed date formatting (`DD/MM/YYYY` + `YYYY-MM-DD`). |
| `enterprise_operations_2026.xlsx` | XLSX (2 sheets) | 40 + 30 rows | Multi-sheet Excel workbook (`Sales_Orders` and `Inventory_Stock`) exercising sheet selection, currency-formatted USD values (`$1,250.00`), mixed dates, and missing optional fields. |
| `enterprise_customers_2026.json` | JSON | 35 objects | Fictional B2B customer accounts exercising camelCase-to-`snake_case` key normalization, boolean/numeric type inference, missing region values, and 1 duplicate object. |

## Edge Case Fixtures (`edge_cases/`)

| File | Scenario Covered |
|---|---|
| `messy_sales_errors.csv` | Inconsistent/blank headers, invalid numeric token (`"INVALID_NUM"`), invalid calendar date (`"2026-99-99"`), empty row rejection, whitespace cleaning, and exact duplicate detection. |
| `empty_file.csv` | Zero-byte file validation error handling. |
| `invalid_structure.json` | Valid JSON syntax lacking a tabular array of record objects. |
