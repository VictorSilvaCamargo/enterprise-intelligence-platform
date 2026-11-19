# Enterprise Intelligence Platform

Modular enterprise platform designed to unify **data integration**, **AI knowledge hubs (RAG)**, **multi-agent orchestration**, **business intelligence**, and **workflow automation** inside a disciplined modular monolith foundation.

> **Current Stage:** Stage 1 — Foundation & Architecture (`v0.1.0`)

## Key Objectives (Stage 1)

- **Clean Modular Monolith Foundation:** Separate infrastructure core, persistence contracts, API boundaries, and planned domain extension points without premature microservices complexity.
- **Observable Runtime Probes:** FastAPI liveness (`GET /health`) and concurrent dependency readiness (`GET /health/ready`) validating PostgreSQL and Redis connectivity.
- **Enterprise SaaS Frontend Shell:** React + TypeScript + Vite SPA presenting the platform architecture and real-time backend/database/cache connectivity status.
- **Reproducible Infrastructure:** Docker Compose orchestration with persistent named volumes, network isolation (`eip_internal`, `eip_edge`), healthchecks, and Windows/Linux verification scripts.
- **Engineering Governance:** Ruff, Mypy strict mode, Pytest, ESLint, Prettier, Vitest, Pull Request/Issue templates, Conventional Commits, and Architecture Decision Records (ADRs).

## Platform Roadmap

| Stage | Scope | Status |
|---|---|---|
| **1. Foundation & Architecture** | Repository governance, FastAPI core, React/TypeScript/Vite SPA, PostgreSQL & Redis connectivity, Docker Compose, ADRs & docs | Completed |
| **2. Data Engineering & Integration** | Connectors, ingestion pipelines, schema contracts, persistence models | Planned |
| **3. Backend & Web Application** | Core domain APIs, authentication/RBAC, management UI | Planned |
| **4. Document Intelligence & RAG** | Document ingestion, chunking, embeddings, semantic retrieval | Planned |
| **5. Multi-Agent System** | Specialized AI agents, tool registries, orchestration runtime | Planned |
| **6. Business Intelligence & ML** | Analytical dashboards, predictive modeling, KPI views | Planned |
| **7. Process Automation** | Event-driven workflows, job queues, scheduling | Planned |
| **8. Quality, Observability & Delivery** | CI/CD pipelines, telemetry, security hardening, release automation | Planned |

## Technology Stack

- **Backend:** Python `3.12`, FastAPI `0.165.0`, Uvicorn `0.54.0`, Pydantic `2.14.4`, Pydantic Settings `2.16.3`, SQLAlchemy `2.1.9`, asyncpg `0.32.0`, redis-py `8.1.0`
- **Frontend:** React `19.3.1`, TypeScript `5.9.3`, Vite `8.3.8`, Nginx `1.27-alpine`
- **Data & Cache:** PostgreSQL `17-alpine`, Redis `7-alpine`
- **Quality & Testing:** Ruff `0.17.5`, Mypy `2.4.1`, Pytest `9.2.0`, ESLint `10.15.0`, Prettier `3.10.1`, Vitest `5.1.1`
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
3. Verify all services and live health endpoints:
   ```powershell
   .\scripts\verify-stack.ps1
   ```
4. Open the interfaces in your browser:
   - **Frontend SPA:** [http://localhost:5173](http://localhost:5173)
   - **Backend OpenAPI (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Liveness Probe:** [http://localhost:8000/health](http://localhost:8000/health)
   - **Readiness Probe:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

## Documentation

- **System Architecture & Extension Blueprint:** [`docs/architecture/overview.md`](./docs/architecture/overview.md)
- **Architecture Decision Records (ADR-001 to ADR-006):** [`docs/decisions/README.md`](./docs/decisions/README.md)
- **Setup, Execution & Troubleshooting:** [`docs/development/setup-and-run.md`](./docs/development/setup-and-run.md)
- **Git Workflow & Branch Protection Guide:** [`docs/development/git-workflow.md`](./docs/development/git-workflow.md)
