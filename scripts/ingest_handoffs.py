#!/usr/bin/env python3
"""Ingest handoff reports into MemoryHub as episode entries with embeddings."""
from __future__ import annotations

import asyncio
import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HANDOFF_DIR = REPO_ROOT / "docs" / "session-logs"


async def main(dry_run: bool, limit: int | None) -> None:
    from core.memory.hub import MemoryHub
    from core.memory.embeddings import OllamaEmbedder

    handoffs = sorted(HANDOFF_DIR.rglob("*handoff*.md"))
    if limit:
        handoffs = handoffs[:limit]

    hub = MemoryHub()
    embedder = OllamaEmbedder()
    await hub.connect()
    ingested = 0

    for path in handoffs:
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text.strip()) < 50:
            continue

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", str(path))
        session_date = date_match.group(1) if date_match else "unknown"

        if dry_run:
            print(f"[DRY] Would ingest: {path.relative_to(REPO_ROOT)} ({len(text)} chars)")
            ingested += 1
            continue

        # Generate embedding from first 1000 chars
        emb_result = await embedder.embed_one(text[:1000])

        await hub.store_memory(
            agent_id="system",
            memory_type="episode",
            content=text[:8000],
            embedding=emb_result.embedding,
            importance=0.7,
            metadata={
                "source": "handoff_ingest",
                "file": str(path.relative_to(REPO_ROOT)),
                "session_date": session_date,
            },
        )
        print(f"Ingested: {path.relative_to(REPO_ROOT)}")
        ingested += 1

    await embedder.close()
    await hub.close()
    print(f"\nTotal: {ingested} handoff reports {'would be ' if dry_run else ''}ingested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(main(args.dry_run, args.limit))
