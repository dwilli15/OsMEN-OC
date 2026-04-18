# Recon 05: Service Health + Accessibility Truth

**Date:** 2026-04-18 03:25 CDT
**Method:** curl -sS -o /dev/null -w '%{http_code}' -m 5 + podman ps -a + systemctl

## Results

| # | Service | Port | Container | Status | HTTP Code | Notes |
|---|---------|------|-----------|--------|-----------|-------|
| 1 | SABnzbd | 8082 | osmen-media-sabnzbd | ✅ Running | 303 → /wizard/ | Needs initial setup wizard |
| 2 | qBittorrent | 9090 | osmen-media-qbittorrent | ✅ Running | 200 | Accessible |
| 3 | Prowlarr | 9696 | osmen-media-prowlarr | ✅ Running | 200 | /ping also 200 |
| 4 | Sonarr | 8989 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 5 | Radarr | 7878 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 6 | Lidarr | 8686 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 7 | Readarr | 8787 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 8 | Bazarr | 6767 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 9 | Mylar3 | 8090 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 10 | Plex | 32400 | _(native)_ | ✅ Running (systemd) | 302 → /web/index.html | Native service, active |
| 11 | Tautulli | 8181 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 12 | Kometa | — | _(none)_ | ❌ No container | — | Batch process, no web UI, container absent |
| 13 | Kavita | 5000 | osmen-librarian-kavita | ❌ Exited | 000 | Exited, bound to 192.168.4.21:5000 |
| 14 | Komga | 25600 | osmen-media-komga-comics | ❌ Exited (143) | 000 | Killed 8h ago, bound to 192.168.4.21:25600 |
| 15 | Audiobookshelf | 13378 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 16 | Nextcloud | 8080 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 17 | SiYuan | 6806 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 18 | Langflow | 7860 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 19 | Grafana | 3002 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 20 | Prometheus | 9091 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 21 | Uptime Kuma | 3001 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 22 | Portall | — | _(none)_ | ❌ No container | 000 | Container does not exist |
| 23 | ChromaDB | 8000 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 24 | ConvertX | 3000 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 25 | FlareSolverr | 8191 | osmen-media-flaresolverr | ❌ Exited | 000 | Exited |
| 26 | Gluetun | 8888 | osmen-media-gluetun | ✅ Running | 400 | Proxy responding (400 = no target host) |
| 27 | Caddy | 80/443 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 28 | Whisper | 9001 | _(none)_ | ❌ No container | 000 | Container does not exist |
| 29 | LM Studio | 1234 | _(native)_ | ❌ Down | 000 | Not running |
| 30 | Ollama | 11434 | _(native)_ | ✅ Running | 200 | /api/tags responding |
| 31 | Plex (native) | — | systemd | ✅ Active | — | plexmediaserver active |
| 32 | OpenClaw | — | systemd | ✅ Running | — | Gateway running |
| 33 | PostgreSQL | — | _(none)_ | ❌ No container | — | No postgres container found |
| 34 | Redis | — | _(none)_ | ❌ No container | — | No redis container found |

## Infrastructure Container

| Container | Status | Notes |
|-----------|--------|-------|
| 5b49464c15de-infra | Up 6 hours | Runs Gluetun + exposes 8082/8888/9090/9696 |
| osmen-core-gateway-test | Created (not started) | OpenClaw gateway test container |

**Key insight:** All media containers (sabnzbd, qbittorrent, prowlarr) run inside the `5b49464c15de-infra` pod via Gluetun. Port mapping is shared across all containers in the infra pod.

## Summary

| Category | Count | Services |
|----------|-------|----------|
| ✅ Running & Accessible | **5** | SABnzbd, qBittorrent, Prowlarr, Plex, Ollama |
| ✅ Running (infra/proxy) | **2** | Gluetun, OpenClaw |
| ❌ Exited (container exists) | **3** | Kavita, Komga, FlareSolverr |
| ❌ No container exists | **21** | Sonarr, Radarr, Lidarr, Readarr, Bazarr, Mylar3, Tautulli, Kometa, Audiobookshelf, Nextcloud, SiYuan, Langflow, Grafana, Prometheus, Uptime Kuma, Portall, ChromaDB, ConvertX, Caddy, Whisper, PostgreSQL, Redis |
| ❌ Native service down | **1** | LM Studio |

**Bottom line:** Only 5 of 30+ planned services are actually running. The media download stack (SAB/qBit/Prowlarr) works but has no *arr* managers to consume downloads. Most of the ecosystem (monitoring, reading apps, notes, AI services) has never been deployed or containers were removed. PostgreSQL and Redis — likely needed by many services — are missing entirely.
