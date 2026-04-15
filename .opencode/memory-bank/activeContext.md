# Active Context

**Taskwarrior is the source of truth.** This file answers "what's going on?"
Run `task list project:osmen` to answer "what happens next?"

## Current State

- **Branch**: install/fresh-setup-20260407
- **TW**: reconciliation ledger verified 370 install tasks total, 127 pending across 14 install sub-projects
- **Immediate execution gate**: Tier 1 stabilization tranche from `temp_1st_install/RECONCILIATION_LEDGER.md`
- **Primary build lane after stabilization**: P19 orchestration — 23 tasks, `core/orchestration/` doesn't exist yet
- **Blocked**: P22 verification (39 tasks) waiting on stabilization + P19
- **Partially ready**: P14m voice/models and P17 ingress wiring exist, but both still depend on missing runtime or migrations
- **Operational findings**: 12 failing tests, 20 unhealthy containers, 6 failing user services are catalogued and task-shaped

## Verified This Session

- full reconciliation ledger written to `temp_1st_install/RECONCILIATION_LEDGER.md`
- P0-P7, P9, P11, P12, and P15 mechanically verified green; P18 is functionally complete with one future mount task
- Redis auth was verified via in-container env expansion; literal host CLI password passing is unsafe for the current base64 secret
- healthcheck failures, timer/service gaps, and test regressions were reduced to a Tier 1 stabilization tranche ahead of new P19 code
- resume surfaces now point at the reconciled order instead of the pre-audit build order
