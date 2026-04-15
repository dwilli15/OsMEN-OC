# OsMEN-OC Resume Dispatcher

**Taskwarrior is the source of truth.** Use this file to choose the right lane, then switch to the lane pointer plus the live Taskwarrior query for execution truth.

## Active Lanes

- **Primary build lane — orchestration spine (`osmen.install.p19`)**
  Read [RESUME.osmen.install.p19.md](RESUME.osmen.install.p19.md)
  Taskwarrior: `task project:osmen.install.p19 list`

- **Supporting build lane — Taskwarrior ingress and operator workflow (`osmen.install.p17`)**
  Read [RESUME.osmen.install.p17.md](RESUME.osmen.install.p17.md)
  Taskwarrior: `task project:osmen.install.p17 list`

- **Parallel execution lane — media cleanup and transfer automation (`osmen.media`)**
  Read [RESUME.osmen.media.md](RESUME.osmen.media.md)
  Taskwarrior: `task project:osmen.media list`

- **Parallel audit lane — resource consolidation and repo hygiene (`osmen.audit`)**
  Read [RESUME.osmen.audit.md](RESUME.osmen.audit.md)
  Taskwarrior: `task project:osmen.audit list`

## Shared State

- **Branch**: `install/fresh-setup-20260407`
- **Repo state**: run `git status --short` before acting
- **Live services**: OpenClaw `:18789`, Lemonade `:13305`, Ollama `:11434`
- **Latest reconciliation ledger**: [RECONCILIATION_LEDGER.md](../../temp_1st_install/RECONCILIATION_LEDGER.md)
- **Latest orchestration direction**: [2026-04-14_235950_handoff.md](2026-04-14/2026-04-14_235950_handoff.md)
- **Latest orchestration build handoff**: [2026-04-14_234500_handoff.md](2026-04-14/2026-04-14_234500_handoff.md)
- **Latest media recon handoff**: [handoff_2026-04-14_144435/handoff.md](2026-04-14/handoff_2026-04-14_144435/handoff.md)
- **Audit dispatch surface**: [install-audit-dispatch.md](/home/dwill/dev/OsMEN-OC/openclaw/state/install-audit-dispatch.md)

## Resume Rule

1. Pick one lane.
2. Read that lane file before older handoffs.
3. Run the matching Taskwarrior query.
4. Update the lane file when pausing.
5. Only rewrite this root dispatcher when the primary lane changes or a lane is added/retired.

## Current Priority

- **Primary lane remains P19**, but the next executable tranche is the verified Tier 1 stabilization work in the reconciliation ledger.
- **Clear or explicitly defer the five quick wins first**: timer service definitions, quadlet hardening, Plex handler tests, and the backup env-path mismatch.
- **Resume package/model work in P19 immediately after that tranche**, starting with `core/orchestration/` and typed models.
- **P17 stays supporting work** and should not outrun the runtime that P19 creates.
