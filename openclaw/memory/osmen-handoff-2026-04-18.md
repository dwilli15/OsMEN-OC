# OsMEN-OC expert handoff — last 48 hours

**Generated:** 2026-04-18 22:00 CDT  
**Scope:** Consolidated handoff across the sessions active in the last ~48 hours, with emphasis on the OsMEN install, audit drift, media stack drift, and what a fresh expert agent needs to know before touching anything.

---

## 0. Read this first

The install is **not cleanly broken**, but it is **not cleanly converged either**.

The main pattern across the last 48 hours:
- multiple agents solved immediate runtime problems by **manual podman/container recreation**
- Taskwarrior and earlier handoffs contain some good evidence, but also some stale assumptions and duplicate tasks
- the repo/quadlets no longer perfectly describe the live runtime for the media/download path
- some earlier “failures” were false negatives and were later corrected
- some real fixes were made but the cleanup/reconciliation pass never happened

If you are the next expert agent, do **not** assume either of these is fully true:
1. “the install is mostly done”
2. “everything is botched”

The real state is: **core platform mostly works, media/download stack has drift, and the install ledger needs a sober reconciliation pass before more feature work.**

---

## 1. Non-negotiable operator preferences / constraints

These were established during the recent sessions and should be treated as active constraints unless D says otherwise:

- Stay pragmatic; avoid over-engineering.
- **No mergerfs.**
- **No systemd mount units / elaborate fstab gymnastics** just to handle removable media behavior.
- External drives are **not expected to be unplugged**, so hot-plug robustness is not a priority.
- **Tailscale stays installed for now**, but it is **not required** and should **not** be treated as an install blocker.
- Inference rationalization (**Ollama vs Lemonade vs LM Studio**) is **blocked on user input**; do not silently consolidate runtimes.
- The download-stack/proxy work was explicitly **paused** after the proxy started working.
- User had previously asked Jarvis to remain in **planning mode unless told to implement**; the current handoff/TW update request is an explicit implementation request for documentation/reconciliation, not a blank check to keep changing the system.

---

## 2. Highest-confidence current picture

### Solidly true
- Plex was pivoted from container to **native `.deb` install** and is running as `plexmediaserver`.
- Kometa and Tautulli remain containerized.
- OpenClaw/gateway/core infra were heavily audited and many earlier false negatives were corrected.
- VPN routing for the download stack **was verified working**: download traffic exits via the VPN, host traffic does not.
- A working **Gluetun HTTP proxy** was exposed on `127.0.0.1:8888` and verified.
- SABnzbd was stuck in its first-run wizard; that was later fixed via web UI, and Eweka downloads started working at high speed.
- A large amount of DC comic and manga acquisition work happened after that fix.

### Also solidly true
- The **runtime is drifted away from clean quadlet/systemd ownership** for the download stack.
- qBittorrent auth is still unstable/broken for API-driven use.
- Prowlarr’s manual search/API behavior is still unreliable or outright broken for some flows.
- There are stale/noisy keepalive/reminder jobs related to manga/comics work.
- The working tree is currently dirty with both tracked modifications and untracked files.

---

## 3. Corrections to earlier bad assumptions

These points matter because several previous sessions got them wrong and then later corrected them:

1. **Tailscale is not a dependency.**  
   It is installed, not logged in, intentionally non-critical, and nothing in repo/config depends on it.

2. **LM Studio is not a daemon that should always be running.**  
   It is primarily a GUI app with a headless CLI path (`lms`). Earlier “dead service” framing was wrong.

3. **Download traffic was not leaking to the host WAN.**  
   Earlier concern was corrected: qBittorrent/SABnzbd traffic was verified exiting via the VPN endpoint while the host retained its own public IP.

4. **SABnzbd server config was not failing because the config file was wrong.**  
   It was failing because SABnzbd had never completed the first-run wizard, so config edits were effectively ignored.

5. **The “vanishing SAB queue” was not necessarily a bug.**  
   Once Eweka was configured, many comic NZBs completed so fast they disappeared between polls.

---

## 4. Session-by-session handoff summary (last ~48h)

## Session cluster A — 2026-04-16 audit / install reconciliation / prior handoff consolidation

This cluster produced the most install-focused evidence.

### What happened
- Cross-phase auditing continued and was consolidated.
- Core install phases P0–P9 had already been audited; later work extended/cleaned up findings for higher phases.
- Earlier handoff work was consolidated into a broad platform handoff.
- Multiple install tasks were marked complete, especially around orchestration, monitoring, and voice/runtime cleanup.

### Important outcomes
- SSH hardening typo was fixed.
- Lemonade/LM Studio/Tailscale understanding got corrected.
- Monitoring, orchestration, and several P14m/P19/P21/P22 tasks were moved forward or closed.
- Existing handoff docs were created, but they are now superseded by this one because the media/download sessions after that materially changed the live state.

### Caveat
A lot of TW completions from this cluster are real, but they coexist with later runtime drift in the media stack. Treat the core-platform completions as mostly trustworthy; treat media-stack “done” states as needing runtime verification.

---

## Session cluster B — 2026-04-17 Discord/general + subagents: manga networking + Komga + pod recreation

### What happened
- A coder subagent updated the download-stack pod design so Prowlarr could live inside the Gluetun-routed pod network.
- The download stack was manually recreated with ports for qBittorrent, SABnzbd, and Prowlarr.
- qBittorrent password work happened, including temporary password discovery and permanent password reset attempts.
- Manga bulk download activity restarted and real queueing resumed.
- A Komga comics container/setup path was created as a workaround because quadlet generation/systemd state was not trustworthy.

### Important outcomes
- Prowlarr, SABnzbd, and qBittorrent were pushed toward a shared VPN-routed pod model.
- Manual recreation solved immediate access/networking problems.
- A new Komga comics path/container was stood up, but again via workaround rather than a clean quadlet pipeline.

### Caveat
This was one of the big moments where **runtime functionality beat configuration hygiene**. It fixed real problems, but it increased drift between repo intent, quadlets, systemd, and actual running containers.

---

## Session cluster C — 2026-04-17 overnight/main: SAB wizard breakthrough + Eweka + comics flood

This is the single biggest operational breakthrough in the last 48h.

### What happened
- The agent discovered SABnzbd was still in the **Quick-Start Wizard**.
- SAB’s configured Usenet server was effectively inert until the wizard was completed through the browser UI.
- The wizard was completed with Eweka settings and the connection tested successfully.
- NZBgeek ingestion/queuing logic was repaired (notably the user-agent and enclosure URL handling).
- Hundreds of comic NZBs were queued and began completing very fast.

### Important outcomes
- **Eweka Usenet is live.**
- DC comic acquisition became real instead of hypothetical.
- “Why does SAB ignore config?” and “why does the queue look empty?” were both effectively resolved.

### Caveat
This work is operationally valuable, but it also deepened the gap between “install completion” and “system cleanly managed.” The system started doing useful work before the install was truly reconciled.

---

## Session cluster D — 2026-04-17 morning: triple-source manga acquisition

### What happened
- Komga library root mismatch was fixed.
- Kavita had to be re-registered after container recreation.
- Manga acquisition branched into three sources:
  - Nyaa torrents
  - NZBgeek/Usenet for licensed volumes
  - MangaDex for fan-scanlated material
- Large manga and comics transfers were initiated.

### Important outcomes
- The stack proved it could actually ingest a lot of content once SAB was functioning.
- Manga source strategy matured: MangaDex is incomplete for licensed items, Usenet is useful for official digital releases, torrents fill some of the rest.

### Caveat
This cluster moved the media objective forward, but it did not solve the install reconciliation. It also exposed persistent qBittorrent auth problems and more container lifecycle fragility.

---

## Session cluster E — 2026-04-18 keepalive / reviewer / continuation state

### What happened
- Download containers had exited and were manually restarted again.
- Yen Press PDF copying/post-processing resumed in the background.
- MangaDex bulk downloading was restarted from repo code after `/tmp` content disappeared.
- qBittorrent auth was still failing.
- Prowlarr search/API issues still looked broken.

### Important outcomes
- The work is still alive enough to continue, but only with babysitting.
- Background processes were still doing useful work on 2026-04-18.

### Caveat
This is more evidence that the media stack is **functional-but-fragile**, not stable.

---

## 5. Current install blockers for a new expert agent

Ordered by practical importance, not by phase number.

### A. Download stack drift: repo vs runtime vs systemd vs quadlet
**Problem:**
The working download stack was manually recreated. The repo quadlets were edited for the proxy and VPN approach, but the live stack is not cleanly reconciled back to systemd/quadlet ownership.

**Why this matters:**
Every later fix risks getting reverted, orphaned, or half-applied because there are now several sources of truth.

**What the next expert should do:**
1. Baseline the live stack (`podman ps`, `podman pod ps`, relevant unit status, mounted volumes, exposed ports).
2. Compare against:
   - `quadlets/media/download-stack.pod`
   - `quadlets/media/osmen-media-gluetun.container`
   - any user-level generated/systemd copies
3. Reconcile back to a single source of truth **without losing**:
   - VPN egress correctness
   - Prowlarr reachability
   - qBittorrent/SAB access
   - HTTP proxy at `127.0.0.1:8888`

### B. qBittorrent authentication is still broken
**Problem:**
The permanent password path has been unstable; API auth and local-bypass approaches have failed, and repeated attempts can trigger bans.

**Why this matters:**
It blocks reliable torrent automation and makes Prowlarr/qBittorrent integration brittle.

**Likely resolution path:**
A browser-based/manual login/reset may be required first, followed by a clean verification of config persistence.

### C. Prowlarr manual search/API behavior remains unreliable
**Problem:**
Multiple sessions reported manual/API search returning empty or unusable results even though some app-driven flows work.

**Why this matters:**
It creates false impressions that indexers are dead when the issue may be query path specific.

**Need:**
A clean diagnostic pass after the runtime/source-of-truth reconciliation.

### D. Keepalive / cron noise cleanup
**Problem:**
Manga/comics keepalive jobs were useful while D was AFK, but at least one reminder stream became noisy/stale.

**Why this matters:**
The install ledger gets polluted and the operator gets spammed.

### E. Nextcloud admin still not actually finished
This remains one of the legit pending install tasks.

### F. Calendar sync policy / implementation gap
Still unresolved; both operator decision and actual code posture matter.

### G. LM Studio verification is still technically pending
Not because LM Studio is broken, but because “verify API” only means something when it is manually launched for that purpose.

---

## 6. Pending install tasks that still genuinely matter

These are the meaningful pending install tasks still visible in TW:

- **P10.6 / P10.7 / P10.8 / P10.9** — live Telegram/Discord bridge verification and approval-flow verification
- **P14.5** — restore PKM data from backup
- **P16.4** — finish Nextcloud admin setup (duplicated in TW as both original and audit follow-up)
- **P17.5** — Google Calendar sync policy and follow-on implementation reality
- **P20.4 / P20.5** — gaming verification tasks, lower priority for install stabilization
- **P22.17** — Tailscale mesh task is effectively deprecated and should not block anything
- **P8.9 / P8.11** — LM Studio API verification and fallback-routing test, both contingent on deliberate manual runtime setup

---

## 7. Recommended first move for the next expert agent

Do this in order:

1. **Freeze the story.**  
   Read this file, the expert brief, and inspect TW before changing anything.

2. **Baseline the live state.**  
   Especially:
   - `git status --short`
   - user services for podman/quadlet-managed media units
   - native Plex service
   - actual running podman pods/containers
   - active cron jobs related to manga/comics keepalives

3. **Reconcile the download stack ownership first.**  
   Not qBittorrent auth first, not Prowlarr search first. Ownership/source-of-truth first.

4. **Then fix qBittorrent auth.**

5. **Then re-test Prowlarr search/indexer flows.**

6. **Then clean up stale cron reminders / keepalives.**

Only after that should the agent spend time on lower-priority install leftovers.

---

## 8. Working tree / artifact warning

At the time of this handoff, the repo is **not clean**.

Examples already observed in `git status`:
- modified docs and heartbeat files
- modified quadlets for media/librarian services
- modified transfer scripts
- new manga/media acquisition scripts
- new state/ and docs/plans content
- untracked skill/coder/openclaw memory artifacts

A fresh expert agent should treat the working tree as **evidence**, not as automatically correct or ready to commit.

---

## 9. Key files and paths

### Handoff / memory
- `openclaw/memory/osmen-handoff-2026-04-16.md`
- `openclaw/memory/osmen-handoff-2026-04-18.md` ← this file
- `openclaw/memory/osmen-expert-agent-brief-2026-04-18.md`
- `openclaw/memory/2026-04-16.md`
- `openclaw/memory/2026-04-17.md`
- `openclaw/memory/2026-04-18.md`

### Audit logs
- `vault/logs/audit-combined-2026-04-14.log`
- plus the phase-specific audit logs already referenced from earlier handoffs

### Media/download stack
- `quadlets/media/download-stack.pod`
- `quadlets/media/osmen-media-gluetun.container`
- `quadlets/media/osmen-media-prowlarr.container`
- `quadlets/media/osmen-media-komga-comics.container`
- `scripts/media/acquisition/mangadex_dl.py`
- `scripts/media/acquisition/queue_all_dc_comics.py`

### Env / runtime config
- `~/.config/osmen/env`
- `~/.openclaw/openclaw.json`

---

## 10. Bottom line

The next expert agent should **not** start by chasing every open thread.

The install can be stabilized fastest by doing three things well:
1. re-establish a single source of truth for the download/media runtime
2. fix qBittorrent auth and re-verify Prowlarr behavior on top of that stable base
3. clean the install ledger / keepalives / duplicate handoff clutter so future work stops fighting ghost state

If you do only one thing first, do **download-stack reconciliation**.
