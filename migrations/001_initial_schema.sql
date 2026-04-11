-- 001_initial_schema.sql
-- OsMEN-OC initial database schema.
-- Applies to osmen database on osmen-core-postgres.
--
-- Run with:
--   podman exec -i osmen-core-postgres \
--     psql -U osmen -d osmen < migrations/001_initial_schema.sql
--
-- Idempotent: uses IF NOT EXISTS / CREATE OR REPLACE throughout.

-- ── Extensions ───────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector for embeddings

-- ── audit_trail ──────────────────────────────────────────────────────────────
-- Append-only log of every tool invocation outcome from the approval gate.

CREATE TABLE IF NOT EXISTS audit_trail (
    record_id       TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    risk_level      TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    outcome         TEXT NOT NULL CHECK (outcome IN ('approved', 'denied')),
    reason          TEXT NOT NULL DEFAULT '',
    parameters      JSONB NOT NULL DEFAULT '{}',
    correlation_id  TEXT,
    flagged_for_summary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_trail_agent_id
    ON audit_trail (agent_id);

CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at
    ON audit_trail (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_trail_flagged
    ON audit_trail (flagged_for_summary)
    WHERE flagged_for_summary = TRUE;

-- ── audit_archive ────────────────────────────────────────────────────────────
-- Compressed destination for records older than retention period.
-- Schema mirrors audit_trail exactly (INSERT ... SELECT * FROM audit_trail).

CREATE TABLE IF NOT EXISTS audit_archive (
    record_id       TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    risk_level      TEXT NOT NULL,
    outcome         TEXT NOT NULL,
    reason          TEXT NOT NULL DEFAULT '',
    parameters      JSONB NOT NULL DEFAULT '{}',
    correlation_id  TEXT,
    flagged_for_summary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_archive_created_at
    ON audit_archive (created_at DESC);

-- ── schema_version ───────────────────────────────────────────────────────────
-- Simple migration tracking (no alembic).

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description TEXT NOT NULL DEFAULT ''
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Initial schema: audit_trail, audit_archive, pgvector')
ON CONFLICT (version) DO NOTHING;
