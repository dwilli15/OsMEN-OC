---
name: handoff-continue
description: Use this skill when the user wants to create a handoff, save session progress, document current state, or pause work for a later continuation. It captures files, decisions, commands, blockers, and next steps in a structured handoff.
---

# Session Handoff Continue

Capture enough detail that another agent can resume work without guessing.

## Use It When

Use this skill when the user asks to:
- create a handoff
- save this session
- document progress
- continue later
- prepare a clean resume point
- `/handoff-continue`

## Default Output

Prefer workspace-local handoffs:

```text
{workspace}/docs/session-logs/YYYY-MM-DD/YYYY-MM-DD_HHMMSS_handoff.md
```

Update the stable pointer here:

```text
{workspace}/docs/session-logs/RESUME.md
```

When parallel workstreams exist, also support lane-specific pointers such as:

```text
{workspace}/docs/session-logs/RESUME.<lane>.md
```

## What To Capture

- the original goal
- major decisions and why they were made
- files created or modified
- commands run and their outcomes
- tests or verification status
- blockers, drifts, and unresolved questions
- the exact next steps
- a stable resume identifier for the lane

## Process

1. Reconstruct the session arc from the user request to the current state.
2. Inventory the meaningful artifacts and commands.
3. Record decisions, not just edits.
4. Separate completed work from pending work.
5. Add quick resume commands that re-check the live state.
6. Write or preserve a stable `Resume ID` and `Resume Lane`.
7. Update `RESUME.md` so the next agent has one obvious entry point for the primary lane.

## Resume Pointer Fields

Every pointer file should include at least:

- `Resume ID`: stable identifier for this execution thread
- `Resume Lane`: human-readable lane or scope name
- `Pointer Role`: `primary_execution`, `secondary_lane`, `architecture_direction`, or similar
- `Last handoff`
- `Report`

If parallel agents are active, prefer creating or updating `RESUME.<lane>.md` rather
than stealing the root `RESUME.md`.

## Handoff Quality Bar

A good handoff lets the next agent answer:

- What changed?
- What is verified?
- What is still open?
- Where should work resume first?

## Guardrails

- Never include secrets or raw tokens.
- Prefer exact file paths and concrete commands.
- Do not claim a task is complete unless the session actually verified it.
- Keep the summary concise, but make the pending work unambiguous.
- Do not overwrite another lane's pointer without an explicit user decision.
