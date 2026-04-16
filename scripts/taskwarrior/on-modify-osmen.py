#!/usr/bin/env python3
"""Taskwarrior on-modify hook — queues modified tasks for OsMEN-OC event bus.

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
    """Read old + new task from stdin, enqueue the new one, echo it back."""
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) < 2:
        # Unexpected format — pass through
        for line in lines:
            print(line)
        return 0

    # Taskwarrior sends: line 1 = original JSON, line 2 = modified JSON
    raw_new = lines[1]

    try:
        task_new = json.loads(raw_new)
    except json.JSONDecodeError:
        print(raw_new)
        return 0

    # Always echo the modified task JSON back
    print(json.dumps(task_new))

    # Enqueue for async processing (never raise — hooks must not block)
    try:
        from core.tasks.queue import TaskQueue  # noqa: PLC0415

        queue = TaskQueue()
        queue.push("modify", task_new)
        queue.close()
    except Exception:
        # Swallow ALL errors — hook must never block Taskwarrior
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
