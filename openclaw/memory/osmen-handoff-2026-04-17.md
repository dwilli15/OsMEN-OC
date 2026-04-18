# OsMEN-OC Media Pipeline Handoff
**Date**: 2026-04-17 22:00 CDT
**Author**: OpenClaw main session (glm-5.1, multiple sessions over 48h)
**Purpose**: Clean handoff for a new agent to take over the OsMEN media pipeline

---

## Executive Summary

The OsMEN media acquisition pipeline is **partially functional** with several critical broken components. An expert agent coming in needs to fix **3 blockers** before any further automated progress is possible. Two background processes are running and should be monitored.

**What works**: MangaDex downloads, SABnzbd/Eweka Usenet downloads, NZBgeek API search
**What's broken**: Prowlarr search API, qBittorrent auth, VPN split routing for torrents
**What's running**: MangaDex bulk download (PID 193847), Yen.Press file copy (may have finished)

---

## Current System State

### Storage
| Drive | Mount | Used | Free | Notes |
|---|---|---|---|---|
| nvme0n1 (913G ext4) | `/` | 527G | 340G | OsMEN system + containers |
| sdc2 (932G NTFS) | `/run/media/dwill/Other_Media` | 653G | 279G | Comics + Manga + Media |

### Media Libraries
| Library | Location | Size | Files | Status |
|---|---|---|---|---|
| DC Comics | `/run/media/dwill/Other_Media/Media/Other/Comics/DC/` | 135G | 3,800 CBZ | ✅ Complete |
| Manga | `/run/media/dwill/Other_Media/Manga/` | 184G | 94 series dirs | 🔄 Downloading |

### Container Status
| Container | Status | Port | Notes |
|---|---|---|---|
| osmen-media-gluetun | Up | — | VPN (Privado, Amsterdam) |
| osmen-media-sabnzbd | Up | 8082 | ✅ Working, Eweka connected |
| osmen-media-prowlarr | Up | 9696 | ❌ Search API broken |
| osmen-media-qbittorrent | Up | 9090 | ❌ Auth broken |
| osmen-librarian-kavita | Exited | 5000 | Was running earlier |
| osmen-media-komga-comics | Exited | — | Comics reader |
| osmen-media-flaresolverr | Exited | 8191 | Cloudflare bypass |

**⚠️ Containers keep dying** — all download containers (SABnzbd, Prowlarr, qBittorrent) were found exited on 4/17 ~21:00 CDT and had to be manually restarted. Root cause unknown (possibly OOM or gluetun VPN dropout).

### SABnzbd Details
- **Port**: 8082 (container 8080 → host 8082)
- **API key**: `28f95b5a838e4421af5d32dfaa58303d`
- **History**: 1061 items, 129GB total
- **Eweka Usenet**: Connected and working (news.eweka.nl:563 SSL, 50 connections)
- **2 failed downloads**: SAO Phantom Bullet Vol.04, SAO Project Alicization Vol.05 (missing articles)
- **Config volume**: `~/.local/share/containers/storage/volumes/osmen-sab-config.volume/_data/`
- **Complete dir** (inside container): `/config/Downloads/complete/`
- **Host path for complete dir**: Above volume path + `Downloads/complete/`
- **1037 total items** in complete dir (DC comics + manga + misc)

### NZBgeek API
- **API key**: `TvhZpWlqHU7ekUND5ShYVWQvRldQ5FIB`
- **Base URL**: `https://api.nzbgeek.info/api`
- **Working**: ✅ Returns results for comics, manga volumes
- **Caveat**: Blocks Python default User-Agent (403) — use `Mozilla/5.0 SABnzbd/4.5.1`
- **Manga availability**: Good for VIZ/Yen Press/Kodansha digital volumes, poor for individual manga chapters

---

## 🚨 THREE CRITICAL BLOCKERS

### Blocker 1: Prowlarr Search API Dead
**Symptom**: `curl http://localhost:9696/api/v1/search?query=anything` returns empty string (not even empty JSON)
**Duration**: Broken for 48+ hours across multiple container restarts
**Logs**: Repeated `HealthCheckService.cs:line 162` stack traces
**What was tried**: Container restart (multiple times), no fix
**What to try**:
1. Check Prowlarr logs: `podman logs osmen-media-prowlarr --tail 50`
2. Try Prowlarr web UI at `http://127.0.0.1:9696/` — may need browser login
3. Check if indexers are still configured (NZBgeek should be there)
4. Nuclear option: delete Prowlarr config volume, recreate from scratch
5. Config volume: `~/.local/share/containers/storage/volumes/osmen-prowlarr-config.volume/_data/`

### Blocker 2: qBittorrent Authentication Broken
**Symptom**: All API login attempts return "Fails." or "Forbidden", IP gets banned after ~5 attempts
**Duration**: Broken since initial setup ~48h ago
**What was tried**:
- Password `Dw8533Dw` (supposedly set via temp password flow) — rejected
- Removing PBKDF2 hash from config — rejected
- Adding new PBKDF2 hash for "adminadmin" — rejected
- `bypass_local_auth=true` in config — doesn't help
**Config volume**: `~/.local/share/containers/storage/volumes/osmen-qbit-config.volume/_data/qBittorrent/qBittorrent.conf`
**What to try**:
1. **Browser login** at `http://127.0.0.1:9090/` — may show first-run password prompt
2. Stop container, delete PBKDF2 lines from config, restart — qBittorrent generates temp password in logs
3. `podman logs osmen-media-qbittorrent 2>&1 | grep -i password` for temp password
4. Once logged in, set a known password and verify API access works

### Blocker 3: VPN Blocks Torrent Tracker Access
**Symptom**: qBittorrent can't reach torrent trackers through gluetun VPN
**Fix needed**: Add `FIREWALL_OUTBOUND_SUBNETS` env var to gluetun config to allow local network access
**Specifically**: Need to allow qBittorrent to reach both the internet (for trackers) AND local services (for FlareSolverr)
**Config**: Gluetun container env vars or quadlet file

---

## Manga Download Pipeline — Detailed Status

### Must-Have Series (for 13yo girl)
| Series | Status | Files | Size | Source |
|---|---|---|---|---|
| Apothecary Diaries | ✅ | 15 CBZ + 21 alt | 856M + 91M | SABnzbd + MangaDex |
| Ancient Magus' Bride | ✅ | 114 CBZ | 1.5G | MangaDex |
| Sword Art Online | ✅ | 743 files | 15G | SABnzbd (Yen Press) |
| **SPY×FAMILY** | **❌ EMPTY** | 0 | 0 | Not available anywhere |

### SPY×FAMILY — Why It's Missing
- **MangaDex**: External-only (links to MangaPlus/VIZ)
- **NZBgeek**: 2,756 results but ALL are anime episodes, zero manga volumes
- **Needs**: Torrent download via Nyaa.si or similar, or manual download
- **Blocked by**: qBittorrent auth (Blocker 2) and VPN routing (Blocker 3)

### Current Manga Library (94 series, 184GB)
Top series by size:
- Sword Art Online (Official) — 743 files, 15G
- Naruto Digital Color Raw v01-v72 — 72 vols, 17G
- Konosuba — 17G
- The Ancient Magus' Bride — 114 files, 1.5G
- Attack on Titan v01-34 — 34 files, 3.7G
- Fire Force v01-30 — 30 files, 1.8G
- My Hero Academia v01-31 — 31 files, 1.4G
- Vinland Saga v01-25 — 25 files, 2.5G
- Berserk v01-40 — 40 files, 3.3G
- Fullmetal Alchemist v01-27 — 27 files, 918M
- Demon Slayer v01-23 — 23 files, 1.1G
- Kaguya-sama v01-23 — 23 files, 1.1G
- Apothecary Diaries — 15 files, 856M

Plus: Goblin Slayer, Horimiya, Overlord, No Game No Life, Re:Zero, Silent Witch, Komi-san, Mob Psycho, Death Note, Yotsuba, Dr. Stone, Jujutsu Kaisen, Dandadan (empty), Tongari Boushi (empty), and ~30 more.

### Background Processes
1. **MangaDex bulk download** (PID 193847)
   - Script: `/tmp/bulk_manga_restart.py`
   - Using: `/home/dwill/dev/OsMEN-OC/scripts/media/acquisition/mangadex_dl.py`
   - 72 titles queued, on title ~13/72 as of 22:00 CDT
   - Log: `/tmp/manga-bulk-dl.log`
   - Some titles timeout (5min limit), some are external-only
   - Will run for several more hours

2. **Yen.Press file copy** (PID 120616) — may have finished
   - Was copying 104 Yen.Press dirs from SABnzbd to manga library
   - 48GB total, very slow on NTFS
   - Log: `/tmp/copy_manga.log`

### Yen.Press Content in SABnzbd (104 volumes)
Located at: `~/.local/share/containers/storage/volumes/osmen-sab-config.volume/_data/Downloads/complete/Yen.Press-*`
- All are PDF format (BitBook/eBook releases), not CBZ
- Series include: Goblin Slayer, Konosuba, Overlord, Horimiya, Sword Art Online (many sub-series), and more
- Some were already copied to manga library during earlier sessions
- Files are password-protected 7zip archives (SABnzbd handles auto-extraction with known passwords)

---

## DC Comics — Complete

**Status**: ✅ Done. 3,800 CBZ files across 1,253 series folders, 135GB.
**Location**: `/run/media/dwill/Other_Media/Media/Other/Comics/DC/`
**Details**: 
- Started with 646 series, cross-referenced against Flashpoint+ bibliography
- 28 truly missing series identified, 23/28 acquired via Eweka Usenet
- Remaining 5 are extremely rare miniseries with no Usenet availability
- CBR→CBZ conversion done (614 converted, 16 errors)
- 34 Komga reading order lists created

---

## DC Comics NZB Staging Files (may be gone from /tmp)
- `/tmp/dc-nzbs-staging/` — 215 individual issue NZBs
- `/tmp/dc-nzbs/` — 12 TPB NZBs
- `/tmp/dc-nzbs-retry/` — 959 NZBs from retry search
- All likely deleted by now (tmpfs cleanup)

---

## Key Credentials

| Service | Credential | Notes |
|---|---|---|
| SABnzbd API | `28f95b5a838e4421af5d32dfaa58303d` | Works on port 8082 |
| SABnzbd Eweka | User: `e0930d48f5d59774`, Pass: `Dw8533Dw` | news.eweka.nl:563 SSL |
| NZBgeek API | `TvhZpWlqHU7ekUND5ShYVWQvRldQ5FIB` | Works, block Python UA |
| Kavita | `osmen` / `Oc!8533!Oc` | Re-registered 4/17 |
| qBittorrent | `admin` / `Dw8533Dw`? | BROKEN — doesn't work |

---

## Container Architecture Notes

### Download Stack Pod
All 4 download containers share a pod created via `podman run` (NOT quadlet):
- `osmen-media-gluetun` — VPN (Privado)
- `osmen-media-sabnzbd` — Usenet client
- `osmen-media-qbittorrent` — Torrent client
- `osmen-media-prowlarr` — Indexer aggregator

Ports: 9090 (qBit), 8082 (SAB), 9696 (Prowlarr)

**⚠️ Quadlet files at `~/.config/containers/systemd/` may be stale** — containers were recreated manually, not from quadlets.

### Config Volume Paths
All under `~/.local/share/containers/storage/volumes/`:
- `osmen-sab-config.volume/_data/` — SABnzbd config + downloads
- `osmen-prowlarr-config.volume/_data/` — Prowlarr config
- `osmen-qbit-config.volume/_data/` — qBittorrent config
- `systemd-osmen-qbit-config/_data/` — alt qBit config (stale?)

---

## Scripts in Repo
- `/home/dwill/dev/OsMEN-OC/scripts/media/acquisition/mangadex_dl.py` — MangaDex downloader (WORKING)
  - Usage: `python3 mangadex_dl.py "<title>" [output_dir] [max_chapters]`
  - Downloads chapters as CBZ files
  - Skips external-only chapters automatically

All other scripts were in `/tmp/` and are gone. Key ones that need recreation:
- Bulk manga download orchestrator
- NZBgeek search + SABnzbd queue script
- DC comics post-processor (CBR→CBZ, series organizer)
- Komga/Kavita library management scripts

---

## Recommended Priority Order for Next Agent

1. **Fix qBittorrent auth** (browser login → set password → verify API)
2. **Fix Prowlarr** (check logs → maybe nuke config → reconfigure indexers)
3. **Download SPY×FAMILY** via qBittorrent torrents (Nyaa.si search)
4. **Fix VPN split routing** for torrent tracker access
5. **Monitor MangaDex bulk download** (check `/tmp/manga-bulk-dl.log`)
6. **Post-process remaining Yen.Press content** into manga library
7. **Clean up SABnzbd complete dir** — 1037 items, mostly DC comics already moved
8. **Start Kavita** and verify manga library scans correctly
9. **Restart Komga** and verify DC comics library
10. **Update TaskWarrior** with completion notes and close completed tasks

---

## TaskWarrior State (72 tasks)
See full list in `task list` output. Key tasks:

### Comics/Manga Tasks (active)
- **#60** (H): Manga Library Setup — bulk download 299 titles
- **#65**: COMICS-019 — Manga download running (218 series from MangaDex)
- **#69**: COMICS-021 — Komga library rescan + dedup after imports
- **#66**: COMICS-024 — BLOCKED: VPN blocks torrent tracker access
- **#67**: COMICS-028 — BLOCKED: VPN blocks FlareSolverr access
- **#68**: COMICS-018 — DC comic gap audit
- **#70**: COMICS-029 — Manga torrent downloads from Nyaa.si
- **#59**: COMICS-015 — Final verification all comics indexed
- **#61-64**: Manga subtasks (download, post-process, verify, document)

### Handoff Tasks
- **#41**: OsMEN-OC Platform Handoff (this document supersedes)
- **#40**: Previous handoff doc
- **#42**: Baseline repos — prune branches, sync main

### Non-comics Tasks
- 39 osmen.install.* tasks (bridge tests, Nextcloud, calendar, FFXIV, etc.)
- 6 osmen.maint tasks (SMART checks, encryption)
- 8 osmen.roadmap.acp tasks (external agent orchestration)
- 6 osmen.roadmap.devx tasks (agent cleanup)
- 8 osmen.dashboard.homepage tasks (Homepage widget setup)
- 6 osmen.media.pipeline tasks (Lidarr, Readarr, Bazarr, etc.)

---

## Known Gotchas

1. **SABnzbd history endpoint**: Returns `{"history":{"slots":[...]}}` not `{"history":[...]}` — use `.history.slots` in jq
2. **SABnzbd addurl**: Needs POST, not GET, when URL contains `&`
3. **NZBgeek blocks Python UA**: Use `Mozilla/5.0 SABnzbd/4.5.1` header
4. **Yen.Press downloads**: Nested password-protected 7zip — SABnzbd auto-extracts but reports "Unpack nesting too deep" (files are fine)
5. **NTFS filesystem**: Slow for large file operations, no hardlinks across devices
6. **Container pod networking**: All download containers share pod network through gluetun VPN
7. **Container lifecycle**: Containers die unexpectedly — possibly OOM or VPN dropout. Need monitoring.
8. **/tmp is tmpfs**: All scripts in /tmp are lost on reboot. Store persistent scripts in the repo at `scripts/media/acquisition/`
9. **MangaDex rate limiting**: 1 req/sec is safe, bulk downloads take many hours
10. **Filenames with special chars**: SPY×FAMILY uses × (not x) — be careful with shell quoting

---

## Memory Files
- `memory/2026-04-16.md` — Original platform handoff from install agent
- `memory/2026-04-17.md` — Detailed daily notes from 3 sessions (DC comics + manga pipeline)
- `memory/2026-04-18.md` — Tonight's keepalive session notes
- `memory/osmen-handoff-2026-04-16.md` — Full system handoff from install agent (39 tasks + system state)
- `memory/p13-plex-phase-spec.md` — Phase spec for Plex setup

---

*End of handoff. Good luck.*
