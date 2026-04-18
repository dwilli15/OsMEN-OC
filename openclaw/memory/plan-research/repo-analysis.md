# OsMEN-OC Repository Consistency Audit

**Date:** 2026-04-18  
**Scope:** Full line-by-line analysis of quadlets, symlinks, volumes, scripts, and git diff.

---

## 1. Quadlet Consistency Findings

### CRITICAL ISSUES

#### 1.1 `ReadOnly=true` on containers that write to non-volume paths

| Container | Issue |
|-----------|-------|
| `osmen-core-caddy` | `ReadOnly=true` + writes to `/data` (volume-mounted) + `/config` (volume-mounted). The Caddy process also writes to `/tmp`. **Will likely break** — Caddy needs `/tmp` for temp files. |
| `osmen-core-chromadb` | `ReadOnly=true` but comment says "ReadOnly removed" — **the directive is still present**. ChromaDB writes `/chroma/chroma.log` and `/tmp`. Contradiction between comment and config. |
| `osmen-core-postgres` | `ReadOnly=true` — PostgreSQL writes to `/var/lib/postgresql/data` (volume) AND `/var/run/postgresql` (socket dir), `/tmp`. **Will break**. |
| `osmen-core-redis` | `ReadOnly=true` — Redis writes to `/data` (volume) but also needs `/tmp`. Risky. |
| `osmen-core-gateway` | `ReadOnly=true` + mounts `%h/.task:/root/.task` (writable). Comment says Taskwarrior data — but ReadOnly blocks writes. **Contradiction**. |
| `osmen-core-bazarr` | `ReadOnly=true` — Bazarr writes temp files during subtitle download. Risky. |
| `osmen-media-lidarr` | `ReadOnly=true` — *arr services write to their config dirs. Config is volume-mounted, but temp dirs aren't. Risky. |
| `osmen-media-mylar3` | `ReadOnly=true` — same issue. |
| `osmen-media-radarr` | `ReadOnly=true` — same issue. |
| `osmen-media-readarr` | `ReadOnly=true` — same issue. |
| `osmen-media-sonarr` | `ReadOnly=true` — same issue. |
| `osmen-media-plex` | `ReadOnly=true` — Plex writes metadata to `/config` (volume) but also to `/transcode` and `/tmp`. The container is DEPRECATED anyway. |
| `osmen-media-sabnzbd` | `ReadOnly=true` — writes temp files during download/extract. **Will break**. |
| `osmen-media-prowlarr` | `ReadOnly=true` — same *arr issue. |
| `osmen-media-qbittorrent` | `ReadOnly=true` — needs `/tmp` for torrent staging. **Will break**. |
| `osmen-media-tautulli` | `ReadOnly=true` — writes logs and cache. Risky. |
| `osmen-monitoring-grafana` | `ReadOnly=true` — Grafana writes to `/var/lib/grafana` (volume) but also needs writable temp/plugin dirs. |
| `osmen-monitoring-uptimekuma` | `ReadOnly=true` — writes logs, uploads, database. **Will break**. |
| `osmen-monitoring-portall` | `ReadOnly=true` — writes logs. Risky. |
| `osmen-monitoring-prometheus` | `ReadOnly=true` — writes WAL segments to `/prometheus` (volume) but needs `/tmp`. Risky. |
| `osmen-media-kometa` | `ReadOnly=true` — batch process writes logs and temp files. Risky. |

**Note:** If Podman's `ReadOnly=true` behavior allows tmpfs on `/tmp` automatically (some container runtimes do), some of these may work. But the comment on chromadb explicitly says ReadOnly was removed for this reason, suggesting it does NOT work — meaning all other ReadOnly containers may be broken.

#### 1.2 Duplicate `HealthCmd` directives

| Container | Issue |
|-----------|-------|
| `osmen-core-chromadb` | Two `HealthCmd=` lines — Podman Quadlet will use **last one wins**, making the first useless. |
| `osmen-core-postgres` | Two `HealthCmd=` lines — same issue. |
| `osmen-core-redis` | Two `HealthCmd=` lines — same issue. |

#### 1.3 `osmen-media-komga-comics` is malformed

- Missing `[Unit]` section (no `After=`/`Requires=` dependencies)
- Missing `Description=` header comment
- Uses `:latest` tag (floating, not pinned)
- Uses **hardcoded absolute path** `/home/dwill/media/comics` instead of `%h/media/comics`
- Uses **hardcoded absolute path** `/home/dwill/media/komga-config-comics` instead of a named volume
- `AutoUpdate=registry` with `:latest` — will auto-update on every podman pull, risky for data integrity
- No health check
- No `ReadOnly` setting (defaults to false — fine)

#### 1.4 `osmen-librarian-whisper` — missing network and unit deps

- No `[Unit]` section at all (no `After=`/`Requires=`)
- No `Network=` — runs on default podman network, isolated from other services
- Publishes to `127.0.0.1:9001:8000` but with no network attachment, only accessible via published port

#### 1.5 `osmen-librarian-kavita` — LAN exposure (uncommitted change)

- Changed from `127.0.0.1:5000:5000` to `192.168.4.21:5000:5000`
- Exposes Kavita to entire LAN subnet — intentional for tablet/phone access but a security widening

#### 1.6 PUID/PGID inconsistency

| Container | PUID | PGID | Notes |
|-----------|------|------|-------|
| `osmen-media-prowlarr` | 1000 | 1000 | Only container with explicit PUID/PGID |
| All others | _(none)_ | _(none)_ | Rely on Podman's rootless UID mapping |

Most linuxserver.io images expect PUID/PGID. Only Prowlarr sets them. Sonarr, Radarr, Lidarr, Sabnzbd, Bazarr, Mylar3, Readarr are all linuxserver images but lack PUID/PGID — they'll default to root inside the container.

#### 1.7 Port conflict: Prometheus vs qBittorrent pod

- `download-stack.pod` publishes `127.0.0.1:9090:9090` (qBittorrent web UI)
- `osmen-monitoring-prometheus` publishes `127.0.0.1:9091:9090` (remapped to avoid conflict)
- Comment acknowledges the conflict — **currently resolved** by remapping Prometheus to 9091

#### 1.8 Port conflict: Grafana vs ConvertX

- `osmen-librarian-convertx`: `127.0.0.1:3000:3000`
- `osmen-monitoring-grafana`: `127.0.0.1:3002:3000` (remapped)
- Comment acknowledges — **currently resolved** by remapping Grafana to 3002

#### 1.9 Image version summary

| Pinned ✅ | Floating ❌ |
|-----------|-------------|
| caddy:2.9-alpine | komga:**:latest** |
| chroma:0.5.23 | |
| langflow:1.3.1 | |
| nextcloud:31.0.5-apache | |
| pgvector:pg17 | |
| redis:7.2.5-alpine | |
| siyuan:v3.6.4 | |
| bazarr:1.5.2 | |
| gluetun:v3.40.2 | |
| kometa:v2.3.1 | |
| lidarr:3.1.0 | |
| mylar3:0.8.1 | |
| plex:1.43.1 | |
| prowlarr:1.35.1 | |
| qbittorrent:5.1.0 | |
| radarr:5.21.1 | |
| readarr:0.4.12-nightly | |
| sabnzbd:4.5.1 | |
| sonarr:4.0.14 | |
| tautulli:v2.17.0 | |
| audiobookshelf:2.21.0 | |
| convertx:v0.17.0 | |
| kavita:0.8.6 | |
| whisper-server:0.6.0-rc.3-cuda | |
| grafana:12.1.0 | |
| portall:2.0.4 | |
| prometheus:v3.4.0 | |
| uptime-kuma:1.23.16 | |

Only `komga:latest` is floating.

---

## 2. Symlink Health

**All 64 symlinks in `~/.config/containers/systemd/` resolve to existing files.** ✅

Zero broken symlinks detected.

**Note:** 3 symlinks point to `quadlets/media/*.volume` files (lidarr, mylar3, readarr configs) rather than the canonical `quadlets/volumes/` location. These work but violate the organizational convention.

---

## 3. Volume Cross-Reference Matrix

### Volume files by location

**`quadlets/volumes/`** (27 files):
osmen-audiobookshelf-config, osmen-audiobookshelf-metadata, osmen-bazarr-config, osmen-caddy-config, osmen-caddy-data, osmen-chromadb-data, osmen-convertx-data, osmen-grafana-data, osmen-kavita-config, osmen-kometa-config, osmen-langflow-data, osmen-nextcloud-data, osmen-ollama-models, osmen-plex-config, osmen-portall-data, osmen-postgres-data, osmen-prometheus-data, osmen-prowlarr-config, osmen-qbit-config, osmen-radarr-config, osmen-redis-data, osmen-sab-config, osmen-sonarr-config, osmen-tautulli-config, osmen-uptimekuma-data, osmen-whisper-models

**`quadlets/media/`** (3 files, non-standard location):
osmen-lidarr-config, osmen-mylar3-config, osmen-readarr-config

### Container → Volume mapping

| Container | Volumes Used |
|-----------|-------------|
| osmen-core-caddy | osmen-caddy-data ✅, osmen-caddy-config ✅ |
| osmen-core-chromadb | osmen-chromadb-data ✅ |
| osmen-core-postgres | osmen-postgres-data ✅ |
| osmen-core-redis | osmen-redis-data ✅ |
| osmen-core-nextcloud | osmen-nextcloud-data ✅ |
| osmen-core-langflow | osmen-langflow-data ✅ |
| osmen-core-siyuan | _(bind mount only)_ |
| osmen-core-gateway | _(bind mount only)_ |
| osmen-media-bazarr | osmen-bazarr-config ✅ |
| osmen-media-kometa | osmen-kometa-config ✅ |
| osmen-media-lidarr | osmen-lidarr-config ✅ (in media/) |
| osmen-media-mylar3 | osmen-mylar3-config ✅ (in media/) |
| osmen-media-readarr | osmen-readarr-config ✅ (in media/) |
| osmen-media-radarr | osmen-radarr-config ✅ |
| osmen-media-sonarr | osmen-sonarr-config ✅ |
| osmen-media-prowlarr | osmen-prowlarr-config ✅ |
| osmen-media-qbittorrent | osmen-qbit-config ✅ |
| osmen-media-sabnzbd | osmen-sab-config ✅ |
| osmen-media-plex | osmen-plex-config ✅ |
| osmen-media-tautulli | osmen-tautulli-config ✅ |
| osmen-media-gluetun | _(none)_ |
| osmen-librarian-audiobookshelf | osmen-audiobookshelf-config ✅, osmen-audiobookshelf-metadata ✅ |
| osmen-librarian-convertx | osmen-convertx-data ✅ |
| osmen-librarian-kavita | osmen-kavita-config ✅ |
| osmen-librarian-whisper | osmen-whisper-models ✅ |
| osmen-monitoring-grafana | osmen-grafana-data ✅ |
| osmen-monitoring-prometheus | osmen-prometheus-data ✅ |
| osmen-monitoring-uptimekuma | osmen-uptimekuma-data ✅ |
| osmen-monitoring-portall | osmen-portall-data ✅ |
| osmen-media-komga-comics | _(hardcoded paths, no named volume)_ |

### Orphaned volumes (defined but never referenced)

| Volume | Status |
|--------|--------|
| osmen-ollama-models | **ORPHANED** — no container references it. Likely for a planned Ollama container that doesn't exist yet. |

### Missing volumes (no issues detected)

All referenced volumes have corresponding `.volume` files.

---

## 4. Script Issues

### `scripts/media/transfer/movie_transfer.sh`
- **Path change:** Now uses `/mnt/plex/Media/Movies` (env-overridable) instead of old hardcoded `/run/media/dwill/plex/Media/Movies`. This matches the fstab entries added on 2026-04-16. ✅ Good improvement.
- **Changed from `mv` to `cp -n`** — safer, won't delete source. ✅ Good.
- **No container name references** — operates on filesystem paths only. Clean.

### `scripts/media/acquisition/mangadex_dl.py`, `scripts/media/acquisition/monitor_downloads.py`, etc.
- No container name references found in any scripts.
- No hardcoded API keys in script files (credentials are in SABnzbd/Prowlarr configs, accessed at runtime).

### Stale scripts in `/tmp` (from memory notes)
- `/tmp/queue_dc_v3.py`, `/tmp/queue_dc_v4.py`, `/tmp/bulk_manga_download.py`, `/tmp/bulk_manga_restart.py`
- These are in `/tmp` — will be lost on reboot. Not repo issues but worth noting.

---

## 5. Git Diff Assessment

### Quadlet changes (should be committed)

| File | Change | Assessment |
|------|--------|------------|
| `quadlets/media/download-stack.pod` | Added port 9696 (Prowlarr) + 8888 (HTTP proxy) | **Commit.** Fixes missing Prowlarr port. |
| `quadlets/media/osmen-media-gluetun.container` | Added `HTTPPROXY=on` | **Commit.** Enables HTTP proxy feature. |
| `quadlets/media/osmen-media-prowlarr.container` | Moved to download-stack pod (Pod=, removed Network=) | **Commit.** Fixes VPN routing for Prowlarr. |
| `quadlets/librarian/osmen-librarian-kavita.container` | LAN exposure + manga-downloads volume | **Commit with caution.** Intentional for device access. |

### Script changes (should be committed)

| File | Change | Assessment |
|------|--------|------------|
| `scripts/media/transfer/movie_transfer.sh` | Major rewrite: env-var paths, cp instead of mv, sanitize_title | **Commit.** Clear improvement. |

### Doc changes (should be committed)

| File | Change | Assessment |
|------|--------|------------|
| `docs/media/transfer-protocols.md` | Updated paths from `/media/plex/*` to `/mnt/*` | **Commit.** Matches new fstab layout. |

### Memory/state files (should be committed or gitignored)

| File | Change | Assessment |
|------|--------|------------|
| `openclaw/memory/2026-04-16.md` | **Massive rewrite** — entire file replaced with manga/comics session notes. Original content (memory maintenance, cron fixes, P13-P22, 859 tests, etc.) appears **LOST** from this file. | ⚠️ **Original content may need recovery from git history (`git show HEAD:openclaw/memory/2026-04-16.md`)** |
| `openclaw/memory/.dreams/*` | Auto-generated recall data | Normal operation, commit. |
| `openclaw/HEARTBEAT.md` | Changed from template to manga check task | **Commit.** Intentional. |
| `openclaw/auditor/models.json` | Added `apiKey` for codex | **Commit.** Configuration update. |

### Critical concern: `openclaw/memory/2026-04-16.md`

The git diff shows the **entire original content was replaced** with manga session notes. The original had critical operational records (memory maintenance implementation, 859 test results, cron fix root cause, RustDesk notes, model fallback disaster, P13-P22 completion status, fstab entries, PR #46 info). This looks like an accidental overwrite — the new content appears duplicated in the file (the manga session is written twice).

---

## 6. Top 10 Most Dangerous Inconsistencies

1. **`ReadOnly=true` on 20+ containers** — Most of these likely break silently or fail at startup. The chromadb comment explicitly says ReadOnly was removed for write reasons, but the directive remains. If containers are currently running, they may be running without ReadOnly (started before it was added) or failing to start.

2. **`openclaw/memory/2026-04-16.md` content loss** — Critical operational history replaced with duplicate manga session notes. Recover from `git show HEAD:openclaw/memory/2026-04-16.md`.

3. **`osmen-media-komga-comics.container` is malformed** — No unit section, `:latest` tag, hardcoded paths, no health check. Will auto-update unpredictably.

4. **Duplicate `HealthCmd` on chromadb, postgres, redis** — Last one wins silently, making the first directive dead code.

5. **PUID/PGID missing on 6 linuxserver containers** — Sonarr, Radarr, Lidarr, Sabnzbd, Bazarr, Mylar3, Readarr all run as root inside the container instead of the user's UID.

6. **3 volume files in wrong directory** — `osmen-lidarr-config`, `osmen-mylar3-config`, `osmen-readarr-config` are in `quadlets/media/` instead of `quadlets/volumes/`. Works but violates convention.

7. **Orphaned `osmen-ollama-models` volume** — No container references it. Either delete or create the Ollama container.

8. **`osmen-librarian-whisper` has no network** — Runs on default network, isolated from all other services. Can't be reached by other containers via DNS.

9. **Kavita exposed to LAN (192.168.4.21)** — Uncommitted change widens attack surface. Intentional for tablet access but should be documented.

10. **Quadlet vs manual podman mismatch** — Memory notes indicate download stack containers were recreated with `podman run` not quadlet, meaning systemd units may be stale and won't survive reboot.
