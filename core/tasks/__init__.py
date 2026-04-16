"""Taskwarrior integration: hooks queue and async sync worker."""

from core.tasks.queue import TaskQueue

__all__ = ["TaskQueue", "TaskSyncWorker"]


def __getattr__(name: str):
    if name == "TaskSyncWorker":
        from core.tasks.sync import TaskSyncWorker
        return TaskSyncWorker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
