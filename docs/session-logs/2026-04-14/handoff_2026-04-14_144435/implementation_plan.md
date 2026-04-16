# ΩΣΕ∆ Media Library Normalization & Script Migration

```
⟐ Ω·Σ ⊸ [★Ε₁·∆₁★ | Ε₂·∆₁ | Ε₃·∆₂ | Ε₄·∆₃ | Ε₅·∆₄] ⊸ ◈RECON◈ ⟐
```

## Problem Statement

The OsMEN media library (across 3 external NTFS drives) has accumulated significant naming inconsistencies, duplicate show directories, and legacy Windows PowerShell scripts that need replacement with Linux-native equivalents. The entire media stack (Sonarr, Radarr, Prowlarr, etc.) is now running on Ubuntu via Podman quadlets — the tooling needs to catch up.

---

## Reconnaissance Findings

### Drive Layout

| Drive | Device | Size | Label | Mount | Contents |
|-------|--------|------|-------|-------|----------|
| WD Elements | sdb | 4.5T | `plex` | `/run/media/dwill/plex` | Movies, TV, Anime, Comics, scripts, config |
| WD My Passport | sda | 1.8T | `TV_Anime_OFlow` | `/run/media/dwill/TV_Anime_OFlow` | Overflow TV + Anime |
| Samsung SSD 870 | sdc | 931G | `Other_Media` | `/run/media/dwill/Other_Media` | Light novels, other media |

> [!WARNING]
> All 3 drives mount via **udisks2** (not fstab). They will **not auto-mount on reboot** without user login or fstab entries. This needs to be addressed.

### Running Services (Podman Quadlets)

| Status | Service | Notes |
|--------|---------|-------|
| ✅ Running | Sonarr, Radarr, Prowlarr, Bazarr, qBittorrent, SABnzbd, Tautulli, Mylar3, Readarr, Audiobookshelf, ConvertX | Healthy |
| ❌ Restart Loop | Kometa, Lidarr | `activating (auto-restart)` — needs investigation |
| ❌ Not Found | Plex config volume | Volume service missing |

---

## User Review Required

> [!IMPORTANT]
> **TV Show Duplicates Found** — The following shows exist as 2-4 separate directories with fragmented episodes. The plan proposes merging them into a single canonical directory. Please confirm which name is canonical for each:

### Duplicate Group 1: Monarch Legacy of Monsters
| Directory | Episodes | Season |
|-----------|----------|--------|
| `Monarch.Legacy.of.Monsters` | 1 | Season 02 |
| `Monarch.Legacy.of.Monsters..1080p` | 2 | Season 02 |
| `Monarch Legacy of Monsters (2023)` | 3 | Season 02 |
| **Proposed canonical** → `Monarch Legacy of Monsters (2023)` | 6 total | Season 02 |

### Duplicate Group 2: Star Trek Starfleet Academy
| Directory | Episodes | Season |
|-----------|----------|--------|
| `Star Trek Starfleet Academy` | 1 | Season 01 |
| `Star Trek - Starfleet Academy (2025)` | 6 | Season 01 |
| `Star Trek Starfleet Academy (2025)` | 3 | Season 01 |
| `Star Trek Starfleet Academy (2026)` | 1 | Season 01 |
| **Proposed canonical** → `Star Trek - Starfleet Academy (2025)` | 11 total | Season 01 |

### Duplicate Group 3: CIA
| Directory | Episodes | Season |
|-----------|----------|--------|
| `CIA 2026` | 5 | Season 01 |
| `CIA. (2026)` | 14 | Season 01 |
| **Proposed canonical** → `CIA (2026)` | 19 total | Season 01 |

### Duplicate Group 4: DTF St. Louis
| Directory | Episodes | Season |
|-----------|----------|--------|
| `DTF.St.Louis` | 4 | Season 01 |
| `DTF.St.Louis..1080p` | 4 | Season 01 |
| **Proposed canonical** → `DTF St Louis (YYYY)` | 8 total (may have dups) | Season 01 |

> [!IMPORTANT]
> **Naming Standard Decision** — The library currently mixes 3 season-naming styles. Which should be canonical?
> - `Season 01` (zero-padded, used by most shows on plex drive) ← **recommended**
> - `Season 1` (used by House MD, Newsroom, West Wing)
> - `S01` (used on overflow drive)

> [!IMPORTANT]
> **Movie Structure** — 346 loose movie files sit directly in the Movies directory. Plex best practice is one folder per movie: `Movie Name (Year)/Movie Name (Year).ext`. Should we auto-folder them?

> [!CAUTION]
> **Movie Naming Conflict Discovered** — The existing `plex-organize` skill on the plex drive explicitly says **"NO SUB-DIRECTORIES IN MOVIES FOLDER"** (flat `Movies/Movie (Year).ext`), but Plex's own documentation and best practices recommend per-movie folders. The 7-phase `media-transfer` skill also enforces flat. **You need to pick one standard** — this will affect 346+ files and all future acquisitions.

> [!WARNING]
> **Windows→Linux Skills Gap** — 8 existing skills on the plex drive (plex-organize, media-transfer, media-pipeline-status, plex-health-check, torrent-cleanup, gap-fill, comic-hunter, vpn-audit) all reference Windows paths (`D:\Media\*`), Windows commands (PowerShell, `Get-Service`), and Windows APIs (Windows Firewall). They need porting to Linux equivalents. Additionally, agent configs (AGENTS.md, SOUL.md, TOOLS.md) and the `config/launchers/media.yaml` workspace still point to `D:\`. OneDrive backup locations (`osmen-migration/`, `oc_backup/`, `osmen-agent-handoffs/`) contain migration plans, changelogs, and handoff docs that should be reviewed for unfinished items.

---

## Proposed Changes

### Phase A: Media Structure Audit (✅ COMPLETE — this document)

Research-only phase to map the full state of the library.

---

### Phase B: TV & Anime Deduplication + Rename

**Agent:** `Ε₂ ⬡₂ Engineer-Infrastructure`

#### TV Shows — Merge Duplicates
For each duplicate group:
1. Create canonical directory with Plex naming: `Show Name (Year)/Season XX/`
2. Move all episodes into canonical season dirs (copy-first, verify, then delete source)
3. Check for actual duplicate files (same episode, different quality) — keep highest quality
4. Delete empty source directories

#### TV Shows — Fix Naming Issues

| Current | Proposed | Issue |
|---------|----------|-------|
| `The Continental` (loose files) | `The Continental (2023)/Season 01/` | No year, no season dir |
| `The Last of Us` (`Season 01` + `Season 2`) | `The Last of Us (2023)/Season 01/Season 02/` | No year, mixed padding |
| `The Lord of the Rings The Rings of Power` | `The Lord of the Rings The Rings of Power (2022)/Season 02/` | No year |
| `Supernatural` (scene-pack dirs) | `Supernatural (2005)/Season 01-15/` | Scene-pack subdirs, not Season dirs |
| `Daredevil Born Again (2025)` S02 only | Verify if S01 exists elsewhere or if this is correct | Starts at Season 02 |
| `House MD (2004)` (`Season 1` not `Season 01`) | `House MD (2004)/Season 01-08/` | Inconsistent padding |

#### Anime — Fix Naming Issues

| Current | Proposed | Issue |
|---------|----------|-------|
| `Avatar The Last Airbender (2005)` (scene-pack subdirs) | `Avatar The Last Airbender (2005)/Season 01-03/` | Scene names as season dirs |
| `Justice League (2001)` on overflow (`S01-S05`) | `Justice League (2001)/Season 01-05/` | `S01` format |

#### Overflow Drive Consistency

| Current | Proposed | Issue |
|---------|----------|-------|
| `Alias (2001)` (`S01-S05`) | `Alias (2001)/Season 01-05/` | `S01` format |
| `Chuck (2007)` (`S01-S04`) | `Chuck (2007)/Season 01-04/` + `Extras/` | `S01` format |

---

### Phase C: Movie Structure Normalization

**Agent:** `Ε₂ ⬡₂ Engineer-Infrastructure`

1. Parse each loose movie file for title + year (from filename)
2. Create `Movie Name (Year)/` directory for each
3. Move file into its directory
4. Handle edge cases (multi-part, extras, sample files)

---

### Phase D: Script, Skill, and Agent Migration (PowerShell → Bash/Python)

**Agent:** `Ε₃ ⬡₃ Engineer-Architecture`

The plex drive contains **100+ legacy PowerShell scripts** AND **8 existing Claude skills** from the old Windows setup. These need to be categorized, prioritized, and rewritten as Linux-native scripts. Additionally, agent config files and pipeline docs from `c:\Dev\osmen`, `osmen-migration/`, and `oc_backup/` need reconciliation.

#### Script Categories (from recon)

| Category | Count | Priority | Examples |
|----------|-------|----------|----------|
| **Media Transfer** | ~15 | 🔴 HIGH | `transfer_phase1-7.ps1`, `media_transfer_complete.ps1` |
| **VPN/Firewall** | ~12 | ⚫ OBSOLETE | `fix_firewall_v*.ps1`, `vpn_watchdog.ps1` (Windows-specific) |
| **Plex Management** | ~10 | 🟡 MEDIUM | `plex_collection_*.ps1`, `scan_complete.ps1` |
| **Acquisition** | ~8 | 🔴 HIGH | `grab_movies_v3.py`, `download_monitor.ps1` |
| **Credential Mgmt** | ~8 | 🟡 MEDIUM | `store_creds.ps1`, `get_plex_creds.ps1` |
| **Comics/Books** | ~6 | 🟢 LOW | `comic_cbr_to_cbz.ps1`, `search_comics.ps1` |
| **Subtitle** | ~6 | 🟡 MEDIUM | `subtitle_downloader_v3.py` (already Python!) |
| **Research/Search** | ~6 | 🟢 LOW | `analyze_results.py`, `search_indexers.sh` |

#### New Script Architecture

```
scripts/media/
├── transfer/
│   ├── tv_transfer.sh          # TV episode intake → sort → rename → place
│   ├── movie_transfer.sh       # Movie intake → folder → place
│   ├── anime_transfer.sh       # Anime intake → match → season → place
│   ├── audiobook_transfer.sh   # Audiobook intake
│   ├── comics_transfer.sh      # Comics/manga intake
│   └── music_transfer.sh       # Music intake (placeholder for Lidarr)
├── naming/
│   ├── plex_naming.py          # Core naming convention engine
│   ├── validate_structure.py   # Audit tool for naming violations
│   └── rename_dry_run.py       # Preview renames before execution
├── acquisition/
│   ├── placeholder.md          # Media acquisition placeholder
│   └── monitor_downloads.py    # Watch download dirs for completed items
├── plex/
│   ├── scan_library.py         # Trigger Plex library scan
│   ├── collections.py          # Manage Plex collections
│   └── health_check.py         # Verify Plex health
└── maintenance/
    ├── dedup_check.py          # Find duplicate episodes across drives
    ├── quality_audit.py        # Report on file quality (resolution, codec)
    └── orphan_cleanup.py       # Find files not in any Plex library
```

---

### Phase E: Configuration & Dependencies

**Agent:** `Ε₅ ⬡₅ Engineer-Operations`

1. **Fix fstab entries** for the 3 external drives (auto-mount on boot)
2. **Fix Kometa** — investigate restart loop, repair config
3. **Fix Lidarr** — investigate restart loop, repair config
4. **Fix Plex config volume** — missing quadlet service
5. **Sonarr/Radarr naming** — wire root folders + naming conventions to match our standard
6. **Install missing dependencies** for new scripts (Python libs, etc.)

---

### Phase F: Transfer Protocol Scripts

**Agent:** `Ε₃ ⬡₃ Engineer-Architecture`

Each media type needs a specific, well-documented transfer protocol:

| Protocol | Source | Destination | Naming Standard |
|----------|--------|-------------|-----------------|
| TV → Plex | Sonarr download dir | `plex/Media/TV/Show (Year)/Season XX/` | `Show - SXXEXX - Title.ext` |
| Movies → Plex | Radarr download dir | `plex/Media/Movies/Movie (Year)/` | `Movie (Year).ext` |
| Anime → Plex | Manual/Sonarr | `plex/Media/Anime/Show (Year)/Season XX/` | `Show - SXXEXX - Title.ext` |
| Music → Plex | Lidarr | `media/music/Artist/Album (Year)/` | `XX - Track.ext` |
| Books → Readarr | Readarr | `media/books/Author/Title/` | `Title.ext` |
| Comics → Mylar | Mylar3 | `media/comics/Series/` | `Series Issue #XXX.cbz` |
| Audiobooks → ABS | Manual | `media/audiobooks/Author/Title/` | `XX - Chapter.mp3` |
| Podcasts → ABS | RSS/Manual | `media/podcasts/Show/` | per-episode |

---

### Phase G: Taskwarrior Expansion

**Agent:** `Ε₄ ⬡₄ Engineer-QA`

Expand the Taskwarrior database with granular subtasks for each phase above. This will be the operational backbone that other agents execute from.

---

## Open Questions

> [!IMPORTANT]
> 1. **DTF St. Louis** — What year was this show? Need it for the canonical name.
> 2. **Daredevil Born Again** — Is Season 02 correct, or should this be Season 01?
> 3. **Avatar TLA** — The `Featurettes & Extras` dir: keep as `Extras/` or ignore?
> 4. **Movie quality preference** — When deduplicating, prefer 1080p BluRay > 720p > WEB-DL? Or highest resolution always wins?
> 5. **Overflow drive strategy** — Long-term, should overflow content be merged back to the main plex drive (4.5T has ~2T free), or stay split across drives?
> 6. **Media acquisition scripts** — You mentioned this can be a placeholder. Confirm: you want the transfer/naming scripts fully built but acquisition left as stubs for now?

## Verification Plan

### Automated Tests
- **Dry-run rename script** that outputs proposed changes without executing
- **Structure validator** that scans all media dirs and flags violations
- **Duplicate detector** that finds same-episode files across directories
- **Post-merge file count verification** (total episodes before = total after)

### Manual Verification
- User reviews dry-run output for each duplicate group before merge
- User confirms canonical names for ambiguous shows
- User spot-checks Plex UI after library scan to verify metadata matches
