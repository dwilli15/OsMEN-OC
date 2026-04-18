# OsMEN-OC — Honest State of Play
## 2026-04-18 03:30 CDT — Synthesized from 10 recon agents

---

## The uncomfortable truth

Previous handoffs said the install was 80-85% done. **It's not.** Based on the actual live recon:

### What's actually running right now
- **Download stack pod** (gluetun + SABnzbd + qBittorrent + Prowlarr) — manually created, not systemd-owned
- **Plex** — native .deb, healthy
- **Ollama** — healthy, 3 models on RTX 5070
- **Lemonade** — 16 models (TTS, image gen, whisper, upscaling)
- **OpenClaw gateway** — healthy, Discord + Telegram connected

That's it. **5 running services + OpenClaw + Lemonade.** Everything else is a quadlet file on disk that was never deployed.

### What does NOT exist (no container, not running, never started)
- Sonarr, Radarr, Lidarr, Readarr, Bazarr, Mylar3 (all arr apps)
- Tautulli, Kometa
- PostgreSQL, Redis (core data services — blocks Nextcloud, Langflow, gateway features)
- Caddy (reverse proxy)
- Nextcloud, SiYuan, Langflow
- Grafana, Prometheus, Uptime Kuma, Portall (all monitoring)
- Audiobookshelf, ConvertX, Whisper (all librarian services)
- ChromaDB

### What exists but is stopped/broken
- Kavita — exited
- Komga — exited
- FlareSolverr — exited
- SABnzbd — running but in wizard mode (config didn't persist)
- qBittorrent — running but auth broken
- osmen-core-gateway-test — created but never started

---

## Hardware (confirmed)

| Component | Detail |
|-----------|--------|
| Machine | HP OMEN 17" laptop |
| CPU | AMD Ryzen AI 9 365 (10C/20T) + NPU |
| RAM | 60 GB |
| dGPU | NVIDIA RTX 5070 Max-Q 8GB |
| iGPU | AMD Radeon 880M |
| NPU | `/dev/accel0` present, unused |
| Boot drive | SK Hynix 928GB NVMe, LUKS encrypted, 63% used |
| External 1 | WD Elements 4.6TB (Plex media, 56% used) |
| External 2 | WD Passport 1.9TB (TV/Anime overflow, 6% used) |
| External 3 | Samsung 870 QVO 932GB (Other_Media — manga/comics, 75% used) |

---

## Blocker inventory (ordered by impact)

### 🔴 CRITICAL — Must fix first

1. **5 quadlet files have git merge conflicts**
   - chromadb, postgres, redis, core network, core slice
   - This blocks ALL quadlet generation. Nothing systemd-managed will work.
   - Files: `quadlets/core/osmen-core-chromadb.container`, `osmen-core.network`, `osmen-core-postgres.container`, `osmen-core-redis.container`, `user-osmen-core.slice`

2. **4 missing slice definitions**
   - `user-osmen-services.slice`, `user-osmen-media.slice`, `user-osmen-background.slice`, `user-osmen-inference.slice`
   - Referenced by containers but don't exist
   - Will cause unit load failures even after merge conflicts are fixed

3. **No firewall active**
   - UFW inactive, iptables wide open, nft not loaded
   - SSH (22) and Plex (32400) bound to 0.0.0.0
   - Any coffee shop WiFi = exposed

4. **PostgreSQL and Redis don't exist**
   - Core data services — Gateway features, Nextcloud, Langflow, ChromaDB all need them
   - Can't be created until merge conflicts are fixed

### 🟡 HIGH — Fix after critical

5. **Download stack not systemd-owned**
   - Running containers were manually created
   - Won't survive reboot
   - Can't be fixed until merge conflicts + missing slices are resolved

6. **SABnzbd wizard regression**
   - Config didn't persist — needs volume verification + wizard re-completion
   - Blocked on download-stack reconciliation

7. **qBittorrent auth broken**
   - D chose option (b): nuke and recreate
   - Blocked on download-stack reconciliation

8. **ReadOnly=true on 20+ quadlets**
   - Most linuxserver.io apps will fail to start
   - Must fix before deploying any new containers

9. **PUID/PGID missing on 6+ linuxserver containers**
   - Will run as root inside container
   - Permission mismatches on volumes

10. **3 floating images** (SABnzbd :latest, Komga :latest, Readarr :nightly)

### 🟠 MEDIUM — After high

11. **125GB SABnzbd volume on root NVMe** — should move to external
12. **Broken symlinks in ~/media/** — point to /run/media/ but drives mount at /mnt/
13. **Duplicate volumes** — both `osmen-X` and `systemd-osmen-X` variants
14. **sdc2 double-mounted** at /mnt/other-media AND /run/media/dwill/Other_Media
15. **Malformed komga-comics quadlet** — no Unit section, hardcoded paths, :latest
16. **Security: Discord groupPolicy="open"**, Telegram allowFrom="*"
17. **osmen-db-backup.service failed** at 02:32 tonight
18. **37.5GB reclaimable** in unused images
19. **135GB in orphaned volumes**

---

## Revised completion estimate

| Area | Previous claim | Actual |
|------|---------------|--------|
| Core platform (gateway, channels) | 85% | **70%** (running but postgres/redis missing) |
| Media download stack | 65% | **30%** (running but not owned, wizard broken, auth broken) |
| Media management (arr apps) | 40% | **0%** (none deployed) |
| Librarian services | 40% | **0%** (all exited or never started) |
| Monitoring | 30% | **0%** (none deployed) |
| Core services (DB, cache, proxy) | 60% | **0%** (none deployed) |
| Inference | 50% | **60%** (Ollama + Lemonade working, LM Studio empty) |
| Security | 40% | **20%** (SSH good, no firewall, open Discord policy) |
| **Overall** | **~70%** | **~25%** |

---

## Revised plan: what actually needs to happen

### Tier 0: Unblock everything (1-2 hours)
1. Resolve 5 git merge conflicts
2. Create 4 missing slice definitions
3. Enable UFW with basic rules (SSH, Plex, localhost containers)
4. Fix ReadOnly=true across all quadlets
5. Add missing PUID/PGID
6. Pin floating images
7. `systemctl --user daemon-reload`

### Tier 1: Core services (2-3 hours)
8. Deploy PostgreSQL + Redis via quadlet
9. Verify they're healthy
10. Deploy Caddy (reverse proxy)

### Tier 2: Download stack stabilization (2-3 hours)
11. Stop manually-created download stack
12. Start download stack via systemd/quadlet
13. Re-complete SABnzbd wizard
14. Nuke + recreate qBittorrent config
15. Verify Prowlarr search
16. Add FIREWALL_OUTBOUND_SUBNETS for FlareSolverr

### Tier 3: Arr stack deployment (2-3 hours)
17. Deploy Sonarr, Radarr, Lidarr, Readarr, Bazarr, Mylar3
18. Wire Prowlarr app sync to all arr apps
19. Configure root folders and profiles

### Tier 4: Librarian + monitoring (2-3 hours)
20. Deploy Kavita, Komga, Audiobookshelf, ConvertX, Whisper
21. Deploy Grafana, Prometheus, Uptime Kuma
22. Deploy Homepage dashboard (port visibility for D)

### Tier 5: Core apps (1-2 hours)
23. Deploy Nextcloud (D committed to it)
24. Deploy SiYuan, Langflow, ChromaDB

### Tier 6: Cleanup + verification (1-2 hours)
25. Fix broken ~/media/ symlinks
26. Clean duplicate volumes
27. Reclaim 37.5GB in unused images
28. Move SABnzbd volume off root NVMe
29. Fix double-mounted sdc2
30. Git commit the whole thing

### Tier 7: Post-stabilization features
31. Bridge testing (Telegram/Discord)
32. Calendar integration (bidirectional per D's choice)
33. Multi-agent Discord team
34. Paperless-ngx deployment
35. PKM architecture
36. Inference optimization

---

## D's answers applied

| Decision | Answer | Impact |
|----------|--------|--------|
| Download-stack ownership | (a) quadlet/systemd | Reconciliation is go |
| qBittorrent auth | (b) nuke and recreate | Clean slate, no browser needed |
| Nextcloud | (a) commit | Deploy after PostgreSQL is up |
| Calendar | (b) bidirectional | Implementation after stabilization |
| PKM | (c) fresh start | SiYuan stays clean, no OneDrive restore |

---

## Time estimate

| Tier | Hours | Can run overnight? |
|------|-------|--------------------|
| 0: Unblock | 1-2 | Yes (agent work) |
| 1: Core services | 2-3 | Yes |
| 2: Download stack | 2-3 | Mostly (wizard needs browser) |
| 3: Arr stack | 2-3 | Yes |
| 4: Librarian + monitoring | 2-3 | Yes |
| 5: Core apps | 1-2 | Yes |
| 6: Cleanup | 1-2 | Yes |
| **Total** | **~12-18 hours** | Most of it |

This is real work, not "just clean up a few things." The install needs to be built, not just fixed.
