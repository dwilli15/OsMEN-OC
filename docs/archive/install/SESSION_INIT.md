# First Install Session — Init Snapshot
## Date: 2026-04-07
## Branch: install/fresh-setup-20260407

## System State at Session Start

| Item | Value |
|------|-------|
| OS | Ubuntu 26.04 (Resolute Raccoon) — development branch |
| Python | 3.14.3 (system) — project requires 3.13 in .venv |
| Git branch | `install/fresh-setup-20260407` (off `main` at `a4b637c`) |
| Git identity | NOT configured (blocks commits) |
| Podman | NOT installed |
| sops | NOT installed |
| OpenClaw | NOT installed |
| .venv | NOT created |
| Secrets | None created |
| Quadlets | NOT deployed |
| Timers | NOT deployed |
| Core services | NOT running |

## Staged Changes (uncommitted)
- `scripts/bootstrap.sh` — `sudo` → `pkexec` (4 occurrences)

## Untracked Files
- `OsMEN-OC.code-workspace`
- `docs/INSTALL_HANDOFF_2026-04-07.md`

## Python Version Conflict
- System Python is 3.14.3
- `pyproject.toml` requires `>=3.12`
- `Makefile` verify-python enforces exactly 3.13
- **Resolution needed**: Either install python3.13 or relax the Makefile check

## Key Directories
- Repo root: `/home/dwill/dev/OsMEN-OC`
- Workspace assets: `/home/dwill/dev/.github/`, `/home/dwill/dev/.vscode/` (outside repo)
- Config target: `~/.config/osmen/`
- Quadlet target: `~/.config/containers/systemd/`
- Timer target: `~/.config/systemd/user/`

## Privilege Escalation
- Use `pkexec` (PolicyKit GUI dialog) — NEVER sudo
- bootstrap.sh already patched but not committed

## Rules for This Session
- NO installations or system changes without explicit user approval
- `temp_1st_install/` is ephemeral — for logs, scratch, session state only
- Must be in `.gitignore`
