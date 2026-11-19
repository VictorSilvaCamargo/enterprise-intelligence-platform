# ADR-003: Use PostgreSQL as the Primary Relational Database

## Status
Accepted

## Date
2026-11-19

## Context
The platform will store structured enterprise metadata, pipeline execution records, workflow states, user/workspace configurations, and eventually vector embeddings or analytical aggregates. We need an ACID-compliant, open-source database suitable for both local Docker development and production workloads.

## Decision
Use **PostgreSQL 17** (`postgres:17-alpine`) accessed asynchronously via **SQLAlchemy 2.1 (`asyncio`)** and **`asyncpg`**.

## Alternatives Considered

### SQLite
- **Pros:** Zero external container needed.
- **Cons:** Limited concurrent write scalability, no production multi-container sharing, and lacks PostgreSQL extension ecosystem.
- **Rejected:** Unsuitable as the primary multi-service enterprise store.

### MySQL / MariaDB
- **Pros:** Widely available relational engine.
- **Cons:** Inferior JSONB indexing, CTE/analytical window feature parity, and lacks `pgvector` capability for Stage 4 RAG.
- **Rejected:** PostgreSQL covers both transactional and future vector/analytical needs.

## Consequences
- Named Docker volume (`eip_postgres_data`) guarantees durability across container restarts.
- `asyncpg` provides consistent async performance on both Windows hosts and Linux containers.
- SQLAlchemy `DeclarativeBase` with deterministic constraint naming conventions prepares the codebase cleanly for Alembic migrations in Stage 2.
