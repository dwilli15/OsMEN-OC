---
name: superpowers
description: Use this skill when the user explicitly asks for /superpowers or wants stronger engineering discipline around planning, debugging, verification, and completion. It applies the core superpowers operating style even when the full external bundle is not available as a native plugin.
---

# Superpowers

Use a disciplined operating mode instead of improvising.

## What This Skill Does

This is a portable entrypoint for the superpowers style:

- choose the right mode before acting
- plan when the work is ambiguous
- debug systematically when behavior is broken
- verify before claiming completion
- parallelize only independent work
- finish with proof, not vibes

## When To Use It

Use this skill when the user asks for:

- `/superpowers`
- stronger engineering process
- a written plan before implementation
- systematic debugging
- tighter completion discipline
- more deliberate multi-agent execution

## Operating Modes

### Plan

Use when the work is broad or ambiguous.

- define the target outcome
- identify unknowns and risks
- sequence the work into finishable steps
- avoid implementing against a fuzzy goal

### Debug

Use when something is broken or confusing.

- reproduce first
- isolate the failing path
- test one hypothesis at a time
- fix root cause, not symptoms
- verify the fix under the original failure condition

### Build

Use when the goal is already clear.

- make the smallest change that completes the requirement
- preserve nearby patterns
- keep the critical path moving

### Verify

Use before declaring success.

- run the relevant test or smoke command
- inspect the actual wiring path
- confirm user-visible behavior or integration points

### Finish

Close with evidence:

- what changed
- what proved it works
- what remains open

## If The Full Superpowers Bundle Is Present

Prefer the deeper specialized skills when available, especially:

- `writing-plans`
- `systematic-debugging`
- `verification-before-completion`
- `dispatching-parallel-agents`
- `subagent-driven-development`

This wrapper exists so `/superpowers` still gives a useful operating mode everywhere.
