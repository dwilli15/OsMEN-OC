"""Async worker that drains the local TaskQueue into the Redis event bus.

Runs as a long-lived background task.  Polls the local SQLite queue
every *poll_interval* seconds and publishes pending events as
``EventEnvelope`` messages on the bus.

If Redis is unreachable, events stay in the local queue and are
retried on the next poll cycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
from loguru import logger

from core.events.envelope import EventEnvelope, EventPriority
from core.tasks.queue import TaskQueue

if TYPE_CHECKING:
    from core.events.bus import EventBus

# Category mapping for task events
_ACTION_CATEGORY = {
    "add": "task_created",
    "modify": "task_modified",
}


class TaskSyncWorker:
    """Background worker that syncs Taskwarrior events to the event bus.

    Args:
        event_bus: The Redis-backed event bus.
        poll_interval: Seconds between queue polls.
        queue: Optional custom TaskQueue (uses default path if omitted).
    """

    def __init__(
        self,
        event_bus: EventBus,
        *,
        poll_interval: float = 5.0,
        queue: TaskQueue | None = None,
    ) -> None:
        self._bus = event_bus
        self._interval = poll_interval
        self._queue = queue or TaskQueue()
        self._running = False

    async def run(self) -> None:
        """Poll the local queue and publish events until cancelled."""
        self._running = True
        logger.info("TaskSyncWorker started (poll_interval={}s)", self._interval)

        try:
            while self._running:
                await self._drain_once()
                await anyio.sleep(self._interval)
        finally:
            self._queue.close()
            logger.info("TaskSyncWorker stopped")

    async def _drain_once(self) -> None:
        """Read pending events from local queue and publish to event bus."""
        pending = await anyio.to_thread.run_sync(lambda: self._queue.pending(limit=50))
        if not pending:
            return

        synced_ids: list[str] = []

        for event in pending:
            category = _ACTION_CATEGORY.get(event["action"], "task_event")
            task_data = event["task_data"]

            # Determine priority from the task
            tw_priority = task_data.get("priority", "")
            if tw_priority == "H":
                priority = EventPriority.HIGH
            elif tw_priority == "M":
                priority = EventPriority.NORMAL
            else:
                priority = EventPriority.LOW

            envelope = EventEnvelope(
                domain="tasks",
                category=category,
                payload=task_data,
                source="taskwarrior_hook",
                correlation_id=task_data.get("uuid"),
                priority=priority,
            )

            try:
                await self._bus.publish(envelope)
                synced_ids.append(event["id"])
                logger.debug(
                    "Synced task event action={} uuid={}",
                    event["action"],
                    task_data.get("uuid", "?"),
                )
            except Exception:
                logger.warning(
                    "Failed to publish task event {} — will retry",
                    event["id"],
                )
                # Stop processing this batch; retry next poll
                break

        if synced_ids:
            await anyio.to_thread.run_sync(lambda: self._queue.mark_synced(synced_ids))
            logger.info("Synced {} task events to event bus", len(synced_ids))

    def stop(self) -> None:
        """Signal the worker to stop on the next poll cycle."""
        self._running = False
