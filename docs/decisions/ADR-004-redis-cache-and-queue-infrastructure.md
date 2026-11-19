# ADR-004: Use Redis for Caching and Future Queue Infrastructure

## Status
Accepted

## Date
2026-11-19

## Context
Upcoming platform stages require fast ephemeral caching, rate-limiting/session state, pub/sub messaging, and asynchronous background job queues for document ingestion (Stage 4), multi-agent runs (Stage 5), and automated workflows (Stage 7).

## Decision
Include **Redis 7** (`redis:7-alpine`) with Append-Only File persistence (`--appendonly yes`) and wire `redis.asyncio` (`RedisManager`) into the FastAPI lifespan and `/health/ready` probe from Stage 1.

## Alternatives Considered

### RabbitMQ / Apache Kafka in Stage 1
- **Pros:** Dedicated enterprise message brokering and stream retention.
- **Cons:** Significant memory footprint and operational complexity before asynchronous workloads exist.
- **Rejected:** Overkill for Stage 1; Redis cleanly supports caching and lightweight queues first.

### In-Memory Python Dict / Local Cache Only
- **Pros:** Zero external process.
- **Cons:** State is lost on restart and cannot be shared across multiple worker processes.
- **Rejected:** Does not prepare the platform for multi-worker or background job execution.

## Consequences
- Redis readiness is verified alongside PostgreSQL via `GET /health/ready`.
- Named volume `eip_redis_data` preserves AOF/RDB snapshots across container restarts.
- `app.core.redis.get_redis_client` provides an immediate extension dependency for Stage 2+ caching and task queuing.
