# Online Research: Podman Quadlet + VPN Download Stack Best Practices

**Date:** 2026-04-18
**Researcher:** online-researcher subagent

---

## 1. Podman Quadlet Patterns for VPN-Routed Download Stacks

### How to Run Download Clients Through a VPN Pod

The established pattern uses **gluetun as the VPN container** with other containers sharing its network namespace via `network_mode: "service:gluetun"` (docker-compose) or by joining the same pod.

**Two approaches:**

#### A. Pod-based (shared network namespace)
Create a `.pod` quadlet for the VPN pod, then have containers join it via `PodName=`:

```
# download-pod.pod
[Pod]
PublishPort=8080:8080
PublishPort=6789:6789

# gluetun.container
[Container]
PodName=download-pod
Image=qmcgaw/gluetun
ContainerName=gluetun
CapAdd=NET_ADMIN
Device=/dev/net/tun

# sabnzbd.container
[Container]
PodName=download-pod
Image=lscr.io/linuxserver/sabnzbd
ContainerName=sabnzbd
```

**Key detail:** Ports published at the pod level are shared across all containers. Do NOT publish ports on individual containers that are already published at the pod level — this causes conflicts.

#### B. network_mode approach (docker-compose style)
Not directly supported in quadlet's `[Container]` section. Use pods instead.

### Quadlet Pod + Container Dependency Chain

The correct systemd dependency ordering:

```
# In each container's .container file:
[Unit]
Requires=download-pod.service
After=download-pod.service

[Container]
PodName=download-pod
```

Quadlet generates:
- `download-pod.pod` → `download-pod.service` (Type=forking)
- Each `.container` → `.service` (Type=notify by default)

The `Requires=` ensures the pod starts; `After=` ensures ordering. **Use `.service` suffixes in dependency directives, not `.pod` or `.container`.**

### How `systemctl --user daemon-reload` Interacts with Quadlet

- Quadlet is a **systemd generator** that runs at boot and on `daemon-reload`
- It reads `.container`, `.pod`, `.network`, `.volume`, `.kube` files from search paths
- Generates corresponding `.service` files in `/run/systemd/generator/`
- `daemon-reload` re-runs the generator, so changes to quadlet files take effect after reload
- **Symlinks are supported** — you can symlink quadlet files from other locations into the search path
- The `[Install]` section (WantedBy) is applied during generation, not via `systemctl enable`

### Sources
- [Podman Quadlet docs (v5.5.0)](https://docs.podman.io/en/v5.5.0/markdown/podman-systemd.unit.5.html)
- [VPN-enabled podman containers - beerstra.org](https://beerstra.org/2024/07/12/vpn-enabled-podman-containers/)
- [Multi-container apps with quadlets - Giacomo Coletto](https://giacomo.coletto.io/blog/podman-quadlets)

---

## 2. SABnzbd Wizard-Mode Persistence

### Why SABnzbd Falls Back to Wizard Mode

SABnzbd triggers the wizard when **`sabnzbd.ini` is missing or cannot be read** from the expected config location. In the linuxserver.io container, this is `/config/sabnzbd.ini`.

**Common causes:**
1. The `/config` volume mount is not persisted (tmpfs, wrong path, or not mounted at all)
2. The config directory has wrong permissions (PUID/PGID mismatch)
3. The `sabnzbd.ini` file was deleted or the config directory was wiped
4. SELinux labels missing on the volume (`:z` or `:Z` flag)

### Config File Flags

There is no explicit "wizard complete" flag. SABnzbd simply checks if `sabnzbd.ini` exists and is readable. Once the wizard completes, it writes the config file. On subsequent starts, if the file exists, the wizard is skipped.

### LinuxServer.io Image Behavior

- On **first run** (no `/config/sabnzbd.ini`): SABnzbd starts in wizard mode, serves the web UI on port 8080
- On **subsequent runs** (config exists): SABnzbd reads existing config and starts normally
- The init system sets ownership based on `PUID`/`PGID` environment variables

### Prevention

- **Always mount `/config` to a persistent volume** (named volume or host path)
- Set `PUID`/`PGID` to match the host user owning the config directory
- Add `:z` SELinux relabel flag on volume mounts
- Consider backing up `sabnzbd.ini` after initial setup

### Sources
- [SABnzbd Forums - "Wizard keeps coming"](https://forums.sabnzbd.org/viewtopic.php?t=10292)
- [SABnzbd Forums - "is it possible to skip the wizard?"](https://forums.sabnzbd.org/viewtopic.php?t=19025)
- [LinuxServer SABnzbd docs](https://docs.linuxserver.io/images/docker-sabnzbd/)

---

## 3. qBittorrent Auth in Containers

### PBKDF2 Password Issues (qBittorrent 4.6.x / 5.x)

qBittorrent 4.6.x introduced PBKDF2 password hashing for the WebUI. Key issues:

- **4.6.1 broke WebUI login** for some users — the password hash format changed between versions ([linuxserver/docker-qbittorrent#268](https://github.com/linuxserver/docker-qbittorrent/issues/268))
- If you restore an old `qBittorrent.conf` with a plaintext password, qBittorrent may re-hash it and cause confusion
- The `WebUI\Password` field in `qBittorrent.conf` stores a PBKDF2-derived hash, not plaintext

### Resetting the Password

**Reliable method for linuxserver.io images:**

1. **Stop the container**
2. **Edit `/config/qBittorrent.conf`**: Remove or comment out the `WebUI\Password` line
3. **Restart the container** — qBittorrent will generate a temporary password
4. **Check container logs** for the temporary password: `podman logs qbittorrent 2>&1 | grep -i password`
5. **Log in with the temp password** and set a new one

**Alternative:** Delete `qBittorrent.conf` entirely (wipes ALL settings — not recommended unless starting fresh).

### `WEBUI_PORT` and Auth Bypass

- linuxserver.io qBittorrent images support `WEBUI_PORT` environment variable (default: 8080)
- There is **no official auth bypass** — PR [#408](https://github.com/linuxserver/docker-qbittorrent/pull/408) proposing `WEBUI_USER`/`WEBUI_PASS` env vars was opened but **not merged**
- The container init script does NOT set a default password — it relies on qBittorrent's built-in temp password mechanism on first run

### Sources
- [linuxserver/docker-qbittorrent#268 - 4.6.1 breaks WebUI login](https://github.com/linuxserver/docker-qbittorrent/issues/268)
- [linuxserver/docker-qbittorrent#61 - Lost password](https://github.com/linuxserver/docker-qbittorrent/issues/61)
- [linuxserver/docker-qbittorrent#408 - WEBUI_USER/WEBUI_PASS PR](https://github.com/linuxserver/docker-qbittorrent/pull/408)
- [VahaC - Reset qBittorrent WebUI Password](https://vahac.com/reset-qbittorrent-webui-password-in-docker/)

---

## 4. Pod Topology for Media Stacks

### Single Pod (Download Clients + VPN) vs Multiple Pods

**Single VPN pod with all download clients:**
- ✅ All traffic forced through VPN (no leak risk)
- ✅ Simple network topology — containers share the pod's network namespace
- ✅ Lower resource overhead (one pause container)
- ❌ If VPN container restarts, ALL containers in the pod restart
- ❌ Can't have containers in the pod that need direct (non-VPN) network access

**Multiple pods:**
- ✅ Isolation — VPN pod failure doesn't affect non-VPN services
- ✅ Can mix VPN-routed and direct-access containers
- ❌ More complex dependency management
- ❌ Arr apps (Sonarr/Radarr) need to reach download clients — requires cross-pod networking

### Recommended Architecture

**Best practice (widely adopted):**

```
[VPN Pod]
  ├── gluetun (VPN)
  ├── qBittorrent (torrents)
  └── SABnzbd (usenet)

[App Pod / Standalone Containers]
  ├── Sonarr
  ├── Radarr
  ├── Lidarr
  ├── Prowlarr
  └── FlareSolverr
```

- Download clients live in the VPN pod (all traffic routed through VPN)
- Arr apps run outside the VPN pod with their own network
- Arr apps connect to download clients via **the pod's published ports** or via a shared network
- Prowlarr runs outside the VPN (needs direct internet access for indexer searches)

### How Arr Apps Connect to Download Clients in a VPN Pod

Two approaches:

1. **Via published ports on the host**: Arr apps point to `http://host-ip:port` — simplest but exposes ports on the host
2. **Via shared Podman network**: Create a network, assign it to the VPN pod, and have arr containers on the same network. The VPN pod can use `FIREWALL_OUTBOUND_SUBNETS` in gluetun to allow local network access.

**Important:** When using `network_mode: "service:gluetun"` (docker-compose) or a pod, the containers share gluetun's network. Arr apps outside the pod need to reach them via published ports or a network that the pod is attached to.

### FlareSolverr Reachability from Inside VPN Pods

FlareSolverr should **NOT** be inside the VPN pod. It needs direct internet access to solve CAPTCHAs. Run it as a standalone container or in a non-VPN pod, and have Prowlarr (also outside VPN) connect to it directly.

### Sources
- [Building Media Automation Suite with Podman Quadlets - Blackfyre/Medium](https://blog.blackfyre.ninja/building-a-complete-self-hosted-media-automation-suite-with-podman-quadlets-fa0a46eee7c3)
- [VPN-enabled podman containers - beerstra.org](https://beerstra.org/2024/07/12/vpn-enabled-podman-containers/)
- [Podman Quadlets Arr-Stack discussion - Lemmy](https://lemmy.world/post/41941707/21681889)

---

## 5. Systemd + Quadlet Stability Patterns

### Ensuring Containers Survive Reboots

1. **Enable lingering** for the user: `sudo loginctl enable-linger <username>`
   - Without this, user systemd services stop when the user logs out
2. **Use `[Install] WantedBy=default.target`** in quadlet files
   - Quadlet applies this during generation (no need for `systemctl enable`)
3. **Use `podman system migrate`** after initial setup
4. **Ensure podman socket is enabled**: `systemctl --user enable --now podman.socket`

### `podman auto-update` Integration

Add the label to each quadlet:
```
[Container]
Label=io.containers.autoupdate=registry
```

Then enable the timer:
```bash
systemctl --user enable --now podman-auto-update.timer
```

**Strategies:**
- `registry` — always pull latest from registry (recommended)
- `local` — only update if local image changes

**Caveat for VPN pods:** If gluetun restarts due to auto-update, dependent containers in the same pod will also restart. This is generally fine but worth noting.

### Health Check Patterns

Quadlet supports health checks via:
```
[Container]
HealthCmd=/usr/bin/curl -f http://localhost:8080/ || exit 1
HealthInterval=30s
HealthRetries=3
HealthTimeout=5s
HealthStartPeriod=60s
```

Then use `Notify=healthy` in `[Service]` to make systemd wait for health before marking the service as started:
```
[Service]
Notify=healthy
```

**Known issue:** If `HealthStartPeriod` exceeds systemd's `TimeoutStartSec` (default 90s), systemd may time out before health is confirmed. Set `TimeoutStartSec` accordingly:
```
[Service]
TimeoutStartSec=300
```

Source: [podman#27290](https://github.com/containers/podman/issues/27290)

### Handling `ReadOnly=true`

LinuxServer.io images support read-only filesystems. The image provides a `/tmp` writable overlay automatically. For quadlet:
```
[Container]
ReadOnly=true
```

**What still needs to be writable:**
- `/config` volume — always writable (mounted)
- `/tmp` — handled by the container's init system
- Some apps need `/run` writable — linuxserver.io images handle this via their init scripts

**Not all images support this.** Check the specific image's docs. LinuxServer.io explicitly documents which images support `--read-only=true`.

### Sources
- [Automatic container updates with Podman quadlets - major.io](https://major.io/p/podman-quadlet-automatic-updates/)
- [How to Configure Auto-Update in Quadlet - oneuptime](https://oneuptime.com/blog/post/2026-03-17-configure-auto-update-quadlet/view)
- [Podman Quadlet docs (v5.5.0)](https://docs.podman.io/en/v5.5.0/markdown/podman-systemd.unit.5.html)
- [LinuxServer.io Read-Only docs](https://docs.linuxserver.io/misc/read-only/)

---

## OsMEN-OC Assessment Notes

### What OsMEN-OC Is Likely Doing Right
- Using podman quadlets (correct modern approach)
- Using linuxserver.io images (well-maintained, good documentation)
- VPN pod concept for download clients

### What to Verify / Fix
- **Lingering enabled?** Without `loginctl enable-linger`, user services die on logout
- **Config volume persistence** — verify SABnzbd's `/config` is a persistent volume, not tmpfs
- **Port publishing** — ensure ports are published at the pod level, not duplicated on containers
- **Dependency ordering** — use `Requires=` and `After=` with `.service` suffixes
- **Health checks** — add health checks to gluetun at minimum; consider `Notify=healthy`
- **TimeoutStartSec** — increase from default 90s for VPN containers that take time to connect
- **auto-update** — add `io.containers.autoupdate=registry` labels and enable the timer
- **Arr app connectivity** — ensure arr apps can reach download clients (published ports or shared network)
- **FlareSolverr** — should NOT be in the VPN pod
- **qBittorrent password** — if lost, check logs for temp password after clearing `WebUI\Password` in config
