"""Typed data models for the orchestration ledger.

All models use Pydantic v2 for validation and serialisation.  Ledger
persistence uses asyncpg with a companion migration (``003_orchestration.sql``)
that mirrors these structures as PostgreSQL tables.

Design principles:

- **Immutability where possible**: ``SwarmNote``, ``Claim``, ``Receipt``,
  and ``DecisionPacket`` are frozen once created.  Mutations produce new
  instances (append-only audit trail).
- **Status enums are closed**: Every state machine transition is explicit;
  no free-form strings in status fields.
- **Correlation by ``workflow_id``**: All artifacts within a workflow
  share the same ``workflow_id`` for efficient ledger queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ── Workflow ────────────────────────────────────────────────────────────────


class WorkflowMode(StrEnum):
    """Execution strategy for a workflow."""

    COOPERATIVE = "cooperative"  # Mode A: driver decomposes, workers execute
    DISCUSSION = "discussion"  # Mode B: parallel claim/attack/repair/synthesize


class WorkflowStatus(StrEnum):
    """Lifecycle state of a workflow."""

    CREATED = "created"
    RUNNING = "running"
    SUSPENDED = "suspended"  # waiting for external input
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Workflow(BaseModel):
    """Top-level orchestration unit.

    A workflow represents one end-to-end processing pipeline triggered
    by an ingress event (bridge message, task creation, domain event).
    It contains work items (Mode A) or claims (Mode B) and produces
    a final synthesis.
    """

    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: WorkflowMode = WorkflowMode.COOPERATIVE
    status: WorkflowStatus = WorkflowStatus.CREATED
    driver_agent_id: str | None = None
    request: str = ""
    request_class: str | None = None  # e.g. "question", "task", "debug"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_event_id: str | None = None
    source_channel: str | None = None
    correlation_id: str | None = None
    final_synthesis: str | None = None
    error: str | None = None

    @model_validator(mode="after")
    def _sync_timestamps(self) -> Workflow:
        """Ensure ``updated_at`` is never before ``created_at``."""
        if self.updated_at < self.created_at:
            self.updated_at = self.created_at
        return self


# ── Work Item ───────────────────────────────────────────────────────────────


class WorkItemStatus(StrEnum):
    """Lifecycle state of a single work item within a workflow."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkItem(BaseModel):
    """A discrete unit of work within a Mode A cooperative workflow.

    The driver agent decomposes the parent request into work items,
    assigns each to a worker agent, and collects receipts.
    """

    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    parent_item_id: str | None = None  # for nested decomposition
    agent_id: str | None = None
    description: str = ""
    status: WorkItemStatus = WorkItemStatus.PENDING
    priority: int = 5  # 1 (highest) to 10 (lowest)
    depends_on: list[str] = Field(default_factory=list)  # item_ids
    result: str | None = None
    error: str | None = None
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Swarm Note ──────────────────────────────────────────────────────────────


class SwarmNote(BaseModel):
    """An observation or annotation produced by any agent during execution.

    Swarm notes are the primary artifact for inter-agent communication.
    They carry the agent's analysis, evidence, and reasoning.
    """

    note_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    agent_id: str = ""
    role: str = ""  # e.g. "driver", "worker", "critic", "synthesizer"
    content: str = ""
    note_type: str = "observation"  # observation, evidence, reasoning, question
    target_item_id: str | None = None  # links to a specific work item
    target_claim_id: str | None = None  # links to a specific claim
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    embedding: list[float] | None = None  # pgvector for semantic search
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Claim ───────────────────────────────────────────────────────────────────


class Claim(BaseModel):
    """A Mode B artifact: an agent claims a portion of the task.

    In discussion mode, agents independently claim sub-problems,
    produce analyses, and later their work is critiqued and synthesized.
    """

    claim_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    agent_id: str = ""
    portion_description: str = ""
    analysis: str = ""
    evidence: list[str] = Field(default_factory=list)
    status: str = "claimed"  # claimed, attacked, repaired, accepted, rejected
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    repaired_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Receipt ─────────────────────────────────────────────────────────────────


class Receipt(BaseModel):
    """Proof that an agent completed (or failed) an assigned unit of work.

    Receipts are the completion signal in both modes.  In Mode A they
    accompany work item completion; in Mode B they accompany claim
    resolution.
    """

    receipt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    agent_id: str = ""
    target_type: str = ""  # "work_item" or "claim"
    target_id: str = ""  # item_id or claim_id
    outcome: str = "success"  # success, failure, partial, timeout
    result_summary: str = ""
    error_detail: str | None = None
    duration_ms: int | None = None
    model_used: str | None = None
    compute_backend: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Decision Packet ─────────────────────────────────────────────────────────


class DecisionPacket(BaseModel):
    """A structured decision produced by the driver or synthesizer.

    Decision packets capture the reasoning chain, alternatives considered,
    and the chosen path.  They provide an audit trail for how orchestration
    outcomes were reached.
    """

    packet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    agent_id: str = ""
    decision_type: str = ""  # route, escalate, synthesize, delegate, abort
    trigger: str = ""  # what prompted this decision
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    chosen: str = ""
    reasoning: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Interrupt ───────────────────────────────────────────────────────────────


class InterruptKind(StrEnum):
    """Types of interrupts that can halt or alter workflow execution."""

    USER_INPUT = "user_input"  # needs human decision
    APPROVAL = "approval"  # needs approval gate
    TIMEOUT = "timeout"  # a step exceeded its time budget
    ERROR = "error"  # unrecoverable error in a worker
    STORM_DETECTED = "storm_detected"  # anti-storm watchdog triggered
    NOVELTY_LOW = "novelty_low"  # watchdog: no new information produced
    VELOCITY_HIGH = "velocity_high"  # watchdog: too many messages too fast
    RECEIPT_ABSENT = "receipt_absent"  # watchdog: expected receipt never arrived
    EXTERNAL = "external"  # external event (e.g. new bridge message)


class Interrupt(BaseModel):
    """A signal that halts or alters the current workflow execution.

    Interrupts can come from watchdogs, approval gates, timeouts, or
    external events.  They carry the context needed to resume or abort.
    """

    interrupt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    kind: InterruptKind = InterruptKind.EXTERNAL
    message: str = ""
    source_agent_id: str | None = None
    target_agent_id: str | None = None
    target_item_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    resolution: str | None = None  # "resumed", "escalated", "aborted", None
    resolved_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
