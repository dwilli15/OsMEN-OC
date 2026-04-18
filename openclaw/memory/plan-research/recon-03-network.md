# Recon 03: Network + Ports + VPN Truth

**Date:** 2026-04-18 03:25 CDT

## Podman Networks

| Network | Subnet | Interface | DNS | Containers |
|---------|--------|-----------|-----|------------|
| `osmen-core` | 10.89.0.0/24 | podman1 | yes | *(none currently)* |
| `osmen-media` | 10.89.1.0/24 | podman2 | yes | 5b49464c15de-infra (10.89.1.3) |
| `podman` | 10.88.0.0/16 | podman0 | no | *(none currently)* |
| `podman-default-kube-network` | 10.89.2.0/24 | podman3 | yes | *(none currently)* |

**Note:** All containers show port mappings but only `5b49464c15de-infra` is registered on a network. The media containers (gluetun, sabnzbd, qbittorrent, prowlarr) are in a pod sharing the pod network namespace — they all share one IP via the infra container.

## Network Topology

```
                    HOST (Ubu-OsMEN)
                    ├─ enx605b3038498d (ethernet USB)
                    ├─ wlo1 (wifi)
                    └─ tailscale0

    ┌─────────────────────────────────────────────────┐
    │  osmen-media pod (10.89.1.3 via podman2)       │
    │                                                  │
    │  5b49464c15de-infra (infra container)            │
    │  ├─ osmen-media-gluetun  (VPN gateway)          │
    │  ├─ osmen-media-sabnzbd  (usenet downloader)    │
    │  ├─ osmen-media-qbittorrent (torrent downloader) │
    │  └─ osmen-media-prowlarr  (indexer)             │
    └─────────────────────────────────────────────────┘

    osmen-core network (10.89.0.0/24) — EMPTY, no containers
    podman-default-kube-network (10.89.2.0/24) — EMPTY, no containers
```

## Complete Port Map

### Container Ports (all bound to 127.0.0.1 only)

| Host Port | Container Port | Service | Container | Purpose |
|-----------|---------------|---------|-----------|---------|
| 8082 | 8080 | qBittorrent Web UI | osmen-media-qbittorrent | Torrent client UI |
| 8888 | 8888 | Gluetun HTTP proxy | osmen-media-gluetun | HTTP proxy (control plane port?) |
| 9090 | 9090 | Sabnzbd Web UI | osmen-media-sabnzbd | Usenet client UI |
| 9696 | 9696 | Prowlarr Web UI | osmen-media-prowlarr | Indexer manager UI |

**Note:** All 5 containers in the pod share the same port mappings because they share the network namespace. Only one service actually listens on each port internally. Port 8888 is the gluetun control port.

### Container Internal-Only Ports (not mapped to host)

| Port | Protocol | Container | Purpose |
|------|----------|-----------|---------|
| 8000 | TCP | gluetun | Gluetun internal |
| 8388 | TCP+UDP | gluetun | Shadowsocks proxy |
| 6881 | TCP+UDP | qbittorrent | BitTorrent |

### Host Services

| Port | Bind | Process | Service | Notes |
|------|------|---------|---------|-------|
| 22 | 0.0.0.0 + [::] | (ssh) | SSH | **PUBLIC — exposed to all interfaces** |
| 32400 | 0.0.0.0 | Plex Media Serv | Plex Media Server | **PUBLIC — exposed to all interfaces** |
| 18789 | 127.0.0.1 | openclaw-gatewa | OpenClaw Gateway (web) | Local only |
| 18791 | 127.0.0.1 | openclaw-gatewa | OpenClaw Gateway (api?) | Local only |
| 5353 | 0.0.0.0 | openclaw-gatewa | mDNS/DNS-SD | OpenClaw mDNS |
| 11434 | 127.0.0.1 | (ollama?) | Ollama API | Local only |
| 631 | 127.0.0.1 | (cups) | Printing | Local only |
| 52569 | 127.0.0.1 | code-insiders | VS Code Insiders | Local only |
| 46041 | 127.0.0.1 | code-insiders | VS Code Insiders | Local only |
| 43744 | 127.0.0.1 | code-insiders | VS Code Insiders | Local only |
| 45203 | 127.0.0.1 | wavesrv.x64 | Wavebox (email client) | Local only |
| 33119 | 127.0.0.1 | wavesrv.x64 | Wavebox | Local only |
| 9000 | 127.0.0.1 | (unknown) | Unknown | Possibly PHP-FPM or SonarQube? |
| 8001 | 127.0.0.1 | (unknown) | Unknown | No process owner visible |
| 8002 | 127.0.0.1 | (unknown) | Unknown | No process owner visible |
| 32600 | 127.0.0.1 | (unknown) | Unknown | Likely ephemeral/app port |
| 32401 | 127.0.0.1 | (unknown) | Unknown | Possibly Plex companion/discovery |
| 13305 | 127.0.0.1 | (unknown) | Unknown | Likely ephemeral/app port |
| 41759 | 127.0.0.1 | (unknown) | Unknown | Likely ephemeral/app port |
| 53 | 127.0.0.53 | systemd-resolved | DNS stub | System DNS resolver |
| 54 | 127.0.0.54 | systemd-resolved | DNS stub | System DNS resolver |

### UDP Notable Ports

| Port | Bind | Process | Notes |
|------|------|---------|-------|
| 33085 | 0.0.0.0 | rustdesk | RustDesk remote desktop |
| 21119 | 0.0.0.0 | rustdesk | RustDesk relay |
| 5353 | 0.0.0.0 | openclaw-gateway + chrome | mDNS |
| 3702 | multi | python3 | WS-Discovery (likely printer/scanner) |
| 32410-32414 | 0.0.0.0 | (plex) | Plex service discovery |

## VPN Routing Verification

| Source | Exit IP | VPN? |
|--------|---------|------|
| Host (`curl ifconfig.me`) | **46.110.121.251** | NO — host's real ISP IP |
| Gluetun container (`wget ifconfig.me`) | **91.148.236.73** | **YES** — different IP, VPN active |
| HTTP proxy (`curl -x 127.0.0.1:8888`) | **91.148.236.73** | **YES** — routes through gluetun VPN |

✅ VPN is working. Gluetun successfully tunnels all media pod traffic through VPN. Exit IP 91.148.236.73 differs from host IP 46.110.121.251.

## DNS Inside Gluetun

```
nameserver 198.18.0.1
search dns.podman .
```

Gluetun uses a MagicDNS-style local address (198.18.0.1) — this is the gluetun VPN DNS resolver, which handles DNS-over-VPN to prevent leaks.

## Firewall Status

- **iptables:** All chains ACCEPT, no rules (wide open)
- **nftables:** Not active
- **UFW:** Inactive

⚠️ **No host firewall is active.** All services bound to 0.0.0.0 are publicly accessible on the network.

## Inter-Container Connectivity

| Test | Result | Notes |
|------|--------|-------|
| Prowlarr → Sabnzbd (same pod) | ✅ Connected (HTTP 403) | Reached server, 403 is expected (API auth required) |
| Sonarr → Sabnzbd | ❌ No container | **Sonarr does not exist** — not deployed yet |
| Sonarr → Prowlarr | ❌ No container | Same — sonarr not deployed |

## Security Concerns

1. **Plex (32400) bound to 0.0.0.0** — accessible from all networks with no firewall
2. **SSH (22) bound to 0.0.0.0** — exposed, relies on key auth only
3. **UFW inactive** — no host firewall rules at all
4. **iptables wide open** — ACCEPT policy on all chains, zero rules
5. **RustDesk (33085/21119) bound to 0.0.0.0** — remote desktop exposed to LAN

## Missing Services (Expected but Not Running)

- **Sonarr** — not deployed (was expected in media stack)
- **Radarr** — not deployed
- **Jellyfin** — not deployed
- **Kavita** — exited (created 292 years ago — stale container)
- **Flaresolverr** — exited (stale)
- **Komga** — exited 8 hours ago
- **osmen-core-gateway-test** — created, never started

## Gluetun HTTP Proxy Detail

Port 8888 on the gluetun container is an HTTP proxy that routes traffic through the VPN tunnel. Confirmed working: `curl -x http://127.0.0.1:8888` exits via VPN IP 91.148.236.73.

## Container Port Mapping Anomaly

All 5 containers in the media pod show identical port mappings (8082, 8888, 9090, 9696). This is because podman pods share a network namespace — all containers share one IP. Only the actual service listening on each port responds:
- 8082 → qBittorrent
- 8888 → Gluetun (control plane + HTTP proxy)
- 9090 → Sabnzbd
- 9696 → Prowlarr
