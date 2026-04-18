# OsMEN-OC live install audit — 2026-04-18 23:50 CDT

## Scope
Live verification pass against the current repo, Taskwarrior, podman runtime, systemd ownership, and active OpenClaw cron jobs.

## Executive summary
The install is **usable but not converged**.

The most important live findings:
1. **download-stack drift is real and current**
   - the active pod/containers are running
   - the repo quadlets have the intended VPN/proxy/Prowlarr-in-pod changes
   - but the live runtime is **not currently owned by user systemd/quadlet units**
2. **SABnzbd regressed back into wizard mode on the live endpoint**
   - `http://127.0.0.1:8082/` redirects to `/wizard/`
   - the page title is `SABnzbd Quick-Start Wizard`
   - SAB API still answers `{"version":"4.5.5"}`
   - this means the earlier wizard fix did **not** survive cleanly into the current runtime path
3. **qBittorrent and Prowlarr are reachable, but qBittorrent auth was intentionally not retried**
   - qBittorrent UI responds on `127.0.0.1:9090`
   - Prowlarr `/ping` returns `200 OK`
   - qBittorrent login attempts were not repeated during this audit to avoid ban churn
4. **only one OpenClaw cron job is active now**
   - `heckler-reviewer-300s` every 5 minutes
   - stale/noisy reminder state may now be more of a Taskwarrior/handoff cleanup problem than a large live cron inventory problem
5. **Taskwarrior still contains useful pending tasks, but also some stale or misleading state**
   - current pending counts observed during this audit:
     - `osmen.install`: 14
     - `osmen.handoff`: 3
     - `osmen.media.pipeline`: 9
   - one handoff task still encodes stale claims (`VPN split routing` as a blocker)

## Repo / git state
Observed dirty working tree includes:
- modified:
  - `quadlets/media/download-stack.pod`
  - `quadlets/media/osmen-media-gluetun.container`
  - `quadlets/media/osmen-media-prowlarr.container`
  - `quadlets/librarian/osmen-librarian-kavita.container`
  - `scripts/media/transfer/movie_transfer.sh`
  - multiple OpenClaw memory/docs files
- untracked:
  - `quadlets/media/osmen-media-komga-comics.container`
  - `scripts/media/acquisition/mangadex_dl.py`
  - `scripts/media/acquisition/queue_all_dc_comics.py`
  - multiple temporary/iterative manga scripts
  - `state/`, `docs/plans/`, and OpenClaw handoff artifacts

## Download-stack ownership audit
### Repo intent
The quadlets now describe:
- pod-level publish for:
  - qBittorrent `127.0.0.1:9090`
  - SABnzbd `127.0.0.1:8082`
  - Prowlarr `127.0.0.1:9696`
  - Gluetun HTTP proxy `127.0.0.1:8888`
- Gluetun with `HTTPPROXY=on`
- Prowlarr moved into `Pod=download-stack.pod`

### Live runtime
Running containers during audit:
- `osmen-media-gluetun`
- `osmen-media-sabnzbd`
- `osmen-media-qbittorrent`
- `osmen-media-prowlarr`
- pod infra container

### Ownership problem
- `systemctl --user status download-stack-pod.service osmen-media-gluetun.service osmen-media-sabnzbd.service osmen-media-qbittorrent.service osmen-media-prowlarr.service`
  reported **unit not found** for all queried download-stack units
- the running containers did **not** show systemd/quadlet ownership metadata in the container labels inspected during this audit
- conclusion: live containers appear to have been started outside current user systemd/quadlet control

## Media runtime snapshot
### Running now
- download-stack pod running
- Plex native service active (`plexmediaserver.service`)

### Not running now (from `podman ps -a` snapshot)
- `osmen-librarian-kavita` exited
- `osmen-media-flaresolverr` exited
- `osmen-media-komga-comics` exited
- `osmen-core-gateway-test` created only

## Taskwarrior audit notes
### High-confidence install blockers still real
- `P10.6` / `P10.7` / `P10.8` / `P10.9` live bridge and approval verification still need real operator tests
- `P14.5` PKM restore still blocked/deferred
- `P16.4` Nextcloud admin still not confirmed complete
- `P17.5` calendar policy + implementation remains unresolved
- `P8.9` / `P8.11` LM Studio verification/fallback remain pending and should stay explicitly manual
- `Reconcile download-stack runtime back to quadlet/systemd ownership...` is correctly pending and should be treated as top install stabilization work

### TW hygiene issues observed
- `osmen.handoff` has 3 pending, not 2
- handoff task 74 still mentions `VPN split routing` as a blocker even though recent handoffs corrected that assumption
- several media tasks include DONE annotations inside still-pending tasks, which is useful context but makes the ledger noisy

## Recommended order from this live audit
1. Reconcile download-stack runtime back to one explicit owner (quadlet/systemd or a newly documented alternative).
2. Re-stabilize SABnzbd state so the wizard regression is eliminated persistently.
3. Recover qBittorrent auth with a browser/manual path, avoiding repeated API lockouts.
4. Re-test Prowlarr manual/API behavior only after steps 1-3.
5. Clean stale TW/handoff noise and the reviewer cron if it is no longer wanted.
6. Resume lower-priority install leftovers (Nextcloud admin, PKM restore, calendar policy, LM Studio manual verification, gaming verification).

## Bottom line
This is **not** a green install.
It is also **not** a dead install.

The machine is in a classic “runtime works better than ownership/state” condition:
- good enough to mislead someone into thinking setup is mostly done
- drifted enough that every additional fix risks compounding the mess unless ownership is stabilized first
