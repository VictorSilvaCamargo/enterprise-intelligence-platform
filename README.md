# Enterprise Intelligence Platform

Modular enterprise platform designed to unify **data integration**, **AI knowledge hubs (RAG)**, **multi-agent orchestration**, **business intelligence**, and **workflow automation** inside a disciplined modular monolith foundation.

> **Current Stage:** Stage 2 — Data Engineering & Integration (`v0.2.0`)

## Key Capabilities (Stages 1–2)

- **Clean Modular Monolith Foundation:** Separate infrastructure core, persistence contracts, API boundaries, and domain modules (`app/modules/data_integration/`).
- **Multi-Format Data Ingestion & Preview:** Upload CSV, multi-sheet XLSX, and JSON files via `POST /api/v1/data-sources/preview` and confirm persistence via `POST /api/v1/data-sources/import`.
- **ETL & Data Quality Engine:** Column normalization (`snake_case`), whitespace/null cleaning, dominant type inference, explicit row rejection with raw traceability, duplicate detection, and documented weighted quality scoring (`35%` completeness + `30%` validity + `20%` uniqueness + `15%` type consistency).
- **PostgreSQL JSONB Persistence & Migrations:** Relational `data_sources`, `import_jobs`, and `imported_records` (`JSONB` + GIN index) managed via async Alembic migrations.
- **Data Management Web Interface:** React + TypeScript workspace with **Overview**, **Import Data**, **Data Sources**, and **Data Explorer** (search, date range, dynamic field filters, pagination, and raw record traceability modal).
- **Synthetic Development Datasets & Seed:** Reproducible fictional B2B datasets under `data/samples/` with idempotent seeding via `scripts/seed_data.py`.

## Platform Roadmap

| Stage | Scope | Status |
|---|---|---|
| **1. Foundation & Architecture** | Repository governance, FastAPI core, React/TypeScript/Vite SPA, PostgreSQL & Redis connectivity, Docker Compose, ADRs & docs | Completed |
| **2. Data Engineering & Integration** | CSV/XLSX/JSON ingestion, ETL validation, quality reports, PostgreSQL JSONB persistence, Alembic migrations, Data Management UI | Completed |
| **3. Document Intelligence & RAG** | Document ingestion, chunking, embeddings, semantic retrieval | Planned |
| **4. Analytical Intelligence** | KPI queries, analytical dashboards, forecasting | Planned |
| **5. Multi-Agent & Automation** | Specialized AI agents, tool registries, event-driven workflows | Planned |
| **6. Quality & Release Hardening** | CI/CD pipelines, telemetry, security hardening, final polish | Planned |

## Technology Stack

- **Backend:** Python `3.12`, FastAPI `0.165.0`, Uvicorn `0.54.0`, Pydantic `2.14.4`, Pydantic Settings `2.16.3`, SQLAlchemy `2.1.9`, asyncpg `0.32.0`, Alembic `1.20.1`, Pandas `3.1.1`, OpenPyXL `3.1.5`, python-multipart `0.0.34`, redis-py `8.1.0`
- **Frontend:** React `19.3.1`, TypeScript `5.9.3`, Vite `8.3.8`, Nginx `1.27-alpine`
- **Data & Cache:** PostgreSQL `17-alpine`, Redis `7-alpine`
- **Quality & Testing:** Ruff `0.17.5`, Mypy `2.4.1`, Pytest `9.2.0`, pytest-asyncio `1.5.0`, ESLint `10.15.0`, Prettier `3.10.1`, Vitest `5.1.1`
- **Containers:** Docker & Docker Compose (`v5.5.1`)

## Quick Start

1. Clone the repository and create your local `.env` file (never commit `.env`):
   ```powershell
   git clone https://github.com/VictorSilvaCamargo/enterprise-intelligence-platform.git
   cd enterprise-intelligence-platform
   Copy-Item .env.example .env
   ```
2. Build and start the entire stack:
   ```powershell
   docker compose up -d --build
   ```
3. Run database migrations and seed the synthetic sample datasets:
   ```powershell
   docker compose exec -T backend alembic upgrade head
   docker compose exec -T backend python -m scripts.seed_data
   ```
4. Verify all services and live health endpoints:
   ```powershell
   .\scripts\verify-stack.ps1
   ```
5. Open the interfaces in your browser:
   - **Frontend SPA (Platform Overview & Data Management):** [http://localhost:5173](http://localhost:5173)
   - **Backend OpenAPI (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Liveness Probe:** [http://localhost:8000/health](http://localhost:8000/health)
   - **Readiness Probe:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

## Stage 2 API Endpoints (`/api/v1`)

- `POST /api/v1/data-sources/preview` — Preview and validate CSV, XLSX (with optional `sheet_name`), or JSON uploads
- `POST /api/v1/data-sources/import` — Confirm and atomically persist data source, import job, and validated records
- `GET /api/v1/data-sources` — Paginated data sources listing with search and format filters
- `GET /api/v1/data-sources/{id}` — Data source metadata, schema, operational stats, and recent import jobs
- `GET /api/v1/data-sources/{id}/records` — Paginated record explorer with text search, period, and dynamic field filters
- `GET /api/v1/data-sources/{id}/records/{record_id}` — Detailed record inspection with cleaned and original raw content
- `GET /api/v1/data-sources/{id}/quality` — Data quality indicators, column profiles, and scoring methodology
- `GET /api/v1/import-jobs` & `GET /api/v1/import-jobs/{id}` — Paginated import execution history and job details
- `GET /api/v1/data-management/overview` — Global KPIs and recent execution summary

## Sample Data Provenance

All sample datasets in [`data/samples/`](./data/samples/README.md) (`enterprise_sales_2026.csv`, `enterprise_operations_2026.xlsx`, `enterprise_customers_2026.json`, and `edge_cases/`) are **100% synthetic, fictional B2B records** generated deterministically by `backend/scripts/generate_sample_data.py` (`seed=42`) with zero real personal or confidential data.

## Documentation

- **System Architecture & Extension Blueprint:** [`docs/architecture/overview.md`](./docs/architecture/overview.md)
- **Architecture Decision Records (ADR-001 to ADR-007):** [`docs/decisions/README.md`](./docs/decisions/README.md)
- **Setup, Execution & Troubleshooting:** [`docs/development/setup-and-run.md`](./docs/development/setup-and-run.md)
- **Git Workflow & Branch Protection Guide:** [`docs/development/git-workflow.md`](./docs/development/git-workflow.md)
