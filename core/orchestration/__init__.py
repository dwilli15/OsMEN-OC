"""Orchestration engine for multi-agent workflows.

The orchestration subsystem coordinates agent collaboration through two
modes:

- **Mode A — Cooperative Workflow**: A driver agent decomposes a request
  into work items, assigns them to workers, and synthesizes results.
  Suitable for well-scoped tasks with clear sub-task boundaries.

- **Mode B — Claim/Attack/Repair/Synthesize Loop**: Multiple agents
  independently claim portions of a task, produce parallel analyses,
  critique each other's work, and synthesize a final output.  Suitable
  for open-ended tasks benefiting from diverse perspectives.

Both modes produce :class:`SwarmNote`, :class:`Claim`, :class:`Receipt`,
:class:`DecisionPacket`, and :class:`Interrupt` artifacts stored in the
orchestration ledger.

Architecture::

    Ingress (bridge / task / event)
        │
        ▼
    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
    │  registry    │───▶│   session    │───▶│   router    │
    │  (identities)│    │ (classify)   │    │ (compute)   │
    └─────────────┘    └──────────────┘    └─────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   ledger     │
                    │ (workflows,  │
                    │  items,      │
                    │  claims,     │
                    │  receipts)   │
                    └──────────────┘
                        │         │
              ┌─────────┘         └─────────┐
              ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │  Mode A:        │          │  Mode B:        │
    │  workflow.py    │          │  discussion.py  │
    │  (cooperative)  │          │  (claim/attack)  │
    └─────────────────┘          └─────────────────┘
              │                             │
              └──────────┬──────────────────┘
                         ▼
              ┌──────────────────┐
              │  watchdogs.py    │
              │  (anti-storm)    │
              └──────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  memory bridge   │
              │  + markdown view │
              └──────────────────┘
"""

from core.orchestration.models import (
    Claim,
    DecisionPacket,
    Interrupt,
    InterruptKind,
    Receipt,
    SwarmNote,
    WorkItem,
    WorkItemStatus,
    Workflow,
    WorkflowMode,
    WorkflowStatus,
)

__all__ = [
    "Claim",
    "DecisionPacket",
    "Interrupt",
    "InterruptKind",
    "Receipt",
    "SwarmNote",
    "WorkItem",
    "WorkItemStatus",
    "Workflow",
    "WorkflowMode",
    "WorkflowStatus",
]
