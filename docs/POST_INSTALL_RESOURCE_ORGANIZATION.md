# Resource Catalog

**Purpose**: Reference document for what exists and where. Not a task list — see Taskwarrior
(`task project:osmen.audit list`) for actions.

## Inventory Summary

| Category             | Count            | Location                                              | Status                     |
| -------------------- | ---------------- | ----------------------------------------------------- | -------------------------- |
| Agent manifests      | 9                | `agents/`                                             | Active                     |
| OpenCode skills      | 21               | `~/.config/opencode/skill/`                           | Active, some unused        |
| Claude skills        | 23               | `~/.claude/skills/`                                   | ~95% duplicate of OpenCode |
| Agent definitions    | 11 dirs          | `~/.config/opencode/agent/` + `~/.claude/agents/`     | Duplicated                 |
| Core modules         | 23 files         | `core/`                                               | Active                     |
| P19 target modules   | 14 files         | `core/` subdirs                                       | Not built                  |
| Orchestration        | 0 files          | `core/orchestration/`                                 | Directory doesn't exist    |
| Config files         | 16               | `config/`                                             | Active                     |
| External configs     | 8+               | `~/.openclaw/`, `~/.config/opencode/`, snap/waveterm/ | Active                     |
| Scripts              | 12               | `scripts/`                                            | Active                     |
| Quadlets             | 60+              | `quadlets/`                                           | Active                     |
| Timers               | 5                | `timers/`                                             | Active                     |
| Migrations           | 2                | `migrations/`                                         | Applied                    |
| Tests                | 22               | `tests/`                                              | Active                     |
| Docs                 | 4 + session logs | `docs/`                                               | Active                     |
| Copilot instructions | 12               | `.github/instructions/`                               | Active                     |
| Memory bank          | 6 files          | `.opencode/memory-bank/`                              | Active                     |
| OpenClaw workspace   | 7+ files         | `openclaw/`                                           | Active                     |
| Autonomous logs      | 12 logs          | `.remember/logs/autonomous/`                          | Unknown source             |

## Duplicates Requiring Consolidation

| What                      | Locations                                          | Action (see TW AUDIT-002 through AUDIT-004) |
| ------------------------- | -------------------------------------------------- | ------------------------------------------- |
| Skills (21/23 shared)     | `~/.config/opencode/skill/` vs `~/.claude/skills/` | Consolidate to one, symlink other           |
| Agent defs (11 identical) | `~/.config/opencode/agent/` vs `~/.claude/agents/` | Consolidate to one, symlink other           |
| PIPELINE_CONNECTIONS      | `config/`, `core/`, `scripts/` (3 copies)          | Keep `config/`, symlink others              |

## Stale Artifacts

| What                          | Location              | Action (see TW AUDIT-008 through AUDIT-010) |
| ----------------------------- | --------------------- | ------------------------------------------- |
| temp_1st_install/ (12 files)  | `temp_1st_install/`   | Archive or delete                           |
| OpenClaw config backups (4)   | `~/.openclaw/*.bak.*` | Trim to 1                                   |
| Vim swap file                 | `~/.openclaw/.swp`    | Delete                                      |
| start-claude-osmen.sh.bak     | `scripts/appdrawer/`  | Delete                                      |
| INSTALL_HANDOFF_2026-04-07.md | `docs/`               | Move to archive                             |

## Propagation Needed

| What              | From                                     | To                             | TW Task   |
| ----------------- | ---------------------------------------- | ------------------------------ | --------- |
| Pre-commit hook   | `scripts/hooks/pre-commit-secrets`       | `.git/hooks/pre-commit`        | AUDIT-011 |
| .desktop file     | `scripts/appdrawer/claude-osmen.desktop` | `~/.local/share/applications/` | AUDIT-011 |
| Taskwarrior hooks | `scripts/taskwarrior/on-*-osmen.py`      | `~/.task/hooks/`               | AUDIT-011 |
| Codex spec        | `~/Downloads/.../codex_.txt.md`          | `docs/specs/`                  | AUDIT-006 |
| Agent discussions | `~/Downloads/.../agent discussion/`      | `docs/specs/`                  | AUDIT-007 |

## Deprecation Targets

| What                | Location                                     | Replacement             | TW Task   |
| ------------------- | -------------------------------------------- | ----------------------- | --------- |
| ChromaStore         | `core/memory/store.py`                       | MemoryHub (`hub.py`)    | AUDIT-012 |
| LateralBridge       | `core/memory/lateral.py`                     | MemoryHub hybrid search | AUDIT-012 |
| Unused skills (TBD) | reachy-mini-sdk, datadog, notion, jira, glab | —                       | AUDIT-001 |

## External Services (verified 2026-04-14)

| Service          | Endpoint | Running               |
| ---------------- | -------- | --------------------- |
| OpenClaw gateway | :18789   | Yes                   |
| Lemonade         | :13305   | Yes (8 models loaded) |
| Ollama           | :11434   | Yes (4 models)        |
| LM Studio        | :1234    | Not checked           |
