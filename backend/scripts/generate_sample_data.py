"""Deterministic generator for synthetic enterprise datasets and validation edge cases."""

from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = REPO_ROOT / "data" / "samples"
EDGE_CASES_DIR = SAMPLES_DIR / "edge_cases"

FICTIONAL_CUSTOMERS = [
    "SynthCorp Logistics",
    "Northwind Fictional Retail",
    "Meridian Demo Manufacturing",
    "Aurora Synthetic Systems",
    "Vanguard Mock Industries",
    "Cobalt Test Distribution",
    "Apex Fictional Energy",
    "Solstice Demo Healthcare",
    "Horizon Synthetic Foods",
    "Atlas Mock Aerospace",
]

REGIONS = ["North America", "Latin America", "Europe", "Asia-Pacific"]
PRODUCTS = [
    ("Cloud Telemetry Suite", "Software", 420.0),
    ("Industrial IoT Gateway", "Hardware", 890.0),
    ("Supply Chain Connector", "Integration", 650.0),
    ("Enterprise Audit Pack", "Compliance", 310.0),
    ("Edge Sensor Kit", "Hardware", 245.5),
]
STATUSES = ["Completed", "Processing", "Completed", "Completed", "Pending"]


def _build_sales_csv(rng: random.Random) -> Path:
    """Create enterprise_sales_2026.csv (~60 rows with duplicates and missing values)."""
    headers = [
        "Order ID",
        "Order Date",
        "Customer Name ",
        "Region",
        "Product",
        "Category",
        "Quantity",
        "Unit Price (USD)",
        "Total Value",
        "Status",
    ]
    base_date = date(2026, 1, 5)
    rows: list[list[object]] = []

    for idx in range(1, 59):
        product, category, unit_price = rng.choice(PRODUCTS)
        customer = rng.choice(FICTIONAL_CUSTOMERS)
        region: str | None = rng.choice(REGIONS)
        qty = rng.randint(1, 15)
        order_date = (base_date + timedelta(days=idx * 3)).isoformat()
        total_val = round(qty * unit_price, 2)
        status = rng.choice(STATUSES)

        # Inject controlled inconsistencies for ETL verification.
        if idx in (7, 23):
            customer = f"  {customer}  "
        if idx in (12, 34):
            region = ""
        if idx == 19:
            status = "N/A"
        if idx == 41:
            order_date = (base_date + timedelta(days=idx * 3)).strftime("%d/%m/%Y")
        if idx == 48:
            region = "  North   America  "

        rows.append(
            [
                f"ORD-2026-{idx:04d}",
                order_date,
                customer,
                region,
                product,
                category,
                qty,
                f"{unit_price:.2f}",
                f"{total_val:.2f}",
                status,
            ]
        )

    # Append 2 exact duplicate rows to exercise duplicate detection.
    rows.append(list(rows[2]))
    rows.append(list(rows[10]))

    target = SAMPLES_DIR / "enterprise_sales_2026.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return target


def _build_operations_xlsx(rng: random.Random) -> Path:
    """Create enterprise_operations_2026.xlsx with Sales_Orders and Inventory_Stock sheets."""
    base_date = date(2026, 2, 1)
    sales_orders: list[dict[str, object]] = []
    for idx in range(1, 41):
        product, category, price = rng.choice(PRODUCTS)
        qty = rng.randint(2, 20)
        order_dt = base_date + timedelta(days=idx * 2)
        date_str = order_dt.strftime("%d/%m/%Y") if idx % 6 == 0 else order_dt.isoformat()
        sales_orders.append(
            {
                "Order Reference": f"OPS-{idx:04d}",
                "Fulfillment Date": date_str,
                "Client Account": rng.choice(FICTIONAL_CUSTOMERS),
                "Region": None if idx in (9, 27) else rng.choice(REGIONS),
                "Item Name": product,
                "Division": category,
                "Units": qty,
                "Amount USD": f"${qty * price:,.2f}" if idx % 5 == 0 else round(qty * price, 2),
                "Order Status": rng.choice(["Dispatched", "Delivered", "Scheduled"]),
            }
        )

    inventory_rows: list[dict[str, object]] = []
    warehouses = ["WH-NORTH-01", "WH-LATAM-02", "WH-EU-03", "WH-APAC-04"]
    for idx in range(1, 31):
        product, category, price = PRODUCTS[idx % len(PRODUCTS)]
        stock_qty = rng.randint(15, 240)
        reorder_level = rng.randint(20, 60)
        inventory_rows.append(
            {
                "SKU Code": f"SYN-SKU-{idx:03d}",
                "Warehouse ID": warehouses[idx % len(warehouses)],
                "Product Name": product,
                "Category": category,
                "Stock On Hand": stock_qty,
                "Reorder Threshold": reorder_level,
                "Unit Cost": round(price * 0.62, 2),
                "Last Audit Date": (date(2026, 3, 1) + timedelta(days=idx)).isoformat(),
                "Stock Health": "Low" if stock_qty < reorder_level else "Healthy",
            }
        )

    target = SAMPLES_DIR / "enterprise_operations_2026.xlsx"
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        pd.DataFrame(sales_orders).to_excel(writer, sheet_name="Sales_Orders", index=False)
        pd.DataFrame(inventory_rows).to_excel(writer, sheet_name="Inventory_Stock", index=False)
    return target


def _build_customers_json(rng: random.Random) -> Path:
    """Create enterprise_customers_2026.json (~35 fictional B2B customer accounts)."""
    segments = ["Enterprise", "Mid-Market", "Growth"]
    accounts: list[dict[str, object]] = []
    base_date = date(2025, 1, 10)

    for idx in range(1, 35):
        company = f"{FICTIONAL_CUSTOMERS[idx % len(FICTIONAL_CUSTOMERS)]} #{idx:02d}"
        accounts.append(
            {
                "accountId": f"ACC-SYN-{idx:04d}",
                "companyName": company,
                "segment": rng.choice(segments),
                "region": None if idx in (8, 22) else rng.choice(REGIONS),
                "annualContractUsd": round(rng.uniform(18000.0, 240000.0), 2),
                "onboardingDate": (base_date + timedelta(days=idx * 14)).isoformat(),
                "isStrategic": idx % 3 == 0,
                "accountStatus": rng.choice(["Active", "Active", "Onboarding"]),
            }
        )

    # Inject 1 duplicate record.
    accounts.append(dict(accounts[4]))

    target = SAMPLES_DIR / "enterprise_customers_2026.json"
    with target.open("w", encoding="utf-8") as handle:
        json.dump(accounts, handle, indent=2)
    return target


def _build_edge_case_files() -> list[Path]:
    """Create edge-case fixtures covering validation errors, empty files, and bad JSON."""
    EDGE_CASES_DIR.mkdir(parents=True, exist_ok=True)

    messy_csv = EDGE_CASES_DIR / "messy_sales_errors.csv"
    with messy_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Order ID", "Order Date ", "Customer Name", "Unit Price ($)", ""])
        writer.writerow(["ERR-001", "2026-05-01", "  SynthCorp   Demo ", "$120.50", "Note A"])
        writer.writerow(["ERR-002", "15/05/2026", "Aurora Fictional", "250.00", "Note B"])
        writer.writerow(["ERR-003", "2026-05-03", "Northwind Demo", "INVALID_NUM", "Bad Price"])
        writer.writerow(["ERR-004", "2026-99-99", "Cobalt Mock", "310.00", "Bad Date"])
        writer.writerow(["ERR-005", "2026-05-05", "", "199.90", "Missing Customer"])
        writer.writerow(["", "", "", "", ""])
        writer.writerow(["ERR-001", "2026-05-01", "SynthCorp Demo", "$120.50", "Note A"])

    empty_csv = EDGE_CASES_DIR / "empty_file.csv"
    empty_csv.write_bytes(b"")

    invalid_json = EDGE_CASES_DIR / "invalid_structure.json"
    invalid_json.write_text(
        json.dumps(
            {
                "description": "Synthetic invalid non-tabular JSON fixture",
                "metadata_only": True,
                "count": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return [messy_csv, empty_csv, invalid_json]


def generate_all_samples() -> list[Path]:
    """Generate all deterministic Stage 2 synthetic datasets."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    generated = [
        _build_sales_csv(rng),
        _build_operations_xlsx(rng),
        _build_customers_json(rng),
    ]
    generated.extend(_build_edge_case_files())
    return generated


if __name__ == "__main__":
    paths = generate_all_samples()
    for file_path in paths:
        print(f"Generated: {file_path.relative_to(REPO_ROOT)}")
