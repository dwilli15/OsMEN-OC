"""Local SQLite queue for Taskwarrior hook events.

Taskwarrior hooks MUST NOT block on network I/O (PF18).  They append to
this local SQLite database which a background :class:`TaskSyncWorker`
drains asynchronously into the Redis event bus.

The database lives at ``~/.local/share/osmen/task-queue.db``.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "osmen" / "task-queue.db"


class TaskQueue:
    """Append-only local queue backed by SQLite.

    All methods are synchronous and designed for the Taskwarrior hook
    context (no asyncio available).

    Args:
        db_path: Override the default database location.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._db_path),
            timeout=2.0,
            isolation_level="DEFERRED",
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_events (
                id        TEXT PRIMARY KEY,
                action    TEXT NOT NULL,
                task_json TEXT NOT NULL,
                created   TEXT NOT NULL,
                synced    INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._conn.commit()

    def push(self, action: str, task_data: dict[str, Any]) -> str:
        """Enqueue a task event.

        Args:
            action: ``"add"`` or ``"modify"``.
            task_data: Taskwarrior JSON for the task.

        Returns:
            The generated event id.
        """
        event_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            "INSERT INTO task_events (id, action, task_json, created) VALUES (?, ?, ?, ?)",
            (event_id, action, json.dumps(task_data), now),
        )
        self._conn.commit()
        return event_id

    def pending(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return up to *limit* unsynced events (oldest first).

        Returns:
            List of dicts with keys ``id``, ``action``, ``task_data``, ``created``.
        """
        rows = self._conn.execute(
            "SELECT id, action, task_json, created FROM task_events "
            "WHERE synced = 0 ORDER BY created ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": row[0],
                "action": row[1],
                "task_data": json.loads(row[2]),
                "created": row[3],
            }
            for row in rows
        ]

    def mark_synced(self, event_ids: list[str]) -> int:
        """Mark events as successfully synced.

        Args:
            event_ids: List of event IDs to mark.

        Returns:
            Number of rows updated.
        """
        if not event_ids:
            return 0
        placeholders = ",".join("?" for _ in event_ids)
        cursor = self._conn.execute(
            f"UPDATE task_events SET synced = 1 WHERE id IN ({placeholders})",  # noqa: S608
            event_ids,
        )
        self._conn.commit()
        return cursor.rowcount

    def prune(self, *, keep_days: int = 7) -> int:
        """Delete synced events older than *keep_days*.

        Returns:
            Number of rows deleted.
        """
        cutoff = datetime.now(UTC).isoformat()
        cursor = self._conn.execute(
            "DELETE FROM task_events WHERE synced = 1 AND created < date(?, ?)",
            (cutoff, f"-{keep_days} days"),
        )
        self._conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
