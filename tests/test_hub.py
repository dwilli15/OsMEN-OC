"""Tests for MemoryHub — the unified pgvector memory system."""

from __future__ import annotations

import pytest

from core.memory.hub import ChunkResult, MemoryEntry, MemoryHub, _get_dsn

# asyncpg requires asyncio (not trio)
pytestmark = [pytest.mark.anyio]

@pytest.fixture(params=["asyncio"])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return request.param


# ── Unit tests (no DB required) ──────────────────────────────────────────────

def test_chunk_result_defaults() -> None:
    cr = ChunkResult(
        chunk_id="c1",
        document_id="d1",
        collection="docs",
        content="hello",
        similarity=0.9,
    )
    assert cr.chunk_id == "c1"
    assert cr.metadata == {}
    assert cr.similarity == 0.9


def test_memory_entry_defaults() -> None:
    me = MemoryEntry(
        entry_id="e1",
        agent_id="daily_brief",
        memory_type="fact",
        content="The sky is blue",
        importance=0.8,
    )
    assert me.entry_id == "e1"
    assert me.similarity == 0.0
    assert me.metadata == {}


def test_hub_not_connected_raises() -> None:
    hub = MemoryHub(dsn="postgresql://fake:fake@localhost/fake")
    with pytest.raises(RuntimeError, match="not connected"):
        _ = hub.pool


def test_get_dsn_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    # If env file doesn't exist, should return default
    dsn = _get_dsn()
    assert dsn.startswith("postgresql://")


# ── Integration tests (require live PostgreSQL) ──────────────────────────────

@pytest.mark.anyio
async def test_hub_connect_and_count() -> None:
    """Connect to the real PG instance, verify empty counts."""
    hub = MemoryHub()
    try:
        await hub.connect()
        count = await hub.count_chunks()
        assert isinstance(count, int)
        assert count >= 0
        entry_count = await hub.count_entries()
        assert isinstance(entry_count, int)
        assert entry_count >= 0
    finally:
        await hub.close()


@pytest.mark.anyio
async def test_hub_store_and_search_roundtrip() -> None:
    """Full roundtrip: register doc → store chunks → search → delete."""
    hub = MemoryHub()
    test_doc_id = "test-doc-roundtrip"
    test_chunk_id = "test-chunk-roundtrip"
    try:
        await hub.connect()

        # Register document
        await hub.register_document(
            document_id=test_doc_id,
            source_path="/tmp/test.md",
            source_type="markdown",
            collection="test_collection",
            title="roundtrip test",
            chunk_count=1,
        )

        # Store a chunk with a fake 768-dim embedding
        embedding = [0.1] * 768
        stored = await hub.store_chunks(
            "test_collection",
            test_doc_id,
            chunk_ids=[test_chunk_id],
            texts=["Deep learning with neural networks"],
            embeddings=[embedding],
            metadatas=[{"test": "true"}],
        )
        assert stored == 1

        # Verify count
        count = await hub.count_chunks("test_collection")
        assert count >= 1

        # Search by embedding
        results = await hub.search(
            "test_collection",
            embedding,
            n_results=5,
        )
        assert len(results) >= 1
        found = [r for r in results if r.chunk_id == test_chunk_id]
        assert len(found) == 1
        assert found[0].similarity > 0.99  # Same vector → near-perfect similarity
        assert found[0].content == "Deep learning with neural networks"
        assert found[0].document_id == test_doc_id

    finally:
        # Cleanup
        await hub.delete_document(test_doc_id)
        await hub.close()


@pytest.mark.anyio
async def test_hub_memory_entry_roundtrip() -> None:
    """Store and recall a structured memory entry."""
    hub = MemoryHub()
    try:
        await hub.connect()
        embedding = [0.2] * 768

        entry_id = await hub.store_memory(
            agent_id="test_agent",
            memory_type="fact",
            content="Python 3.13 supports pattern matching",
            embedding=embedding,
            importance=0.9,
            metadata={"source": "test"},
        )
        assert entry_id.startswith("mem-")

        # Recall
        results = await hub.recall(
            "test_agent",
            embedding,
            n_results=5,
        )
        assert len(results) >= 1
        found = [r for r in results if r.entry_id == entry_id]
        assert len(found) == 1
        assert found[0].content == "Python 3.13 supports pattern matching"
        assert found[0].importance == pytest.approx(0.9, abs=1e-6)

    finally:
        # Cleanup
        if entry_id:
            await hub.pool.execute(
                "DELETE FROM memory_entries WHERE entry_id = $1", entry_id
            )
        await hub.close()


@pytest.mark.anyio
async def test_hub_collections_list() -> None:
    """Verify collections() returns distinct collection names."""
    hub = MemoryHub()
    test_doc_id = "test-doc-collections"
    try:
        await hub.connect()

        await hub.register_document(
            document_id=test_doc_id,
            source_path="/tmp/collections_test.md",
            source_type="markdown",
            collection="alpha_collection",
        )
        await hub.store_chunks(
            "alpha_collection",
            test_doc_id,
            chunk_ids=["coll-test-chunk"],
            texts=["test content"],
            embeddings=[[0.5] * 768],
        )

        colls = await hub.collections()
        assert "alpha_collection" in colls

    finally:
        await hub.delete_document(test_doc_id)
        await hub.close()


@pytest.mark.anyio
async def test_hub_cross_collection_search() -> None:
    """Search across all collections (collection=None)."""
    hub = MemoryHub()
    test_ids = ["cross-doc-a", "cross-doc-b"]
    try:
        await hub.connect()

        # Seed two collections
        for i, doc_id in enumerate(test_ids):
            coll = f"cross_coll_{i}"
            await hub.register_document(
                document_id=doc_id,
                source_path=f"/tmp/{doc_id}.md",
                source_type="markdown",
                collection=coll,
            )
            emb = [0.3 + i * 0.1] * 768
            await hub.store_chunks(
                coll,
                doc_id,
                chunk_ids=[f"cross-chunk-{i}"],
                texts=[f"content for cross test {i}"],
                embeddings=[emb],
            )

        # Search across ALL collections
        results = await hub.search(
            None,  # no collection filter
            [0.3] * 768,
            n_results=10,
        )
        found_ids = {r.chunk_id for r in results}
        assert "cross-chunk-0" in found_ids

    finally:
        for doc_id in test_ids:
            await hub.delete_document(doc_id)
        await hub.close()
