# OpenClaw Protocols for Non-OpenClaw Agents

> **Audience:** Claude Code, Codex, Gemini, or any agent/human that needs to understand and safely modify OsMEN-OC's OpenClaw instance.
> **Last updated:** 2026-04-18

---

## 1. OpenClaw Architecture

### Config File: `~/.openclaw/openclaw.json`

This is the main config. It's JSON. Key sections:

| Section | Purpose |
|---|---|
| `gateway` | Port (18789), auth mode (token), bind (loopback), node config |
| `agents.defaults` | Default workspace, models, memory search config, subagent settings |
| `agents.list[]` | Per-agent config: id, model, skills, tools, identity |
| `cron` | Cron job engine settings (max concurrent, retries, retention) |
| `models.providers` | Model provider configs (zai, ollama, github-copilot) |
| `auth.profiles` | Auth profile definitions per provider |
| `tools` | Tool permissions (profile: "full" = all tools available) |
| `plugins.entries` | Enabled/disabled plugins (ollama, github-copilot, telegram, discord, browser, etc.) |
| `channels.telegram` | Telegram bot config |
| `channels.discord` | Discord bot config |
| `skills.entries` | Per-skill config (API keys, enabled/disabled) |
| `browser` | Browser SSRF policy |
| `diagnostics` | Diagnostic/logging settings |

**No `config.json` exists** — the file is `openclaw.json`. Backups are auto-created as `openclaw.json.bak`, `.bak.1`, etc.

### Agents

| ID | Name | Primary Model | Role |
|---|---|---|---|
| `main` | Main | github-copilot/claude-opus-4.6 | Primary agent, full tools + browser + canvas + message + gateway + nodes + tts |
| `auditor` | Install Auditor | github-copilot/gpt-5.4 | Ground-truth verification, never commits or fixes |
| `researcher` | Researcher | github-copilot/gpt-5.4 | Investigates, reads docs, reports findings, does not modify |
| `coder` | Coder | github-copilot/gpt-5.4 | Writes code, creates files, runs tests, commits |
| `reviewer` | Reviewer | github-copilot/gpt-5.4 | Code review, PR review, reports but doesn't fix |
| `basic` | Basic Worker | zai/glm-4.7-flash | Lightweight tasks, fast and cheap |

### Cron Jobs: `~/.openclaw/cron/jobs.json`

Format:
```json
{
  "version": 1,
  "jobs": [
    {
      "id": "unique-id",
      "agentId": "agent-name",
      "name": "Human-readable name",
      "enabled": true/false,
      "schedule": { "kind": "every", "everyMs": 300000 },
      "sessionTarget": "isolated" | "main",
      "wakeMode": "now",
      "payload": {
        "kind": "agentTurn",
        "message": "prompt text",
        "thinking": "low",
        "timeoutSeconds": 90,
        "lightContext": true
      },
      "delivery": { "mode": "announce", "channel": "last" },
      "state": { /* auto-managed */ }
    }
  ]
}
```

Both current jobs are **disabled** (`heckler-reviewer-300s`, `subagent-nudge`).

### Workspace: `/home/dwill/dev/OsMEN-OC/openclaw/`

| File | Role | When Loaded |
|---|---|---|
| `AGENTS.md` | Agent behavior rules: session startup, memory system, red lines, group chat behavior, heartbeat guidance | Every session (injected as project context) |
| `SOUL.md` | Persona: tone, values, boundaries, vibe | Every session |
| `USER.md` | Info about D (timezone, email, notes) | Every session |
| `IDENTITY.md` | Agent self-identification metadata | Every session |
| `MEMORY.md` | **Long-term curated memory** — distilled from daily notes | **Main/private sessions ONLY** (security) |
| `HEARTBEAT.md` | Checklist for periodic heartbeat checks | Heartbeat polls |
| `TOOLS.md` | Local environment-specific notes (cameras, SSH hosts, etc.) | Every session |

### Memory System

- **`memory/YYYY-MM-DD.md`** — Daily raw notes. Created by the agent during each session to log what happened.
- **`memory/*.md`** — Various handoff docs, audit reports, plan docs, etc.
- **`memory/plan-research/`** — Research and planning documents.
- **`MEMORY.md`** (workspace root) — Curated long-term memory. Only loaded in main/private sessions.

Memory search is enabled via Ollama (`nomic-embed-text` embeddings). The `memory_search` tool indexes all `memory/*.md` and `MEMORY.md`.

### Local Skills

Two custom skills exist beyond the bundled ones:
- `skills/osmen-tts/` — Kokoro TTS via Lemonade Server (localhost:13305)
- `skills/osmen-image-gen/` — SD-Turbo image generation via Lemonade sd-cpp server

---

## 2. How to Edit OpenClaw Config

### PROTECTED Paths (must edit JSON directly)

These paths **cannot** be patched via `openclaw gateway config.patch`:
- `exec.security` — exec security mode
- `exec.ask` — exec approval mode

Edit them by directly modifying `~/.openclaw/openclaw.json`, then restart.

### Safe Paths (can use config.patch)

Most other paths can be patched:
```bash
openclaw gateway config.patch '{"channels.telegram.status":"online"}'
```

### Restarting

```bash
openclaw gateway restart
```

### Validation Caveats

- Config must be valid JSON — OpenClaw won't start on malformed JSON
- Auto-backups are created before changes (`.bak`, `.bak.1`, etc.)
- Some changes take effect immediately; others need a restart
- Model/provider changes may require gateway restart to take full effect

---

## 3. How to Edit Workspace Files

### MEMORY.md
- Long-term curated memory, distilled from daily notes
- **Security rule:** Only load in main/private sessions (direct chat with D)
- Do NOT load in shared contexts (Discord, group chats)
- Can be read, edited, and updated freely in main sessions

### memory/YYYY-MM-DD.md
- Daily raw notes — log what happened, decisions made, context
- Create new files as needed (no limit)
- These are the "raw journal" vs MEMORY.md being the "curated wisdom"

### HEARTBEAT.md
- Short checklist for periodic heartbeat checks
- Keep small to limit token burn
- Agent reads this during heartbeat polls and acts on it

### How Changes Are Picked Up

Workspace files (AGENTS.md, SOUL.md, USER.md, etc.) are **injected at session start** as project context. Changes take effect on the **next session** — not mid-session. The agent re-reads `memory/` files explicitly when needed.

---

## 4. TaskWarrior Integration

### Config: `~/.taskrc`

```ini
data.location=~/.task
confirmation=off
verbose=blank,header,footnote,label,new-id,affected,edit,special,project,sync,unwait,recur
```

Custom UDAs:
- `energy` (string): high/medium/low — task effort level
- `interaction` (string): PKEXEC, USER_DECISION, USER_INPUT, INTERACTIVE, USER_ACTION, SHARED_SYSTEM, autonomous
- `caldav_uid` (string): CalDAV sync ID

Custom report: `next` — shows id, age, deps, priority, project, tags, recurrence, scheduled, due, until, description, urgency.

### How TW Is Used

- Primary task tracking for OsMEN-OC installation/setup phases
- Project structure uses `osmen.*` prefix (e.g., `osmen.install`)
- Tasks tagged by phase (e.g., `install`, `phase`)
- The auditor agent reads TW state to verify installation progress
- Energy and interaction UDAs help classify task difficulty and autonomy level

---

## 5. Container Management Protocol

### Quadlet Files: `~/.config/containers/systemd/`

All containers use **Podman Quadlet** (systemd unit generator). File types:
- `.container` — Container definition
- `.volume` — Named volume
- `.network` — Network definition
- `.pod` — Pod definition
- `.service` — Service wrapper (for non-quadlet things like LM Studio)
- `.slice` — Resource grouping (`user-osmen-core.slice`, `user-osmen-media.slice`, etc.)

### Naming Convention

`osmen-{tier}-{name}` where tier is:
- `core` — Essential infrastructure (PostgreSQL, Redis, ChromaDB, Gateway, Caddy, Langflow, Miniflux, Paperless, Siyuan)
- `media` — Media stack (Plex, Sonarr, Radarr, Lidarr, Readarr, Prowlarr, qBittorrent, SABnzbd, Bazarr, Kometa, Komga, Mylar3, Tautulli)
- `dashboard` — Dashboards (Homepage)
- `monitoring` — Monitoring (Grafana, Prometheus, UptimeKuma, Portall)
- `tools` — Utilities (BentoPDF)
- `inference` — AI inference (LM Studio)
- `librarian` — Library services (Audiobookshelf, ConvertX, Whisper, Kavita)

### How to Add/Modify Containers

```bash
# 1. Edit or create the quadlet file
vim ~/.config/containers/systemd/osmen-{tier}-{name}.container

# 2. Reload systemd to regenerate the transient unit
systemctl --user daemon-reload

# 3. Restart the service
systemctl --user restart osmen-{tier}-{name}

# 4. Verify
systemctl --user status osmen-{tier}-{name}
podman ps | grep {name}
```

Disabled containers have `.disabled` suffix — rename to enable.

### Network Topology

| Network | Subnet | Purpose |
|---|---|---|
| `osmen-core` | 10.89.0.0/24 | Internal-only bridge for core services. No LAN exposure. PostgreSQL, Redis, ChromaDB, Gateway, etc. |
| `osmen-media` | 10.89.1.0/24 | Media services bridge. Plex, *arr stack, download pod. |

### Pod Structure: `download-stack.pod`

- **Pod:** `download-stack` — shared network namespace
- **Members:** `osmen-media-gluetun` (VPN provider), `osmen-media-qbittorrent`, `osmen-media-sabnzbd`, `osmen-media-prowlarr`
- **Network:** Connected to `osmen-media.network` so arr services can reach download clients
- **VPN:** All external traffic from pod members goes through Gluetun's WireGuard tunnel
- **Ports:** 9090 (qBittorrent), 8082 (SABnzbd web), 9696 (Prowlarr), 8888 (Gluetun HTTP proxy) — all localhost-only

### Systemd Slices

Resource grouping:
- `user-osmen-core.slice` — Core infrastructure
- `user-osmen-media.slice` — Media stack
- `user-osmen-dashboard.slice` — Dashboards
- `user-osmen-inference.slice` — AI inference
- `user-osmen-services.slice` — Services
- `user-osmen-background.slice` — Background tasks

---

## 6. Git Workflow

### Repo: `/home/dwill/dev/OsMEN-OC/`

Single branch: `main`. Remote at `origin/main`.

### What Gets Committed

- Quadlet files (symlinked or copied from `~/.config/containers/systemd/`)
- OpenClaw workspace files (AGENTS.md, SOUL.md, USER.md, memory/, etc.)
- Scripts and documentation
- Handoff/state documents in `memory/`

### Commit Style

Recent commits show descriptive prefixes: `session3 handoff:`, `session3 final:`, `stabilization:`.

---

## 7. Known Gotchas

### Podman Secrets: ALWAYS use `echo -n`
```bash
# CORRECT — no trailing newline
echo -n "my-secret-value" | podman secret create my-secret -

# WRONG — includes trailing newline
echo "my-secret-value" | podman secret create my-secret -
```
This causes silent auth failures that are extremely hard to debug.

### Gluetun DNS Doesn't Resolve Container Names
Containers inside the download-stack pod share Gluetun's network namespace. Gluetun's DNS only resolves public names. To reach other containers:
- Use IP addresses directly (e.g., `10.89.1.x`)
- Don't use container names as hostnames in arr service configs

### Prowlarr IP Fragility
Prowlarr's IP address can change on container recreation. If arr services can't reach Prowlarr, check the current IP and update configs accordingly.

### ReadOnly=true Needs Tmpfs=/tmp
When a container is set `ReadOnly=true` in the quadlet file, any process that needs to write to `/tmp` will fail. Add:
```ini
Tmpfs=/tmp
```

### SABnzbd Regenerates API Key on Container Recreation
SABnzbd generates a new API key every time the container is recreated. Any service configured with SABnzbd's API key (e.g., Sonarr, Radarr) will need to be updated after recreation. The key is in `~/.config/sabnzbd/sabnzbd.ini` inside the config volume.

### qBittorrent PBKDF2 Hash Generation
qBittorrent uses PBKDF2 hashing for its Web API password. To generate the hash:
```bash
# Install qBittorrent-nox or use Python
python3 -c "
import hashlib
password = 'your-password'
salt = b'qBittorrent'  # or whatever the configured salt is
iterations = 100000
hash_val = hashlib.pbkdf2_hmac('sha512', password.encode(), salt, iterations)
print(hash_val.hex())
"
```
The hash goes in `qBittorrent/config/qBittorrent.conf` as `WebUI\\Password_PBKDF2_SHA512`.

---

## Quick Reference Commands

```bash
# OpenClaw
openclaw gateway status
openclaw gateway restart
openclaw gateway config.patch '{"key":"value"}'

# Containers
systemctl --user daemon-reload
systemctl --user restart osmen-{tier}-{name}
systemctl --user status osmen-{tier}-{name}
podman ps
podman logs osmen-{tier}-{name}

# TaskWarrior
task next
task list project:osmen.install
task add "description" project:osmen.install +phase

# Git
cd /home/dwill/dev/OsMEN-OC
git add -A && git commit -m "description" && git push
```
