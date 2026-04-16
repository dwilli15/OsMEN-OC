"""Workflow session management.

Provides request classification, freshness preflight checks, and
workflow lifecycle management.  When a new request arrives (via bridge,
task, or domain event), the session classifier determines whether it
should start a new workflow or resume an existing one.

Classification heuristics:

1. **Correlation match**: If a ``correlation_id`` is provided and a
   non-terminal workflow exists for it, resume that workflow.
2. **Freshness check**: If a recent (within ``STALE_THRESHOLD_SECONDS``)
   completed workflow exists for the same ``request_class``, skip
   creating a new one and return the cached result.
3. **New workflow**: Otherwise, create a fresh workflow.

The classifier does NOT execute workflows — it only decides *whether*
to create or resume them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from core.orchestration.models import (
    Workflow,
    WorkflowMode,
    WorkflowStatus,
)

# ── Constants ───────────────────────────────────────────────────────────────

# A workflow is considered "stale" after this many seconds with no activity.
STALE_THRESHOLD_SECONDS = 300  # 5 minutes

# A completed workflow's result is considered fresh for this many seconds.
FRESHNESS_WINDOW_SECONDS = 3600  # 1 hour

# Default request classification rules.
# Keys are substrings matched against the raw request text (case-insensitive).
# Values are the assigned request_class.  First match wins.
_DEFAULT_CLASS_RULES: list[tuple[str, str]] = [
    ("what is", "question"),
    ("how do", "question"),
    ("how can", "question"),
    ("why does", "question"),
    ("explain", "question"),
    ("define", "question"),
    ("compare", "question"),
    ("summarize", "task"),
    ("summarise", "task"),
    ("create", "task"),
    ("build", "task"),
    ("fix", "debug"),
    ("debug", "debug"),
    ("error", "debug"),
    ("broken", "debug"),
    ("crash", "debug"),
    ("help", "question"),
    ("investigate", "task"),
    ("research", "task"),
    ("analyze", "task"),
    ("analyse", "task"),
    ("review", "task"),
    ("write", "task"),
    ("generate", "task"),
    ("translate", "task"),
    ("transcribe", "task"),
]


class SessionClassifier:
    """Determines whether to create or resume a workflow.

    Args:
        ledger: The orchestration ledger for workflow lookups.
        stale_threshold: Seconds of inactivity before a workflow is stale.
        freshness_window: Seconds for which a completed result stays fresh.
    """

    def __init__(
        self,
        ledger: Any,
        *,
        stale_threshold: int = STALE_THRESHOLD_SECONDS,
        freshness_window: int = FRESHNESS_WINDOW_SECONDS,
    ) -> None:
        self._ledger = ledger
        self._stale_threshold = stale_threshold
        self._freshness_window = freshness_window
        self._class_rules: list[tuple[str, str]] = list(_DEFAULT_CLASS_RULES)

    # ── Public API ──────────────────────────────────────────────────────────

    async def classify(
        self,
        request: str,
        *,
        correlation_id: str | None = None,
        source_event_id: str | None = None,
        source_channel: str | None = None,
        mode: WorkflowMode | None = None,
        driver_agent_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, bool]:
        """Classify a request and decide the workflow action.

        Returns:
            A tuple of ``(workflow_id, is_new)``.  If ``is_new`` is True,
            the caller should create a workflow with the returned ID.
            If False, the caller should resume the existing workflow.
        """
        # 1. Check for existing workflow by correlation_id
        if correlation_id:
            existing = await self._find_resumable_workflow(correlation_id)
            if existing:
                logger.debug(
                    "session: resuming workflow {} by correlation {}",
                    existing.workflow_id,
                    correlation_id,
                )
                return existing.workflow_id, False

        # 2. Classify the request
        request_class = self._classify_request(request)

        # 3. Check freshness — skip if recent completed workflow exists
        fresh = await self._find_fresh_workflow(request_class)
        if fresh:
            logger.debug(
                "session: fresh workflow {} for class {} (within {}s)",
                fresh.workflow_id,
                request_class,
                self._freshness_window,
            )
            return fresh.workflow_id, False

        # 4. Create new workflow
        import uuid

        workflow_id = str(uuid.uuid4())
        wf = Workflow(
            workflow_id=workflow_id,
            mode=mode or WorkflowMode.COOPERATIVE,
            status=WorkflowStatus.CREATED,
            driver_agent_id=driver_agent_id,
            request=request,
            request_class=request_class,
            source_event_id=source_event_id,
            source_channel=source_channel,
            correlation_id=correlation_id,
            context=context or {},
        )
        await self._ledger.create_workflow(wf)
        logger.info(
            "session: created workflow {} class={} mode={}",
            workflow_id,
            request_class,
            wf.mode,
        )
        return workflow_id, True

    def classify_request_text(self, request: str) -> str:
        """Classify a request string without touching the ledger.

        Useful for pre-classification in contexts where no ledger is
        available (e.g. logging, metrics).
        """
        return self._classify_request(request)

    def add_class_rule(self, pattern: str, request_class: str) -> None:
        """Add a custom classification rule (matched before defaults)."""
        self._class_rules.insert(0, (pattern.lower(), request_class))

    async def preflight_check(self, workflow_id: str) -> dict[str, Any]:
        """Run a freshness/staleness preflight on an existing workflow.

        Returns a dict with keys:
            - ``exists``: bool
            - ``status``: str or None
            - ``is_stale``: bool
            - ``is_fresh``: bool (completed + within freshness window)
            - ``age_seconds``: int or None
        """
        wf = await self._ledger.get_workflow(workflow_id)
        if wf is None:
            return {"exists": False, "status": None, "is_stale": False, "is_fresh": False, "age_seconds": None}

        now = datetime.now(timezone.utc)
        age = (now - wf.updated_at).total_seconds()

        is_stale = (
            wf.status == WorkflowStatus.RUNNING
            and age > self._stale_threshold
        )
        is_fresh = (
            wf.status == WorkflowStatus.COMPLETED
            and age < self._freshness_window
        )

        return {
            "exists": True,
            "status": wf.status,
            "is_stale": is_stale,
            "is_fresh": is_fresh,
            "age_seconds": int(age),
        }

    # ── Internal ────────────────────────────────────────────────────────────

    def _classify_request(self, request: str) -> str:
        """Apply classification rules to a request string."""
        lower = request.lower().strip()
        for pattern, cls in self._class_rules:
            if pattern in lower:
                return cls
        return "task"  # default

    async def _find_resumable_workflow(
        self,
        correlation_id: str,
    ) -> Workflow | None:
        """Find a non-terminal workflow by correlation ID."""
        # The ledger doesn't have a direct correlation lookup yet,
        # so we search recent workflows.  This is fine for now —
        # the correlation index exists in the migration.
        workflows = await self._ledger.list_workflows(limit=50)
        for wf in workflows:
            if (
                wf.correlation_id == correlation_id
                and wf.status
                in (
                    WorkflowStatus.CREATED,
                    WorkflowStatus.RUNNING,
                    WorkflowStatus.SUSPENDED,
                )
            ):
                return wf
        return None

    async def _find_fresh_workflow(
        self,
        request_class: str,
    ) -> Workflow | None:
        """Find a recently completed workflow of the same class."""
        workflows = await self._ledger.list_workflows(
            status=WorkflowStatus.COMPLETED,
            limit=10,
        )
        now = datetime.now(timezone.utc)
        for wf in workflows:
            if wf.request_class == request_class:
                age = (now - wf.completed_at).total_seconds() if wf.completed_at else float("inf")
                if age < self._freshness_window:
                    return wf
        return None
