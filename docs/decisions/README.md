# Architecture Decision Records (ADRs)

This directory captures the architectural decisions made during the construction of the **Enterprise Intelligence Platform**. Each record documents the context, chosen decision, considered alternatives, and trade-offs so future contributors understand *why* the platform is structured this way.

## Decision Lifecycle

```text
Proposed ──▶ Accepted ──▶ Deprecated / Superseded by ADR-XXX
```

## Index

| ID | Decision | Status | Date |
|---|---|---|---|
| [ADR-001](./ADR-001-modular-monolith-architecture.md) | Adopt Modular Monolith Architecture Instead of Initial Microservices | Accepted | 2026-11-19 |
| [ADR-002](./ADR-002-fastapi-backend.md) | Use Python and FastAPI for the Backend API | Accepted | 2026-11-19 |
| [ADR-003](./ADR-003-postgresql-primary-database.md) | Use PostgreSQL as the Primary Relational Database | Accepted | 2026-11-19 |
| [ADR-004](./ADR-004-redis-cache-and-queue-infrastructure.md) | Use Redis for Caching and Future Queue Infrastructure | Accepted | 2026-11-19 |
| [ADR-005](./ADR-005-react-typescript-vite-frontend.md) | Use React, TypeScript, and Vite for the Frontend Application | Accepted | 2026-11-19 |
| [ADR-006](./ADR-006-docker-compose-local-infrastructure.md) | Use Docker Compose for Reproducible Local Development Infrastructure | Accepted | 2026-11-19 |
