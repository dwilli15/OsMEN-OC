# OsMEN-OC Service State Capture

**Captured:** 2026-04-18 ~21:02 CDT (post-restart, ~10 min uptime)

---

## 1. All Containers

| Name | Image | Status | Ports |
|------|-------|--------|-------|
| osmen-media-flaresolverr | flaresolverr:latest | **Exited (0)** 292y ago | 127.0.0.1:8191→8191, 8192 |
| osmen-core-gateway-test | localhost/osmen-gateway:dev | **Created** (not running) | 127.0.0.1:18789→8080 |
| download-stack-infra | (network infra) | Up | 8082, 8888, 9090, 9696 |
| osmen-core-redis | redis:7.2.5-alpine | Up (healthy) | 127.0.0.1:6379→6379 |
| osmen-core-caddy | caddy:2.9-alpine | Up (healthy) | 0.0.0.0:80→80, 0.0.0.0:443→443 |
| osmen-monitoring-uptimekuma | louislam/uptime-kuma:1.23.16 | Up (healthy) | 127.0.0.1:3001→3000 |
| osmen-monitoring-portall | need4swede/portall:2.0.4 | Up (healthy) | 127.0.0.1:3080→8080 |
| osmen-core-chromadb | chromadb/chroma:0.5.23 | Up (healthy) | 127.0.0.1:8000→8000 |
| osmen-core-siyuan | b3log/siyuan:v3.6.4 | Up (healthy) | 127.0.0.1:6806→6806 |
| osmen-media-readarr | linuxserver/readarr:0.4.12-nightly | Up (healthy) | 127.0.0.1:8787→8787 |
| osmen-librarian-convertx | c4illin/convertx:v0.17.0 | Up (healthy) | 127.0.0.1:3000→3000 |
| osmen-tools-bentopdf | ghcr.io/alam00000/bentopdf:latest | Up (healthy) | 127.0.0.1:3020→8080 |
| osmen-media-komga-comics | gotson/komga:1.24.3 | Up (healthy) | 127.0.0.1:25600→25600 |
| osmen-media-mylar3 | linuxserver/mylar3:0.8.1 | Up (healthy) | 127.0.0.1:8090→8090 |
| osmen-media-lidarr | linuxserver/lidarr:3.1.0 | Up (healthy) | 127.0.0.1:8686→8686 |
| osmen-media-tautulli | tautulli/tautulli:v2.17.0 | Up (healthy) | 127.0.0.1:8181→8181 |
| osmen-media-sonarr | linuxserver/sonarr:4.0.14 | Up (healthy) | 127.0.0.1:8989→8989 |
| osmen-media-bazarr | linuxserver/bazarr:1.5.2 | Up (healthy) | 127.0.0.1:6767→6767 |
| osmen-media-radarr | linuxserver/radarr:5.21.1 | Up (healthy) | 127.0.0.1:7878→7878 |
| osmen-monitoring-prometheus | prom/prometheus:v3.4.0 | Up (healthy) | 127.0.0.1:9091→9090 |
| osmen-dashboard-homepage | ghcr.io/gethomepage/homepage:latest | Up (healthy) | 127.0.0.1:3010→3000 |
| osmen-librarian-whisper | fedirz/faster-whisper-server:0.6.0-rc.3-cuda | Up (healthy) | 127.0.0.1:9001→8000 |
| osmen-core-postgres | pgvector/pgvector:pg17 | Up (healthy) | 127.0.0.1:5432→5432 |
| osmen-librarian-audiobookshelf | advplyr/audiobookshelf:2.21.0 | Up (healthy) | 127.0.0.1:13378→80 |
| osmen-media-gluetun | qmcgaw/gluetun:v3.40.2 | Up (healthy) | 8082, 8888, 9090, 9696, 8388 |
| osmen-monitoring-grafana | grafana/grafana-oss:12.1.0 | Up (healthy) | 127.0.0.1:3002→3000 |
| osmen-core-miniflux | miniflux/miniflux:latest | Up (healthy) | 127.0.0.1:8180→8080 |
| osmen-core-gateway | localhost/osmen-gateway:dev | Up (healthy) | 127.0.0.1:18788→8080 |
| osmen-core-langflow | langflowai/langflow:1.3.1 | Up (healthy) | 127.0.0.1:7860→7860 |
| osmen-core-paperless | ghcr.io/paperless-ngx/paperless-ngx:latest | Up (healthy) | 127.0.0.1:8010→8000 |
| osmen-media-prowlarr | linuxserver/prowlarr:1.35.1 | Up (healthy) | 8082, 8888, 9090, 9696 |
| osmen-media-sabnzbd | linuxserver/sabnzbd:4.5.1 | Up (healthy) | 8082, 8888, 9090, 9696 |
| osmen-media-qbittorrent | linuxserver/qbittorrent:5.1.0 | Up (healthy) | 8082, 8888, 9090, 9696, 6881 |

**Total:** 33 containers (31 running, 1 exited, 1 created)

---

## 2. Container Health

All 31 running containers report **healthy**. The `download-stack-infra` network container has no healthcheck defined.

---

## 3. Resource Usage

| Container | Memory | CPU% |
|-----------|--------|------|
| osmen-media-komga-comics | **1.18 GB** | **111.76%** ⚠️ |
| osmen-core-langflow | **1.19 GB** | 4.30% |
| osmen-core-paperless | 637.6 MB | 5.07% |
| osmen-media-sonarr | 271.9 MB | 1.76% |
| osmen-media-bazarr | 233 MB | 2.02% |
| osmen-media-lidarr | 212.8 MB | 1.11% |
| osmen-media-radarr | 189 MB | 1.19% |
| osmen-media-readarr | 180.8 MB | 1.11% |
| osmen-media-prowlarr | 177 MB | 1.01% |
| osmen-dashboard-homepage | 161.7 MB | 0.45% |
| osmen-core-chromadb | 152.6 MB | 0.60% |
| osmen-monitoring-uptimekuma | 110.5 MB | 0.79% |
| osmen-librarian-whisper | 116.2 MB | 1.06% |
| osmen-monitoring-grafana | 101.8 MB | 0.56% |
| osmen-media-sabnzbd | 101.1 MB | 0.32% |
| osmen-media-gluetun | 136.9 MB | 0.47% |
| osmen-monitoring-portall | 59.17 MB | 0.15% |
| osmen-media-tautulli | 67.22 MB | 0.51% |
| osmen-media-mylar3 | 97.56 MB | 0.34% |
| osmen-core-caddy | 48.13 MB | 0.03% |
| osmen-librarian-audiobookshelf | 48.45 MB | 0.33% |
| osmen-core-gateway | 74.2 MB | 0.59% |
| osmen-media-qbittorrent | 61.35 MB | 0.13% |
| osmen-core-siyuan | 32.04 MB | 0.33% |
| osmen-core-postgres | 84.61 MB | 0.24% |
| osmen-core-miniflux | 37.65 MB | 0.03% |
| osmen-librarian-convertx | 25.93 MB | 0.68% |
| osmen-core-redis | 13.46 MB | 0.16% |
| osmen-tools-bentopdf | 10.32 MB | 0.02% |
| osmen-monitoring-prometheus | 30.99 MB | 0.06% |
| download-stack-infra | 266.2 kB | 0.00% |

**Total host RAM:** 65.3 GB. Top consumers: Langflow + Komga = ~2.37 GB combined.

---

## 4. systemd Units

### Running Services (28)
All core/media/monitoring/librarian/dashboard services **active (running)**.

### ⚠️ Failed / Auto-Restart Looping (2)
- **osmen-media-kometa.service** — `activating (auto-restart)` — Plex metadata manager
- **osmen-media-plex.service** — `activating (auto-restart)` — Plex Media Server

### Inactive (one-shot, scheduled via timers)
- osmen-chromadb-compact, osmen-db-backup, osmen-db-vacuum, osmen-health-report, osmen-memory-maintenance, osmen-secrets-audit, osmen-smart-check, osmen-vpn-audit

### Active Timers (8)
- osmen-chromadb-compact.timer (weekly)
- osmen-db-backup.timer (nightly)
- osmen-db-vacuum.timer (weekly)
- osmen-health-report.timer (daily)
- osmen-memory-maintenance.timer
- osmen-secrets-audit.timer (daily)
- osmen-smart-check.timer (weekly)
- osmen-vpn-audit.timer

### Failed Units
**0 failed units.** (Kometa/Plex are in auto-restart, not failed state.)

---

## 5. Network Connectivity (curl localhost)

| Service | Port | HTTP Status | Notes |
|---------|------|-------------|-------|
| Caddy | 80 | **200** ✅ | |
| Homepage | 3010 | **200** ✅ | |
| Miniflux | 8180 | **200** ✅ | |
| Paperless | 8010 | **302** ✅ | Redirect (login) |
| BentoPDF | 3020 | **200** ✅ | |
| Komga | 25600 | **200** ✅ | |
| Audiobookshelf | 13378 | **200** ✅ | |
| Grafana | 3000 | **302** ✅ | Redirect (login) |
| Prometheus | 9092 | **000** ❌ | Mapped on 9091→9090, not 9092 |
| Uptime Kuma | 3001 | **302** ✅ | Redirect (login) |
| Portall | 3003 | **000** ❌ | Mapped on 3080→8080, not 3003 |
| SiYuan | 6806 | **401** ✅ | Auth required |
| Langflow | 7860 | **200** ✅ | |
| SABnzbd | 8082 | **200** ✅ | |
| Prowlarr | 9696 | **200** ✅ | |
| qBittorrent | 9090 | **200** ✅ | |
| Sonarr | 8989 | **200** ✅ | |
| Radarr | 7878 | **200** ✅ | |
| Lidarr | 8686 | **200** ✅ | |
| Readarr | 8787 | **200** ✅ | |
| Bazarr | 6767 | **200** ✅ | |
| Mylar3 | 8090 | **401** ✅ | Auth required |
| Whisper | 9000 | **000** ❌ | Mapped on 9001→8000, not 9000 |
| ConvertX | 3100 | **000** ❌ | Mapped on 3000→3000, not 3100 |
| ChromaDB | 8000 | **404** ✅ | No root handler (expected) |

### Port Mapping Corrections
The following services are accessible but on different host ports than listed:
- **Prometheus:** host port **9091** (not 9092)
- **Portall:** host port **3080** (not 3003)
- **Whisper:** host port **9001** (not 9000)
- **ConvertX:** host port **3000** (not 3100)

---

## 6. Cron Jobs (`~/.openclaw/cron/jobs.json`)

| ID | Name | Enabled | Schedule | Last Status |
|----|------|---------|----------|-------------|
| heckler-reviewer-300s | Heckler reviewer loop | **Disabled** | Every 5 min | ok |
| subagent-nudge | subagent-nudge | **Disabled** | Every 200s | ok |

Both jobs are currently **disabled**.

---

## 7. Credentials Reference (Local Services Only)

| Service | User | Password / Key | Notes |
|---------|------|----------------|-------|
| Komga | d.osmen.oc@gmail.com | Oc!8533!Oc | |
| qBittorrent | osmen | Oc!833!Oc | Auth may be broken |
| Miniflux | osmen | Oc!833!Oc! | |
| Paperless | osmen | Oc!833!Oc! | |
| SABnzbd | — | API: b69fd362889549ff9dffd8cddbb983ea | |
| Prowlarr | — | API: 0a7c9db5fe024343af5a1dafaf09aad6 | |
| PostgreSQL | osmen | — | |
| Redis | — | hex: 8887ee14a2625688c35cd054820870939aacbdd6e03b4f88f64060ec921b2c16 | |

---

## 8. Issues / Notes

1. **Komga high CPU** — 111.76% CPU, likely still scanning/initializing post-restart
2. **Plex & Kometa** — Both in auto-restart loop; not yet running successfully
3. **Port mapping discrepancies** — Several services mapped to different host ports than expected (see section 5)
4. **Flaresolverr** — Exited long ago (not needed currently)
5. **osmen-core-gateway-test** — Created but never started (test container)
