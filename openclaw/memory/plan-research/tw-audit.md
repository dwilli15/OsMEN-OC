# Taskwarrior Full Audit — 2026-04-18 00:30 CDT

## Section 1: Summary Stats

| Status | Count |
|--------|-------|
| Pending | 74 |
| Completed | 527 |
| Deleted | 4 |
| **Total** | **605** |

### Pending by project (top groups)

| Project | Count |
|---------|-------|
| osmen.media.pipeline | 10 |
| osmen.roadmap.acp | 8 |
| osmen.dashboard.homepage | 8 |
| osmen.maint | 7 |
| Comics | 6 |
| osmen.install.p10 | 4 |
| osmen.roadmap.devx | 4 |
| osmen.configure | 3 |
| osmen.handoff | 3 |
| osmen.install.p16 | 2 |
| osmen.install.p20 | 2 |
| osmen.install.p8 | 2 |
| osmen.install.p14 | 1 |
| osmen.install.p17 | 1 |
| osmen.install.p22 | 1 |
| osmen.install.p11 | 1 |
| osmen.test / test | 4 |
| manga / manga.priority:* | 5 |
| osmen.maintenance | 1 |
| osmen.300credits | 1 |

### Completed by project (representative)

The 527 completed tasks span osmen.install.p8 through p22, osmen.audit, osmen.roadmap.devx, and various fix/audit tasks. All P19 (orchestration spine) tasks are completed. All P21 (monitoring) tasks are completed. All P14m (model migration) tasks are completed.

---

## Section 2: Tasks to Close (should be deleted or marked done)

### 2.1 Stale/dead handoff tasks

| UUID | Description | Reason |
|------|-------------|--------|
| d22320ce | OSMEN MEDIA HANDOFF 2026-04-17 | Superseded by osmen-handoff-2026-04-18.md. Mentions "VPN split routing" as blocker which was corrected. Handoff tasks are read-once dispatchers, not work items. |

### 2.2 Effectively done but not closed

| UUID | Description | Reason |
|------|-------------|--------|
| 6b27359c | P22.17 Tailscale mesh | Tagged `deprecated`. Tailscale is intentionally non-critical. Close it. |
| 698baa34 | opencode.json agent.general-purpose prompt tuning | Annotation says "blocked on P19" — P19 is done. Task is stale. Either close or rewrite. |
| ae32e5fc | Sync lemonade-server with opencode, claude-code, openclaw | Lemonade is active, OpenClaw is running. This is either done or blocked on operator decisions. Close or clarify. |

### 2.3 Completed download tasks that are now stale

| UUID | Description | Reason |
|------|-------------|--------|
| 2916dbc4 | Manga Library Setup - Bulk download 299 titles | Annotation shows 94 series/184GB done, download still running. Close when download finishes; the "setup" part is done. |
| c717e915 | COMICS-019: Manga download running | Running process from /tmp — ephemeral. Close or convert to a check. |
| 3fba28e2 | COMICS-029: Manga torrent downloads — 15 series | Annotation says completed. Close it. |
| 20efc869 | Download found manga via SABnzbd | Annotation says 104 volumes downloaded, being copied. Close it. |

### 2.4 Test/duplicate tasks

| UUID | Description | Reason |
|------|-------------|--------|
| f162f741 | test_dep_task | Test artifact. Delete. |
| 6ed59689 | child task | Test artifact. Delete. |
| 9f9b49e8 | OsMEN hook integration test | No annotation, no evidence of purpose. Close or delete. |
| 64c31656 | Hook integration verify | Likely duplicate of above. Close or delete. |
| 780c92a0 | P16.4: Complete Nextcloud admin (duplicate) | Duplicate of 22c73013 (P16.4 Configure Nextcloud admin). Close one. |

---

## Section 3: Tasks to Fix

### 3.1 Wrong priority

| UUID | Task | Current | Should Be | Reason |
|------|------|---------|-----------|--------|
| e9d3e070 | Reconcile download-stack runtime | H | **H** ✓ | Correct — this is the top install blocker per handoff. |
| 39477865 | qBittorrent auth recovery | H | **H** ✓ | Correct. |
| f35bf91c | Investigate Prowlarr search | H | **M** | Blocked on qBit auth and download-stack reconciliation. Can't diagnose until those land. |
| 2916dbc4 | Manga Library Setup | H | **L** | Operational work, not install-critical. |
| c717e915 | COMICS-019 | none | **L** | Background process monitoring, not urgent. |

### 3.2 Misleading annotations

| UUID | Issue |
|------|-------|
| d22320ce | Claims "VPN split routing" as blocker — this was corrected in later handoffs. VPN routing is verified correct; the real issue is Gluetun blocking local subnet traffic (a config addition, not split routing). |
| 596f59ac | COMICS-024 claims "VPN blocks torrent tracker access — need split routing" — same misconception. The fix is `FIREWALL_OUTBOUND_SUBNETS` in Gluetun, not split routing. |
| e3777ec3 | COMICS-028 same VPN misconception. |

### 3.3 Wrong project/tag assignments

| UUID | Issue |
|------|-------|
| Comics tasks (6 total) | Should be `osmen.media.pipeline` not bare `Comics`. Fragmented namespace. |
| manga/manga.priority:* tasks (5 total) | Should be `osmen.media.pipeline` with a `manga` tag. Three separate projects for manga work is noise. |
| osmen.handoff (3 tasks) | Handoff tasks are dispatchers, not work. Should either be deleted after reading or moved to `osmen.maint`. |
| osmen.test + test (4 tasks) | Two separate test projects. Consolidate to `osmen.test` and delete artifacts. |

### 3.4 Stale "blocked on P19" annotations

Multiple roadmap.acp and roadmap.devx tasks have annotations saying "Blocked on P19 orchestration build." P19 is complete (all 16+ tasks closed 2026-04-16). These annotations are lying.

Affected UUIDs: e82cf34f, a65adb44, 6d075a81, a50716ac, 193228cf, e1b155e7, 2d27cc01, 063fb19f, 063fb19f.

---

## Section 4: Missing Tasks

### 4.1 Should exist but don't

| Proposed Task | Project | Priority | Reason |
|---------------|---------|----------|--------|
| SABnzbd wizard regression fix | osmen.media.pipeline | H | Live audit (2026-04-18 23:50) found SAB back in wizard mode. No TW task tracks this. |
| Reconcile download-stack quadlets to systemd | osmen.install.p11 | H | e9d3e070 tracks this but is in p11; the quadlet files are in media/. Project assignment may be fine, but a specific "stop containers → enable quadlet units → verify" checklist task would help. |
| Clean git working tree (commit or stash media drift) | osmen.maint | M | Working tree is dirty with media scripts, quadlet edits, docs. No task tracks the commit decision. |
| FlareSolverr network config (FIREWALL_OUTBOUND_SUBNETS) | osmen.media.pipeline | M | COMICS-024/028 describe the symptom but not the fix. Need a task for the actual Gluetun config change. |
| Kavita container restart + library rescan | osmen.media.pipeline | L | f9da6576 mentions it but is in wrong project. |
| Heckler reviewer cron evaluation | osmen.maint | L | Is the 300s reviewer cron still wanted? No task tracks the decision. |

### 4.2 Handoff tasks that should have been created

The 2026-04-18 handoff describes 5 recommended first actions. Only e9d3e070 (download-stack reconciliation) exists as a task. The remaining 4 (SAB wizard fix, qBit auth, Prowlarr re-test, cron cleanup) exist as media.pipeline tasks but aren't sequenced with clear dependencies.

---

## Section 5: Proposed Clean Dependency Graph

### Install stabilization chain (must be sequential)

```
e9d3e070  Reconcile download-stack to quadlet/systemd ownership
    ├── [NEW] SABnzbd wizard regression fix
    ├── 39477865  qBittorrent auth recovery
    │       └── f35bf91c  Investigate Prowlarr search (demote to M)
    └── [NEW] FlareSolverr network config
            └── [NEW] Kavita restart + rescan
```

### Install leftovers (parallel, after stabilization)

```
22c73013  P16.4 Nextcloud admin  (USER_ACTION)
fa1a7b31  P17.5 Calendar policy  (USER_INPUT)
b2ea175b  P14.5 PKM restore      (blocked)
```

### Bridge verification (parallel, USER_ACTION)

```
50f22dd9  P10.6 Telegram send test
abc7220e  P10.7 Telegram receive test
361efaf5  P10.8 Discord mention test
a1eaea82  P10.9 Approval flow test
```

### Media pipeline (after stabilization)

```
d5d7e885  Prowlarr add torrent indexers
596f59ac  COMICS-024 VPN/local access (fix: Gluetun config)
e3777ec3  COMICS-028 same root cause
2fca00f8  Mylar3 indexer
7c09fe94  Lidarr root folder
64b22a1f  Readarr root folder
3550426b  Prowlarr app sync to Lidarr+Readarr
de9510c8  Bazarr verify
```

### Roadmap/ACP (unblocked now that P19 is done)

All 8 osmen.roadmap.acp tasks can proceed. They were incorrectly marked "blocked on P19" but P19 completed 2026-04-16. These need fresh annotations acknowledging P19 is done and updated priority assessments.

### Dashboard (P23)

8 tasks (P23.1-P23.8) are a coherent plan. Keep them grouped. P23.1 is blocked on Podman API access decision.

---

## Section 6: Recommended Project/Tag Taxonomy Cleanup

### 6.1 Consolidate fragmented projects

| From | To | Tasks affected |
|------|----|----------------|
| `Comics` | `osmen.media.pipeline` | 6 tasks |
| `manga` | `osmen.media.pipeline` | 1 task |
| `manga.priority:H` | `osmen.media.pipeline` | 1 task |
| `manga.priority:M` | `osmen.media.pipeline` | 2 tasks |
| `manga.priority:L` | `osmen.media.pipeline` | 1 task |
| `test` | `osmen.test` | 2 tasks |
| `osmen.handoff` | delete after reading | 3 tasks |

### 6.2 Tag cleanup

- Remove `handoff` tag from all tasks (handoffs are docs, not task properties)
- Add `user_action` tag to all tasks requiring operator involvement (P10.6-P10.9, P16.4, P17.5, P8.9)
- Standardize `fix_needed` tag usage — currently on 3 tasks, should be on all media.pipeline tasks that are blocked by infrastructure issues
- Remove `deprecated` tag from P22.17 after closing the task

### 6.3 Priority recalibration

After consolidation, the pending queue should look like:

**H (8):** Download-stack reconciliation, qBit auth, SAB wizard fix, Telegram/Discord bridge tests (4), Nextcloud admin, Calendar policy

**M (8):** Prowlarr search, FlareSolverr config, P10.7/P10.9 bridge tests, P8.9/P8.11 inference verify, P20.4/P20.5 gaming verify, Lidarr/Readarr setup

**L (rest):** Everything else — ACP roadmap, dashboard plan, SMART checks, encryption, cron cleanup, comics verification

### 6.4 Annotation debt

The biggest annotation problem is the "Blocked on P19" lie across 9+ tasks. P19 completed 2026-04-16. Every task with that annotation needs it updated or removed. This is not cosmetic — it makes the dependency graph appear frozen when it isn't.

---

## Bottom Line

The TW database has **74 pending tasks**, of which roughly:
- **8 are genuinely high-priority install blockers**
- **~15 are real but lower-priority work**
- **~20 should be closed** (done, duplicate, stale, or test artifacts)
- **~10 are roadmap/planning tasks with wrong "blocked" annotations**
- **~15 are media pipeline tasks that should wait for download-stack stabilization**
- **~6 are comics/manga tasks in wrong projects**

The single most impactful cleanup action: **fix the "blocked on P19" annotations** on 9+ tasks. That alone unlocks the ACP roadmap and devx backlog.
