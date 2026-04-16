-- 003_orchestration.sql
-- Orchestration ledger tables for multi-agent workflow management.
-- Supports Mode A (cooperative) and Mode B (discussion) orchestration.

BEGIN;

-- ── Workflows ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS workflows (
    workflow_id     TEXT PRIMARY KEY,
    mode            TEXT NOT NULL DEFAULT 'cooperative'
                    CHECK (mode IN ('cooperative', 'discussion')),
    status          TEXT NOT NULL DEFAULT 'created'
                    CHECK (status IN ('created', 'running', 'suspended',
                                     'completed', 'failed', 'cancelled')),
    driver_agent_id TEXT,
    request         TEXT NOT NULL DEFAULT '',
    request_class   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    context         JSONB NOT NULL DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}',
    source_event_id TEXT,
    source_channel  TEXT,
    correlation_id  TEXT,
    final_synthesis TEXT,
    error           TEXT
);

CREATE INDEX IF NOT EXISTS idx_workflows_status
    ON workflows (status);
CREATE INDEX IF NOT EXISTS idx_workflows_created
    ON workflows (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflows_correlation
    ON workflows (correlation_id)
    WHERE correlation_id IS NOT NULL;

-- ── Work Items ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS work_items (
    item_id         TEXT PRIMARY KEY,
    workflow_id     TEXT NOT NULL REFERENCES workflows (workflow_id)
                    ON DELETE CASCADE,
    parent_item_id  TEXT REFERENCES work_items (item_id) ON DELETE SET NULL,
    agent_id        TEXT,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'assigned', 'in_progress',
                                     'blocked', 'completed', 'failed',
                                     'skipped')),
    priority        SMALLINT NOT NULL DEFAULT 5
                    CHECK (priority BETWEEN 1 AND 10),
    depends_on      TEXT[] NOT NULL DEFAULT '{}',
    result          TEXT,
    error           TEXT,
    assigned_at     TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_work_items_workflow
    ON work_items (workflow_id);
CREATE INDEX IF NOT EXISTS idx_work_items_status
    ON work_items (workflow_id, status);
CREATE INDEX IF NOT EXISTS idx_work_items_agent
    ON work_items (agent_id)
    WHERE agent_id IS NOT NULL;

-- ── Swarm Notes ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS swarm_notes (
    note_id         TEXT PRIMARY KEY,
    workflow_id     TEXT NOT NULL REFERENCES workflows (workflow_id)
                    ON DELETE CASCADE,
    agent_id        TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    note_type       TEXT NOT NULL DEFAULT 'observation',
    target_item_id  TEXT,
    target_claim_id TEXT,
    confidence      REAL NOT NULL DEFAULT 1.0
                    CHECK (confidence >= 0.0 AND confidence <= 1.0),
    embedding       vector(768),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_swarm_notes_workflow
    ON swarm_notes (workflow_id);
CREATE INDEX IF NOT EXISTS idx_swarm_notes_agent
    ON swarm_notes (agent_id);
CREATE INDEX IF NOT EXISTS idx_swarm_notes_type
    ON swarm_notes (workflow_id, note_type);

-- ── Claims (Mode B) ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS claims (
    claim_id            TEXT PRIMARY KEY,
    workflow_id         TEXT NOT NULL REFERENCES workflows (workflow_id)
                        ON DELETE CASCADE,
    agent_id            TEXT NOT NULL,
    portion_description TEXT NOT NULL DEFAULT '',
    analysis            TEXT NOT NULL DEFAULT '',
    evidence            TEXT[] NOT NULL DEFAULT '{}',
    status              TEXT NOT NULL DEFAULT 'claimed'
                        CHECK (status IN ('claimed', 'attacked', 'repaired',
                                         'accepted', 'rejected')),
    confidence          REAL NOT NULL DEFAULT 0.8
                        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    repaired_at         TIMESTAMPTZ,
    metadata            JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_claims_workflow
    ON claims (workflow_id);
CREATE INDEX IF NOT EXISTS idx_claims_status
    ON claims (workflow_id, status);

-- ── Receipts ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS receipts (
    receipt_id     TEXT PRIMARY KEY,
    workflow_id    TEXT NOT NULL REFERENCES workflows (workflow_id)
                   ON DELETE CASCADE,
    agent_id       TEXT NOT NULL,
    target_type    TEXT NOT NULL
                   CHECK (target_type IN ('work_item', 'claim')),
    target_id      TEXT NOT NULL,
    outcome        TEXT NOT NULL DEFAULT 'success'
                   CHECK (outcome IN ('success', 'failure', 'partial',
                                     'timeout')),
    result_summary TEXT NOT NULL DEFAULT '',
    error_detail   TEXT,
    duration_ms    INTEGER,
    model_used     TEXT,
    compute_backend TEXT,
    tokens_in      INTEGER,
    tokens_out     INTEGER,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata       JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_receipts_workflow
    ON receipts (workflow_id);
CREATE INDEX IF NOT EXISTS idx_receipts_target
    ON receipts (target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_receipts_created
    ON receipts (workflow_id, created_at DESC);

-- ── Decision Packets ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS decision_packets (
    packet_id    TEXT PRIMARY KEY,
    workflow_id  TEXT NOT NULL REFERENCES workflows (workflow_id)
                 ON DELETE CASCADE,
    agent_id     TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    trigger      TEXT NOT NULL DEFAULT '',
    alternatives JSONB NOT NULL DEFAULT '[]',
    chosen       TEXT NOT NULL DEFAULT '',
    reasoning    TEXT NOT NULL DEFAULT '',
    confidence   REAL NOT NULL DEFAULT 0.8
                 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata     JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_decisions_workflow
    ON decision_packets (workflow_id);

-- ── Interrupts ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS interrupts (
    interrupt_id     TEXT PRIMARY KEY,
    workflow_id      TEXT NOT NULL REFERENCES workflows (workflow_id)
                     ON DELETE CASCADE,
    kind             TEXT NOT NULL
                     CHECK (kind IN ('user_input', 'approval', 'timeout',
                                      'error', 'storm_detected',
                                      'novelty_low', 'velocity_high',
                                      'receipt_absent', 'external')),
    message          TEXT NOT NULL DEFAULT '',
    source_agent_id  TEXT,
    target_agent_id  TEXT,
    target_item_id   TEXT,
    context          JSONB NOT NULL DEFAULT '{}',
    resolution       TEXT
                     CHECK (resolution IS NULL
                            OR resolution IN ('resumed', 'escalated',
                                              'aborted')),
    resolved_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata         JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_interrupts_workflow
    ON interrupts (workflow_id);
CREATE INDEX IF NOT EXISTS idx_interrupts_unresolved
    ON interrupts (workflow_id, created_at)
    WHERE resolution IS NULL;

COMMIT;
