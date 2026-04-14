# Post-First-Install Resource Organization Plan

**Created**: 2026-04-14
**Purpose**: Complete audit and reorganization of all resources across the OsMEN-OC
ecosystem. Deprecate stale artifacts, consolidate duplicates, symlink shared resources
through pipelines, and ensure every tool/config/agent/skill is discoverable and available
to every runtime that needs it.

---

## Resource Categories

### 1. AGENTS (9 manifests + external agent systems)

| Resource                    | Location                                                  | Status           | Action                                               |
| --------------------------- | --------------------------------------------------------- | ---------------- | ---------------------------------------------------- |
| boot_hardening.yaml         | `agents/`                                                 | Active           | Keep                                                 |
| daily_brief.yaml            | `agents/`                                                 | Active           | Keep                                                 |
| focus_guardrails.yaml       | `agents/`                                                 | Active           | Keep                                                 |
| knowledge_librarian.yaml    | `agents/`                                                 | Active           | Keep                                                 |
| media_organization.yaml     | `agents/`                                                 | Active           | Keep                                                 |
| research.yaml               | `agents/`                                                 | Active           | Keep                                                 |
| secrets_custodian.yaml      | `agents/`                                                 | Active           | Keep                                                 |
| system_monitor.yaml         | `agents/`                                                 | Active           | Keep                                                 |
| taskwarrior_sync.yaml       | `agents/`                                                 | Active           | Keep                                                 |
| OpenClaw workspace identity | `openclaw/` (SOUL/IDENTITY/MEMORY/AGENTS/TOOLS)           | Active           | Keep — needs extension for orchestration roles       |
| OpenClaw .openclaw state    | `openclaw/.openclaw/workspace-state.json`                 | Active           | Keep                                                 |
| Claude Code agents library  | `~/.claude/agents/` (11 directories, 55+ agent .md files) | External, active | Symlink key agents into OsMEN repo as reference docs |
| OpenCode agent definitions  | `~/.config/opencode/agent/` (11 directories)              | External, active | Mirror of Claude agents — consolidate, de-dupe       |

**New agents needed (from orchestration spec)**:

- `agents/orchestration/steward.yaml`
- `agents/orchestration/planner.yaml`
- `agents/orchestration/naysayer.yaml`
- `agents/orchestration/verifier.yaml`
- `agents/orchestration/watchdog_storm.yaml`
- `agents/orchestration/watchdog_freshness.yaml`
- `agents/orchestration/watchdog_receipt.yaml`
- `agents/orchestration/memory_curator.yaml`
- `agents/orchestration/summarizer.yaml`

### 2. SKILLS (21 OpenCode + 21 Claude + 1 GitHub Copilot)

| Resource                     | Location                                  | Status                             | Action                                                                                                                   |
| ---------------------------- | ----------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| OpenCode skills (21)         | `~/.config/opencode/skill/`               | Active, shared with Claude         | Audit each — some unused                                                                                                 |
| Claude skills (23)           | `~/.claude/skills/`                       | Active, near-identical to OpenCode | **CONSOLIDATE**: OpenCode and Claude skill dirs are ~95% duplicated. Pick one authoritative location, symlink the other. |
| GitHub Copilot skill         | `.github/skills/python-conventions/`      | Active, repo-local                 | Keep                                                                                                                     |
| Media skills (Windows ports) | Referenced in Taskwarrior tasks D.19-D.26 | **Not yet migrated**               | Port from Windows PS to Bash/Python                                                                                      |

**Skills audit needed**:

- `reachy-mini-sdk` — is this robot SDK actually used?
- `datadog` — is the Datadog CLI used locally?
- `notion` — is Notion CLI configured with credentials?
- `jira` — is Jira actually used for this project?
- `glab` — is GitLab used (repo is on GitHub)?
- `meeting-insights-analyzer` — used?
- `content-research-writer` — used for manifesto drafts, keep

### 3. MCP SERVERS

| Resource                                     | Location                                                | Status       | Action                                          |
| -------------------------------------------- | ------------------------------------------------------- | ------------ | ----------------------------------------------- |
| Claude Code bridge                           | `~/.local/share/claude-bridge/server.mjs`               | Active       | Keep — functional                               |
| OpenCode MCP config                          | `~/.config/opencode/opencode.json` (mcpServers section) | Active       | Audit which MCP servers are actually configured |
| OsMEN gateway MCP                            | `core/gateway/mcp.py`                                   | Active, code | Keep — auto-registers agent tools               |
| ZAI MCP server (filesystem, puppeteer, etc.) | Running in this session                                 | External     | Document in tech context                        |
| Filesystem MCP                               | `~/.config/opencode/` via opencode.json                 | Active       | Already configured                              |

### 4. CONFIG FILES (repo)

| Resource                             | Location                                | Status                                           | Action                                      |
| ------------------------------------ | --------------------------------------- | ------------------------------------------------ | ------------------------------------------- |
| agents.yaml                          | `config/`                               | Active                                           | Keep — agent registry                       |
| compute-routing.yaml                 | `config/`                               | Active                                           | Keep — verified                             |
| hardware.yaml                        | `config/`                               | Active                                           | Keep                                        |
| openclaw.yaml                        | `config/`                               | Active                                           | Keep                                        |
| pipelines.yaml                       | `config/`                               | Active                                           | Keep                                        |
| Caddyfile                            | `config/`                               | Active                                           | Keep                                        |
| prometheus.yml                       | `config/`                               | Active                                           | Keep                                        |
| secrets-registry.yaml                | `config/`                               | Active                                           | Keep                                        |
| restic-db-paths.txt                  | `config/`                               | Active                                           | Keep                                        |
| voice/stt.yaml                       | `config/voice/`                         | Needs migration to lemonade API                  | Update after voice migration                |
| voice/tts.yaml                       | `config/voice/`                         | Needs migration to lemonade API                  | Update after voice migration                |
| api-keys.template.yaml               | `config/secrets/`                       | Template                                         | Keep                                        |
| gh-token.template.yaml               | `config/secrets/`                       | Template                                         | Keep                                        |
| oauth-tokens.template.yaml           | `config/secrets/`                       | Template                                         | Keep                                        |
| PIPELINE_CONNECTIONS.instructions.md | `config/`                               | **DUPLICATE** — also in `core/` and `scripts/`   | Consolidate to one location, symlink others |
| agents.yaml vs individual manifests  | `config/agents.yaml` vs `agents/*.yaml` | **Potential conflict** — which is authoritative? | Audit and clarify                           |

### 5. CONFIG FILES (external)

| Resource                 | Location                                                    | Status                  | Action                                            |
| ------------------------ | ----------------------------------------------------------- | ----------------------- | ------------------------------------------------- |
| OpenClaw main config     | `~/.openclaw/openclaw.json`                                 | Active, 4 backup copies | Trim backups, keep latest only                    |
| OpenClaw env             | `~/.config/osmen/env`                                       | Active, secrets         | Keep                                              |
| OpenClaw secrets         | `~/.config/osmen/secrets/`                                  | Active                  | Keep                                              |
| OpenClaw systemd service | `~/.config/systemd/user/openclaw-gateway.service`           | Active                  | Keep                                              |
| Wave AI config           | `/snap/waveterm/198/.config/waveterm/waveai.json`           | Active                  | Keep                                              |
| Wave settings            | `/snap/waveterm/198/.config/waveterm/settings.json`         | Active                  | Keep                                              |
| OpenCode config          | `~/.config/opencode/opencode.json`                          | Active                  | Keep                                              |
| OpenCode TUI config      | `~/.config/opencode/tui.jsonc`                              | Active                  | Keep                                              |
| Claude settings          | `~/.claude/settings.local.json` (in repo)                   | Active                  | Keep                                              |
| Taskwarrior config       | `~/.taskrc`                                                 | Active                  | Keep                                              |
| Taskwarrior hooks        | `scripts/taskwarrior/on-add-osmen.py`, `on-modify-osmen.py` | Active                  | Keep — symlink to `~/.task/hooks/` if not already |

### 6. SCRIPTS

| Resource                  | Location                            | Status                              | Action                                           |
| ------------------------- | ----------------------------------- | ----------------------------------- | ------------------------------------------------ |
| bootstrap.sh              | `scripts/`                          | Active                              | Keep                                             |
| deploy_quadlets.sh        | `scripts/`                          | Active                              | Keep                                             |
| deploy_timers.sh          | `scripts/`                          | Active                              | Keep                                             |
| lemonade-autoload.sh      | `scripts/`                          | Active                              | Keep                                             |
| export_credential_kit.sh  | `scripts/secrets/`                  | Active                              | Keep                                             |
| pre-commit-secrets        | `scripts/hooks/`                    | Active                              | Keep — symlink to `.git/hooks/`                  |
| start-claude-osmen.sh     | `scripts/appdrawer/`                | Active                              | Keep                                             |
| start-claude-osmen.sh.bak | `scripts/appdrawer/`                | **Stale backup**                    | Delete                                           |
| start-osmen-tmux.sh       | `scripts/appdrawer/`                | Active                              | Keep                                             |
| tmux-osmen.conf           | `scripts/appdrawer/`                | Active                              | Keep                                             |
| claude-osmen.desktop      | `scripts/appdrawer/`                | Active                              | Keep — symlink to `~/.local/share/applications/` |
| load_tasks.sh             | `temp_1st_install/`                 | **Stale** — one-time install script | Move to `scripts/install/` or delete             |
| Media scripts (planned)   | Referenced in ~30 Taskwarrior tasks | **Not yet written**                 | Write in `scripts/media/` per task plan          |

### 7. WORKFLOWS

| Resource             | Location                                  | Status | Action |
| -------------------- | ----------------------------------------- | ------ | ------ |
| CI workflow          | `.github/workflows/ci.yml`                | Active | Keep   |
| Copilot setup steps  | `.github/copilot-setup-steps.yml`         | Active | Keep   |
| Copilot instructions | `.github/copilot-instructions.md`         | Active | Keep   |
| Issue template       | `.github/ISSUE_TEMPLATE/copilot-task.yml` | Active | Keep   |
| PR template          | `.github/pull_request_template.md`        | Active | Keep   |
| Pre-commit config    | `.pre-commit-config.yaml`                 | Active | Keep   |

### 8. PIPELINES

| Resource                  | Location                       | Status               | Action                                          |
| ------------------------- | ------------------------------ | -------------------- | ----------------------------------------------- |
| Pipeline runner           | `core/pipelines/runner.py`     | Active               | Keep                                            |
| Pipeline config           | `config/pipelines.yaml`        | Active               | Keep                                            |
| Task queue                | `core/tasks/queue.py`          | Active               | Keep                                            |
| Task sync                 | `core/tasks/sync.py`           | Active               | Keep                                            |
| PIPELINE_CONNECTIONS (×3) | `config/`, `core/`, `scripts/` | **TRIPLE DUPLICATE** | Keep one in `config/`, delete or symlink others |

### 9. QUADLETS (60+ container definitions)

| Profile                               | Count | Status | Action |
| ------------------------------------- | ----- | ------ | ------ |
| core (7 containers + network + slice) | 9     | Active | Keep   |
| inference (2 + docs)                  | 3     | Active | Keep   |
| librarian (4)                         | 4     | Active | Keep   |
| media (15 + pod + network + volumes)  | 18    | Active | Keep   |
| monitoring (4)                        | 4     | Active | Keep   |
| slices (4)                            | 4     | Active | Keep   |
| volumes (26)                          | 26    | Active | Keep   |

All in `quadlets/` — deployed via `deploy_quadlets.sh`. No action needed on structure.

### 10. TIMERS

| Resource                                | Location  | Status | Action |
| --------------------------------------- | --------- | ------ | ------ |
| osmen-db-backup (.service + .timer)     | `timers/` | Active | Keep   |
| osmen-npu-autoload (.service)           | `timers/` | Active | Keep   |
| osmen-secrets-audit (.service + .timer) | `timers/` | Active | Keep   |

### 11. MIGRATIONS

| Resource                       | Location        | Status     | Action                           |
| ------------------------------ | --------------- | ---------- | -------------------------------- |
| 001_initial_schema.sql         | `migrations/`   | Applied    | Keep                             |
| 002_unified_memory.sql         | `migrations/`   | Applied    | Keep                             |
| Orchestration tables (pending) | Not yet written | **Needed** | Write as `003_orchestration.sql` |

### 12. DOCS

| Resource                           | Location                                                       | Status                                 | Action                                                    |
| ---------------------------------- | -------------------------------------------------------------- | -------------------------------------- | --------------------------------------------------------- |
| GITHUB_AGENT_OPERATIONS.md         | `docs/`                                                        | Active                                 | Keep                                                      |
| INSTALL_HANDOFF_2026-04-07.md      | `docs/`                                                        | **Stale** — superseded by session-logs | Move to `docs/archive/`                                   |
| OUTSIDE_AUDIT_REPORT.md            | `docs/`                                                        | Reference                              | Keep                                                      |
| REPO_AUDIT_2026-04-05.md           | `docs/`                                                        | Reference                              | Keep                                                      |
| Session logs (7 handoffs)          | `docs/session-logs/`                                           | Active                                 | Keep — RESUME.md points to latest                         |
| Manifesto (5 drafts + final + PDF) | `roundtable/`                                                  | Active                                 | Keep                                                      |
| Codex spec                         | `~/Downloads/temp/Integrate_os/agent discussion/codex_.txt.md` | Active, external                       | **Copy into repo** at `docs/specs/codex-orchestration.md` |
| Other agent discussions            | `~/Downloads/temp/Integrate_os/agent discussion/` (5 files)    | Reference                              | Copy relevant ones into `docs/specs/`                     |

### 13. MEMORY SYSTEMS (4 disconnected systems)

| Resource                  | Location                                      | Status                | Action                              |
| ------------------------- | --------------------------------------------- | --------------------- | ----------------------------------- |
| OpenCode Memory Bank      | `.opencode/memory-bank/` (6 files)            | Active, just updated  | Keep — add auto-sync                |
| OpenClaw workspace memory | `openclaw/memory/` (7 .md + dreams/)          | Active                | Keep — wire into MemoryHub          |
| OpenClaw workspace state  | `openclaw/state/`                             | Active                | Keep                                |
| Autonomous logs           | `.remember/logs/autonomous/` (12 logs)        | Unknown source        | Audit — what writes these?          |
| Session PID file          | `.remember/tmp/save-session.pid`              | Active                | Keep                                |
| Vault (empty)             | `vault/` (backups/, logs/, memory/ all empty) | **Empty scaffold**    | Wire into memory system or remove   |
| MemoryHub (PostgreSQL)    | `core/memory/hub.py`                          | Code exists, needs DB | Ensure DB is running                |
| ChromaStore (legacy)      | `core/memory/store.py`                        | Legacy                | Deprecate after MemoryHub migration |
| LateralBridge             | `core/memory/lateral.py`                      | Legacy                | Deprecate after MemoryHub migration |

### 14. TEMPORARY / STALE

| Resource                     | Location                                      | Status                      | Action                    |
| ---------------------------- | --------------------------------------------- | --------------------------- | ------------------------- |
| temp_1st_install/ (12 files) | `temp_1st_install/`                           | **Stale install artifacts** | Review, archive or delete |
| start-claude-osmen.sh.bak    | `scripts/appdrawer/`                          | **Stale backup**            | Delete                    |
| OpenClaw config backups (4)  | `~/.openclaw/openclaw.json.bak.*`             | **Stale backups**           | Trim to 1                 |
| swp file                     | `~/.openclaw/.deep-package-researcher.md.swp` | **Vim swap file**           | Delete                    |
| tatus                        | `tatus` (repo root)                           | **Unknown binary/file**     | Identify and classify     |

### 15. INTERFACING / BRIDGES

| Resource                | Location                                  | Status          | Action                        |
| ----------------------- | ----------------------------------------- | --------------- | ----------------------------- |
| WebSocket bridge client | `core/bridge/ws_client.py`                | Active          | Keep                          |
| Bridge protocol         | `core/bridge/protocol.py`                 | Active, minimal | Extend with typed event types |
| Claude Code MCP bridge  | `~/.local/share/claude-bridge/server.mjs` | Active          | Keep                          |
| Wave Terminal AI        | Snap package config                       | Active          | Keep                          |
| OpenCode TUI            | `~/.config/opencode/tui.jsonc`            | Active          | Keep                          |

### 16. GITHUB COPILOT INSTRUCTIONS (12)

| Resource                                   | Location                | Status | Action |
| ------------------------------------------ | ----------------------- | ------ | ------ |
| agent-manifests.instructions.md            | `.github/instructions/` | Active | Keep   |
| config-files.instructions.md               | `.github/instructions/` | Active | Keep   |
| install-audit.instructions.md              | `.github/instructions/` | Active | Keep   |
| python-code.instructions.md                | `.github/instructions/` | Active | Keep   |
| python-security-guidelines.instructions.md | `.github/instructions/` | Active | Keep   |
| python-test-guidelines.instructions.md     | `.github/instructions/` | Active | Keep   |
| quadlet-files.instructions.md              | `.github/instructions/` | Active | Keep   |
| secrets-lifecycle.instructions.md          | `.github/instructions/` | Active | Keep   |
| shell-scripts.instructions.md              | `.github/instructions/` | Active | Keep   |
| test-files.instructions.md                 | `.github/instructions/` | Active | Keep   |
| update-activity-workflow.instructions.md   | `.github/instructions/` | Active | Keep   |
| copilot-instructions.md                    | `.github/`              | Active | Keep   |

---

## Consolidation Actions (ordered by impact)

### Critical — Duplicates and Conflicts

1. **TRIPLE PIPELINE_CONNECTIONS.instructions.md** — identical file in `config/`, `core/`, and `scripts/`. Keep `config/PIPELINE_CONNECTIONS.instructions.md` as canonical. Delete the other two or replace with symlinks.

2. **DUAL SKILL DIRECTORIES** — `~/.config/opencode/skill/` and `~/.claude/skills/` contain 21 near-identical skill directories. Pick one authoritative location. Symlink from the other. Recommendation: keep `~/.config/opencode/skill/` as source (it's the active runtime), symlink `~/.claude/skills/` to it. But audit first — Claude skills has `handoff-continue` and `handoff-resume` that OpenCode doesn't.

3. **DUAL AGENT DIRECTORIES** — `~/.config/opencode/agent/` and `~/.claude/agents/` contain the same 11 domain directories. Same consolidation approach.

4. **config/agents.yaml vs agents/\*.yaml** — determine which is the source of truth for the MCP registry. The individual manifests in `agents/` are detailed; `config/agents.yaml` may be a summary. Audit and clarify.

### Important — Stale Cleanup

5. **temp_1st_install/** — 12 files from the initial install. Review each:
   - `INSTALL_PLAN.md`, `INSTALL_PLAN_v1_172steps.md`, `INSTALL_INSTRUCTIONS.md` — archive to `docs/archive/install/`
   - `install.log`, `temp_preplancleanos.txt` — delete
   - `load_tasks.sh` — check if still needed, merge into `scripts/` or delete
   - `HANDOFF_5PHASE_AUTONOMOUS.md`, `SESSION_INIT.md`, `LAUNCHER_HANDOFF.md`, `GOOGLE_OAUTH_PIPELINE_A.instructions.md`, `AUDIT_FINDINGS.md`, `install_agent.md` — archive

6. **OpenClaw config backups** — `~/.openclaw/openclaw.json.bak.1` through `.bak.4` — keep only the latest `.bak`, delete the rest.

7. **Vim swap file** — delete `~/.openclaw/.deep-package-researcher.md.swp`.

8. **scripts/appdrawer/start-claude-osmen.sh.bak.20260412-083515** — delete.

9. **Vault directory** — `vault/` has empty subdirectories. Either wire it into the memory system (the handoff spec mentions it as the backup target) or remove the empty scaffold.

### Important — Propagation

10. **Symlink pre-commit hook** — `scripts/hooks/pre-commit-secrets` should be symlinked to `.git/hooks/pre-commit` if not already.

11. **Symlink .desktop file** — `scripts/appdrawer/claude-osmen.desktop` should be symlinked to `~/.local/share/applications/claude-osmen.desktop`.

12. **Symlink Taskwarrior hooks** — `scripts/taskwarrior/on-add-osmen.py` and `on-modify-osmen.py` should be symlinked into `~/.task/hooks/`.

13. **Copy codex spec into repo** — `~/Downloads/temp/Integrate_os/agent discussion/codex_.txt.md` → `docs/specs/codex-orchestration.md`. This is too important to leave in Downloads.

14. **Copy agent discussions** — the other 4 files in `~/Downloads/temp/Integrate_os/agent discussion/` are reference material. Copy to `docs/specs/agent-discussions/`.

15. **Wire vault/ to memory system** — `vault/backups/`, `vault/logs/`, `vault/memory/` should be the local backup targets for the memory pipeline.

### Deprecation

16. **ChromaStore → MemoryHub** — `core/memory/store.py` and `core/memory/lateral.py` target ChromaDB. Mark as deprecated with a comment and a deprecation notice in `__init__.py`. New code targets MemoryHub exclusively.

17. **Skills not in use** — audit `reachy-mini-sdk`, `datadog`, `notion`, `jira`, `glab`. If credentials aren't configured and no tasks reference them, move to a `skills/inactive/` directory.

18. **P22.17 Tailscale** — already marked deprecated in Taskwarrior. Remove or archive the task.

---

## Taskwarrior Tasks for Complete Audit Agent

These tasks should be added to Taskwarrior under project `osmen.audit` with a
`complete_audit` tag. They represent the full resource audit and reorganization.
