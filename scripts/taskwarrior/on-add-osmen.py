#!/usr/bin/env python3
"""Taskwarrior on-add hook — queues new tasks for OsMEN-OC event bus.

This hook MUST NOT block (PF18).  It writes to a local SQLite
queue that the TaskSyncWorker drains asynchronously.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add the OsMEN-OC repo root to sys.path so core.tasks imports work.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    """Read the added task from stdin, enqueue it, echo it back unchanged."""
    raw = sys.stdin.read().strip()
    if not raw:
        return 0

    try:
        task = json.loads(raw)
    except json.JSONDecodeError:
        # Cannot parse — pass through unchanged
        print(raw)
        return 0

    # Always echo the task JSON back (Taskwarrior requires this)
    print(json.dumps(task))

    # Enqueue for async processing (never raise — hooks must not block)
    try:
        from core.tasks.queue import TaskQueue  # noqa: PLC0415

        queue = TaskQueue()
        queue.push("add", task)
        queue.close()
    except Exception:
        # Swallow ALL errors — hook must never block Taskwarrior
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
