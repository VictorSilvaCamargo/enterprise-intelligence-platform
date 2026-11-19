# ADR-002: Use Python and FastAPI for the Backend API

## Status
Accepted

## Date
2026-11-19

## Context
The platform requires a backend framework capable of serving low-latency REST APIs while naturally supporting upcoming stages heavy in data engineering (Stage 2), document processing/RAG (Stage 4), multi-agent orchestration (Stage 5), and machine learning (Stage 6).

## Decision
Use **Python 3.12** with **FastAPI**, **Pydantic v2**, and **Uvicorn**.

## Alternatives Considered

### Node.js (NestJS / Express)
- **Pros:** Shared TypeScript language with the frontend.
- **Cons:** Weaker native ecosystem for data pipelines, vector processing, scientific computing, and ML workloads compared to Python, which would force splitting AI/data services prematurely.
- **Rejected:** Python keeps the backend unified across API, data, and AI stages.

### Django + Django REST Framework
- **Pros:** Batteries-included admin and ORM.
- **Cons:** Sync-first legacy ergonomics, heavier boilerplate for async I/O and OpenAPI-first API design.
- **Rejected:** FastAPI provides native async ASGI support, Pydantic v2 integration, and automatic OpenAPI 3.1 documentation out of the box.

## Consequences
- Automatic interactive API documentation at `/docs` and `/redoc`.
- Strong static and runtime contracts using Python 3.12 type hints, `mypy --strict`, `ruff`, and Pydantic models.
- Clean dependency injection (`Depends`) and lifespan management for database and Redis pools.
