# MEMORY.md - Long-Term Memory

## D
- Primary user, OsMEN-OC project lead
- Timezone: America/Chicago
- Telegram: @dwillnow
- Discord: @deewill
- Self-describes as newbie / inexperienced vibe-coder
- Values solutions that match their skill level
- Prefers GUI admin where possible over CLI-only management
- Buddhist practitioner (Dzogchen, Mahamudra, Tummo, Three Yanas) — student not teacher
- Meditation instructor (entrepreneurial overlap)
- Father/husband
- FFXIV player
- Considering Unraid as management umbrella — **DECIDED AGAINST 2026-04-18: staying Ubuntu 26 + Podman**
- Curious about but not switching to: Unraid ($49 license), Umbrel
- Interested in adding: Paperless-ngx, deeper ConvertX integration, Pangolin, BentoPDF, Audiobookshelf (already has quadlet), RyzenAI-SW (AMD AI), Komodo (container management)
- Wants long-term Podman management strategy for updates/drift prevention

## OsMEN-OC
- Personal operating system / life management platform
- Podman-based containerized stack on Ubuntu (currently quadlet/systemd)
- Plex native install, everything else containerized
- VPN-routed download stack via Gluetun
- OpenClaw as primary AI interface (Telegram, Discord, webchat)
- PKM vision: interconnected tagged databases (personal, work, homeowner, entrepreneurial, dharma, FFXIV, meditation instructor, father-husband)
- Agent team vision: multiple LLM agents in Discord (Claude, OpenCode, local LM, OpenClaw)
- Inference ecosystem: Ollama, LM Studio, Lemonade, VS Code Insiders/Copilot, Claude, OpenCode, Wave Terminal

## Stabilization Progress (2026-04-18)
- Tiers 0-5 complete. 30 containers running, 29 healthy. 42+ tasks done across 3 sessions.
- 64 pending tasks remain. ~40% of total vision.
- Key handoff: memory/osmen-handoff-2026-04-18-session2.md
- Git commits: a46acd0, 0cdb9d4, f1e8a43
- PostgreSQL user is `osmen` (not `postgres`)
- Redis auth-protected (clean hex password, no trailing newline)
- Readarr only has 0.4.12-nightly tag available (no :release/:stable for linuxserver)
- Komga needs initial browser setup (admin creds)
- Exec security/ask are PROTECTED config paths — cannot be patched, must edit JSON directly
- Podman secrets: ALWAYS use `echo -n` (no trailing newline!) when creating
- Gluetun DNS (198.18.0.1) does NOT resolve Podman container names — use IPs for pod→container
- Gluetun FIREWALL_OUTBOUND_SUBNETS needs /16 not /24 to cover all Podman networks
- qBittorrent PBKDF2 hashes: generate with Python hashlib.pbkdf2_hmac('sha512', ...) and inject into config
- Nextcloud admin: osmen / Oc!833!Oc! (10+ char policy)
- qBittorrent: osmen / Oc!833!Oc
- Prowlarr: SABnzbd (localhost:8080) + qBit (localhost:9090) wired, all 4 arr apps at fullSync
- New services deployed: Homepage (:3010), Miniflux (:8180), Paperless-ngx (:8010)
- Volume audit: 125.3GB reclaimable (osmen-sab-config.volume=125GB), needs D approval

## Identity
- Born: 2026-04-11
