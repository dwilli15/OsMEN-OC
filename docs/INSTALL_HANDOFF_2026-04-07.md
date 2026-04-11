# OsMEN-OC Fresh Install Handoff — 2026-04-07

## Context

- Fresh clone of OsMEN-OC at commit `a4b637c` (latest main, 21 commits).
- Local branch `install/fresh-setup-20260407` created with one staged change: `sudo` → `pkexec` in bootstrap.sh.
- Host: Ubuntu 26.04 (Resolute Raccoon dev), Python 3.14.3, `python3.14-venv` installed.
- No Podman installed yet. No containers, no secrets, no quadlet units, no user timers deployed.
- Setup wizard exists at `core/setup/wizard.py` — handles env file, OpenClaw config, LLM key, Telegram, Discord, Plex paths, Postgres/Redis DSNs.
- Workspace custom assets (agents, skills, instructions, prompts, hooks) live in `~/.github/` and `~/.vscode/` — outside OsMEN-OC, untouched.
- New workspace will be rooted at `~/dev/OsMEN-OC`.

## Privilege Escalation

- Use `pkexec` (PolicyKit GUI dialog), not `sudo`.
- Bootstrap.sh already patched on the local branch but not yet committed (git user.email/user.name needed first).

## Git Identity Needed

- `git config user.email` and `user.name` must be set inside OsMEN-OC before commits will work.

---

## Multi-Phase Install Plan

### Phase 0: Repository & Branch Setup
- [ ] 0.1 Configure git user.name and user.email inside OsMEN-OC
- [ ] 0.2 Commit the pkexec patch on `install/fresh-setup-20260407`
- [ ] 0.3 Verify clean branch state, confirm upstream tracking
- **Pause point:** Confirm branch is ready before any system changes.

### Phase 1: System Dependencies (apt)
- [ ] 1.1 Run `pkexec apt-get update`
- [ ] 1.2 Install apt packages: python3-dev, python3-venv, podman, podman-compose, taskwarrior, lm-sensors, smartmontools, restic, age, ffmpeg, git, curl, jq, nodejs/npm (if needed)
- [ ] 1.3 Verify each package installed and callable
- **Pause point:** Confirm all apt packages are present before moving to userland tools.

### Phase 2: Userland Tools (non-apt)
- [ ] 2.1 Install sops to ~/.local/bin
- [ ] 2.2 Verify sops version
- [ ] 2.3 Install OpenClaw (npm -g openclaw) or mark deferred if package not published
- [ ] 2.4 Verify PATH includes ~/.local/bin
- **Pause point:** All CLI tools available before Python environment setup.

### Phase 3: Python Environment
- [ ] 3.1 Create .venv with python3 -m venv
- [ ] 3.2 Bootstrap pip inside venv (ensurepip or get-pip fallback)
- [ ] 3.3 Install OsMEN-OC in editable mode with dev extras: `pip install -e ".[dev]"`
- [ ] 3.4 Verify: `python -c "import core"` succeeds
- [ ] 3.5 Run test suite: `make test`
- [ ] 3.6 Run lint: `make lint`
- [ ] 3.7 Run typecheck: `make typecheck`
- **Pause point:** Dev environment fully green before infrastructure setup.

### Phase 4: Rootless Podman
- [ ] 4.1 Verify subuid/subgid entries for user (add if missing, requires pkexec)
- [ ] 4.2 Enable podman.socket for user session
- [ ] 4.3 Verify `podman info` works rootless
- [ ] 4.4 Run `podman run --rm hello-world` (or equivalent) to confirm OCI runtime
- **Pause point:** Podman functional before deploying service containers.

### Phase 5: Quadlet Deployment (Core Services)
- [ ] 5.1 Deploy quadlet unit files (symlink to ~/.config/containers/systemd/)
- [ ] 5.2 systemctl --user daemon-reload
- [ ] 5.3 Verify units are visible: `systemctl --user list-unit-files | grep osmen`
- **Pause point:** Units registered but NOT started — secrets needed first.

### Phase 6: Secrets & Credentials
- [ ] 6.1 Create Podman secrets (postgres password, user, db, redis password, chromadb token) — auto-generated or user-provided
- [ ] 6.2 Optionally generate age key and configure SOPS for encrypted secrets
- [ ] 6.3 Verify: `podman secret ls` shows 5 osmen-* secrets
- **Pause point:** Secrets in place before starting services.

### Phase 7: Core Services Startup
- [ ] 7.1 Start osmen-core-postgres, osmen-core-redis, osmen-core-chromadb
- [ ] 7.2 Wait for health (up to 90s)
- [ ] 7.3 Verify each service: `podman ps`, connectivity checks
- [ ] 7.4 Run SQL migrations if migrations/ directory exists
- **Pause point:** Core data services running and healthy.

### Phase 8: Timers
- [ ] 8.1 Deploy systemd timer + service units (symlink to ~/.config/systemd/user/)
- [ ] 8.2 daemon-reload, enable and start timers
- [ ] 8.3 Verify: `systemctl --user list-timers --all | grep osmen`
- **Pause point:** Background maintenance scheduled.

### Phase 9: Setup Wizard (Interactive Config)
- [ ] 9.1 Run `python -m core.setup` (or `--reconfigure` if needed)
- [ ] 9.2 Gather LLM/GLM API key (ZAI) — guide user through account creation at open.bigmodel.cn if needed
- [ ] 9.3 Gather Telegram bot token and chat ID — guide user through @BotFather setup
- [ ] 9.4 Gather Discord bot token and guild ID (optional) — guide through Discord Developer Portal
- [ ] 9.5 Set OpenClaw WebSocket URL (default ws://127.0.0.1:18789)
- [ ] 9.6 Set Plex library root and download staging paths
- [ ] 9.7 Confirm Postgres DSN and Redis URL match running services
- [ ] 9.8 Verify written env file at ~/.config/osmen/env
- [ ] 9.9 Verify OpenClaw config at config/openclaw.yaml
- **Pause point:** Core configuration complete. Gateway should be startable.

### Phase 10: Gateway Validation
- [ ] 10.1 Start gateway: `make dev` (uvicorn on 127.0.0.1:8080)
- [ ] 10.2 Hit health endpoint, verify response
- [ ] 10.3 Verify event bus, bridge, and approval gate are wired
- **Pause point:** Core OsMEN-OC platform running.

### Phase 11: Extended Service Integration (Guided, One at a Time)

Each subsystem follows: install → configure → create accounts/OAuth → wire bridge → verify → update repo if needed → next.

#### 11a: Database Verification
- Already running from Phase 7 — verify schema, connectivity from gateway, data persistence across restart.

#### 11b: Siyuan Notes
- [ ] Install Siyuan (AppImage, flatpak, or Podman)
- [ ] Configure workspace, API token
- [ ] Wire OsMEN-OC knowledge/memory bridge to Siyuan API
- [ ] Verify: create and retrieve a test note via bridge

#### 11c: Nextcloud
- [ ] Deploy Nextcloud (Podman or external instance)
- [ ] Create admin account, configure storage
- [ ] Set up CalDAV/CardDAV, WebDAV endpoints
- [ ] Wire Taskwarrior sync, file sync, calendar bridge
- [ ] Verify: file upload/download, calendar event creation

#### 11d: Taskwarrior
- [ ] Configure Taskwarrior (~/.taskrc, data location)
- [ ] Set up sync (taskd or Nextcloud bridge)
- [ ] Wire OsMEN-OC task creation/query handler
- [ ] Verify: create and list tasks via OsMEN-OC

#### 11e: Plex Media Server
- [ ] Install Plex (snap, flatpak, or Podman)
- [ ] Configure library paths (match wizard settings)
- [ ] Plex account login (manual browser step)
- [ ] Claim server, configure remote access
- [ ] Wire OsMEN-OC media organization agent
- [ ] Verify: library scan, media visible in Plex

#### 11f: Prowlarr (Indexer Manager)
- [ ] Deploy Prowlarr (Podman)
- [ ] Configure indexers, API key
- [ ] Wire to download clients and OsMEN-OC
- [ ] Verify: search returns results

#### 11g: Book / Comic / Audiobook Servers
- [ ] Choose and deploy servers (Kavita, Komga, Audiobookshelf, Calibre-Web, etc.)
- [ ] Configure libraries, user accounts
- [ ] Wire OsMEN-OC knowledge librarian agent
- [ ] Verify: content browsable, metadata correct

#### 11h: TTS / STT / Transcription
- [ ] Choose engines (Piper TTS, Whisper STT, etc.)
- [ ] Install/deploy (local models or API-based)
- [ ] Wire OsMEN-OC voice pipeline
- [ ] Verify: text→speech and speech→text roundtrip

#### 11i: Telegram Bridge
- [ ] Bot created in Phase 9 — verify webhook or polling
- [ ] Send test message OsMEN-OC → Telegram
- [ ] Receive command Telegram → OsMEN-OC
- [ ] Verify approval gate notifications

#### 11j: Discord Bridge
- [ ] Bot created in Phase 9 — verify guild permissions
- [ ] Send test message OsMEN-OC → Discord
- [ ] Receive command Discord → OsMEN-OC
- [ ] Verify approval gate notifications

#### 11k: Privado VPN
- [ ] Install Privado VPN client
- [ ] Configure and authenticate
- [ ] Set up split tunneling or container-level VPN routing
- [ ] Verify: IP changes when VPN active, services unaffected

#### 11l: Port & Resource Management
- [ ] Audit all service ports, document in config
- [ ] Set up port conflict detection
- [ ] Configure resource limits (cgroups, systemd slices)
- [ ] Verify: no port conflicts, resources within bounds

### Phase 12: Final Verification & Repo Cleanup
- [ ] 12.1 Full test suite pass: `make check`
- [ ] 12.2 All services healthy: `make status`
- [ ] 12.3 All bridges verified end-to-end
- [ ] 12.4 Commit all repo changes on install branch
- [ ] 12.5 Push branch, create PR against main
- [ ] 12.6 File issues for any deferred items or known gaps
- **Pause point:** System fully operational. PR ready for review.

---

## Current Status (as of handoff)

| Phase | Status |
|-------|--------|
| 0 — Repo & Branch | In progress (branch created, pkexec patch staged, git identity needed) |
| 1–12 | Not started |

## Known Blockers

- Git identity not configured inside OsMEN-OC (blocks commits)
- Podman not installed (blocks Phases 4–7)
- No service accounts created yet (Telegram, Discord, Plex, Zhipu, etc.)

## Files Modified So Far

| File | Change | State |
|------|--------|-------|
| `.github/agents/osmen-install-setup.agent.md` | Rewritten with guided-install mandate | Workspace file (outside repo) |
| `OsMEN-OC/scripts/bootstrap.sh` | `sudo` → `pkexec` (4 occurrences) | Staged, not committed |

## Resumption Instructions

1. Open new workspace at `~/dev/OsMEN-OC`
2. Read this file first
3. The `osmen-install-setup` agent mode has all instructions baked in
4. Start with Phase 0 (git identity → commit pkexec patch)
5. Each phase has a pause point — stop there and confirm before proceeding
