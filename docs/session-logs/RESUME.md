<<<<<<< HEAD
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
- **HEAD**: `c31a44e` — fix(gateway): podman-only runtime + vision MCP handler wiring
- **Repo state**: run `git status --short` before acting
- **Tests**: 671 passed, 0 failed (2026-04-16)
- **Services**: 27 running, 1 failed (osmen-memory-maintenance.service)
- **Live services**: OpenClaw `:18789`, Gateway `:18788` (42 MCP tools), Lemonade `:13305`, Ollama `:11434`
- **Latest handoff**: [2026-04-16_handoff.md](2026-04-16/2026-04-16_handoff.md)
- **Latest reconciliation ledger**: [RECONCILIATION_LEDGER.md](../../temp_1st_install/RECONCILIATION_LEDGER.md)
- **Audit dispatch surface**: [install-audit-dispatch.md](/home/dwill/dev/OsMEN-OC/openclaw/state/install-audit-dispatch.md)

## Resume Rule

1. Pick one lane.
2. Read that lane file before older handoffs.
3. Run the matching Taskwarrior query.
4. Update the lane file when pausing.
5. Only rewrite this root dispatcher when the primary lane changes or a lane is added/retired.

## Current Priority

- **Primary lane remains P19** — 24 tasks, `core/orchestration/` doesn't exist yet, no stabilization gate remaining.
- **Start with P19.1** (package skeleton) → **P19.7** (typed models) → **P19.2-3-5** (registry, ledger, session).
- **Fix `osmen-memory-maintenance.service`** — the only failed service. Quick win.
- **P17 stays supporting work** and should not outrun the runtime that P19 creates.
- **User-blocked tasks**: P10.6/P10.8 (creds), P13.8 (Plex), P16.4 (Nextcloud), P17.5 (calendar), P20.1 (Steam) — do not attempt.
=======
# OsMEN-OC Session Resume Pointer

**Last handoff**: 2026-04-12 00:02:41 CDT  
**Report**: [2026-04-12_000241_handoff.md](2026-04-12/2026-04-12_000241_handoff.md)

## How to Resume

1. Open VS Code in `~/dev/OsMEN-OC`
2. In Chat, switch to **z_final_install** agent mode
3. Say: **"Resume from handoff"**

## State at Pause

- **Branch**: `install/fresh-setup-20260407` (dirty — untracked files to commit in P2.12)
- **Phases done**: P0, P1, P2 (pending P2.12 commit), P4
- **Next immediate action**: `git add ... && git commit` for P2.12, then start Phase 3 (Python venv)
- **Phase 3 entry point**: `uv venv /home/dwill/dev/.venv --python 3.13`
- **OpenClaw**: 2026.4.10, Telegram up, Discord not yet configured
- **Ollama**: running with `nomic-embed-text` for local memory search
- **Podman**: 5.7.0 rootless ✅, 5 cgroup slices deployed ✅

## Previous Handoff

- **2026-04-07 14:11:37 CDT** — [2026-04-07_141137_handoff.md](2026-04-07/2026-04-07_141137_handoff.md)
>>>>>>> origin/main
