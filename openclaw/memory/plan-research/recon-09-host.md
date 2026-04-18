# Recon 09: Host System + OS + Hardware

_Collected: 2026-04-18 03:27 CDT_

## Hardware Spec Sheet

| Component | Detail |
|-----------|--------|
| **Machine** | HP OMEN Gaming Laptop 17-db1xxx (SKU: BK1T7UA#ABA) |
| **Chassis** | Laptop 💻 |
| **CPU** | AMD Ryzen AI 9 365 w/ Radeon 880M — 10C/20T, up to 5.09 GHz, AVX-512, NPU |
| **iGPU** | AMD Radeon 880M (Strix) |
| **dGPU** | NVIDIA GeForce RTX 5070 Max-Q (8 GB VRAM, driver 595.58.03, CUDA 13.2) |
| **RAM** | 60 GiB DDR (40 GiB available) |
| **Swap** | 8 GiB file (`/swap.img`), 1.8 GiB used |
| **Boot NVMe** | 931.5 GB (Samsung?) — LUKS → LVM → ext4 (928.4 GB) |
| **2nd NVMe** | 953.9 GB — Windows dual-boot partitions (256G NTFS, 697G ext4, 735M NTFS) |
| **External HDD 1** | 4.5 TB (sda) → `/mnt/plex` |
| **External HDD 2** | 1.8 TB (sdb) → `/mnt/tv-anime` |
| **External HDD 3** | 931.5 GB (sdc) → `/mnt/other-media` |
| **Root disk usage** | 546 GB / 913 GB (63%) |
| **USB peripherals** | HP True Vision FHD webcam, Logitech Unifying receiver, WD Elements 2621 (USB HDD), Dell WD19S dock, USB-C Digital AV adapter, Bluetooth radio (Realtek) |
| **NPU** | AMD Strix/Krackan Neural Processing Unit present |

## OS and Kernel Details

| Item | Value |
|------|-------|
| **OS** | Ubuntu 26.04 "Resolute Raccoon" (development branch) |
| **Kernel** | 7.0.0-14-generic x86_64 (PREEMPT_DYNAMIC) |
| **Hostname** | Ubu-OsMEN |
| **Firmware** | F.11 (2025-11-24) |
| **Timezone** | America/Chicago (CDT, -0500) |
| **NTP** | Active, synchronized |
| **Uptime** | ~6.5 hours |
| **Display server** | Wayland (gnome-shell + Xwayland) |

### Network Interfaces

| Interface | Status | IP | Notes |
|-----------|--------|----|-------|
| `wlo1` (Wi-Fi) | UP | 192.168.4.21/22 | Primary |
| `enx605b3038498d` (USB) | UP | 192.168.7.248/22 | Likely via Dell dock |
| `eno1` (Ethernet) | DOWN | — | No carrier |
| `tailscale0` | UP | link-local IPv6 only | Tailscale VPN |

## Security Posture

| Check | Status |
|-------|--------|
| **SSH** | OpenSSH 10.2p1 — PasswordAuth=**no**, RootLogin=**no**, PubkeyAuth=**yes** ✅ |
| **UFW** | **NOT ACTIVE** ⚠️ |
| **Full disk encryption** | LUKS on boot drive ✅ |
| **Unattended upgrades** | Active (enabled) ✅ |
| **Linger** | Yes (dwill) — user services run without login |
| **Vulnerabilities** | All mitigated (Spectre/Meltdown/etc.) ✅ |

### Notable Gaps
- **UFW inactive** — no host firewall despite SSH server running
- Tailscale provides network-level protection but local firewall is absent

## Package Ecosystem

| Metric | Value |
|--------|-------|
| **APT packages** | 2,154 |
| **Snap packages** | 20 (Firefox, Chromium, Discord, Steam, waveterm, LocalSend, etc.) |
| **Flatpak packages** | 20+ (Steam, XIVLauncher, Obsidian, plus runtimes) |

### Key Installed Packages

| Package | Version | Notes |
|---------|---------|-------|
| **podman** | 5.7.0 | Container runtime (rootless) |
| **tailscale** | 1.96.4 | VPN mesh networking |
| **plexmediaserver** | 1.43.1 | Media server |
| **ffmpeg** | 8.0.1 | Transcoding |
| **aria2** | 1.37.0 | Download manager |
| **python3** | 3.14.3 (default) + 3.13.12 | Dual Python versions |
| **openssh-server** | 10.2p1 | SSH daemon |
| **git** | 2.53.0 | |
| **curl** | 8.18.0 | |
| **node/npm** | via linuxbrew (v24.14.1) | Not from apt |
| **ollama** | /usr/local/bin/ollama | Running, using 672 MiB VRAM |
| **screen + tmux** | Both installed | Terminal multiplexers |

### Notable Absent
- Docker (using Podman instead)
- nginx/caddy (no reverse proxy from apt)
- wireguard (using Tailscale instead)

## Recent Errors/Warnings

### systemd user errors (last 1 hour)

1. **`osmen-db-backup.service` failed** — Nightly database backup failed at 02:32 CDT
2. **`podman-user-generator` failed** — Exit status 1 at 03:26 (systemd generator issue, likely benign)

### GPU State

- NVIDIA RTX 5070: 42°C, 13W/80W, 6% utilization, 2038 MiB / 8151 MiB used
- Major consumers: ollama (672 MiB), firefox (254 MiB), gnome-shell (201 MiB), code-insiders (137 MiB)

## Summary

Powerful gaming laptop running cutting-edge Ubuntu 26.04 with dual-GPU setup (Radeon 880M + RTX 5070 Max-Q). Heavy local media setup with 3 external HDDs (7+ TB total) and Plex. Container workloads via Podman. AI/ML capable with NPU and CUDA 13.2. LUKS encryption on boot drive. Main security gap: UFW inactive.
