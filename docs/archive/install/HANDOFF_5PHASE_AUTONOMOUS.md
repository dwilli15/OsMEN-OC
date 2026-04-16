# Autonomous 5-Phase Handoff — P8 (finish) → P9 → P10 → P11 → P12

**Created**: 2026-04-12T20:10 CDT | **Revised**: 2026-04-12T21:00 CDT  
**For**: Outside agent (z_final_install mode)  
**Branch**: `install/fresh-setup-20260407`  
**Repo**: `/home/dwill/dev/OsMEN-OC/`  
**Last commit**: `c1598c7` Phase 8: Inference stack  
**Source of truth**: Taskwarrior (`project:osmen.install`)  
**Install plan**: `/home/dwill/dev/OsMEN-OC/temp_1st_install/INSTALL_PLAN.md`  

## Execution Model

These are the next 5 phases from the Taskwarrior megaplan in dependency order.
Work each phase sequentially (P8→P9→P10→P11→P12). Each phase has exit gates.
Do NOT stop for user input — execute all autonomous (priority L/M) tasks, collect
all USER_INPUT / USER_ACTION / USER_DECISION / INTERACTIVE blockers, and continue
to the next phase. At the end, produce ONE handoff listing all blockers.

**Taskwarrior is law.** Every step maps to a TW task. Use `task {id} start` before
work and `task {id} done` after. Do not invent steps — execute what's in TW.

---

## System State (verified 2026-04-12)

| Component | Version | Status | Path/Endpoint |
|-----------|---------|--------|---------------|
| Lemonade Server | 10.2.0 | systemd active, User=lemonade | `/usr/bin/lemond` → `http://127.0.0.1:13305` |
| FastFlowLM | 0.9.38 | `/usr/bin/flm` | NPU validated: 8 columns, FW 1.1.2.64, memlock ∞ |
| Ollama | 0.20.3 | native systemd (`ollama.service`) | `http://127.0.0.1:11434` |
| LM Studio | headless | `~/.lmstudio/bin/lms` | `http://127.0.0.1:1234` (fallback only) |
| PostgreSQL 17 | Podman | port 5432 | `osmen-core-postgres` |
| Redis 7 | Podman | port 6379 | `osmen-core-redis` |
| ChromaDB | Podman | port 8000 | `osmen-core-chromadb` |
| Python venv | 3.14.4 | `/home/dwill/dev/.venv/` |
| NVIDIA driver | 595.58.03 | CUDA 13.2 (driver) |
| NPU memlock | ∞ | `/etc/security/limits.d/99-npu-memlock.conf` + systemd drop-in |
| OpenClaw | 2026.4.10 | systemd user service | Node 24, ws://127.0.0.1:18789 |

### Lemonade Backends: llamacpp:vulkan (b8668), llamacpp:cpu (b8668), llamacpp:system, flm:npu (v0.9.38), kokoro:cpu (b16), whispercpp:cpu (v1.8.2)

### Models Pulled
- **Lemonade**: Qwen3-Coder-30B-A3B-Instruct-GGUF (17.3G), Qwen3.5-4B-GGUF (3.3G), qwen3.5-4b-FLM (4.8G NPU+vision)
- **Ollama**: gemma4:latest (9.6G), llama3.2:3b (2.0G), qwen3.5:2b (2.7G), nomic-embed-text (274M)
- **FLM NPU live test**: Qwen3.5-4B → 12.77 tok/s decode, 984ms TTFT

### NPU Model Catalog (34 models available via `flm list`)
Qwen3.5 (0.8B–9B w/ vision), Qwen3 (0.6B–8B), DeepSeek-R1 (8B), LLaMA3 (1B–8B), Gemma3 (1B–4B), MedGemma, gpt-oss (20B MoE), LFM2/2.5, Phi4-mini, Whisper-v3-turbo, EmbeddingGemma-300M

---

## Phase P8 (finish) — 1 task remaining

**TW query**: `task project:osmen.install.p8 status:pending list`
**Exit gate**: Ollama and Lemonade expose expected APIs and models

| TW ID | Step | Priority | Tags | Description |
|-------|------|----------|------|-------------|
| 2 | P8.5a | L | install phase8 | Install Open WebUI (optional, manual-launch) |

### P8.5a Details (from INSTALL_PLAN.md)
```
- Command: podman pull ghcr.io/open-webui/open-webui:main
- DO NOT auto-start — zero resources unless explicitly opened
- Launch manually: podman run --rm -p 3080:8080 \
    -e OLLAMA_BASE_URL=http://127.0.0.1:11434 \
    -e OPENAI_API_BASE_URL=http://127.0.0.1:13305/api/v1 \
    -e OPENAI_API_KEY=lemonade \
    ghcr.io/open-webui/open-webui:main
- No quadlet — manual-only per canonical spec
- Port 3080 (not 8080 — gateway owns 8080)
```

### Artifacts
- No files to create — this is a container pull + verify-only step

---

## Phase P9 — Setup Wizard + Gateway Validation (15 tasks)

**TW query**: `task project:osmen.install.p9 status:pending list`
**Prereq**: P7+P8 complete
**Exit gate**: Wizard writes env, gateway starts, MCP tools enumerate
**Rollback**: Re-run wizard and overwrite generated local config files only

| TW ID | Step | Priority | Tags | Description |
|-------|------|----------|------|-------------|
| 3 | P9.1 | H | USER_INPUT | Gather ZAI API key |
| 4 | P9.2 | H | USER_ACTION | Gather Telegram bot token |
| 5 | P9.3 | H | USER_ACTION | Gather Telegram chat ID |
| 6 | P9.4 | H | USER_INPUT | Gather Discord bot token (conditional) |
| 7 | P9.5 | H | USER_INPUT | Gather Discord guild ID (conditional) |
| 8 | P9.6 | H | USER_DECISION | Gather Plex library root |
| 9 | P9.7 | H | USER_DECISION | Gather download staging dir |
| 10 | P9.8 | H | USER_INPUT | Gather Google Calendar creds (conditional) |
| 11 | P9.9 | H | INTERACTIVE | Run setup wizard |
| 12 | P9.10 | M | verify | Verify env file permissions |
| 13 | P9.11 | M | verify | Verify DSNs match running services |
| 14 | P9.12 | L | | Start gateway |
| 15 | P9.13 | M | verify | Health check |
| 16 | P9.14 | M | verify | MCP tools listing |
| 17 | P9.15 | M | verify | Verify event bus + bridge status |

### Autonomous work (do these first)
1. **P9.12** — Start gateway:
   ```bash
   source ~/.config/osmen/env 2>/dev/null  # may not exist yet
   cd /home/dwill/dev/OsMEN-OC
   source /home/dwill/dev/.venv/bin/activate
   python -m uvicorn core.gateway.app:app --reload --host 127.0.0.1 --port 8080
   ```
   If env file doesn't exist, the wizard (P9.9) creates it → BLOCKER.

2. **P9.10** — `stat -c '%a' ~/.config/osmen/env` → expect `600`
3. **P9.11** — Verify DSNs: postgres=127.0.0.1:5432, redis=127.0.0.1:6379, chromadb=127.0.0.1:8000
4. **P9.13** — `curl -s http://127.0.0.1:8080/health | python3 -m json.tool`
5. **P9.14** — `curl -s http://127.0.0.1:8080/mcp/tools | python3 -m json.tool` → expect 32+ tools
6. **P9.15** — Check logs for "EventBus connected"

### Blockers to collect (all P9.1–P9.9)
These are all USER_INPUT / USER_ACTION / USER_DECISION / INTERACTIVE. Record each
as a blocker with:
- What's needed (API key, token, path, etc.)
- URL to obtain it
- Default value if applicable (P9.6 default: `/home/dwill/media/plex`, P9.7 default: `/home/dwill/downloads`)

### Key artifacts
- `/home/dwill/dev/OsMEN-OC/core/setup/wizard.py` — setup wizard source
- `/home/dwill/dev/OsMEN-OC/core/setup/__main__.py` — wizard entry point
- `/home/dwill/dev/OsMEN-OC/core/gateway/app.py` — FastAPI gateway
- `/home/dwill/dev/OsMEN-OC/core/gateway/mcp.py` — MCP tools registration
- `~/.config/osmen/env` — generated env file (chmod 600)

---

## Phase P10 — OpenClaw + Messaging Bridges (7 tasks remaining)

**TW query**: `task project:osmen.install.p10 status:pending list`
**Prereq**: P9 complete
**Exit gate**: Bridges exchange messages and approval flow is exercised
**Rollback**: Disable bridge services and clear only local connector config
**Already done**: P10.1 (Node.js v24 ✓), P10.2 (OpenClaw installed ✓), P10.3 (configured ✓), P10.4 (service running ✓)

| TW ID | Step | Priority | Tags | Description |
|-------|------|----------|------|-------------|
| 18 | P10.2a | L | | Restore or install openclaw-keyring |
| 19 | P10.5 | M | verify | Verify WebSocket bridge |
| 20 | P10.6 | H | USER_ACTION | Test Telegram send |
| 21 | P10.7 | M | verify | Test Telegram receive |
| 22 | P10.8 | H | USER_ACTION | Test Discord bot (conditional) |
| 23 | P10.9 | M | verify | Test approval flow |
| 24 | P10.10 | L | | Commit OpenClaw config |

### Autonomous work
1. **P10.2a** — Restore `openclaw-keyring`:
   - Check backup: `ls ~/.local/bin/openclaw-keyring`
   - If missing: create shim that reads from `~/.config/osmen/env`
   - Verify: `~/.local/bin/openclaw-keyring --version` or test credential retrieval

2. **P10.5** — Verify WebSocket bridge:
   - Start gateway, check logs for "OpenClaw bridge connected"
   - If OpenClaw not running: bridge auto-reconnects with backoff — OK, note in report

3. **P10.7** — Test Telegram receive:
   - Requires P10.6 (USER_ACTION) to complete first → depends on blocker resolution
   - If tokens available from P9: send message TO bot, verify gateway logs show incoming

4. **P10.9** — Test approval flow:
   - Trigger medium-risk tool → verify notification in Telegram → approve → verify execution
   - Depends on Telegram being wired (P10.6/P10.7)

5. **P10.10** — `cd /home/dwill/dev/OsMEN-OC && git add config/openclaw.yaml && git commit -m "P10: OpenClaw config"`

### Blockers to collect
- P10.6: Needs TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID from P9
- P10.8: Discord currently not functional (annotation on TW task: "Discord currently not functional for operator use")
- P10.9: Depends on P10.6/P10.7

### Key artifacts
- `/home/dwill/dev/OsMEN-OC/config/openclaw.yaml` — OpenClaw config
- `/home/dwill/dev/OsMEN-OC/core/bridge/ws_client.py` — WebSocket bridge
- `/home/dwill/dev/OsMEN-OC/core/bridge/protocol.py` — Bridge protocol

---

## Phase P11 — VPN + Download Stack Pod (16 tasks)

**TW query**: `task project:osmen.install.p11 status:pending list`
**Prereq**: P7 (core services)
**Exit gate**: gluetun owns pod namespace and leak checks pass
**Rollback**: Tear down pod and recreate only download-stack units
**Architecture**: Single Podman pod, shared gluetun network namespace

| TW ID | Step | Priority | Tags | Description |
|-------|------|----------|------|-------------|
| 25 | P11.1 | L | | Pull gluetun image |
| 26 | P11.2 | L | | Pull qBittorrent image |
| 27 | P11.3 | L | | Pull SABnzbd image |
| 28 | P11.4 | L | | Write download-stack.pod quadlet |
| 29 | P11.5 | L | | Write osmen-media-gluetun.container quadlet |
| 30 | P11.6 | L | | Write osmen-media-qbittorrent.container quadlet |
| 31 | P11.7 | L | | Write osmen-media-sabnzbd.container quadlet |
| 32 | P11.8 | H | USER_INPUT pitfall | Configure VPN credentials |
| 33 | P11.9 | L | | Create download directories |
| 34 | P11.10 | L | | Start gluetun |
| 35 | P11.11 | M | verify pitfall | Verify VPN IP (not home IP) |
| 36 | P11.12 | M | verify pitfall | Verify DNS (no leak) |
| 37 | P11.13 | M | verify pitfall | Verify IPv6 disabled |
| 38 | P11.14 | L | | Start qBittorrent |
| 39 | P11.15 | L | | Start SABnzbd |
| 40 | P11.16 | M | verify pitfall | Verify download stack survives reboot |

### Autonomous work
1. **P11.1–P11.3** — Pull images:
   ```bash
   podman pull docker.io/qmcgaw/gluetun:latest
   podman pull docker.io/linuxserver/qbittorrent:latest
   podman pull docker.io/linuxserver/sabnzbd:latest
   ```

2. **P11.4** — Write `quadlets/media/download-stack.pod`:
   - Ports: 9090 (qBit WebUI), 8082 (SABnzbd WebUI)
   - All containers share gluetun's network namespace

3. **P11.5** — Write `quadlets/media/osmen-media-gluetun.container`:
   - Image: qmcgaw/gluetun
   - Pod: download-stack
   - Env: VPN_SERVICE_PROVIDER=privado, VPN_TYPE=wireguard
   - Secrets: VPN private key via Podman secret
   - Health: `curl ifconfig.me` (IP must differ from home IP)

4. **P11.6** — Write `quadlets/media/osmen-media-qbittorrent.container`:
   - Image: linuxserver/qbittorrent
   - Pod: download-stack (shares gluetun network)
   - Volume: osmen-qbit-config, ~/downloads/
   - Depends: After=osmen-media-gluetun.service

5. **P11.7** — Write `quadlets/media/osmen-media-sabnzbd.container`:
   - Image: linuxserver/sabnzbd
   - Pod: download-stack
   - Volume: osmen-sab-config, ~/downloads/
   - Depends: After=osmen-media-gluetun.service

6. **P11.9** — `mkdir -p ~/downloads/{pending,active,complete,torrents}`

7. **P11.10, P11.14, P11.15** — Start services (BLOCKED on P11.8 VPN creds):
   ```bash
   systemctl --user start download-stack
   systemctl --user start osmen-media-qbittorrent osmen-media-sabnzbd
   ```

8. **P11.11–P11.13** — VPN leak checks (BLOCKED on P11.10):
   ```bash
   podman exec osmen-media-gluetun curl -s ifconfig.me    # Must be VPN IP
   podman exec osmen-media-gluetun cat /etc/resolv.conf   # No ISP DNS
   podman exec osmen-media-gluetun curl -6 ifconfig.me    # Must FAIL (PF05)
   ```

9. **P11.16** — Enable and reboot-test:
   ```bash
   systemctl --user enable download-stack osmen-media-gluetun osmen-media-qbittorrent osmen-media-sabnzbd
   ```

### Blockers to collect
- **P11.8**: USER_INPUT — Privado WireGuard config (private key). Write env to
  `~/.config/containers/systemd/osmen-media-gluetun.env` (chmod 0600). Pitfall PF06: NOT in git.
- P11.10–P11.16 all depend on P11.8 being resolved

### Pitfalls in this phase
- PF04: DNS leak — verify resolv.conf in gluetun
- PF05: IPv6 leak — curl -6 must FAIL
- PF06: VPN creds in git — verify .gitignore + SOPS
- PF07: VPN restart recovery — verify auto-start after reboot
- PF08: Port forwarding for seeding — check gluetun API

### Key artifacts to create
- `/home/dwill/dev/OsMEN-OC/quadlets/media/download-stack.pod`
- `/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-gluetun.container`
- `/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-qbittorrent.container`
- `/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-sabnzbd.container`

---

## Phase P12 — Arr Stack (12 tasks)

**TW query**: `task project:osmen.install.p12 status:pending list`
**Prereq**: P11 (download clients reachable via VPN pod)
**Exit gate**: Prowlarr, Sonarr, Radarr, and Bazarr are cross-wired
**Rollback**: Stop arr services and reapply only service-specific API config

| TW ID | Step | Priority | Tags | Description |
|-------|------|----------|------|-------------|
| 41 | P12.1 | L | | Pull Prowlarr image |
| 42 | P12.2 | L | | Pull Sonarr image |
| 43 | P12.3 | L | | Pull Radarr image |
| 44 | P12.4 | L | | Pull Bazarr image |
| 45 | P12.5 | L | | Write all arr quadlet files |
| 46 | P12.6 | L | | Start all arr services |
| 47 | P12.7 | H | USER_ACTION | Configure Prowlarr indexers |
| 48 | P12.8 | L | | Connect Prowlarr to Sonarr/Radarr |
| 49 | P12.9 | L | | Configure download clients in Sonarr/Radarr |
| 50 | P12.10 | L | | Configure Bazarr subtitle sources |
| 51 | P12.11 | M | verify | Verify all arr services healthy |
| 52 | P12.12 | L | | Commit arr quadlet files |

### Autonomous work
1. **P12.1–P12.4** — Pull images:
   ```bash
   podman pull docker.io/linuxserver/prowlarr:latest
   podman pull docker.io/linuxserver/sonarr:latest
   podman pull docker.io/linuxserver/radarr:latest
   podman pull docker.io/linuxserver/bazarr:latest
   ```

2. **P12.5** — Write quadlet files:
   - `quadlets/media/osmen-media-prowlarr.container` (port 9696)
   - `quadlets/media/osmen-media-sonarr.container` (port 8989)
   - `quadlets/media/osmen-media-radarr.container` (port 7878)
   - `quadlets/media/osmen-media-bazarr.container` (port 6767)
   - All on osmen-media network, Slice=user-osmen-media.slice

3. **P12.6** — Start services:
   ```bash
   systemctl --user start osmen-media-{prowlarr,sonarr,radarr,bazarr}
   podman ps --filter name=osmen-media
   ```

4. **P12.8** — Connect Prowlarr → Sonarr/Radarr (via Prowlarr API — may need API keys from P12.7)

5. **P12.9** — Configure download clients:
   - Sonarr Settings → Download Clients → add qBittorrent (port 9090 via pod)
   - Radarr Settings → Download Clients → add qBittorrent + SABnzbd (port 8082)

6. **P12.10** — Configure Bazarr subtitle sources + connect to Sonarr/Radarr

7. **P12.11** — Health checks:
   ```bash
   curl -sf http://127.0.0.1:9696/api/v1/health?apikey=...
   curl -sf http://127.0.0.1:8989/api/v3/health?apikey=...
   curl -sf http://127.0.0.1:7878/api/v3/health?apikey=...
   curl -sf http://127.0.0.1:6767/api/system/health?apikey=...
   ```

8. **P12.12** — Commit: `git add quadlets/media/ && git commit -m "P12: Arr stack quadlets"`

### Blockers to collect
- **P12.7**: USER_ACTION — User must open http://127.0.0.1:9696 and add indexer sources
- P12.8–P12.10 partially depend on P12.7 (need Prowlarr API key)

### Key artifacts to create
- `/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-prowlarr.container`
- `/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-sonarr.container`
- `/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-radarr.container`
- `/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-bazarr.container`

---

## Final Handoff Report Template

When all 5 phases are done, produce this report:

```markdown
# Handoff Report — P8 (finish) + P9 + P10 + P11 + P12

## Phase Results
| Phase | Autonomous Done | Blocked | Blocker IDs |
|-------|----------------|---------|-------------|
| P8 | X/1 | Y | ... |
| P9 | X/15 | Y | ... |
| P10 | X/7 | Y | ... |
| P11 | X/16 | Y | ... |
| P12 | X/12 | Y | ... |

## Blockers Requiring User Input
1. [TW_ID] P{N}.{X} — [TYPE] — What's needed — How to get it
   (repeat for each)

## Taskwarrior Summary
- `task project:osmen.install.p8 summary`
- `task project:osmen.install.p9 summary`
- (etc.)
- Tasks completed this session: N
- Tasks remaining across P8-P12: N

## Verification Results
| Step | TW ID | Result | Notes |
|------|-------|--------|-------|
| (each verify step) | | PASS/FAIL/BLOCKED | |

## Files Created/Modified
(list all with full paths)

## Pitfall Check Results
| PF ID | Check | Result |
|-------|-------|--------|
| PF04 | DNS leak | |
| PF05 | IPv6 leak | |
| PF06 | VPN creds in git | |
| PF07 | VPN restart recovery | |
| PF08 | Port forwarding | |

## Commits
(git log --oneline for new commits)

## Known Issues
(anything that broke, workarounds applied)
```

---

## Key Reference Files

| File | Purpose |
|------|---------|
| `/home/dwill/dev/OsMEN-OC/temp_1st_install/INSTALL_PLAN.md` | Full ~271-step plan |
| `/home/dwill/dev/OsMEN-OC/temp_1st_install/install.log` | Running install log |
| `/home/dwill/dev/OsMEN-OC/config/compute-routing.yaml` | GPU/NPU routing rules |
| `/home/dwill/dev/OsMEN-OC/config/openclaw.yaml` | OpenClaw config |
| `/home/dwill/dev/OsMEN-OC/core/setup/wizard.py` | Setup wizard |
| `/home/dwill/dev/OsMEN-OC/core/gateway/app.py` | FastAPI gateway |
| `/home/dwill/dev/OsMEN-OC/core/gateway/mcp.py` | MCP tools |
| `/home/dwill/dev/OsMEN-OC/core/bridge/ws_client.py` | OpenClaw WebSocket bridge |
| `/home/dwill/dev/OsMEN-OC/quadlets/inference/osmen-inference-lmstudio.service` | LM Studio service |
| `/etc/systemd/system/lemonade-server.service` | Lemonade systemd unit |
| `/etc/systemd/system/lemonade-server.service.d/npu-memlock.conf` | NPU drop-in |
| `/etc/systemd/system/ollama.service.d/osmen-override.conf` | Ollama drop-in |
| `/home/dwill/dev/OsMEN-OC/.github/copilot-instructions.md` | Project rules |
| `/home/dwill/dev/OsMEN-OC/AGENTS.md` | Agent context |
| `/home/dwill/dev/OsMEN-OC/pyproject.toml` | Python deps |

## Critical Rules

- **Taskwarrior is the plan** — `task {id} start` / `task {id} done` for every step
- **NO stubs** — every module must have working implementation
- **NO `.env` files** — use SOPS or `~/.config/osmen/env`
- **Podman only** — no Docker references. Rootless Podman + systemd Quadlets.
- **Log every command** to `temp_1st_install/install.log`
- **pytest + pytest-anyio** (NOT pytest-asyncio) — marker: `@pytest.mark.anyio`
- **Python 3.13 conventions** — type hints, asyncio, pathlib, httpx, loguru
- Container naming: `osmen-{profile}-{service}` (e.g., `osmen-media-gluetun`)
- Networks: `osmen-{profile}.network` (e.g., `osmen-media.network`)
- Slices: `user-osmen-{slice}.slice` (e.g., `user-osmen-media.slice`)
