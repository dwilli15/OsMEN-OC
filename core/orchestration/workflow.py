"""Mode A — Cooperative Workflow Engine.

The driver agent decomposes a request into work items, assigns each to
a worker agent, collects receipts, and synthesizes a final result.

Lifecycle::

    CREATED → RUNNING → COMPLETED
                  ↘ FAILED
                  ↘ SUSPENDED → RUNNING (on resume)

The engine is driven by an async event loop that:

1. Runs the driver's decomposition pass (produces work items).
2. Dispatches pending items to available workers.
3. Collects receipts as workers complete.
4. Runs watchdogs after each receipt.
5. Synthesizes the final result when all items are resolved.
6. Writes the synthesis to the ledger and transitions to COMPLETED.

The engine is designed to be **external-driver** — it doesn't call LLMs
itself.  Instead, it emits events on the bus that agents subscribe to,
and agents submit receipts via the bus or direct API calls.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from loguru import logger

from core.orchestration.ledger import Ledger
from core.orchestration.models import (
    DecisionPacket,
    Interrupt,
    Receipt,
    SwarmNote,
    WorkItem,
    WorkItemStatus,
    Workflow,
    WorkflowStatus,
)
from core.orchestration.watchdogs import (
    NoveltyWatchdog,
    ReceiptWatchdog,
    TokenBudgetWatchdog,
    VelocityWatchdog,
)


# Type alias for optional async callback
AsyncCallback = Callable[..., Coroutine[Any, Any, None]] | None


class CooperativeEngine:
    """Mode A cooperative workflow engine.

    Args:
        ledger: The orchestration ledger.
        on_work_item_ready: Callback fired when a work item is ready for
            assignment.  Receives ``(workflow_id, work_item)``.
        on_receipt_received: Callback fired when a receipt arrives.
            Receives ``(workflow_id, receipt)``.
        on_interrupt: Callback fired when a watchdog triggers.
            Receives ``(workflow_id, interrupt)``.
        on_completed: Callback fired when the workflow completes.
            Receives ``(workflow_id, workflow)``.
        on_failed: Callback fired when the workflow fails.
            Receives ``(workflow_id, workflow, error)``.
    """

    def __init__(
        self,
        ledger: Ledger,
        *,
        on_work_item_ready: AsyncCallback = None,
        on_receipt_received: AsyncCallback = None,
        on_interrupt: AsyncCallback = None,
        on_completed: AsyncCallback = None,
        on_failed: AsyncCallback = None,
    ) -> None:
        self._ledger = ledger
        self._on_work_item_ready = on_work_item_ready
        self._on_receipt_received = on_receipt_received
        self._on_interrupt = on_interrupt
        self._on_completed = on_completed
        self._on_failed = on_failed

        # Watchdogs
        self._token_watchdog = TokenBudgetWatchdog()
        self._novelty_watchdog = NoveltyWatchdog()
        self._velocity_watchdog = VelocityWatchdog()
        self._receipt_watchdog = ReceiptWatchdog()

        # Track active workflows
        self._active_workflows: dict[str, asyncio.Task] = {}

    # ── Workflow Lifecycle ──────────────────────────────────────────────────

    async def start_workflow(
        self,
        workflow_id: str,
        work_items: list[WorkItem],
    ) -> None:
        """Start the cooperative execution loop for a workflow.

        Args:
            workflow_id: The workflow to start.
            work_items: Initial work items produced by the driver.
        """
        # Create work items in the ledger
        for item in work_items:
            item.workflow_id = workflow_id
            await self._ledger.create_work_item(item)

        # Transition to RUNNING
        updated = await self._ledger.update_workflow_status(
            workflow_id, WorkflowStatus.RUNNING
        )
        if not updated:
            logger.error("engine: cannot start workflow {} — invalid status transition", workflow_id)
            return

        logger.info(
            "engine: workflow {} started with {} work items",
            workflow_id,
            len(work_items),
        )

        # Start the dispatch loop as a background task
        task = asyncio.create_task(
            self._dispatch_loop(workflow_id),
            name=f"workflow-{workflow_id}",
        )
        self._active_workflows[workflow_id] = task

    async def submit_receipt(self, receipt: Receipt) -> None:
        """Submit a receipt from a worker agent.

        Updates the corresponding work item status and triggers
        watchdog checks.
        """
        await self._ledger.add_receipt(receipt)

        # Update the work item based on receipt outcome
        if receipt.outcome == "success":
            await self._ledger.update_work_item(
                receipt.target_id,
                status=WorkItemStatus.COMPLETED,
                result=receipt.result_summary,
            )
        elif receipt.outcome == "failure":
            await self._ledger.update_work_item(
                receipt.target_id,
                status=WorkItemStatus.FAILED,
                error=receipt.error_detail,
            )
        elif receipt.outcome == "partial":
            # Partial success — leave in_progress, add note
            await self._ledger.add_swarm_note(
                SwarmNote(
                    workflow_id=receipt.workflow_id,
                    agent_id=receipt.agent_id,
                    role="worker",
                    content=f"Partial result: {receipt.result_summary}",
                    note_type="observation",
                    target_item_id=receipt.target_id,
                    confidence=0.5,
                )
            )

        if self._on_receipt_received:
            await self._on_receipt_received(receipt.workflow_id, receipt)

        logger.debug(
            "engine: receipt {} for {} {} in workflow {}",
            receipt.receipt_id,
            receipt.target_type,
            receipt.target_id,
            receipt.workflow_id,
        )

    async def submit_note(self, note: SwarmNote) -> None:
        """Submit a swarm note from any agent."""
        await self._ledger.add_swarm_note(note)

    async def submit_decision(self, decision: DecisionPacket) -> None:
        """Submit a decision packet from the driver."""
        await self._ledger.add_decision(decision)

    async def submit_interrupt(self, interrupt: Interrupt) -> None:
        """Submit an external interrupt."""
        await self._ledger.add_interrupt(interrupt)
        if interrupt.kind.value == "storm_detected":
            await self._ledger.update_workflow_status(
                interrupt.workflow_id, WorkflowStatus.SUSPENDED
            )
        if self._on_interrupt:
            await self._on_interrupt(interrupt.workflow_id, interrupt)

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow.  Returns True if cancelled."""
        task = self._active_workflows.pop(workflow_id, None)
        if task:
            task.cancel()
        return await self._ledger.update_workflow_status(
            workflow_id, WorkflowStatus.CANCELLED
        )

    async def add_work_items(
        self,
        workflow_id: str,
        items: list[WorkItem],
    ) -> None:
        """Add new work items to a running workflow (dynamic decomposition)."""
        for item in items:
            item.workflow_id = workflow_id
            await self._ledger.create_work_item(item)
        logger.debug(
            "engine: added {} work items to workflow {}",
            len(items),
            workflow_id,
        )

    # ── Internal ────────────────────────────────────────────────────────────

    async def _dispatch_loop(self, workflow_id: str) -> None:
        """Main loop: dispatch pending items, collect receipts, check completion."""
        try:
            while True:
                # 1. Check for pending work items
                pending = await self._ledger.get_pending_work_items(workflow_id)

                if pending:
                    for item in pending:
                        if self._on_work_item_ready:
                            await self._on_work_item_ready(workflow_id, item)
                        else:
                            logger.debug(
                                "engine: work item {} ready (no handler assigned)",
                                item.item_id,
                            )

                # 2. Check if workflow is complete
                all_items = await self._ledger.get_work_items(workflow_id)
                terminal_statuses = {
                    WorkItemStatus.COMPLETED,
                    WorkItemStatus.FAILED,
                    WorkItemStatus.SKIPPED,
                }
                non_blocked = [i for i in all_items if i.status != WorkItemStatus.BLOCKED]

                if non_blocked and all(i.status in terminal_statuses for i in non_blocked):
                    await self._complete_workflow(workflow_id, all_items)
                    return

                # 3. Run watchdogs
                await self._run_watchdogs(workflow_id)

                # 4. Check for unresolved interrupts
                interrupts = await self._ledger.get_unresolved_interrupts(workflow_id)
                if interrupts:
                    # Don't dispatch more work while interrupts are pending
                    for intr in interrupts:
                        if self._on_interrupt:
                            await self._on_interrupt(workflow_id, intr)
                    logger.debug(
                        "engine: workflow {} has {} unresolved interrupts, pausing dispatch",
                        workflow_id,
                        len(interrupts),
                    )
                    await asyncio.sleep(5)
                    continue

                # 5. Wait before next iteration
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            logger.info("engine: workflow {} dispatch loop cancelled", workflow_id)
            raise
        except Exception as exc:
            logger.error("engine: workflow {} dispatch loop error: {}", workflow_id, exc)
            await self._ledger.update_workflow_status(
                workflow_id,
                WorkflowStatus.FAILED,
                error=str(exc),
            )
            if self._on_failed:
                await self._on_failed(workflow_id, None, str(exc))

    async def _complete_workflow(
        self,
        workflow_id: str,
        items: list[WorkItem],
    ) -> None:
        """Mark workflow as completed with a synthesis."""
        # Build a basic synthesis from work item results
        results = []
        for item in items:
            if item.result:
                results.append(f"[{item.description}]: {item.result}")
            elif item.error:
                results.append(f"[{item.description}]: FAILED — {item.error}")

        synthesis = "\n".join(results) if results else "All work items resolved."

        await self._ledger.update_workflow_status(
            workflow_id,
            WorkflowStatus.COMPLETED,
            final_synthesis=synthesis,
        )

        self._active_workflows.pop(workflow_id, None)

        if self._on_completed:
            wf = await self._ledger.get_workflow(workflow_id)
            if wf:
                await self._on_completed(workflow_id, wf)

        logger.info("engine: workflow {} completed", workflow_id)

    async def _run_watchdogs(self, workflow_id: str) -> None:
        """Run all watchdogs and process any interrupts they produce."""
        notes = await self._ledger.get_swarm_notes(workflow_id, limit=100)
        receipts = await self._ledger.get_receipts(workflow_id)

        # Token budget
        interrupt = self._token_watchdog.check(workflow_id, receipts)
        if interrupt:
            await self.submit_interrupt(interrupt)
            return

        # Novelty
        interrupt = self._novelty_watchdog.check(workflow_id, notes)
        if interrupt:
            await self.submit_interrupt(interrupt)
            return

        # Velocity
        interrupt = self._velocity_watchdog.check(workflow_id, notes, receipts)
        if interrupt:
            await self.submit_interrupt(interrupt)
            return

        # Receipt absence
        items = await self._ledger.get_work_items(workflow_id)
        interrupts = self._receipt_watchdog.check_work_items(workflow_id, items, receipts)
        for intr in interrupts:
            await self.submit_interrupt(intr)
