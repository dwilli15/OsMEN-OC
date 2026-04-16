# OsMEN-OC First Install Plan — Comprehensive Multi-Phase Checklist
# Generated: 2026-04-07 | Branch: install/fresh-setup-20260407
# System: Ubuntu 26.04 (Resolute Raccoon), Python 3.13.12, Ryzen AI 9 365

# ═══════════════════════════════════════════════════════════════════════
# PHASE 0: Repository & Git Identity
# Prereq: None | Output: Clean branch ready for commits
# ═══════════════════════════════════════════════════════════════════════

## 0.1 Configure git identity
- Command: `git config user.name "<name>"` + `git config user.email "<email>"`
- Needs: User to provide name and email
- Verify: `git config user.name && git config user.email`

## 0.2 Stage and commit pre-install fixes
- Files to commit:
  - `scripts/bootstrap.sh` (pkexec patch + python3.13 binary fix)
  - `Makefile` (python3.13 venv + gateway port 8080)
  - `.gitignore` (temp_1st_install/ added)
  - `migrations/001_initial_schema.sql` (initial DB schema)
- Command: `git add -A && git commit -m "fix: pre-install corrections (python3.13, port conflict, schema)"`
- Verify: `git log --oneline -1` and `git status --short` shows clean

## 0.3 Verify branch state
- Command: `git log --oneline -5`
- Expected: install branch ahead of main by commit(s)

### PAUSE POINT 0 — Confirm branch is clean before system changes

# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: System Dependencies (apt)
# Prereq: Phase 0 | Output: All system packages installed
# Elevation: pkexec required
# ═══════════════════════════════════════════════════════════════════════

## 1.1 Update apt cache
- Command: `pkexec apt-get update -qq`
- Note: Will prompt PolicyKit GUI dialog

## 1.2 Install required system packages
- Command:
  ```
  pkexec apt-get install -y --no-install-recommends \
    python3-dev python3-venv \
    nodejs npm \
    podman podman-compose \
    taskwarrior \
    lm-sensors smartmontools \
    restic age \
    ffmpeg \
    git curl jq
  ```
- Already installed (skip): python3.13, git
- Verify each:
  - `podman --version`
  - `task --version`
  - `sensors --version`
  - `smartctl --version`
  - `restic version`
  - `age --version`
  - `ffmpeg -version | head -1`
  - `node --version && npm --version`
  - `jq --version`

## 1.3 Check for python3.13-venv module
- Already verified: python3.13 -m venv works
- If broken: `pkexec apt-get install -y python3.13-venv`

### PAUSE POINT 1 — All apt packages verified before userland tools

# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: Userland Tools (non-apt)
# Prereq: Phase 1 (npm for openclaw) | Output: sops + openclaw ready
# ═══════════════════════════════════════════════════════════════════════

## 2.1 Install sops
- Check if published: `apt-cache show sops 2>/dev/null`
- If not in apt: download binary from GitHub releases to ~/.local/bin/
  ```
  curl -Lo ~/.local/bin/sops https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64
  chmod +x ~/.local/bin/sops
  ```
- Verify: `sops --version`

## 2.2 Install OpenClaw
- Command: `npm install -g openclaw`
- Note: May not be published yet — if so, skip and defer
- Verify: `openclaw --version` (or mark deferred)

## 2.3 Verify PATH
- Check: `echo $PATH | tr ':' '\n' | grep -E '\.local/bin|\.npm'`
- If ~/.local/bin not in PATH, add to ~/.bashrc:
  `export PATH="$HOME/.local/bin:$PATH"`

### PAUSE POINT 2 — CLI tools ready before Python environment

# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: Python Environment
# Prereq: Phase 1 (python3-dev) | Output: .venv with all deps
# ═══════════════════════════════════════════════════════════════════════

## 3.1 Create .venv with Python 3.13
- Command: `python3.13 -m venv .venv`
- Verify: `.venv/bin/python --version` outputs 3.13.x

## 3.2 Bootstrap pip
- Command: `.venv/bin/python -m pip install --upgrade pip`
- Fallback if ensurepip missing: `pkexec apt-get install -y python3-pip`

## 3.3 Install OsMEN-OC (editable + dev extras)
- Command: `.venv/bin/python -m pip install -e ".[dev]"`
- Installs: fastapi, uvicorn, pydantic, pyyaml, loguru, httpx, anyio, cronsim,
            websockets, pytest, ruff, mypy, pytest-cov, types-PyYAML

## 3.4 Verify core import
- Command: `.venv/bin/python -c "import core; print(core.__version__)"`
- Expected: `0.1.0`

## 3.5 Run test suite
- Command: `.venv/bin/python -m pytest tests/ -q --timeout=15`
- Expected: All pass (stubs count as pass)
- If failures: diagnose and fix before proceeding

## 3.6 Run linter
- Command: `.venv/bin/python -m ruff check core/ tests/`
- Expected: Clean (0 violations)

## 3.7 Run type checker
- Command: `.venv/bin/python -m mypy core/ --ignore-missing-imports`
- Expected: Clean or only expected warnings from optional deps

## 3.8 Commit any fixes from test/lint/typecheck
- If changes needed: fix, test, commit on install branch

### PAUSE POINT 3 — Dev environment fully green

# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: Rootless Podman
# Prereq: Phase 1 (podman package) | Output: Rootless podman functional
# Elevation: pkexec for subuid/subgid only
# ═══════════════════════════════════════════════════════════════════════

## 4.1 Verify subuid/subgid
- Check: `grep "^$(whoami):" /etc/subuid /etc/subgid`
- If missing:
  ```
  pkexec usermod --add-subuids 100000-165535 "$(whoami)"
  pkexec usermod --add-subgids 100000-165535 "$(whoami)"
  ```

## 4.2 Enable podman socket
- Command: `systemctl --user enable --now podman.socket`
- Verify: `systemctl --user is-active podman.socket`

## 4.3 Verify rootless podman
- Command: `podman info --format '{{.Host.Security.Rootless}}'`
- Expected: `true`

## 4.4 Test container execution
- Command: `podman run --rm docker.io/library/alpine:3.20 echo "Podman works"`
- Expected: Prints "Podman works", exits 0
- Clean up: `podman image rm docker.io/library/alpine:3.20`

## 4.5 Verify cgroup v2
- Command: `stat -fc %T /sys/fs/cgroup` → expected: `cgroup2fs`
- Also: `podman info --format '{{.Host.CgroupVersion}}'` → expected: `v2`

### PAUSE POINT 4 — Podman rootless confirmed before deploying services

# ═══════════════════════════════════════════════════════════════════════
# PHASE 5: Quadlet Deployment (Units Only — Not Started)
# Prereq: Phase 4 | Output: Quadlet units registered in systemd
# ═══════════════════════════════════════════════════════════════════════

## 5.1 Create target directories
- Commands:
  ```
  mkdir -p ~/.config/containers/systemd
  mkdir -p ~/.config/systemd/user
  ```

## 5.2 Deploy quadlet files (dry-run first)
- Command: `scripts/deploy_quadlets.sh --dry-run`
- Review: Inspect symlinks that would be created
- Then: `scripts/deploy_quadlets.sh` (live)

## 5.3 Reload systemd
- Command: `systemctl --user daemon-reload`

## 5.4 Verify units registered
- Command: `systemctl --user list-unit-files | grep osmen`
- Expected units:
  - osmen-core-postgres.service
  - osmen-core-redis.service
  - osmen-core-chromadb.service
  - osmen-core.network (handled by podman)
  - user-osmen-core.slice

## 5.5 DO NOT START yet — secrets needed first

### PAUSE POINT 5 — Units registered, services NOT started

# ═══════════════════════════════════════════════════════════════════════
# PHASE 6: Secrets & Credentials
# Prereq: Phase 5 | Output: Podman secrets created
# Interactive: User provides or auto-generates passwords
# ═══════════════════════════════════════════════════════════════════════

## 6.1 Generate or collect credentials
- Decide: auto-generate random passwords or user-provided
- Required Podman secrets (5):
  1. `osmen-postgres-password` — PostgreSQL superuser password
  2. `osmen-postgres-user` — PostgreSQL username (default: `osmen`)
  3. `osmen-postgres-db` — PostgreSQL database name (default: `osmen`)
  4. `osmen-redis-password` — Redis AUTH password
  5. `osmen-chromadb-token` — ChromaDB auth credential

## 6.2 Create Podman secrets
- For each secret:
  ```
  echo -n "<value>" | podman secret create osmen-<name> -
  ```
- Example (auto-gen):
  ```
  openssl rand -base64 32 | podman secret create osmen-postgres-password -
  echo -n "osmen" | podman secret create osmen-postgres-user -
  echo -n "osmen" | podman secret create osmen-postgres-db -
  openssl rand -base64 32 | podman secret create osmen-redis-password -
  openssl rand -base64 32 | podman secret create osmen-chromadb-token -
  ```

## 6.3 Verify secrets
- Command: `podman secret ls`
- Expected: 5 secrets with `osmen-` prefix

## 6.4 (Optional) Set up SOPS + age
- Generate age key: `age-keygen -o ~/.config/sops/age/keys.txt`
- Create `.sops.yaml` in repo root pointing to public key
- Encrypt secret configs: `sops --encrypt --age <pubkey> config/secrets/api-keys.yaml`
- This can be deferred — Podman secrets are sufficient for core services

### PAUSE POINT 6 — Secrets in place, ready to start services

# ═══════════════════════════════════════════════════════════════════════
# PHASE 7: Core Services Startup
# Prereq: Phase 6 | Output: PostgreSQL, Redis, ChromaDB running & healthy
# ═══════════════════════════════════════════════════════════════════════

## 7.1 Pull container images (bandwidth-intensive)
- Commands:
  ```
  podman pull docker.io/pgvector/pgvector:pg17
  podman pull docker.io/library/redis:7.2.5-alpine
  podman pull docker.io/chromadb/chroma:0.5.23
  ```
- Verify: `podman images | grep -E 'pgvector|redis|chroma'`

## 7.2 Start services
- Command: `systemctl --user start osmen-core-postgres osmen-core-redis osmen-core-chromadb`
- Or individually for debugging:
  ```
  systemctl --user start osmen-core-postgres
  systemctl --user start osmen-core-redis
  systemctl --user start osmen-core-chromadb
  ```

## 7.3 Wait for health (up to 90s)
- Command: `watch -n5 'podman ps --format "table {{.Names}}\t{{.Status}}"'`
- Expected: All three show "healthy"
- Debug: `systemctl --user status osmen-core-<service>`
- Logs: `journalctl --user -u osmen-core-<service> --no-pager -n 50`

## 7.4 Verify connectivity
- PostgreSQL: `podman exec osmen-core-postgres pg_isready -U osmen -d osmen`
- Redis: `podman exec osmen-core-redis redis-cli -a "$(podman secret inspect osmen-redis-password --showsecret 2>/dev/null || echo '<password>')" ping`
- ChromaDB: `curl -sf http://127.0.0.1:8000/api/v1/heartbeat`

## 7.5 Run SQL migrations
- Command:
  ```
  podman exec -i osmen-core-postgres \
    psql -U osmen -d osmen < migrations/001_initial_schema.sql
  ```
- Verify: `podman exec osmen-core-postgres psql -U osmen -d osmen -c '\dt'`
- Expected tables: audit_trail, audit_archive, schema_version

## 7.6 Verify data persistence
- Restart PG: `systemctl --user restart osmen-core-postgres`
- Wait for healthy, then: `podman exec osmen-core-postgres psql -U osmen -d osmen -c 'SELECT * FROM schema_version;'`
- Expected: Row with version=1 survives restart

### PAUSE POINT 7 — Core data services running and healthy

# ═══════════════════════════════════════════════════════════════════════
# PHASE 8: Timers
# Prereq: Phase 7 (services running) | Output: Backup timers active
# ═══════════════════════════════════════════════════════════════════════

## 8.1 Deploy timer units (dry-run first)
- Command: `scripts/deploy_timers.sh --dry-run`
- Review output
- Then: `scripts/deploy_timers.sh` (live)

## 8.2 Reload and enable
- Command: `systemctl --user daemon-reload`
- Timers are auto-enabled by deploy_timers.sh

## 8.3 Verify timers
- Command: `systemctl --user list-timers --all | grep osmen`
- Expected: osmen-db-backup.timer active, next trigger ~02:30

## 8.4 Note: backup timer needs restic repo
- Restic backup repo must be initialized before first timer fire
- Command (when ready):
  ```
  restic init --repo <backup-location>
  ```
- Can be deferred — timer will warn but not crash

### PAUSE POINT 8 — Timers scheduled

# ═══════════════════════════════════════════════════════════════════════
# PHASE 9: Setup Wizard (Interactive Config)
# Prereq: Phase 7 (services verify DSNs) | Output: ~/.config/osmen/env
# Interactive: User provides API keys, tokens, paths
# ═══════════════════════════════════════════════════════════════════════

## 9.1 Prepare accounts BEFORE running wizard
- Items to gather (user does these manually in browser):

### 9.1a: Zhipu GLM API Key
- URL: https://open.bigmodel.cn
- Sign up → get API key from dashboard
- Note: Base URL is `https://api.z.ai/api/coding/paas/v4`
- Error code 1302 = rate limit → 2 min backoff

### 9.1b: Telegram Bot
- Open Telegram, message @BotFather
- `/newbot` → choose name → get token
- Add bot to target group/channel → get chat ID
- Verify: `curl https://api.telegram.org/bot<TOKEN>/getMe`

### 9.1c: Discord Bot (optional)
- URL: https://discord.com/developers/applications
- New Application → Bot tab → get token
- OAuth2 → generate invite URL with bot+applications.commands scopes
- Invite to server → get Guild ID (enable Developer Mode in Discord settings)

### 9.1d: Plex paths (optional, defer if not ready)
- Decide: where will Plex libraries live? (e.g., `/home/dwill/media/plex`)
- Decide: download staging? (e.g., `/home/dwill/media/staging`)

## 9.2 Run wizard
- Command: `.venv/bin/python -m core.setup`
- The wizard prompts for each field with defaults
- Writes: `~/.config/osmen/env` (chmod 600)
- Writes: `config/openclaw.yaml` (safe to commit)
- Creates: `~/.config/osmen/.setup_complete`

## 9.3 Verify env file
- Command: `cat ~/.config/osmen/env` (review, ensure no blank required fields)
- Check permissions: `stat -c '%a' ~/.config/osmen/env` → expected: `600`

## 9.4 Verify openclaw.yaml
- Command: `cat config/openclaw.yaml`
- Should contain `${ENV_VAR}` references (resolved at runtime by config.py)

## 9.5 Verify DSNs match running services
- postgres_dsn should point to 127.0.0.1:5432 with osmen/osmen creds
- redis_url should point to 127.0.0.1:6379
- If mismatch: re-run `python -m core.setup --reconfigure`

### PAUSE POINT 9 — Configuration complete, gateway should be startable

# ═══════════════════════════════════════════════════════════════════════
# PHASE 10: Gateway Validation
# Prereq: Phase 9 | Output: OsMEN-OC gateway running, endpoints verified
# ═══════════════════════════════════════════════════════════════════════

## 10.1 Source env file
- Command: `set -a && source ~/.config/osmen/env && set +a`

## 10.2 Start gateway
- Command: `make dev`
- Or directly: `.venv/bin/python -m uvicorn core.gateway.app:app --reload --host 127.0.0.1 --port 8080`
- Expected: Uvicorn starts, logs show agent manifest loading

## 10.3 Health check
- Command (new terminal): `curl -s http://127.0.0.1:8080/health | python3 -m json.tool`
- Expected: `{"status": "ok", ...}`

## 10.4 MCP tools listing
- Command: `curl -s http://127.0.0.1:8080/mcp/tools | python3 -m json.tool`
- Expected: 32 tools from 8 agents listed

## 10.5 Readiness check
- Command: `curl -s http://127.0.0.1:8080/ready | python3 -m json.tool`
- Shows which dependencies are connected (redis, pg, chromadb)

## 10.6 Event bus verification
- Check gateway logs for: "EventBus connected" or "EventBus: noop fallback"
- If noop: redis connection issue — check REDIS_URL and password

## 10.7 Bridge status
- Check logs for: "OpenClaw bridge connecting to ws://127.0.0.1:18789"
- Expected to fail if OpenClaw isn't running yet — this is OK
- Bridge will auto-reconnect with exponential backoff

## 10.8 Stop gateway (Ctrl+C)
- Cleanup for next phase

### PAUSE POINT 10 — Core OsMEN-OC platform verified

# ═══════════════════════════════════════════════════════════════════════
# PHASE 11: Extended Service Integration
# Prereq: Phase 10 | Output: Additional services wired and verified
# Each sub-phase is independent — user chooses order and which to do
# ═══════════════════════════════════════════════════════════════════════

## 11a: Database Schema Verification (already done in 7.5)
- Verify: tables exist, data persists across restart
- Test: gateway can query audit_trail (via /ready endpoint)
- Duration: ~5 min

## 11b: Telegram Bridge
- Prereq: Bot token + chat ID from Phase 9
- Test send: `curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage?chat_id=${TELEGRAM_CHAT_ID}&text=OsMEN-OC+online"`
- Start gateway, verify approval notifications route to Telegram
- Test: trigger a medium-risk tool, confirm notification appears
- Duration: ~15 min

## 11c: Discord Bridge (optional)
- Prereq: Bot token + guild ID from Phase 9
- Invite bot to server (if not done)
- Start gateway, verify bot appears online in Discord
- Test: send message from OsMEN-OC → Discord channel
- Duration: ~15 min

## 11d: Taskwarrior
- Install: already done in Phase 1 (`task` command)
- Configure: `task config data.location ~/.task` (or custom)
- Create test: `task add "OsMEN-OC test task" project:osmen`
- Verify via gateway: call sync_tasks handler
- Google Calendar sync: deferred until GOOGLE_CALENDAR_CREDENTIALS_PATH set
- Duration: ~10 min

## 11e: Plex Media Server
- Install options: flatpak, snap, or Podman container
- Configure library paths (match PLEX_LIBRARY_ROOT from wizard)
- Browser: claim server at https://app.plex.tv/desktop
- Wire: OsMEN-OC media_organization agent
- Test: library scan via Plex, media visible
- Duration: ~30 min (depends on library size)

## 11f: Siyuan Notes
- Install: AppImage or Podman
- Configure: API token, workspace path
- Wire: knowledge_librarian agent memory bridge
- Test: create and retrieve note via OsMEN-OC
- Duration: ~20 min

## 11g: Nextcloud
- Deploy: Podman container (or external instance)
- Configure: admin account, storage, CalDAV/CardDAV endpoints
- Wire: taskwarrior sync, file sync, calendar bridge
- Test: file upload/download, calendar event creation
- Duration: ~45 min

## 11h: Prowlarr (Indexer Manager)
- Deploy: Podman container
- Configure: indexers, API key
- Wire: to download clients + OsMEN-OC
- Test: search returns results
- Duration: ~20 min

## 11i: Book/Comic/Audiobook Servers
- Choose: Kavita, Komga, Audiobookshelf, Calibre-Web
- Deploy: Podman container(s)
- Configure: libraries, user accounts
- Wire: knowledge_librarian agent
- Test: content browsable
- Duration: ~30 min per server

## 11j: TTS/STT/Transcription
- Choose: Piper TTS (local), Whisper STT (local)
- Install: download models to ~/.local/share/osmen/models/
- Wire: voice pipeline in core
- Test: text→speech and speech→text roundtrip
- Duration: ~30 min

## 11k: Privado VPN
- Install: Privado client (or gluetun container for VPN pod)
- Configure: credentials, server selection
- Wire: media_organization VPN audit tool
- Test: IP changes, download stack routes through VPN
- Note: VPN pod architecture (gluetun + qBittorrent + SABnzbd) is Phase 11+
- Duration: ~30 min

## 11l: Port & Resource Audit
- Audit all ports: `ss -tlnp | grep LISTEN`
- Document in config/ports.yaml or similar
- Check for conflicts
- Review cgroup limits in user-osmen-core.slice
- Duration: ~10 min

### PAUSE POINT 11 — Extended services installed per user choice

# ═══════════════════════════════════════════════════════════════════════
# PHASE 12: Final Verification & Repo Cleanup
# Prereq: All desired phases complete | Output: PR-ready branch
# ═══════════════════════════════════════════════════════════════════════

## 12.1 Full test suite
- Command: `make check` (runs test + lint + typecheck)
- All must pass

## 12.2 Service health
- Command: `make status`
- All Podman containers healthy
- OpenClaw version (or "not installed" if deferred)
- Python venv OK

## 12.3 End-to-end bridge test
- Start gateway: `make dev`
- If OpenClaw installed: verify WebSocket handshake
- If Telegram configured: send test notification
- If Discord configured: verify bot online

## 12.4 Clean up temp_1st_install/
- Decision: archive to docs/ or delete
- If archive: `mv temp_1st_install/ docs/first_install_log_20260407/`
- If delete: `rm -rf temp_1st_install/`

## 12.5 Final commit
- Stage all changes: `git add -A`
- Commit: `git commit -m "feat: first install complete — all systems operational"`
- Verify: `git log --oneline` shows logical commit history

## 12.6 Push and create PR
- Command: `git push -u origin install/fresh-setup-20260407`
- Create PR against main via GitHub
- PR description: summarize all phases completed, services running, deferred items

## 12.7 File issues for deferred items
- Create GitHub issues for anything skipped:
  - OpenClaw (if npm package not published)
  - Google Calendar sync
  - VPN pod architecture
  - Any extended services not installed
  - Test stubs that need real implementations

### INSTALL COMPLETE ✓
