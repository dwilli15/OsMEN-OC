#!/usr/bin/env python3
"""Generate markdown working-memory views from orchestration ledger state.

Reads the workflow_ledger and receipt_log tables, produces a markdown
summary suitable for the Obsidian vault or .opencode/memory-bank.

Usage:
    python scripts/generate_working_memory.py [--output PATH]
"""
from __future__ import annotations

import asyncio
import argparse
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


async def main(output: Path | None) -> None:
    from core.memory.hub import MemoryHub

    hub = MemoryHub()
    await hub.connect()

    # Recall recent session summaries and working memory
    summaries = await hub.recall(
        query="recent session progress orchestration",
        agent_id="system",
        limit=10,
    )

    lines = [
        f"# Working Memory — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Recent Summaries",
        "",
    ]

    for entry in summaries:
        meta = entry.get("metadata", {})
        source = meta.get("source", "?")
        date = meta.get("session_date", meta.get("synced_at", "?"))
        content = entry.get("content", "")[:500]
        lines.append(f"### {source} ({date})")
        lines.append("```")
        lines.append(content)
        lines.append("```")
        lines.append("")

    output_path = output or REPO_ROOT / "openclaw" / "vault" / "working-memory.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    await hub.close()
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    asyncio.run(main(args.output))
