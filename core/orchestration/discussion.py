"""Mode B — Discussion Engine (Claim / Attack / Repair / Synthesize loop).

Multiple agents independently claim portions of a task, produce parallel
analyses, critique each other's work, and synthesize a final output.

Discussion phases::

    1. CLAIM    — Agents claim sub-problems (parallel, time-bounded).
    2. ATTACK   — Agents critique other agents' claims (parallel).
    3. REPAIR   — Claimed agents revise based on critique.
    4. SYNTHESIZE — Driver merges all claims into a final output.

Each phase has a configurable timeout and iteration limit.  The loop
can repeat ATTACK → REPAIR for multiple rounds until convergence
is detected (claims stabilize) or the iteration limit is hit.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from loguru import logger

from core.orchestration.ledger import Ledger
from core.orchestration.models import (
    Claim,
    DecisionPacket,
    Interrupt,
    InterruptKind,
    Receipt,
    SwarmNote,
    Workflow,
    WorkflowStatus,
)
from core.orchestration.watchdogs import (
    NoveltyWatchdog,
    VelocityWatchdog,
)

AsyncCallback = Callable[..., Coroutine[Any, Any, None]] | None


class DiscussionEngine:
    """Mode B discussion engine.

    Args:
        ledger: The orchestration ledger.
        max_rounds: Maximum ATTACK → REPAIR iterations.
        claim_timeout_seconds: Time to wait for claims before moving on.
        attack_timeout_seconds: Time to wait for attacks per round.
        repair_timeout_seconds: Time to wait for repairs per round.
        convergence_threshold: Fraction of claims that must be unchanged
            between rounds to consider the discussion converged.
        on_phase_change: Callback when the discussion phase changes.
            Receives ``(workflow_id, phase, round_num)``.
        on_claim_received: Callback when a claim is submitted.
            Receives ``(workflow_id, claim)``.
        on_completed: Callback when discussion completes.
            Receives ``(workflow_id, workflow)``.
    """

    def __init__(
        self,
        ledger: Ledger,
        *,
        max_rounds: int = 3,
        claim_timeout_seconds: int = 60,
        attack_timeout_seconds: int = 45,
        repair_timeout_seconds: int = 45,
        convergence_threshold: float = 0.7,
        on_phase_change: AsyncCallback = None,
        on_claim_received: AsyncCallback = None,
        on_completed: AsyncCallback = None,
    ) -> None:
        self._ledger = ledger
        self._max_rounds = max_rounds
        self._claim_timeout = claim_timeout_seconds
        self._attack_timeout = attack_timeout_seconds
        self._repair_timeout = repair_timeout_seconds
        self._convergence_threshold = convergence_threshold
        self._on_phase_change = on_phase_change
        self._on_claim_received = on_claim_received
        self._on_completed = on_completed

        self._novelty_watchdog = NoveltyWatchdog()
        self._velocity_watchdog = VelocityWatchdog()
        self._active: dict[str, asyncio.Task] = {}

    # ── Public API ──────────────────────────────────────────────────────────

    async def start_discussion(self, workflow_id: str) -> None:
        """Begin the discussion loop for a workflow.

        The workflow must already exist in the ledger with status RUNNING.
        """
        updated = await self._ledger.update_workflow_status(
            workflow_id, WorkflowStatus.RUNNING
        )
        if not updated:
            logger.error("discussion: cannot start workflow {}", workflow_id)
            return

        task = asyncio.create_task(
            self._discussion_loop(workflow_id),
            name=f"discussion-{workflow_id}",
        )
        self._active[workflow_id] = task
        logger.info("discussion: started for workflow {}", workflow_id)

    async def submit_claim(self, claim: Claim) -> None:
        """An agent submits a claim for a portion of the task."""
        await self._ledger.create_claim(claim)

        if self._on_claim_received:
            await self._on_claim_received(claim.workflow_id, claim)

        logger.debug(
            "discussion: claim {} by agent {} in workflow {}",
            claim.claim_id,
            claim.agent_id,
            claim.workflow_id,
        )

    async def submit_attack(
        self,
        workflow_id: str,
        attacker_agent_id: str,
        target_claim_id: str,
        critique: str,
    ) -> SwarmNote:
        """An agent attacks (critiques) another agent's claim.

        Records the attack as a swarm note and updates the claim status.
        Returns the swarm note that was created.
        """
        # Update claim status
        await self._ledger.update_claim_status(target_claim_id, "attacked")

        # Record the critique as a note
        note = SwarmNote(
            workflow_id=workflow_id,
            agent_id=attacker_agent_id,
            role="critic",
            content=critique,
            note_type="observation",
            target_claim_id=target_claim_id,
        )
        await self._ledger.add_swarm_note(note)

        logger.debug(
            "discussion: agent {} attacked claim {} in workflow {}",
            attacker_agent_id,
            target_claim_id,
            workflow_id,
        )
        return note

    async def submit_repair(
        self,
        claim_id: str,
        revised_analysis: str,
    ) -> None:
        """A claim author repairs their claim after an attack.

        Updates the claim with revised analysis and status.
        """
        # This requires a direct DB update since we need to update
        # both status and analysis atomically
        import json
        from core.orchestration.ledger import Ledger

        pool = self._ledger._pool
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE claims SET status = 'repaired', analysis = $2, repaired_at = NOW() "
                "WHERE claim_id = $1",
                claim_id,
                revised_analysis,
            )
        logger.debug("discussion: claim {} repaired", claim_id)

    async def submit_synthesis(
        self,
        workflow_id: str,
        agent_id: str,
        synthesis: str,
    ) -> DecisionPacket:
        """The driver submits the final synthesis of the discussion.

        Records a decision packet and marks the workflow as completed.
        """
        decision = DecisionPacket(
            workflow_id=workflow_id,
            agent_id=agent_id,
            decision_type="synthesize",
            trigger="discussion_complete",
            chosen=synthesis,
            reasoning="Final synthesis from discussion loop",
        )
        await self._ledger.add_decision(decision)

        await self._ledger.update_workflow_status(
            workflow_id,
            WorkflowStatus.COMPLETED,
            final_synthesis=synthesis,
        )

        self._active.pop(workflow_id, None)

        if self._on_completed:
            wf = await self._ledger.get_workflow(workflow_id)
            if wf:
                await self._on_completed(workflow_id, wf)

        logger.info("discussion: workflow {} synthesized and completed", workflow_id)
        return decision

    async def cancel_discussion(self, workflow_id: str) -> bool:
        """Cancel a running discussion."""
        task = self._active.pop(workflow_id, None)
        if task:
            task.cancel()
        return await self._ledger.update_workflow_status(
            workflow_id, WorkflowStatus.CANCELLED
        )

    # ── Internal ────────────────────────────────────────────────────────────

    async def _discussion_loop(self, workflow_id: str) -> None:
        """Main discussion loop: claim → attack → repair → synthesize."""
        try:
            # Phase 1: CLAIM
            await self._emit_phase(workflow_id, "claim", 0)
            await asyncio.sleep(self._claim_timeout)

            # Phase 2-3: ATTACK → REPAIR (repeatable)
            for round_num in range(1, self._max_rounds + 1):
                # ATTACK
                await self._emit_phase(workflow_id, "attack", round_num)
                await asyncio.sleep(self._attack_timeout)

                # Check convergence
                if await self._check_convergence(workflow_id, round_num):
                    logger.info(
                        "discussion: workflow {} converged at round {}",
                        workflow_id,
                        round_num,
                    )
                    break

                # REPAIR
                await self._emit_phase(workflow_id, "repair", round_num)
                await asyncio.sleep(self._repair_timeout)

                # Run watchdogs
                await self._run_watchdogs(workflow_id)

                # Check for interrupts
                interrupts = await self._ledger.get_unresolved_interrupts(workflow_id)
                if interrupts:
                    logger.debug(
                        "discussion: workflow {} suspended due to {} interrupts",
                        workflow_id,
                        len(interrupts),
                    )
                    await self._ledger.update_workflow_status(
                        workflow_id, WorkflowStatus.SUSPENDED
                    )
                    return

            # Phase 4: SYNTHESIZE — signal that discussion is ready for synthesis
            await self._emit_phase(workflow_id, "synthesize", self._max_rounds)

            # Record a synthesis-needed decision
            decision = DecisionPacket(
                workflow_id=workflow_id,
                agent_id="system",
                decision_type="synthesize",
                trigger="discussion_rounds_exhausted",
                reasoning="Discussion phases complete, ready for driver synthesis",
            )
            await self._ledger.add_decision(decision)

            logger.info(
                "discussion: workflow {} ready for synthesis",
                workflow_id,
            )

        except asyncio.CancelledError:
            logger.info("discussion: workflow {} loop cancelled", workflow_id)
            raise
        except Exception as exc:
            logger.error("discussion: workflow {} error: {}", workflow_id, exc)
            await self._ledger.update_workflow_status(
                workflow_id, WorkflowStatus.FAILED, error=str(exc)
            )

    async def _emit_phase(
        self,
        workflow_id: str,
        phase: str,
        round_num: int,
    ) -> None:
        """Emit a phase change event."""
        if self._on_phase_change:
            await self._on_phase_change(workflow_id, phase, round_num)

        # Record as a swarm note for audit trail
        await self._ledger.add_swarm_note(
            SwarmNote(
                workflow_id=workflow_id,
                agent_id="system",
                role="facilitator",
                content=f"Discussion phase: {phase} (round {round_num})",
                note_type="observation",
            )
        )

    async def _check_convergence(
        self,
        workflow_id: str,
        round_num: int,
    ) -> bool:
        """Check if claims have stabilized (convergence detected).

        Convergence: >= 70% of claims are in 'accepted' or 'repaired' status
        and haven't been attacked again in this round.
        """
        claims = await self._ledger.get_claims(workflow_id)
        if not claims:
            return False

        stable = sum(
            1
            for c in claims
            if c.status in ("accepted", "repaired")
        )
        ratio = stable / len(claims)
        return ratio >= self._convergence_threshold

    async def _run_watchdogs(self, workflow_id: str) -> None:
        """Run novelty and velocity watchdogs."""
        notes = await self._ledger.get_swarm_notes(workflow_id, limit=100)

        interrupt = self._novelty_watchdog.check(workflow_id, notes)
        if interrupt:
            await self._ledger.add_interrupt(interrupt)
            return

        # Velocity check needs receipts too
        receipts = await self._ledger.get_receipts(workflow_id)
        interrupt = self._velocity_watchdog.check(workflow_id, notes, receipts)
        if interrupt:
            await self._ledger.add_interrupt(interrupt)
