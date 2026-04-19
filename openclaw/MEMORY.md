# MEMORY.md - Long-Term Memory

## D
- Primary user, OsMEN-OC project lead
- Timezone: America/Chicago
- Email: d.osmen.oc@gmail.com (default for all services)
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
- Tiers 0-5 complete. 31 containers running, 29 healthy. 44+ tasks done across 3 sessions.
- 57 pending tasks remain. ~40% of total vision.
- **72h audit: memory/audit-2026-04-18-72h.md** — verified all completions are real
- Key handoff: memory/osmen-handoff-2026-04-18-session3-audit.md
- Git commits: a46acd0, 0cdb9d4, f1e8a43, d39fb93, 59668e2
- PostgreSQL user is `osmen` (not `postgres`)
- Redis auth-protected (clean hex password, no trailing newline)
- Readarr only has 0.4.12-nightly tag available (no :release/:stable for linuxserver)
### Manga Library (2026-04-19)
- Location: /mnt/other-media/Manga (213GB, 169 series)
- Formats: 1,687 CBZ + 323 PDF + 3,432 images — all CBR converted
- Trash: /mnt/other-media/Manga_Trash (43GB) — awaiting D's deletion approval
- Quarantine: /mnt/other-media/Manga_Quarantine/adult (4KB)
- All downloads drained (SABnzbd, qBittorrent, aria2c complete)
- DC/Western comics removed (725+ items), French removed (12), adult quarantined (10)
- Yen Press unsorted fully sorted into series
- Library is Plex/Komga-ready
- Cleanup details: memory/2026-04-18-manga-cleanup.md
- Komga needs initial browser setup (admin creds)
- Exec security/ask are PROTECTED config paths — cannot be patched, must edit JSON directly
- Podman secrets: ALWAYS use `echo -n` (no trailing newline!) when creating
- Gluetun DNS (198.18.0.1) does NOT resolve Podman container names — use IPs for pod→container
- Gluetun FIREWALL_OUTBOUND_SUBNETS needs /16 not /24 to cover all Podman networks
- qBittorrent PBKDF2 hashes: generate with Python hashlib.pbkdf2_hmac('sha512', ...) and inject into config
- Nextcloud admin: osmen / Oc!833!Oc! (10+ char policy)
- qBittorrent: osmen / Oc!833!Oc
- Prowlarr: SABnzbd (localhost:8080) + qBit (localhost:9090) wired, all 4 arr apps at fullSync; **IP-fragile** (hardcoded IPs, breaks on container restart)
- New services deployed: Homepage (:3010), Miniflux (:8180), Paperless-ngx (:8010), BentoPDF (:3020)
- Volume audit: 125.3GB reclaimable (osmen-sab-config.volume=125GB), needs D approval
- systemd failed units: chromadb-compact (Python indent error), secrets-audit (found AGE-SECRET-KEY in git history — investigate)
- 9 containers still have ReadOnly=true without Tmpfs=/tmp (Caddy, Plex, Tautulli, Kometa, monitoring stack)
- Stale crons cleaned: 2 subagent-nudge crons removed (no sub-agents), heckler-reviewer was already disabled

## GLM Team Cutover (2026-04-18)
- Retired Opus/GPT roster: main (opus-4.6), coder (gpt-5.4), auditor (gpt-5.4), reviewer (gpt-5.4), researcher (gpt-5.4)
- New GLM-only team: main (glm-5.1), coder (glm-5-turbo), auditor (glm-4.7-flash), basic (glm-4.7-flashx)
- Collapsed 6→4 agents: reviewer folded into basic, researcher folded into auditor
- All debriefs archived: memory/agent-debriefs/
- Config backup: ~/.openclaw/openclaw.json.pre-glm-handoff
- Stale crons removed: heckler-reviewer-300s, subagent-nudge
- Cost target: $5-8/24h on Z.AI (vs $33.60/72h from heckler alone)
- 8 commits pushed during handoff (a46acd0..c6b0fb1)

## Identity
- Born: 2026-04-11
- First model: claude-opus-4.6
- Current model: zai/glm-5.1 (since 2026-04-18)
