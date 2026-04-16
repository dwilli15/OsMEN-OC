# Resume Lane — osmen.media

**Resume ID**: `resume.osmen.media.execution.2026-04-14`
**Resume Lane**: `osmen.media::execution`
**Pointer Role**: `parallel_execution`
**Last handoff**: [handoff_2026-04-14_144435/handoff.md](2026-04-14/handoff_2026-04-14_144435/handoff.md)
**Taskwarrior query**: `task project:osmen.media list`

## Scope

Media cleanup, naming, transfer automation, and infra fixes discovered during the April 14 reconnaissance session.

## Repo Reality

- the recon is done
- the 91-task media ledger exists in Taskwarrior
- most of the actual media scripts still do not exist
- this lane is not the primary build lane unless the user explicitly points here

## Entry Guidance

1. Read the media handoff before touching tasks.
2. Prefer one sub-phase at a time: dedup/naming, scripts, infra, or protocols.
3. Resolve user decisions explicitly when a task says `DECISION` or requires missing metadata like a release year.

## Good Starting Areas

- script-writing tasks in phase `D`
- infra repair tasks in phase `E`
- user-facing naming decisions before mass rename work

## Blockers

- some tasks require user decisions
- some tasks assume external drives are mounted and reachable
