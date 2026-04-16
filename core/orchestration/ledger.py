"""Orchestration ledger — persistent storage for workflows, work items,
claims, receipts, swarm notes, decisions, and interrupts.

Uses asyncpg for PostgreSQL access.  All methods accept a ``conn`` parameter
obtained via ``async with pool.acquire() as conn:`` so callers control
transaction boundaries.

Design:

- **One pool, many coroutines**: The ledger holds a reference to an
  ``asyncpg.Pool`` but does NOT own its lifecycle.  Callers create/close
  the pool.
- **Idempotent creates**: ``create_workflow`` returns the existing workflow
  if ``workflow_id`` already exists (ON CONFLICT DO NOTHING + fetch).
- **Status guarded updates**: ``update_workflow_status`` validates the
  transition against the :class:`WorkflowStatus` enum before writing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from core.orchestration.models import (
    Claim,
    DecisionPacket,
    Interrupt,
    Receipt,
    SwarmNote,
    WorkItem,
    Workflow,
    WorkflowStatus,
)


class Ledger:
    """Persistent store for orchestration artifacts.

    Args:
        pg_pool: An ``asyncpg.Pool`` connected to the OsMEN-OC database.
            The caller is responsible for opening and closing this pool.
    """

    def __init__(self, pg_pool: Any) -> None:
        self._pool = pg_pool

    # ── Workflow CRUD ─────────────────────────────────────────────────────

    async def create_workflow(self, wf: Workflow) -> Workflow:
        """Insert a new workflow.  Returns the persisted workflow."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workflows
                    (workflow_id, mode, status, driver_agent_id, request,
                     request_class, created_at, updated_at, context, metadata,
                     source_event_id, source_channel, correlation_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb,
                        $11, $12, $13)
                ON CONFLICT DO NOTHING
                """,
                wf.workflow_id,
                wf.mode,
                wf.status,
                wf.driver_agent_id,
                wf.request,
                wf.request_class,
                wf.created_at,
                wf.updated_at,
                json.dumps(wf.context),
                json.dumps(wf.metadata),
                wf.source_event_id,
                wf.source_channel,
                wf.correlation_id,
            )
        logger.debug("ledger: created workflow {}", wf.workflow_id)
        return wf

    async def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Fetch a workflow by ID.  Returns None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflows WHERE workflow_id = $1",
                workflow_id,
            )
        if row is None:
            return None
        return _row_to_workflow(row)

    async def update_workflow_status(
        self,
        workflow_id: str,
        new_status: WorkflowStatus,
        *,
        error: str | None = None,
        final_synthesis: str | None = None,
    ) -> bool:
        """Transition a workflow to a new status.  Returns True if updated."""
        valid_transitions: dict[str, set[str]] = {
            "created": {"running", "cancelled"},
            "running": {"suspended", "completed", "failed", "cancelled"},
            "suspended": {"running", "cancelled"},
            "completed": set(),
            "failed": {"running"},  # retry
            "cancelled": set(),
        }
        async with self._pool.acquire() as conn:
            # Fetch current status for transition validation
            row = await conn.fetchrow(
                "SELECT status FROM workflows WHERE workflow_id = $1",
                workflow_id,
            )
            if row is None:
                logger.warning("ledger: workflow {} not found for status update", workflow_id)
                return False

            current = row["status"]
            if new_status not in valid_transitions.get(current, set()):
                logger.warning(
                    "ledger: invalid transition {} -> {} for workflow {}",
                    current,
                    new_status,
                    workflow_id,
                )
                return False

            completed_at = "NOW()" if new_status in ("completed", "failed", "cancelled") else None
            set_clauses = ["status = $2", "updated_at = NOW()"]
            params: list[Any] = [workflow_id, new_status]
            idx = 3

            if error is not None:
                set_clauses.append(f"error = ${idx}")
                params.append(error)
                idx += 1
            if final_synthesis is not None:
                set_clauses.append(f"final_synthesis = ${idx}")
                params.append(final_synthesis)
                idx += 1
            if completed_at:
                set_clauses.append("completed_at = NOW()")

            sql = f"UPDATE workflows SET {', '.join(set_clauses)} WHERE workflow_id = $1"
            await conn.execute(sql, *params)
            logger.debug("ledger: workflow {} -> {}", workflow_id, new_status)
            return True

    async def list_workflows(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Workflow]:
        """List workflows, optionally filtered by status."""
        async with self._pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    "SELECT * FROM workflows WHERE status = $1 "
                    "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                    status,
                    limit,
                    offset,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM workflows ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                    limit,
                    offset,
                )
        return [_row_to_workflow(r) for r in rows]

    # ── Work Items ─────────────────────────────────────────────────────────

    async def create_work_item(self, item: WorkItem) -> WorkItem:
        """Insert a new work item."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO work_items
                    (item_id, workflow_id, parent_item_id, agent_id, description,
                     status, priority, depends_on, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
                """,
                item.item_id,
                item.workflow_id,
                item.parent_item_id,
                item.agent_id,
                item.description,
                item.status,
                item.priority,
                item.depends_on,
                json.dumps(item.metadata),
                item.created_at,
            )
        return item

    async def update_work_item(
        self,
        item_id: str,
        *,
        status: str | None = None,
        agent_id: str | None = None,
        result: str | None = None,
        error: str | None = None,
    ) -> bool:
        """Update fields on a work item.  Returns True if a row was updated."""
        set_clauses: list[str] = []
        params: list[Any] = [item_id]
        idx = 2

        field_map = {"status": status, "agent_id": agent_id, "result": result, "error": error}
        for field, value in field_map.items():
            if value is not None:
                set_clauses.append(f"{field} = ${idx}")
                params.append(value)
                idx += 1

        if not set_clauses:
            return False

        # Add timestamp fields based on status transitions
        if status == "assigned":
            set_clauses.append("assigned_at = NOW()")
        elif status == "in_progress":
            set_clauses.append("started_at = NOW()")
        elif status in ("completed", "failed", "skipped"):
            set_clauses.append("completed_at = NOW()")

        sql = f"UPDATE work_items SET {', '.join(set_clauses)} WHERE item_id = $1"
        async with self._pool.acquire() as conn:
            result = await conn.execute(sql, *params)
            updated = int(result.split()[-1])
            return updated > 0

    async def get_work_items(self, workflow_id: str) -> list[WorkItem]:
        """Fetch all work items for a workflow."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM work_items WHERE workflow_id = $1 ORDER BY priority, created_at",
                workflow_id,
            )
        return [_row_to_work_item(r) for r in rows]

    async def get_pending_work_items(self, workflow_id: str) -> list[WorkItem]:
        """Fetch work items that are ready to be assigned (pending, unblocked)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT wi.* FROM work_items wi
                WHERE wi.workflow_id = $1
                  AND wi.status = 'pending'
                  AND NOT EXISTS (
                      SELECT 1 FROM unnest(wi.depends_on) AS dep
                      JOIN work_items dep_wi ON dep_wi.item_id = dep
                      WHERE dep_wi.status NOT IN ('completed', 'skipped')
                  )
                ORDER BY wi.priority, wi.created_at
                """,
                workflow_id,
            )
        return [_row_to_work_item(r) for r in rows]

    # ── Swarm Notes ────────────────────────────────────────────────────────

    async def add_swarm_note(self, note: SwarmNote) -> SwarmNote:
        """Persist a swarm note."""
        emb_str = (
            "[" + ",".join(str(v) for v in note.embedding) + "]"
            if note.embedding
            else None
        )
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO swarm_notes
                    (note_id, workflow_id, agent_id, role, content, note_type,
                     target_item_id, target_claim_id, confidence, embedding,
                     metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::vector, $11::jsonb, $12)
                """,
                note.note_id,
                note.workflow_id,
                note.agent_id,
                note.role,
                note.content,
                note.note_type,
                note.target_item_id,
                note.target_claim_id,
                note.confidence,
                emb_str,
                json.dumps(note.metadata),
                note.created_at,
            )
        return note

    async def get_swarm_notes(
        self,
        workflow_id: str,
        *,
        agent_id: str | None = None,
        note_type: str | None = None,
        limit: int = 100,
    ) -> list[SwarmNote]:
        """Retrieve swarm notes for a workflow."""
        conditions = ["workflow_id = $1"]
        params: list[Any] = [workflow_id]
        idx = 2

        if agent_id:
            conditions.append(f"agent_id = ${idx}")
            params.append(agent_id)
            idx += 1
        if note_type:
            conditions.append(f"note_type = ${idx}")
            params.append(note_type)
            idx += 1

        where = " AND ".join(conditions)
        params.extend([limit])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM swarm_notes WHERE {where} ORDER BY created_at DESC LIMIT ${idx}",
                *params,
            )
        return [_row_to_swarm_note(r) for r in rows]

    # ── Claims ─────────────────────────────────────────────────────────────

    async def create_claim(self, claim: Claim) -> Claim:
        """Insert a new claim."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO claims
                    (claim_id, workflow_id, agent_id, portion_description,
                     analysis, evidence, status, confidence, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
                """,
                claim.claim_id,
                claim.workflow_id,
                claim.agent_id,
                claim.portion_description,
                claim.analysis,
                claim.evidence,
                claim.status,
                claim.confidence,
                json.dumps(claim.metadata),
                claim.created_at,
            )
        return claim

    async def update_claim_status(
        self,
        claim_id: str,
        new_status: str,
    ) -> bool:
        """Update claim status.  Sets repaired_at when status is 'repaired'."""
        async with self._pool.acquire() as conn:
            if new_status == "repaired":
                await conn.execute(
                    "UPDATE claims SET status = $2, repaired_at = NOW() WHERE claim_id = $1",
                    claim_id,
                    new_status,
                )
            else:
                await conn.execute(
                    "UPDATE claims SET status = $2 WHERE claim_id = $1",
                    claim_id,
                    new_status,
                )
            return True

    async def get_claims(self, workflow_id: str) -> list[Claim]:
        """Fetch all claims for a workflow."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM claims WHERE workflow_id = $1 ORDER BY created_at",
                workflow_id,
            )
        return [_row_to_claim(r) for r in rows]

    # ── Receipts ───────────────────────────────────────────────────────────

    async def add_receipt(self, receipt: Receipt) -> Receipt:
        """Persist a receipt."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO receipts
                    (receipt_id, workflow_id, agent_id, target_type, target_id,
                     outcome, result_summary, error_detail, duration_ms,
                     model_used, compute_backend, tokens_in, tokens_out,
                     metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb, $15)
                """,
                receipt.receipt_id,
                receipt.workflow_id,
                receipt.agent_id,
                receipt.target_type,
                receipt.target_id,
                receipt.outcome,
                receipt.result_summary,
                receipt.error_detail,
                receipt.duration_ms,
                receipt.model_used,
                receipt.compute_backend,
                receipt.tokens_in,
                receipt.tokens_out,
                json.dumps(receipt.metadata),
                receipt.created_at,
            )
        return receipt

    async def get_receipts(self, workflow_id: str) -> list[Receipt]:
        """Fetch all receipts for a workflow."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM receipts WHERE workflow_id = $1 ORDER BY created_at",
                workflow_id,
            )
        return [_row_to_receipt(r) for r in rows]

    # ── Decision Packets ───────────────────────────────────────────────────

    async def add_decision(self, decision: DecisionPacket) -> DecisionPacket:
        """Persist a decision packet."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO decision_packets
                    (packet_id, workflow_id, agent_id, decision_type, trigger,
                     alternatives, chosen, reasoning, confidence, metadata,
                     created_at)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10::jsonb, $11)
                """,
                decision.packet_id,
                decision.workflow_id,
                decision.agent_id,
                decision.decision_type,
                decision.trigger,
                json.dumps(decision.alternatives),
                decision.chosen,
                decision.reasoning,
                decision.confidence,
                json.dumps(decision.metadata),
                decision.created_at,
            )
        return decision

    async def get_decisions(self, workflow_id: str) -> list[DecisionPacket]:
        """Fetch all decision packets for a workflow."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM decision_packets WHERE workflow_id = $1 ORDER BY created_at",
                workflow_id,
            )
        return [_row_to_decision(r) for r in rows]

    # ── Interrupts ─────────────────────────────────────────────────────────

    async def add_interrupt(self, interrupt: Interrupt) -> Interrupt:
        """Persist an interrupt."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO interrupts
                    (interrupt_id, workflow_id, kind, message, source_agent_id,
                     target_agent_id, target_item_id, context, metadata,
                     created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10)
                """,
                interrupt.interrupt_id,
                interrupt.workflow_id,
                interrupt.kind,
                interrupt.message,
                interrupt.source_agent_id,
                interrupt.target_agent_id,
                interrupt.target_item_id,
                json.dumps(interrupt.context),
                json.dumps(interrupt.metadata),
                interrupt.created_at,
            )
        return interrupt

    async def resolve_interrupt(
        self,
        interrupt_id: str,
        resolution: str,
    ) -> bool:
        """Mark an interrupt as resolved."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE interrupts SET resolution = $2, resolved_at = NOW() "
                "WHERE interrupt_id = $1 AND resolution IS NULL",
                interrupt_id,
                resolution,
            )
            return int(result.split()[-1]) > 0

    async def get_unresolved_interrupts(self, workflow_id: str) -> list[Interrupt]:
        """Fetch unresolved interrupts for a workflow."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM interrupts WHERE workflow_id = $1 AND resolution IS NULL "
                "ORDER BY created_at",
                workflow_id,
            )
        return [_row_to_interrupt(r) for r in rows]


# ── Row-to-model converters ─────────────────────────────────────────────────


def _row_to_workflow(row: Any) -> Workflow:
    """Convert an asyncpg Record to a Workflow model."""
    return Workflow(
        workflow_id=row["workflow_id"],
        mode=row["mode"],
        status=row["status"],
        driver_agent_id=row["driver_agent_id"],
        request=row["request"],
        request_class=row["request_class"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
        context=row["context"] if isinstance(row["context"], dict) else {},
        metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
        source_event_id=row["source_event_id"],
        source_channel=row["source_channel"],
        correlation_id=row["correlation_id"],
        final_synthesis=row["final_synthesis"],
        error=row["error"],
    )


def _row_to_work_item(row: Any) -> WorkItem:
    return WorkItem(
        item_id=row["item_id"],
        workflow_id=row["workflow_id"],
        parent_item_id=row["parent_item_id"],
        agent_id=row["agent_id"],
        description=row["description"],
        status=row["status"],
        priority=row["priority"],
        depends_on=row["depends_on"],
        result=row["result"],
        error=row["error"],
        assigned_at=row["assigned_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        created_at=row["created_at"],
        metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
    )


def _row_to_swarm_note(row: Any) -> SwarmNote:
    return SwarmNote(
        note_id=row["note_id"],
        workflow_id=row["workflow_id"],
        agent_id=row["agent_id"],
        role=row["role"],
        content=row["content"],
        note_type=row["note_type"],
        target_item_id=row["target_item_id"],
        target_claim_id=row["target_claim_id"],
        confidence=row["confidence"],
        embedding=row["embedding"],
        created_at=row["created_at"],
        metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
    )


def _row_to_claim(row: Any) -> Claim:
    return Claim(
        claim_id=row["claim_id"],
        workflow_id=row["workflow_id"],
        agent_id=row["agent_id"],
        portion_description=row["portion_description"],
        analysis=row["analysis"],
        evidence=row["evidence"],
        status=row["status"],
        confidence=row["confidence"],
        created_at=row["created_at"],
        repaired_at=row["repaired_at"],
        metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
    )


def _row_to_receipt(row: Any) -> Receipt:
    return Receipt(
        receipt_id=row["receipt_id"],
        workflow_id=row["workflow_id"],
        agent_id=row["agent_id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        outcome=row["outcome"],
        result_summary=row["result_summary"],
        error_detail=row["error_detail"],
        duration_ms=row["duration_ms"],
        model_used=row["model_used"],
        compute_backend=row["compute_backend"],
        tokens_in=row["tokens_in"],
        tokens_out=row["tokens_out"],
        created_at=row["created_at"],
        metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
    )


def _row_to_decision(row: Any) -> DecisionPacket:
    return DecisionPacket(
        packet_id=row["packet_id"],
        workflow_id=row["workflow_id"],
        agent_id=row["agent_id"],
        decision_type=row["decision_type"],
        trigger=row["trigger"],
        alternatives=row["alternatives"] if isinstance(row["alternatives"], list) else [],
        chosen=row["chosen"],
        reasoning=row["reasoning"],
        confidence=row["confidence"],
        created_at=row["created_at"],
        metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
    )


def _row_to_interrupt(row: Any) -> Interrupt:
    return Interrupt(
        interrupt_id=row["interrupt_id"],
        workflow_id=row["workflow_id"],
        kind=row["kind"],
        message=row["message"],
        source_agent_id=row["source_agent_id"],
        target_agent_id=row["target_agent_id"],
        target_item_id=row["target_item_id"],
        context=row["context"] if isinstance(row["context"], dict) else {},
        resolution=row["resolution"],
        resolved_at=row["resolved_at"],
        created_at=row["created_at"],
        metadata=row["metadata"] if isinstance(row["metadata"], dict) else {},
    )
