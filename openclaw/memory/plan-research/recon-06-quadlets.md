# RECON 06: Quadlet Files — Line-by-Line Truth

Generated: 2026-04-18 03:25 CDT

---

## MERGE CONFLICT SUMMARY

**5 files with unresolved git merge conflicts:**

| File | Conflict Count |
|------|---------------|
| `core/osmen-core-chromadb.container` | 3 conflicts |
| `core/osmen-core-postgres.container` | 2 conflicts |
| `core/osmen-core-redis.container` | 2 conflicts |
| `core/osmen-core.network` | 1 conflict |
| `core/user-osmen-core.slice` | 1 conflict |

**These files CANNOT deploy until conflicts are resolved.**

---

## DEPENDENCY CROSS-REFERENCE

### Volumes Referenced vs. Defined

**Referenced but NOT in volumes/ directory (defined elsewhere):**
- `osmen-lidarr-config.volume` — defined in `media/osmen-lidarr-config.volume` ✅
- `osmen-mylar3-config.volume` — defined in `media/osmen-mylar3-config.volume` ✅
- `osmen-readarr-config.volume` — defined in `media/osmen-readarr-config.volume` ✅

All other volume references match files in `volumes/`. ✅

### Pods Referenced vs. Defined
- `download-stack.pod` — defined in `media/download-stack.pod` ✅ (referenced by gluetun, prowlarr, qbittorrent, sabnzbd)

### Networks Referenced vs. Defined
- `osmen-core.network` — defined in `core/osmen-core.network` ✅
- `osmen-media.network` — defined in `media/osmen-media.network` ✅

### Service Dependencies (After=)
- `osmen-core-network.service` → generated from `core/osmen-core.network` ✅
- `osmen-media-network.service` → generated from `media/osmen-media.network` ✅
- `osmen-core-postgres.service` → generated from `core/osmen-core-postgres.container` ✅
- `osmen-core-redis.service` → generated from `core/osmen-core-redis.container` ✅
- `osmen-core-chromadb.service` → generated from `core/osmen-core-chromadb.container` ✅
- `osmen-media-gluetun.service` → generated from `media/osmen-media-gluetun.container` ✅
- `osmen-monitoring-prometheus.service` → generated from `monitoring/osmen-monitoring-prometheus.container` ✅

### Slice References (Slice=)
- `user-osmen-services.slice` — ⚠️ **NOT defined anywhere** (used by: caddy, gateway, langflow, nextcloud, siyuan)
- `user-osmen-core.slice` — defined in `core/user-osmen-core.slice` ✅ (used by: chromadb, postgres, redis)
- `user-osmen-media.slice` — ⚠️ **NOT defined anywhere** (used by: bazarr, gluetun, komga-comics, lidarr, mylar3, plex, prowlarr, qbittorrent, radarr, readarr, sabnzbd, sonarr)
- `user-osmen-background.slice` — ⚠️ **NOT defined anywhere** (used by: kometa, tautulli, audiobookshelf, convertx, kavita, whisper, grafana, portall, prometheus, uptimekuma)
- `user-osmen-inference.slice` — ⚠️ **NOT defined anywhere** (used by: ollama, lmstudio)

---

## FILE-BY-FILE DETAILS

---

### CORE

---

#### `core/osmen-core-caddy.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/library/caddy:2.9-alpine` |
| **ContainerName** | `osmen-core-caddy` |
| **Pod** | — |
| **Network** | `osmen-core.network`, `osmen-media.network` |
| **PublishPort** | `80:80`, `443:443` (0.0.0.0 — LAN-wide) |
| **Volumes** | `%h/dev/OsMEN-OC/config/Caddyfile:/etc/caddy/Caddyfile:ro`, `osmen-caddy-data.volume:/data`, `osmen-caddy-config.volume:/config` |
| **Env** | — (none) |
| **Secrets** | — (none) |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:80` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-services.slice` ⚠️ undefined |
| **MemoryMax** | `256M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `core/osmen-core-chromadb.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/chromadb/chroma:0.5.23` |
| **ContainerName** | `osmen-core-chromadb` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:8000:8000` |
| **Volumes** | `osmen-chromadb-data.volume:/chroma/chroma` |
| **Env** | `CHROMA_SERVER_AUTH_PROVIDER`, `IS_PERSISTENT`, `ANONYMIZED_TELEMETRY` |
| **Secrets** | `osmen-chromadb-token` → `CHROMA_SERVER_AUTH_CREDENTIALS` |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | ⚠️ **CONFLICT** — HEAD: `curl -sf http://127.0.0.1:8000/api/v1/heartbeat` vs origin/main: `/bin/sh -c "curl -sf ..."` |
| **ReadOnly** | ⚠️ **CONFLICT** — HEAD: no ReadOnly (has Tmpfs=/tmp, SecurityLabelDisable, NoNewPrivileges) vs origin/main: `ReadOnly=true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-core.slice` |
| **MemoryMax** | `2G` |
| **CPUQuota** | `200%` |
| **Merge conflicts** | **3 UNRESOLVED** (Documentation URL, HealthCmd, ReadOnly/Security) |

---

#### `core/osmen-core-gateway.container`

| Field | Value |
|-------|-------|
| **Image** | `osmen-gateway:dev` (local build) |
| **ContainerName** | `osmen-core-gateway` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:18788:8080` |
| **Volumes** | `%h/dev/OsMEN-OC/agents:/app/agents:ro`, `%h/dev/OsMEN-OC/config:/app/config:ro`, `%h/.taskrc:/root/.taskrc:ro`, `%h/.task:/root/.task` |
| **Env** | `DATABASE_HOST`, `DATABASE_PORT`, `REDIS_HOST`, `REDIS_PORT`, `CHROMADB_HOST`, `CHROMADB_PORT` |
| **Secrets** | `osmen-postgres-password` → `DATABASE_PASSWORD`, `osmen-redis-password` → `REDIS_PASSWORD`, `osmen-chromadb-token` → `CHROMADB_TOKEN` |
| **After** | `osmen-core-postgres.service`, `osmen-core-redis.service`, `osmen-core-chromadb.service`, `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `python3 -c 'import socket; s=socket.socket(); s.connect(("127.0.0.1",8080)); s.close()'` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-services.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `200%` |
| **Merge conflicts** | None |

---

#### `core/osmen-core-langflow.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/langflowai/langflow:1.3.1` |
| **ContainerName** | `osmen-core-langflow` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:7860:7860` |
| **Volumes** | — (none) |
| **Env** | `LANGFLOW_DO_NOT_TRACK` |
| **Secrets** | `osmen-langflow-db-url` → `LANGFLOW_DATABASE_URL` |
| **After** | `osmen-core-postgres.service`, `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `bash -c 'echo > /dev/tcp/127.0.0.1/7860'` |
| **ReadOnly** | — (not set; Tmpfs=/tmp) |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 10s |
| **Slice** | `user-osmen-services.slice` ⚠️ undefined |
| **MemoryMax** | `2G` |
| **CPUQuota** | `200%` |
| **Merge conflicts** | None |

---

#### `core/osmen-core-nextcloud.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/library/nextcloud:31.0.5-apache` |
| **ContainerName** | `osmen-core-nextcloud` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:8080:80` |
| **Volumes** | `osmen-nextcloud-data.volume:/var/www/html` |
| **Env** | `REDIS_HOST` |
| **Secrets** | `osmen-nextcloud-postgres-host`, `osmen-nextcloud-postgres-db`, `osmen-nextcloud-postgres-user`, `osmen-nextcloud-postgres-password`, `osmen-redis-password` |
| **After** | `osmen-core-postgres.service`, `osmen-core-redis.service`, `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `curl -sf http://127.0.0.1/status.php` |
| **ReadOnly** | `false` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 10s |
| **Slice** | `user-osmen-services.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `200%` |
| **Merge conflicts** | None |

---

#### `core/osmen-core-postgres.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/pgvector/pgvector:pg17` |
| **ContainerName** | `osmen-core-postgres` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:5432:5432` |
| **Volumes** | `osmen-postgres-data.volume:/var/lib/postgresql/data` |
| **Env** | — (none) |
| **Secrets** | `osmen-postgres-password` → `POSTGRES_PASSWORD`, `osmen-postgres-user` → `POSTGRES_USER`, `osmen-postgres-db` → `POSTGRES_DB` |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **Exec** | `postgres -c wal_level=logical -c max_connections=200` |
| **HealthCmd** | ⚠️ **CONFLICT** — HEAD: `pg_isready -U osmen -d osmen` vs origin/main: `/bin/sh -c "pg_isready -U $POSTGRES_USER -d $POSTGRES_DB"` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-core.slice` |
| **MemoryMax** | `1G` |
| **CPUQuota** | `200%` |
| **Merge conflicts** | **2 UNRESOLVED** (Documentation URL, HealthCmd) |

---

#### `core/osmen-core-redis.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/library/redis:7.2.5-alpine` |
| **ContainerName** | `osmen-core-redis` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:6379:6379` |
| **Volumes** | `osmen-redis-data.volume:/data` |
| **Env** | — (none) |
| **Secrets** | `osmen-redis-password` → `REDIS_PASSWORD` |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **Exec** | ⚠️ **CONFLICT** — HEAD: `sh -ceu 'exec redis-server ... "$${REDIS_PASSWORD}"'` vs origin/main: `redis-server ... "${REDIS_PASSWORD}"` |
| **HealthCmd** | ⚠️ **CONFLICT** — HEAD: `sh -ceu 'redis-cli -a "$${REDIS_PASSWORD}" ping \| grep -q PONG'` vs origin/main: `/bin/sh -c "redis-cli -a \"${REDIS_PASSWORD}\" ping \| grep -q PONG"` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-core.slice` |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | **2 UNRESOLVED** (Documentation URL, Exec+HealthCmd block) |

---

#### `core/osmen-core-siyuan.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/b3log/siyuan:v3.6.4` |
| **ContainerName** | `osmen-core-siyuan` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:6806:6806` |
| **Volumes** | `%h/dev/pkm:/siyuan/workspace` |
| **Env** | — (none) |
| **Secrets** | `osmen-siyuan-auth` → `SIYUAN_ACCESS_AUTH_CODE` |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `wget -q -O /dev/null http://127.0.0.1:6806/api/system/version` |
| **ReadOnly** | — (not set; Tmpfs=/tmp) |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-services.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `200%` |
| **Merge conflicts** | None |

---

#### `core/osmen-core.network`

| Field | Value |
|-------|-------|
| **NetworkName** | `osmen-core` |
| **Driver** | `bridge` |
| **Subnet** | ⚠️ **CONFLICT** — HEAD: `10.89.0.0/24` / `10.89.0.1` vs origin/main: `10.88.0.0/24` / `10.88.0.1` |
| **IPv6** | `false` |
| **Merge conflicts** | **1 UNRESOLVED** (Subnet/Gateway) |

---

#### `core/user-osmen-core.slice`

| Field | Value |
|-------|-------|
| **MemoryMax** | `4G` |
| **MemoryHigh** | `3G` |
| **CPUQuota** | `400%` |
| **IOWeight** | `100` |
| **Merge conflicts** | **1 UNRESOLVED** (Documentation URL only) |

---

### MEDIA

---

#### `media/download-stack.pod`

| Field | Value |
|-------|-------|
| **PodName** | `download-stack` |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:9090:9090`, `127.0.0.1:8082:8080`, `127.0.0.1:9696:9696`, `127.0.0.1:8888:8888` |
| **WantedBy** | `default.target` |
| **Merge conflicts** | None |

**Members:** gluetun, prowlarr, qbittorrent, sabnzbd

---

#### `media/osmen-media-gluetun.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/qmcgaw/gluetun:v3.40.2` |
| **ContainerName** | `osmen-media-gluetun` |
| **Pod** | `download-stack.pod` |
| **Network** | — (uses pod network) |
| **PublishPort** | — (ports on pod) |
| **Volumes** | — (none) |
| **Env** | `VPN_SERVICE_PROVIDER`, `VPN_TYPE`, `VPN_ENDPOINT_IP`, `VPN_ENDPOINT_PORT`, `WIREGUARD_PUBLIC_KEY`, `DNS_ADDRESS`, `DOT_IPV6`, `HTTPPROXY` |
| **Secrets** | `osmen-vpn-wireguard-private-key` → `WIREGUARD_PRIVATE_KEY`, `osmen-vpn-wireguard-addresses` → `WIREGUARD_ADDRESSES` |
| **After** | — (none) |
| **Requires** | — (none) |
| **HealthCmd** | `wget -q -O /dev/null http://127.0.0.1:9999` |
| **ReadOnly** | — (not set; Tmpfs=/tmp) |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 10s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `256M` |
| **CPUQuota** | `50%` |
| **Merge conflicts** | None |
| **Notes** | AddCapability=NET_ADMIN, AddDevice=/dev/net/tun, Sysctl=net.ipv6.conf.all.disable_ipv6=1 |

---

#### `media/osmen-media-prowlarr.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/prowlarr:1.35.1` |
| **ContainerName** | `osmen-media-prowlarr` |
| **Pod** | `download-stack.pod` |
| **Network** | — (uses pod network) |
| **PublishPort** | — (port on pod: 9696) |
| **Volumes** | `osmen-prowlarr-config.volume:/config` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — (none) |
| **After** | `osmen-media-gluetun.service` |
| **Requires** | `osmen-media-gluetun.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:9696/ping` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-qbittorrent.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/qbittorrent:5.1.0` |
| **ContainerName** | `osmen-media-qbittorrent` |
| **Pod** | `download-stack.pod` |
| **Network** | — (uses pod network) |
| **PublishPort** | — (port on pod: 9090) |
| **Volumes** | `osmen-qbit-config.volume:/config`, `%h/Downloads:/downloads` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago`, `WEBUI_PORT=9090` |
| **Secrets** | — (none) |
| **After** | `osmen-media-gluetun.service` |
| **Requires** | `osmen-media-gluetun.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:9090` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-sabnzbd.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/sabnzbd:4.5.1` |
| **ContainerName** | `osmen-media-sabnzbd` |
| **Pod** | `download-stack.pod` |
| **Network** | — (uses pod network) |
| **PublishPort** | — (port on pod: 8082→8080) |
| **Volumes** | `osmen-sab-config.volume:/config`, `%h/Downloads:/downloads` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — (none) |
| **After** | `osmen-media-gluetun.service` |
| **Requires** | `osmen-media-gluetun.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:8080` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-bazarr.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/bazarr:1.5.2` |
| **ContainerName** | `osmen-media-bazarr` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:6767:6767` |
| **Volumes** | `osmen-bazarr-config.volume:/config`, `%h/media/plex:/media/plex` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:6767/api` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-kometa.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/kometateam/kometa:v2.3.1` |
| **ContainerName** | `osmen-media-kometa` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | — (none — batch scheduler) |
| **Volumes** | `osmen-kometa-config.volume:/config` |
| **Env** | `TZ=America/Chicago`, `KOMETA_RUN`, `KOMETA_TIME` |
| **Secrets** | — |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `/bin/sh -c "pgrep -f kometa \|\| exit 1"` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 60s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-komga-comics.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/gotson/komga:latest` ⚠️ no version pin |
| **ContainerName** | `osmen-media-komga-comics` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:25600:25600` |
| **Volumes** | `/home/dwill/media/comics:/comics:ro`, `/home/dwill/media/komga-config-comics:/config` |
| **Env** | — |
| **Secrets** | — |
| **After** | — (none — no [Unit] section!) ⚠️ |
| **Requires** | — (none) |
| **HealthCmd** | — (none) ⚠️ |
| **ReadOnly** | — (not set) |
| **PUID/PGID** | — |
| **WantedBy** | — (no [Install] section!) ⚠️ |
| **Restart** | `always` |
| **Slice** | — (none) ⚠️ |
| **MemoryMax** | — (none) ⚠️ |
| **CPUQuota** | — (none) ⚠️ |
| **Merge conflicts** | None |
| **Notes** | Has `AutoUpdate=registry` + `Label=io.containers.autoupdate=registry`. Uses hardcoded `/home/dwill/` path instead of `%h/`. **Malformed** — no [Unit] or [Install] sections, missing resource limits, security settings, health check. |

---

#### `media/osmen-media-lidarr.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/lidarr:3.1.0` |
| **ContainerName** | `osmen-media-lidarr` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:8686:8686` |
| **Volumes** | `osmen-lidarr-config.volume:/config`, `%h/Downloads:/downloads`, `%h/media/music:/media/music` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:8686/ping` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-mylar3.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/mylar3:0.8.1` |
| **ContainerName** | `osmen-media-mylar3` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:8090:8090` |
| **Volumes** | `osmen-mylar3-config.volume:/config`, `%h/Downloads:/downloads`, `%h/media/comics:/media/comics` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:8090` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-plex.container` — **DEPRECATED**

| Field | Value |
|-------|-------|
| **Image** | `docker.io/plexinc/pms-docker:1.43.1` |
| **ContainerName** | `osmen-media-plex` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `32400:32400` (0.0.0.0 — LAN-wide) |
| **Volumes** | `osmen-plex-config.volume:/config`, 5 media bind mounts (Movies, TV, Anime, TV_overflow, Comics) |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | `osmen-plex-claim` → `PLEX_CLAIM` |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `curl -sf http://127.0.0.1:32400/identity` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 10s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `4G` |
| **CPUQuota** | `400%` |
| **Merge conflicts** | None |
| **Notes** | Header says "DEPRECATED — Plex now runs natively via .deb package. Do not deploy." NVIDIA GPU passthrough commented out. |

---

#### `media/osmen-media-radarr.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/radarr:5.21.1` |
| **ContainerName** | `osmen-media-radarr` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:7878:7878` |
| **Volumes** | `osmen-radarr-config.volume:/config`, `%h/Downloads:/downloads`, `%h/media/plex:/media/plex` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:7878/ping` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-readarr.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/readarr:0.4.12-nightly` |
| **ContainerName** | `osmen-media-readarr` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:8787:8787` |
| **Volumes** | `osmen-readarr-config.volume:/config`, `%h/Downloads:/downloads`, `%h/media/books:/media/books` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:8787/ping` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-sonarr.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/linuxserver/sonarr:4.0.14` |
| **ContainerName** | `osmen-media-sonarr` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:8989:8989` |
| **Volumes** | `osmen-sonarr-config.volume:/config`, `%h/Downloads:/downloads`, `%h/media/plex:/media/plex` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:8989/ping` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-media.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media-tautulli.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/tautulli/tautulli:v2.17.0` |
| **ContainerName** | `osmen-media-tautulli` |
| **Pod** | — |
| **Network** | `osmen-media.network` |
| **PublishPort** | `127.0.0.1:8181:8181` |
| **Volumes** | `osmen-tautulli-config.volume:/config` |
| **Env** | `PUID=1000`, `PGID=1000`, `TZ=America/Chicago` |
| **Secrets** | — |
| **After** | `osmen-media-network.service` |
| **Requires** | `osmen-media-network.service` |
| **HealthCmd** | `curl -sf http://127.0.0.1:8181/status` |
| **ReadOnly** | `true` |
| **PUID/PGID** | `1000/1000` |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `media/osmen-media.network`

| Field | Value |
|-------|-------|
| **NetworkName** | `osmen-media` |
| **Driver** | `bridge` |
| **Subnet** | `10.89.1.0/24` |
| **Gateway** | `10.89.1.1` |
| **IPv6** | `false` |
| **Merge conflicts** | None |

---

### LIBRARIAN

---

#### `librarian/osmen-librarian-audiobookshelf.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/advplyr/audiobookshelf:2.21.0` |
| **ContainerName** | `osmen-librarian-audiobookshelf` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:13378:80` |
| **Volumes** | `osmen-audiobookshelf-config.volume:/config`, `osmen-audiobookshelf-metadata.volume:/metadata`, `%h/media/audiobooks:/audiobooks:ro`, `%h/media/podcasts:/podcasts:ro` |
| **Env** | — |
| **Secrets** | — |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:80/healthcheck` |
| **ReadOnly** | — (Tmpfs=/tmp) |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `librarian/osmen-librarian-convertx.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/c4illin/convertx:v0.17.0` |
| **ContainerName** | `osmen-librarian-convertx` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:3000:3000` |
| **Volumes** | `osmen-convertx-data.volume:/app/data` |
| **Env** | — |
| **Secrets** | — |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `curl -sf http://127.0.0.1:3000` |
| **ReadOnly** | — (Tmpfs=/tmp) |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `librarian/osmen-librarian-kavita.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/jvmilazz0/kavita:0.8.6` |
| **ContainerName** | `osmen-librarian-kavita` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `192.168.4.21:5000:5000` ⚠️ bound to specific LAN IP |
| **Volumes** | `osmen-kavita-config.volume:/kavita/config`, `%h/media/books:/books:ro`, `%h/media/comics:/comics:ro`, `%h/media/manga:/manga:ro`, `%h/media/manga-downloads:/manga-downloads:ro` |
| **Env** | — |
| **Secrets** | — |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `curl -sf http://127.0.0.1:5000` |
| **ReadOnly** | — (Tmpfs=/tmp) |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

#### `librarian/osmen-librarian-whisper.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/fedirz/faster-whisper-server:0.6.0-rc.3-cuda` |
| **ContainerName** | `osmen-librarian-whisper` |
| **Pod** | — |
| **Network** | — (none) ⚠️ |
| **PublishPort** | `127.0.0.1:9001:8000` |
| **Volumes** | `osmen-whisper-models.volume:/root/.cache/huggingface` |
| **Env** | `WHISPER__MODEL=large-v3`, `WHISPER__DEVICE=cuda` |
| **Secrets** | — |
| **After** | — (none) |
| **Requires** | — (none) |
| **HealthCmd** | `python3 -c 'import socket; s=socket.socket(); s.connect(("127.0.0.1",8000)); s.close()'` |
| **ReadOnly** | — (disabled for NVIDIA CDI) |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 10s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `4G` |
| **CPUQuota** | `200%` |
| **Merge conflicts** | None |
| **Notes** | AddDevice=nvidia.com/gpu=all. No network — only accessible via host port. |

---

### MONITORING

---

#### `monitoring/osmen-monitoring-grafana.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/grafana/grafana-oss:12.1.0` |
| **ContainerName** | `osmen-monitoring-grafana` |
| **Pod** | — |
| **Network** | — (none) |
| **PublishPort** | `127.0.0.1:3002:3000` |
| **Volumes** | `osmen-grafana-data.volume:/var/lib/grafana`, `%h/dev/OsMEN-OC/config/grafana/provisioning:/etc/grafana/provisioning:ro`, `%h/dev/OsMEN-OC/config/grafana/dashboards:/var/lib/grafana/dashboards:ro` |
| **Env** | `GF_SECURITY_ADMIN_PASSWORD__FILE=/run/secrets/osmen-grafana-admin-password` |
| **Secrets** | `osmen-grafana-admin-password` (type=mount) |
| **After** | `osmen-monitoring-prometheus.service` |
| **Requires** | — (none) |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:3000/api/health` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |
| **Notes** | DISABLED BY DEFAULT — opt-in via P21. Comment says port 3000 conflicts with ConvertX; already remapped to 3002. |

---

#### `monitoring/osmen-monitoring-portall.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/need4swede/portall:2.0.4` |
| **ContainerName** | `osmen-monitoring-portall` |
| **Pod** | — |
| **Network** | — (none) |
| **PublishPort** | `127.0.0.1:3080:8080` |
| **Volumes** | `/run/user/1000/podman/podman.sock:/var/run/docker.sock:ro` |
| **Env** | `DOCKER_HOST=unix:///var/run/docker.sock` |
| **Secrets** | — |
| **After** | — (none) |
| **Requires** | — (none) |
| **HealthCmd** | `nc -z 127.0.0.1 8080` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — (but User=1000:1000) |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `256M` |
| **CPUQuota** | `50%` |
| **Merge conflicts** | None |

---

#### `monitoring/osmen-monitoring-prometheus.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/prom/prometheus:v3.4.0` |
| **ContainerName** | `osmen-monitoring-prometheus` |
| **Pod** | — |
| **Network** | — (none) |
| **PublishPort** | `127.0.0.1:9091:9090` |
| **Volumes** | `osmen-prometheus-data.volume:/prometheus`, `%h/dev/OsMEN-OC/config/prometheus.yml:/etc/prometheus/prometheus.yml:ro` |
| **Env** | — |
| **Secrets** | — |
| **After** | — (none) |
| **Requires** | — (none) |
| **HealthCmd** | `wget -q --spider http://127.0.0.1:9090/-/healthy` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `1G` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |
| **Notes** | DISABLED BY DEFAULT — opt-in via P21. Port remapped 9091→9090 to avoid qBittorrent pod conflict. |

---

#### `monitoring/osmen-monitoring-uptimekuma.container`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/louislam/uptime-kuma:1.23.16` |
| **ContainerName** | `osmen-monitoring-uptimekuma` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:3001:3001` |
| **Volumes** | `osmen-uptimekuma-data.volume:/app/data` |
| **Env** | — |
| **Secrets** | — |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `curl -sf http://127.0.0.1:3001` |
| **ReadOnly** | `true` |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-background.slice` ⚠️ undefined |
| **MemoryMax** | `512M` |
| **CPUQuota** | `100%` |
| **Merge conflicts** | None |

---

### INFERENCE

---

#### `inference/osmen-inference-ollama.container.disabled`

| Field | Value |
|-------|-------|
| **Image** | `docker.io/ollama/ollama:0.9.2` |
| **ContainerName** | `osmen-inference-ollama` |
| **Pod** | — |
| **Network** | `osmen-core.network` |
| **PublishPort** | `127.0.0.1:11434:11434` |
| **Volumes** | `osmen-ollama-models.volume:/root/.ollama` |
| **Env** | — |
| **Secrets** | — |
| **After** | `osmen-core-network.service` |
| **Requires** | `osmen-core-network.service` |
| **HealthCmd** | `/bin/sh -c "wget -q --spider http://127.0.0.1:11434/api/tags \|\| exit 1"` |
| **ReadOnly** | — (not set) |
| **PUID/PGID** | — |
| **WantedBy** | `default.target` |
| **Restart** | `always` / 5s |
| **Slice** | `user-osmen-inference.slice` ⚠️ undefined |
| **MemoryMax** | `16G` |
| **CPUQuota** | `800%` |
| **Merge conflicts** | None |
| **Notes** | DISABLED (file extension .disabled). AddDevice=nvidia.com/gpu=all. |

---

#### `inference/osmen-inference-lmstudio.service`

| Field | Value |
|-------|-------|
| **Type** | `.service` (native systemd, NOT a container) |
| **ExecStart** | `%h/.lmstudio/bin/lms server start --port 1234` |
| **ExecStop** | `%h/.lmstudio/bin/lms server stop` |
| **Env** | `VULKAN_SDK=/usr`, `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json` |
| **After** | — (none) |
| **Requires** | — (none) |
| **Restart** | `on-failure` / 10s |
| **Slice** | `user-osmen-inference.slice` ⚠️ undefined |
| **MemoryMax** | `8G` |
| **CPUQuota** | `400%` |
| **WantedBy** | `default.target` |
| **Merge conflicts** | None |
| **Notes** | Native binary for AMD Vulkan inference. Exposes OpenAI-compatible API on 127.0.0.1:1234. |

---

### VOLUMES

All `.volume` files in `volumes/` are trivial `VolumeName=` declarations. No conflicts.

| File | VolumeName |
|------|-----------|
| `volumes/osmen-audiobookshelf-config.volume` | `osmen-audiobookshelf-config` |
| `volumes/osmen-audiobookshelf-metadata.volume` | `osmen-audiobookshelf-metadata` |
| `volumes/osmen-bazarr-config.volume` | `osmen-bazarr-config` |
| `volumes/osmen-caddy-config.volume` | `osmen-caddy-config` |
| `volumes/osmen-caddy-data.volume` | `osmen-caddy-data` |
| `volumes/osmen-chromadb-data.volume` | `osmen-chromadb-data` |
| `volumes/osmen-convertx-data.volume` | `osmen-convertx-data` |
| `volumes/osmen-grafana-data.volume` | `osmen-grafana-data` |
| `volumes/osmen-kavita-config.volume` | `osmen-kavita-config` |
| `volumes/osmen-kometa-config.volume` | `osmen-kometa-config` |
| `volumes/osmen-langflow-data.volume` | `osmen-langflow-data` |
| `volumes/osmen-nextcloud-data.volume` | `osmen-nextcloud-data` |
| `volumes/osmen-ollama-models.volume` | `osmen-ollama-models` |
| `volumes/osmen-plex-config.volume` | `osmen-plex-config` |
| `volumes/osmen-portall-data.volume` | `osmen-portall-data` |
| `volumes/osmen-postgres-data.volume` | `osmen-postgres-data` |
| `volumes/osmen-prometheus-data.volume` | `osmen-prometheus-data` |
| `volumes/osmen-prowlarr-config.volume` | `osmen-prowlarr-config` |
| `volumes/osmen-qbit-config.volume` | `osmen-qbit-config` |
| `volumes/osmen-radarr-config.volume` | `osmen-radarr-config` |
| `volumes/osmen-redis-data.volume` | `osmen-redis-data` |
| `volumes/osmen-sab-config.volume` | `osmen-sab-config` |
| `volumes/osmen-sonarr-config.volume` | `osmen-sonarr-config` |
| `volumes/osmen-tautulli-config.volume` | `osmen-tautulli-config` |
| `volumes/osmen-uptimekuma-data.volume` | `osmen-uptimekuma-data` |
| `volumes/osmen-whisper-models.volume` | `osmen-whisper-models` |

Plus 3 volumes defined in `media/`:
| File | VolumeName |
|------|-----------|
| `media/osmen-lidarr-config.volume` | `osmen-lidarr-config` |
| `media/osmen-mylar3-config.volume` | `osmen-mylar3-config` |
| `media/osmen-readarr-config.volume` | `osmen-readarr-config` |

---

## ISSUES SUMMARY

### 🔴 Blocking (must fix before deploy)

1. **5 files with unresolved merge conflicts** — chromadb (3), postgres (2), redis (2), network (1), slice (1)
2. **4 missing slice definitions** — `user-osmen-services.slice`, `user-osmen-media.slice`, `user-osmen-background.slice`, `user-osmen-inference.slice`
3. **Komga quadlet is malformed** — no [Unit], no [Install], no resource limits, no security settings, no health check, uses hardcoded paths, unpinned image (`:latest`)

### 🟡 Should fix

4. **Kavita PublishPort bound to specific LAN IP** `192.168.4.21` — will break if IP changes
5. **Plex container marked deprecated** but still present — confusing; should be moved to archive or clearly renamed
6. **Ollama container disabled** (`.disabled` extension) — intentional but worth noting
7. **Grafana/Prometheus "disabled by default"** — no formal disable mechanism (comments only)
8. **Core network subnet conflicts** — HEAD uses `10.89.0.0/24`, origin/main uses `10.88.0.0/24`; media uses `10.89.1.0/24` which overlaps with HEAD's core subnet (different third octet so OK, but both use 10.89.x which could be confusing)
9. **Monitoring containers have no network** — grafana, portall, prometheus only accessible via host ports, not via podman network

### 📊 Totals

- **Container files:** 30 (1 deprecated, 1 disabled)
- **Pod files:** 1
- **Network files:** 2
- **Volume files:** 28 (25 in volumes/ + 3 in media/)
- **Slice files:** 1 (core only — 4 others missing)
- **Service files:** 1 (lmstudio — native)
- **Total files:** 63
