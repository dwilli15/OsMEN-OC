#!/usr/bin/env python3
"""Sync .opencode/memory-bank with MemoryHub at session start/end.

Reads activeContext.md and progress.md from the memory bank,
stores them in MemoryHub with recall metadata so the orchestration
layer can retrieve them for context enrichment.

Usage:
    python scripts/sync_memory_bank.py [--direction start|end]
"""
from __future__ import annotations

import asyncio
import argparse
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MEMORY_BANK = REPO_ROOT / ".opencode" / "memory-bank"


async def main(direction: str) -> None:
    from core.memory.hub import MemoryHub

    hub = MemoryHub()
    await hub.connect()

    for name in ("activeContext", "progress"):
        path = MEMORY_BANK / f"{name}.md"
        if not path.exists():
            print(f"Skip: {name}.md not found")
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            continue

        await hub.store_memory(
            agent_id="system",
            memory_type="context",
            content=text[:8000],
            importance=0.5 if direction == "start" else 0.6,
            metadata={
                "source": "memory_bank_sync",
                "file": f"{name}.md",
                "direction": direction,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        print(f"Synced: {name}.md ({direction})")

    await hub.close()
    print("Memory bank sync complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction", choices=["start", "end"], default="start")
    args = parser.parse_args()
    asyncio.run(main(args.direction))
