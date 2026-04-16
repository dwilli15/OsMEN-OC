"""Orchestration watchdogs.

Four independent watchdogs monitor workflow health and emit
:class:`Interrupt` signals when anomalies are detected:

- **TokenBudgetWatchdog**: Tracks cumulative LLM token usage per
  workflow.  Fires when a workflow exceeds its token budget.
- **NoveltyWatchdog**: Detects when the workflow is producing redundant
  swarm notes (low novelty / high similarity).  Fires when the
  rolling novelty score drops below a threshold.
- **VelocityWatchdog**: Detects message storms — too many notes or
  receipts in a short window.  Fires when the rate exceeds a limit.
- **ReceiptWatchdog**: Monitors for missing receipts.  When a work
  item or claim transitions to ``in_progress`` but no receipt arrives
  within the timeout, fires an interrupt.

All watchdogs are stateless between calls — they accept the full
history and compute state from scratch.  This makes them testable and
predictable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from core.orchestration.models import (
    Interrupt,
    InterruptKind,
    Receipt,
    SwarmNote,
    WorkItem,
    WorkItemStatus,
)


# ── Token Budget Watchdog ───────────────────────────────────────────────────


class TokenBudgetWatchdog:
    """Monitors cumulative token usage against a per-workflow budget.

    Args:
        max_tokens_in: Maximum input tokens across all receipts.
        max_tokens_out: Maximum output tokens across all receipts.
        warn_pct: Emit a warning interrupt at this percentage of budget.
    """

    def __init__(
        self,
        *,
        max_tokens_in: int = 200_000,
        max_tokens_out: int = 100_000,
        warn_pct: float = 0.8,
    ) -> None:
        self.max_tokens_in = max_tokens_in
        self.max_tokens_out = max_tokens_out
        self.warn_pct = warn_pct

    def check(
        self,
        workflow_id: str,
        receipts: list[Receipt],
    ) -> Interrupt | None:
        """Check cumulative token usage against budget.

        Returns an Interrupt if the budget is exceeded or near limit.
        Returns None if usage is healthy.
        """
        total_in = sum(r.tokens_in or 0 for r in receipts)
        total_out = sum(r.tokens_out or 0 for r in receipts)

        in_pct = total_in / self.max_tokens_in if self.max_tokens_in else 0
        out_pct = total_out / self.max_tokens_out if self.max_tokens_out else 0
        max_pct = max(in_pct, out_pct)

        if max_pct >= 1.0:
            return Interrupt(
                workflow_id=workflow_id,
                kind=InterruptKind.VELOCITY_HIGH,
                message=(
                    f"Token budget exceeded: {total_in:,} in "
                    f"(limit {self.max_tokens_in:,}), {total_out:,} out "
                    f"(limit {self.max_tokens_out:,})"
                ),
                context={
                    "total_tokens_in": total_in,
                    "total_tokens_out": total_out,
                    "max_tokens_in": self.max_tokens_in,
                    "max_tokens_out": self.max_tokens_out,
                    "usage_pct": round(max_pct, 3),
                },
            )

        if max_pct >= self.warn_pct:
            logger.warning(
                "watchdog: workflow {} token usage at {:.1f}% "
                "({:,} in, {:,} out)",
                workflow_id,
                max_pct * 100,
                total_in,
                total_out,
            )
            return Interrupt(
                workflow_id=workflow_id,
                kind=InterruptKind.VELOCITY_HIGH,
                message=(
                    f"Token budget at {max_pct:.0%}: {total_in:,} in, "
                    f"{total_out:,} out"
                ),
                context={
                    "total_tokens_in": total_in,
                    "total_tokens_out": total_out,
                    "usage_pct": round(max_pct, 3),
                    "is_warning": True,
                },
            )

        return None


# ── Novelty Watchdog ────────────────────────────────────────────────────────


class NoveltyWatchdog:
    """Detects low-novelty (redundant) swarm notes.

    Computes a rolling novelty score based on the ratio of unique
    content hashes to total notes in a sliding window.  When the ratio
    drops below the threshold, it signals that agents are producing
    redundant output.

    Args:
        window_size: Number of recent notes to consider.
        min_novelty_ratio: Minimum unique/total ratio before triggering.
        min_notes_before_check: Don't check until at least this many
            notes have been produced (avoids false positives early).
    """

    def __init__(
        self,
        *,
        window_size: int = 20,
        min_novelty_ratio: float = 0.3,
        min_notes_before_check: int = 5,
    ) -> None:
        self.window_size = window_size
        self.min_novelty_ratio = min_novelty_ratio
        self.min_notes_before_check = min_notes_before_check

    def check(
        self,
        workflow_id: str,
        notes: list[SwarmNote],
    ) -> Interrupt | None:
        """Check the novelty of recent swarm notes.

        Returns an Interrupt if novelty is too low.
        """
        if len(notes) < self.min_notes_before_check:
            return None

        # Use a sliding window of the most recent notes
        recent = notes[-self.window_size:]
        content_hashes = self._hash_contents(recent)

        unique_count = len(set(content_hashes))
        novelty_ratio = unique_count / len(content_hashes) if content_hashes else 1.0

        if novelty_ratio < self.min_novelty_ratio:
            return Interrupt(
                workflow_id=workflow_id,
                kind=InterruptKind.NOVELTY_LOW,
                message=(
                    f"Low novelty detected: {unique_count}/{len(recent)} "
                    f"unique notes in window ({novelty_ratio:.0%} < "
                    f"{self.min_novelty_ratio:.0%})"
                ),
                context={
                    "unique_notes": unique_count,
                    "total_notes_in_window": len(recent),
                    "novelty_ratio": round(novelty_ratio, 3),
                    "threshold": self.min_novelty_ratio,
                },
            )

        return None

    @staticmethod
    def _hash_contents(notes: list[SwarmNote]) -> list[str]:
        """Hash note contents for dedup comparison.

        Uses a simple normalised-hash approach: strip whitespace, lowercase,
        then take first 32 chars of SHA-256.  This catches exact and
        near-duplicate content without requiring embeddings.
        """
        import hashlib

        hashes = []
        for note in notes:
            normalised = " ".join(note.content.lower().split())
            h = hashlib.sha256(normalised.encode()).hexdigest()[:32]
            hashes.append(h)
        return hashes


# ── Velocity Watchdog ───────────────────────────────────────────────────────


class VelocityWatchdog:
    """Detects message storms within a workflow.

    Monitors the rate of swarm notes and receipts.  If the rate
    exceeds the configured limits within a sliding time window,
    it emits a storm-detected interrupt.

    Args:
        max_notes_per_minute: Maximum swarm notes per minute.
        max_receipts_per_minute: Maximum receipts per minute.
        window_seconds: Sliding window for rate calculation.
    """

    def __init__(
        self,
        *,
        max_notes_per_minute: float = 30.0,
        max_receipts_per_minute: float = 10.0,
        window_seconds: int = 60,
    ) -> None:
        self.max_notes_per_minute = max_notes_per_minute
        self.max_receipts_per_minute = max_receipts_per_minute
        self.window_seconds = window_seconds

    def check(
        self,
        workflow_id: str,
        notes: list[SwarmNote],
        receipts: list[Receipt],
        now: datetime | None = None,
    ) -> Interrupt | None:
        """Check message velocity against limits.

        Returns an Interrupt if velocity exceeds limits.
        """
        now = now or datetime.now(timezone.utc)
        cutoff = now.timestamp() - self.window_seconds

        recent_notes = [n for n in notes if n.created_at.timestamp() > cutoff]
        recent_receipts = [r for r in receipts if r.created_at.timestamp() > cutoff]

        notes_rate = len(recent_notes) / (self.window_seconds / 60)
        receipts_rate = len(recent_receipts) / (self.window_seconds / 60)

        max_rate = max(notes_rate, receipts_rate)
        note_limit = self.max_notes_per_minute
        receipt_limit = self.max_receipts_per_minute

        if notes_rate > note_limit:
            return Interrupt(
                workflow_id=workflow_id,
                kind=InterruptKind.STORM_DETECTED,
                message=(
                    f"Message storm: {notes_rate:.1f} notes/min "
                    f"(limit {note_limit}/min)"
                ),
                context={
                    "notes_in_window": len(recent_notes),
                    "receipts_in_window": len(recent_receipts),
                    "notes_per_minute": round(notes_rate, 1),
                    "receipts_per_minute": round(receipts_rate, 1),
                    "note_limit": note_limit,
                    "receipt_limit": receipt_limit,
                },
            )

        if receipts_rate > receipt_limit:
            return Interrupt(
                workflow_id=workflow_id,
                kind=InterruptKind.STORM_DETECTED,
                message=(
                    f"Message storm: {receipts_rate:.1f} receipts/min "
                    f"(limit {receipt_limit}/min)"
                ),
                context={
                    "notes_in_window": len(recent_notes),
                    "receipts_in_window": len(recent_receipts),
                    "notes_per_minute": round(notes_rate, 1),
                    "receipts_per_minute": round(receipts_rate, 1),
                    "note_limit": note_limit,
                    "receipt_limit": receipt_limit,
                },
            )

        return None


# ── Receipt Watchdog ────────────────────────────────────────────────────────


class ReceiptWatchdog:
    """Monitors for missing receipts from in-progress work items/claims.

    When a work item transitions to ``in_progress`` or a claim enters
    ``claimed`` status, the watchdog expects a receipt within a timeout
    period.  If none arrives, it emits a ``RECEIPT_ABSENT`` interrupt.

    Args:
        timeout_seconds: How long to wait for a receipt before triggering.
    """

    def __init__(self, *, timeout_seconds: int = 120) -> None:
        self.timeout_seconds = timeout_seconds

    def check_work_items(
        self,
        workflow_id: str,
        work_items: list[WorkItem],
        receipts: list[Receipt],
        now: datetime | None = None,
    ) -> list[Interrupt]:
        """Check for missing receipts on in-progress work items.

        Returns a list of interrupts (one per missing receipt).
        """
        now = now or datetime.now(timezone.utc)
        cutoff = now.timestamp() - self.timeout_seconds

        # Index receipts by target_id
        receipt_targets = {r.target_id for r in receipts if r.target_type == "work_item"}

        interrupts: list[Interrupt] = []
        for item in work_items:
            if item.status != WorkItemStatus.IN_PROGRESS:
                continue
            if item.item_id in receipt_targets:
                continue  # receipt exists

            # Check if the work item has been in_progress long enough
            start = item.started_at or item.assigned_at or item.created_at
            if start.timestamp() < cutoff:
                interrupts.append(
                    Interrupt(
                        workflow_id=workflow_id,
                        kind=InterruptKind.RECEIPT_ABSENT,
                        message=(
                            f"No receipt for work item {item.item_id} "
                            f"after {self.timeout_seconds}s "
                            f"(agent: {item.agent_id or 'unassigned'})"
                        ),
                        target_item_id=item.item_id,
                        target_agent_id=item.agent_id,
                        context={
                            "item_id": item.item_id,
                            "agent_id": item.agent_id,
                            "description": item.description,
                            "timeout_seconds": self.timeout_seconds,
                            "started_at": start.isoformat(),
                        },
                    )
                )

        return interrupts

    def check_claims(
        self,
        workflow_id: str,
        claim_ids_with_receipts: set[str],
        claims_in_progress: list[Any],
        now: datetime | None = None,
    ) -> list[Interrupt]:
        """Check for missing receipts on claimed claims.

        Args:
            claim_ids_with_receipts: Set of claim IDs that have receipts.
            claims_in_progress: Claims in 'claimed' status.
        """
        now = now or datetime.now(timezone.utc)
        cutoff = now.timestamp() - self.timeout_seconds

        interrupts: list[Interrupt] = []
        for claim in claims_in_progress:
            if claim.claim_id in claim_ids_with_receipts:
                continue
            if claim.created_at.timestamp() < cutoff:
                interrupts.append(
                    Interrupt(
                        workflow_id=workflow_id,
                        kind=InterruptKind.RECEIPT_ABSENT,
                        message=(
                            f"No receipt for claim {claim.claim_id} "
                            f"after {self.timeout_seconds}s "
                            f"(agent: {claim.agent_id})"
                        ),
                        target_agent_id=claim.agent_id,
                        context={
                            "claim_id": claim.claim_id,
                            "agent_id": claim.agent_id,
                            "timeout_seconds": self.timeout_seconds,
                        },
                    )
                )

        return interrupts
