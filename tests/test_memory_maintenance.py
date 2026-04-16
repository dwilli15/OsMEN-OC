"""Tests for core.memory.maintenance — promotion, decay, expiration.

All database and Redis interactions are fully mocked.  Every test exercises
the *real* business logic (thresholds, decay formula, batched deletion, etc.)
with realistic inputs and assertions.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.memory.maintenance import (
    DECAY_FLOOR,
    DECAY_GRACE_DAYS,
    DECAY_HALF_LIFE_DAYS,
    EXPIRE_BATCH_SIZE,
    PROMOTION_ACCESS_THRESHOLD,
    PROMOTION_IMPORTANCE_FLOOR,
    REDIS_WORKING_MEMORY_PREFIX,
    _load_env,
    decay_stale_entries,
    expire_entries,
    promote_working_memory,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _wm_entry(
    *,
    content: str = "test memory content",
    importance: float = 0.5,
    access_count: int = 0,
    memory_type: str = "fact",
    created_at: str = "2026-04-15T00:00:00Z",
) -> str:
    """Build a realistic JSON working-memory entry value."""
    return json.dumps({
        "content": content,
        "importance": importance,
        "access_count": access_count,
        "type": memory_type,
        "created_at": created_at,
    })


def _make_mock_redis(*, entries: dict[str, dict[str, str]] | None = None) -> MagicMock:
    """Create a mock ``redis.asyncio`` client.

    *entries* maps Redis key → {field: JSON-value}.  Keys not present in
    *entries* return empty hashes from ``hgetall``.
    """
    redis = AsyncMock()
    entries = entries or {}

    # scan() returns (cursor, [matching_keys]) — fully paginated
    all_keys = list(entries.keys())
    redis.scan.return_value = (0, all_keys)

    # hgetall() returns the hash fields for a given key
    async def _hgetall(key: str) -> dict[str, str]:
        return entries.get(key, {})

    redis.hgetall.side_effect = _hgetall
    redis.hdel = AsyncMock()
    redis.ping = AsyncMock()
    return redis


def _make_mock_pg() -> tuple[MagicMock, AsyncMock]:
    """Create a mock ``asyncpg.Pool`` with a working async ``acquire()`` ctx.

    ``asyncpg.Pool.acquire()`` returns a *synchronous* context manager that
    yields an ``asyncpg.Connection``.  We use ``MagicMock`` for the pool so
    ``pool.acquire()`` is not auto-coroutined by ``AsyncMock``, then attach
    real ``__aenter__`` / ``__aexit__`` to the return value.

    Returns ``(pool, conn)`` where *conn* is the mock connection yielded by
    ``async with pool.acquire() as conn:``.
    """
    conn = AsyncMock()
    pool = MagicMock()

    # Build a real async context manager so ``async with pool.acquire()`` works
    @asynccontextmanager
    async def _acquire():
        yield conn

    # Use side_effect so each pool.acquire() returns a fresh context manager
    pool.acquire.side_effect = lambda: _acquire()
    pool.close = AsyncMock()
    return pool, conn


# ── Promotion Tests ──────────────────────────────────────────────────────────


class TestPromotionThresholds:
    """Verify that the promotion gate works: importance ≥ floor OR access ≥ threshold."""

    @pytest.mark.anyio
    async def test_skip_below_both_thresholds(self) -> None:
        """Below importance floor AND below access count → skipped."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": _wm_entry(importance=0.1, access_count=0)},
        })
        pg_pool, _ = _make_mock_pg()

        result = await promote_working_memory(redis, pg_pool)

        assert result["scanned"] == 1
        assert result["skipped"] == 1
        assert result["promoted"] == 0

    @pytest.mark.anyio
    async def test_promote_high_importance_low_access(self) -> None:
        """Above importance floor but zero accesses → promoted."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": _wm_entry(importance=0.8, access_count=0)},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            result = await promote_working_memory(redis, pg_pool)

        assert result["promoted"] == 1
        assert result["skipped"] == 0
        # Verify the INSERT was executed
        assert conn.execute.called
        # Verify Redis key was cleaned up
        redis.hdel.assert_called_once_with("wm:agent1", "e1")

    @pytest.mark.anyio
    async def test_promote_low_importance_high_access(self) -> None:
        """Below importance floor but above access threshold → promoted."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": _wm_entry(importance=0.2, access_count=5)},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            result = await promote_working_memory(redis, pg_pool)

        assert result["promoted"] == 1

    @pytest.mark.anyio
    async def test_promote_at_exact_floor(self) -> None:
        """Importance exactly at the floor → promoted (≥ check)."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": _wm_entry(importance=PROMOTION_IMPORTANCE_FLOOR, access_count=0)},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            result = await promote_working_memory(redis, pg_pool)

        assert result["promoted"] == 1

    @pytest.mark.anyio
    async def test_promote_at_exact_access_threshold(self) -> None:
        """Access count exactly at threshold → promoted (≥ check)."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": _wm_entry(importance=0.0, access_count=PROMOTION_ACCESS_THRESHOLD)},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            result = await promote_working_memory(redis, pg_pool)

        assert result["promoted"] == 1

    @pytest.mark.anyio
    async def test_skip_just_below_importance_floor(self) -> None:
        """Importance floor minus epsilon → skipped (unless access count saves it)."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": _wm_entry(importance=PROMOTION_IMPORTANCE_FLOOR - 0.01, access_count=0)},
        })
        pg_pool, _ = _make_mock_pg()

        result = await promote_working_memory(redis, pg_pool)

        assert result["skipped"] == 1
        assert result["promoted"] == 0


class TestPromotionContent:
    """Verify content-related promotion logic."""

    @pytest.mark.anyio
    async def test_skip_empty_content(self) -> None:
        """Whitespace-only content → skipped."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": _wm_entry(content="   \t\n")},
        })
        pg_pool, _ = _make_mock_pg()

        result = await promote_working_memory(redis, pg_pool)

        assert result["skipped"] == 1
        assert result["promoted"] == 0

    @pytest.mark.anyio
    async def test_skip_missing_content_key(self) -> None:
        """JSON without 'content' key → empty string → skipped."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": '{"importance": 0.9, "access_count": 10}'},
        })
        pg_pool, _ = _make_mock_pg()

        result = await promote_working_memory(redis, pg_pool)

        assert result["skipped"] == 1

    @pytest.mark.anyio
    async def test_handle_bad_json(self) -> None:
        """Malformed JSON → counted as error, not crash."""
        redis = _make_mock_redis(entries={
            "wm:agent1": {"e1": "not json{{{"},
        })
        pg_pool, _ = _make_mock_pg()

        result = await promote_working_memory(redis, pg_pool)

        assert result["errors"] == 1
        assert result["promoted"] == 0


class TestPromotionMemoryType:
    """Verify memory_type normalization against DB constraint."""

    VALID_TYPES = {"fact", "observation", "decision", "context", "preference", "episode", "learning"}

    @pytest.mark.anyio
    async def test_valid_type_passed_through(self) -> None:
        for valid_type in self.VALID_TYPES:
            redis = _make_mock_redis(entries={
                "wm:a": {"e": _wm_entry(importance=0.9, memory_type=valid_type)},
            })
            pg_pool, conn = _make_mock_pg()

            with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
                await promote_working_memory(redis, pg_pool)

            # $2 in the INSERT is memory_type (index 2 after SQL string)
            assert conn.execute.call_args[0][2] == valid_type

    @pytest.mark.anyio
    async def test_invalid_type_normalizes_to_context(self) -> None:
        redis = _make_mock_redis(entries={
            "wm:a": {"e": _wm_entry(importance=0.9, memory_type="bogus_type")},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            result = await promote_working_memory(redis, pg_pool)

        assert result["promoted"] == 1
        assert conn.execute.call_args[0][2] == "context"

    @pytest.mark.anyio
    async def test_missing_type_defaults_to_fact(self) -> None:
        """JSON without 'type' key → code does data.get("type", "fact")."""
        redis = _make_mock_redis(entries={
            "wm:a": {"e": '{"content": "hi", "importance": 0.9, "access_count": 0}'},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            result = await promote_working_memory(redis, pg_pool)

        assert result["promoted"] == 1
        assert conn.execute.call_args[0][2] == "fact"


class TestPromotionEmbedding:
    """Verify embedding generation and fallback."""

    @pytest.mark.anyio
    async def test_embedding_failure_still_promotes(self) -> None:
        """If Ollama embedding fails (returns None), promotion still proceeds with NULL embedding."""
        redis = _make_mock_redis(entries={
            "wm:a": {"e": _wm_entry(importance=0.9)},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=None):
            result = await promote_working_memory(redis, pg_pool)

        assert result["promoted"] == 1
        # $4 is the embedding parameter (index 4 after SQL string)
        assert conn.execute.call_args[0][4] is None

    @pytest.mark.anyio
    async def test_embedding_serialized_correctly(self) -> None:
        """Embedding list should be serialized as a bracket-delimited string."""
        embedding = [0.01, 0.02, 0.03]
        redis = _make_mock_redis(entries={
            "wm:a": {"e": _wm_entry(importance=0.9)},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=embedding):
            await promote_working_memory(redis, pg_pool)

        emb_param = conn.execute.call_args[0][4]
        assert emb_param == "[0.01,0.02,0.03]"


class TestPromotionRedis:
    """Verify Redis scanning and cleanup."""

    @pytest.mark.anyio
    async def test_no_wm_keys_returns_early(self) -> None:
        """No matching Redis keys → zero scanned, no DB activity."""
        redis = _make_mock_redis(entries={})
        pg_pool, _ = _make_mock_pg()

        result = await promote_working_memory(redis, pg_pool)

        assert result["scanned"] == 0
        assert result["promoted"] == 0

    @pytest.mark.anyio
    async def test_empty_hash_key_skipped(self) -> None:
        """WM key exists but hash is empty → no scan, no error."""
        redis = _make_mock_redis(entries={"wm:agent1": {}})
        pg_pool, _ = _make_mock_pg()

        result = await promote_working_memory(redis, pg_pool)

        assert result["scanned"] == 0

    @pytest.mark.anyio
    async def test_multiple_keys_and_entries(self) -> None:
        """Two agents, multiple entries each — counts aggregate correctly."""
        redis = _make_mock_redis(entries={
            "wm:alpha": {
                "e1": _wm_entry(importance=0.9, content="high importance"),
                "e2": _wm_entry(importance=0.1, access_count=0),  # skipped
            },
            "wm:beta": {
                "e3": _wm_entry(importance=0.1, access_count=5, content="high access"),
                "e4": '{"broken json',
            },
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            result = await promote_working_memory(redis, pg_pool)

        assert result["scanned"] == 4
        assert result["promoted"] == 2
        assert result["skipped"] == 1
        assert result["errors"] == 1

    @pytest.mark.anyio
    async def test_agent_id_extracted_from_key(self) -> None:
        """The agent_id in the INSERT should come from the Redis key prefix."""
        redis = _make_mock_redis(entries={
            "wm:my-special-agent": {"e1": _wm_entry(importance=0.9)},
        })
        pg_pool, conn = _make_mock_pg()

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            await promote_working_memory(redis, pg_pool)

        # $1 in INSERT is agent_id (index 1 after SQL string)
        assert conn.execute.call_args[0][1] == "my-special-agent"


class TestPromotionDryRun:
    """Verify dry-run mode does not write to DB or Redis."""

    @pytest.mark.anyio
    async def test_dry_run_no_insert_or_delete(self) -> None:
        redis = _make_mock_redis(entries={
            "wm:a": {"e1": _wm_entry(importance=0.9)},
        })
        pg_pool, conn = _make_mock_pg()

        result = await promote_working_memory(redis, pg_pool, dry_run=True)

        assert result["promoted"] == 0
        conn.execute.assert_not_called()
        redis.hdel.assert_not_called()


class TestPromotionDbError:
    """Verify DB errors are counted, not raised."""

    @pytest.mark.anyio
    async def test_insert_failure_counted(self) -> None:
        redis = _make_mock_redis(entries={
            "wm:a": {"e1": _wm_entry(importance=0.9)},
        })
        pg_pool, conn = _make_mock_pg()
        conn.execute.side_effect = Exception("connection reset")

        with patch("core.memory.maintenance._generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768):
            result = await promote_working_memory(redis, pg_pool)

        assert result["errors"] == 1
        assert result["promoted"] == 0
        # Redis key should NOT be deleted on failure
        redis.hdel.assert_not_called()


# ── Decay Tests ──────────────────────────────────────────────────────────────


class TestDecayImportance:
    """Verify the decay formula: ``importance *= 0.5 ^ (days / HALF_LIFE)``."""

    @pytest.mark.anyio
    async def test_decay_updates_importance(self) -> None:
        """A stale entry should have its importance reduced via the UPDATE."""
        pg_pool, conn = _make_mock_pg()

        conn.fetch.return_value = [
            {
                "entry_id": "mem-1",
                "importance": 0.8,
                "access_count": 1,
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=60),
                "created_at": datetime.now(timezone.utc) - timedelta(days=90),
            },
        ]

        result = await decay_stale_entries(pg_pool)

        assert result["decayed"] == 1
        # UPDATE memory_entries SET importance = $1 WHERE entry_id = $2
        update_call = conn.execute.call_args
        sql = update_call[0][0]
        new_importance = update_call[0][1]  # $1 = new importance
        entry_id = update_call[0][2]        # $2 = entry_id
        assert "UPDATE" in sql
        assert entry_id == "mem-1"
        assert 0 < new_importance < 0.8

    @pytest.mark.anyio
    async def test_decay_formula_accuracy(self) -> None:
        """Verify the exact decay factor is applied correctly."""
        pg_pool, conn = _make_mock_pg()

        days_ago = 30  # exactly one half-life
        conn.fetch.return_value = [
            {
                "entry_id": "mem-1",
                "importance": 1.0,
                "access_count": 1,
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=days_ago),
                "created_at": datetime.now(timezone.utc) - timedelta(days=100),
            },
        ]

        await decay_stale_entries(pg_pool)

        # $1 = new importance
        new_importance = conn.execute.call_args[0][1]
        expected = 1.0 * (0.5 ** (days_ago / DECAY_HALF_LIFE_DAYS))
        assert abs(new_importance - expected) < 1e-9, f"Expected {expected}, got {new_importance}"

    @pytest.mark.anyio
    async def test_no_decay_for_recent_entries(self) -> None:
        """Entries accessed within the half-life window are not in the query result."""
        pg_pool, conn = _make_mock_pg()

        # DB query filters by last_accessed < NOW - HALF_LIFE_DAYS, so recent
        # entries won't be returned.  Empty result = no work.
        conn.fetch.return_value = []

        result = await decay_stale_entries(pg_pool)

        assert result["decayed"] == 0
        assert result["removable"] == 0
        conn.execute.assert_not_called()


class TestDecayRemoval:
    """Verify entries below floor past grace period are removed."""

    @pytest.mark.anyio
    async def test_remove_floor_entry_past_grace(self) -> None:
        """Importance decays below floor AND age > grace → removable."""
        pg_pool, conn = _make_mock_pg()

        conn.fetch.return_value = [
            {
                "entry_id": "mem-old",
                "importance": 0.01,
                "access_count": 0,
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=120),
                "created_at": datetime.now(timezone.utc) - timedelta(days=200),
            },
        ]
        conn.execute.return_value = "DELETE 1"

        result = await decay_stale_entries(pg_pool)

        assert result["removable"] == 1
        # The DELETE uses ANY($1::text[])
        delete_call = conn.execute.call_args
        assert "DELETE FROM memory_entries" in delete_call[0][0]

    @pytest.mark.anyio
    async def test_keep_floor_entry_within_grace(self) -> None:
        """Importance below floor BUT age ≤ grace → NOT removable, still decayed."""
        pg_pool, conn = _make_mock_pg()

        conn.fetch.return_value = [
            {
                "entry_id": "mem-new",
                "importance": 0.01,
                "access_count": 0,
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=60),
                "created_at": datetime.now(timezone.utc) - timedelta(days=2),
            },
        ]

        result = await decay_stale_entries(pg_pool)

        assert result["removable"] == 0
        # But it still gets decayed (UPDATE)
        assert result["decayed"] == 1

    @pytest.mark.anyio
    async def test_multiple_removable_batched(self) -> None:
        """Multiple removable entries should be deleted in a single ANY() call."""
        pg_pool, conn = _make_mock_pg()

        conn.fetch.return_value = [
            {
                "entry_id": f"mem-{i}",
                "importance": 0.001,
                "access_count": 0,
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=180),
                "created_at": datetime.now(timezone.utc) - timedelta(days=300),
            }
            for i in range(5)
        ]
        conn.execute.return_value = "DELETE 5"

        result = await decay_stale_entries(pg_pool)

        assert result["removable"] == 5
        # The DELETE uses $1 = list of IDs
        delete_ids = conn.execute.call_args[0][1]
        assert len(delete_ids) == 5


class TestDecayDryRun:
    """Verify dry-run does not modify the database."""

    @pytest.mark.anyio
    async def test_dry_run_no_updates(self) -> None:
        pg_pool, conn = _make_mock_pg()

        conn.fetch.return_value = [
            {
                "entry_id": "mem-1",
                "importance": 0.5,
                "access_count": 1,
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=60),
                "created_at": datetime.now(timezone.utc) - timedelta(days=90),
            },
        ]

        result = await decay_stale_entries(pg_pool, dry_run=True)

        # dry_run logs but doesn't UPDATE or DELETE
        for call in conn.execute.call_args_list:
            sql = call[0][0] if call[0] else ""
            assert not sql.startswith("UPDATE"), f"Unexpected UPDATE in dry run: {sql}"
            assert not sql.startswith("DELETE"), f"Unexpected DELETE in dry run: {sql}"


class TestDecayErrors:
    """Verify DB errors are counted, not raised."""

    @pytest.mark.anyio
    async def test_update_failure_counted(self) -> None:
        pg_pool, conn = _make_mock_pg()

        conn.fetch.return_value = [
            {
                "entry_id": "mem-1",
                "importance": 0.8,
                "access_count": 1,
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=60),
                "created_at": datetime.now(timezone.utc) - timedelta(days=90),
            },
        ]
        conn.execute.side_effect = Exception(" deadlock")

        result = await decay_stale_entries(pg_pool)

        assert result["errors"] == 1
        assert result["decayed"] == 0

    @pytest.mark.anyio
    async def test_delete_failure_counted_per_entry(self) -> None:
        pg_pool, conn = _make_mock_pg()

        conn.fetch.return_value = [
            {
                "entry_id": f"mem-{i}",
                "importance": 0.001,
                "access_count": 0,
                "last_accessed": datetime.now(timezone.utc) - timedelta(days=200),
                "created_at": datetime.now(timezone.utc) - timedelta(days=400),
            }
            for i in range(3)
        ]
        conn.execute.side_effect = Exception("disk full")

        result = await decay_stale_entries(pg_pool)

        # The DELETE failure path increments errors by len(removable_ids)
        assert result["errors"] == 3


# ── Expiration Tests ─────────────────────────────────────────────────────────


class TestExpireEntries:
    """Verify timed-out entry removal."""

    @pytest.mark.anyio
    async def test_expire_deletes_entries(self) -> None:
        """Expired entries (expires_at < NOW) should be deleted."""
        pg_pool, conn = _make_mock_pg()
        conn.execute.return_value = "DELETE 3"

        result = await expire_entries(pg_pool)

        assert result["entries_expired"] == 3
        first_sql = conn.execute.call_args_list[0][0][0]
        assert "DELETE FROM memory_entries WHERE expires_at" in first_sql

    @pytest.mark.anyio
    async def test_expire_zero_entries(self) -> None:
        """No expired entries → count is 0."""
        pg_pool, conn = _make_mock_pg()
        conn.execute.return_value = "DELETE 0"

        result = await expire_entries(pg_pool)

        assert result["entries_expired"] == 0


class TestExpireOrphans:
    """Verify orphaned chunk removal."""

    @pytest.mark.anyio
    async def test_orphaned_chunks_deleted(self) -> None:
        """Chunks referencing non-existent documents should be deleted."""
        pg_pool, conn = _make_mock_pg()

        # First call: DELETE entries (returns 0).  Second call: DELETE chunks.
        conn.execute.side_effect = ["DELETE 0", "DELETE 5"]

        result = await expire_entries(pg_pool)

        assert result["chunks_orphaned"] == 5

    @pytest.mark.anyio
    async def test_orphaned_chunks_batched(self) -> None:
        """More orphans than EXPIRE_BATCH_SIZE should be looped."""
        pg_pool, conn = _make_mock_pg()

        # First loop deletes BATCH_SIZE, second loop deletes remainder
        conn.execute.side_effect = [
            "DELETE 0",                      # entries expired
            f"DELETE {EXPIRE_BATCH_SIZE}",   # first chunk batch
            f"DELETE {EXPIRE_BATCH_SIZE - 1}",  # second chunk batch (triggers break)
        ]

        result = await expire_entries(pg_pool)

        expected = EXPIRE_BATCH_SIZE + (EXPIRE_BATCH_SIZE - 1)
        assert result["chunks_orphaned"] == expected
        # Should have 3 execute calls: entries + 2 chunk batches
        assert conn.execute.call_count == 3

    @pytest.mark.anyio
    async def test_no_orphans(self) -> None:
        """All chunks have valid documents → 0 orphaned."""
        pg_pool, conn = _make_mock_pg()
        conn.execute.side_effect = ["DELETE 0", "DELETE 0"]

        result = await expire_entries(pg_pool)

        assert result["chunks_orphaned"] == 0


class TestExpireDryRun:
    """Verify dry-run counts but doesn't delete."""

    @pytest.mark.anyio
    async def test_dry_run_counts_entries(self) -> None:
        pg_pool, conn = _make_mock_pg()
        conn.fetchrow.return_value = {"n": 7}

        result = await expire_entries(pg_pool, dry_run=True)

        assert result["entries_expired"] == 7
        assert result["chunks_orphaned"] >= 0
        conn.execute.assert_not_called()

    @pytest.mark.anyio
    async def test_dry_run_counts_orphans(self) -> None:
        pg_pool, conn = _make_mock_pg()
        # First fetchrow: expired entries count.  Second: orphaned chunks count.
        conn.fetchrow.side_effect = [{"n": 2}, {"n": 13}]

        result = await expire_entries(pg_pool, dry_run=True)

        assert result["entries_expired"] == 2
        assert result["chunks_orphaned"] == 13
        conn.execute.assert_not_called()


class TestExpireErrors:
    """Verify DB errors are counted, not raised."""

    @pytest.mark.anyio
    async def test_entry_delete_failure(self) -> None:
        pg_pool, conn = _make_mock_pg()
        conn.execute.side_effect = Exception("table locked")

        result = await expire_entries(pg_pool)

        assert result["errors"] >= 1

    @pytest.mark.anyio
    async def test_chunk_delete_failure(self) -> None:
        pg_pool, conn = _make_mock_pg()
        conn.execute.side_effect = ["DELETE 0", Exception("out of memory")]

        result = await expire_entries(pg_pool)

        assert result["entries_expired"] == 0
        assert result["errors"] >= 1


# ── Env Loading ──────────────────────────────────────────────────────────────


class TestLoadEnv:
    """Verify environment variable loading from file."""

    def test_reads_env_file(self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing env vars should be loaded from the env file."""
        env_dir = tmp_path / "osmen_cfg"
        env_dir.mkdir()
        env_file = env_dir / "env"
        env_file.write_text(
            "POSTGRES_DSN=postgresql://test:pass@localhost/testdb\n"
            "REDIS_URL=redis://localhost:6380\n"
        )

        monkeypatch.delenv("POSTGRES_DSN", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setattr(
            "core.memory.maintenance.os.path.expanduser",
            lambda p: str(env_dir / "env"),
        )

        _load_env()

        from core.memory.maintenance import POSTGRES_DSN, REDIS_URL
        assert POSTGRES_DSN == "postgresql://test:pass@localhost/testdb"
        assert REDIS_URL == "redis://localhost:6380"

    def test_env_vars_take_precedence(self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set env vars should NOT be overridden by the env file."""
        env_dir = tmp_path / "osmen_cfg"
        env_dir.mkdir()
        env_file = env_dir / "env"
        env_file.write_text(
            "POSTGRES_DSN=postgresql://file:override@localhost/file\n"
            "REDIS_URL=redis://file:6380\n"
        )

        monkeypatch.setenv("POSTGRES_DSN", "postgresql://env:first@localhost/env")
        monkeypatch.setenv("REDIS_URL", "redis://env:6380")
        monkeypatch.setattr(
            "core.memory.maintenance.os.path.expanduser",
            lambda p: str(env_dir / "env"),
        )

        _load_env()

        from core.memory.maintenance import POSTGRES_DSN, REDIS_URL
        assert POSTGRES_DSN == "postgresql://env:first@localhost/env"
        assert REDIS_URL == "redis://env:6380"

    def test_missing_env_file_no_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-existent env file should be silently ignored."""
        monkeypatch.delenv("POSTGRES_DSN", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setattr(
            "core.memory.maintenance.os.path.expanduser",
            lambda p: "/nonexistent/path/env",
        )

        _load_env()  # should not raise

        from core.memory.maintenance import POSTGRES_DSN, REDIS_URL
        assert POSTGRES_DSN == ""
        assert REDIS_URL == ""


# ── Constants ────────────────────────────────────────────────────────────────


class TestConstants:
    """Verify configuration constants are within sane bounds."""

    def test_promotion_thresholds(self) -> None:
        assert 0 < PROMOTION_IMPORTANCE_FLOOR <= 1.0
        assert PROMOTION_ACCESS_THRESHOLD >= 1

    def test_decay_constants(self) -> None:
        assert DECAY_HALF_LIFE_DAYS > 0
        assert 0 <= DECAY_FLOOR < 0.5
        assert DECAY_GRACE_DAYS > 0

    def test_expire_batch_size(self) -> None:
        assert EXPIRE_BATCH_SIZE > 0

    def test_redis_prefix(self) -> None:
        assert REDIS_WORKING_MEMORY_PREFIX.endswith(":")
