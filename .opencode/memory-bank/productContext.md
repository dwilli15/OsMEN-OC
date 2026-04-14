# Product Context

OsMEN-OC is a multi-agent AI orchestration platform designed to run
specialized AI departments on local hardware with cloud fallback for
judgment-critical tasks.

## What Problem It Solves

Single-model AI cannot self-correct. The organizational pattern where one
entity plans, executes, reviews, and approves guarantees sycophancy and
confident mediocrity. OsMEN-OC solves this by deploying structured teams of
specialized agents with defined accountability, adversarial review loops, and
human oversight at critical transitions.

## How It Should Work

Agents operate in two modes:

- **Mode A (cooperative)**: Structured team execution for research, strategy,
  implementation. Roles: steward, planner, researcher, worker, critic,
  verifier. Deterministic decomposition and artifact progression.
- **Mode B (adversarial)**: Structured debate for critique, stress testing,
  brainstorming. Roles: proposer, naysayer, lateral_innovation, stable_focus,
  iteration_steward, verifier. Hard turn limits, forced move types, max 3
  cycles before human escalation.

The swarm-elite hierarchy uses small NPU models (0.6B-4B) for 90% of calls
(watchdogs, critics, curators, classifiers) and reserves cloud frontier models
for the remaining 10% (strategic synthesis, arbitration, final answers).

## Key User Experience Goals

- Discord is the visible multiplayer surface — agents have distinct bot
  identities, presence, and channel-scoped permissions.
- Discord is NOT the authoritative state store — PostgreSQL and markdown files
  are. Discord is a view and input channel only.
- Humans witness or approve critical transitions. If human is unavailable,
  workflows downgrade to advisory-only — no authoritative answers, no external
  side effects.
- Agent public speech is a scarce resource, not default behavior. Anti-storm
  controls (driver token, novelty gate, velocity gate, mention gate, silent
  default) are mandatory and mechanical, not prompt-based.
