-- Redline initial schema
-- Raw incoming requests, computed consensus results, and rollup summaries
-- for TTL'd data, per the storage & lifecycle-management requirement.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS raw_clauses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_text  TEXT NOT NULL,
    context      JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_clauses_received_at ON raw_clauses (received_at);
CREATE INDEX IF NOT EXISTS idx_raw_clauses_context_gin ON raw_clauses USING GIN (context);

CREATE TABLE IF NOT EXISTS consensus_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_clause_id   UUID NOT NULL REFERENCES raw_clauses (id) ON DELETE CASCADE,
    result          JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_consensus_results_raw_clause_id ON consensus_results (raw_clause_id);
CREATE INDEX IF NOT EXISTS idx_consensus_results_result_gin ON consensus_results USING GIN (result);
CREATE INDEX IF NOT EXISTS idx_consensus_results_created_at ON consensus_results (created_at);

-- Rollup table populated by the TTL purge job before raw rows are deleted.
CREATE TABLE IF NOT EXISTS audit_rollups (
    period_start    TIMESTAMPTZ PRIMARY KEY,
    period_end      TIMESTAMPTZ NOT NULL,
    request_count   BIGINT NOT NULL DEFAULT 0,
    rollup          JSONB NOT NULL DEFAULT '{}'::jsonb
);
