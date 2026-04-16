"""Markdown view renderer for orchestration workflows.

Provides human-readable Markdown representations of workflow state,
progress, and results.  Used for:
- CLI output (``task info``, ``orchestration status``)
- Bridge responses back to OpenClaw
- Audit trail exports

Each renderer method returns a Markdown string suitable for direct
display or further formatting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.orchestration.models import (
    Claim,
    DecisionPacket,
    Interrupt,
    Receipt,
    SwarmNote,
    WorkItem,
    WorkItemStatus,
    Workflow,
    WorkflowMode,
    WorkflowStatus,
)


class WorkflowView:
    """Renders orchestration artifacts as Markdown.

    All public methods return Markdown strings.
    """

    # ── Workflow Summary ────────────────────────────────────────────────────

    @staticmethod
    def workflow_summary(wf: Workflow) -> str:
        """Render a workflow summary card."""
        status_emoji = _STATUS_EMOJI.get(wf.status, "❓")
        mode_label = "Cooperative" if wf.mode == WorkflowMode.COOPERATIVE else "Discussion"

        lines = [
            f"## Workflow `{wf.workflow_id[:8]}` {status_emoji}",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Status | {wf.status.value} |",
            f"| Mode | {mode_label} |",
            f"| Driver | {wf.driver_agent_id or 'unassigned'} |",
            f"| Class | {wf.request_class or 'unknown'} |",
            f"| Created | {_fmt_dt(wf.created_at)} |",
            f"| Updated | {_fmt_dt(wf.updated_at)} |",
        ]

        if wf.completed_at:
            lines.append(f"| Completed | {_fmt_dt(wf.completed_at)} |")
        if wf.error:
            lines.append(f"| Error | {wf.error} |")

        if wf.correlation_id:
            lines.append(f"| Correlation | `{wf.correlation_id[:12]}` |")
        if wf.source_channel:
            lines.append(f"| Source | {wf.source_channel} |")

        lines.append("")
        lines.append(f"**Request:** {wf.request}")

        if wf.final_synthesis:
            lines.append("")
            lines.append("### Synthesis")
            lines.append("")
            lines.append(wf.final_synthesis)

        return "\n".join(lines)

    # ── Work Items ──────────────────────────────────────────────────────────

    @staticmethod
    def work_items_table(items: list[WorkItem]) -> str:
        """Render work items as a Markdown table."""
        if not items:
            return "_No work items._"

        lines = [
            "| ID | Status | Agent | Priority | Description |",
            "|----|--------|-------|----------|-------------|",
        ]

        for item in items:
            emoji = _ITEM_STATUS_EMOJI.get(item.status, "")
            agent = item.agent_id or "—"
            desc = _truncate(item.description, 50)
            lines.append(
                f"| `{item.item_id[:8]}` | {emoji} {item.status.value} "
                f"| {agent} | {item.priority} | {desc} |"
            )

        # Summary
        status_counts: dict[str, int] = {}
        for item in items:
            status_counts[item.status.value] = status_counts.get(item.status.value, 0) + 1

        lines.append("")
        parts = [f"{v} {k}" for k, v in sorted(status_counts.items())]
        lines.append(f"**Totals:** {', '.join(parts)}")

        return "\n".join(lines)

    @staticmethod
    def work_item_detail(item: WorkItem) -> str:
        """Render detailed view of a single work item."""
        lines = [
            f"### Work Item `{item.item_id}`",
            "",
            f"- **Status:** {item.status.value}",
            f"- **Agent:** {item.agent_id or 'unassigned'}",
            f"- **Priority:** {item.priority}",
        ]

        if item.description:
            lines.append(f"- **Description:** {item.description}")
        if item.depends_on:
            deps = ", ".join(f"`{d[:8]}`" for d in item.depends_on)
            lines.append(f"- **Depends on:** {deps}")
        if item.parent_item_id:
            lines.append(f"- **Parent:** `{item.parent_item_id[:8]}`")
        if item.result:
            lines.append("")
            lines.append("**Result:**")
            lines.append("")
            lines.append(item.result)
        if item.error:
            lines.append("")
            lines.append(f"**Error:** {item.error}")

        timestamps = []
        if item.assigned_at:
            timestamps.append(f"Assigned: {_fmt_dt(item.assigned_at)}")
        if item.started_at:
            timestamps.append(f"Started: {_fmt_dt(item.started_at)}")
        if item.completed_at:
            timestamps.append(f"Completed: {_fmt_dt(item.completed_at)}")
        if timestamps:
            lines.append("")
            lines.append(f"**Timeline:** {' | '.join(timestamps)}")

        return "\n".join(lines)

    # ── Swarm Notes ─────────────────────────────────────────────────────────

    @staticmethod
    def swarm_notes_timeline(notes: list[SwarmNote]) -> str:
        """Render swarm notes as a chronological timeline."""
        if not notes:
            return "_No swarm notes._"

        lines = ["### Swarm Notes Timeline", ""]

        for note in notes:
            time_str = _fmt_dt(note.created_at, time_only=True)
            lines.append(f"**{time_str}** — `{note.agent_id}` ({note.role})")
            if note.target_item_id:
                lines.append(f"  → item `{note.target_item_id[:8]}`")
            lines.append(f"  {note.content}")
            if note.confidence < 1.0:
                lines.append(f"  _confidence: {note.confidence:.0%}_")
            lines.append("")

        return "\n".join(lines)

    # ── Claims ──────────────────────────────────────────────────────────────

    @staticmethod
    def claims_table(claims: list[Claim]) -> str:
        """Render claims as a Markdown table."""
        if not claims:
            return "_No claims._"

        lines = [
            "| Claim | Agent | Status | Confidence | Portion |",
            "|-------|-------|--------|------------|---------|",
        ]

        for claim in claims:
            status_emoji = _CLAIM_STATUS_EMOJI.get(claim.status, "")
            portion = _truncate(claim.portion_description, 40)
            lines.append(
                f"| `{claim.claim_id[:8]}` | {claim.agent_id} | "
                f"{status_emoji} {claim.status} | {claim.confidence:.0%} | "
                f"{portion} |"
            )

        return "\n".join(lines)

    # ── Receipts ────────────────────────────────────────────────────────────

    @staticmethod
    def receipts_summary(receipts: list[Receipt]) -> str:
        """Render receipts as a compact summary."""
        if not receipts:
            return "_No receipts._"

        lines = ["### Receipts", ""]
        total_in = sum(r.tokens_in or 0 for r in receipts)
        total_out = sum(r.tokens_out or 0 for r in receipts)

        for receipt in receipts:
            outcome_emoji = _RECEIPT_OUTCOME_EMOJI.get(receipt.outcome, "")
            model = receipt.model_used or "unknown"
            duration = f"{receipt.duration_ms}ms" if receipt.duration_ms else "—"
            summary = _truncate(receipt.result_summary, 60) or "—"
            lines.append(
                f"- {outcome_emoji} `{receipt.target_id[:8]}` by `{receipt.agent_id}` "
                f"({model}, {duration}): {summary}"
            )

        if total_in or total_out:
            lines.append("")
            lines.append(f"**Total tokens:** {total_in:,} in / {total_out:,} out")

        return "\n".join(lines)

    # ── Decisions ───────────────────────────────────────────────────────────

    @staticmethod
    def decisions_timeline(decisions: list[DecisionPacket]) -> str:
        """Render decision packets as a timeline."""
        if not decisions:
            return "_No decisions._"

        lines = ["### Decision Trail", ""]

        for d in decisions:
            lines.append(f"**{d.decision_type}** — `{d.agent_id}`")
            lines.append(f"- Trigger: {d.trigger}")
            lines.append(f"- Chosen: **{d.chosen}**")
            if d.reasoning:
                lines.append(f"- Reasoning: {d.reasoning}")
            if d.alternatives:
                alts = ", ".join(
                    str(a.get("option", a)) if isinstance(a, dict) else str(a)
                    for a in d.alternatives
                )
                lines.append(f"- Alternatives: {alts}")
            lines.append(f"- Confidence: {d.confidence:.0%}")
            lines.append("")

        return "\n".join(lines)

    # ── Interrupts ──────────────────────────────────────────────────────────

    @staticmethod
    def interrupts_table(interrupts: list[Interrupt]) -> str:
        """Render interrupts as a table."""
        if not interrupts:
            return "_No interrupts._"

        lines = [
            "| Kind | Message | Resolution |",
            "|------|---------|------------|",
        ]

        for intr in interrupts:
            res = intr.resolution or "pending"
            msg = _truncate(intr.message, 60)
            lines.append(f"| {intr.kind.value} | {msg} | {res} |")

        return "\n".join(lines)

    # ── Full Workflow View ──────────────────────────────────────────────────

    @staticmethod
    def full_workflow_view(
        wf: Workflow,
        items: list[WorkItem] | None = None,
        notes: list[SwarmNote] | None = None,
        claims: list[Claim] | None = None,
        receipts: list[Receipt] | None = None,
        decisions: list[DecisionPacket] | None = None,
        interrupts: list[Interrupt] | None = None,
    ) -> str:
        """Render a complete workflow view with all artifacts."""
        parts = [WorkflowView.workflow_summary(wf)]

        if items:
            parts.append("")
            parts.append("## Work Items")
            parts.append("")
            parts.append(WorkflowView.work_items_table(items))

        if claims:
            parts.append("")
            parts.append("## Claims")
            parts.append("")
            parts.append(WorkflowView.claims_table(claims))

        if notes:
            parts.append("")
            parts.append(WorkflowView.swarm_notes_timeline(notes))

        if receipts:
            parts.append("")
            parts.append(WorkflowView.receipts_summary(receipts))

        if decisions:
            parts.append("")
            parts.append(WorkflowView.decisions_timeline(decisions))

        if interrupts:
            parts.append("")
            parts.append("## Interrupts")
            parts.append("")
            parts.append(WorkflowView.interrupts_table(interrupts))

        return "\n".join(parts)


# ── Helpers ─────────────────────────────────────────────────────────────────

_STATUS_EMOJI = {
    WorkflowStatus.CREATED: "🆕",
    WorkflowStatus.RUNNING: "🔄",
    WorkflowStatus.SUSPENDED: "⏸️",
    WorkflowStatus.COMPLETED: "✅",
    WorkflowStatus.FAILED: "❌",
    WorkflowStatus.CANCELLED: "🚫",
}

_ITEM_STATUS_EMOJI = {
    WorkItemStatus.PENDING: "⬜",
    WorkItemStatus.ASSIGNED: "📋",
    WorkItemStatus.IN_PROGRESS: "🔄",
    WorkItemStatus.BLOCKED: "🚧",
    WorkItemStatus.COMPLETED: "✅",
    WorkItemStatus.FAILED: "❌",
    WorkItemStatus.SKIPPED: "⏭️",
}

_CLAIM_STATUS_EMOJI = {
    "claimed": "📌",
    "attacked": "⚔️",
    "repaired": "🔧",
    "accepted": "✅",
    "rejected": "❌",
}

_RECEIPT_OUTCOME_EMOJI = {
    "success": "✅",
    "failure": "❌",
    "partial": "⚠️",
    "timeout": "⏰",
}


def _fmt_dt(dt: datetime, *, time_only: bool = False) -> str:
    """Format a datetime for display."""
    if time_only:
        return dt.strftime("%H:%M:%S")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
