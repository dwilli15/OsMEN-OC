# OsMEN-OC Stabilization & Completion Plan
## Generated 2026-04-18 00:35 CDT — Synthesized from 5 sub-agent research passes

---

# Part 0: User Decisions Required

**Before anything executes, D answers these.** Minimum: Tier 1 (5 questions, 5 minutes). Full: all 20.

See: `openclaw/memory/plan-research/user-input-batch.md`

Quick reference for the 5 must-answer-now items:

| # | Question | Options | Default |
|---|----------|---------|---------|
| 1 | Download-stack ownership | (a) quadlet/systemd (b) manual (c) hybrid | **(a)** |
| 2 | qBittorrent auth path | (a) browser login (b) nuke config (c) deprioritize | **(a)** |
| 3 | Nextcloud | (a) commit (b) deprecate (c) defer | **(b)** |
| 4 | Calendar policy | (a) read-only (b) bidirectional (c) none (d) defer | **(a)** |
| 5 | PKM restore | (a) OneDrive (b) other (c) fresh start (d) defer | **(c)** |

---

# Part 1: Critical Findings Across All Research

## 🔴 Showstoppers (must fix before anything else)

1. **5 quadlet files have unresolved git merge conflicts** — `<<<<<<< HEAD` markers in chromadb, network, postgres, redis, core slice. These break quadlet generation entirely. Nothing systemd-managed will work until these are resolved.

2. **Download-stack is NOT under systemd/quadlet control** — containers were manually created via `podman run`. They will NOT survive a reboot. Quadlet symlinks exist but the generator hasn't processed them because of the merge conflicts.

3. **SABnzbd regressed to wizard mode** — `http://127.0.0.1:8082/` serves the Quick-Start Wizard. The earlier fix did not persist. Root cause per online research: SABnzbd enters wizard when `/config/sabnzbd.ini` is missing or unreadable. The container image is also floating on `:latest` instead of pinned.

4. **Postgres and Redis units show `not-found`** — symlinks exist but systemd hasn't loaded them. Gateway, Nextcloud, and Langflow all silently depend on these.

## 🟡 High-risk issues

5. **`ReadOnly=true` on 20+ containers** — most linuxserver.io apps need writable `/tmp`. The chromadb quadlet even has a comment saying ReadOnly was removed, but the directive is still there. Containers may be failing silently or were started before the directive was added.

6. **PUID/PGID missing on 6+ linuxserver containers** — Sonarr, Radarr, Lidarr, SABnzbd, Bazarr, Mylar3, Readarr all lack explicit user mapping. They run as root inside the container.

7. **3 floating images** — SABnzbd `:latest`, Komga-comics `:latest` (with auto-update!), Readarr `:nightly`. Unpredictable behavior on pulls.

8. **`openclaw/memory/2026-04-16.md` content was overwritten** — original daily notes (memory maintenance, 859 test results, cron fix, P13-P22 completions) were accidentally replaced with duplicate manga session data. Recoverable from git.

## 🟢 Things that are actually fine

- Pod topology is sound — download-stack as a single VPN pod is correct
- All 64 quadlet symlinks resolve to real files
- Volume cross-references are clean (1 orphan: ollama-models)
- VPN egress routing was verified correct
- Plex native install is stable
- Port conflicts are all resolved via remapping

---

# Part 2: The Plan — 6 Phases

## Phase 0: Prerequisites (before any container work)
**Time: 30 min | Dependency: D's Tier 1 answers | TaskFlow step: `prerequisites`**

### 0.1 Resolve git merge conflicts
Fix the 5 quadlet files with `<<<<<<< HEAD` markers:
- `quadlets/core/osmen-core-chromadb.container`
- `quadlets/core/osmen-core.network`
- `quadlets/core/osmen-core-postgres.container`
- `quadlets/core/osmen-core-redis.container`
- `quadlets/core/user-osmen-core.slice`

**Action:** Keep HEAD versions (they have the correct `$${VAR}` escaping and `10.89.0.0/24` subnet).

### 0.2 Recover lost daily notes
```
git show HEAD:openclaw/memory/2026-04-16.md > /tmp/2026-04-16-original.md
```
Merge original content back with any new additions.

### 0.3 Pin floating images
- `osmen-media-sabnzbd.container`: `:latest` → `:4.5.1`
- `osmen-media-komga-comics.container`: `:latest` → pin to current stable, remove `AutoUpdate=registry`
- `osmen-media-readarr.container`: `:nightly` → stable tag

### 0.4 Fix ReadOnly across all quadlets
For every container with `ReadOnly=true`, evaluate:
- If linuxserver.io image: add `Tmpfs=/tmp` alongside ReadOnly, or remove ReadOnly
- If the comment says ReadOnly was removed but the directive remains: remove the directive
- Specific fix for chromadb: remove `ReadOnly=true` (matches comment intent)

### 0.5 Add missing PUID/PGID
Add to all linuxserver.io containers that lack them:
```
Environment=PUID=1000
Environment=PGID=1000
```

### 0.6 Remove duplicate HealthCmd directives
Clean up chromadb, postgres, redis — keep only the correct health check for each.

**TW actions for Phase 0:**
- ADD: "Resolve 5 git merge conflicts in core quadlets" (H, osmen.maint, fix_needed)
- ADD: "Recover openclaw/memory/2026-04-16.md from git" (M, osmen.maint)
- ADD: "Pin floating container images (SAB, Komga, Readarr)" (H, osmen.media.pipeline)
- ADD: "Fix ReadOnly=true on 20+ quadlets" (H, osmen.maint, fix_needed)
- ADD: "Add missing PUID/PGID to linuxserver containers" (M, osmen.maint)
- ADD: "Remove duplicate HealthCmd directives" (L, osmen.maint)

---

## Phase 1: Download-Stack Reconciliation
**Time: 2-4 hours | Dependency: Phase 0 + D's answer to Q1 | TaskFlow step: `download_stack_reconcile`**

### 1.1 Stop manually-created containers
```bash
podman pod stop download-stack
podman pod rm download-stack
# Remove orphan containers if any
podman rm osmen-media-gluetun osmen-media-sabnzbd osmen-media-qbittorrent osmen-media-prowlarr
```

### 1.2 Reload quadlet generator
```bash
systemctl --user daemon-reload
```

### 1.3 Verify units now exist
```bash
systemctl --user list-unit-files | grep -E 'download-stack|osmen-media-(gluetun|sabnzbd|qbittorrent|prowlarr)'
```

### 1.4 Add missing dependency directives
Per architecture review:
- Gluetun: add `After=download-stack-pod.service Requires=download-stack-pod.service`
- download-stack.pod: add `After=osmen-media-network.service Requires=osmen-media-network.service`

### 1.5 Start the stack via systemd
```bash
systemctl --user start download-stack-pod.service
```

### 1.6 Verify
- All 4 containers running: `podman ps`
- Ports responding: 8082, 9090, 9696, 8888
- VPN egress: `podman exec osmen-media-gluetun wget -qO- ifconfig.me` (should be VPN IP, not host IP)
- SAB wizard state: check if `/config/sabnzbd.ini` exists in the volume

### 1.7 Topology correction (from online research)
**Prowlarr should NOT be in the VPN pod.** It needs direct internet for indexer searches. FlareSolverr also runs outside VPN.

Current quadlet has `Pod=download-stack.pod` for Prowlarr. Research strongly suggests Prowlarr should be standalone on `osmen-media.network`, reaching download clients via published pod ports.

**Decision point for D:** Move Prowlarr out of the VPN pod, or keep it in?
- Moving it out: better indexer reach, simpler FlareSolverr integration
- Keeping it in: all download-related services share VPN, but Prowlarr searches may be slower/restricted

**TW actions for Phase 1:**
- EXISTING: e9d3e070 "Reconcile download-stack runtime..." — keep, this is the anchor task
- ADD: "Evaluate Prowlarr placement (in-pod vs standalone)" (M, osmen.media.pipeline, user_input)

---

## Phase 2: SABnzbd Wizard Persistence Fix
**Time: 30-90 min | Dependency: Phase 1 | TaskFlow step: `sab_wizard_fix`**

### 2.1 Verify config volume
After Phase 1, the systemd-managed container should mount `osmen-sab-config.volume:/config`. Verify:
```bash
podman exec osmen-media-sabnzbd ls -la /config/sabnzbd.ini
```

### 2.2 If wizard is still showing
- Complete the wizard via browser at `http://127.0.0.1:8082/wizard/`
- Configure Eweka (host: `news.eweka.nl`, port: 563 SSL, connections: 50)
- Verify `/config/sabnzbd.ini` was written

### 2.3 Restart and recheck
```bash
systemctl --user restart osmen-media-sabnzbd.service
```
Verify root page no longer redirects to `/wizard/`.

### 2.4 Backup the config
```bash
podman exec osmen-media-sabnzbd cp /config/sabnzbd.ini /config/sabnzbd.ini.bak
```

**TW actions for Phase 2:**
- ADD: "Fix SABnzbd wizard regression — ensure config persists through restarts" (H, osmen.media.pipeline, fix_needed)

---

## Phase 3: qBittorrent Auth Recovery
**Time: 30-90 min | Dependency: Phase 1, D's answer to Q2 | TaskFlow step: `qbit_auth_fix`**

### If D chose (a) — browser login:
1. Stop the container
2. Clear `WebUI\Password` line from qBittorrent config in the volume
3. Start the container
4. Check logs for temp password: `podman logs osmen-media-qbittorrent 2>&1 | grep -i password`
5. Login with temp password at `http://127.0.0.1:9090`
6. Set new permanent password
7. Verify API login works

### If D chose (b) — nuke and recreate:
1. Delete the `osmen-qbit-config` volume contents
2. Restart container for fresh first-run
3. Set password on first login

### If D chose (c) — deprioritize:
Close the TW task with annotation "deprioritized by operator, Usenet is primary"

**TW actions for Phase 3:**
- EXISTING: 39477865 "qBittorrent auth recovery" — keep, execute per D's choice

---

## Phase 4: Prowlarr + FlareSolverr Stabilization
**Time: 1-2 hours | Dependency: Phases 1-3, D's answer to Q8 | TaskFlow step: `prowlarr_stabilize`**

### 4.1 Retest Prowlarr search
After the stack is systemd-owned and stable:
```bash
curl 'http://127.0.0.1:9696/api/v1/search?query=test&indexerIds=-1' -H 'X-Api-Key: <key>'
```

### 4.2 If FlareSolverr routing requested (Q8 = a)
Add to gluetun container environment:
```
Environment=FIREWALL_OUTBOUND_SUBNETS=10.89.0.0/24,192.168.4.0/24
```
This allows gluetun (and everything in the pod) to reach local subnet services like FlareSolverr.

### 4.3 Verify FlareSolverr reachability from pod
```bash
podman exec osmen-media-prowlarr curl -sf http://osmen-media-flaresolverr:8191/health
```

**TW actions for Phase 4:**
- EXISTING: f35bf91c "Investigate Prowlarr search" — demote to M, depends on Phases 1-3
- ADD: "Add FIREWALL_OUTBOUND_SUBNETS to gluetun for FlareSolverr access" (M, osmen.media.pipeline)
- FIX: COMICS-024 and COMICS-028 annotations — replace "VPN split routing" with "FIREWALL_OUTBOUND_SUBNETS"

---

## Phase 5: Taskwarrior + Cron Cleanup
**Time: 1-2 hours | Dependency: Phases 0-4 | TaskFlow step: `tw_cleanup`**

### 5.1 Close ~20 stale tasks
Per TW audit: test artifacts, completed downloads, deprecated Tailscale, duplicate Nextcloud, stale handoff dispatchers.

### 5.2 Fix "Blocked on P19" annotations
9+ tasks falsely claim P19 dependency. P19 completed 2026-04-16. Update all annotations.

### 5.3 Consolidate project taxonomy
- `Comics` → `osmen.media.pipeline` + tag `comics`
- `manga.*` → `osmen.media.pipeline` + tag `manga`
- `test` → `osmen.test` (then close artifacts)
- `osmen.handoff` tasks → delete after reading

### 5.4 Evaluate heckler-reviewer cron (per D's answer to Q9)
If kill: `openclaw cron delete heckler-reviewer-300s`
If modify: update interval

### 5.5 Reconcile core systemd units
Run `systemctl --user daemon-reload` and verify postgres/redis units load. This may already be fixed by Phase 0 merge conflict resolution.

**TW actions for Phase 5:**
- CLOSE: ~20 tasks (per tw-audit.md Section 2)
- FIX: 9+ annotations (per tw-audit.md Section 3.4)
- CONSOLIDATE: project taxonomy (per tw-audit.md Section 6)
- ADD: "Verify postgres/redis systemd units load after daemon-reload" (H, osmen.maint)

---

## Phase 6: Remaining Install Milestones
**Time: variable, can be parallel | Dependency: Phases 0-5 | TaskFlow step: `install_milestones`**

### 6.1 Bridge verification (P10.6-P10.9)
Requires D to send test messages. Provide step-by-step guide when ready.

### 6.2 Nextcloud (P16.4) — per D's answer to Q3
If deprecate: close task with annotation. If commit: provide admin setup URL.

### 6.3 Calendar (P17.5) — per D's answer to Q4
If read-only: create implementation task. If none: close task.

### 6.4 PKM restore (P14.5) — per D's answer to Q5
Per answer, either restore or close.

### 6.5 LM Studio verification (P8.9, P8.11) — per D's answer to Q6
These are explicitly manual-launch windows. Schedule when D is available.

### 6.6 Git working tree reconciliation
After stabilization: commit useful changes, revert or stash drift.

---

# Part 3: TaskFlow Integration

## How this merges TW + TaskFlow

**Taskwarrior** remains the ledger of record for individual tasks — what needs doing, what's done, priorities, dependencies.

**TaskFlow** provides the execution orchestration — flow identity, step progression, waiting states, child task linkage.

### Proposed TaskFlow structure

```
Flow: osmen-stabilization-2026-04-18
  controllerId: "osmen/install-stabilization"
  goal: "Stabilize OsMEN-OC install to single-source-of-truth state"

  Steps (sequential):
    prerequisites       → Phase 0 (merge conflicts, image pins, ReadOnly fixes)
    user_decisions       → WAITING on D's Tier 1 answers
    download_stack       → Phase 1 (reconcile to systemd)
    sab_wizard_fix       → Phase 2
    qbit_auth_fix        → Phase 3
    prowlarr_stabilize   → Phase 4
    tw_cleanup           → Phase 5
    install_milestones   → Phase 6 (parallel sub-tasks)
    finish               → All done

  stateJson:
    {
      "userDecisions": {},          // D's answers, populated after Q&A
      "phaseStatus": {
        "prerequisites": "pending",
        "download_stack": "pending",
        "sab_wizard": "pending",
        "qbit_auth": "pending",
        "prowlarr": "pending",
        "tw_cleanup": "pending",
        "milestones": "pending"
      },
      "twTasksClosed": [],
      "twTasksCreated": [],
      "blockers": []
    }
```

### TaskFlow waiting states

The flow enters `waiting` at these points:
1. After Phase 0: waiting on D's Tier 1 decisions
2. During Phase 3: if D needs to do browser login (manual action)
3. During Phase 6: if D needs to send test messages for bridge verification

Each waiting state has a clear `waitJson` describing what's needed and who needs to do it.

### Child tasks

Each phase can spawn child tasks via `taskFlow.runTask()`:
- Phase 0 prereqs → subagent for merge conflict resolution + quadlet fixes
- Phase 1 reconciliation → subagent for the actual container work
- Phase 4 Prowlarr → subagent for search testing
- Phase 5 cleanup → subagent for TW bulk mutations

### How TW tasks map to TaskFlow steps

| TW Task UUID | Description | TaskFlow Step |
|---|---|---|
| e9d3e070 | Reconcile download-stack | `download_stack` |
| 39477865 | qBittorrent auth | `qbit_auth_fix` |
| f35bf91c | Prowlarr search | `prowlarr_stabilize` |
| e94c22a8 | Cron cleanup | `tw_cleanup` |
| 22c73013 | Nextcloud admin | `install_milestones` |
| fa1a7b31 | Calendar policy | `install_milestones` |
| b2ea175b | PKM restore | `install_milestones` |
| 50f22dd9 | Telegram send test | `install_milestones` |
| 361efaf5 | Discord mention test | `install_milestones` |
| NEW | SAB wizard fix | `sab_wizard_fix` |
| NEW | Merge conflict resolution | `prerequisites` |
| NEW | Pin floating images | `prerequisites` |
| NEW | Fix ReadOnly | `prerequisites` |

---

# Part 4: Summary

## What this plan does

1. **Fixes the foundation first** (merge conflicts, broken directives, floating images)
2. **Restores systemd ownership** of the download stack
3. **Eliminates the SAB wizard regression** with proper config persistence
4. **Recovers qBittorrent auth** via the least-disruptive path
5. **Stabilizes Prowlarr** only after the base is solid
6. **Cleans the TW ledger** so it stops lying
7. **Uses TaskFlow** for durable step-by-step execution with waiting states for user input
8. **Batches all user decisions** into one pass

## What it does NOT do

- No pod restructuring (topology is sound)
- No inference engine rationalization (blocked on D's input)
- No new feature work until stabilization completes
- No manga/comics pipeline expansion
- No dashboard deployment

## Estimated total time

| Phase | Estimate | Parallelizable |
|-------|----------|----------------|
| Phase 0: Prerequisites | 30 min | No |
| User decisions | 5-15 min (D's time) | Parallel with Phase 0 |
| Phase 1: Download stack | 2-4 hours | No |
| Phase 2: SAB wizard | 30-90 min | No |
| Phase 3: qBit auth | 30-90 min | No (may need D) |
| Phase 4: Prowlarr | 1-2 hours | No |
| Phase 5: TW cleanup | 1-2 hours | Yes (after Phase 4) |
| Phase 6: Milestones | Variable | Yes (parallel) |

**Critical path: ~6-10 hours of agent work + ~15 min of D's time**

---

# Part 5: Implementation Gate

**⚠️ This plan does NOT auto-execute.**

D: review this plan, answer the Tier 1 questions (at minimum), and confirm:
- "Go" — execute the plan as written
- "Go with modifications" — specify what to change
- "Hold" — more discussion needed

The TaskFlow will be created and the first phase kicked off only after confirmation.
