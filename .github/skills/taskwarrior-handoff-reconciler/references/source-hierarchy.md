# Source Hierarchy And Evidence Checklist

Use this reference when reconciling OsMEN-OC handoffs into Taskwarrior.

## Source Surfaces

Read these in roughly this order:

1. `docs/session-logs/RESUME.md`
2. newest files in `docs/session-logs/YYYY-MM-DD/*handoff.md`
3. live Taskwarrior export
4. repo implementation surfaces:
   - `core/`
   - `gateway/`
   - `agents/`
   - `config/`
   - `scripts/`
   - `tests/`
   - `quadlets/`
5. memory surfaces:
   - `.opencode/memory-bank/*.md`
   - `openclaw/memory/*.md`
   - `openclaw/state/*.md`

## OsMEN-OC Reconciliation Heuristics

- Architecture claims must match the current pipeline, not just the intent.
- "Wired" means ingress, routing, processing, and egress are connected.
- A generated markdown artifact is not proof of durable memory if the real write path should land in PostgreSQL or another service first.
- Agent discussion surfaces are not the authoritative workflow unless the orchestration layer records typed state.
- Public chat transport is not a source of truth. Internal envelopes, ledgers, and routing rules are.

## Evidence Strong Enough To Close A Task

Prefer more than one of these when possible:

- implementation file exists in the expected module
- configuration references the implementation
- tests cover the behavior or smoke command passes
- another module imports or calls the new path
- a service, hook, or adapter now points at the new wiring

## Evidence That Requires Caution

Do not mark a task done based only on:

- a handoff sentence
- a TODO comment
- a placeholder file
- a partially written interface
- a config key that is never consumed

## Recommended Task Categories

When the list needs stronger structure, prefer categories like:

- architecture
- inference
- communication
- memory
- ingress
- verification
- rollout

Then order within each category by dependency and timeline.
