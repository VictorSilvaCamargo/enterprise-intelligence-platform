# ADR-007: Hybrid Relational + JSONB Storage, Extensible ETL, and Alembic Migrations

## Status
Accepted

## Date
2026-11-21

## Context
Stage 2 introduces enterprise file ingestion (CSV, XLSX, JSON), ETL validation, quality profiling, and record exploration. Imported datasets have heterogeneous schemas across sources while sharing structured execution metadata, quality metrics, and audit requirements.

## Decision
1. **Hybrid Relational + JSONB Persistence (`data_sources`, `import_jobs`, `imported_records`):**
   - Store structured entity metadata, counts, statuses, timestamps, and foreign-key relationships in standard PostgreSQL relational columns with `CheckConstraint` guards.
   - Store variable record payloads in `imported_records.content` (`JSONB`) indexed with a GIN index (`ix_imported_records_content_gin`) alongside `imported_records.raw_content` (`JSONB`) to guarantee raw audit traceability.
2. **Alembic Async Migrations:**
   - Adopt Alembic configured with `asyncpg` and `Base.metadata` (inheriting deterministic Stage 1 naming conventions) to manage schema evolution reliably across local and containerized environments.
3. **Extensible Extractor + Two-Phase Preview/Confirm ETL Pipeline:**
   - Isolate format parsing behind `BaseFileExtractor` and `ExtractorRegistry`, decoupling extraction from `ETLPipeline` normalization, type inference, rejection tracking (zero silent drops), and duplicate fingerprinting.
   - Support stateless `POST /api/v1/data-sources/preview` before transactional `POST /api/v1/data-sources/import`.
4. **Transparent Weighted Quality Scoring:**
   - Compute and persist explicit quality dimensions using the formula:
     `overall_score = 0.35 * completeness_rate + 0.30 * validity_rate + 0.20 * uniqueness_rate + 0.15 * type_consistency_rate`.

## Alternatives Considered

### Pure EAV (Entity-Attribute-Value) Tables
- **Cons:** High join fan-out and slow paginated filtering over wide datasets.
- **Rejected:** PostgreSQL `JSONB` + GIN indexing delivers schema flexibility with fast relational filtering and simple queries.

### Dynamic DDL (`CREATE TABLE` per Upload)
- **Cons:** Unbounded schema proliferation, migration drift, and SQL injection risks.
- **Rejected:** Overly complex for Stage 2 multi-format ingestion.

## Consequences
- New file or connector types can be added by registering another `BaseFileExtractor` without rewriting `ETLPipeline` or database schemas.
- Future Stage 4 (RAG) and Stage 6 (BI) modules can read normalized `JSONB` records and `schema_metadata` directly from PostgreSQL.
