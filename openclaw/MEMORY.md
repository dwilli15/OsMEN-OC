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
- Tiers 0-5 complete. 27 containers healthy. 32 tasks done this session.
- 74 pending tasks remain. ~70% of total vision.
- Key handoff: memory/osmen-handoff-2026-04-18-session2.md
- Git commit: a46acd0
- PostgreSQL user is `osmen` (not `postgres`)
- Redis is auth-protected
- Readarr only has 0.4.12-nightly tag available (no :release/:stable for linuxserver)
- Komga needs its quadlet symlinked — legacy podman-generate unit was overriding it
- Exec security/ask are PROTECTED config paths — cannot be patched, must edit JSON directly
- Subagent-nudge cron active (a947bdab, every 200s)

## Identity
- Born: 2026-04-11
