# ADR-001: Adopt Modular Monolith Architecture Instead of Initial Microservices

## Status
Accepted

## Date
2026-11-19

## Context
The Enterprise Intelligence Platform is planned to evolve across eight stages encompassing Data Integration, RAG Knowledge Hub, Multi-Agent Systems, Business Intelligence, and Workflow Automation. At Stage 1, domain boundaries are defined conceptually, but domain schemas and inter-service data access patterns are not yet finalized.

## Decision
Structure the backend as a **Modular Monolith** inside a single FastAPI codebase (`backend/app/`), enforcing internal separation via `core/`, `models/`, `repositories/`, `services/`, `schemas/`, `api/v1/`, and `modules/`, rather than splitting into separate microservices at Stage 1.

## Alternatives Considered

### Microservices from Day One
- **Pros:** Independent deployment units and language heterogeneity per service.
- **Cons:** Introduces premature network serialization overhead, distributed transactions, service discovery, duplicated config, and heavy local resource usage before domain boundaries are validated.
- **Rejected:** High operational complexity with zero immediate benefit at Stage 1.

### Unstructured Monolith (Flat MVC)
- **Pros:** Fastest initial file creation.
- **Cons:** Encourages tight coupling between routes, SQL queries, and business logic, making future extraction difficult.
- **Rejected:** Violates clean separation of responsibilities required for an 8-stage platform.

## Consequences
- Single backend container (`eip-backend`) and streamlined local debugging.
- Future modules (`data_integration`, `ai_knowledge_hub`, `ai_agents`, `business_intelligence`, `workflow_automation`) plug into `/api/v1` via `register_module_router()` without modifying core infrastructure.
- If a specific workload (such as heavy agent execution or ETL workers) later requires independent horizontal scaling, its isolated module boundary allows extraction into a dedicated worker or service with minimal refactoring.
