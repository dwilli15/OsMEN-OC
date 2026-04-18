# User Input Batch — Decisions Needed from D

**Compiled:** 2026-04-18 00:30 CDT  
**Purpose:** One pass, one sitting. Answer everything here so no agent has to interrupt you again during stabilization work.

**How to answer:** For each item, just write your choice next to the number. Skip anything marked `can-defer` if you want to come back to it later.

---

## Tier 1 — Must Answer Now (blocks active stabilization work)

### 1. Download-stack ownership model
**Question:** Should the download stack (gluetun, sabnzbd, qbittorrent, prowlarr) be reconciled back to quadlet/systemd user units, or documented as a manual podman-run workflow?
- **(a)** Reconcile to quadlet/systemd — single source of truth in repo, survives reboots cleanly
- **(b)** Document as manual podman-run — less config debt, you restart it when you need it
- **(c)** Hybrid — quadlet for the pod, manual for containers inside it

**Context:** The live containers were manually recreated and are NOT under systemd control. Every restart right now is manual babysitting.
**Default:** (a) — quadlet/systemd reconciliation
**Impact if deferred:** Every container restart is manual. SAB wizard regression keeps recurring. The system is fragile.
**Category:** architecture  
**Priority:** must-answer-now

### 2. qBittorrent auth recovery path
**Question:** qBittorrent login is broken (password rejected, API lockouts). Are you willing to do a one-time browser login to `127.0.0.1:9090`, reset the password, and confirm it sticks? Or should we just nuke and recreate the qBittorrent container/config?
- **(a)** I'll do the browser login — tell me exactly what to click
- **(b)** Nuke and recreate the container with fresh config
- **(c)** Deprioritize qBittorrent entirely, rely on SABnzbd/Usenet for now

**Context:** Torrent automation is blocked. Usenet (SABnzbd + Eweka) works fine for NZBgeek content.
**Default:** (a) — browser login, least disruptive
**Impact if deferred:** No torrent downloads work. MangaDex-external titles (like SPY×FAMILY) remain unobtainable via automated pipelines.
**Category:** auth  
**Priority:** must-answer-now

### 3. Nextcloud: commit or deprecate?
**Question:** Nextcloud is reachable but admin setup was never completed. Do you want to actually use it, or should we stop pretending it's part of the install?
- **(a)** I want Nextcloud — I'll complete the admin setup (just tell me the URL)
- **(b)** Deprecate it — remove from install milestones, leave container running but don't invest more time
- **(c)** Defer — leave pending, I'll decide later

**Context:** It's been pending since install Phase 16. No admin user exists. Every audit flags it as incomplete.
**Default:** (b) — deprecate unless you have a specific use case
**Impact if deferred:** It keeps showing up as a failed install task. Wastes audit cycles.
**Category:** policy  
**Priority:** must-answer-now

### 4. Calendar sync policy
**Question:** No calendar integration code exists yet. If/when it's built, what should the policy be?
- **(a)** Read-only surface — agents can read your Google Calendar but never write to it
- **(b)** Bidirectional — agents can create/modify calendar events
- **(c)** No calendar integration at all
- **(d)** Defer — decide when the feature is actually requested

**Context:** Task P17.5 has been pending since install start. No code exists. This is just a policy decision to unblock future work.
**Default:** (a) — read-only is safest
**Impact if deferred:** Any future calendar implementation has to guess your intent.
**Category:** policy  
**Priority:** must-answer-now

### 5. PKM restore: still wanted?
**Question:** SiYuan is running but no PKM (personal knowledge management) data has been restored from backup. Do you still want this?
- **(a)** Yes — restore from OneDrive (need to verify backup contents first)
- **(b)** Yes — restore from a different source (specify)
- **(c)** No — SiYuan stays running but I don't need old data
- **(d)** Defer

**Context:** OneDrive audit was completed but no pulls were made because nothing was verified. The task has been blocked for weeks.
**Default:** (c) — unless you have specific data you need
**Impact if deferred:** Low. SiYuan works fine as a fresh instance.
**Category:** feature  
**Priority:** must-answer-now

---

## Tier 2 — Should Answer Soon (affects next steps after stabilization)

### 6. Inference engine strategy
**Question:** Three inference runtimes exist: Ollama (working, daemonized), LM Studio (GUI app, manual launch), Lemonade (tasked but unclear status). What should happen?
- **(a)** Ollama only — deprecate LM Studio and Lemonade
- **(b)** Ollama primary + LM Studio on-demand (for GUI experimentation)
- **(c)** Ollama primary + Lemonade (AMD GPU inference)
- **(d)** Keep all three, just make sure routing rules work
- **(e)** Defer — I'll decide after stabilization is done

**Context:** Per your ground rules, no auto-rationalization. This is explicitly your call.
**Default:** (e) — defer per your stated preference
**Impact if deferred:** None for stabilization. Only matters when inference routing is tested.
**Category:** architecture  
**Priority:** should-answer-soon

### 7. Tailscale: formally deprecate or keep dormant?
**Question:** Tailscale is installed but not logged in, not required, and nothing depends on it. Should we:
- **(a)** Formally deprecate — close the task, document as "not needed"
- **(b)** Keep dormant — leave installed, don't touch it
- **(c)** Actually set it up — I do want mesh access

**Context:** Multiple sessions have confirmed Tailscale is non-critical. The task keeps showing up as pending/deprecated.
**Default:** (a) — formally deprecate to clean the ledger
**Impact if deferred:** Minor. One stale TW task.
**Category:** architecture  
**Priority:** should-answer-soon

### 8. FlareSolverr: worth fixing the gluetun routing?
**Question:** FlareSolverr works standalone (bypasses Cloudflare) but Prowlarr inside the VPN pod can't reach it. Fixing this requires adding `FIREWALL_OUTBOUND_SUBNETS` to the gluetun config. Is this worth doing?
- **(a)** Yes — fix the routing so Prowlarr can use FlareSolverr for CF-protected indexers
- **(b)** No — leave FlareSolverr standalone, it's not critical
- **(c)** Move FlareSolverr into the VPN pod alongside Prowlarr

**Context:** This would unlock torrent indexers behind Cloudflare (1337x, etc.) for Prowlarr automated searches.
**Default:** (a) — it's a small config change with real value
**Impact if deferred:** Torrent indexers behind Cloudflare remain inaccessible to Prowlarr.
**Category:** architecture  
**Priority:** should-answer-soon

### 9. Heckler reviewer cron: keep, modify, or kill?
**Question:** There's an active OpenClaw cron job (`heckler-reviewer-300s`) running every 5 minutes. What should happen to it?
- **(a)** Keep it as-is
- **(b)** Modify the interval (specify: ___ minutes)
- **(c)** Kill it — it's noise
- **(d)** I don't know what this is — explain it first

**Context:** This is the only active OpenClaw cron job. It may be generating noise during stabilization.
**Default:** (c) — kill during stabilization, re-enable later if needed
**Impact if deferred:** Possible noise in agent sessions. Minor.
**Category:** cleanup  
**Priority:** should-answer-soon

### 10. Telegram/Discord bridge live testing
**Question:** Tasks P10.6-P10.9 require you to send actual test messages through Telegram and Discord to verify the bridge works end-to-end. Are you available/willing to do this testing?
- **(a)** Yes — give me the test steps for Telegram
- **(b)** Yes — give me the test steps for both Telegram and Discord
- **(c)** Not now — defer to after stabilization
- **(d)** Discord isn't working for me anyway — skip it

**Context:** The bridge code paths are verified but never live-tested. Untested ≠ broken, but also ≠ working.
**Default:** (c) — defer until stabilization is done
**Impact if deferred:** Conversation mode remains unverified. Not a blocker for anything else.
**Category:** feature  
**Priority:** should-answer-soon

### 11. Gaming verification: still a priority?
**Question:** Steam is installed. FFXIV GPU verification (P20.4) and GPU conflict testing (P20.5) are pending. Do you still care about these?
- **(a)** Yes — test gaming after stabilization
- **(b)** No — close these tasks, gaming is manual/visual verification
- **(c)** Defer indefinitely

**Context:** These were Phase 20 tasks. They're explicitly lower priority than stabilization.
**Default:** (b) — close them unless gaming is important to you right now
**Impact if deferred:** None for stabilization.
**Category:** feature  
**Priority:** should-answer-soon

---

## Tier 3 — Can Defer (nice-to-have, not blocking)

### 12. External drives: mount policy?
**Question:** You have three external drives (WD Elements 4.5T, WD My Passport 1.8T, Samsung 870 QVO 1T) that stay plugged in. Do you need any mount policy beyond "they stay plugged in and mounted where they are"?
- **(a)** No — current setup is fine, drives stay plugged in
- **(b)** Yes — I want specific fstab entries or mount points (specify)
- **(c)** Yes — I want LUKS encryption on one or more (specify which)

**Context:** Per your ground rules, no elaborate mount solutions. This is just confirming the baseline.
**Default:** (a) — no changes needed
**Impact if deferred:** None. Drives are already working.
**Category:** architecture  
**Priority:** can-defer

### 13. Manga/comics acquisition: done for now or ongoing?
**Question:** The manga pipeline has 72 titles queued from MangaDex, 104 Yen.Press volumes copying, and DC comics at ~3800 CBZ. The pipeline is functional but fragile (qBittorrent down, Prowlarr unreliable). What's the goal?
- **(a)** Finish what's in-flight, then stop — current queued content is enough
- **(b)** Keep going after stabilization — fix the blockers and continue acquiring
- **(c)** Pause everything — I'll curate manually later
- **(d)** I'm satisfied with what we have — close out all manga/comic tasks

**Context:** ~184GB of manga + ~135GB of DC comics acquired. Several background processes are still running.
**Default:** (a) — let in-flight work finish, then pause
**Impact if deferred:** Background processes may complete on their own. No harm in waiting.
**Category:** feature  
**Priority:** can-defer

### 14. Homepage dashboard: proceed with plan?
**Question:** Tasks P23.1-P23.8 describe a Homepage dashboard deployment (quadlet, config generation, Caddy proxy, secrets strategy). Should this be built after stabilization?
- **(a)** Yes — proceed with the full P23 plan after stabilization
- **(b)** Simplified version — just the container, minimal config
- **(c)** Not now — defer to a future milestone
- **(d)** I don't need a dashboard

**Context:** The plan is detailed and ready to execute. It's purely additive work.
**Default:** (c) — defer until the install is actually stable
**Impact if deferred:** None. It's a nice-to-have.
**Category:** feature  
**Priority:** can-defer

### 15. Git working tree cleanup
**Question:** The repo has modified quadlets, new scripts, untracked files, and handoff artifacts. When should we commit/reconcile this?
- **(a)** After stabilization — one big reconciliation commit
- **(b)** Now — commit what's useful, trash the rest
- **(c)** I'll handle git myself

**Context:** The working tree is messy but contains real work product (manga scripts, updated quadlets, handoff docs).
**Default:** (a) — after stabilization, commit everything that's real
**Impact if deferred:** Risk of losing track of what changed. Low practical impact.
**Category:** cleanup  
**Priority:** can-defer

### 16. SMART health checks for all drives
**Question:** Five SMART health check tasks are pending (nvme0n1, nvme1n1, sda, sdb, sdc). Want these run?
- **(a)** Yes — run all five now
- **(b)** Yes — but defer to after stabilization
- **(c)** No — I'll handle drive health manually

**Default:** (b) — run them eventually, they're 5-minute checks
**Impact if deferred:** None. Just maintenance.
**Category:** cleanup  
**Priority:** can-defer

### 17. Windows drive encryption (nvme0n1)
**Question:** Your Windows system drive (Samsung 954G) is unencrypted. A task exists to encrypt it (BitLocker or VeraCrypt). Want to pursue this?
- **(a)** Yes — use BitLocker
- **(b)** Yes — use VeraCrypt
- **(c)** No — leave it unencrypted
- **(d)** Defer

**Default:** (d) — defer, this is a manual Windows operation
**Impact if deferred:** None for Linux/OSMEN work.
**Category:** cleanup  
**Priority:** can-defer

### 18. LUKS verification on Linux drive (nvme1n1)
**Question:** Your Linux system drive (SK Hynix 932G) has LUKS. Want to verify key slots and backup headers?
- **(a)** Yes — verify now
- **(b)** Yes — after stabilization
- **(c)** No — I'm confident it's fine
- **(d)** Defer

**Default:** (b) — quick check, do it when convenient
**Impact if deferred:** None. Just due diligence.
**Category:** cleanup  
**Priority:** can-defer

### 19. ACP / external-agent integration roadmap
**Question:** There are 7 pending tasks in `osmen.roadmap.acp` for external-agent ingress (Claude Code, VS Code, OpenCode, etc.). All are blocked on P19 orchestration. What should happen to this roadmap?
- **(a)** Keep the tasks — they're correctly blocked, just waiting
- **(b)** Close them — this is scope creep, revisit later
- **(c)** Consolidate into a single tracking task, close the rest

**Default:** (c) — consolidate to reduce TW noise
**Impact if deferred:** None. They're all blocked anyway.
**Category:** cleanup  
**Priority:** can-defer

### 20. Google Cloud $300 credits
**Question:** You have $300 in Google Cloud credits to spend. Any strategic plans?
- **(a)** Yes — I have a plan (specify)
- **(b)** No — defer, I'll think about it
- **(c)** Let an agent propose options

**Default:** (b) — defer, no urgency
**Impact if deferred:** Credits expire eventually but no immediate loss.
**Category:** feature  
**Priority:** can-defer

---

## Summary

| Tier | Count | Purpose |
|------|-------|---------|
| 1 — Must Answer Now | 5 | Blocks stabilization work |
| 2 — Should Answer Soon | 6 | Affects next steps after stabilization |
| 3 — Can Defer | 9 | Nice-to-have, not blocking |

**Total decisions:** 20

**Minimum viable response:** Answer Tier 1 (items 1-5). That's 5 decisions and unblocks all active stabilization work.
