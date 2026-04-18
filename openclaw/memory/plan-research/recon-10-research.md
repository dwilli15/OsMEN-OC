# Recon 10: Research — D's Interests + Long-term Podman Management

> Generated: 2026-04-18

---

## 1. Long-term Podman Management

**What it is:** Strategies for keeping Podman containers reproducible, updated, and free of configuration drift over time.

**Key findings:**
- **Podman auto-update** (`podman auto-update`) works with Quadlet by adding `ContainerImage=...` policy labels and enabling a systemd timer (`podman-auto-update.timer`). Images tagged with specific policies (e.g., `io.containers.autoupdate=registry`) get auto-pulled and recreated.
- **Version pinning:** Quadlet `.container` files with explicit `Image=docker.io/foo:2.21.0` prevent drift. The problem OsMEN-OC hit was likely manual podman CLI runs diverging from quadlet definitions.
- **Anti-drift:** Commit all `.container`, `.volume`, `.network`, `.kube` files to git. Use `--dry-run` before applying. Never run `podman run` outside of quadlet.
- **Quadlet reproducibility:** One `.container` file = one service. Keep all quadlets in the repo under `quadlets/`. Symlink into `~/.config/containers/systemd/`.
- **Backup:** Use `restic` or `borg` against volume paths (`~/.local/share/containers/storage/volumes/`). For critical data, mount named volumes to known paths and back those up.

| Aspect | Detail |
|---|---|
| **Feasibility** | High — native Podman features |
| **Effort** | Days (setup timers, backup scripts, git workflow) |
| **Priority** | After-stabilization |
| **Conflicts** | None — enhances current stack |

---

## 2. Komodo (github.com/moghtech/komodo)

**What it is:** A Rust/TS tool (10.7k★) for building and deploying software across many servers with a web GUI — think PaaS-lite.

**Key findings:**
- Primarily Docker-oriented. Podman support is unofficial — users report using `podman` → `docker` alias or `security_opt: label=disable` workarounds.
- Provides: server monitoring (CPU/mem/disk), web shell, build pipelines, deployment management, alerting.
- **Does NOT replace Unraid's GUI** — it's an app deployment platform, not a NAS/VM/storage manager.
- Could provide a port dashboard if configured, but that's a side effect, not its purpose.

| Aspect | Detail |
|---|---|
| **Feasibility** | Low-Medium — Podman support is hacky/unofficial |
| **Effort** | Days (setup + Podman compatibility wrestling) |
| **Priority** | Backlog |
| **Conflicts** | Podman socket compatibility issues; may need Docker compat layer |

---

## 3. Pangolin (docs.pangolin.net)

**What it is:** A tunneled reverse proxy with built-in authentication — positioned as an NGINX Proxy Manager + Tailscale alternative.

**Key findings:**
- Provides reverse proxy, tunnel (like Cloudflare Tunnel / Tailscale Funnel), and built-in SSO/auth.
- Self-hostable, Docker/Podman container available.
- Solves the "expose services securely to the internet" problem without needing a separate reverse proxy + auth layer.
- Could complement or replace Caddy/Traefik in OsMEN-OC's stack.

| Aspect | Detail |
|---|---|
| **Feasibility** | High — containerized, self-hosted |
| **Effort** | Hours to a day |
| **Priority** | After-stabilization (if D wants external access) |
| **Conflicts** | May overlap with existing reverse proxy if one exists |

---

## 4. Paperless-ngx

**What it is:** Self-hosted document management system — scan, OCR, tag, and search all your documents (37.8k★).

**Key findings:**
- Podman-compatible. Community quadlets exist (github.com/travier/paperless-ngx-quadlets).
- Multi-container setup: web app, Redis, PostgreSQL, Gotenberg (for OCR/document conversion).
- **Resource requirements:** ~2GB RAM recommended, needs Redis + PostgreSQL.
- Fits OsMEN-OC's quadlet structure well — would add 3-4 container files to `quadlets/librarian/`.
- Natural integration point: ConvertX can pre-process documents before Paperless ingestion.

| Aspect | Detail |
|---|---|
| **Feasibility** | High — well-documented Podman support |
| **Effort** | Days (multi-container quadlet setup, PostgreSQL, Redis, volume mounts) |
| **Priority** | After-stabilization |
| **Conflicts** | Needs PostgreSQL (may conflict with existing DB if ports collide) |

---

## 5. BentoPDF

**What it is:** Privacy-first, self-hosted PDF toolkit — merge, split, compress, convert PDFs (and Office files via LibreOffice).

**Key findings:**
- Official Docker/Podman deployment guide exists (bentopdf.com/docs/self-hosting/docker).
- Client-side processing by default; self-hosted version adds server-side conversion.
- Office file conversion requires LibreOffice sidecar container.
- Lightweight — good complement to Paperless-ngx or as standalone tool.
- Podman quadlet would be simple: single container + optional LibreOffice container.

| Aspect | Detail |
|---|---|
| **Feasibility** | High — explicit Podman support |
| **Effort** | Hours (simple quadlet, maybe 2 containers) |
| **Priority** | After-stabilization |
| **Conflicts** | Overlaps with ConvertX for PDF tasks — evaluate which covers more needs |

---

## 6. Audiobookshelf

**What it is:** Self-hosted audiobook and podcast server with a nice web UI.

**Current state in OsMEN-OC:**
- Quadlet exists at `quadlets/librarian/osmen-librarian-audiobookshelf.container`
- Image pinned: `docker.io/advplyr/audiobookshelf:2.21.0` ✅
- Binds to `127.0.0.1:13378` ✅ (not exposed to internet)
- Uses `osmen-core.network` ✅
- Named volumes for config and metadata ✅
- Library mounts (audiobooks, podcasts) as read-only ✅
- Health check configured ✅
- Security: `SecurityLabelDisable=true`, `NoNewPrivileges=true`, `Tmpfs=/tmp` ✅
- Resource limits: 1G memory, 100% CPU quota ✅

**Assessment:** Well-configured. Follows all best practices. No changes needed.

| Aspect | Detail |
|---|---|
| **Feasibility** | Already deployed |
| **Effort** | 0 — done |
| **Priority** | N/A |
| **Conflicts** | None |

---

## 7. Umbrel

**What it is:** A polished home server OS with app store — turnkey self-hosting platform (like Unraid but simpler, app-store focused).

**Key findings:**
- UmbrelOS is a **full OS** — installs on Raspberry Pi, mini PCs, or VMs. It is NOT an app you run on existing Ubuntu.
- Uses Docker internally. Would **conflict** with Podman-managed services if run alongside.
- More limited than Unraid (no VM management, limited storage features).
- Designed for non-technical users who want one-click apps.
- **Not suitable** for OsMEN-OC's current approach — D already has a more powerful/controlled setup.

| Aspect | Detail |
|---|---|
| **Feasibility** | Low — requires its own OS, conflicts with Podman |
| **Effort** | N/A — wrong approach for current stack |
| **Priority** | Backlog / Skip |
| **Conflicts** | **Major** — full OS replacement, Docker-based, would conflict with existing setup |

---

## 8. RyzenAI-SW (github.com/amd/RyzenAI-SW)

**What it is:** AMD's toolkit for running AI inference on Ryzen AI NPUs (801★).

**Key findings:**
- **D's hardware: AMD Ryzen AI 9 365 w/ Radeon 880M** — this **does have a Ryzen AI NPU** (XDNA architecture). ✅
- RyzenAI-SW primarily targets **Windows** (onnxruntime-ryzen package). Linux support is limited/experimental.
- The NPU is designed for lightweight inference (small models, ~13 TOPS). Not suitable for running full LLMs.
- **Ollama integration:** Ollama doesn't natively support AMD NPU. It supports AMD GPU (ROCm) for the Radeon 880M iGPU, which is more useful.
- **Lemonade integration:** No direct path. NPU is too constrained for server-side LLM workloads.

**Recommendation:** Skip RyzenAI-SW. Focus on ROCm for the Radeon 880M iGPU with Ollama instead. The NPU is better suited for on-device Windows AI features (Copilot+, background blur, etc.), not server workloads.

| Aspect | Detail |
|---|---|
| **Feasibility** | Low — Linux support limited, NPU too weak for LLMs |
| **Effort** | Weeks (with uncertain payoff) |
| **Priority** | Backlog / Skip |
| **Conflicts** | None, but overlaps with ROCm GPU compute which is more useful |

---

## 9. ConvertX Deeper Integration

**What it is:** Currently a file format converter running at `127.0.0.1:3000` for document conversion in the knowledge pipeline.

**Current state in OsMEN-OC:**
- Quadlet at `quadlets/librarian/osmen-librarian-convertx.container`
- Image: `c4illin/convertx:v0.17.0`
- Single volume for data, health check configured, security hardening applied
- Currently used for pre-ingestion document conversion

**Deeper integration opportunities:**
- **API automation:** ConvertX has REST endpoints — `POST /api/convert` for programmatic conversion. Could be called from OpenClaw agents or cron jobs.
- **Pipeline integration:** Wire ConvertX into Paperless-ngx's consumption folder so documents auto-convert before OCR.
- **Webhook triggers:** ConvertX supports conversion on upload — could watch a watched directory for new files.
- **Batch processing:** Script bulk conversions for existing document libraries.

| Aspect | Detail |
|---|---|
| **Feasibility** | High — already running, API available |
| **Effort** | Hours (API wiring, pipeline scripts) |
| **Priority** | After-stabilization |
| **Conflicts** | None — integration only |

---

## 10. Multi-agent Discord Team

**What it is:** Running multiple LLM-powered bots (Claude, OpenCode, local LLM, OpenClaw) as separate bot accounts in one Discord server.

**Key findings:**
- Each agent needs its own Discord bot token (separate application in Discord Developer Portal).
- **OpenClaw** already supports multi-agent routing — single gateway, multiple agents with different personas/models. Can route by channel or mention.
- **Claude (Anthropic):** Can be wrapped via OpenClaw or a custom bot using the Anthropic API.
- **OpenCode (Claude Code):** Can run as a Discord bot via OpenClaw ACP harness or custom integration.
- **Local LLM:** Ollama can power a Discord bot via OpenClaw (already configured in OsMEN-OC).
- **Best practices from community:** Dedicated channels per agent, allowlist routing to prevent agents from responding to each other, isolated workspaces per agent.

**Technical requirements:**
- 4 Discord bot applications (or use OpenClaw multi-agent to run multiple personas under fewer bots)
- Each agent needs its own API key/model backend
- Channel-per-agent or mention-based routing to prevent chaos
- Rate limiting to avoid burning API costs

| Aspect | Detail |
|---|---|
| **Feasibility** | High — OpenClaw multi-agent routing handles most of this |
| **Effort** | Days (bot setup, channel design, routing config) |
| **Priority** | After-stabilization |
| **Conflicts** | None — additive |

---

## Summary Priority Matrix

| Topic | Feasibility | Effort | Priority |
|---|---|---|---|
| **Podman Management** | High | Days | After-stabilization |
| **Komodo** | Low-Med | Days | Backlog |
| **Pangolin** | High | Hours | After-stabilization |
| **Paperless-ngx** | High | Days | After-stabilization |
| **BentoPDF** | High | Hours | After-stabilization |
| **Audiobookshelf** | ✅ Done | 0 | N/A |
| **Umbrel** | Low | N/A | Skip |
| **RyzenAI-SW** | Low | Weeks | Skip (use ROCm instead) |
| **ConvertX Integration** | High | Hours | After-stabilization |
| **Multi-agent Discord** | High | Days | After-stabilization |

### Recommended Next Steps (after stabilization)
1. **Podman management** — auto-update timers + backup scripts
2. **Pangolin** — evaluate as reverse proxy for external access
3. **BentoPDF** — quick win, simple quadlet
4. **ConvertX integration** — wire API into knowledge pipeline
5. **Paperless-ngx** — larger project but high value
6. **Multi-agent Discord** — fun project, high D-interest value
7. **Komodo** — reconsider if Podman support improves
