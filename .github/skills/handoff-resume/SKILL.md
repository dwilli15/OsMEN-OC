---
name: handoff-resume
description: Use this skill when the user wants to resume from a prior handoff, continue earlier work, or restore enough context from session logs to proceed safely. It locates the latest handoff, verifies current state, and identifies the next action.
---

# Session Handoff Resume

Resume from the latest trustworthy handoff without blindly trusting stale notes.

## Use It When

Use this skill when the user asks to:
- resume from handoff
- continue from the last session
- restore context
- pick up where work stopped
- `/handoff-resume`

## Lookup Order

Look first for:

```text
{workspace}/docs/session-logs/RESUME.md
```

If that exists, use it to find the current handoff.

If multiple pointer files exist, prefer the one whose `Resume Lane` or `Resume ID`
matches the user's stated lane. Otherwise use the root `RESUME.md` as the primary lane.

If not, locate the newest file matching:

```text
{workspace}/docs/session-logs/YYYY-MM-DD/YYYY-MM-DD_HHMMSS_handoff.md
```

## Process

1. Read `RESUME.md`, or the lane-specific `RESUME.<lane>.md` when applicable.
2. Extract the previous summary, completed work, pending work, blockers, and quick checks.
3. Re-run safe verification commands or equivalent state checks.
4. Compare the current repo state with the saved handoff.
5. Report drift before acting if the repo moved on.
6. Continue from the first clear pending task.

## Pointer Identity

Read and report these fields when present:

- `Resume ID`
- `Resume Lane`
- `Pointer Role`

These fields exist to prevent parallel agents from accidentally resuming the wrong lane.

## Resume Output

Provide a concise status report with:

- the handoff being resumed
- what was completed
- what is still pending
- any drift or broken assumptions
- the next recommended action

## Guardrails

- Treat handoffs as guidance, not proof.
- Verify important claims before editing code or tasks.
- If multiple handoffs conflict, prefer the newest one that still matches the repo.
- If multiple resume pointers exist, do not merge lanes implicitly. Name which lane you resumed.
- If nothing trustworthy exists, say so and rebuild context explicitly.
