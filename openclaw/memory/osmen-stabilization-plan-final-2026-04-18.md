# OsMEN-OC Stabilization Plan
## Source of truth: Taskwarrior
## Execution engine: OpenClaw TaskFlow
## Generated: 2026-04-18 03:47 CDT

---

## How this works

1. **Taskwarrior IS the plan.** Every task, dependency, and priority below is a real TW entry.
2. **TaskFlow executes it.** It reads TW's `depends:` graph, picks unblocked tasks, spawns subagents, marks done.
3. **This MD file is a view.** It's generated from live TW state. If TW changes, regenerate this.

## D's decisions (locked in)
- Download-stack: **(a) quadlet/systemd**
- qBittorrent: **(b) nuke and recreate**
- Nextcloud: **(a) commit**
- Calendar: **(b) bidirectional**
- PKM: **(c) fresh start**

---

## Task counts

| Tier | Count | Description | Est. hours |
|------|-------|-------------|------------|
| 0 | 9 | Unblock (merge conflicts, slices, firewall, ReadOnly) | 1-2 |
| 1 | 3 | Core services (PostgreSQL, Redis, Caddy) | 2-3 |
| 2 | 1 + 2 existing | Download stack stabilization | 2-3 |
| 3 | 4 | Arr stack + Prowlarr | 2-3 |
| 4 | 3 | Librarian + monitoring + dashboard | 2-3 |
| 5 | 2 | Core apps (Nextcloud, SiYuan, etc.) | 1-2 |
| 6 | 5 | Cleanup | 1-2 |
| 7 | 9 | Post-stabilization features | variable |
| — | 65 | Pre-existing (install, roadmap, configure) | — |
| **Total** | **101** | | **~12-18** |

---

## Dependency flow

```
TIER 0 (no deps — start immediately)
├── T0.1 Merge conflicts ──┐
├── T0.2 Missing slices ───┤
├── T0.3 UFW firewall      │ (independent)
├── T0.4 ReadOnly fix ─────┤
├── T0.5 Pin images         │
├── T0.6 PUID/PGID          │
├── T0.7 HealthCmd cleanup   │
├── T0.8 Recover daily notes │
└── T0.9 daemon-reload ─────┘ (depends: T0.1, T0.2, T0.4)
         │
TIER 1 ──┴── (depends: T0.9)
├── T1.1 PostgreSQL ──┐
├── T1.2 Redis ───────┤
└── T1.3 Caddy        │
         │            │
TIER 2 ──┴── (depends: T0.9 + T0.5)
├── Download-stack reconciliation (e9d3e070)
│   ├── T2.2 SABnzbd wizard fix
│   ├── qBittorrent nuke+recreate (39477865)
│   └── T3.4 FlareSolverr routing
│
TIER 3 ──── (depends: SAB + qBit)
├── Prowlarr search retest (f35bf91c)
│   ├── T3.1 Deploy Sonarr
│   ├── T3.2 Deploy Radarr
│   └── T3.3 Deploy Lidarr/Readarr/Bazarr/Mylar3
│
TIER 4 ──── (depends: T0.9)
├── T4.1 Librarian services
├── T4.2 Monitoring stack
│   └── T4.3 Homepage dashboard (depends: T4.2)
│
TIER 5 ──── (depends: T1.1 + T1.2)
├── T5.1 Nextcloud → P16.4 admin setup (depends: T5.1)
└── T5.2 SiYuan + Langflow + ChromaDB
│
TIER 6 ──── (no strict deps — run after main work)
├── T6.1 Fix symlinks
├── T6.2 Clean volumes
├── T6.3 Move SAB volume
├── T6.4 Fix double-mount
└── T6.5 Git commit
│
TIER 7 ──── (post-stabilization)
├── T7.1 Paperless-ngx (depends: PostgreSQL + Redis)
├── T7.2 Multi-agent Discord team
├── T7.3 Calendar bidirectional
├── T7.4 PKM architecture (depends: SiYuan)
├── T7.5 BentoPDF
├── T7.6 Miniflux (depends: PostgreSQL)
├── T7.7 Pangolin eval
├── T7.8 Restic/Borgmatic backups
└── T7.9 OpenClaw security tightening
```

---

## TaskFlow integration

### Execution loop

```
TaskFlow reads TW → picks unblocked tasks → spawns subagent → task done → TW unblocks next tier → repeat
```

### Tags TaskFlow understands

| Tag | Action |
|-----|--------|
| +USER_ACTION | → TaskFlow enters waiting state, prompts D |
| +USER_INPUT | → TaskFlow enters waiting state, prompts D |
| +fix_needed | → Spawn subagent to fix |
| +deploy | → Spawn subagent to deploy |
| +cleanup | → Spawn subagent to clean |
| +verify | → Spawn subagent to verify |
| +security | → Spawn subagent (may need elevated) |

### Flow identity

```
controllerId: "osmen/install-stabilization"
goal: "Execute TW dependency graph to stable single-source-of-truth state"
currentStep: <derived from TW unblocked tier>
stateJson: { completedTasks: [], currentTwUuid: null, blockedOnUser: [] }
```

### How to modify the plan

- Reprioritize: `task <uuid> modify priority:H` → TaskFlow picks it up
- Add task: `task add ... depends:<uuid>` → enters graph naturally
- Skip task: `task <uuid> done` → dependents unblock
- Pause everything: TaskFlow `requestCancel()` → TW state preserved

---

## Honest state (from 10-agent recon)

- **Running:** 5 containers + Plex native + Ollama + Lemonade + OpenClaw
- **Not deployed:** 21 planned services (all arr apps, all monitoring, core DB/cache, Nextcloud, etc.)
- **Broken:** SABnzbd (wizard), qBittorrent (auth), 3 exited containers
- **Blocking everything:** 5 merge conflicts + 4 missing slices + ReadOnly on 20+ quadlets
- **Security gap:** No firewall, SSH/Plex exposed to 0.0.0.0
- **Actual completion:** ~25%
- **Estimated work to stable:** 12-18 hours

---

*TW is the bible. TaskFlow reads it. This file is the view.*
