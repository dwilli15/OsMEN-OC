# OsMEN-OC Session Handoff — 2026-04-18 03:54 CDT

## STATUS: Plan complete, TW wired, awaiting D's "go" to execute

---

## What happened this session

1. D asked for a full TW install audit with detailed completion plan
2. Ran 5-agent research swarm (TW audit, online research, repo analysis, architecture review, user-input batch)
3. Built a 6-phase plan — D corrected: **TW is the bible**, plan must BE in TW, not float above it
4. Rewrote everything as real TW mutations with `depends:` chains + TaskFlow as execution engine
5. D answered Tier 1 decisions: **(1)a (2)b (3)a (4)b (5)c**
6. D considered Unraid → **decided to stay on Ubuntu 26 + Podman**
7. D shared massive vision dump (PKM, multi-agent Discord, inference ecosystem, interests)
8. Ran 10-agent deep recon swarm — **discovered install is ~25% done, not 70-80%**
9. Executed all TW mutations (36 new tasks, ~10 closed, 9 annotations fixed, projects consolidated)
10. Generated final plan MD + TaskFlow integration spec
11. Presented plan to D. **Awaiting "go" to begin Tier 0 execution.**

---

## D's locked-in decisions

| # | Decision | Answer |
|---|----------|--------|
| 1 | Download-stack ownership | **(a) quadlet/systemd** |
| 2 | qBittorrent auth | **(b) nuke and recreate** |
| 3 | Nextcloud | **(a) commit to it** |
| 4 | Calendar | **(b) bidirectional** |
| 5 | PKM | **(c) fresh start** |

---

## The honest state (from 10-agent recon)

- **Running now:** download-stack pod (gluetun, SAB, qBit, Prowlarr) + Plex native + Ollama + Lemonade + OpenClaw
- **NOT DEPLOYED (21 services):** ALL arr apps, PostgreSQL, Redis, Caddy, ALL monitoring, ALL librarian, Nextcloud, SiYuan, Langflow, ChromaDB
- **Broken:** SABnzbd (wizard mode), qBittorrent (auth), Kavita/Komga/FlareSolverr (exited)
- **Blocking everything:** 5 git merge conflicts + 4 missing slice definitions + ReadOnly=true on 20+ quadlets
- **Security:** No firewall. SSH + Plex exposed to 0.0.0.0
- **Actual completion:** ~25%
- **Hardware:** HP OMEN 17", Ryzen AI 9 365, RTX 5070 Max-Q 8GB, Radeon 880M iGPU, 60GB RAM, NPU unused

---

## TW state after mutations

**101 pending tasks** across 7 tiers + pre-existing:

| Tier | Count | What |
|------|-------|------|
| 0 | 9 | Unblock: merge conflicts, missing slices, UFW, ReadOnly, pin images, PUID/PGID |
| 1 | 3 | Core services: PostgreSQL, Redis, Caddy |
| 2 | 1 + 2 existing | Download stack: reconcile → SAB wizard → qBit nuke |
| 3 | 4 | Arr stack: Prowlarr retest → Sonarr/Radarr/Lidarr/etc |
| 4 | 3 | Librarian + monitoring + Homepage dashboard |
| 5 | 2 | Nextcloud, SiYuan/Langflow/ChromaDB |
| 6 | 5 | Cleanup: symlinks, volumes, SAB volume move, git commit |
| 7 | 9 | Features: Paperless-ngx, multi-agent Discord, calendar, PKM, BentoPDF, Miniflux, backups |

All tasks have real `depends:` chains. TW's dependency engine produces the execution order.

### Critical dependency chain
```
T0.1 merge conflicts + T0.2 slices + T0.4 ReadOnly
  → T0.9 daemon-reload
    → T1.1 PostgreSQL + T1.2 Redis (parallel)
    → Download-stack reconcile (e9d3e070)
      → SAB wizard (ec589dc6) + qBit nuke (39477865) (parallel)
        → Prowlarr retest (f35bf91c)
          → Sonarr/Radarr/etc deployment
```

---

## Key files the next session needs

| File | What |
|------|------|
| `openclaw/memory/osmen-stabilization-plan-final-2026-04-18.md` | The plan (MD view of TW state) |
| `openclaw/memory/osmen-honest-state-2026-04-18.md` | Honest state-of-play from recon |
| `openclaw/memory/plan-research/taskflow-tw-integration.md` | How TaskFlow drives TW |
| `openclaw/memory/plan-research/recon-01-containers.md` through `recon-10-research.md` | All 10 recon reports |
| `openclaw/memory/plan-research/tw-audit.md` | TW audit with close/fix/add recommendations |
| `openclaw/memory/plan-research/user-input-batch.md` | 20 decisions (Tier 1 answered, Tier 2+3 open) |
| `openclaw/memory/2026-04-18.md` | Daily notes with full session log |
| `scripts/tw-stabilization-plan.sh` | TW mutation script (already executed) |

---

## What the next session should do

### If D says "go":
1. Read this handoff + the stabilization plan
2. Start executing Tier 0 tasks (all agent-executable, no user input needed):
   - T0.1: Resolve 5 git merge conflicts (keep HEAD versions)
   - T0.2: Create 4 missing slice definitions
   - T0.3: Enable UFW
   - T0.4: Fix ReadOnly on 20+ quadlets
   - T0.5: Pin floating images
   - T0.6: Add PUID/PGID
   - T0.7: Remove duplicate HealthCmd
   - T0.8: Recover 2026-04-16.md from git
3. After T0.1 + T0.2 + T0.4 complete → run T0.9 (daemon-reload)
4. After T0.9 → Tier 1 and Tier 2 unblock

### If D wants changes:
- Edit TW directly: `task <id> modify ...` — TaskFlow adapts
- The plan IS TW. Change TW, you changed the plan.

---

## D's vision (captured, not yet actioned)

- **PKM:** Interconnected tagged databases — personal (secret), work, homeowner, entrepreneurial, father-husband, FFXIV, meditation instructor, dharma (dzogchen/mahamudra/tummo, 3 yanas, personal studies)
- **Multi-agent Discord:** Claude, OpenCode, local LM agents alongside OpenClaw in team chat
- **Inference:** Trial-and-error exploration of Lemonade, Ollama, LM Studio, VS Code Insiders, Claude, OpenCode, Wave Terminal
- **Port dashboard:** Homepage (P23) solves this — already in plan as T4.3
- **Interests:** Paperless-ngx, BentoPDF, Pangolin, deeper ConvertX, Miniflux, Restic/Borgmatic
- **Staying on Ubuntu 26 + Podman** (no Unraid, no Docker migration)

---

## Do NOT repeat these mistakes

1. Don't claim the install is 70-80% done. It's 25%.
2. Don't start with qBittorrent auth or Prowlarr. Start with merge conflicts.
3. Don't create containers manually with `podman run`. Use quadlet/systemd.
4. Don't assume services are running because quadlet files exist. Most have never been deployed.
5. Don't build plans outside TW. TW is the bible.
6. "Blocked on P19" is a lie — P19 completed 2026-04-16. Already corrected in 9+ task annotations.
7. VPN split routing was never the problem. The fix for FlareSolverr access is FIREWALL_OUTBOUND_SUBNETS in gluetun.
