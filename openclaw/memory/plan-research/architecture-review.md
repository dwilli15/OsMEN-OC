# Architecture + Stability Review — OsMEN-OC Pod Topology & Update Resilience

**Date:** 2026-04-18  
**Scope:** All quadlet units, live runtime state, dependency chains, SPOFs

---

## 1. Pod Topology Recommendation

### Current state
- **1 pod:** `download-stack` (gluetun + qBittorrent + SABnzbd + Prowlarr)
- **No pods** for arr apps, librarian services, or monitoring
- ~25 containers total, most standalone on `osmen-media.network` or `osmen-core.network`

### Assessment

**The download-stack pod is correct as-is.** Gluetun provides the shared network namespace, and qBittorrent + SABnzbd + Prowlarr must route through it. Splitting them would require each to independently configure VPN routing — more complexity, more failure modes, and risk of IP leaks.

**Arr apps (Sonarr, Radarr, Lidarr, Readarr, Mylar3) should NOT be in the pod.** They don't need VPN egress — they talk to download clients and Prowlarr over the internal network. Current placement is correct.

**Librarian services (Kavita, Komga, Audiobookshelf) should NOT share a pod.** They're independent read-only library servers with no shared network requirements. A pod would force unnecessary shared restarts.

**Verdict:** The current topology is sound. Don't restructure pods. The real problem is **ownership drift**, not topology.

### Network relationship (VPN → non-VPN)

```
download-stack pod (gluetun namespace)
├── gluetun → WireGuard tunnel (all egress)
├── qBittorrent → uses gluetun's network stack
├── SABnzbd → uses gluetun's network stack  
└── Prowlarr → uses gluetun's network stack

osmen-media.network (bridge)
├── Sonarr, Radarr, Lidarr, Readarr, Mylar3
├── Bazarr, Kometa, Tautulli
├── Komga-comics
└── download-stack pod (dual-homed via pod Network=)

osmen-core.network (bridge)
├── PostgreSQL, Redis, ChromaDB
├── Gateway, Caddy, Langflow, Nextcloud, SiYuan
├── Uptime Kuma, Portall
└── Librarian services (Kavita, ABS, ConvertX, Whisper)
```

This is clean. The only cross-network bridge is Caddy (dual-homed) and the download-stack pod.

---

## 2. Update Resilience Assessment

### Image pinning status

| Container | Pin | AutoUpdate label | Risk |
|---|---|---|---|
| gluetun | v3.40.2 ✅ | No | Low |
| qBittorrent | 5.1.0 ✅ | No | Low |
| SABnzbd | latest ⚠️ | No | **Medium** — wizard regression risk |
| Prowlarr | 1.35.1 ✅ | No | Low |
| Sonarr | 4.0.14 ✅ | No | Low |
| Radarr | 5.21.1 ✅ | No | Low |
| Lidarr | 3.1.0 ✅ | No | Low |
| Readarr | 0.4.12-nightly ⚠️ | No | **Medium** — nightly tag |
| Mylar3 | 0.8.1 ✅ | No | Low |
| Bazarr | 1.5.2 ✅ | No | Low |
| Kometa | v2.3.1 ✅ | No | Low |
| Tautulli | v2.17.0 ✅ | No | Low |
| Komga-comics | latest ⚠️ | **Yes** | **High** — auto-updates uncontrolled |
| Kavita | 0.8.6 ✅ | No | Low |
| Caddy | 2.9-alpine ✅ | No | Low |
| ChromaDB | 0.5.23 ✅ | No | Low |
| PostgreSQL | pg17 ✅ | No | Low |
| Redis | 7.2.5-alpine ✅ | No | Low |
| Nextcloud | 31.0.5-apache ✅ | No | Low |
| Others | Pinned | No | Low |

**Action items:**
1. **Pin SABnzbd** to `4.5.1` (or whatever current working version is) — `:latest` caused wizard regression
2. **Pin Komga-comics** and remove `AutoUpdate=registry` — it's the only auto-updating container
3. **Pin Readarr** to a stable tag — `:nightly` is reckless for a persistent service

### `podman auto-update` impact

Currently only `osmen-media-komga-comics` has the autoupdate label. No other containers would be affected. This is actually fine — auto-update is opt-in and narrowly scoped.

### Reboot behavior

**Critical finding: The download-stack pod is NOT owned by systemd quadlets right now.** The audit confirmed `systemctl --user status` shows "unit not found" for all download-stack units. This means:

- ✅ All other containers with `WantedBy=default.target` and proper symlinks will auto-start
- ❌ **Gluetun, qBittorrent, SABnzbd, Prowlarr will NOT auto-start on reboot** — they were manually created
- ❌ SABnzbd's `:latest` tag means a fresh pull after reboot could get a different version

### Postgres/Redis unit status

`osmen-core-postgres.service` and `osmen-core-redis.service` show as **not-found** — symlinks exist but systemd hasn't loaded them. This could mean:
- The symlinks were created but `systemctl --user daemon-reload` wasn't run
- Or the quadlet generator hasn't processed them yet

**This is a silent SPOF** — if these services aren't running, Gateway, Nextcloud, Langflow, and ChromaDB all fail.

---

## 3. Dependency Graph

```
NETWORKS (foundational)
  osmen-core.network ← required by all core/librarian services
  osmen-media.network ← required by all media services

DATA SERVICES (layer 1)
  osmen-core-postgres ← After/Requires: osmen-core-network
  osmen-core-redis    ← After/Requires: osmen-core-network

APPLICATION SERVICES (layer 2)
  osmen-core-chromadb    ← After/Requires: osmen-core-network
  osmen-core-gateway     ← After: postgres, redis, chromadb, network; Requires: network only ⚠️
  osmen-core-langflow    ← After: postgres, network; Requires: network only
  osmen-core-nextcloud   ← After: postgres, redis, network; Requires: network only
  osmen-core-caddy       ← After/Requires: osmen-core-network
  osmen-core-siyuan      ← After/Requires: osmen-core-network

MEDIA (layer 2)
  download-stack.pod     ← Network: osmen-media.network
    osmen-media-gluetun    ← (no After/Requires on pod!) ⚠️
    osmen-media-sabnzbd    ← After/Requires: gluetun
    osmen-media-qbittorrent← After/Requires: gluetun
    osmen-media-prowlarr   ← After/Requires: gluetun

MEDIA ARR (layer 3, independent of VPN)
  Sonarr, Radarr, Lidarr, Readarr, Mylar3, Bazarr ← After/Requires: osmen-media-network
  Kometa, Tautulli ← After/Requires: osmen-media-network

LIBRARIAN (layer 2)
  Kavita, Audiobookshelf, ConvertX, Whisper ← After/Requires: osmen-core-network

MONITORING (layer 3)
  Uptime Kuma ← After/Requires: osmen-core-network
  Portall ← (no network dependency) ⚠️
  Prometheus ← (no dependency declared)
  Grafana ← After: prometheus (only)
```

### Issues found

1. **Gateway doesn't `Require` its data backends.** It `After=` postgres/redis/chromadb but only `Requires=` the network. If postgres dies, gateway will still start and fail at runtime. **Fix:** Add `Requires=osmen-core-postgres.service osmen-core-redis.service` or use `Wants=` for softer coupling.

2. **Gluetun has no `After=` on the pod.** The pod creates the network namespace; gluetun should declare `After=download-stack-pod.service`. Currently it works because podman handles pod ordering, but it's fragile.

3. **Portall has no network dependency.** It uses the podman socket, not a network, so this is actually fine — but worth documenting.

4. **No `After=` relationship between download-stack pod and `osmen-media-network.service`.** The pod declares `Network=osmen-media.network` but doesn't `Require` or `After` the network unit. If the network isn't created first, pod creation could fail.

5. **Circular risk avoided:** Arr apps correctly don't `Require` gluetun/download-stack — they communicate over the shared network, so they don't need VPN up to start.

---

## 4. Single Points of Failure

### Gluetun (VPN gateway) — **CRITICAL SPOF**

If gluetun dies:
- qBittorrent, SABnzbd, Prowlarr lose all network connectivity (shared namespace)
- Active torrents stall, active Usenet downloads abort
- Prowlarr can't search indexers
- `Requires=osmen-media-gluetun.service` means systemd will try to restart all three alongside gluetun

**Mitigation:**
- Current `Restart=always` with `RestartSec=10s` on gluetun is adequate for transient crashes
- The `Requires=` chain ensures the whole stack restarts together — this is actually correct behavior
- **Gap:** No health-check-triggered restart. If gluetun's health check fails (tunnel drops but process stays alive), systemd won't notice. Consider adding `ExecStartPost` with a readiness gate or using podman's `--health-cmd` restart policy.

**What to add:**
```
[Service]
# If gluetun is unhealthy for >3 minutes, systemd will kill and restart
WatchdogSec=180
```

### PostgreSQL — **HIGH SPOF**

If postgres dies:
- Gateway, Nextcloud, Langflow all fail
- Currently shows as `not-found` in systemd — may not be running at all
- No `Requires=` from dependent services means they start anyway and fail silently

### External drive unmount (Plex)

Plex runs as native `.deb`, not containerized. If `/run/media/dwill/plex/` unmounts:
- Plex shows empty libraries
- No data corruption (read-only mounts)
- Re-mounting restores service
- **No mitigation needed** — this is expected behavior for removable media

### Redis failure

Less critical than postgres but affects Nextcloud locking and the event bus.

---

## 5. Innovation Recommendations (ranked by impact/effort)

### 🔴 High impact, low effort

1. **Fix download-stack ownership** — Reconcile runtime to quadlet/systemd. Stop the manually-created containers, run `systemctl --user daemon-reload`, then `systemctl --user start download-stack-pod.service`. This is the #1 stability fix.

2. **Pin all floating images** — SABnzbd → `4.5.1`, Komga-comics → specific tag, Readarr → stable. Remove `AutoUpdate=registry`.

3. **Run `daemon-reload` and verify all units load** — postgres and redis showing as `not-found` means the symlinks aren't being processed.

### 🟡 Medium impact, low effort

4. **Add `Requires=` for Gateway's data backends** — `Requires=osmen-core-postgres.service` prevents silent startup failures.

5. **Add pod dependency to gluetun** — `After=download-stack-pod.service Requires=download-stack-pod.service`

6. **Add network dependency to download-stack.pod** — `After=osmen-media-network.service Requires=osmen-media-network.service`

### 🟢 Medium impact, medium effort

7. **Enable Uptime Kuma and configure monitors** — Already has a quadlet. Add HTTP checks for all services. First alerting win.

8. **Centralized log aggregation** — Add `journald` LogRateLimit bump + optional Loki/Vector sidecar. Currently no log visibility.

9. **Container config backup** — `tar` up all named volumes weekly. The `osmen-db-backup.timer` already exists — extend it to cover volume snapshots.

### 🔵 Lower priority

10. **Health-check-triggered restart for gluetun** — Use `podman healthcheck run` in a timer, restart pod if unhealthy.

11. **Git merge conflict cleanup** — Multiple quadlets have unresolved `<<<<<<< HEAD` markers (chromadb, network, postgres, redis). **These will cause quadlet generation failures.**

---

## 6. Specific Quadlet Changes Recommended

### Immediate (stability)

**a) `quadlets/media/osmen-media-sabnzbd.container`**
```
- Image=docker.io/linuxserver/sabnzbd:latest
+ Image=docker.io/linuxserver/sabnzbd:4.5.1
```

**b) `quadlets/media/osmen-media-komga-comics.container`**
```
- Image=docker.io/gotson/komga:latest
+ Image=docker.io/gotson/komga:1.15.0   (or current stable)
- AutoUpdate=registry
- Label=io.containers.autoupdate=registry
+ Add full [Unit] section with After/Requires on osmen-media-network
+ Add [Service] section with Slice, MemoryMax, CPUQuota
+ Add [Install] section with WantedBy=default.target
```

**c) `quadlets/media/osmen-media-readarr.container`**
```
- Image=docker.io/linuxserver/readarr:0.4.12-nightly
+ Image=docker.io/linuxserver/readarr:0.4.0   (or current stable)
```

**d) `quadlets/core/osmen-core-gateway.container`**
```
- Requires=osmen-core-network.service
+ Requires=osmen-core-network.service osmen-core-postgres.service osmen-core-redis.service
```

**e) `quadlets/media/osmen-media-gluetun.container`**
```
[Unit]
+ After=download-stack-pod.service
+ Requires=download-stack-pod.service
```

**f) `quadlets/media/download-stack.pod`**
```
[Unit]
Description=OsMEN-OC Download Stack Pod
+ After=osmen-media-network.service
+ Requires=osmen-media-network.service
```

### Critical: Resolve git merge conflicts

The following files have unresolved merge conflicts that will **break quadlet generation**:
- `quadlets/core/osmen-core-chromadb.container`
- `quadlets/core/osmen-core.network`
- `quadlets/core/osmen-core-postgres.container`
- `quadlets/core/osmen-core-redis.container`
- `quadlets/core/user-osmen-core.slice`

Each has `<<<<<<< HEAD` / `=======` / `>>>>>>> origin/main` markers. The HEAD version appears to be the correct one (uses `$${VAR}` escaping, `10.89.0.0/24` subnet). Resolve by keeping HEAD.

---

## Summary

| Area | Status | Priority |
|---|---|---|
| Pod topology | ✅ Sound | No changes needed |
| Image pinning | ⚠️ 3 floating | Pin SAB, Komga, Readarr |
| Systemd ownership | 🔴 Broken | Reconcile download-stack, daemon-reload |
| Git merge conflicts | 🔴 5 files | Resolve immediately |
| Dependency chains | ⚠️ Minor gaps | Add 4-5 missing Requires/After |
| SPOFs | Gluetun (managed), Postgres (not-loaded) | Fix unit loading |
| Monitoring | Quadlet exists, not running | Enable Uptime Kuma |
| Backup | Timer exists, scope unknown | Extend to volumes |
