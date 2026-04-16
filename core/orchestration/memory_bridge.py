"""Memory bridge — persists orchestration artifacts into the unified memory store.

After a workflow completes, the memory bridge extracts key insights,
decisions, and learnings from the workflow artifacts and promotes them
to long-term memory.  This ensures that orchestration outcomes are
searchable and available for future workflows.

What gets persisted:

- **Decision packets**: The reasoning chain and chosen path.
- **High-confidence swarm notes**: Notes with confidence >= threshold.
- **Final synthesis**: The workflow's output.
- **Error patterns**: Failed work items and their causes.

The bridge uses the same ``MemoryHub`` interface as other memory
producers, ensuring orchestration artifacts participate in the same
promotion, decay, and expiration lifecycle.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from core.orchestration.models import (
    Claim,
    DecisionPacket,
    SwarmNote,
    WorkItem,
    Workflow,
    WorkflowStatus,
)
from core.orchestration.ledger import Ledger


# ── Constants ───────────────────────────────────────────────────────────────

# Minimum confidence for a swarm note to be promoted to memory
MIN_NOTE_CONFIDENCE = 0.7

# Maximum notes to extract per workflow (avoids flooding memory)
MAX_NOTES_PER_WORKFLOW = 10

# Memory types used for orchestration artifacts
_MEMORY_TYPE_MAP = {
    "decision": "decision",
    "synthesis": "context",
    "error": "learning",
    "claim_accepted": "fact",
    "high_confidence_note": "observation",
}


class MemoryBridge:
    """Bridges orchestration artifacts to the memory store.

    Args:
        ledger: The orchestration ledger for reading workflow data.
        memory_store: A ``MemoryHub``-compatible store for writing memories.
            Must support an ``add()`` method with the standard signature.
    """

    def __init__(
        self,
        ledger: Ledger,
        memory_store: Any,
        *,
        min_confidence: float = MIN_NOTE_CONFIDENCE,
        max_notes: int = MAX_NOTES_PER_WORKFLOW,
    ) -> None:
        self._ledger = ledger
        self._store = memory_store
        self._min_confidence = min_confidence
        self._max_notes = max_notes

    async def persist_workflow(self, workflow_id: str) -> int:
        """Extract and persist key artifacts from a completed workflow.

        Args:
            workflow_id: The workflow to persist.

        Returns:
            Number of memories created.
        """
        wf = await self._ledger.get_workflow(workflow_id)
        if wf is None:
            logger.warning("memory_bridge: workflow {} not found", workflow_id)
            return 0

        if wf.status != WorkflowStatus.COMPLETED:
            logger.debug(
                "memory_bridge: skipping workflow {} (status={})",
                workflow_id,
                wf.status,
            )
            return 0

        count = 0

        # 1. Persist final synthesis
        if wf.final_synthesis:
            count += await self._persist_memory(
                agent_id="orchestrator",
                memory_type="context",
                content=wf.final_synthesis,
                source=f"workflow:{workflow_id}",
                importance=0.8,
            )

        # 2. Persist decision packets
        decisions = await self._ledger.get_decisions(workflow_id)
        for decision in decisions:
            content = self._format_decision(decision)
            count += await self._persist_memory(
                agent_id=decision.agent_id,
                memory_type="decision",
                content=content,
                source=f"workflow:{workflow_id}:decision:{decision.packet_id}",
                importance=decision.confidence,
            )

        # 3. Persist high-confidence swarm notes (sorted by confidence desc)
        notes = await self._ledger.get_swarm_notes(
            workflow_id, limit=self._max_notes
        )
        # Filter and sort by confidence
        high_conf = [
            n for n in notes
            if n.confidence >= self._min_confidence
            and n.note_type != "observation"  # skip generic observations
        ]
        high_conf.sort(key=lambda n: n.confidence, reverse=True)
        high_conf = high_conf[: self._max_notes]

        for note in high_conf:
            content = f"[{note.role}] {note.content}"
            count += await self._persist_memory(
                agent_id=note.agent_id,
                memory_type="observation",
                content=content,
                source=f"workflow:{workflow_id}:note:{note.note_id}",
                importance=note.confidence,
            )

        # 4. Persist error patterns from failed work items
        items = await self._ledger.get_work_items(workflow_id)
        for item in items:
            if item.status == "failed" and item.error:
                content = (
                    f"Work item '{item.description}' failed: {item.error}"
                )
                count += await self._persist_memory(
                    agent_id=item.agent_id or "unknown",
                    memory_type="learning",
                    content=content,
                    source=f"workflow:{workflow_id}:item:{item.item_id}",
                    importance=0.6,
                )

        # 5. Persist accepted claims (Mode B)
        claims = await self._ledger.get_claims(workflow_id)
        for claim in claims:
            if claim.status == "accepted" and claim.analysis:
                content = (
                    f"Claim by {claim.agent_id}: {claim.portion_description}\n"
                    f"Analysis: {claim.analysis}"
                )
                count += await self._persist_memory(
                    agent_id=claim.agent_id,
                    memory_type="fact",
                    content=content,
                    source=f"workflow:{workflow_id}:claim:{claim.claim_id}",
                    importance=claim.confidence,
                )

        logger.info(
            "memory_bridge: persisted {} memories from workflow {}",
            count,
            workflow_id,
        )
        return count

    async def persist_decision(self, decision: DecisionPacket) -> bool:
        """Persist a single decision packet immediately.

        Useful for real-time decision logging during workflow execution.
        """
        content = self._format_decision(decision)
        count = await self._persist_memory(
            agent_id=decision.agent_id,
            memory_type="decision",
            content=content,
            source=f"decision:{decision.packet_id}",
            importance=decision.confidence,
        )
        return count > 0

    # ── Internal ────────────────────────────────────────────────────────────

    async def _persist_memory(
        self,
        *,
        agent_id: str,
        memory_type: str,
        content: str,
        source: str,
        importance: float,
    ) -> int:
        """Write a single memory entry to the store."""
        try:
            if self._store is None:
                return 0

            # The memory store interface: store.add(agent_id, content, type, ...)
            # We use a duck-typed approach — try the standard interface
            if hasattr(self._store, "add"):
                await self._store.add(
                    agent_id=agent_id,
                    content=content,
                    memory_type=memory_type,
                    importance=importance,
                    source=source,
                )
                return 1

            # Alternative: direct Redis/DB write
            logger.debug(
                "memory_bridge: store has no add() method, skipping memory write"
            )
            return 0
        except Exception as exc:
            logger.error(
                "memory_bridge: failed to persist memory: {}",
                exc,
            )
            return 0

    @staticmethod
    def _format_decision(decision: DecisionPacket) -> str:
        """Format a decision packet as readable text for memory storage."""
        parts = [
            f"Decision: {decision.decision_type}",
            f"Trigger: {decision.trigger}",
            f"Chosen: {decision.chosen}",
            f"Reasoning: {decision.reasoning}",
        ]
        if decision.alternatives:
            alt_text = ", ".join(
                str(a.get("option", a)) if isinstance(a, dict) else str(a)
                for a in decision.alternatives
            )
            parts.append(f"Alternatives: {alt_text}")
        return " | ".join(parts)
