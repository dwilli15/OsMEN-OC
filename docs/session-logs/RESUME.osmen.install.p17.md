# Resume Lane — osmen.install::p17-task-ingress

**Resume ID**: `resume.osmen.install.p17.task-ingress.2026-04-14`
**Resume Lane**: `osmen.install::p17-task-ingress`
**Pointer Role**: `supporting_execution`
**Last handoff**: [2026-04-14_235950_handoff.md](2026-04-14/2026-04-14_235950_handoff.md)
**Taskwarrior query**: `task project:osmen.install.p17 list`

## Scope

Finish the Taskwarrior ingress lane without pretending the orchestration runtime already exists.

## Mechanically Verified Complete

- `P17.1` `~/.taskrc` and `~/.task` present and populated
- `P17.2` task inventory, hook wiring, and project counts verified
- `P17.3` UDAs already defined
- `P17.4` Taskwarrior hooks exist and are symlinked into `~/.task/hooks/`
- `P17.6` [`core/tasks/sync.py`](/home/dwill/dev/OsMEN-OC/core/tasks/sync.py:1) exists and `tests/test_tasks.py` passes

## Active Fronts

- `P17.5` operator decision: bidirectional vs operator-only calendar policy
- `P17.7` verified only through `queue -> event bus publication`
- `P17.9` tasks-domain workflow creation and receipt logging still missing
- `P17.10` Taskwarrior-facing reports/filters still missing
- `P17.11` `taskwarrior_sync` manifest/pipeline wiring is dead until handlers exist or are removed
- `P17.8` stays blocked until the unfinished wiring above is real

## Next 1-3 Actions

1. If you are writing code in this lane, start with `P17.9` or `P17.11`.
2. Do not mark end-to-end ingress complete based only on hook or queue tests.
3. Keep commit work in `P17.8` blocked until the real ingress path is exercised.

## Blockers

- `core/orchestration/` does not exist yet, so full workflow ingress cannot be proven
- calendar behavior is still waiting on user policy in `P17.5`
