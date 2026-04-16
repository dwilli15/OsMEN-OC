# P13 — Plex + Kometa + Tautulli Phase Spec

**Created:** 2026-04-14 05:42 CDT
**Status:** Planning (implementation paused pending approval)
**Author:** Jarvis

---

## Current State (As Found)

### What Already Exists
- **Quadlet files** written at `~/.config/containers/systemd/`:
  - `osmen-media-plex.container`
  - `osmen-media-kometa.container`
  - `osmen-media-tautulli.container`
- **Podman volumes** created (e.g., `osmen-plex-config`, `osmen-kometa-config`, `osmen-tautulli-config`)
- **Systemd slices** exist (`user-osmen-media.slice`, `user-osmen-background.slice`)
- **Network**: `osmen-media.network`
- **Media dirs**: `~/media/plex/`, `~/media/books/`, `~/media/comics/`, `~/media/music/`
- **NVIDIA GPU**: RTX card detected (`nvidia-smi` works, driver 595.58.03, CUDA 13.2)
- **DRI devices**: `/dev/dri/renderD128`, `/dev/dri/renderD129` present

### What's Broken
All 3 services were in **crash-loop** due to stale Docker image tags:

| Service | Image | Error | Restart Count |
|---------|-------|-------|---------------|
| Plex | `plexinc/pms-docker:1.41.6.9685` | `manifest unknown` | ~3,634 |
| Kometa | `kometateam/kometa:2.2.1` | `manifest unknown` | ~629 |
| Tautulli | `tautulli/tautulli:2.15.1` | `manifest unknown` | ~6,960 |

### Other Issues Found
- `~/media/TV_Anime_OFlow/` referenced in Plex quadlet but **does not exist** on disk
- Plex claim secret file (`~/.config/containers/osmen-plex-claim`) **does not exist**
- No firewall rules for Plex discovery ports (1900/udp, 5353/udp, 32410-32414/udp, 32469/tcp)

---

## Actions Taken

| # | Action | Time | Notes |
|---|--------|------|-------|
| 1 | Stopped all 3 crash-looping services | 05:42 CDT | `systemctl --user stop osmen-media-plex osmen-media-kometa osmen-media-tautulli` |
| 2 | Disabled all 3 services from auto-start | 05:42 CDT | `systemctl --user disable ...` — prevents resume on reboot |
| 3 | Fixed Plex image tag | 06:10 CDT | `plexinc/pms-docker:1.41.6.9685` → `plexinc/pms-docker:latest` |
| 4 | Fixed Kometa image tag | 06:10 CDT | `kometateam/kometa:2.2.1` → `kometateam/kometa:v2.3.1` |
| 5 | Fixed Tautulli image tag | 06:10 CDT | `tautulli/tautulli:2.15.1` → `tautulli/tautulli:v2.17.0` |
| 6 | Fixed Plex volume mounts | 06:10 CDT | `%h/media/plex` → actual `/run/media/dwill/` paths, added all 3 drives |
| 7 | Deleted 7 duplicate anime folders from TV_Anime_OFlow | 06:10 CDT | 508 files, ~257G freed. MD5-verified identical. Justice League (unique) kept. |
| 8 | Replaced Podman secret `osmen-plex-claim` with fresh Plex claim token | 06:27 CDT | Used immediately for first boot |
| 9 | Started Plex successfully and verified claim | 06:28 CDT | `http://127.0.0.1:32400/identity` returned `claimed="1"` |
| 10 | Temporarily disabled NVIDIA passthrough in Plex quadlet | 06:28 CDT | Rootless Podman error: `unresolvable CDI devices nvidia.com/gpu=all` |

---

## Revised P13 Implementation Plan

### Phase A: Image Tag Fix (Blocker)

| Step | Task | Priority | Owner |
|------|------|----------|-------|
| A1 | Find current tags for `plexinc/pms-docker`, `kometateam/kometa`, `tautulli/tautulli` | 🔴 Blocker | Jarvis |
| A2 | Update image tags in all 3 quadlet files | 🔴 | Jarvis |
| A3 | Pull updated images | 🔴 | Jarvis |
| A4 | Reload systemd daemon | 🟡 | Jarvis |

### Phase B: Plex Setup

| Step | Task | Priority | Owner |
|------|------|----------|-------|
| B1 | Create missing `~/media/TV_Anime_OFlow/` or remove from quadlet | 🔴 | D decision |
| B2 | Get Plex claim token from `plex.tv/claim` | 🔴 | D (4-min expiry) |
| B3 | Write claim secret to `~/.config/containers/osmen-plex-claim` | 🔴 | Jarvis |
| B4 | Enable + start Plex service | 🔴 | Jarvis |
| B5 | Verify Plex web UI at `:32400/web` | 🔴 | Jarvis |
| B6 | Configure Plex libraries (movies, TV, anime paths) | 🔴 | D decision |
| B7 | Verify NVIDIA HW transcoding in Plex settings | 🟡 | D or Jarvis |

### Phase C: Tautulli Setup

| Step | Task | Priority | Owner |
|------|------|----------|-------|
| C1 | Enable + start Tautulli | 🟡 | Jarvis |
| C2 | Access Tautulli at `127.0.0.1:8181`, complete setup wizard | 🟡 | D |
| C3 | Connect Tautulli to Plex (URL + token) | 🟡 | D |
| C4 | Configure notification agents (Discord, Telegram) | 🟢 | D decision |
| C5 | Verify webhook → Redis event bus integration | 🟡 | Jarvis |

### Phase D: Kometa Setup

| Step | Task | Priority | Owner |
|------|------|----------|-------|
| D1 | Write Kometa `config.yml` (collections, overlays, metadata) | 🟡 | D decision + Jarvis |
| D2 | Enable + start Kometa | 🟡 | Jarvis |
| D3 | Verify scheduled run (daily 3 AM) | 🟢 | Jarvis |

### Phase E: Network & Hardening

| Step | Task | Priority | Owner |
|------|------|----------|-------|
| E1 | Add firewall rules for Plex discovery ports | 🟡 | Jarvis (elevated) |
| E2 | Verify NVIDIA CDI works rootless (`AddDevice=nvidia.com/gpu=all`) | 🟡 | Jarvis |
| E3 | Test client auto-discovery on LAN | 🟢 | D |

### Phase F: Cleanup

| Step | Task | Priority | Owner |
|------|------|----------|-------|
| F1 | Commit updated quadlets to git | 🟢 | Jarvis |
| F2 | Update Taskwarrior P13 tasks (mark done/in-progress) | 🟢 | Jarvis |
| F3 | Document final state in memory | 🟢 | Jarvis |

---

## Answers from D (2026-04-14 05:54 CDT)

1. **TV_Anime_OFlow** — it's a real external drive, keep it.
2. **Plex libraries** — Movies, TV Shows, Anime. No music.
3. **Kometa collections** — default collections from Kometa wiki are fine to start.
4. **Tautulli notifications** — both Discord + Telegram, but test-only for now. Wants a separate Discord thread for it. Add permanent setup later.
5. **Plex claim** — Jarvis to prompt when ready.

---

## External Drive Map

All 3 drives are NTFS, currently auto-mounted by `udisks2` (not in fstab). This is **unreliable for boot-time services** — Plex/Tautulli/Kometa systemd units may start before drives are mounted.

### Drive Inventory

| Drive | Label | UUID | Size | Used | udisks2 Mount |
|-------|-------|------|------|------|---------------|
| sda1 | `plex` | `B048B7E948B7AD0A` | 4.6T | 2.6T (55%) | `/run/media/dwill/plex` |
| sdb2 | `TV_Anime_OFlow` | `7C3CF5EF3CF5A3F4` | 1.9T | 366G (20%) | `/run/media/dwill/TV_Anime_OFlow` |
| sdc2 | `Other_Media` | `58F6F406F6F3E1E4` | 932G | 584G (63%) | `/run/media/dwill/Other_Media` |

### Media Distribution Across Drives

**Movies** (372 titles) — single source
- `plex/Media/Movies/`

**TV Shows** (60 total) — split across 2 drives
- `plex/Media/TV/` — 56 shows
- `TV_Anime_OFlow/Media/TV/` — 4 shows (Alias, Chuck, Newsroom, West Wing)

**Anime** (up to 15 titles) — split across 2 drives, some overlap
- `plex/Media/Anime/` — 7 titles
- `TV_Anime_OFlow/Media/Anime/` — 8 titles
- Overlap: Avatar, HxH, Monogatari, MHA (dedup needed?)

**Comics** — 2 locations
- `Other_Media/Media/Other/Comics/` — DC, Superman Post-Crisis
- `plex/Media/Other/Comics/` — also exists

**Audiobooks** — 2 locations
- `Other_Media/Media/Other/Audiobooks/` — Sarah J. Maas
- `plex/Media/Other/Audiobooks/` — also exists

**Light Novels** — single source
- `Other_Media/Officially Translated Light Novels/` — large collection

### Mount Reliability Plan

Current `udisks2` auto-mount is NOT reliable for systemd services at boot. Two options:

**Option A: fstab entries (recommended)**
Add to `/etc/fstab`:
```
UUID=B048B7E948B7AD0A /mnt/plex ntfs3 defaults,nofail,uid=1000,gid=1000,noatime 0 0
UUID=7C3CF5EF3CF5A3F4 /mnt/tv_anime_oflow ntfs3 defaults,nofail,uid=1000,gid=1000,noatime 0 0
UUID=58F6F406F6F3E1E4 /mnt/other_media ntfs3 defaults,nofail,uid=1000,gid=1000,noatime 0 0
```
- `nofail` = boot continues if drive is unplugged
- Stable paths at `/mnt/` instead of volatile `/run/media/dwill/`

**Option B: systemd mount units**
- More granular dependency ordering (Plex `After=mnt-plex.mount`)
- Same `nofail` semantics
- More complex to maintain

### Quadlet Mount Corrections Needed

Current quadlet mounts (WRONG):
```
Volume=%h/media/plex:/data/plex:ro
Volume=%h/media/TV_Anime_OFlow:/data/TV_Anime_OFlow:ro
```

Corrected mounts (after fstab, all 3 drives):
```
Volume=/mnt/plex/Media/Movies:/data/Movies:ro
Volume=/mnt/plex/Media/TV:/data/TV:ro
Volume=/mnt/plex/Media/Anime:/data/Anime_plex:ro
Volume=/mnt/tv_anime_oflow/Media/TV:/data/TV_overflow:ro
Volume=/mnt/tv_anime_oflow/Media/Anime:/data/Anime_overflow:ro
Volume=/mnt/other_media/Media/Other/Comics:/data/Comics:ro
Volume=/mnt/other_media/Media/Other/Audiobooks:/data/Audiobooks:ro
Volume=/mnt/other_media/Officially Translated Light Novels:/data/LightNovels:ro
```

**Plex library mapping:**
- **Movies** library → `/data/Movies`
- **TV Shows** library → `/data/TV` + `/data/TV_overflow` (multi-folder)
- **Anime** library → `/data/Anime_plex` + `/data/Anime_overflow` (multi-folder, dedup TBD)
- **Comics** (optional, not core P13) → `/data/Comics`
- **Audiobooks** (optional, for Audiobookshelf not Plex) → skipped here
- **Light Novels** (optional, for Kavita not Plex) → skipped here

---

## Open Questions (Updated)

1. ~~TV_Anime_OFlow~~ ✅ Resolved — real drive, keep it
2. ~~Libraries~~ ✅ Movies, TV, Anime. No music.
3. ~~Kometa~~ ✅ Default collections
4. ~~Notifications~~ ✅ Both, test-only, separate Discord thread
5. **Plex claim** — pending, Jarvis will prompt when ready
6. **NEW: fstab vs systemd mount units** — which approach for stable mounts? (Jarvis recommends fstab)
7. **NEW: Anime dedup** — some titles exist on both plex and TV_Anime_OFlow drives. Consolidate or keep both?
8. **NEW: Comics/Audiobooks/LightNovels** — include in Plex or leave for Kavita/Audiobookshelf (P14)?

---

## Research Sources

- [Plex rootless Podman quadlet](https://myee111.github.io/posts/plex/) — Fedora rootless setup, firewall ports, volume strategy
- [Plex in Podman container](https://oneuptime.com/blog/post/2026-03-18-run-plex-media-server-podman-container/view) — NVIDIA GPU passthrough, claim token flow
- [Kometa install guide](https://metamanager.wiki/en/latest/kometa/install/overview/) — Docker vs local install, config structure
- [Tautulli setup](https://selfhosting.sh/apps/tautulli/) — Docker config, Plex token retrieval, notification agents
- [NVIDIA GPUs in containers](https://gist.github.com/Iksas/ee6920f0443dab028e6857c019be62ba) — CDI device passthrough for Podman
- [Kometa default collections](https://test.kometa.wiki/en/latest/defaults/collections/#collection-section-order) — default collection ordering
