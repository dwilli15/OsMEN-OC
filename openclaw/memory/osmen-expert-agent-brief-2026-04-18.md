# Expert-agent brief — fix the OsMEN install without making it messier

You are inheriting an OsMEN-OC install that is **partly working and partly drifted**.

## Your mission
Stabilize the install and runtime **without** doing broad redesign.

## Ground rules from D
- No mergerfs.
- No over-engineered mount/systemd solutions for external media drives.
- Tailscale may remain installed, but it is **not** an install dependency.
- Do **not** auto-rationalize Ollama/Lemonade/LM Studio without user input.
- Prefer boring, reversible fixes.

## What is actually broken
1. **download-stack ownership drift**
   - live pod/containers were manually recreated
   - repo quadlets and runtime are not fully reconciled
   - proxy at `127.0.0.1:8888` works and must not be lost

2. **qBittorrent auth is still broken**
   - API login unreliable
   - repeated attempts can trigger bans
   - may require manual browser reset/login path

3. **Prowlarr manual/API search is unreliable**
   - some searches return empty/broken results
   - do not diagnose this before fixing ownership drift

4. **stale keepalive/reminder noise exists**
   - manga/comics keepalive jobs became noisy

5. **install leftovers still pending**
   - Nextcloud admin setup
   - Calendar policy/implementation gap
   - LM Studio API verification only when manually launched

## Facts you should trust
- Plex is native `.deb`, not containerized.
- Kometa and Tautulli are containerized.
- SABnzbd wizard was the real root cause of prior Usenet failure; Eweka now works.
- VPN egress for download clients was verified as correct.
- LM Studio is not a daemon expected to run 24/7.
- Tailscale is not blocking anything.

## First 6 actions
1. Read `openclaw/memory/osmen-handoff-2026-04-18.md`.
2. Inspect `git status --short`.
3. Baseline live media/download runtime (`podman ps`, `podman pod ps`, relevant user units, native Plex service).
4. Compare live state to:
   - `quadlets/media/download-stack.pod`
   - `quadlets/media/osmen-media-gluetun.container`
   - `quadlets/media/osmen-media-prowlarr.container`
5. Reconcile runtime back to one source of truth **without breaking** the proxy or VPN egress.
6. After that, fix qBittorrent auth and only then re-test Prowlarr.

## Don’t waste time on this first
- inference-engine cleanup
- Tailscale mesh
- gaming verification
- more manga/comic feature work
- new architecture docs

## Success condition
When you are done with the first stabilization pass:
- the download stack is once again clearly owned by repo quadlets/systemd or another explicitly documented single authority
- qBittorrent auth works reliably
- Prowlarr behavior is re-tested on a stable base
- noisy keepalives are cleaned up
- TW/handoff state matches reality better than it does now
