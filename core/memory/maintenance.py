"""Memory tier maintenance — promotion, decay, and cleanup.

Periodic one-shot invoked by ``osmen-memory-maintenance.timer``.
Runs three passes:

1. **Promotion** — scans Redis working-memory candidates (entries with
   sufficient access frequency or importance) and promotes them into
   the persistent ``memory_entries`` table with a pgvector embedding.
   Working-memory keys are removed from Redis after promotion.

2. **Decay** — applies time-based importance decay to ``memory_entries``
   rows that haven't been accessed recently.  Entries that decay below
   a floor threshold and are older than the grace period are flagged
   for archival or deletion.

3. **Expiration** — removes expired entries (``expires_at < NOW()``)
   from ``memory_entries`` and orphaned chunks from ``memory_chunks``
   whose parent ``document_id`` no longer exists.

Redis key conventions::

    wm:{agent_id} — hash of working-memory entries for an agent.
        Field:  ``{entry_id}``
        Value:  JSON ``{"content": ..., "importance": ..., "type": ...,
                         "access_count": ..., "created_at": ...}``

Environment variables used (fall back to ``~/.config/osmen/env``)::

    POSTGRES_DSN  — PostgreSQL connection string
    REDIS_URL     — Redis connection string

Usage::

    python -m core.memory.maintenance
    python -m core.memory.maintenance --dry-run
    python -m core.memory.maintenance --promote-only
    python -m core.memory.maintenance --decay-only
    python -m core.memory.maintenance --expire-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import anyio
from loguru import logger


# ── Configuration ────────────────────────────────────────────────────────────

PROMOTION_ACCESS_THRESHOLD: int = 3
"""Minimum access_count for a working-memory entry to be promotion-worthy."""

PROMOTION_IMPORTANCE_FLOOR: float = 0.4
"""Minimum importance score for promotion consideration."""

DECAY_HALF_LIFE_DAYS: int = 30
"""Days after last access before importance halves."""

DECAY_FLOOR: float = 0.05
"""Entries decayed below this are candidates for removal."""

DECAY_GRACE_DAYS: int = 7
"""Minimum age (days) before a decayed entry can be removed."""

EXPIRE_BATCH_SIZE: int = 500
"""Rows to delete per batch during expiration sweep."""

REDIS_WORKING_MEMORY_PREFIX: str = "wm:"
"""Key prefix for working-memory hashes in Redis."""

POSTGRES_DSN: str = ""
REDIS_URL: str = ""


def _load_env() -> None:
    """Load DSN / URL from environment or the env file."""
    global POSTGRES_DSN, REDIS_URL
    POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "")
    REDIS_URL = os.environ.get("REDIS_URL", "")

    env_file = os.path.expanduser("~/.config/osmen/env")
    if not POSTGRES_DSN or not REDIS_URL:
        try:
            with open(env_file) as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("POSTGRES_DSN=") and not POSTGRES_DSN:
                        POSTGRES_DSN = line.split("=", 1)[1]
                    elif line.startswith("REDIS_URL=") and not REDIS_URL:
                        REDIS_URL = line.split("=", 1)[1]
        except FileNotFoundError:
            pass


# ── Promotion ────────────────────────────────────────────────────────────────

async def _generate_embedding(text: str) -> list[float] | None:
    """Call Ollama to embed *text*.  Returns None on failure."""
    import httpx

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ollama_url}/api/embed",
                json={"model": model, "input": text},
            )
            resp.raise_for_status()
            return resp.json()["embeddings"][0]
    except Exception as exc:
        logger.warning("Embedding generation failed for promotion: {}", exc)
        return None


async def promote_working_memory(
    redis_client: Any,
    pg_pool: Any,
    *,
    dry_run: bool = False,
) -> dict[str, int]:
    """Scan Redis working-memory entries and promote high-signal ones to Postgres.

    Returns a summary dict with keys: scanned, promoted, skipped, errors.
    """
    summary = {"scanned": 0, "promoted": 0, "skipped": 0, "errors": 0}

    # Discover all working-memory keys
    pattern = f"{REDIS_WORKING_MEMORY_PREFIX}*"
    cursor = 0
    wm_keys: list[str] = []

    while True:
        cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
        wm_keys.extend(keys)
        if cursor == 0:
            break

    if not wm_keys:
        logger.info("promotion: no working-memory keys found (pattern={})", pattern)
        return summary

    logger.info("promotion: scanning {} working-memory key(s)", len(wm_keys))

    for key in wm_keys:
        # Extract agent_id from key  "wm:agent_name" -> "agent_name"
        agent_id = key.removeprefix(REDIS_WORKING_MEMORY_PREFIX) or "default"

        entries = await redis_client.hgetall(key)
        if not entries:
            continue

        for entry_id, raw_json in entries.items():
            summary["scanned"] += 1
            try:
                data = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning("promotion: bad JSON in {} field={}", key, entry_id)
                summary["errors"] += 1
                continue

            importance = float(data.get("importance", 0.0))
            access_count = int(data.get("access_count", 0))

            # Check promotion criteria
            if (
                importance < PROMOTION_IMPORTANCE_FLOOR
                and access_count < PROMOTION_ACCESS_THRESHOLD
            ):
                summary["skipped"] += 1
                continue

            content = data.get("content", "").strip()
            if not content:
                summary["skipped"] += 1
                continue

            memory_type = data.get("type", "fact")
            # Validate memory_type against DB constraint
            valid_types = {
                "fact", "observation", "decision", "context",
                "preference", "episode", "learning",
            }
            if memory_type not in valid_types:
                memory_type = "context"

            # Generate embedding for semantic search
            embedding = await _generate_embedding(content)

            if dry_run:
                logger.info(
                    "promotion [dry-run]: would promote entry={} agent={} "
                    "importance={} type='{}' content={:.60s}...",
                    entry_id,
                    agent_id,
                    importance,
                    memory_type,
                    content,
                )
            else:
                emb_str = (
                    "[" + ",".join(str(v) for v in embedding) + "]"
                    if embedding
                    else None
                )
                try:
                    async with pg_pool.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO memory_entries
                                (agent_id, memory_type, content, embedding,
                                 importance, access_count, metadata, source_event)
                            VALUES ($1, $2, $3, $4::vector, $5, $6, $7::jsonb, $8)
                            ON CONFLICT DO NOTHING
                            """,
                            agent_id,
                            memory_type,
                            content,
                            emb_str,
                            importance,
                            access_count,
                            json.dumps({
                                "promoted_from": "redis_working_memory",
                                "original_entry_id": entry_id,
                            }),
                            entry_id,
                        )
                    # Remove from Redis after successful promotion
                    await redis_client.hdel(key, entry_id)
                    summary["promoted"] += 1
                    logger.debug(
                        "promotion: entry={} agent={} type='{}' promoted",
                        entry_id,
                        agent_id,
                        memory_type,
                    )
                except Exception as exc:
                    logger.error("promotion: failed for entry={}: {}", entry_id, exc)
                    summary["errors"] += 1

    logger.info(
        "promotion: done — scanned={} promoted={} skipped={} errors={}",
        summary["scanned"],
        summary["promoted"],
        summary["skipped"],
        summary["errors"],
    )
    return summary


# ── Decay ────────────────────────────────────────────────────────────────────

async def decay_stale_entries(
    pg_pool: Any,
    *,
    dry_run: bool = False,
) -> dict[str, int]:
    """Apply importance decay to entries not accessed recently.

    Decay formula::

        decayed = original * 0.5 ^ (days_since_access / HALF_LIFE_DAYS)

    Entries below DECAY_FLOOR that are older than DECAY_GRACE_DAYS are
    candidates for removal.

    Returns a summary dict with keys: decayed, removable, errors.
    """
    summary = {"decayed": 0, "removable": 0, "errors": 0}

    now = datetime.now(timezone.utc)

    async with pg_pool.acquire() as conn:
        # Fetch entries that haven't been accessed in DECAY_HALF_LIFE_DAYS
        rows = await conn.fetch(
            """
            SELECT entry_id, importance, access_count, last_accessed, created_at
            FROM memory_entries
            WHERE last_accessed < NOW() - INTERVAL '1 day' * $1
              AND importance > $2
              AND (expires_at IS NULL OR expires_at > NOW())
            """,
            DECAY_HALF_LIFE_DAYS,
            DECAY_FLOOR,
        )

        logger.info("decay: found {} stale entries to evaluate", len(rows))

        removable_ids: list[str] = []

        for row in rows:
            entry_id = row["entry_id"]
            original_importance = float(row["importance"])
            last_accessed = row["last_accessed"]
            created_at = row["created_at"]

            # Calculate decay factor
            days_since_access = (now - last_accessed).days
            decay_factor = 0.5 ** (days_since_access / DECAY_HALF_LIFE_DAYS)
            new_importance = original_importance * decay_factor

            if new_importance < DECAY_FLOOR:
                age_days = (now - created_at).days
                if age_days > DECAY_GRACE_DAYS:
                    removable_ids.append(entry_id)
                    summary["removable"] += 1
                    continue

            if dry_run:
                logger.info(
                    "decay [dry-run]: entry={} importance {:.3f} → {:.3f}",
                    entry_id,
                    original_importance,
                    new_importance,
                )
            else:
                try:
                    await conn.execute(
                        "UPDATE memory_entries SET importance = $1 WHERE entry_id = $2",
                        new_importance,
                        entry_id,
                    )
                    summary["decayed"] += 1
                except Exception as exc:
                    logger.error("decay: failed for entry={}: {}", entry_id, exc)
                    summary["errors"] += 1

        # Remove decayed entries past grace period
        if removable_ids and not dry_run:
            try:
                result = await conn.execute(
                    "DELETE FROM memory_entries WHERE entry_id = ANY($1::text[])",
                    removable_ids,
                )
                deleted = int(result.split()[-1])
                summary["decayed"] += deleted  # count removals in decayed total
                logger.info("decay: removed {} fully-decayed entries", deleted)
            except Exception as exc:
                logger.error("decay: failed to remove entries: {}", exc)
                summary["errors"] += len(removable_ids)

    logger.info(
        "decay: done — decayed={} removable={} errors={}",
        summary["decayed"],
        summary["removable"],
        summary["errors"],
    )
    return summary


# ── Expiration ────────────────────────────────────────────────────────────────

async def expire_entries(
    pg_pool: Any,
    *,
    dry_run: bool = False,
) -> dict[str, int]:
    """Remove expired entries and orphaned chunks.

    1. Deletes ``memory_entries`` where ``expires_at < NOW()``.
    2. Deletes ``memory_chunks`` whose ``document_id`` references a
       document that no longer exists.

    Returns a summary dict with keys: entries_expired, chunks_orphaned, errors.
    """
    summary = {"entries_expired": 0, "chunks_orphaned": 0, "errors": 0}

    async with pg_pool.acquire() as conn:
        # Expire timed-out entries
        if dry_run:
            count_row = await conn.fetchrow(
                "SELECT COUNT(*) AS n FROM memory_entries WHERE expires_at < NOW()"
            )
            count = count_row["n"]
            logger.info("expire [dry-run]: would expire {} entries", count)
            summary["entries_expired"] = count
        else:
            try:
                result = await conn.execute(
                    "DELETE FROM memory_entries WHERE expires_at < NOW()"
                )
                deleted = int(result.split()[-1])
                summary["entries_expired"] = deleted
                if deleted:
                    logger.info("expire: removed {} expired entries", deleted)
            except Exception as exc:
                logger.error("expire: failed to remove expired entries: {}", exc)
                summary["errors"] += 1

        # Remove orphaned chunks (document_id references deleted document)
        if dry_run:
            count_row = await conn.fetchrow(
                """
                SELECT COUNT(*) AS n
                FROM memory_chunks mc
                WHERE mc.document_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM documents d WHERE d.document_id = mc.document_id
                  )
                """
            )
            count = count_row["n"]
            logger.info("expire [dry-run]: would remove {} orphaned chunks", count)
            summary["chunks_orphaned"] = count
        else:
            try:
                # Delete in batches to avoid long lock contention
                total_deleted = 0
                while True:
                    result = await conn.execute(
                        """
                        DELETE FROM memory_chunks
                        WHERE chunk_id IN (
                            SELECT mc.chunk_id
                            FROM memory_chunks mc
                            WHERE mc.document_id IS NOT NULL
                              AND NOT EXISTS (
                                  SELECT 1 FROM documents d
                                  WHERE d.document_id = mc.document_id
                              )
                            LIMIT $1
                        )
                        """,
                        EXPIRE_BATCH_SIZE,
                    )
                    deleted = int(result.split()[-1])
                    total_deleted += deleted
                    if deleted < EXPIRE_BATCH_SIZE:
                        break

                summary["chunks_orphaned"] = total_deleted
                if total_deleted:
                    logger.info("expire: removed {} orphaned chunks", total_deleted)
            except Exception as exc:
                logger.error("expire: failed to remove orphaned chunks: {}", exc)
                summary["errors"] += 1

    logger.info(
        "expire: done — entries_expired={} chunks_orphaned={} errors={}",
        summary["entries_expired"],
        summary["chunks_orphaned"],
        summary["errors"],
    )
    return summary


# ── Main ─────────────────────────────────────────────────────────────────────

async def run_maintenance(
    *,
    dry_run: bool = False,
    promote_only: bool = False,
    decay_only: bool = False,
    expire_only: bool = False,
) -> dict[str, dict[str, int]]:
    """Run the full maintenance pipeline.

    Returns a dict keyed by pass name, each containing a summary dict.
    """
    _load_env()

    results: dict[str, dict[str, int]] = {}

    # Connect to PostgreSQL
    import asyncpg

    if not POSTGRES_DSN:
        logger.error("POSTGRES_DSN not configured — aborting")
        sys.exit(1)

    pg_pool = await asyncpg.create_pool(POSTGRES_DSN, min_size=1, max_size=3)
    logger.info("connected to PostgreSQL")

    # Connect to Redis (optional — promotion only)
    redis_client = None
    if not expire_only and not decay_only:
        if REDIS_URL:
            try:
                import redis.asyncio as aioredis

                redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
                await redis_client.ping()
                logger.info("connected to Redis at {}", REDIS_URL)
            except Exception as exc:
                logger.warning("Redis unavailable ({}), skipping promotion pass", exc)
                redis_client = None
        else:
            logger.warning("REDIS_URL not configured, skipping promotion pass")

    try:
        # Promotion pass
        if not decay_only and not expire_only:
            if redis_client is not None:
                results["promotion"] = await promote_working_memory(
                    redis_client, pg_pool, dry_run=dry_run,
                )
            else:
                logger.info("promotion: skipped (no Redis)")

        # Decay pass
        if not promote_only and not expire_only:
            results["decay"] = await decay_stale_entries(pg_pool, dry_run=dry_run)

        # Expiration pass
        if not promote_only and not decay_only:
            results["expiration"] = await expire_entries(pg_pool, dry_run=dry_run)

    finally:
        await pg_pool.close()
        if redis_client is not None:
            await redis_client.close()

    # Log summary
    for pass_name, summary in results.items():
        logger.info("maintenance pass '{}': {}", pass_name, summary)

    return results


def main() -> None:
    """CLI entry point for ``python -m core.memory.maintenance``."""
    parser = argparse.ArgumentParser(
        description="OsMEN-OC memory tier maintenance (promotion / decay / expiration)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would happen without making changes",
    )
    parser.add_argument(
        "--promote-only",
        action="store_true",
        help="Run only the Redis → Postgres promotion pass",
    )
    parser.add_argument(
        "--decay-only",
        action="store_true",
        help="Run only the importance decay pass",
    )
    parser.add_argument(
        "--expire-only",
        action="store_true",
        help="Run only the expiration / cleanup pass",
    )
    args = parser.parse_args()

    anyio.run(run_maintenance, dry_run=args.dry_run, promote_only=args.promote_only, decay_only=args.decay_only, expire_only=args.expire_only)


if __name__ == "__main__":
    main()
