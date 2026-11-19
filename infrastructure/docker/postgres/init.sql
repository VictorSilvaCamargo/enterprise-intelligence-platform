-- Stage 1 PostgreSQL initialization script.
-- Domain tables and migrations are intentionally deferred to Stage 2.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
