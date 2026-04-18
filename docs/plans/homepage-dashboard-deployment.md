# Homepage Dashboard Deployment Plan

**Date**: 2026-04-16
**Status**: Planning — not yet implemented
**Project**: osmen.dashboard.homepage

## Overview

Deploy [Homepage](https://github.com/gethomepage/homepage) (gethomepage) as the unified service dashboard for all 28 OsMEN-OC containers + native services. YAML-driven config, version-controlled in the repo.

## Why Homepage

- 160+ service integrations covering our entire stack (Sonarr, Radarr, qBit, Prowlarr, Tautulli, Plex, Bazarr, Lidarr, Readarr, SABnzbd, Nextcloud, Kavita, Audiobookshelf, Grafana, UptimeKuma, Gluetun, etc.)
- YAML config — fits our git-driven workflow
- SSG (static site generation) — fast, lightweight (~30MB RAM)
- Proxied API calls — API keys stay server-side
- Docker socket integration for container status
- Podman-compatible via socket or HTTP API

## Architecture

```
Browser → Caddy (:80) → homepage.osmen.local → Homepage (:3003)
                                    ↓
                            Podman Socket API
                            (28 containers status)
                                    ↓
                            Service APIs (proxied)
                            (Sonarr, Radarr, Plex, etc.)
```

## Podman Socket Bridge

Podman rootless socket confirmed working:
- **Path**: `/run/user/1000/podman/podman.sock`
- **Owner**: dwill:dwill
- **Accessible**: Yes (28 containers returned via API test)
- **Homepage needs**: Mount socket read-only into container

Homepage runs as root inside the container but accesses the socket as user 0.
Podman rootless socket is owned by uid 1000 (dwill). **Solution**: use Podman's
Docker-compatible HTTP API instead of socket, or configure Podman to allow
root access to the socket (not recommended), or run Homepage with `--user 1000`.

**Recommended approach**: Use Podman HTTP API via `podman system service` on a
TCP port, then configure Homepage's `docker.yaml` to connect via host:port.

## Port Assignment

| Service | Port | Status |
|---|---|---|
| Homepage | **3003** | ✅ Free (3000=Grafana, 3001=UptimeKuma, 3002=Grafana) |

## Network

- **Container network**: `osmen-core` (same as gateway, Caddy, PostgreSQL, Redis)
- **Published**: `127.0.0.1:3003:3000` (localhost only, behind Caddy)
- **Caddy reverse proxy**: `homepage.osmen.local:80 → localhost:3003`

## Files to Create

```
quadlets/core/osmen-core-homepage.container    # Quadlet unit
config/homepage/                               # Homepage config directory
  services.yaml                                # Service definitions (auto-generated)
  bookmarks.yaml                               # Quick links
  widgets.yaml                                  # Info widgets (weather, system, search)
  settings.yaml                                 # Theme, layout, header
  docker.yaml                                   # Podman API connection
scripts/generate-homepage-services.py          # Auto-generates services.yaml from quadlets
```

## services.yaml Structure

Auto-generated from quadlets. Example sections:

```yaml
- Media:
    - Plex:
        icon: plex.png
        href: http://plex.osmen.local:32400
        description: Media server (native)
        widget:
          type: plex
          url: http://osmen-media-plex:32400
          key: NaxyQSk5i2fnKQyctmQg

    - Sonarr:
        icon: sonarr.png
        href: http://localhost:8989
        description: TV series management
        widget:
          type: sonarr
          url: http://osmen-media-sonarr:8989
          key: 1cbf2bc42cbb450181b85d59a344155e
        server: osmen-core
        container: osmen-media-sonarr

    - Radarr:
        icon: radarr.png
        href: http://localhost:7878
        description: Movie management
        widget:
          type: radarr
          url: http://osmen-media-radarr:7878
          key: 1ed7c7d3706e49739986bed19a8da64f

    - qBittorrent:
        icon: qbittorrent.png
        widget:
          type: qbittorrent
          url: http://osmen-media-qbittorrent:9090
        # Note: behind VPN, may need container network access

    - Prowlarr:
        icon: prowlarr.png
        widget:
          type: prowlarr
          url: http://osmen-media-prowlarr:9696
          key: 0a7c9db5fe024343af5a1dafaf09aad6

    - Tautulli:
        icon: tautulli.png
        widget:
          type: tautulli
          url: http://osmen-media-tautulli:8181
          key: (get from Tautulli config)

    - Lidarr:
        icon: lidarr.png
        widget:
          type: lidarr
          url: http://osmen-media-lidarr:8686
          key: 45ff7fe5dc7c4bfda4f46fb39002c0e3

    - Readarr:
        icon: readarr.png
        widget:
          type: readarr
          url: http://osmen-media-readarr:8787
          key: 843db6342879438d9578c6458ba90341

    - Bazarr:
        icon: bazarr.png
        widget:
          type: bazarr
          url: http://osmen-media-bazarr:6767
          key: a5600746b238a59029d5cafadadf7b1d

    - SABnzbd:
        icon: sabnzbd.png
        widget:
          type: sabnzbd
          url: http://osmen-media-sabnzbd:8080
          key: b69fd362889549ff9dffd8cddbb983ea

    - Mylar3:
        icon: mylar.png
        widget:
          type: mylar
          url: http://osmen-media-mylar3:8090
          key: 4e8c84867a6e018406bc31f8b686184f

- Monitoring:
    - Grafana:
        icon: grafana.png
        href: http://grafana.osmen.local
        widget:
          type: grafana
          url: http://osmen-monitoring-grafana:3000

    - Prometheus:
        icon: prometheus.png
        href: http://localhost:9091
        widget:
          type: prometheus
          url: http://osmen-monitoring-prometheus:9090

    - UptimeKuma:
        icon: uptime-kuma.png
        href: http://uptimekuma.osmen.local
        widget:
          type: uptimekuma
          url: http://osmen-monitoring-uptimekuma:3001

- Librarian:
    - Kavita:
        icon: kavita.png
        href: http://localhost:5000
        widget:
          type: kavita
          url: http://osmen-librarian-kavita:5000

    - Audiobookshelf:
        icon: audiobookshelf.png
        href: http://localhost:13378
        widget:
          type: audiobookshelf
          url: http://osmen-librarian-audiobookshelf:80

- Core:
    - OsMEN Gateway:
        icon: api.png
        href: http://localhost:18788
        description: 45 MCP tools, health/metrics/tasks endpoints
        widget:
          type: customapi
          url: http://osmen-core-gateway:8080/health

    - Nextcloud:
        icon: nextcloud.png
        href: http://localhost:8080
        widget:
          type: nextcloud
          url: http://osmen-core-nextcloud:8080

    - SiYuan:
        icon: siyuan.png
        href: http://localhost:6806

    - Langflow:
        icon: langflow.png
        href: http://localhost:7860

- Infrastructure:
    - Gluetun (VPN):
        icon: vpn.png
        widget:
          type: gluetun
          url: http://osmen-media-gluetun:9999

    - Caddy:
        icon: caddy.png
        widget:
          type: caddy
          url: http://osmen-core-caddy:2019
```

## API Keys Inventory

All keys needed for widget configuration (already extracted during media pipeline work):

| Service | Key | Source |
|---|---|---|
| Plex | `NaxyQSk5i2fnKQyctmQg` | Native install config |
| Sonarr | `1cbf2bc42cbb450181b85d59a344155e` | config.xml |
| Radarr | `1ed7c7d3706e49739986bed19a8da64f` | config.xml |
| Prowlarr | `0a7c9db5fe024343af5a1dafaf09aad6` | config.xml |
| Lidarr | `45ff7fe5dc7c4bfda4f46fb39002c0e3` | config.xml |
| Readarr | `843db6342879438d9578c6458ba90341` | config.xml |
| Bazarr | `a5600746b238a59029d5cafadadf7b1d` | config.yaml |
| SABnzbd | `b69fd362889549ff9dffd8cddbb983ea` | sabnzbd.ini |
| Mylar3 | `4e8c84867a6e018406bc31f8b686184f` | config.ini (generated) |
| Tautulli | **TODO** | Need to extract from Tautulli config |

## Security Considerations

1. **API keys in YAML**: Homepage proxies all API calls — keys never leave the server.
   But the YAML files in the repo contain keys. Options:
   - Store keys in env vars, reference via `$VAR` in YAML
   - Use SOPS-encrypted YAML (consistent with OsMEN secrets pattern)
   - `.gitignore` the YAML and store encrypted version only
   - **Recommended**: env vars via Podman secret/quadlet, template into YAML at start

2. **No auth on Homepage**: Homepage has no built-in auth. Mitigations:
   - Listen on 127.0.0.1 only (behind Caddy)
   - Caddy can add basic auth if needed later
   - Already behind VPN for remote access

3. **Podman socket access**: Mounting the socket gives Homepage container read access
   to all container metadata. Read-only mount is essential.

## Implementation Steps

See TW tasks P23.1–P23.8 for ordered breakdown.

## Open Questions

1. **Podman socket vs HTTP API**: Socket needs UID mapping. HTTP API needs `podman system service tcp:HOST:PORT`. Test both.
2. **Secrets strategy**: SOPS-encrypted services.yaml or env var templating?
3. **Auto-generation**: Should `scripts/generate-homepage-services.py` run as a hook or manual?
4. **Portracker later**: Tier 2 — add after Homepage is stable?

## References

- Homepage docs: https://gethomepage.dev/
- Homepage GitHub: https://github.com/gethomepage/homepage
- Service widgets: https://gethomepage.dev/widgets/services/
- Docker/Podman config: https://gethomepage.dev/configs/docker/
- OsMEN Caddyfile: config/Caddyfile
- OsMEN quadlets: quadlets/*/
