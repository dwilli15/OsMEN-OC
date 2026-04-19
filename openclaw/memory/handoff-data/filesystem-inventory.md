# OsMEN-OC Filesystem Inventory
**Generated:** 2026-04-18 21:02 CDT  
**Host:** Ubu-OsMEN (Linux 7.0.0-14-generic x64)

---

## 1. Quadlet Files (`~/.config/containers/systemd/`)

All are **symlinks** to `/home/dwill/dev/OsMEN-OC/quadlets/`. Source of truth is the repo.

### Pods
| Symlink | Target |
|---|---|
| `/home/dwill/.config/containers/systemd/download-stack.pod` | `…/quadlets/media/download-stack.pod` |

### Containers (Active)
| Symlink | Target |
|---|---|
| `/home/dwill/.config/containers/systemd/osmen-core-caddy.container` | `…/quadlets/core/osmen-core-caddy.container` |
| `/home/dwill/.config/containers/systemd/osmen-core-chromadb.container` | `…/quadlets/core/osmen-core-chromadb.container` |
| `/home/dwill/.config/containers/systemd/osmen-core-gateway.container` | `…/quadlets/core/osmen-core-gateway.container` |
| `/home/dwill/.config/containers/systemd/osmen-core-langflow.container` | `…/quadlets/core/osmen-core-langflow.container` |
| `/home/dwill/.config/containers/systemd/osmen-core-miniflux.container` | `…/quadlets/core/osmen-core-miniflux.container` |
| `/home/dwill/.config/containers/systemd/osmen-core-paperless.container` | `…/quadlets/core/osmen-core-paperless.container` |
| `/home/dwill/.config/containers/systemd/osmen-core-postgres.container` | `…/quadlets/core/osmen-core-postgres.container` |
| `/home/dwill/.config/containers/systemd/osmen-core-redis.container` | `…/quadlets/core/osmen-core-redis.container` |
| `/home/dwill/.config/containers/systemd/osmen-core-siyuan.container` | `…/quadlets/core/osmen-core-siyuan.container` |
| `/home/dwill/.config/containers/systemd/osmen-dashboard-homepage.container` | `…/quadlets/dashboard/osmen-dashboard-homepage.container` |
| `/home/dwill/.config/containers/systemd/osmen-librarian-audiobookshelf.container` | `…/quadlets/librarian/osmen-librarian-audiobookshelf.container` |
| `/home/dwill/.config/containers/systemd/osmen-librarian-convertx.container` | `…/quadlets/librarian/osmen-librarian-convertx.container` |
| `/home/dwill/.config/containers/systemd/osmen-librarian-whisper.container` | `…/quadlets/librarian/osmen-librarian-whisper.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-bazarr.container` | `…/quadlets/media/osmen-media-bazarr.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-gluetun.container` | `…/quadlets/media/osmen-media-gluetun.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-kometa.container` | `…/quadlets/media/osmen-media-kometa.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-komga-comics.container` | `…/quadlets/media/osmen-media-komga-comics.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-lidarr.container` | `…/quadlets/media/osmen-media-lidarr.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-mylar3.container` | `…/quadlets/media/osmen-media-mylar3.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-plex.container` | `…/quadlets/media/osmen-media-plex.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-prowlarr.container` | `…/quadlets/media/osmen-media-prowlarr.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-qbittorrent.container` | `…/quadlets/media/osmen-media-qbittorrent.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-radarr.container` | `…/quadlets/media/osmen-media-radarr.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-readarr.container` | `…/quadlets/media/osmen-media-readarr.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-sabnzbd.container` | `…/quadlets/media/osmen-media-sabnzbd.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-sonarr.container` | `…/quadlets/media/osmen-media-sonarr.container` |
| `/home/dwill/.config/containers/systemd/osmen-media-tautulli.container` | `…/quadlets/media/osmen-media-tautulli.container` |
| `/home/dwill/.config/containers/systemd/osmen-monitoring-grafana.container` | `…/quadlets/monitoring/osmen-monitoring-grafana.container` |
| `/home/dwill/.config/containers/systemd/osmen-monitoring-portall.container` | `…/quadlets/monitoring/osmen-monitoring-portall.container` |
| `/home/dwill/.config/containers/systemd/osmen-monitoring-prometheus.container` | `…/quadlets/monitoring/osmen-monitoring-prometheus.container` |
| `/home/dwill/.config/containers/systemd/osmen-monitoring-uptimekuma.container` | `…/quadlets/monitoring/osmen-monitoring-uptimekuma.container` |
| `/home/dwill/.config/containers/systemd/osmen-tools-bentopdf.container` | `…/quadlets/tools/osmen-tools-bentopdf.container` |

### Containers (Disabled — `.disabled` suffix)
| Symlink | Target |
|---|---|
| `/home/dwill/.config/containers/systemd/osmen-core-nextcloud.container.disabled` | `…/quadlets/core/osmen-core-nextcloud.container` |
| `/home/dwill/.config/containers/systemd/osmen-librarian-kavita.container.disabled` | `…/quadlets/librarian/osmen-librarian-kavita.container` |

### Networks
| Symlink | Target |
|---|---|
| `/home/dwill/.config/containers/systemd/osmen-core.network` | `…/quadlets/core/osmen-core.network` |
| `/home/dwill/.config/containers/systemd/osmen-media.network` | `…/quadlets/media/osmen-media.network` |

### Volumes (35 symlinks)
All symlinked to `…/quadlets/volumes/` or `…/quadlets/core/` or `…/quadlets/media/` or `…/quadlets/dashboard/`:
- `/home/dwill/.config/containers/systemd/osmen-audiobookshelf-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-audiobookshelf-metadata.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-bazarr-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-caddy-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-caddy-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-chromadb-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-convertx-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-grafana-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-homepage-config.volume` → `…/quadlets/dashboard/`
- `/home/dwill/.config/containers/systemd/osmen-kavita-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-kometa-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-langflow-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-lidarr-config.volume` → `…/quadlets/media/`
- `/home/dwill/.config/containers/systemd/osmen-mylar3-config.volume` → `…/quadlets/media/`
- `/home/dwill/.config/containers/systemd/osmen-nextcloud-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-ollama-models.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-paperless-data.volume` → `…/quadlets/core/`
- `/home/dwill/.config/containers/systemd/osmen-paperless-media.volume` → `…/quadlets/core/`
- `/home/dwill/.config/containers/systemd/osmen-plex-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-portall-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-postgres-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-prometheus-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-prowlarr-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-qbit-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-radarr-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-readarr-config.volume` → `…/quadlets/media/`
- `/home/dwill/.config/containers/systemd/osmen-redis-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-sab-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-sonarr-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-tautulli-config.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-uptimekuma-data.volume` → `…/quadlets/volumes/`
- `/home/dwill/.config/containers/systemd/osmen-whisper-models.volume` → `…/quadlets/volumes/`

### Slices
| Symlink | Target |
|---|---|
| `/home/dwill/.config/containers/systemd/user-osmen-background.slice` | `…/quadlets/slices/user-osmen-background.slice` |
| `/home/dwill/.config/containers/systemd/user-osmen-core.slice` | `…/quadlets/core/user-osmen-core.slice` |
| `/home/dwill/.config/containers/systemd/user-osmen-dashboard.slice` | `…/quadlets/dashboard/user-osmen-dashboard.slice` |
| `/home/dwill/.config/containers/systemd/user-osmen-inference.slice` | `…/quadlets/slices/user-osmen-inference.slice` |
| `/home/dwill/.config/containers/systemd/user-osmen-media.slice` | `…/quadlets/slices/user-osmen-media.slice` |
| `/home/dwill/.config/containers/systemd/user-osmen-services.slice` | `…/quadlets/slices/user-osmen-services.slice` |

---

## 2. OpenClaw Workspace (`/home/dwill/dev/OsMEN-OC/openclaw/`)

### Root Files
| Path | Purpose |
|---|---|
| `/home/dwill/dev/OsMEN-OC/openclaw/AGENTS.md` | Agent behavior rules |
| `/home/dwill/dev/OsMEN-OC/openclaw/SOUL.md` | Persona definition |
| `/home/dwill/dev/OsMEN-OC/openclaw/USER.md` | User profile (D) |
| `/home/dwill/dev/OsMEN-OC/openclaw/IDENTITY.md` | Agent identity metadata |
| `/home/dwill/dev/OsMEN-OC/openclaw/MEMORY.md` | Long-term curated memory |
| `/home/dwill/dev/OsMEN-OC/openclaw/TOOLS.md` | Local tool notes |
| `/home/dwill/dev/OsMEN-OC/openclaw/HEARTBEAT.md` | Heartbeat checklist |
| `/home/dwill/dev/OsMEN-OC/openclaw/vampires_dancing.png` | Image asset |
| `/home/dwill/dev/OsMEN-OC/openclaw/vampires_dancing2.png` | Image asset |
| `/home/dwill/dev/OsMEN-OC/openclaw/.openclaw/workspace-state.json` | OpenClaw internal state |

### Subagent Workspaces
Each has: `AGENTS.md`, `BOOTSTRAP.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `HEARTBEAT.md`, `TOOLS.md`

- `/home/dwill/dev/OsMEN-OC/openclaw/basic/` — Basic agent
- `/home/dwill/dev/OsMEN-OC/openclaw/coder/` — Coding agent
- `/home/dwill/dev/OsMEN-OC/openclaw/researcher/` — Research agent
- `/home/dwill/dev/OsMEN-OC/openclaw/reviewer/` — Review agent
- `/home/dwill/dev/OsMEN-OC/openclaw/auditor/` — Audit agent (also has `auth-profiles.json`, `models.json`)

### Taskwarrior Data
- `/home/dwill/dev/OsMEN-OC/openclaw/tw/pending.data`
- `/home/dwill/dev/OsMEN-OC/openclaw/tw/completed.data`

### State
- `/home/dwill/dev/OsMEN-OC/openclaw/state/install-audit-dispatch.md`

---

## 3. Memory Files

### `/home/dwill/dev/OsMEN-OC/openclaw/memory/`

#### Daily Logs
| File | Size | Notes |
|---|---|---|
| `2026-04-11.md` | 234B | Initial day |
| `2026-04-14.md` | 1.6K | Multi-agent exploration |
| `2026-04-14-1438.md` | 1.6K | Session notes |
| `2026-04-14-1909.md` | 179B | Session notes |
| `2026-04-14-multi-agent-options.md` | 13.9K | Multi-agent architecture analysis |
| `2026-04-14-ptyxis-launch-tabs-fix.md` | 6.5K | Ptyxis terminal fix |
| `2026-04-16.md` | 8.9K | Platform day |
| `2026-04-17.md` | 27.5K | Major session (permissions: 600) |
| `2026-04-18.md` | 6.7K | Latest daily log |
| `2026-04-18-expert-handoff.md` | 8.1K | Expert handoff brief |
| `2026-04-18-handoff-expert.md` | 8.1K | Duplicate of above |
| `2026-04-19-heartbeat-check.md` | 6.3K | Heartbeat check |

#### Handoff & Planning Documents
| File | Size |
|---|---|
| `osmen-handoff-2026-04-16.md` | 10K |
| `osmen-handoff-2026-04-17.md` | 13.9K |
| `osmen-handoff-2026-04-18.md` | 15.5K |
| `osmen-handoff-2026-04-18-session2.md` | 8K |
| `osmen-handoff-2026-04-18-session3-audit.md` | 11.9K |
| `osmen-handoff-2026-04-18-final.md` | 6.1K |
| `osmen-expert-agent-brief-2026-04-18.md` | 2.8K |
| `osmen-honest-state-2026-04-18.md` | 7.9K |
| `osmen-install-audit-2026-04-18-live.md` | 5.5K |
| `osmen-stabilization-plan-2026-04-18.md` | 17K |
| `osmen-stabilization-plan-final-2026-04-18.md` | 5.1K |
| `osmen-master-plan-2026-04-18.md` | 77.7K |
| `audit-2026-04-18-72h.md` | 6.9K |
| `p13-plex-phase-spec.md` | 10.6K |

#### Subdirectories
- `/home/dwill/dev/OsMEN-OC/openclaw/memory/.dreams/` — Private dreams directory
- `/home/dwill/dev/OsMEN-OC/openclaw/memory/handoff-data/` — This inventory lives here
- `/home/dwill/dev/OsMEN-OC/openclaw/memory/plan-research/` — Recon and planning research (see below)

### Plan Research (`/home/dwill/dev/OsMEN-OC/openclaw/memory/plan-research/`)
| File | Size | Purpose |
|---|---|---|
| `architecture-review.md` | 13.2K | Architecture analysis |
| `online-research.md` | 13.1K | Web research findings |
| `recon-01-containers.md` | 12K | Container inventory |
| `recon-02-systemd.md` | 4.6K | Systemd state |
| `recon-03-network.md` | 7.6K | Network config |
| `recon-04-storage.md` | 5.3K | Storage layout |
| `recon-05-services.md` | 4.8K | Service inventory |
| `recon-06-quadlets.md` | 38.8K | Full quadlet dump |
| `recon-07-inference.md` | 6.4K | ML/AI inference setup |
| `recon-08-openclaw.md` | 7.2K | OpenClaw config review |
| `recon-09-host.md` | 4.4K | Host system info |
| `recon-10-research.md` | 11.7K | Research backlog |
| `repo-analysis.md` | 14.8K | Git repo analysis |
| `taskflow-tw-integration.md` | 6.7K | TaskWarrior integration plan |
| `tw-audit.md` | 10.7K | TaskWarrior audit |
| `user-input-batch.md` | 14.5K | Batched user requirements |

---

## 4. Scripts (`/home/dwill/dev/OsMEN-OC/scripts/`)

### Root Scripts
| Path | Purpose |
|---|---|
| `/home/dwill/dev/OsMEN-OC/scripts/bootstrap.sh` | Initial bootstrap |
| `/home/dwill/dev/OsMEN-OC/scripts/backup.sh` | Backup utility |
| `/home/dwill/dev/OsMEN-OC/scripts/deploy_quadlets.sh` | Quadlet deployment |
| `/home/dwill/dev/OsMEN-OC/scripts/deploy_timers.sh` | Timer deployment |
| `/home/dwill/dev/OsMEN-OC/scripts/verify-versions.sh` | Version verification |
| `/home/dwill/dev/OsMEN-OC/scripts/resource_audit.sh` | Resource audit |
| `/home/dwill/dev/OsMEN-OC/scripts/lemonade-autoload.sh` | Lemonade server autostart |
| `/home/dwill/dev/OsMEN-OC/scripts/tw-stabilization-plan.sh` | TW stabilization |
| `/home/dwill/dev/OsMEN-OC/scripts/sync_memory_bank.py` | Memory sync |
| `/home/dwill/dev/OsMEN-OC/scripts/generate_working_memory.py` | Working memory gen |
| `/home/dwill/dev/OsMEN-OC/scripts/ingest_handoffs.py` | Handoff ingestion |
| `/home/dwill/dev/OsMEN-OC/scripts/manga_downloader.py` | Manga download |
| `/home/dwill/dev/OsMEN-OC/scripts/manga_bulk_v2.py` | Manga bulk v2 |
| `/home/dwill/dev/OsMEN-OC/scripts/manga_bulk_v3.py` | Manga bulk v3 |
| `/home/dwill/dev/OsMEN-OC/scripts/manga_bulk_v4.py` | Manga bulk v4 |
| `/home/dwill/dev/OsMEN-OC/scripts/manga_postprocess.py` | Manga post-processing |
| `/home/dwill/dev/OsMEN-OC/scripts/_bulk_manga.py` | Manga bulk helper |
| `/home/dwill/dev/OsMEN-OC/scripts/_bulk_run.py` | Bulk run helper |

### Secrets
| Path | Purpose |
|---|---|
| `/home/dwill/dev/OsMEN-OC/scripts/secrets/export_credential_kit.sh` | Credential export |

### Hooks
| Path | Purpose |
|---|---|
| `/home/dwill/dev/OsMEN-OC/scripts/hooks/pre-commit-secrets` | Git pre-commit hook for secrets |

### TaskWarrior Hooks
| Path | Purpose |
|---|---|
| `/home/dwill/dev/OsMEN-OC/scripts/taskwarrior/on-add-osmen.py` | TW on-add hook |
| `/home/dwill/dev/OsMEN-OC/scripts/taskwarrior/on-modify-osmen.py` | TW on-modify hook |
| `/home/dwill/dev/OsMEN-OC/scripts/taskwarrior-hooks/README.md` | TW hooks docs |

### App Drawer Scripts
| Path | Purpose |
|---|---|
| `/home/dwill/dev/OsMEN-OC/scripts/appdrawer/start-claude-osmen.sh` | Claude OsMEN launcher |
| `/home/dwill/dev/OsMEN-OC/scripts/appdrawer/start-claude-osmen.sh.bak.20260412-083515` | Backup of launcher |
| `/home/dwill/dev/OsMEN-OC/scripts/appdrawer/start-osmen-tmux.sh` | Tmux OsMEN launcher |
| `/home/dwill/dev/OsMEN-OC/scripts/appdrawer/tmux-osmen.conf` | Tmux config for OsMEN |
| `/home/dwill/dev/OsMEN-OC/scripts/appdrawer/claude-osmen.desktop` | Desktop entry |

### Media Scripts
| Path | Purpose |
|---|---|
| `/home/dwill/dev/OsMEN-OC/scripts/media/naming/validate_structure.py` | Validate media naming |
| `/home/dwill/dev/OsMEN-OC/scripts/media/naming/plex_naming.py` | Plex naming conventions |
| `/home/dwill/dev/OsMEN-OC/scripts/media/transfer/movie_transfer.sh` | Movie transfer |
| `/home/dwill/dev/OsMEN-OC/scripts/media/acquisition/mangadex_dl.py` | MangaDex downloader |
| `/home/dwill/dev/OsMEN-OC/scripts/media/acquisition/monitor_downloads.py` | Download monitor |
| `/home/dwill/dev/OsMEN-OC/scripts/media/acquisition/queue_all_dc_comics.py` | DC comics queue |
| `/home/dwill/dev/OsMEN-OC/scripts/media/acquisition/placeholder.md` | Placeholder notes |
| `/home/dwill/dev/OsMEN-OC/scripts/media/plex/health_check.py` | Plex health check |
| `/home/dwill/dev/OsMEN-OC/scripts/media/plex/plex_collections.py` | Plex collection mgmt |
| `/home/dwill/dev/OsMEN-OC/scripts/media/plex/fix_tv_anime_naming.py` | TV/anime naming fix |
| `/home/dwill/dev/OsMEN-OC/scripts/media/plex/scan_library.py` | Library scan trigger |
| `/home/dwill/dev/OsMEN-OC/scripts/media/maintenance/orphan_cleanup.py` | Orphan file cleanup |
| `/home/dwill/dev/OsMEN-OC/scripts/media/maintenance/quality_audit.py` | Media quality audit |
| `/home/dwill/dev/OsMEN-OC/scripts/media/maintenance/dedup_check.py` | Deduplication check |

### /tmp Scripts
None found.

---

## 5. Media Paths (`/home/dwill/media/`)

### Symlinks
| Path | Target | Notes |
|---|---|---|
| `/home/dwill/media/audiobooks` | `/mnt/plex/Media/Other/Audiobooks` | NTFS drive sdb1 |
| `/home/dwill/media/comics` | `/mnt/other-media/Media/Other/Comics` | NTFS drive sdc2 |
| `/home/dwill/media/manga` | `/mnt/other-media/Manga` | NTFS drive sdc2 (ACL) |
| `/home/dwill/media/manga-downloads` | `/mnt/other-media/Manga` | Same target as manga (ACL) |
| `/home/dwill/media/plex` | `/mnt/plex/Media` | NTFS drive sdb1 |
| `/home/dwill/media/tv-anime-overflow` | `/mnt/tv-anime` | NTFS drive sda2 (ACL) |

### Directories (local)
- `/home/dwill/media/books/`
- `/home/dwill/media/komga-config-comics/`
- `/home/dwill/media/manga-library/`
- `/home/dwill/media/movies/`
- `/home/dwill/media/music/`
- `/home/dwill/media/podcasts/`
- `/home/dwill/media/prowlarr-config/`
- `/home/dwill/media/tv/`

### External Drive Mount Status
| Device | Mount Point | FS | Size | Used | Avail | Use% |
|---|---|---|---|---|---|---|
| `/dev/sdb1` | `/mnt/plex` | ntfs3 | 4.6T | 2.6T | 2.1T | 56% |
| `/dev/sdc2` | `/mnt/other-media` | ntfs3 | 932G | 693G | 240G | 75% |
| `/dev/sda2` | `/mnt/tv-anime` | ntfs3 | 1.9T | 109G | 1.8T | 6% |

### Host Storage
| Device | Mount Point | Size | Used | Avail | Use% |
|---|---|---|---|---|---|
| `/dev/mapper/ubuntu--vg-ubuntu--lv` | `/` | 913G | 616G | 252G | 72% |
| `/dev/nvme0n1p2` | `/boot` | 2.0G | 310M | 1.5G | 17% |
| `/dev/nvme0n1p1` | `/boot/efi` | 1.1G | 6.4M | 1.1G | 1% |

---

## 6. Key Config Files

### OpenClaw Config
- **No `~/.openclaw/config.json` found** — config may be in `~/.openclaw/openclaw.json` or other location
- OpenClaw internal files at `~/.openclaw/`:
  - `/home/dwill/.openclaw/openclaw.json.bak.{1,4}` — Config backups
  - `/home/dwill/.openclaw/memory/main.sqlite` — Main memory DB
  - `/home/dwill/.openclaw/memory/reviewer.sqlite` — Reviewer memory DB
  - `/home/dwill/.openclaw/cron/jobs.json` — Cron job definitions
  - `/home/dwill/.openclaw/exec-approvals.json` — Exec approvals
  - `/home/dwill/.openclaw/tasks/runs.sqlite` — Task run tracking
  - `/home/dwill/.openclaw/update-check.json` — Update check state
  - `/home/dwill/.openclaw/identity/device.json` — Device identity
  - `/home/dwill/.openclaw/credentials/telegram-pairing.json` — Telegram pairing
  - `/home/dwill/.openclaw/credentials/discord-pairing.json` — Discord pairing
  - `/home/dwill/.openclaw/credentials/github-copilot.token.json` — GitHub Copilot token
  - `/home/dwill/.openclaw/credentials/discord-default-allowFrom.json` — Discord allow list

### Containers Systemd Structure
All files in `~/.config/containers/systemd/` are symlinks (no direct files). Source is repo at `/home/dwill/dev/OsMEN-OC/quadlets/`.

### TaskWarrior Config (`~/.taskrc`)
Custom UDAs: `energy` (high/medium/low), `interaction` (PKEXEC/USER_DECISION/USER_INPUT/INTERACTIVE/USER_ACTION/SHARED_SYSTEM/autonomous). CalDAV UID support. Custom report columns.

### Git Status
- **Branch:** `main` (ahead of origin by 5 commits)
- **Uncommitted changes:** `MEMORY.md`, `USER.md`, `quadlets/media/osmen-media-komga-comics.container`
- **Untracked:** `openclaw/basic/`, `openclaw/coder/`, `openclaw/researcher/`, memory files

#### Recent Commits
```
59668e2 session3 handoff: audit briefing for 72h agent work reconciliation
d39fb93 session3 final: BentoPDF deployed, 31 containers, 29 healthy
f1e8a43 session3 continued: Mylar3 health fix, T6.4 resolved, volume audit
0cdb9d4 session3: Tier 7 deployments + Prowlarr wiring + secrets fix
a46acd0 stabilization: T0-T5 complete — all core services deployed
ce47bc2 docs: add platform handoff document (39 pending tasks, system state)
2c8299c OsMEN-OC fresh install — complete platform setup (#46)
aed28a6 Install/fresh setup 20260407 (#45)
8e773f0 chore: remove identity-specific references repo-wide (#44)
b6c4277 fix: pre-install corrections (python3.13, port 8080, pkexec, schema) (#43)
```

---

## 7. Podman Volumes (44 total)

### Named Volumes (systemd-managed)
| Volume |
|---|
| `systemd-osmen-postgres-data` |
| `systemd-osmen-redis-data` |
| `systemd-osmen-chromadb-data` |
| `systemd-osmen-qbit-config` |
| `systemd-osmen-sab-config` |
| `systemd-osmen-prowlarr-config` |
| `systemd-osmen-sonarr-config` |
| `systemd-osmen-radarr-config` |
| `systemd-osmen-bazarr-config` |
| `systemd-osmen-kometa-config` |
| `systemd-osmen-kavita-config` |
| `systemd-osmen-tautulli-config` |
| `systemd-osmen-convertx-data` |
| `systemd-osmen-audiobookshelf-config` |
| `systemd-osmen-audiobookshelf-metadata` |
| `systemd-osmen-whisper-models` |
| `systemd-osmen-nextcloud-data` |
| `systemd-osmen-uptimekuma-data` |
| `systemd-osmen-caddy-config` |
| `systemd-osmen-caddy-data` |
| `systemd-osmen-prometheus-data` |
| `systemd-osmen-grafana-data` |
| `systemd-osmen-plex-config` |
| `systemd-osmen-langflow-data` |
| `systemd-osmen-portall-data` |
| `systemd-osmen-homepage-config` |
| `systemd-osmen-paperless-data` |
| `systemd-osmen-paperless-media` |
| `systemd-osmen-ollama-models` |

### Non-systemd Named Volumes
| Volume | Notes |
|---|---|
| `osmen-mylar3-config` | |
| `osmen-readarr-config` | |
| `osmen-lidarr-config` | |
| `osmen-kometa-config` | Duplicate? (also systemd- version exists) |
| `osmen-prowlarr-config.volume` | |
| `osmen-sab-config.volume` | |
| `osmen-qbit-config.volume` | |
| `osmen-kavita-config.volume` | |
| `osmen-sab-config` | |
| `osmen-qbit-config` | |
| `osmen-prowlarr-config` | |
| `osmen-qbit-config-fresh` | Likely stale |

### Anonymous Volumes (hash-based — potentially stale)
- `7d49a61ccc5dd7de...`
- `a108ec43a565a96c...`
- `ce4795ff07231004...`
- `d2726b01a59f9be5...`
- `335dd16d7fd303ef...`

**Note:** Several volumes appear to be duplicates or stale (e.g., `osmen-prowlarr-config` vs `systemd-osmen-prowlarr-config` vs `osmen-prowlarr-config.volume`). Clean-up candidate.

---

## 8. Podman Networks

| Network ID | Name | Driver |
|---|---|---|
| `6dc3b480a172` | `osmen-core` | bridge |
| `fbe498980515` | `osmen-media` | bridge |
| `2f259bab93aa` | `podman` | bridge |
| `6eb8c5d667b1` | `podman-default-kube-network` | bridge |
