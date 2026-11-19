# ADR-006: Use Docker Compose for Reproducible Local Development Infrastructure

## Status
Accepted

## Date
2026-11-19

## Context
The primary development host runs Windows 11 with Antigravity and Docker Desktop, while target production runtimes are Linux containers. The full stack (PostgreSQL, Redis, FastAPI, React/Nginx) must start reliably with a single command and remain reproducible on any workstation.

## Decision
Standardize local and portfolio orchestration using **Docker Compose** (`docker-compose.yml`), multi-stage/non-root **Dockerfiles**, segmented bridge networks (`eip_internal`, `eip_edge`), named persistent volumes (`eip_postgres_data`, `eip_redis_data`), and explicit container healthchecks with `depends_on: condition: service_healthy`.

## Alternatives Considered

### Native Host-Only Installation of Postgres & Redis
- **Pros:** Slightly lower memory overhead than containers.
- **Cons:** Inconsistent service versions across Windows/macOS/Linux workstations and manual port/credential drift.
- **Rejected:** Fails the reproducibility requirement.

### Local Kubernetes (kind / minikube)
- **Pros:** Production-like Kubernetes manifests.
- **Cons:** High RAM/CPU overhead and steep setup friction for Stage 1 local development.
- **Rejected:** Premature complexity before deployment orchestration is needed in Stage 8.

## Consequences
- Anyone can boot the full stack via `docker compose up -d --build` after copying `.env.example` to `.env`.
- `.gitattributes` enforces LF line endings across container/source files so Windows hosts do not introduce CRLF issues inside Linux containers.
- Container healthchecks guarantee deterministic startup ordering (`postgres` & `redis` -> `backend` -> `frontend`).
