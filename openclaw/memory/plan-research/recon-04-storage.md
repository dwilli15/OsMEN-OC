# Recon 04: Storage + Volumes + Drives Truth

**Date:** 2026-04-18 03:25 CDT

## Drive Inventory

| Device | Label | Mount | FS | Size | Used | Free | Use% |
|--------|-------|-------|----|------|------|------|------|
| nvme0n1p3 (LUKS→LVM) | — | `/` | ext4 | 913G | 546G | 321G | 63% |
| nvme0n1p2 | — | `/boot` | ext4 | 2.0G | 310M | 1.5G | 17% |
| nvme0n1p1 | — | `/boot/efi` | vfat | 1.1G | 6.4M | 1.1G | 1% |
| sda1 | plex | `/mnt/plex` | ntfs3 | 4.6T | 2.6T | 2.1T | 56% |
| sdb2 | TV_Anime_OFlow | `/mnt/tv-anime` | ntfs3 | 1.9T | 109G | 1.8T | 6% |
| sdc2 | Other_Media | `/mnt/other-media` | ntfs3 | 932G | 693G | 240G | 75% |
| nvme1n1p4 | win_closet | `/mnt/win_closet` | ext4 | (noauto) | — | — | — |

**Notable:** sdc2 is mounted **twice** — once at `/mnt/other-media` (fstab) and once at `/run/media/dwill/Other_Media` (udisks2 auto-mount).

## /home/dwill/media/ — Symlinks

| Symlink | Target |
|---------|--------|
| `plex` → `/run/media/dwill/plex/Media` | **BROKEN** — plex drive mounts at `/mnt/plex`, not `/run/media/dwill/plex` |
| `tv-anime-overflow` → `/run/media/dwill/TV_Anime_OFlow` | **BROKEN** — tv-anime mounts at `/mnt/tv-anime`, not `/run/media/dwill/TV_Anime_OFlow` |
| `audiobooks` → `/run/media/dwill/plex/Media/Other/Audiobooks` | **BROKEN** (same issue) |
| `comics` → `/run/media/dwill/Other_Media/Media/Other/Comics` | Works (Other_Media auto-mounts at `/run/media/dwill/Other_Media`) |
| `manga` → `/run/media/dwill/Other_Media/Officially Translated Light Novels` | Works |
| `manga-downloads` → `/run/media/dwill/Other_Media/Manga` | Works |

## fstab Configured Mounts

- `/` — LUKS-encrypted LVM on nvme0n1p3
- `/boot` — nvme0n1p2
- `/boot/efi` — nvme0n1p1
- `/mnt/win_closet` — nvme1n1p4 ext4 (**noauto** — not mounted)
- `/mnt/plex` — sda1 ntfs3
- `/mnt/tv-anime` — sdb2 ntfs3
- `/mnt/other-media` — sdc2 ntfs3

## Podman Storage Summary

| Type | Total | Active | Size | Reclaimable |
|------|-------|--------|------|-------------|
| Images | 103 | 8 | 39.9G | 37.5G (94%) |
| Containers | 9 | 5 | 28M | 20.6M (73%) |
| Local Volumes | 37 | 5 | 135.6G | 135.4G (100%) |

## Podman Volume Inventory (37 volumes)

### Large Volumes (>1G)

| Volume | Size | Notes |
|--------|------|-------|
| osmen-sab-config.volume | **125G** | SABnzbd download cache — biggest consumer on root drive |
| systemd-osmen-nextcloud-data | 842M | Nextcloud data |
| systemd-osmen-kavita-config | 782M | Kavita config (likely includes library metadata) |
| osmen-kavita-config.volume | 175M | Duplicate kavita config? |
| systemd-osmen-sonarr-config | 207M | Sonarr config |

### Medium Volumes (10-100M)

| Volume | Size |
|--------|------|
| systemd-osmen-grafana-data | 51M |
| systemd-osmen-tautulli-config | 28M |
| systemd-osmen-radarr-config | 33M |
| osmen-readarr-config | 14M |
| osmen-prowlarr-config.volume | 19M |
| osmen-qbit-config.volume | 22M |
| osmen-prowlarr-config | 5.4M |
| osmen-qbit-config | 8.1M |
| systemd-osmen-prowlarr-config | 35M |
| systemd-osmen-qbit-config | 8.2M |

### Small Volumes (<10M)

| Volume | Size |
|--------|------|
| osmen-lidarr-config | 8.7M |
| systemd-osmen-kometa-config | 748K |
| osmen-kometa-config | 12K |
| systemd-osmen-bazarr-config | 4.9M |
| systemd-osmen-chromadb-data | 6.4M |
| osmen-mylar3-config | 412K |
| systemd-osmen-convertx-data | 60K |
| systemd-osmen-caddy-config | 16K |
| systemd-osmen-caddy-data | 24K |
| systemd-osmen-audiobookshelf-config | 424K |
| systemd-osmen-audiobookshelf-metadata | 64K |
| systemd-osmen-plex-config | 8K |
| systemd-osmen-postgres-data | 8K |
| systemd-osmen-prometheus-data | 836K |
| systemd-osmen-redis-data | 16K |
| systemd-osmen-sab-config | 228K |
| systemd-osmen-uptimekuma-data | 288K |
| systemd-osmen-whisper-models | 8K |
| osmen-sab-config | 60K |
| 3 unnamed hash volumes | 8K each |

## Storage Hot Spots (Root Drive)

| Path | Size |
|------|------|
| `.local/share/containers/` | **165G** total |
| ↳ osmen-sab-config.volume (SABnzbd) | 125G |
| ↳ container images | ~40G (37.5G reclaimable) |
| ↳ other volumes | ~1.3G |
| Downloads | 2.0G |
| media/komga-config-comics | 101M |

## Free Space Warnings

1. **⚠️ Root drive at 63%** — 321G free. The 125G SABnzbd volume on root is the biggest risk. If downloads fill up, root could hit capacity.
2. **⚠️ Other_Media at 75%** — 240G free. Highest percentage use of any drive.
3. **✅ Plex drive at 56%** — 2.1T free. Healthy.
4. **✅ TV-Anime at 6%** — 1.8T free. Barely used.
5. **🔧 37.5G reclaimable** in unused container images — run `podman image prune` to reclaim.

## Key Issues

1. **Broken symlinks in `/home/dwill/media/`** — `plex`, `tv-anime-overflow`, `audiobooks` all point to `/run/media/dwill/plex` which doesn't exist (drive mounts at `/mnt/plex`)
2. **SABnzbd 125G on root drive** — should ideally be on an external drive to protect root space
3. **Duplicate volume naming** — several services have both `osmen-X` and `systemd-osmen-X` volumes (e.g., kavita, prowlarr, sab, qbit) — likely from migration between compose systems
4. **sdc2 double-mounted** — both `/mnt/other-media` and `/run/media/dwill/Other_Media`
5. **win_closet not mounted** (noauto) — nvme1n1p4 ext4 partition exists but isn't auto-mounted
