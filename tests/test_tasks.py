"""Tests for core.tasks — TaskQueue and TaskSyncWorker."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.events.envelope import EventEnvelope, EventPriority
from core.tasks.queue import TaskQueue
from core.tasks.sync import TaskSyncWorker


# ── TaskQueue (synchronous) ──────────────────────────────────────────


@pytest.fixture()
def tmp_queue(tmp_path: Path) -> TaskQueue:
    db = tmp_path / "test-queue.db"
    q = TaskQueue(db_path=db)
    yield q
    q.close()


class TestTaskQueue:
    def test_push_and_pending(self, tmp_queue: TaskQueue) -> None:
        task = {"uuid": "abc-123", "description": "Test task", "status": "pending"}
        event_id = tmp_queue.push("add", task)
        assert event_id  # non-empty UUID

        pending = tmp_queue.pending()
        assert len(pending) == 1
        assert pending[0]["action"] == "add"
        assert pending[0]["task_data"]["uuid"] == "abc-123"

    def test_mark_synced(self, tmp_queue: TaskQueue) -> None:
        e1 = tmp_queue.push("add", {"uuid": "1", "description": "a"})
        e2 = tmp_queue.push("add", {"uuid": "2", "description": "b"})

        count = tmp_queue.mark_synced([e1])
        assert count == 1

        pending = tmp_queue.pending()
        assert len(pending) == 1
        assert pending[0]["id"] == e2

    def test_mark_synced_empty_list(self, tmp_queue: TaskQueue) -> None:
        assert tmp_queue.mark_synced([]) == 0

    def test_pending_limit(self, tmp_queue: TaskQueue) -> None:
        for i in range(10):
            tmp_queue.push("add", {"uuid": str(i), "description": f"task {i}"})
        assert len(tmp_queue.pending(limit=3)) == 3

    def test_push_preserves_order(self, tmp_queue: TaskQueue) -> None:
        ids = [tmp_queue.push("add", {"uuid": str(i)}) for i in range(5)]
        pending = tmp_queue.pending()
        assert [p["id"] for p in pending] == ids

    def test_database_created(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sub" / "dir" / "queue.db"
        q = TaskQueue(db_path=db_path)
        assert db_path.exists()
        q.close()


# ── on-add hook (subprocess) ────────────────────────────────────────


class TestOnAddHook:
    def test_hook_echos_json_and_queues(self, tmp_path: Path) -> None:
        """Simulate what Taskwarrior does: pipe JSON into the hook."""
        import subprocess

        hook_path = Path(__file__).resolve().parents[1] / "scripts" / "taskwarrior" / "on-add-osmen.py"

        task_json = json.dumps({
            "uuid": "test-hook-uuid",
            "description": "hook test",
            "status": "pending",
        })

        db_path = tmp_path / "hook-test-queue.db"
        env = {"OSMEN_TASK_QUEUE_DB": str(db_path)}

        # The hook should echo the task JSON back unchanged
        result = subprocess.run(
            ["python3", str(hook_path)],
            input=task_json,
            capture_output=True,
            text=True,
            timeout=5,
            env={**__import__("os").environ, **env},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        assert output["uuid"] == "test-hook-uuid"


class TestOnModifyHook:
    def test_modify_hook_echos_new_json(self, tmp_path: Path) -> None:
        import subprocess

        hook_path = Path(__file__).resolve().parents[1] / "scripts" / "taskwarrior" / "on-modify-osmen.py"

        old_task = json.dumps({"uuid": "mod-uuid", "description": "old", "status": "pending"})
        new_task = json.dumps({"uuid": "mod-uuid", "description": "new", "status": "completed"})
        stdin = f"{old_task}\n{new_task}"

        result = subprocess.run(
            ["python3", str(hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        assert output["description"] == "new"
        assert output["status"] == "completed"


# ── TaskSyncWorker (async) ──────────────────────────────────────────


class TestTaskSyncWorker:
    @pytest.mark.anyio()
    async def test_drain_publishes_events(self, tmp_path: Path) -> None:
        """Worker should drain pending queue items into event bus."""
        queue = TaskQueue(db_path=tmp_path / "sync-test.db")
        queue.push("add", {
            "uuid": "sync-test-1",
            "description": "drain test",
            "priority": "H",
            "status": "pending",
        })

        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock(return_value="msg-id-1")

        worker = TaskSyncWorker(mock_bus, poll_interval=1.0, queue=queue)
        await worker._drain_once()

        mock_bus.publish.assert_called_once()
        envelope: EventEnvelope = mock_bus.publish.call_args[0][0]
        assert envelope.domain == "tasks"
        assert envelope.category == "task_created"
        assert envelope.payload["uuid"] == "sync-test-1"
        assert envelope.priority == EventPriority.HIGH

        # Verify event was marked synced
        assert len(queue.pending()) == 0
        queue.close()

    @pytest.mark.anyio()
    async def test_drain_retries_on_failure(self, tmp_path: Path) -> None:
        """If bus.publish fails, events stay pending for retry."""
        queue = TaskQueue(db_path=tmp_path / "retry-test.db")
        queue.push("modify", {"uuid": "fail-1", "description": "will fail"})
        queue.push("modify", {"uuid": "fail-2", "description": "also fail"})

        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock(side_effect=ConnectionError("Redis down"))

        worker = TaskSyncWorker(mock_bus, poll_interval=1.0, queue=queue)
        await worker._drain_once()

        # Both events should still be pending
        assert len(queue.pending()) == 2
        queue.close()

    @pytest.mark.anyio()
    async def test_drain_empty_queue_noop(self, tmp_path: Path) -> None:
        """Draining an empty queue should not call publish."""
        queue = TaskQueue(db_path=tmp_path / "empty-test.db")
        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock()

        worker = TaskSyncWorker(mock_bus, poll_interval=1.0, queue=queue)
        await worker._drain_once()

        mock_bus.publish.assert_not_called()
        queue.close()

    @pytest.mark.anyio()
    async def test_priority_mapping(self, tmp_path: Path) -> None:
        """Task priority should map to EventPriority correctly."""
        queue = TaskQueue(db_path=tmp_path / "priority-test.db")
        queue.push("add", {"uuid": "low", "description": "low prio", "priority": "L"})
        queue.push("add", {"uuid": "med", "description": "med prio", "priority": "M"})
        queue.push("add", {"uuid": "none", "description": "no prio"})

        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock(return_value="msg-id")

        worker = TaskSyncWorker(mock_bus, poll_interval=1.0, queue=queue)
        await worker._drain_once()

        calls = mock_bus.publish.call_args_list
        assert len(calls) == 3
        assert calls[0][0][0].priority == EventPriority.LOW
        assert calls[1][0][0].priority == EventPriority.NORMAL
        assert calls[2][0][0].priority == EventPriority.LOW
        queue.close()

    @pytest.mark.anyio()
    async def test_modify_category(self, tmp_path: Path) -> None:
        """Modify actions should produce task_modified category."""
        queue = TaskQueue(db_path=tmp_path / "mod-cat-test.db")
        queue.push("modify", {"uuid": "mod-1", "description": "modified"})

        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock(return_value="msg-id")

        worker = TaskSyncWorker(mock_bus, poll_interval=1.0, queue=queue)
        await worker._drain_once()

        envelope: EventEnvelope = mock_bus.publish.call_args[0][0]
        assert envelope.category == "task_modified"
        queue.close()

    @pytest.mark.anyio()
    async def test_stop(self, tmp_path: Path) -> None:
        """Worker should stop when stop() is called."""
        queue = TaskQueue(db_path=tmp_path / "stop-test.db")
        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock()

        worker = TaskSyncWorker(mock_bus, poll_interval=0.1, queue=queue)
        worker.stop()
        assert worker._running is False
