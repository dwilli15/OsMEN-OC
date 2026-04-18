# Recon 02: Systemd + Quadlet Ownership Truth

**Date:** 2026-04-18 03:25 CDT
**Auditor:** Recon Agent 02

## Summary

All 30 quadlet container files exist with valid symlinks, but **3 have git merge conflicts** (chromadb, postgres, redis). After `daemon-reload`, **zero quadlet-generated container units are listed** — only `osmen-media-komga-comics.service` appears (and has no corresponding `.container` file). **All 5 running containers are orphaned** — their quadlet services are inactive.

## Critical Findings

1. **3 quadlet files have merge conflicts:** osmen-core-chromadb, osmen-core-postgres, osmen-core-redis — these will generate broken systemd units
2. **Running containers are NOT managed by quadlet** — all quadlet services are inactive despite containers running
3. **`osmen-core-postgres.service` and `osmen-core-redis.service` show as `not-found`** in `list-units` — quadlet cannot parse their conflicted `.container` files
4. **`osmen-media-komga-comics.service` is enabled but has no `.container` file** in the quadlet directory — orphaned unit file
5. **`podman-auto-update.timer` is disabled** — auto-updates not active
6. **Linger=yes** — user services survive logout ✓

## Running Containers vs Systemd Ownership

| Container | Quadlet File | Service Status | Verdict |
|---|---|---|---|
| 5b49464c15de-infra | N/A (no matching quadlet) | N/A | **ORPHAN** — no quadlet definition at all |
| osmen-media-gluetun | YES, clean | inactive | **ORPHAN** — running outside quadlet |
| osmen-media-sabnzbd | YES, clean | inactive | **ORPHAN** — running outside quadlet |
| osmen-media-qbittorrent | YES, clean | inactive | **ORPHAN** — running outside quadlet |
| osmen-media-prowlarr | YES, clean | inactive | **ORPHAN** — running outside quadlet |

## Full Quadlet Container Matrix

| Quadlet Container | Target Exists | Merge Conflicts | Unit Loaded | Unit Active | Verdict |
|---|---|---|---|---|---|
| osmen-core-caddy | YES | NO | NO | NO | Defined but unused |
| osmen-core-chromadb | YES | **YES** | NO | NO | **BROKEN — merge conflict** |
| osmen-core-gateway | YES | NO | NO | NO | Defined but unused |
| osmen-core-langflow | YES | NO | NO | NO | Defined but unused |
| osmen-core-nextcloud | YES | NO | NO | NO | Defined but unused |
| osmen-core-postgres | YES | **YES** | not-found | NO | **BROKEN — merge conflict, unit not generated** |
| osmen-core-redis | YES | **YES** | not-found | NO | **BROKEN — merge conflict, unit not generated** |
| osmen-core-siyuan | YES | NO | NO | NO | Defined but unused |
| osmen-librarian-audiobookshelf | YES | NO | NO | NO | Defined but unused |
| osmen-librarian-convertx | YES | NO | NO | NO | Defined but unused |
| osmen-librarian-kavita | YES | NO | NO | NO | Defined but unused |
| osmen-librarian-whisper | YES | NO | NO | NO | Defined but unused |
| osmen-media-bazarr | YES | NO | NO | NO | Defined but unused |
| osmen-media-gluetun | YES | NO | NO | NO | Defined but running as orphan |
| osmen-media-kometa | YES | NO | NO | NO | Defined but unused |
| osmen-media-lidarr | YES | NO | NO | NO | Defined but unused |
| osmen-media-mylar3 | YES | NO | NO | NO | Defined but unused |
| osmen-media-plex | YES | NO | NO | NO | Defined but unused |
| osmen-media-prowlarr | YES | NO | NO | NO | Defined but running as orphan |
| osmen-media-qbittorrent | YES | NO | NO | NO | Defined but running as orphan |
| osmen-media-radarr | YES | NO | NO | NO | Defined but unused |
| osmen-media-readarr | YES | NO | NO | NO | Defined but unused |
| osmen-media-sabnzbd | YES | NO | NO | NO | Defined but running as orphan |
| osmen-media-sonarr | YES | NO | NO | NO | Defined but unused |
| osmen-media-tautulli | YES | NO | NO | NO | Defined but unused |
| osmen-monitoring-grafana | YES | NO | NO | NO | Defined but unused |
| osmen-monitoring-portall | YES | NO | NO | NO | Defined but unused |
| osmen-monitoring-prometheus | YES | NO | NO | NO | Defined but unused |
| osmen-monitoring-uptimekuma | YES | NO | NO | NO | Defined but unused |

## Orphaned Unit: osmen-media-komga-comics.service

- Listed in `list-unit-files` as `enabled`
- **No corresponding `.container` file** exists in `~/.config/containers/systemd/`
- Shows as loaded in `list-units` with description "Podman container-osmen-media-komga-comics.service"
- Orphaned unit file — no quadlet source

## Linger

`Linger=yes` — user systemd services persist after logout. ✓

## Timers

All 8 OsMEN maintenance timers active and firing. No `podman-auto-update.timer` (disabled).

## daemon-reload

Completed with no errors.
