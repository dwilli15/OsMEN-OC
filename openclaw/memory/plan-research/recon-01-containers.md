# RECON 01: Container Inventory

**Collected:** 2026-04-18 03:25 CDT
**Host:** Ubu-OsMEN

---

## Pods

| Pod Name | Pod ID (short) | Created | Status | Network | Member Containers |
|---|---|---|---|---|---|
| download-stack | 5b49464c15de | 2026-04-17 21:54 CDT | Running | osmen-media | gluetun, sabnzbd, qbittorrent, prowlarr (+ infra) |

---

## Containers

### Running Containers

| Name | Image | Status | Uptime | Ports (host:container) | Pod | Restart | Systemd? | Health |
|---|---|---|---|---|---|---|---|---|
| 5b49464c15de-infra | (infra) | Running | 6h | 8082→8080, 8888→8888, 9090→9090, 9696→9696 (all 127.0.0.1) | download-stack | no | ❌ | 🟡 infra container |
| osmen-media-gluetun | docker.io/qmcgaw/gluetun:v3.40.2 | Running | 6h | (via pod ports) | download-stack | no | ❌ | 🟡 VPN client, unknown tunnel status |
| osmen-media-sabnzbd | docker.io/linuxserver/sabnzbd:latest (4.5.5-ls249) | Running | 6h | 8080 (pod-internal) | download-stack | no | ❌ | 🟡 running, unknown health |
| osmen-media-qbittorrent | docker.io/linuxserver/qbittorrent:5.1.0 | Running | 6h | 6881/tcp+udp (pod-internal), 8080 (pod-internal) | download-stack | no | ❌ | 🟡 running, unknown health |
| osmen-media-prowlarr | docker.io/linuxserver/prowlarr:latest (2.3.5.5327-ls142) | Running | 6h | 9696 (pod-internal) | download-stack | no | ❌ | 🟡 running, unknown health |

### Stopped/Exited Containers

| Name | Image | Status | Created | Exit Code | Ports | Pod | Restart | Systemd? | Health |
|---|---|---|---|---|---|---|---|---|
| osmen-librarian-kavita | docker.io/jvmilazz0/kavita:0.8.6 | Exited (0) | ~27h ago | 0 | 192.168.4.21:5000→5000 | — | no | ❌ | 🔴 stopped |
| osmen-media-flaresolverr | docker.io/flaresolverr/flaresolverr:latest (v3.4.6) | Exited (0) | ~27h ago | 0 | 127.0.0.1:8191→8191 | — | unless-stopped | ❌ | 🔴 stopped |
| osmen-media-komga-comics | docker.io/gotson/komga:latest (24.10) | Exited (143) | ~9h ago | 143 (SIGTERM) | 192.168.4.21:25600→25600 | — | no | ❌ | 🔴 stopped |

### Created (Never Started)

| Name | Image | Status | Created | Ports | Pod | Restart | Systemd? | Health |
|---|---|---|---|---|---|---|---|
| osmen-core-gateway-test | localhost/osmen-gateway:dev | Created | ~20h ago | 127.0.0.1:18789→8080 | — | no | ❌ | ⚫ never started |

---

## Volume Mounts (per container)

### osmen-librarian-kavita
| Type | Source | Destination | RW |
|---|---|---|---|
| volume | osmen-kavita-config.volume | /kavita/config | RW |
| bind | /home/dwill/media/manga-downloads | /manga-downloads | RO |
| bind | /home/dwill/media/books | /books | RO |
| bind | /home/dwill/media/comics | /comics | RO |
| bind | /home/dwill/media/manga | /manga | RO |

### osmen-media-flaresolverr
| Type | Source | Destination | RW |
|---|---|---|---|
| volume | ce4795ff… (anonymous) | /config | RW |

### osmen-media-komga-comics
| Type | Source | Destination | RW |
|---|---|---|---|
| bind | /home/dwill/media/komga-config-comics | /config | RW |
| bind | /home/dwill/media/comics | /comics | RO |
| bind | /run/media/dwill/Other_Media/Manga | /manga | RO |

### osmen-media-sabnzbd
| Type | Source | Destination | RW |
|---|---|---|---|
| volume | osmen-sab-config | /config | RW |
| bind | /home/dwill/Downloads | /downloads | RW |

### osmen-media-qbittorrent
| Type | Source | Destination | RW |
|---|---|---|---|
| volume | osmen-qbit-config | /config | RW |
| bind | /home/dwill/Downloads | /downloads | RW |

### osmen-media-prowlarr
| Type | Source | Destination | RW |
|---|---|---|---|
| volume | osmen-prowlarr-config | /config | RW |

### osmen-media-gluetun, osmen-core-gateway-test
No mounts.

---

## All Volumes (37 total)

| Name | Driver | Created | Mounted? | Notes |
|---|---|---|---|---|
| systemd-osmen-postgres-data | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-redis-data | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-chromadb-data | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-qbit-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-sab-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-prowlarr-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-sonarr-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-radarr-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-bazarr-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-kometa-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-kavita-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-tautulli-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-convertx-data | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-audiobookshelf-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-whisper-models | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-nextcloud-data | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-uptimekuma-data | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-caddy-config | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-audiobookshelf-metadata | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-caddy-data | local | 2026-04-12 | ❌ | Quadlet-named, no container |
| systemd-osmen-prometheus-data | local | 2026-04-13 | ❌ | Quadlet-named, no container |
| systemd-osmen-grafana-data | local | 2026-04-13 | ❌ | Quadlet-named, no container |
| systemd-osmen-plex-config | local | 2026-04-15 | ❌ | Quadlet-named, no container |
| osmen-mylar3-config | local | 2026-04-12 | ❌ | No container |
| osmen-readarr-config | local | 2026-04-12 | ❌ | No container |
| osmen-lidarr-config | local | 2026-04-12 | ❌ | No container |
| osmen-kometa-config | local | 2026-04-16 | ❌ | No container |
| osmen-prowlarr-config.volume | local | 2026-04-16 | ❌ | Duplicate of prowlarr config |
| osmen-sab-config.volume | local | 2026-04-16 | ❌ | Duplicate of sab config |
| osmen-qbit-config.volume | local | 2026-04-16 | ❌ | Duplicate of qbit config |
| osmen-kavita-config.volume | local | 2026-04-17 | ✅ kavita | Stopped container still exists |
| 7d49a61c… | local | 2026-04-17 | ❌ | Anonymous, no name |
| a108ec43… | local | 2026-04-17 | ❌ | Anonymous, no name |
| ce4795ff… | local | 2026-04-17 | ❌ | Anonymous, mounted by flaresolverr |
| osmen-sab-config | local | 2026-04-17 | ✅ sabnzbd | Active |
| osmen-qbit-config | local | 2026-04-17 | ✅ qbittorrent | Active |
| osmen-prowlarr-config | local | 2026-04-17 | ✅ prowlarr | Active |

**Only 5 of 37 volumes are actively mounted.**

---

## Networks (4 total)

| Name | Driver | Subnet | DNS | Created | Notes |
|---|---|---|---|---|---|
| osmen-core | bridge | 10.89.0.0/24 | yes | 2026-04-12 | No active containers |
| osmen-media | bridge | 10.89.1.0/24 | yes | 2026-04-12 | download-stack pod |
| podman | bridge | 10.88.0.0/16 | no | 2026-04-18 | Default, just created |
| podman-default-kube-network | bridge | 10.89.2.0/24 | yes | 2026-04-16 | From kube play |

---

## Images (non-dangling, with containers or named tags)

| Image | Size | Containers | Notes |
|---|---|---|---|
| localhost/osmen-gateway:dev | 267 MB | 1 (created, not running) | Local build |
| localhost/test-gateway:latest | 132 MB | 0 | Test build |
| docker.io/linuxserver/sabnzbd:latest (4.5.5) | 179 MB | 1 | Running |
| docker.io/linuxserver/prowlarr:latest (2.3.5) | 195 MB | 1 | Running |
| docker.io/linuxserver/qbittorrent:5.1.0 | 200 MB | 1 | Running |
| docker.io/qmcgaw/gluetun:v3.40.2 | 42 MB | 1 | Running |
| docker.io/gotson/komga:latest (24.10) | 604 MB | 1 | Stopped |
| docker.io/jvmilazz0/kavita:0.8.6 | 601 MB | 1 | Stopped |
| docker.io/flaresolverr/flaresolverr:latest (v3.4.6) | 690 MB | 1 | Stopped |
| docker.io/linuxserver/lidarr:3.1.0 | 310 MB | 0 | Pulled, no container |
| docker.io/linuxserver/lidarr:latest | 310 MB | 0 | Duplicate tag? |
| docker.io/b3log/siyuan:v3.6.4 | 246 MB | 0 | No container |
| docker.io/linuxserver/mylar3:latest (v0.9.0) | 547 MB | 0 | No container |
| docker.io/linuxserver/mylar3:0.8.1 | 200 MB | 0 | Old version |
| docker.io/library/python:3.13-slim | 130 MB | 0 | Base image |
| docker.io/library/ubuntu:24.04 | 81 MB | 0 | Base image |
| docker.io/kometateam/kometa:v2.3.1 | 309 MB | 0 | No container |
| docker.io/tautulli/tautulli:v2.17.0 | 219 MB | 0 | No container |
| ghcr.io/open-webui/open-webui:main | 4.8 GB | 0 | No container |
| docker.io/pgvector/pgvector:pg17 | 450 MB | 0 | No container |
| docker.io/c4illin/convertx:v0.17.0 | 3.7 GB | 0 | No container |
| docker.io/linuxserver/bazarr:1.5.2 | 434 MB | 0 | No container |
| docker.io/grafana/grafana-oss:12.1.0 | 732 MB | 0 | No container |
| docker.io/linuxserver/sabnzbd:4.5.1 | 180 MB | 0 | Old version |
| docker.io/need4swede/portall:latest | 401 MB | 0 | No container |
| docker.io/need4swede/portall:2.0.4 | 224 MB | 0 | Old version |
| docker.io/linuxserver/sonarr:4.0.14 | 208 MB | 0 | No container |
| docker.io/linuxserver/prowlarr:1.35.1 | 183 MB | 0 | Old version |
| docker.io/prom/prometheus:v3.4.0 | 305 MB | 0 | No container |
| docker.io/library/nextcloud:31.0.5-apache | 1.5 GB | 0 | No container |
| docker.io/library/nextcloud:31.0.5-fpm | 1.5 GB | 0 | No container |
| docker.io/advplyr/audiobookshelf:2.21.0 | 616 MB | 0 | No container |
| docker.io/linuxserver/radarr:5.21.1 | 209 MB | 0 | No container |
| docker.io/langflowai/langflow:1.3.1 | 2.5 GB | 0 | No container |
| docker.io/linuxserver/readarr:0.4.12-nightly | 191 MB | 0 | No container |
| docker.io/linuxserver/readarr:0.4.5-develop | 186 MB | 0 | Old version |
| docker.io/library/caddy:2.9-alpine | 49 MB | 0 | No container |
| docker.io/fedirz/faster-whisper-server:0.6.0-rc.3-cuda | 4.6 GB | 0 | No container |
| docker.io/louislam/uptime-kuma:1.23.16 | 470 MB | 0 | No container |
| docker.io/chromadb/chroma:0.5.23 | 486 MB | 0 | No container |
| docker.io/library/redis:7.2.5-alpine | 42 MB | 0 | No container |

## Dangling Images

**18 dangling images** — all `localhost/osmen-gateway:dev` build intermediates from repeated dev builds on 2026-04-16.

Notable: 2 dangling images at ~5.9 GB each (failed large builds).

---

## Disk Usage

| Type | Total | Active | Size | Reclaimable |
|---|---|---|---|---|
| Images | 103 | 8 | 39.92 GB | 37.47 GB (94%) |
| Containers | 9 | 5 | 28.18 MB | 20.64 MB (73%) |
| Local Volumes | 37 | 5 | 135.6 GB | 135.4 GB (100%) |

---

## Key Findings

1. **⚠️ No containers are systemd/quadlet managed.** All 9 containers lack the `PODMAN_SYSTEMD_UNIT` label. Yet 23 volumes have `systemd-osmen-` prefix naming, suggesting quadlet volumes were created but the containers are being run manually.

2. **Only 5 of 9 containers are running.** The download-stack pod (gluetun, sabnzbd, qbittorrent, prowlarr) is up. Kavita, FlareSolverr, and Komga are stopped. The gateway test container was created but never started.

3. **32 volumes have no active container** (135.4 GB potentially reclaimable). Many are `systemd-osmen-` prefixed with no matching running container, suggesting incomplete install.

4. **18 dangling images (~8 GB)** from gateway dev builds. Including two ~5.9 GB failed builds.

5. **Massive image bloat:** 39.92 GB total images, only 37.47 GB reclaimable. Many images pulled but never run (open-webui 4.8 GB, faster-whisper 4.6 GB, langflow 2.5 GB, convertx 3.7 GB, nextcloud 3 GB across two tags).

6. **Only the download-stack pod uses a custom network** (osmen-media). The osmen-core network has zero containers.

7. **Komga bind-mounts to external disk** (`/run/media/dwill/Other_Media/Manga`) — will fail if disk not mounted.
