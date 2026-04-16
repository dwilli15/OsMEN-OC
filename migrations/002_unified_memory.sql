-- 002_unified_memory.sql
-- Unified memory hub: documents, chunks with pgvector embeddings,
-- structured memory entries, and full-text search.
--
-- Run with:
--   podman exec -i osmen-core-postgres \
--     psql -U osmen -d osmen < migrations/002_unified_memory.sql
--
-- Idempotent: uses IF NOT EXISTS throughout.

-- ── documents ────────────────────────────────────────────────────────────────
-- Central catalog of every ingested source (files, URLs, notes, transcripts).
-- Every chunk links back here via document_id.

CREATE TABLE IF NOT EXISTS documents (
    document_id     TEXT PRIMARY KEY,
    source_path     TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK (source_type IN (
        'markdown', 'plain_text', 'html', 'pdf', 'epub',
        'url', 'note', 'transcript', 'siyuan', 'obsidian'
    )),
    collection      TEXT NOT NULL DEFAULT 'documents',
    title           TEXT NOT NULL DEFAULT '',
    content_hash    TEXT NOT NULL DEFAULT '',
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    metadata        JSONB NOT NULL DEFAULT '{}',
    ingested_by     TEXT NOT NULL DEFAULT 'system',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_collection
    ON documents (collection);

CREATE INDEX IF NOT EXISTS idx_documents_source_type
    ON documents (source_type);

CREATE INDEX IF NOT EXISTS idx_documents_ingested_by
    ON documents (ingested_by);

CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON documents (created_at DESC);

-- ── memory_chunks ────────────────────────────────────────────────────────────
-- Every piece of text that has been chunked and embedded.
-- This replaces ChromaDB collections entirely.
-- The 'collection' column replaces ChromaDB's separate collections concept.

CREATE TABLE IF NOT EXISTS memory_chunks (
    chunk_id        TEXT PRIMARY KEY,
    document_id     TEXT REFERENCES documents(document_id) ON DELETE CASCADE,
    collection      TEXT NOT NULL DEFAULT 'documents',
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    content         TEXT NOT NULL,
    embedding       vector(768),
    metadata        JSONB NOT NULL DEFAULT '{}',
    -- Full-text search vector, auto-populated by trigger
    textsearch      tsvector GENERATED ALWAYS AS (
        to_tsvector('english', content)
    ) STORED,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_cosine
    ON memory_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_chunks_textsearch
    ON memory_chunks USING gin (textsearch);

-- Filter by collection (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_chunks_collection
    ON memory_chunks (collection);

-- Filter by document
CREATE INDEX IF NOT EXISTS idx_chunks_document_id
    ON memory_chunks (document_id);

-- ── memory_entries ───────────────────────────────────────────────────────────
-- Structured agent memory: facts, observations, decisions, context.
-- Promoted from Redis working memory when deemed worth keeping.

CREATE TABLE IF NOT EXISTS memory_entries (
    entry_id        TEXT PRIMARY KEY DEFAULT 'mem-' || gen_random_uuid()::text,
    agent_id        TEXT NOT NULL,
    memory_type     TEXT NOT NULL CHECK (memory_type IN (
        'fact', 'observation', 'decision', 'context',
        'preference', 'episode', 'learning'
    )),
    content         TEXT NOT NULL,
    embedding       vector(768),
    importance      REAL NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    access_count    INTEGER NOT NULL DEFAULT 0,
    last_accessed   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    source_event    TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Semantic search on memory entries
CREATE INDEX IF NOT EXISTS idx_entries_embedding_cosine
    ON memory_entries USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Agent-scoped queries
CREATE INDEX IF NOT EXISTS idx_entries_agent_id
    ON memory_entries (agent_id);

CREATE INDEX IF NOT EXISTS idx_entries_memory_type
    ON memory_entries (memory_type);

-- Decay: find stale entries
CREATE INDEX IF NOT EXISTS idx_entries_last_accessed
    ON memory_entries (last_accessed);

-- Expiration cleanup
CREATE INDEX IF NOT EXISTS idx_entries_expires_at
    ON memory_entries (expires_at)
    WHERE expires_at IS NOT NULL;

-- ── Helper views ─────────────────────────────────────────────────────────────

-- Cross-collection chunk search with document context
CREATE OR REPLACE VIEW v_chunks_with_source AS
SELECT
    mc.chunk_id,
    mc.collection,
    mc.chunk_index,
    mc.content,
    mc.embedding,
    mc.metadata AS chunk_metadata,
    mc.created_at AS chunk_created_at,
    d.document_id,
    d.source_path,
    d.source_type,
    d.title AS document_title,
    d.ingested_by,
    d.created_at AS document_created_at
FROM memory_chunks mc
LEFT JOIN documents d ON mc.document_id = d.document_id;

-- ── Version tracking ─────────────────────────────────────────────────────────

INSERT INTO schema_version (version, description)
VALUES (2, 'Unified memory: documents, memory_chunks (pgvector), memory_entries, full-text search')
ON CONFLICT (version) DO NOTHING;
