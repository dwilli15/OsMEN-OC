# OsMEN-OC Platform Handoff
**Date**: 2026-04-16 17:20 CDT
**Git**: `main` @ `2c8299c` (PR #46 merged)
**Tests**: 843 passed, 20 failed (expectation mismatches from Plex native migration — not bugs)
**Services**: 27 running, 1 failed (secrets-audit — by design, found AGE key in git history)
**TW**: 40 pending (39 original + 1 handoff), 492 completed, 40 deleted

---

## System State

### Host
- **Name**: Ubu-OsMEN
- **OS**: Ubuntu 24.10, kernel 7.0.0-14-generic, x86_64
- **CPU**: AMD Ryzen AI 9 365 (10C/20T, up to 5.1GHz)
- **GPU**: Radeon 880M (ROCm), XDNA 2 NPU
- **RAM**: 60GB (46GB available)
- **Swap**: 8GB (644MB used)

### Storage
| Drive | Size | Used | Free | Mount | FS |
|---|---|---|---|---|---|
| nvme0n1 (Samsung 954G) | 913G | 394G | 473G | `/` (LUKS→LVM) | ext4 |
| sda (WD Elements 4.5T) | 4.6T | 2.5T | 2.1T | `/run/media/dwill/plex` | ntfs3 |
| sdb (WD My Passport 1.8T) | 1.9T | 109G | 1.8T | `/run/media/dwill/TV_Anime_OFlow` | ntfs3 |
| nvme1n1p3 (SK Hynix 256G) | 256G | — | — | ❌ unmounted | NTFS (Windows) |
| nvme1n1p4 (SK Hynix 697G) | 697G | — | — | ❌ unmounted | ext4 (win_closet) |
| sdc (Samsung 870 QVO 1T) | 0B | — | — | ❌ empty | — |

**⚠️ fstab mismatch**: fstab declares `/mnt/plex` and `/mnt/tv-anime` but actual mounts at `/run/media/dwill/` via udisks2. Breaks on reboot before login.

### Media Library (2.3TB total)
| Library | Folders | Files | Size |
|---|---|---|---|
| TV (main) | 50 | 3,375 | 1.1TB |
| Movies | 333 | 348 | 847GB |
| Anime (main) | 7 | 502 | 258GB |
| TV (overflow) | 4 | 372 | 101GB |
| Anime (overflow) | 1 | 91 | 7.9GB |

### Container Services (28 running)
Gateway :18788, Plex :32400 (native), PostgreSQL :5432, Redis :6379, ChromaDB :8000, Sonarr :8989, Radarr :7878, Prowlarr :9696, qBittorrent :9090 (VPN), SABnzbd :8082 (VPN), Gluetun (VPN kill-switch ON), Tautulli :8181, Lidarr :8686, Bazarr :6767, Readarr :8787, Mylar3 :8090, Kavita :5000, Audiobookshelf :13378, Nextcloud :8080, Langflow :7860, SiYuan :6806, Whisper :9001, ConvertX :3000, Caddy :80/443, Prometheus :9091, Grafana :3002, UptimeKuma :3001, PortalL :3080

**⚠️ Kometa**: restart-looping, needs TMDB API key from themoviedb.org/settings/api

### Key Endpoints
- Gateway health: `http://127.0.0.1:18788/health`
- Gateway metrics: `http://127.0.0.1:18788/metrics`
- MCP tools (45): `http://127.0.0.1:18788/mcp/tools`
- Tautulli webhook: `http://osmen-core-gateway:8080/webhooks/tautulli`
- Tasks: `/tasks/summary`, `/tasks/pending`
- OpenClaw control: `http://127.0.0.1:18789`

### Credentials (for reference, NOT to be shared)
- Sonarr API: `1cbf2bc42cbb450181b85d59a344155e`
- Radarr API: `1ed7c7d3...`
- Plex token: `NaxyQSk5i2fnKQyctmQg`
- 15 Podman secrets managed
- No .env files — secrets at `~/.config/osmen/secrets/` (SOPS-encrypted YAML)

### Security
- ✅ SSH key-only auth (ed25519 + dandroid key)
- ✅ Docker not installed (Podman only)
- ✅ 0 failed SSH logins in 24h
- ⚠️ UFW inactive — no host firewall
- ⚠️ AGE secret key in git history

### Key Decisions (locked)
- **Plex**: Native .deb, NOT containerized (Podman 5.7.0 broke secret syntax)
- **Kometa + Tautulli**: Remain containerized
- **Podman only**: No Docker
- **No .env**: SOPS-encrypted YAML at `~/.config/osmen/secrets/`
- **Media naming**: Per-movie folders, see `docs/media/NAMING_CONVENTIONS.md`
- **Containerfile**: Build from repo root (`podman build -f core/Containerfile .`), `.dockerignore` excludes `.git`/`.venv`
- **Gateway port**: Quadlet publishes `127.0.0.1:18788:8080`
- **Memory maintenance**: Real implementation at `core/memory/maintenance.py` — no stubs
- **Orchestration**: Pool-external lifecycle (caller owns `asyncpg.Pool`)

---

## 39 Pending Tasks — Grouped by Priority

### 🔴 HIGH — Operator Action Required (4 tasks)

| ID | Task | Blocker |
|---|---|---|
| **1** | P10.6 Test Telegram send → workflow ingress → steward output | USER_ACTION: needs live Telegram test |
| **3** | P10.8 Test Discord mention-only ingress (single-bot safe mode) | USER_ACTION: needs live Discord test |
| **6** | P16.4 Configure Nextcloud admin | USER_ACTION: occ install or web UI first-run |
| **7** | P17.5 Configure Google Calendar sync policy | USER_INPUT: bidirectional vs operator-only? No calendar code exists yet |

### 🟡 MEDIUM — Manual Verification Needed (5 tasks)

| ID | Task | Notes |
|---|---|---|
| **2** | P10.7 Test Telegram receive → workflow ingress → ledger context | Code verified, needs live test |
| **4** | P10.9 Test approval flow + public/private output gating | ApprovalGate in core/approval/gate.py, needs live test |
| **37** | P8.11 Test inference routing (CUDA → Vulkan fallback) | Needs LM Studio + Ollama running simultaneously |
| **38** | P8.9 Verify LM Studio API | Needs manual `lms server start`, then curl :1234/v1/models |
| **39** | P16.4: Complete Nextcloud admin setup (occ install or web UI) | Audit finding — admin never configured |

### 🟠 LOW-MEDIUM — Conditional/Deferred (3 tasks)

| ID | Task | Notes |
|---|---|---|
| **8** | P20.4 Verify FFXIV runs on NVIDIA | Gaming: XIVLauncher installed via flatpak, Proton enabled |
| **9** | P20.5 Test GPU conflict rule | Gaming: compute-routing.yaml has GPU rules |
| **10** | P22.17 Tailscale mesh | DEPRECATED: intentionally stopped. Network mesh deferred |
| **5** | P14.5 Restore PKM data from backup | Blocked: OneDrive audit done, no pulls until user verifies |

### 🔵 LOW — Roadmap & Maintenance (27 tasks)

#### ACP / Orchestration Roadmap (8 tasks)
| ID | Task |
|---|---|
| **11** | Design external-agent ingress: VS Code Insiders / Claude Code / OpenCode / OpenClaw over orchestration workflow envelopes |
| **12** | Define cross-runtime envelope schema (identity, allowFrom, intent, payload, correlation_id, workflow_id) |
| **13** | Implement external-agent relay on top of core/bridge + core/orchestration |
| **14** | VS Code Insiders integration: expose ACP endpoint via Copilot chat extension or MCP tool |
| **15** | Claude Code integration: ACP adapter (stdin/stdout or local socket) |
| **16** | OpenCode integration: ACP adapter |
| **17** | OpenClaw integration: register external-agent ingress with trust policy + steward-only public output |
| **18** | Test external-agent handoff into Mode A/Mode B workflow |

#### DevX / Cleanup (4 tasks)
| ID | Task |
|---|---|
| **19** | Audit and clean Claude + OpenCode integrations (agents, skills, tools, MCPs, plugins) |
| **20** | Prune stale/duplicate Claude/OpenCode agent definitions and fix broken tool mappings |
| **21** | Inventory MCP servers/tools and disable orphaned endpoints |
| **22** | Review plugin set (OpenClaw/IDE) and remove unused or risky plugins |

#### OpenCode / Agent Config (3 tasks)
| ID | Task |
|---|---|
| **23** | opencode.json agent.general-purpose prompt tuning — craft ideal system prompt |
| **24** | Update opencode.json plugin list and formatter config |
| **25** | Sync lemonade-server with opencode, claude-code, and openclaw — install complete lemonade stack |

#### Maintenance (8 tasks)
| ID | Task |
|---|---|
| **26** | Create cron job to purge opencode/claude logs older than 10 days |
| **27** | SMART health check — nvme0n1 (Samsung 954G, Windows) |
| **28** | SMART health check — nvme1n1 (SK Hynix 932G, Linux) |
| **29** | SMART health check — sda (WD Elements 4.5T, plex) |
| **30** | SMART health check — sdb (WD My Passport 1.8T, TV_Anime_OFlow) |
| **31** | SMART health check — sdc (Samsung SSD 870 QVO 1T, Other_Media) |
| **32** | Encrypt Windows system drive nvme0n1 — BitLocker or VeraCrypt |
| **33** | Verify LUKS encryption on Linux system drive nvme1n1 — check key slots and backup header |

#### Misc (2 tasks)
| ID | Task |
|---|---|
| **34** | Spend $300 Google Cloud credits strategically |
| **35** | OsMEN hook integration test |
| **36** | Hook integration verify |

---

## Known Issues (non-TW)

1. **UFW firewall inactive** — no host firewall, SSH exposed on 0.0.0.0:22
2. **sdc drive 0B** — Samsung 870 QVO uninitialized, needs partitioning/formatting
3. **nvme1p3/p4 unmounted** — Windows partitions not accessible from Linux
4. **Kometa needs TMDB API key** — themoviedb.org/settings/api
5. **SiYuan returns 401** — likely needs auth token
6. **20 test expectation mismatches** — Plex native vs containerized references in tests
7. **Media symlinks fragile** — `~/media/*` → `/run/media/dwill/*` breaks on reboot before login
8. **AGE secret key in git history** — from Copilot branch merges

---

## File Locations Reference

- **Containerfile**: `core/Containerfile` (build from repo root: `podman build -f core/Containerfile .`)
- **Naming conventions**: `docs/media/NAMING_CONVENTIONS.md`
- **Transfer protocols**: `docs/media/transfer-protocols.md`
- **Media scripts**: `scripts/media/{naming,transfer,plex,maintenance,acquisition}/`
- **Gateway**: `core/gateway/app.py`
- **Orchestration**: `core/orchestration/`
- **Memory maintenance**: `core/memory/maintenance.py`
- **Agent configs**: `agents/*.yaml`
- **System config**: `config/{openclaw.yaml,compute-routing.yaml,orchestration.yaml,secrets-registry.yaml}`
- **Monitoring**: `config/grafana/{provisioning,dashboards}/`
- **Quadlets**: `quadlets/{core,media,librarian,monitoring}/*.container`
- **Timers**: `timers/*.service`, `timers/*.timer`
- **Secrets**: `~/.config/osmen/secrets/` (SOPS-encrypted)
- **OpenClaw config**: `~/.openclaw/openclaw.json`
- **Cron jobs**: `~/.openclaw/cron/jobs.json`

---

## Session History (this run)

This agent session (Jarvis) completed:
- Full system audit (services, containers, storage, networking, security)
- Fixed Containerfile COPY context (was double-nesting, gateway couldn't start)
- Fixed anyio.run() signature in memory maintenance
- Rebuilt gateway image, verified 45 MCP tools
- Merged PR #46 to main
- Synced local main to origin/main @ 2c8299c
- Created this handoff document

**Model**: `zai/glm-5-turbo`
**Runtime**: OpenClaw agent=main, host=Ubu-OsMEN
