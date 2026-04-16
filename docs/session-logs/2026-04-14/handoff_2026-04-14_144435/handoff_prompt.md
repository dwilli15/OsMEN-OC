# ΩΣΕ∆ Media Library Normalization — Handoff Prompt

You are resuming an in-progress project. A previous agent session spent roughly 6 hours performing deep reconnaissance of a media library spread across 3 external hard drives attached to a Linux machine. That agent created 91 granular Taskwarrior tasks, a full implementation plan, and documented every issue found. No files were moved, renamed, or deleted — the previous session was research-and-planning only. You are picking up at execution.

The work is governed by the ΩΣΕ∆ multi-agent audit framework, which uses 11 coordinated agents working in phases with live demo gates between each phase. The user explicitly stated that most of the actual work will be done by other agents, and that every phase must include a dry-run that the user reviews and approves before any file operations happen. Scope can only expand, never shrink.

---

## The Two Machines

There are two machines on the same LAN that can SSH to each other with key-based auth (ed25519). Both directions are verified working.

**Linux Machine** — this is where all the media lives and where all the work happens:
- Hostname: `Ubu-OsMEN`
- IP: `192.168.7.248`
- User: `dwill`
- OS: Ubuntu 26.04
- Container runtime: Podman (rootless, using systemd quadlet files in `/home/dwill/.config/containers/systemd/`)
- SSH config: `/home/dwill/.ssh/config`
- System drive: 932G NVMe (LUKS encrypted, LVM, 39% used)
- From the Windows machine you can connect with just `ssh ubu-osmen`

**Windows Machine** — this is the secondary machine that has source code, agent configs, and OneDrive backups:
- Hostname: `Dlex`
- IP: `192.168.7.249`
- User: `armad`
- SSH config: `C:\Users\armad\.ssh\config`
- From the Linux machine you can connect with just `ssh Dlex`

**Important note about PowerShell escaping**: If you are running on Windows and trying to execute complex bash commands on Linux via `ssh ubu-osmen "..."`, PowerShell will mangle the quotes and kill your bash syntax. The proven workaround from this session is to write your bash script to a local file, SCP it to `/tmp/` on the Linux machine, then SSH in and execute it with `bash /tmp/yourscript.sh`.

---

## Files You Must Read

The previous session generated a full handoff package. These files exist in identical copies on both machines. Read them from whichever machine you're on.

**The exhaustive handoff report** is the most important document. It's approximately 600 lines and contains: the complete SSH setup, full hardware and storage layout, every one of the 22 running Podman services with health status, the VPN-walled download pod architecture, every media structure issue found (duplicates, bad naming, missing years, scene-pack folders, inconsistent season padding), a full inventory of 100+ legacy PowerShell scripts, all 8 existing Claude skills that need porting from Windows to Linux, the 91 Taskwarrior task breakdown, all 7 open questions that need user answers, every decision made during the session, and the ordered list of pending work.

- Linux path: `/home/dwill/dev/OsMEN-OC/docs/session-logs/2026-04-14/handoff_2026-04-14_144435/handoff.md`
- Windows path: `C:\Dev\osmen\docs\session-logs\2026-04-14\handoff_2026-04-14_144435\handoff.md`

**The implementation plan** is the ΩΣΕ∆ phased execution plan covering Phase B (TV and anime deduplication and renaming), Phase C (movie structure normalization), Phase D (script, skill, and agent migration from PowerShell to bash/python), Phase E (configuration and dependencies including fstab, broken services), and Phase F (transfer protocol documentation). It includes user-review-required warnings about a movie naming conflict and the Windows-to-Linux skills gap.

- Linux path: `/home/dwill/dev/OsMEN-OC/docs/session-logs/2026-04-14/handoff_2026-04-14_144435/implementation_plan.md`
- Windows path: `C:\Dev\osmen\docs\session-logs\2026-04-14\handoff_2026-04-14_144435\implementation_plan.md`

**The raw recon output** is 564 lines of the actual output from a bash audit script that was run against all 3 media drives. For every TV show and anime series, it lists the show name, the number of season directories found, the number of loose files, the total episode count, and the number of subdirectories. It also lists every script file found on the media drives and in the OsMEN dev directory.

- Linux path: `/home/dwill/dev/OsMEN-OC/docs/session-logs/2026-04-14/handoff_2026-04-14_144435/recon_output.txt`
- Windows path: `C:\Dev\osmen\docs\session-logs\2026-04-14\handoff_2026-04-14_144435\recon_output.txt`

---

## The Storage Layout

There are 3 external NTFS hard drives attached to the Linux machine. They are currently mounted via udisks2 (auto-mount on user login), but critically, they are NOT in fstab, which means they will disappear on reboot. Adding fstab entries is Task E.1 and should be done early.

The **primary media drive** is a 4.5 terabyte WD Elements mounted at `/run/media/dwill/plex`. It is 55% full with 2.1TB free. This is where the main Plex library lives under `/run/media/dwill/plex/Media/` with subdirectories for `TV/` (58 shows), `Anime/` (7 shows), `Movies/` (346 loose files), `Comics/`, and `Other/`. The drive root also contains a huge amount of legacy material from the old Windows setup: about 100+ PowerShell and Python scripts scattered across `agent-in/`, `tools/`, `temp/`, `tmp/`, and `media-research/` directories, plus agent identity files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`), Claude skill files under `.claude/skills/`, and various JSON config files.

The **overflow drive** is a 1.8 terabyte WD My Passport mounted at `/run/media/dwill/TV_Anime_OFlow`. It is only 6% full. It holds 4 TV shows (`Alias`, `Chuck`, `The Newsroom`, `The West Wing`) and 1 anime (`Justice League`) under `/run/media/dwill/TV_Anime_OFlow/Media/`. The shows on this drive use a different season naming convention (`S01`, `S02`) than the main plex drive (`Season 01`, `Season 02`).

The **other media drive** is a 932GB Samsung SSD 870 mounted at `/run/media/dwill/Other_Media`. It is 63% full and contains light novels under `Officially Translated Light Novels/` and miscellaneous media under `Media/Other/`.

There are also empty placeholder directories at `/home/dwill/media/` with subdirectories for `audiobooks/`, `books/`, `comics/`, `manga/`, `music/`, `plex/`, and `podcasts/`. These were created as intended mount targets or symlink anchors but are currently empty.

---

## The VPN-Walled Download Architecture

This is critical context for all transfer and acquisition scripts. The torrent and usenet download clients do NOT run on the bare metal host. They run inside a Podman pod called `download-stack.pod` that shares the network namespace of a gluetun VPN gateway container. This means all torrent and usenet traffic is forced through the VPN tunnel, and if the VPN drops, the kill-switch should prevent any traffic from leaking.

Specifically: `osmen-media-qbittorrent` (Web UI on `127.0.0.1:9090`) and `osmen-media-sabnzbd` (Web UI on `127.0.0.1:8082`) both have `Requires=osmen-media-gluetun.service` and `Pod=download-stack.pod` in their quadlet files. Both download to `/home/dwill/Downloads` via a volume mount.

There is a file ownership issue: files downloaded inside the containers are created with UID `100910` and GID `101000`, not `dwill:dwill` (`1000:1000`). Any transfer script that needs to move, rename, or read these files must handle the ownership mismatch, either by running `chown` or by using ACLs.

---

## What's Broken

Three services are unhealthy:
- `osmen-media-kometa` is stuck in an auto-restart loop. This is the Plex metadata manager (Kometa). Its logs need investigation to find the config error. This is Task E.2.
- `osmen-media-lidarr` is stuck in an auto-restart loop. This is the music acquisition manager. Its logs need investigation. This is Task E.3.
- `osmen-plex-config-volume` has a `not-found` status, meaning the quadlet service file is missing. This is Task E.4.

---

## The Existing Skills on the Plex Drive

There are 8 Claude skills in `/run/media/dwill/plex/.claude/skills/` and 3 more in `/run/media/dwill/plex/agent-in/.claude/skills/`. These were written for the old Windows setup and all reference Windows paths (`D:\Media\*`), PowerShell commands, and Windows APIs. They are the source of truth for the media naming conventions and transfer protocols, but they need complete rewriting for the Linux environment.

The two most important ones are:

`plex-organize` at `/run/media/dwill/plex/.claude/skills/plex-organize/SKILL.md` — this defines the canonical naming conventions for movies, TV, and anime. Key rules: movies must be flat files directly in the Movies folder (NO per-movie subdirectories), TV shows use `Show Name (Year)/Season XX/Show Name (Year) - sXXeYY - Episode Title.ext`, anime follows the same pattern as TV but in a separate `Anime/` root. Season folders must be zero-padded (`Season 01`, never `Season 1`).

`media-transfer` at `/run/media/dwill/plex/.claude/skills/media-transfer/skill.md` — this defines an elaborate 7-phase transfer protocol: Phase 0 clears completed torrents from qBittorrent, Phase 1 discovers and hashes all source files, Phase 2 classifies them as movie/TV/anime, Phase 3 handles subtitles, Phase 4 copies files to their Plex destinations, Phase 5 does SHA256 hash verification AND Plex API verification (checking `Part.file` in Plex's XML), Phase 6 shows results and gets user permission, Phase 7 deletes sources only after triple verification. This entire protocol is PowerShell and needs to be rewritten.

**There is a naming conflict**: the `plex-organize` skill says movies must be flat (no subdirectories), but Plex's own documentation recommends per-movie folders for better metadata matching. The user needs to pick one standard, and the decision affects 346+ existing files and all future acquisitions.

---

## What's on the Windows Side

The Windows machine has source material that informs the migration:

- `C:\Dev\osmen\` is the main OsMEN workspace with the `config/launchers/media.yaml` launcher config (still references `D:\`), taskwarrior sync scripts in `scripts/taskwarrior/`, and the ΩΣΕ∆ workflow definition at `C:\Dev\osmen\.agents\workflows\multi-agent-audit.md`
- `C:\Users\armad\OneDrive\Documents\osmen-migration\` has a 326KB `MIGRATION_CHANGELOG.md` documenting the Windows-to-Linux migration, plus a 20GB `osmen-snapshot.tar`, post-install scripts, and gap analysis reports
- `C:\Users\armad\OneDrive\Documents\oc_backup\plans\` has 18 planning documents from the migration era including a dual-boot migration spec and the OsMEN Control Center spec
- `C:\Users\armad\OneDrive\Documents\osmen-agent-handoffs\2026-04-02_ubuntu26_linux_local_agent_handoff_slim\` has the 7-section handoff from the Ubuntu install

These Windows-side files don't need to be acted on directly — they're context for understanding what was planned vs what actually got migrated.

---

## The Taskwarrior Tasks

There are 91 pending tasks under `project:osmen.media` in Taskwarrior on the Linux machine. They were batch-imported via scripts during this session. Each task has a priority (H, M, or L), a phase tag (`+phaseB` through `+phaseF`), and one or more category tags. Here's how to query them:

- `task project:osmen.media priority:H list` — shows the 20 highest-priority, critical-path tasks
- `task project:osmen.media +phaseB list` — 26 tasks for TV and anime deduplication and renaming
- `task project:osmen.media +phaseC list` — 4 tasks for movie structure normalization
- `task project:osmen.media +phaseD list` — 39 tasks for script, skill, and agent migration
- `task project:osmen.media +phaseE list` — 10 tasks for configuration, dependencies, and broken service fixes
- `task project:osmen.media +phaseF list` — 9 tasks for transfer protocol documentation
- `task project:osmen.media +dedup list` — just the duplicate-merge tasks
- `task project:osmen.media +rename list` — just the rename tasks
- `task project:osmen.media +vpn list` — 7 tasks specifically about the VPN-walled pod architecture
- `task project:osmen.media +skills list` — 8 tasks for porting skills from Windows to Linux
- `task project:osmen.media +naming list` — 3 tasks for naming convention decisions
- `task project:osmen.media +agents list` — 6 tasks for reconciling agent config files

To mark a task as in-progress: `task <ID> start`. To mark it done: `task <ID> done`.

Taskwarrior hooks at `/home/dwill/.task/hooks/on-add-osmen.py` and `on-modify-osmen.py` queue task events into an OsMEN-OC SQLite event bus. The config is at `/home/dwill/.taskrc`.

---

## The 7 Open Questions (Must Be Answered Before Execution)

These were identified during recon and block multiple tasks:

1. **DTF St. Louis** — one of the duplicate TV show groups. We don't know the premiere year, which is needed for the canonical folder name `DTF St Louis (YYYY)`. The user needs to provide the year.

2. **Daredevil Born Again** — its only directory is `Season 02` with just 1 episode. Is Season 02 correct (i.e., it's a continuation of the original Daredevil series), or should this be Season 01 (i.e., it's a new show)?

3. **Avatar The Last Airbender Extras** — there's a `Featurettes & Extras` subdirectory alongside the 3 season directories. Should it be preserved as an `Extras/` folder, or can it be discarded?

4. **Movie quality preference** — when duplicate episodes or movies are found across the fragmented directories, which quality should be kept? Should the rule be 1080p BluRay > 720p > WEB-DL, or simply "highest resolution always wins"?

5. **Overflow drive strategy** — the overflow drive has only 4 TV shows and 1 anime on a 1.8TB drive that's 94% empty. Should that content be merged back onto the main plex drive (which has 2.1TB free), or should it stay split across drives?

6. **Acquisition scripts** — the user mentioned that media acquisition can be a placeholder if the agent isn't comfortable helping back up their physical library. Confirm: should acquisition scripts be stubs only for now?

7. **Movie naming: flat or per-folder?** — this is the biggest blocking question. The existing `plex-organize` and `media-transfer` skills both enforce a flat movie structure (`Movies/Movie (Year).ext` with no subdirectories), but Plex's official documentation recommends per-movie folders (`Movies/Movie (Year)/Movie (Year).ext`). The user must pick one standard. This decision affects 346+ existing movie files, all transfer scripts, and the core naming engine that needs to be written.

---

## Recommended Execution Order

1. Ask the user the 7 open questions above
2. Task E.1 — add fstab entries for the 3 external drives (they'll vanish on reboot otherwise)
3. Phase B — TV and anime dedup and rename (start with dry-runs for the 4 duplicate groups)
4. Phase C — movie structure normalization (blocked on question 7)
5. Phase E.2-E.4 — fix Kometa, Lidarr, and Plex config volume
6. Phase D — script, skill, and agent migration (the bulk of the work)
7. Phase F — transfer protocol documentation

For every phase, produce a dry-run first, show it to the user, get approval, then execute. Copy files before deleting sources. Verify file counts before and after.
