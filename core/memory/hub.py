"""Unified memory hub — PostgreSQL + pgvector as the single source of truth.

Replaces ChromaDB for vector storage.  Keeps Redis for ephemeral working
memory.  All persistent memory flows through PostgreSQL.

Usage::

    hub = MemoryHub(dsn="postgresql://osmen:osmen@localhost:5432/osmen")
    await hub.connect()
    await hub.store_chunks("documents", doc_id, chunks, embeddings)
    results = await hub.search("documents", query_embedding, n=5)
    await hub.close()
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import asyncpg
from loguru import logger


def _get_dsn() -> str:
    """Read DSN from env file, falling back to POSTGRES_DSN env var."""
    dsn = os.environ.get("POSTGRES_DSN")
    if dsn:
        return dsn
    env_file = os.path.expanduser("~/.config/osmen/env")
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("POSTGRES_DSN="):
                    return line.split("=", 1)[1]
    except FileNotFoundError:
        pass
    return "postgresql://osmen:osmen@localhost:5432/osmen"


@dataclass
class ChunkResult:
    """A single vector search result."""

    chunk_id: str
    document_id: str | None
    collection: str
    content: str
    similarity: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryEntry:
    """A single structured memory entry."""

    entry_id: str
    agent_id: str
    memory_type: str
    content: str
    importance: float
    similarity: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryHub:
    """Unified interface to PostgreSQL-backed memory.

    Handles:
      - Document registration (``documents`` table)
      - Chunk storage with pgvector embeddings (``memory_chunks``)
      - Structured agent memory (``memory_entries``)
      - Semantic search with cosine similarity
      - Hybrid search (vector + full-text)

    Args:
        dsn: PostgreSQL connection string.  Falls back to
            ``~/.config/osmen/env`` then a localhost default.
        min_pool: Minimum connection pool size.
        max_pool: Maximum connection pool size.
    """

    def __init__(
        self,
        dsn: str | None = None,
        *,
        min_pool: int = 2,
        max_pool: int = 10,
    ) -> None:
        self._dsn = dsn or _get_dsn()
        self._min_pool = min_pool
        self._max_pool = max_pool
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Create the connection pool."""
        if self._pool is not None:
            return
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=self._min_pool,
            max_size=self._max_pool,
        )
        logger.info("MemoryHub connected to PostgreSQL (pool {}-{})",
                     self._min_pool, self._max_pool)

    async def close(self) -> None:
        """Drain and close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("MemoryHub disconnected")

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("MemoryHub not connected — call connect() first")
        return self._pool

    # ── Documents ─────────────────────────────────────────────────────────────

    async def register_document(
        self,
        *,
        document_id: str,
        source_path: str,
        source_type: str,
        collection: str = "documents",
        title: str = "",
        content_hash: str = "",
        chunk_count: int = 0,
        metadata: dict[str, Any] | None = None,
        ingested_by: str = "system",
    ) -> None:
        """Upsert a document record in the catalog."""
        import json

        await self.pool.execute(
            """
            INSERT INTO documents
                (document_id, source_path, source_type, collection, title,
                 content_hash, chunk_count, metadata, ingested_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
            ON CONFLICT (document_id) DO UPDATE SET
                source_path  = EXCLUDED.source_path,
                source_type  = EXCLUDED.source_type,
                collection   = EXCLUDED.collection,
                title        = EXCLUDED.title,
                content_hash = EXCLUDED.content_hash,
                chunk_count  = EXCLUDED.chunk_count,
                metadata     = EXCLUDED.metadata,
                ingested_by  = EXCLUDED.ingested_by,
                updated_at   = NOW()
            """,
            document_id,
            source_path,
            source_type,
            collection,
            title,
            content_hash,
            chunk_count,
            json.dumps(metadata or {}),
            ingested_by,
        )

    # ── Chunks ────────────────────────────────────────────────────────────────

    async def store_chunks(
        self,
        collection: str,
        document_id: str | None,
        *,
        chunk_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> int:
        """Store text chunks with embeddings.  Returns number stored."""
        import json

        if not chunk_ids:
            return 0
        metas = metadatas or [{}] * len(chunk_ids)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                stmt = await conn.prepare(
                    """
                    INSERT INTO memory_chunks
                        (chunk_id, document_id, collection, chunk_index,
                         content, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6::vector, $7::jsonb)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content   = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata  = EXCLUDED.metadata
                    """
                )
                for i, (cid, text, emb, meta) in enumerate(
                    zip(chunk_ids, texts, embeddings, metas, strict=True)
                ):
                    emb_str = "[" + ",".join(str(v) for v in emb) + "]"
                    await stmt.fetch(
                        cid, document_id, collection, i,
                        text, emb_str, json.dumps(meta),
                    )

        return len(chunk_ids)

    async def search(
        self,
        collection: str | None,
        query_embedding: list[float],
        *,
        n_results: int = 5,
        min_similarity: float = 0.0,
        where: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        """Cosine-similarity search across chunks.

        Args:
            collection: Filter to this collection, or None for all.
            query_embedding: 768-dim query vector.
            n_results: Max results to return.
            min_similarity: Minimum cosine similarity threshold.
            where: Optional metadata key-value filter (AND logic).
        """
        emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Build dynamic WHERE clause
        conditions: list[str] = []
        params: list[Any] = [emb_str]
        idx = 2

        if collection:
            conditions.append(f"collection = ${idx}")
            params.append(collection)
            idx += 1

        if where:
            for k, v in where.items():
                conditions.append(f"metadata->>'{k}' = ${idx}")
                params.append(str(v))
                idx += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                chunk_id,
                document_id,
                collection,
                content,
                1 - (embedding <=> $1::vector) AS similarity,
                metadata
            FROM memory_chunks
            {where_clause}
            ORDER BY embedding <=> $1::vector
            LIMIT {n_results}
        """
        rows = await self.pool.fetch(query, *params)
        results = []
        for row in rows:
            sim = float(row["similarity"])
            if sim >= min_similarity:
                import json
                meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else dict(row["metadata"]) if row["metadata"] else {}
                results.append(ChunkResult(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    collection=row["collection"],
                    content=row["content"],
                    similarity=sim,
                    metadata=meta,
                ))
        return results

    async def hybrid_search(
        self,
        collection: str | None,
        query_text: str,
        query_embedding: list[float],
        *,
        n_results: int = 5,
        vector_weight: float = 0.7,
    ) -> list[ChunkResult]:
        """Combined vector + full-text search using RRF.

        Reciprocal Rank Fusion: score = 1/(k+rank_vector) + 1/(k+rank_text).
        """
        emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        coll_filter = "WHERE collection = $3" if collection else ""

        query = f"""
            WITH vector_ranked AS (
                SELECT chunk_id, document_id, collection, content, metadata,
                       ROW_NUMBER() OVER (ORDER BY embedding <=> $1::vector) AS v_rank,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM memory_chunks
                {coll_filter}
                LIMIT 50
            ),
            text_ranked AS (
                SELECT chunk_id,
                       ROW_NUMBER() OVER (
                           ORDER BY ts_rank_cd(textsearch, plainto_tsquery('english', $2)) DESC
                       ) AS t_rank
                FROM memory_chunks
                {coll_filter}
                AND textsearch @@ plainto_tsquery('english', $2)
                LIMIT 50
            )
            SELECT
                v.chunk_id, v.document_id, v.collection, v.content,
                v.similarity, v.metadata,
                (
                    {vector_weight} * (1.0 / (60 + v.v_rank)) +
                    {1 - vector_weight} * (1.0 / (60 + COALESCE(t.t_rank, 999)))
                ) AS rrf_score
            FROM vector_ranked v
            LEFT JOIN text_ranked t ON v.chunk_id = t.chunk_id
            ORDER BY rrf_score DESC
            LIMIT $4
        """
        params: list[Any] = [emb_str, query_text]
        if collection:
            params.append(collection)
        params.append(n_results)

        rows = await self.pool.fetch(query, *params)
        results = []
        for row in rows:
            import json
            meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else dict(row["metadata"]) if row["metadata"] else {}
            results.append(ChunkResult(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                collection=row["collection"],
                content=row["content"],
                similarity=float(row["similarity"]),
                metadata=meta,
            ))
        return results

    # ── Memory entries ────────────────────────────────────────────────────────

    async def store_memory(
        self,
        *,
        agent_id: str,
        memory_type: str,
        content: str,
        embedding: list[float] | None = None,
        importance: float = 0.5,
        source_event: str | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: Any = None,
    ) -> str:
        """Store a structured memory entry.  Returns the entry_id."""
        import json

        emb_str = "[" + ",".join(str(v) for v in embedding) + "]" if embedding else None

        row = await self.pool.fetchrow(
            """
            INSERT INTO memory_entries
                (agent_id, memory_type, content, embedding,
                 importance, source_event, metadata, expires_at)
            VALUES ($1, $2, $3, $4::vector, $5, $6, $7::jsonb, $8)
            RETURNING entry_id
            """,
            agent_id,
            memory_type,
            content,
            emb_str,
            importance,
            source_event,
            json.dumps(metadata or {}),
            expires_at,
        )
        return row["entry_id"]

    async def recall(
        self,
        agent_id: str | None,
        query_embedding: list[float],
        *,
        n_results: int = 5,
        memory_types: list[str] | None = None,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """Semantic search across agent memory entries."""
        emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        conditions: list[str] = []
        params: list[Any] = [emb_str]
        idx = 2

        if agent_id:
            conditions.append(f"agent_id = ${idx}")
            params.append(agent_id)
            idx += 1

        if memory_types:
            placeholders = ", ".join(f"${idx + i}" for i in range(len(memory_types)))
            conditions.append(f"memory_type IN ({placeholders})")
            params.extend(memory_types)
            idx += len(memory_types)

        if min_importance > 0:
            conditions.append(f"importance >= ${idx}")
            params.append(min_importance)
            idx += 1

        # Exclude expired
        conditions.append("(expires_at IS NULL OR expires_at > NOW())")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                entry_id, agent_id, memory_type, content,
                importance, metadata,
                1 - (embedding <=> $1::vector) AS similarity
            FROM memory_entries
            {where_clause}
            ORDER BY embedding <=> $1::vector
            LIMIT {n_results}
        """
        rows = await self.pool.fetch(query, *params)
        results = []
        for row in rows:
            import json
            meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else dict(row["metadata"]) if row["metadata"] else {}
            results.append(MemoryEntry(
                entry_id=row["entry_id"],
                agent_id=row["agent_id"],
                memory_type=row["memory_type"],
                content=row["content"],
                importance=float(row["importance"]),
                similarity=float(row["similarity"]),
                metadata=meta,
            ))

        # Touch access count for returned entries
        if results:
            entry_ids = [r.entry_id for r in results]
            await self.pool.execute(
                """
                UPDATE memory_entries
                SET access_count = access_count + 1,
                    last_accessed = NOW()
                WHERE entry_id = ANY($1::text[])
                """,
                entry_ids,
            )

        return results

    # ── Deletion ──────────────────────────────────────────────────────────────

    async def delete_document(self, document_id: str) -> int:
        """Delete a document and all its chunks.  Returns chunk count deleted."""
        result = await self.pool.execute(
            "DELETE FROM memory_chunks WHERE document_id = $1", document_id
        )
        await self.pool.execute(
            "DELETE FROM documents WHERE document_id = $1", document_id
        )
        return int(result.split()[-1])

    async def delete_chunks(self, chunk_ids: list[str]) -> int:
        """Delete specific chunks by ID."""
        result = await self.pool.execute(
            "DELETE FROM memory_chunks WHERE chunk_id = ANY($1::text[])",
            chunk_ids,
        )
        return int(result.split()[-1])

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def count_chunks(self, collection: str | None = None) -> int:
        """Count chunks, optionally filtered by collection."""
        if collection:
            row = await self.pool.fetchrow(
                "SELECT COUNT(*) AS n FROM memory_chunks WHERE collection = $1",
                collection,
            )
        else:
            row = await self.pool.fetchrow(
                "SELECT COUNT(*) AS n FROM memory_chunks",
            )
        return int(row["n"])

    async def count_entries(self, agent_id: str | None = None) -> int:
        """Count memory entries, optionally filtered by agent."""
        if agent_id:
            row = await self.pool.fetchrow(
                "SELECT COUNT(*) AS n FROM memory_entries WHERE agent_id = $1",
                agent_id,
            )
        else:
            row = await self.pool.fetchrow(
                "SELECT COUNT(*) AS n FROM memory_entries",
            )
        return int(row["n"])

    async def collections(self) -> list[str]:
        """List all distinct collection names."""
        rows = await self.pool.fetch(
            "SELECT DISTINCT collection FROM memory_chunks ORDER BY collection"
        )
        return [row["collection"] for row in rows]
