# OsMEN-OC Master State of Play

**Generated:** 2026-04-18 21:06 CDT (post-restart)
**Purpose:** Complete handoff for a non-OpenClaw agent/team to continue OsMEN-OC setup
**Host:** Ubu-OsMEN | Linux 7.0.0-14-generic (x64) | 65.3GB RAM | AMD Ryzen
**User:** D (d.osmen.oc@gmail.com) — newbie/vibe-coder, prefers GUI admin
**Agent:** OpenClaw (Opus 4.6) — primary AI interface via Telegram, Discord, webchat

---

# TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Container & Service State](#2-container--service-state)
3. [TaskWarrior State](#3-taskwarrior-state)
4. [Filesystem Map](#4-filesystem-map)
5. [OpenClaw Architecture & Edit Protocols](#5-openclaw-architecture--edit-protocols)
6. [Container Management Protocol](#6-container-management-protocol)
7. [Credentials](#7-credentials)
8. [Known Issues & Gotchas](#8-known-issues--gotchas)
9. [What Needs D](#9-what-needs-d)
10. [Detailed Source Data Files](#10-detailed-source-data-files)

---

# 1. EXECUTIVE SUMMARY

OsMEN-OC is a personal operating system / life management platform built on Ubuntu 26 + Podman. After 72 hours of agent-driven setup (Apr 16-18), the infrastructure is largely deployed and healthy.

**Current state:**
- **31 containers running**, 29 healthy, 2 in auto-restart (Plex, Kometa)
- **67 pending TW tasks** across 20 projects
- **~150+ tasks completed** in the last 72h across 3 sessions
- **Key services:** PostgreSQL, Redis, Caddy, full *arr stack, Komga (comics+manga), monitoring, Paperless, Miniflux, BentoPDF
- **Removed this session:** Nextcloud (no use case), Kavita (consolidated into Komga)
- **Remaining work:** UFW firewall, volume cleanup (125GB), Homepage widgets, media pipeline fixes, ACP roadmap, DevX cleanup

**What's left is ~40% of the total vision:** security hardening, media pipeline completion, agent/team tooling, and polish tasks.

---

# 2. CONTAINER & SERVICE STATE

## Running Containers (31)

| Container | Image | Host Port | Status | Memory |
|-----------|-------|-----------|--------|--------|
| osmen-core-postgres | pgvector/pgvector:pg17 | 127.0.0.1:5432 | healthy | 85 MB |
| osmen-core-redis | redis:7.2.5-alpine | 127.0.0.1:6379 | healthy | 13 MB |
| osmen-core-caddy | caddy:2.9-alpine | 0.0.0.0:80, 0.0.0.0:443 | healthy | 48 MB |
| osmen-core-chromadb | chromadb/chroma:0.5.23 | 127.0.0.1:8000 | healthy | 153 MB |
| osmen-core-langflow | langflowai/langflow:1.3.1 | 127.0.0.1:7860 | healthy | 1.19 GB |
| osmen-core-siyuan | b3log/siyuan:v3.6.4 | 127.0.0.1:6806 | healthy | 32 MB |
| osmen-core-miniflux | miniflux/miniflux:latest | 127.0.0.1:8180 | healthy | 38 MB |
| osmen-core-paperless | paperless-ngx:latest | 127.0.0.1:8010 | healthy | 638 MB |
| osmen-core-gateway | localhost/osmen-gateway:dev | 127.0.0.1:18788 | healthy | 74 MB |
| osmen-media-gluetun | qmcgaw/gluetun:v3.40.2 | (pod) | healthy | 137 MB |
| osmen-media-sabnzbd | linuxserver/sabnzbd:4.5.1 | 127.0.0.1:8082 | healthy | 101 MB |
| osmen-media-qbittorrent | linuxserver/qbittorrent:5.1.0 | 127.0.0.1:9090 | healthy | 61 MB |
| osmen-media-prowlarr | linuxserver/prowlarr:1.35.1 | 127.0.0.1:9696 | healthy | 177 MB |
| osmen-media-sonarr | linuxserver/sonarr:4.0.14 | 127.0.0.1:8989 | healthy | 272 MB |
| osmen-media-radarr | linuxserver/radarr:5.21.1 | 127.0.0.1:7878 | healthy | 189 MB |
| osmen-media-lidarr | linuxserver/lidarr:3.1.0 | 127.0.0.1:8686 | healthy | 213 MB |
| osmen-media-readarr | linuxserver/readarr:0.4.12-nightly | 127.0.0.1:8787 | healthy | 181 MB |
| osmen-media-bazarr | linuxserver/bazarr:1.5.2 | 127.0.0.1:6767 | healthy | 233 MB |
| osmen-media-mylar3 | linuxserver/mylar3:0.8.1 | 127.0.0.1:8090 | healthy | 98 MB |
| osmen-media-komga-comics | gotson/komga:1.24.3 | 127.0.0.1:25600 | healthy | 1.18 GB |
| osmen-media-tautulli | tautulli/tautulli:v2.17.0 | 127.0.0.1:8181 | healthy | 67 MB |
| osmen-media-plex | plexinc/pms-docker | 127.0.0.1:32400 | ⚠️ auto-restart | — |
| osmen-media-kometa | kometateam/kometa:v2.3.1 | — | ⚠️ auto-restart | — |
| osmen-librarian-audiobookshelf | advplyr/audiobookshelf:2.21.0 | 127.0.0.1:13378 | healthy | 48 MB |
| osmen-librarian-convertx | c4illin/convertx:v0.17.0 | 127.0.0.1:3000 | healthy | 26 MB |
| osmen-librarian-whisper | fedirz/faster-whisper-server:0.6.0 | 127.0.0.1:9001 | healthy | 116 MB |
| osmen-monitoring-grafana | grafana/grafana-oss:12.1.0 | 127.0.0.1:3002 | healthy | 102 MB |
| osmen-monitoring-prometheus | prom/prometheus:v3.4.0 | 127.0.0.1:9091 | healthy | 31 MB |
| osmen-monitoring-uptimekuma | louislam/uptime-kuma:1.23.16 | 127.0.0.1:3001 | healthy | 111 MB |
| osmen-monitoring-portall | need4swede/portall:2.0.4 | 127.0.0.1:3080 | healthy | 59 MB |
| osmen-dashboard-homepage | gethomepage/homepage:latest | 127.0.0.1:3010 | healthy | 162 MB |
| osmen-tools-bentopdf | alam00000/bentopdf:latest | 127.0.0.1:3020 | healthy | 10 MB |

**Disabled containers:** osmen-core-nextcloud.container.disabled, osmen-librarian-kavita.container.disabled

**Total RAM:** ~5.4 GB across all containers. Host has 65.3 GB.

## Services in Restart Loop
- **osmen-media-plex** — Plex Media Server, native install may conflict with container
- **osmen-media-kometa** — Plex metadata manager, depends on Plex

## Network Topology
| Network | Subnet | Members |
|---------|--------|---------|
| osmen-core | 10.89.0.0/24 | PostgreSQL, Redis, Caddy, ChromaDB, Gateway, Langflow, SiYuan, Miniflux, Paperless, Homepage |
| osmen-media | 10.89.1.0/24 | All media containers, download-stack pod, librarian, monitoring, Komga, Tautulli, Plex |

## Download Stack Pod
- **Pod:** `download-stack` — shared network namespace, all traffic through Gluetun VPN
- **Members:** gluetun, SABnzbd, qBittorrent, Prowlarr
- **VPN:** Privado Amsterdam via WireGuard
- **Ports:** 8082 (SAB), 9090 (qBit), 9696 (Prowlarr), 8888 (Gluetun proxy) — all localhost-only

---

# 3. TASKWARRIOR STATE

## Config
- **Taskwarrior data:** `~/.task/`
- **Config:** `~/.taskrc`
- **Hooks:** `/home/dwill/dev/OsMEN-OC/scripts/taskwarrior/` (on-add, on-modify)
- **Custom UDAs:** `energy` (high/medium/low), `interaction` (USER_ACTION/autonomous/etc.), `caldav_uid`

## Pending Tasks: 67 across 20 projects

### By Priority
| Priority | Count | Key Tasks |
|----------|-------|-----------|
| H | 4 | T0.3 UFW firewall, P10.6 Telegram bridge test, P10.8 Discord test, P17.5 Calendar policy |
| M | 17 | Volume cleanup, SABnzbd move, media pipeline fixes, Komga manga setup, backups, security |
| L | 25 | ACP roadmap, DevX cleanup, SMART checks, encryption, PKM, cloud drive evaluation |
| None | 21 | Homepage widget chain, media pipeline backlog, handoff, credits |

### By Project (top 10)
| Project | Pending | Nature |
|---------|---------|--------|
| osmen.media.pipeline | 14 | Manga/comics fixes, Prowlarr, corrupt files, library organization |
| osmen.maint | 12 | UFW, volumes, SMART, encryption, backups, security |
| osmen.roadmap.acp | 9 | External agent ingress design (all unblocked, low priority) |
| osmen.dashboard.homepage | 8 | Homepage widget config chain (P23.1-P23.8) |
| osmen.install.p10 | 4 | Bridge tests (need D to send messages) |
| osmen.roadmap.devx | 4 | Claude/OpenCode/MCP cleanup |
| osmen.configure | 3 | OpenCode, Lemonade, plugin review |
| osmen.install.p17 | 2 | Calendar (needs D decision) |
| osmen.install.p20 | 2 | FFXIV/GPU |
| osmen.install.p8 | 2 | LM Studio, CUDA fallback |

### Completed (last 72h): ~150+
Key completions:
- **T0.1–T0.9:** Full quadlet stabilization (merge conflicts, slices, ReadOnly, image pinning, PUID/PGID, daemon-reload)
- **T1.1–T1.3:** PostgreSQL, Redis, Caddy deployed
- **T2.2:** SABnzbd wizard fixed + Eweka Usenet connected
- **T3.1–T3.4:** Full *arr stack + gluetun firewall fix
- **T4.1–T4.2:** Librarian + monitoring stack
- **T5.1–T5.2:** Nextcloud (since removed), SiYuan, Langflow, ChromaDB
- **T7.1, T7.5, T7.6:** Paperless-ngx, BentoPDF, Miniflux
- **~60 media tasks:** DC comics download pipeline (3,800 CBZ, 1,253 series), manga acquisition

**Full TW dump:** See `memory/handoff-data/tw-state.md`

---

# 4. FILESYSTEM MAP

## Repo: `/home/dwill/dev/OsMEN-OC/`
Single `main` branch. Remote: `origin/main`.

### Key Directories
| Path | Purpose |
|------|---------|
| `/home/dwill/dev/OsMEN-OC/quadlets/` | **Source of truth** for all container definitions |
| `/home/dwill/dev/OsMEN-OC/quadlets/core/` | PostgreSQL, Redis, Caddy, ChromaDB, Langflow, SiYuan, Miniflux, Paperless, Gateway |
| `/home/dwill/dev/OsMEN-OC/quadlets/media/` | Plex, *arr stack, download stack, Komga, Kometa, Tautulli, Mylar3 |
| `/home/dwill/dev/OsMEN-OC/quadlets/librarian/` | Audiobookshelf, ConvertX, Whisper, (Kavita disabled) |
| `/home/dwill/dev/OsMEN-OC/quadlets/monitoring/` | Grafana, Prometheus, UptimeKuma, Portall |
| `/home/dwill/dev/OsMEN-OC/quadlets/dashboard/` | Homepage |
| `/home/dwill/dev/OsMEN-OC/quadlets/tools/` | BentoPDF |
| `/home/dwill/dev/OsMEN-OC/quadlets/volumes/` | Volume definitions |
| `/home/dwill/dev/OsMEN-OC/quadlets/slices/` | Systemd slice definitions |
| `/home/dwill/dev/OsMEN-OC/openclaw/` | **OpenClaw workspace** (see Section 5) |
| `/home/dwill/dev/OsMEN-OC/scripts/` | Utility scripts (bootstrap, backup, deploy, manga download, TW hooks) |
| `/home/dwill/dev/OsMEN-OC/core/` | OsMEN-OC application code (orchestration, bridge, etc.) |
| `/home/dwill/dev/OsMEN-OC/docs/` | Documentation, plans, media docs |

### Systemd Quadlet Directory
`~/.config/containers/systemd/` — all files are **symlinks** to `/home/dwill/dev/OsMEN-OC/quadlets/`
- 31 active `.container` files
- 2 disabled (`.container.disabled`) — Nextcloud, Kavita
- 1 `.pod` (download-stack)
- 2 `.network` (osmen-core, osmen-media)
- 35 `.volume` definitions
- 6 `.slice` definitions

### Media Paths
| Symlink | Target | Drive | Usage |
|---------|--------|-------|-------|
| `~/media/plex` | `/mnt/plex` | WD Elements 4.5TB (NTFS) | 56% used |
| `~/media/other-media` | `/mnt/other-media` | Samsung 870 QVO 1TB (NTFS) | 75% used |
| `~/media/tv-anime` | `/mnt/tv-anime` | WD My Passport 1.8TB (NTFS) | 6% used |
| `~/media/comics` | `/mnt/other-media/Comics` | (same as other-media) | DC: 3,800 CBZ, 1,253 series |
| `~/media/manga` | `/mnt/other-media/Manga` | (same as other-media) | 144 series, Komga scanning |
| `~/media/manga-downloads` | `/mnt/other-media/Manga` | (same as other-media) | (duplicate symlink) |

### OpenClaw Workspace: `/home/dwill/dev/OsMEN-OC/openclaw/`
| File | Purpose |
|------|---------|
| `AGENTS.md` | Agent behavior rules (session startup, memory, red lines) |
| `SOUL.md` | Persona definition |
| `USER.md` | User profile (D) |
| `IDENTITY.md` | Agent identity |
| `MEMORY.md` | Long-term curated memory (**main sessions only** for security) |
| `HEARTBEAT.md` | Periodic heartbeat checklist |
| `TOOLS.md` | Local environment notes |
| `memory/` | Daily logs, handoff docs, audit reports, plan docs |
| `memory/plan-research/` | 10 recon reports, architecture reviews, user input |
| `basic/`, `coder/`, `researcher/`, `reviewer/`, `auditor/` | Sub-agent workspaces |

### Key Memory/Handoff Files
| File | Size | Purpose |
|------|------|---------|
| `memory/osmen-master-plan-2026-04-18.md` | 78K | Master plan with all 101 tasks |
| `memory/osmen-handoff-2026-04-18-session3-audit.md` | 12K | Last session handoff + 72h audit briefing |
| `memory/audit-2026-04-18-72h.md` | 7K | 72h audit results |
| `memory/2026-04-17.md` | 28K | Biggest daily log (comics/manga pipeline) |
| `memory/2026-04-18.md` | 7K | Latest daily log |

### Scripts: `/home/dwill/dev/OsMEN-OC/scripts/`
- `bootstrap.sh`, `backup.sh`, `deploy_quadlets.sh`, `deploy_timers.sh`
- `manga_downloader.py`, `manga_bulk_v2.py` through `v4.py`, `manga_postprocess.py`
- `taskwarrior/on-add-osmen.py`, `taskwarrior/on-modify-osmen.py`
- `secrets/export_credential_kit.sh`
- `lemonade-autoload.sh`, `resource_audit.sh`

**Full filesystem inventory:** See `memory/handoff-data/filesystem-inventory.md`

---

# 5. OPENCLAW ARCHITECTURE & EDIT PROTOCOLS

## Config
- **File:** `~/.openclaw/openclaw.json` (NOT `config.json`)
- **Backups:** Auto-created as `openclaw.json.bak`, `.bak.1`, etc.
- **Restart:** `openclaw gateway restart`
- **Status:** `openclaw gateway status`

### Agents
| ID | Model | Role |
|----|-------|------|
| main | github-copilot/claude-opus-4.6 | Primary agent, all tools |
| auditor | github-copilot/gpt-5.4 | Verification, never modifies |
| researcher | github-copilot/gpt-5.4 | Investigates, reports findings |
| coder | github-copilot/gpt-5.4 | Writes code, commits |
| reviewer | github-copilot/gpt-5.4 | Reviews, doesn't fix |
| basic | zai/glm-4.7-flash | Lightweight tasks, cheap |

### Cron Jobs: `~/.openclaw/cron/jobs.json`
- `heckler-reviewer-300s` — **DISABLED** (was $33.60/72h)
- `subagent-nudge` — **DISABLED** (no active sub-agents)

### PROTECTED Config Paths (CANNOT use config.patch)
- `exec.security`
- `exec.ask`
- **Must edit `~/.openclaw/openclaw.json` directly**, then restart

### Safe Config Patching
```bash
openclaw gateway config.patch '{"channels.telegram.status":"online"}'
```

### How to Edit Workspace Files
- All workspace files (`AGENTS.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, etc.) are **plain markdown**
- Changes take effect on the **next session** (files are injected at session start)
- `MEMORY.md` — **only load in main/private sessions** (contains personal context)
- `memory/YYYY-MM-DD.md` — daily raw notes, agent creates these each session
- `HEARTBEAT.md` — periodic check tasks, keep small to limit token burn

### How to Add/Modify Cron Jobs
Edit `~/.openclaw/cron/jobs.json` directly. Format:
```json
{
  "id": "unique-id",
  "agentId": "main",
  "name": "Job Name",
  "enabled": true,
  "schedule": { "kind": "every", "everyMs": 300000 },
  "sessionTarget": "isolated",
  "payload": { "kind": "agentTurn", "message": "prompt", "thinking": "low" },
  "delivery": { "mode": "announce", "channel": "last" }
}
```

### Channels
- **Telegram** — primary chat interface
- **Discord** — secondary, group chat capability
- **Webchat** — Control UI at `http://localhost:18789`

**Full protocol doc:** See `memory/handoff-data/openclaw-protocols.md`

---

# 6. CONTAINER MANAGEMENT PROTOCOL

### How to Add/Modify a Container
```bash
# 1. Create/edit the quadlet file in the REPO
vim /home/dwill/dev/OsMEN-OC/quadlets/{tier}/osmen-{tier}-{name}.container

# 2. Create symlink in systemd dir (if not already there)
ln -sf /home/dwill/dev/OsMEN-OC/quadlets/{tier}/osmen-{tier}-{name}.container \
       ~/.config/containers/systemd/

# 3. Reload + restart
systemctl --user daemon-reload
systemctl --user restart osmen-{tier}-{name}

# 4. Verify
systemctl --user status osmen-{tier}-{name}
podman ps | grep {name}
```

### How to Disable a Container
```bash
systemctl --user stop osmen-{tier}-{name}
mv ~/.config/containers/systemd/osmen-{tier}-{name}.container{,.disabled}
systemctl --user daemon-reload
```

### How to Create a Podman Secret
```bash
# CRITICAL: Always use echo -n (no trailing newline!)
echo -n "secret-value" | podman secret create my-secret-name -
```

### Quadlet File Format (.container)
```ini
[Container]
ContainerName=osmen-{tier}-{name}
Image=docker.io/namespace/image:tag
Volume=/host/path:/container/path:ro
Network=osmen-{tier}.network
Environment=KEY=value
Secret=my-secret,type=env,target=ENV_VAR
PublishPort=127.0.0.1:hostport:containerport
HealthCmd=curl -sf http://localhost:port/ || exit 1
HealthInterval=30s
HealthRetries=3
HealthStartPeriod=30s
Label=io.containers.autoupdate=registry

[Service]
Restart=always
Slice=user-osmen-{tier}.slice
```

### Naming Convention
`osmen-{tier}-{name}` where tier = core | media | dashboard | monitoring | tools | inference | librarian

---

# 7. CREDENTIALS

| Service | User | Password/Key | Notes |
|---------|------|-------------|-------|
| Komga | d.osmen.oc@gmail.com | Oc!8533!Oc | Comics + manga reader |
| qBittorrent | osmen | Oc!833!Oc | Auth may be broken (5.1.0 bug) |
| Miniflux | osmen | Oc!833!Oc! | RSS reader |
| Paperless | osmen | Oc!833!Oc! | Document management |
| PostgreSQL | osmen | (podman secret) | DB user |
| Redis | — | 8887ee14...b2c16 | Hex password (podman secret) |
| SABnzbd | — | API: b69fd362889549ff9dffd8cddbb983ea | Regenerates on container recreate |
| Prowlarr | — | API: 0a7c9db5fe024343af5a1dafaf09aad6 | Indexer manager |
| Mylar3 | osmen | osmen | Default |
| Nextcloud | — | — | **REMOVED** |
| Kavita | — | — | **REMOVED** (consolidated into Komga) |

---

# 8. KNOWN ISSUES & GOTCHAS

### Critical
1. **T0.3 UFW Firewall** — iptables wide open, UFW inactive. Needs sudo. **Highest priority security item.**
2. **Prowlarr IP Fragility** — All arr app-sync URLs use hardcoded IPs (gluetun DNS doesn't resolve container names). Any arr container restart breaks sync. Fix: pin container IPs or use Caddy proxy.
3. **qBittorrent Auth** — Login broken on 5.1.0. PBKDF2 hash doesn't stick. May need downgrade to v4.x.
4. **AGE-SECRET-KEY in Git History** — Secrets audit service found a secret key in git commits. Investigate + rotate if needed.

### Important
5. **Plex + Kometa in restart loop** — Both services auto-restarting post-reboot. Plex is a native install that may conflict with container.
6. **ReadOnly without Tmpfs** — 9 containers have `ReadOnly=true` but no `Tmpfs=/tmp`. Currently fine but will break on restart if apps write to /tmp. Affected: Caddy, Plex, Tautulli, Kometa, Grafana, Portall, Prometheus, UptimeKuma, Gateway.
7. **Komga high CPU** — 112% CPU post-restart, likely still scanning 1,170+ manga series. Should settle.
8. **chromadb-compact timer** — Inline Python has IndentationError. Won't run until fixed.

### Media Pipeline
9. **70 corrupt files** in manga library — 64 CBR (bad RAR headers), 3 PDF, 2 CBZ, 1 junk. Mostly Batman Eternal issues from incomplete Usenet downloads.
10. **DC comics in manga folder** — `/manga/Yen Press (unsorted)/` contains Batman Eternal issues that belong in the comics library.
11. **SABnzbd API key regeneration** — Key changes every time container is recreated. Update all consumers.

### Operational
12. **Podman secrets trailing newline** — Always use `echo -n` when creating secrets. Silent auth failures otherwise.
13. **Gluetun DNS** — VPN pod DNS (198.18.0.1) only resolves public names. Use IPs for inter-container communication within the pod.
14. **Volume bloat** — 125.3GB reclaimable from duplicate/orphaned volumes. SABnzbd config volume alone is 125GB on root NVMe.
15. **Port mapping differences** — Prometheus is :9091 (not 9092), Portall is :3080 (not 3003), Whisper is :9001 (not 9000), ConvertX is :3000 (not 3100).

### Git
16. **5 unpushed commits** — All stabilization work from Apr 18 needs a push.
17. **3 uncommitted changes** — Working tree not clean.

---

# 9. WHAT NEEDS D

These tasks are blocked on D's input, approval, or physical action:

| Task | Why Blocked | Priority |
|------|------------|----------|
| T0.3 UFW Firewall | Needs sudo/elevated permissions | H |
| P10.6-P10.9 Bridge Tests | D must send live Telegram/Discord messages | H |
| P17.5 Calendar Sync Policy | D must decide: bidirectional vs read-only | H |
| T6.2 Volume Cleanup (125GB) | D must approve deletion | M |
| T6.3 SABnzbd Move (125GB) | D must confirm target drive | M |
| P14.5 PKM Restore | D said no pulls until verified | L |
| Komga manga library org | Low urgency, can be done anytime | M |
| Plex restart loop | May need D to check native install conflict | M |

---

# 10. DETAILED SOURCE DATA FILES

The sub-agents produced 4 detailed data files in `memory/handoff-data/`:

| File | Size | Contents |
|------|------|----------|
| `memory/handoff-data/tw-state.md` | ~15K | Full TW dump: 67 pending tasks, ~150 completed, projects, tags, priorities |
| `memory/handoff-data/filesystem-inventory.md` | ~24K | Every file path, symlink, volume, script, config on the system |
| `memory/handoff-data/service-state.md` | ~8K | Live container state, health, resource usage, port connectivity, systemd |
| `memory/handoff-data/openclaw-protocols.md` | ~12K | Detailed OpenClaw config, edit procedures, container protocol, gotchas |

### Prior Handoff Documents (chronological)
| File | Session | Key Content |
|------|---------|-------------|
| `memory/osmen-handoff-2026-04-16.md` | Day 1 | Initial recon + media library work |
| `memory/osmen-handoff-2026-04-17.md` | Day 2 | Comics/manga pipeline |
| `memory/osmen-handoff-2026-04-18-session2.md` | Session 2 (02:00-05:20) | 10-agent recon sweep, Tiers 0-5 |
| `memory/osmen-handoff-2026-04-18-session3-audit.md` | Session 3 (06:00-19:38) | Prowlarr wiring, Tier 7, 72h audit |
| **THIS DOCUMENT** | Session 3 (20:00+) | **Post-restart consolidation** |

---

# QUICK REFERENCE

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
task add "description" project:osmen.maint priority:M

# Git
cd /home/dwill/dev/OsMEN-OC
git add -A && git commit -m "description" && git push

# Quadlet edits
vim /home/dwill/dev/OsMEN-OC/quadlets/{tier}/osmen-{tier}-{name}.container
systemctl --user daemon-reload
systemctl --user restart osmen-{tier}-{name}
```
