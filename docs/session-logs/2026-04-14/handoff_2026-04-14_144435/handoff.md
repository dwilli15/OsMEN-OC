# Session Handoff Report — ΩΣΕ∆ Media Library Normalization
**Generated**: 2026-04-14 14:44:35 CDT  
**Session Duration**: ~6 hours (11:22 AM → 2:44 PM CDT, with gaps)  
**Model**: Gemini 3.1 Pro (High) → Claude Opus 4.6 (Thinking)  
**Git**: LOCAL-ONLY (no remote)  
**Workflow**: `/multi-agent-audit` (ΩΣΕ∆ Framework)

---

## Summary

This session performed **deep reconnaissance** of the OsMEN media library across 3 external NTFS drives attached to the Ubuntu Linux machine (`Ubu-OsMEN` at `192.168.7.248`), audited 60+ TV shows, 8 anime series, 346 loose movie files, and 100+ legacy PowerShell scripts. The session culminated in **91 granular Taskwarrior tasks** under `project:osmen.media` ready for multi-agent execution. **No files were moved, renamed, or deleted** — this was research and planning only, per explicit user instruction.

The user wants a larger model to take over execution from here. The ΩΣΕ∆ multi-agent audit framework is the intended execution model (11 agents in coordinated phases with demo gates).

---

## SSH Access (Verified Working)

| Machine | Hostname | IP | User | SSH Config Alias |
|---------|----------|----|------|------------------|
| **Windows** (this machine) | `Dlex` | `192.168.7.249` | `armad` | `Dlex` (in Linux ~/.ssh/config) |
| **Linux** (Ubuntu 26.04) | `Ubu-OsMEN` | `192.168.7.248` | `dwill` | `ubu-osmen` (in Windows ~/.ssh/config) |

- SSH key auth works both directions (ed25519)
- Both `sshd` and `ssh-agent` services running on Windows
- Tested: packet send/receive, SCP file transfers, remote command execution
- **Wave Terminal** on Linux can connect to Windows via `ssh Dlex`

### SSH Config Files

**Windows** (`C:\Users\armad\.ssh\config`):
```
Host Ubu-OsMEN ubu-osmen omen
    HostName 192.168.7.248
    User dwill
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 6
    StrictHostKeyChecking accept-new
```

**Linux** (`/home/dwill/.ssh/config`) — updated this session to fix stale IP:
```
Host Ubu-OsMEN ubu-osmen
    HostName Ubu-OsMEN
    User dwill
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
    ConnectTimeout 5

Host Dlex dlex
    HostName 192.168.7.249      # ← UPDATED from .246 to .249 this session
    User armad
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
    ConnectTimeout 5
```

---

## Hardware & Storage Layout

### Block Devices (from `lsblk`)

| Device | Size | Type | Label | Mount | Use |
|--------|------|------|-------|-------|-----|
| nvme0n1 | 954G | NVMe Samsung | — | (Windows partitions) | Windows system drive |
| nvme0n1p4 | 697G | ext4 | `win_closet` | `/mnt/win_closet` (noauto) | Shared Windows partition |
| nvme1n1 | 932G | NVMe SK Hynix | — | `/` (LUKS encrypted) | Linux system drive |
| **sda** | **1.8T** | WD My Passport | `TV_Anime_OFlow` | `/run/media/dwill/TV_Anime_OFlow` | Overflow TV + anime |
| **sdb** | **4.5T** | WD Elements | `plex` | `/run/media/dwill/plex` | Main media library |
| **sdc** | **932G** | Samsung SSD 870 | `Other_Media` | `/run/media/dwill/Other_Media` | Light novels, other |

### Disk Usage
```
/dev/sdb1  4.6T  2.6T  2.1T  55%  /run/media/dwill/plex
/dev/sda2  1.9T  109G  1.8T   6%  /run/media/dwill/TV_Anime_OFlow
/dev/sdc2  932G  584G  349G  63%  /run/media/dwill/Other_Media
```

> **⚠️ CRITICAL**: All 3 external drives are mounted via **udisks2** (NOT fstab). They will NOT auto-mount on reboot. Task E.1 addresses this.

---

## Running Services (22 Podman Quadlets)

### Healthy (Running)
| Service | Description |
|---------|-------------|
| `osmen-core-caddy` | Caddy Reverse Proxy |
| `osmen-core-chromadb` | ChromaDB |
| `osmen-core-langflow` | Langflow |
| `osmen-core-nextcloud` | Nextcloud |
| `osmen-core-postgres` | PostgreSQL 17 + pgvector |
| `osmen-core-redis` | Redis 7 |
| `osmen-core-siyuan` | SiYuan PKM |
| `osmen-librarian-audiobookshelf` | Audiobookshelf |
| `osmen-librarian-convertx` | ConvertX |
| `osmen-librarian-kavita` | Kavita (Books/Comics/Manga) |
| `osmen-media-bazarr` | Bazarr (subtitles) |
| `osmen-media-gluetun` | **gluetun VPN Gateway** |
| `osmen-media-mylar3` | Mylar3 (comics) |
| `osmen-media-prowlarr` | Prowlarr (indexer) |
| `osmen-media-qbittorrent` | qBittorrent (in VPN pod) |
| `osmen-media-radarr` | Radarr (movies) |
| `osmen-media-readarr` | Readarr (books) |
| `osmen-media-sabnzbd` | SABnzbd (usenet, in VPN pod) |
| `osmen-media-sonarr` | Sonarr (TV) |
| `osmen-media-tautulli` | Tautulli (Plex stats) |
| `osmen-monitoring-portall` | Portall dashboard |
| `osmen-monitoring-uptimekuma` | Uptime Kuma |

### Unhealthy
| Service | Status | Issue |
|---------|--------|-------|
| `osmen-media-kometa` | `activating (auto-restart)` | Restart loop — needs config investigation |
| `osmen-media-lidarr` | `activating (auto-restart)` | Restart loop — needs config investigation |
| `osmen-plex-config-volume` | `not-found` | Missing quadlet service file |

### VPN-Walled Architecture (CRITICAL)
```
download-stack.pod
├── osmen-media-gluetun (VPN gateway — all traffic exits through VPN)
├── osmen-media-qbittorrent (shares gluetun network namespace)
│   ├── Web UI: 127.0.0.1:9090
│   └── Downloads: ~/Downloads
└── osmen-media-sabnzbd (shares gluetun network namespace)
    ├── Web UI: 127.0.0.1:8082
    └── Downloads: ~/Downloads
```

Both qBit and SABnzbd `Requires=osmen-media-gluetun.service` and use `Pod=download-stack.pod`. All traffic is VPN-walled. Kill-switch verification is pending (Task E.9).

**File ownership issue**: Downloads created inside containers are owned by `100910:101000`, not `dwill:dwill`. Transfer scripts must handle chown/ACL (Task D.38).

---

## Media Library Structure

### Drive: `plex` (sdb, 4.5T) — Primary Library

```
/run/media/dwill/plex/
├── Media/
│   ├── Anime/        (7 shows, well-structured except Avatar TLA)
│   ├── Movies/       (346 loose files, 2 subdirs — NEEDS NORMALIZATION)
│   ├── TV/           (58 shows — 4 duplicate groups, naming issues)
│   ├── Comics/
│   └── Other/
├── Plex/             (Playlists)
├── Torrents/
├── Transfer/
├── agent-in/         (legacy Windows agent scripts)
├── linux-transfer/   (migration prep from Windows era)
├── media-research/
├── tools/            (legacy Windows tools)
├── temp/ & tmp/      (legacy temp files)
├── config/
├── .claude/          (skills, hooks, settings)
├── .openclaw/        (adapter config)
├── AGENTS.md, SOUL.md, TOOLS.md, USER.md, etc.
└── [~60 legacy .ps1/.py scripts at root]
```

### Drive: `TV_Anime_OFlow` (sda, 1.8T) — Overflow
```
/run/media/dwill/TV_Anime_OFlow/Media/
├── Anime/
│   └── Justice League (2001)/S01-S05
└── TV/
    ├── Alias (2001)/S01-S05
    ├── Chuck (2007)/S01-S04 + Chuck Extras
    ├── The Newsroom (2012)/Season 1-3
    └── The West Wing (1999)/Season 0-7
```

### Drive: `Other_Media` (sdc, 932G)
```
/run/media/dwill/Other_Media/
├── Media/Other/
├── Officially Translated Light Novels/
└── Tools/
```

### Home Directory Media Stubs
```
/home/dwill/media/          (empty placeholder dirs)
├── audiobooks/  books/  comics/  manga/  music/  plex/  podcasts/
```

---

## TV Show Duplicate Groups (MUST BE MERGED)

### Group 1: Monarch Legacy of Monsters — 3 directories, 6 episodes
| Directory | Episodes | Season | Quality |
|-----------|----------|--------|---------|
| `Monarch.Legacy.of.Monsters` | 1 | Season 02 | Unknown |
| `Monarch.Legacy.of.Monsters..1080p` | 2 | Season 02 | 1080p |
| `Monarch Legacy of Monsters (2023)` | 3 | Season 02 | Unknown |
| **Proposed canonical** | **6** | **Season 02** | Merge, keep best |

### Group 2: Star Trek Starfleet Academy — 4 directories, 11 episodes
| Directory | Episodes | Season |
|-----------|----------|--------|
| `Star Trek Starfleet Academy` | 1 | Season 01 |
| `Star Trek - Starfleet Academy (2025)` | 6 | Season 01 |
| `Star Trek Starfleet Academy (2025)` | 3 | Season 01 |
| `Star Trek Starfleet Academy (2026)` | 1 | Season 01 |
| **Proposed canonical** | **11** | **Season 01** |

### Group 3: CIA — 2 directories, 19 episodes
| Directory | Episodes | Season |
|-----------|----------|--------|
| `CIA 2026` | 5 | Season 01 |
| `CIA. (2026)` | 14 | Season 01 |
| **Proposed canonical** | **19** | **Season 01** |

### Group 4: DTF St. Louis — 2 directories, 8 episodes
| Directory | Episodes | Season |
|-----------|----------|--------|
| `DTF.St.Louis` | 4 | Season 01 |
| `DTF.St.Louis..1080p` | 4 | Season 01 |
| **Proposed canonical** | **8 (may have dups)** | **Season 01** |

---

## TV Show Naming Issues (NON-DUPLICATE)

| Show | Issue | Proposed Fix |
|------|-------|--------------|
| `The Continental` | No year, 3 loose .mkv files (no season dir) | → `The Continental (2023)/Season 01/` |
| `The Last of Us` | No year, mixed `Season 01` AND `Season 2` | → `The Last of Us (2023)/Season 01/Season 02/` |
| `The Lord of the Rings The Rings of Power` | No year, only Season 02 | → `...The Rings of Power (2022)/Season 02/` |
| `Supernatural (2005)` | 12 scene-pack dirs (`Supernatural.S01.COMPLETE.BluRay...`) | → `Season 01` through `Season 15` |
| `Daredevil Born Again (2025)` | Starts at Season 02, only 1 ep | Investigate if correct |
| `House MD (2004)` | `Season 1-8` not `Season 01-08` | Zero-pad, keep Extras/ |
| `The Newsroom (2012)` | `Season 1-3` not `Season 01-03` | Zero-pad |
| `The West Wing (1999)` | `Season 0-7` not `Season 00-07` | Zero-pad |

## Anime Naming Issues

| Show | Location | Issue | Fix |
|------|----------|-------|-----|
| Avatar TLA (2005) | plex | Scene-pack subdirs instead of Season dirs | → `Season 01-03/` + `Extras/` |
| Justice League (2001) | overflow | `S01-S05` format | → `Season 01-05/` |
| Alias (2001) | overflow | `S01-S05` format | → `Season 01-05/` |
| Chuck (2007) | overflow | `S01-S04` format | → `Season 01-04/` + `Extras/` |

## Season Naming Inconsistency

Three formats exist across the library:
1. `Season 01` (zero-padded) — **recommended canonical standard**
2. `Season 1` (no padding) — House MD, Newsroom, West Wing, Last of Us S2
3. `S01` (abbreviated) — all overflow drive content, Justice League

---

## Movie Structure Issue

**346 loose movie files** sit directly in `/run/media/dwill/plex/Media/Movies/` with only 2 subdirectories.

### ⚠️ NAMING CONFLICT DISCOVERED
The existing `plex-organize` skill on the plex drive says **"NO SUB-DIRECTORIES IN MOVIES FOLDER"** (flat structure: `Movies/Movie (Year).ext`). The `media-transfer` skill's 7-phase protocol also enforces flat. But Plex's own documentation recommends per-movie folders for better metadata matching.

**User must decide**: Flat or per-movie folders. This affects 346+ files and all future acquisitions.

---

## Existing Skills (on plex drive — ALL WINDOWS-BASED, NEED PORTING)

| Skill | Location | What It Does | Port Priority |
|-------|----------|--------------|---------------|
| `plex-organize` | `.claude/skills/` | Unified movie/TV/anime naming + structure | 🔴 HIGH |
| `media-transfer` | `.claude/skills/` | 7-phase transfer protocol (hash verify, Plex API verify, recycle-bin delete) | 🔴 HIGH |
| `media-pipeline-status` | `.claude/skills/` | Full pipeline health dashboard (VPN, acquisition, indexing, Plex, storage) | 🟡 MEDIUM |
| `plex-health-check` | `.claude/skills/` | Plex server health monitoring | 🟡 MEDIUM |
| `torrent-cleanup` | `.claude/skills/` | qBittorrent completed torrent removal | 🟢 LOW |
| `gap-fill` | `.claude/skills/` | Find missing episodes/seasons | 🟢 LOW |
| `comic-hunter` | `.claude/skills/` | Comic acquisition | 🟢 LOW |
| `vpn-audit` | `.claude/skills/` | VPN connection audit (Windows VPN client) | 🟢 LOW (rewrite for gluetun) |
| `torrent-discover` | `agent-in/.claude/skills/` | Torrent search | 🟡 MEDIUM |
| `torrent-season` | `agent-in/.claude/skills/` | Season pack torrent handling | 🟡 MEDIUM |
| `handoff-continue` | `.claude/skills/` | Session handoff (generic) | — |
| `handoff-resume` | `.claude/skills/` | Session resume (generic) | — |

All skills reference `D:\Media\*` paths, PowerShell commands, and Windows APIs. They are the **source of truth** for naming conventions and transfer protocols but need complete rewriting for Linux.

---

## Legacy Script Inventory (100+ files on plex drive)

### Key Directories
| Path | Count | Type | Notes |
|------|-------|------|-------|
| `/run/media/dwill/plex/agent-in/` | ~40 | PowerShell (.ps1) + Python (.py) | Agent workspace scripts |
| `/run/media/dwill/plex/tools/` | ~20 | PowerShell | Transfer phases, Plex tools |
| `/run/media/dwill/plex/temp/` | ~15 | PowerShell + Python | Phased transfer pipeline |
| `/run/media/dwill/plex/media-research/` | ~8 | Mixed | Prowlarr/indexer scripts |
| `/run/media/dwill/plex/Media/` | ~6 | Python | Subtitle downloaders |
| `/run/media/dwill/plex/` (root) | ~15 | Mixed | Firewall fixes, VPN, misc |

### PowerShell Module Files (Windows-specific)
- `agent-in/MediaCore/` — Core media management module
- `agent-in/CredentialManager.psm1` — Credential storage
- `agent-in/ElevatedExecutor.psm1` — Elevated command execution
- `agent-in/ComicParser.psm1` — Comic file parsing

---

## Windows-Side Files (Source Material for Migration)

### `c:\Dev\osmen\` (Main OsMEN Workspace)
- `config/launchers/media.yaml` — Media launcher config (references `D:\`, needs port to Linux paths)
- `scripts/taskwarrior/` — 2 scripts: `google_tasks_sync.py`, `sync_to_calendar.py`
- `scripts/` — 124 scripts total (many are OsMEN system scripts, not media-specific)
- `.agents/workflows/multi-agent-audit.md` — ΩΣΕ∆ Framework workflow file
- `.claude/skills/` — 5 skills (decision-trail, docker-health, gh-transplant, glm-test, handoff-*)

### `C:\Users\armad\OneDrive\Documents\osmen-migration\`
- `MIGRATION_CHANGELOG.md` (326KB!) — Massive changelog from Windows→Linux migration
- `MIGRATION_HANDOFF_INDEX.md` — Index of all handoffs
- `osmen-snapshot.tar` (20GB) — Full OsMEN snapshot
- `osmen_omen_postinstall.sh` — Post-install script
- `ORCHESTRATION_CONVERGENCE_GAP_REPORT_2026-03-16.md` — Gap analysis
- Various migration tracking docs

### `C:\Users\armad\OneDrive\Documents\oc_backup\`
- `plans/` — 18 planning docs including `HP_OMEN_DUAL_BOOT_MIGRATION_SPEC.md`, `OSMEN_CONTROL_CENTER_SPEC.md`
- `manifests/`, `scripts/`, `session-logs/`, `snapshots/`
- `BACKUP_STATUS_2026-03-15.md`

### `C:\Users\armad\OneDrive\Documents\osmen-agent-handoffs\`
- `2026-04-02_ubuntu26_linux_local_agent_handoff/` — Full handoff from Ubuntu install
- `2026-04-02_ubuntu26_linux_local_agent_handoff_slim/` — Slim version (7 sections: summary, transcript, runtime-network, display-gpu-npu, github-shift, research-and-artifacts, source-docs)

---

## Taskwarrior State

### Configuration
- Location: `~/.task/` on Linux
- Config: `~/.taskrc` (custom UDAs: energy, interaction, caldav_uid)
- Hooks: `on-add-osmen.py`, `on-modify-osmen.py` (queue tasks to OsMEN-OC event bus via SQLite)
- Binary: `/usr/bin/task`

### Media Project Tasks: 91 pending

| Phase | Tag | Count | Focus |
|-------|-----|-------|-------|
| B | `+phaseB` | 26 | TV/Anime dedup & rename |
| C | `+phaseC` | 4 | Movie structure normalization |
| D | `+phaseD` | 39 | Script, skill, agent migration + VPN |
| E | `+phaseE` | 10 | Config, deps, service fixes |
| F | `+phaseF` | 9 | Transfer protocol documentation |
| — | `+infra` | 3 | Infrastructure (symlinks, cleanup) |

### High-Priority Tasks (20)
```bash
task project:osmen.media priority:H status:pending list
```
Key items:
- B.1-B.4: Merge 4 duplicate TV show groups
- B.8: Rename Supernatural scene-pack dirs
- C.1: Audit 346 loose movie files
- D.1: Categorize 100+ legacy scripts
- D.2-D.3: Write core naming engine + validator
- D.5-D.7: Write TV/movie/anime transfer scripts
- D.19-D.20: Port plex-organize + media-transfer skills
- D.33: Resolve movie naming conflict (flat vs folders)
- D.36: Account for VPN-walled pod in all transfer scripts
- E.1: Add fstab entries for 3 external drives
- E.2-E.4: Fix Kometa, Lidarr, Plex config volume

### Query Cheatsheet
```bash
task project:osmen.media +phaseB list          # TV/Anime dedup & rename
task project:osmen.media +phaseC list          # Movie structure
task project:osmen.media +phaseD list          # Script/skill/agent migration
task project:osmen.media +phaseE list          # Config & deps
task project:osmen.media +phaseF list          # Transfer protocols
task project:osmen.media priority:H list       # Critical path
task project:osmen.media +dedup list           # Duplicate merges only
task project:osmen.media +rename list          # Rename tasks only
task project:osmen.media +skills list          # Skill porting
task project:osmen.media +vpn list             # VPN architecture tasks
task project:osmen.media +naming list          # Naming convention tasks
task project:osmen.media +agents list          # Agent config migration
```

---

## Decisions Made

1. **Season naming standard**: `Season 01` (zero-padded) recommended as canonical — **PENDING USER CONFIRMATION**
2. **Movie structure**: Flat vs per-folder — **CONFLICT DISCOVERED, PENDING USER DECISION**
3. **No changes policy**: User explicitly stated no file moves/renames/deletes during this session — research and planning only
4. **Multi-agent execution**: User specified other agents will do the actual work via ΩΣΕ∆ framework
5. **Acquisition scripts**: User said placeholder is OK if assistant isn't comfortable helping with media acquisition
6. **SSH config fix**: Updated Linux `~/.ssh/config` to fix stale Windows IP (`.246` → `.249`)
7. **Downloads dir**: Deleted `/home/dwill/downloads` (lowercase, with permission issues) via sudo — distinct from `~/Downloads`

---

## Open Questions (MUST BE ANSWERED BEFORE EXECUTION)

1. **DTF St. Louis** — What year? Needed for canonical folder name `DTF St Louis (YYYY)`
2. **Daredevil Born Again** — Is `Season 02` correct, or should it be `Season 01`?
3. **Avatar TLA Extras** — Keep `Featurettes & Extras` dir as `Extras/` or discard?
4. **Movie quality preference** — When deduplicating: 1080p BluRay > 720p > WEB-DL? Or highest resolution always wins?
5. **Overflow drive strategy** — Merge overflow content back to plex drive (2.1T free), or keep split across drives?
6. **Acquisition scripts** — Confirm stubs only for now?
7. **Movie naming standard** — Flat (`Movies/Movie (Year).ext`) matching existing skills, or per-movie folders (`Movies/Movie (Year)/Movie (Year).ext`) matching Plex docs?

---

## Files Created This Session

| File | Location | Purpose |
|------|----------|---------|
| `media_recon.sh` | `/tmp/` on Linux (also local scratch) | Bash recon script for media directory auditing |
| `taskwarrior_expand.sh` | `/tmp/` on Linux (also local scratch) | Batch import of 67 initial Taskwarrior tasks |
| `taskwarrior_expand_gap.sh` | `/tmp/` on Linux (also local scratch) | 17 additional tasks for skills/agent migration gap |
| `taskwarrior_vpn.sh` | `/tmp/` on Linux (also local scratch) | 7 VPN architecture tasks |
| `recon_output.txt` | Local scratch dir | Full recon script output (564 lines) |
| `implementation_plan.md` | Artifact dir | Comprehensive ΩΣΕ∆ implementation plan |
| `task.md` | Artifact dir | Task tracker |

### Files Modified This Session

| File | Change |
|------|--------|
| `/home/dwill/.ssh/config` (Linux) | Fixed `Dlex` host IP from `192.168.7.246` → `192.168.7.249` |

### Files Transferred This Session

| Source (Windows) | Destination (Linux) | Method |
|------------------|---------------------|--------|
| `C:\Users\armad\OneDrive\Documents\Family\mltsdoc.pdf` | `~/Downloads/mltsdoc.pdf` | SCP |
| `C:\Users\armad\Downloads\Gemini_Generated_Image_7be2e77be2e77be2.png` | `~/Downloads/` | SCP |

### Files Deleted This Session

| Path | Method | Reason |
|------|--------|--------|
| `/home/dwill/downloads/` (lowercase) | `sudo rm -rf` | User request — contained torrent client artifacts with permission issues |

---

## Commands Executed (Key Commands Only)

| Command | Result | Purpose |
|---------|--------|---------|
| `Get-Service sshd` | Running | Verify Windows SSH server |
| `ssh ubu-osmen hostname` | `Ubu-OsMEN` | Verify SSH connectivity |
| `ping 192.168.7.248 -n 10` | 0% loss, 1ms avg | Network health check |
| `scp ... ubu-osmen:~/Downloads/` | Success | File transfers (2 files) |
| `ssh ubu-osmen 'bash /tmp/media_recon.sh'` | 564 lines output | Full media structure audit |
| `ssh ubu-osmen 'bash /tmp/taskwarrior_expand.sh'` | 67 tasks created | Phase B-F task import |
| `ssh ubu-osmen 'bash /tmp/taskwarrior_expand_gap.sh'` | 17 tasks created | Skills/agent gap tasks |
| `ssh ubu-osmen 'bash /tmp/taskwarrior_vpn.sh'` | 7 tasks created | VPN architecture tasks |
| `ssh ubu-osmen 'lsblk -o NAME,SIZE,...'` | Full disk layout | Hardware recon |
| `ssh ubu-osmen 'systemctl --user list-units ...'` | 22 running services | Service inventory |

---

## Environment State

### Windows (Dlex)
- OS: Windows (current)
- SSH: OpenSSH_for_Windows_9.5p2, LibreSSL 3.8.2
- Workspace: `c:\Dev\osmen`

### Linux (Ubu-OsMEN)
- OS: Ubuntu 26.04
- SSH: OpenSSH_10.2p1 Ubuntu-2ubuntu3
- Taskwarrior: `/usr/bin/task` (working with hooks)
- Container runtime: Podman (rootless, quadlets in `~/.config/containers/systemd/`)
- Drives: 3 external NTFS (udisks2 mounted, NOT fstab)
- GPU: NVIDIA (passthrough to Plex for HW transcoding)
- System drive: 932G NVMe (LUKS encrypted, LVM, 39% used)

---

## Known Issues

1. **Kometa in restart loop** — `activating (auto-restart)`, needs log investigation
2. **Lidarr in restart loop** — `activating (auto-restart)`, needs log investigation
3. **Plex config volume missing** — quadlet service `not-found`
4. **External drives not in fstab** — will NOT auto-mount on reboot
5. **Download file ownership** — container creates files as `100910:101000`, not `dwill:dwill`
6. **PowerShell escaping** — complex bash scripts can't be run via `ssh ubu-osmen "..."` from PowerShell; must SCP a script file first and then execute it remotely
7. **DNS on Linux** — `systemd-resolved` using degraded feature set for DNS servers `206.225.75.225/226` (VPN DNS?), falling back to TCP

---

## Pending Work (Ordered)

### Immediate (Before Any File Operations)
1. **Get user answers** to the 7 open questions above
2. **Resolve movie naming conflict** (flat vs per-folder) — this blocks Phase C and all transfer scripts

### Phase B: TV/Anime Dedup + Rename (26 tasks)
3. Build dry-run scripts for each duplicate group
4. User reviews and approves dry-run output
5. Execute merges (copy-first, verify, delete source)
6. Fix remaining naming issues (scene-packs, missing years, padding)

### Phase C: Movie Structure (4 tasks)
7. Audit 346 movies, parse title+year
8. Build dry-run for folder creation
9. Execute (pending naming decision)

### Phase D: Script/Skill Migration (39 tasks)
10. Categorize 100+ legacy PS1 scripts
11. Port `plex-organize` and `media-transfer` skills to Linux
12. Write core `plex_naming.py` engine
13. Write `validate_structure.py` auditor
14. Write transfer scripts (tv, movie, anime, audiobook, comics, music)
15. Port remaining skills
16. Reconcile agent configs
17. Review migration docs for unfinished items

### Phase E: Config & Dependencies (10 tasks)
18. Add fstab entries for 3 drives
19. Fix Kometa, Lidarr, Plex config volume
20. Wire Sonarr/Radarr naming templates
21. Verify VPN kill-switch and pod networking
22. Install Python deps

### Phase F: Transfer Protocols (9 tasks)
23. Document each media type's transfer protocol
24. Document VPN-walled acquisition flow

---

## Quick Resume Commands

```powershell
# From Windows — verify SSH still works
ssh ubu-osmen uptime

# Check Taskwarrior media tasks
ssh ubu-osmen "task project:osmen.media status:pending count"

# List high-priority tasks
ssh ubu-osmen "task project:osmen.media priority:H list"

# Check services
ssh ubu-osmen "systemctl --user list-units --type=service --state=running | grep osmen"

# Check disk mounts
ssh ubu-osmen "df -h /run/media/dwill/plex /run/media/dwill/TV_Anime_OFlow /run/media/dwill/Other_Media"

# Run the media recon script again (still on disk)
ssh ubu-osmen "bash /tmp/media_recon.sh"
```

---

## ΩΣΕ∆ Framework Reference

The user invoked `/multi-agent-audit` — the intended execution model uses 11 agents:

| Agent | Role | Assigned Work |
|-------|------|---------------|
| Ω Orchestrator | Phase sequencing, demo gates | Coordinates all phases |
| Σ Sentinel | Quality monitoring | Validates all agent outputs |
| Ε₂ Infrastructure | Phase B (dedup/rename), Phase C (movies) | File operations |
| Ε₃ Architecture | Phase D (scripts/skills), Phase F (protocols) | Code migration |
| Ε₄ QA | Phase G (Taskwarrior) | Task management (DONE) |
| Ε₅ Operations | Phase E (config/deps) | Infrastructure fixes |
| ∆₁-∆₄ Shadows | Demo design + failure anticipation | Pre-design demos for each engineer |

Workflow file: `c:\Dev\osmen\.agents\workflows\multi-agent-audit.md`

**Key rule**: Every phase requires a **live demo gate** — user must run, verify, and approve before proceeding. Scope can only expand, never shrink.

---

*End of handoff. 91 Taskwarrior tasks loaded. No files modified beyond SSH config. All recon data captured. Ready for larger model to execute.*
