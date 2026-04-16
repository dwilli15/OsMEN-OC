---
name: taskwarrior-handoff-reconciler
description: Use this skill when the user wants to merge multiple handoffs, memory notes, repo evidence, and existing tasks into a single Taskwarrior-first execution ledger. It verifies completed work before closing tasks, rewrites unfinished work into actionable Taskwarrior entries, and treats memory as gist while Taskwarrior remains the source of truth.
---

# Taskwarrior Handoff Reconciler

Taskwarrior is the execution ledger. Handoffs, memory files, chat summaries, and scratch notes are inputs, not the final truth.

Use this skill when you need to:
- merge several handoffs into one execution picture
- convert repo context into Taskwarrior tasks
- reconcile "claimed complete" work against actual code, tests, configs, and scripts
- rewrite vague roadmap items into concrete, finishable tasks
- re-anchor a drifting project so future agents can trust Taskwarrior first

## Operating Rules

- Treat Taskwarrior as the canonical task ledger.
- Treat handoffs and memory as claims that must be reconciled.
- Mark work complete only after mechanical evidence exists.
- Keep memory high level. Do not duplicate the entire task system into memory.
- Rewrite vague tasks into deliverable tasks with explicit finish conditions.
- Prefer a few well-structured tasks over many overlapping tasks.

## Source Priority

When sources disagree, prefer them in this order:

1. User instructions in the current session
2. Mechanical repo evidence: code paths, configs, tests, scripts, services
3. Live Taskwarrior state
4. Current `docs/session-logs/RESUME.md` and newest handoffs
5. Memory surfaces such as `.opencode/memory-bank/` and `openclaw/memory/`
6. Older handoffs and speculative notes

If a handoff says something is done but the repo does not support that claim, keep the Taskwarrior entry open and annotate the mismatch.

## Workflow

### Phase 1: Gather Sources

Start with a structured inventory before editing tasks.

- Read `docs/session-logs/RESUME.md` if present.
- Read the newest handoffs first, then older ones only as needed.
- Inspect live memory surfaces only for gist, drift, and missing context.
- Export current Taskwarrior state before rewriting it.
- Check the code, configs, tests, and scripts that are supposed to prove completion.

Use the bundled audit helper when helpful:

```bash
python3 .github/skills/taskwarrior-handoff-reconciler/scripts/context_audit.py --workspace "$PWD" --format markdown
```

For repo-specific source patterns and evidence rules, read:

```text
references/source-hierarchy.md
```

### Phase 2: Build a Reconciliation Ledger

Convert every claim you find into one of these buckets:

- `verified_complete`: repo evidence supports completion
- `in_progress`: partially built, but not finished
- `not_started`: described, but no evidence exists
- `obsolete`: no longer aligned with the current architecture or user direction
- `uncertain`: conflicting evidence or missing proof

This phase is about classification, not yet editing the whole task list.

### Phase 3: Verify Completion Mechanically

Before marking a Taskwarrior item done, confirm at least one of:

- the required file or config exists in the correct path
- the wiring path is present end to end, not just a stub file
- tests pass for the relevant surface
- a smoke command succeeds
- the runtime config clearly references the new behavior

Good evidence is specific. Example:

- `core/tasks/sync.py` exists and tests pass
- hook script exists in `scripts/taskwarrior/`
- config points to the adapter that the handoff claimed was wired

Weak evidence is not enough:

- a plan says it was done
- a handoff says "implemented"
- a file exists but is not referenced anywhere

If completion is real, close the task and annotate what proved it.

### Phase 4: Rewrite Unfinished Work Into Taskwarrior

Rewrite vague or oversized tasks so each entry has:

- one clear outcome
- the correct project/category
- an actionable scope
- a meaningful priority
- a timeline signal when appropriate (`due`, `wait`, or sequence position)
- an explicit finish condition

Prefer tasks that describe shipping work, not vague aspirations.

Examples of strong task framing:

- `Wire Discord mention-only ingress through gateway and novelty gates`
- `Persist handoff reports into MemoryHub ledger and generate markdown views`
- `Verify Taskwarrior hook -> Redis queue -> orchestration ingress path`

Examples of weak task framing:

- `Do Discord`
- `Finish memory`
- `Improve architecture`

### Phase 5: Organize the Ledger

Make the resulting Taskwarrior list easy for future agents to trust:

- group by project and concern
- order by timeline and dependency
- reserve highest priority for blocking or foundational work
- split architecture, implementation, verification, and rollout when they are materially different kinds of work
- preserve history with annotations instead of deleting context

If a task is really a checklist, split it into separate child tasks or distinct entries.

### Phase 6: Push Only the Gist Back to Memory

After Taskwarrior is corrected:

- update handoffs or resume notes to say that Taskwarrior is now the source of truth
- summarize major completed areas, active fronts, and blockers
- do not recreate the full ledger in markdown memory files

Memory should answer "what is going on?" Taskwarrior should answer "what must happen next?"

## Finish Criteria

This skill is complete when:

- all major handoff claims have been classified
- completed claims are either verified and closed or left open with a reason
- unfinished work is represented in Taskwarrior as actionable entries
- the ledger reflects current architecture, not stale direction
- handoff and memory surfaces clearly point back to Taskwarrior

## Practical Notes

- Prefer annotations over silent rewrites when correcting a bad task assumption.
- When a change in architecture ripples through the whole backlog, update the nearby tasks that inherit that assumption.
- When a task says "wired", verify the actual ingress, transit, and egress path.
- When a task says "done", look for runtime evidence, not just authored files.
- If the repo contains several planning surfaces, keep them subordinate to Taskwarrior once reconciliation is finished.
