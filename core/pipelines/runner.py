"""Pipeline runner — loads pipeline definitions and dispatches steps.

The runner reads ``config/pipelines.yaml``, registers event-stream
subscriptions for event-triggered pipelines, and schedules cron-triggered
pipelines.  Each pipeline step is executed through the approval gate
and audit trail, then publishes a completion event.

Usage::

    runner = PipelineRunner(
        event_bus=bus,
        mcp_registry=registry,
        approval_gate=gate,
        audit_trail_pool=pg_pool,
    )
    await runner.start()
    ...
    await runner.stop()
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import anyio
from cronsim import CronSim
from loguru import logger

from core.approval.gate import ApprovalGate, ApprovalOutcome, ApprovalRequest, RiskLevel
from core.audit.trail import AuditRecord, AuditTrail
from core.events.envelope import EventEnvelope, EventPriority
from core.gateway.handlers import HandlerContext, handler_registry
from core.gateway.mcp import MCPTool
from core.utils.config import load_config
from core.utils.exceptions import PipelineError

_RETRY_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 0.25


def _topological_sort(steps: list[PipelineStep]) -> list[PipelineStep]:
    """Return *steps* in dependency-respecting execution order.

    Uses Kahn's algorithm.  Raises :class:`~core.utils.exceptions.PipelineError`
    if a cycle is detected or a ``depends_on`` reference names an unknown tool.

    Args:
        steps: Ordered list of pipeline steps (index order is tie-broken first).

    Returns:
        Re-ordered list with all dependencies satisfied before each step.

    Raises:
        PipelineError: On cycle detection or unknown dependency reference.
    """
    # Build tool-name → step mapping (last wins on duplicate tool names)
    by_tool: dict[str, PipelineStep] = {s.tool: s for s in steps}

    # Validate that all depends_on references exist
    for step in steps:
        for dep in step.depends_on:
            if dep not in by_tool:
                raise PipelineError(
                    f"Step '{step.tool}' depends_on unknown tool '{dep}'"
                )

    # Compute in-degree and adjacency list
    in_degree: dict[str, int] = {s.tool: 0 for s in steps}
    dependents: dict[str, list[str]] = {s.tool: [] for s in steps}
    for step in steps:
        for dep in step.depends_on:
            in_degree[step.tool] += 1
            dependents[dep].append(step.tool)

    # Initialise queue with zero-in-degree nodes (preserve original order)
    queue: list[str] = [
        s.tool for s in steps if in_degree[s.tool] == 0
    ]
    sorted_tools: list[str] = []

    while queue:
        tool_name = queue.pop(0)
        sorted_tools.append(tool_name)
        for child in dependents[tool_name]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(sorted_tools) != len(steps):
        raise PipelineError(
            "Cycle detected in pipeline step dependencies"
        )

    return [by_tool[t] for t in sorted_tools]


@dataclass
class PipelineStep:
    """A single step within a pipeline."""

    agent: str
    tool: str
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    """Tool names that must complete before this step runs."""


@dataclass
class Pipeline:
    """A pipeline loaded from ``config/pipelines.yaml``."""

    id: str
    trigger_type: str  # "cron" or "event"
    trigger_value: str  # cron expression or stream key
    steps: list[PipelineStep] = field(default_factory=list)


class PipelineRunner:
    """Orchestrates pipeline execution in response to triggers.

    Event-triggered pipelines subscribe to Redis Streams via the
    :class:`~core.events.bus.EventBus`.  Cron-triggered pipelines are
    evaluated on a 60-second polling interval.

    Args:
        event_bus: Live event bus for subscribing and publishing.
        mcp_registry: Tool name → MCPTool mapping from the gateway.
        approval_gate: Gate instance for evaluating tool risk.
        audit_trail_pool: Optional asyncpg pool; when present, audit
            records are written for each step.
        config_path: Path to ``pipelines.yaml``.  Defaults to
            ``config/pipelines.yaml`` relative to the project root.
    """

    def __init__(
        self,
        *,
        event_bus: Any,
        mcp_registry: dict[str, MCPTool],
        approval_gate: ApprovalGate,
        audit_trail_pool: Any | None = None,
        app_state: Any = None,
        config_path: str | Path = "config/pipelines.yaml",
    ) -> None:
        self._event_bus = event_bus
        self._registry = mcp_registry
        self._gate = approval_gate
        self._pool = audit_trail_pool
        self._app_state = app_state
        self._config_path = config_path
        self.pipelines: list[Pipeline] = []
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    async def _run_with_retries(
        self,
        *,
        operation_name: str,
        correlation_id: str,
        fn: Any,
        max_attempts: int = _RETRY_MAX_ATTEMPTS,
    ) -> Any:
        """Run an awaitable operation with bounded exponential backoff retries."""
        attempt = 1
        while True:
            try:
                return await fn()
            except Exception:
                if attempt >= max_attempts:
                    raise
                delay = _RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "{} retry {}/{} failed (correlation_id={}); backing off {:.2f}s",
                    operation_name,
                    attempt,
                    max_attempts,
                    correlation_id,
                    delay,
                )
                await anyio.sleep(delay)
                attempt += 1

    def _load_pipelines(self) -> list[Pipeline]:
        """Parse ``config/pipelines.yaml`` into :class:`Pipeline` objects."""
        try:
            config = load_config(self._config_path)
        except Exception as exc:
            raise PipelineError(f"Failed to load pipeline config: {exc}") from exc

        raw_pipelines = config.get("pipelines", [])
        result: list[Pipeline] = []

        for raw in raw_pipelines:
            trigger = raw.get("trigger", {})
            trigger_type = trigger.get("type", "")
            if trigger_type == "cron":
                trigger_value = trigger.get("schedule", "")
            elif trigger_type == "event":
                trigger_value = trigger.get("stream", "")
            else:
                logger.warning(
                    "Unknown trigger type '{}' in pipeline '{}'",
                    trigger_type,
                    raw.get("id"),
                )
                continue

            steps = [
                PipelineStep(
                    agent=s.get("agent", ""),
                    tool=s.get("tool", ""),
                    parameters=s.get("parameters", {}),
                    depends_on=s.get("depends_on", []),
                )
                for s in raw.get("steps", [])
            ]
            result.append(
                Pipeline(
                    id=raw["id"],
                    trigger_type=trigger_type,
                    trigger_value=trigger_value,
                    steps=steps,
                )
            )

        return result

    async def start(self) -> None:
        """Load pipelines and start subscription / scheduling tasks."""
        self.pipelines = self._load_pipelines()
        self._running = True

        for pipeline in self.pipelines:
            if pipeline.trigger_type == "event":
                task = asyncio.create_task(
                    self._event_loop(pipeline),
                    name=f"pipeline:{pipeline.id}",
                )
                self._tasks.append(task)
                logger.info(
                    "Pipeline '{}' subscribed to stream '{}'",
                    pipeline.id,
                    pipeline.trigger_value,
                )
            elif pipeline.trigger_type == "cron":
                task = asyncio.create_task(
                    self._cron_loop(pipeline),
                    name=f"pipeline:{pipeline.id}",
                )
                self._tasks.append(task)
                logger.info(
                    "Pipeline '{}' scheduled with cron '{}'",
                    pipeline.id,
                    pipeline.trigger_value,
                )

    async def stop(self) -> None:
        """Cancel all running pipeline tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _event_loop(self, pipeline: Pipeline) -> None:
        """Subscribe to a Redis stream and execute the pipeline on each event."""
        consumer_name = f"pipeline-{pipeline.id}"
        try:
            subscription = self._event_bus.subscribe(pipeline.trigger_value, consumer_name)
            if inspect.isawaitable(subscription):
                subscription = await subscription
            if not hasattr(subscription, "__aiter__"):
                logger.error(
                    "Pipeline '{}' subscribe() did not return an async iterator",
                    pipeline.id,
                )
                return

            async for envelope in subscription:
                if not self._running:
                    return
                logger.info(
                    "Pipeline '{}' triggered by event on '{}'",
                    pipeline.id,
                    pipeline.trigger_value,
                )
                await self._execute_pipeline(pipeline, trigger_payload=envelope.payload)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.error("Pipeline '{}' event loop error: {}", pipeline.id, exc)

    async def _cron_loop(self, pipeline: Pipeline) -> None:
        """Poll-based cron evaluator.

        Checks once per minute whether the current time matches the
        pipeline's cron schedule.  For simplicity this uses a minute-granularity
        match against HH:MM fields of the cron expression.
        """
        try:
            while self._running:
                if self._cron_matches_now(pipeline.trigger_value):
                    logger.info("Pipeline '{}' cron trigger matched", pipeline.id)
                    await self._execute_pipeline(pipeline, trigger_payload={})
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.error("Pipeline '{}' cron loop error: {}", pipeline.id, exc)

    @staticmethod
    def _cron_matches_now(cron_expr: str, *, _now: Any | None = None) -> bool:
        """Match full 5-field cron expressions at UTC minute granularity.

        Args:
            cron_expr: Standard 5-field cron expression.
            _now: Override for current UTC time (testing only).
        """
        from datetime import UTC, datetime

        now = (_now or datetime.now(UTC)).replace(second=0, microsecond=0)
        try:
            next_fire = next(CronSim(cron_expr, now - timedelta(minutes=1)))
        except Exception:
            return False

        return next_fire == now

    async def _execute_pipeline(self, pipeline: Pipeline, *, trigger_payload: Any) -> None:
        """Execute all steps in a pipeline, respecting dependency order."""
        try:
            ordered_steps = _topological_sort(pipeline.steps)
        except PipelineError as exc:
            logger.error(
                "Pipeline '{}' step ordering failed: {}", pipeline.id, exc
            )
            return

        for idx, step in enumerate(ordered_steps):
            tool = self._registry.get(step.tool)
            if tool is None:
                logger.warning(
                    "Pipeline '{}' step {}: tool '{}' not in registry, skipping",
                    pipeline.id,
                    idx,
                    step.tool,
                )
                continue

            merged_params = {**step.parameters}
            if isinstance(trigger_payload, dict):
                merged_params.setdefault("_trigger", trigger_payload)

            await self._execute_step(pipeline.id, step, tool, merged_params)

        # Publish pipeline completion event
        completion = EventEnvelope(
            domain="pipelines",
            category="completed",
            source=f"pipeline:{pipeline.id}",
            correlation_id=f"pipeline:{pipeline.id}:completed",
            priority=EventPriority.LOW,
            payload={"pipeline_id": pipeline.id, "steps": len(pipeline.steps)},
        )
        try:
            await self._run_with_retries(
                operation_name="pipeline_completion_publish",
                correlation_id=completion.correlation_id or "",
                fn=lambda: self._event_bus.publish(completion),
            )
        except Exception as exc:
            logger.warning("Failed to publish pipeline completion event: {}", exc)

    async def _execute_step(
        self,
        pipeline_id: str,
        step: PipelineStep,
        tool: MCPTool,
        parameters: dict[str, Any],
    ) -> None:
        """Execute a single pipeline step through approval → audit → event."""
        approval_req = ApprovalRequest(
            tool_name=step.tool,
            agent_id=step.agent,
            risk_level=RiskLevel(tool.risk_level),
            parameters=parameters,
            correlation_id=f"pipeline:{pipeline_id}:{step.tool}",
        )
        correlation_id = approval_req.correlation_id or ""

        try:
            gate_result = await self._gate.evaluate(approval_req)
        except Exception as exc:
            logger.error(
                "Pipeline '{}' step '{}' approval error: {}",
                pipeline_id,
                step.tool,
                exc,
            )
            return

        # Write audit record if pool is available
        if self._pool is not None:
            trail = AuditTrail(self._pool)
            record = AuditRecord(
                agent_id=step.agent,
                tool_name=step.tool,
                risk_level=tool.risk_level,
                outcome=gate_result.outcome.value,
                reason=gate_result.reason,
                parameters=parameters,
                correlation_id=f"pipeline:{pipeline_id}:{step.tool}",
                flagged_for_summary=gate_result.flagged_for_summary,
            )
            try:
                await trail.insert(record)
            except Exception as exc:
                logger.warning(
                    "Pipeline '{}' step '{}' audit write failed: {}",
                    pipeline_id,
                    step.tool,
                    exc,
                )

        # Publish step completion event
        handler_result: dict[str, Any] | None = None
        if gate_result.outcome == ApprovalOutcome.APPROVED and handler_registry.has(step.tool):
            ctx = HandlerContext(
                agent_id=step.agent,
                correlation_id=correlation_id,
                app_state=self._app_state,
            )
            try:
                handler_result = await self._run_with_retries(
                    operation_name="pipeline_step_handler",
                    correlation_id=correlation_id,
                    fn=lambda: handler_registry.execute(step.tool, parameters, ctx),
                )
                logger.info(
                    "Pipeline '{}' step '{}' handler returned: {} (correlation_id={})",
                    pipeline_id,
                    step.tool,
                    handler_result.get("status", "unknown"),
                    correlation_id,
                )
            except Exception as exc:
                logger.error(
                    "Pipeline '{}' step '{}' handler error: {} (correlation_id={})",
                    pipeline_id,
                    step.tool,
                    exc,
                    correlation_id,
                )

        step_event = EventEnvelope(
            domain="pipelines",
            category="step_completed",
            source=f"pipeline:{pipeline_id}",
            correlation_id=correlation_id,
            priority=EventPriority.NORMAL,
            payload={
                "pipeline_id": pipeline_id,
                "tool_name": step.tool,
                "agent_id": step.agent,
                "outcome": gate_result.outcome.value,
                "parameters": parameters,
                "handler_result": handler_result,
            },
        )
        try:
            await self._run_with_retries(
                operation_name="pipeline_step_publish",
                correlation_id=correlation_id,
                fn=lambda: self._event_bus.publish(step_event),
            )
        except Exception as exc:
            logger.warning(
                "Pipeline '{}' step '{}' event publish failed: {} (correlation_id={})",
                pipeline_id,
                step.tool,
                exc,
                correlation_id,
            )

        logger.info(
            "Pipeline '{}' step '{}' → {}",
            pipeline_id,
            step.tool,
            gate_result.outcome.value,
        )
