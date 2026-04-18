# TaskFlow ↔ Taskwarrior Integration Design
# OsMEN-OC Stabilization — 2026-04-18

## Principle

**TW is the bible.** Every task, every dependency, every priority lives in Taskwarrior.

**TaskFlow is the engine.** It reads TW state, drives execution through subagents,
manages waiting states when user input is needed, and updates TW when work completes.

TaskFlow does NOT duplicate TW's plan. It executes it.

## How it works

### 1. Flow identity

One managed TaskFlow for the stabilization effort:
```
controllerId: "osmen/install-stabilization"
goal: "Execute TW dependency graph to stable single-source-of-truth state"
```

### 2. Step progression reads TW

Each TaskFlow step corresponds to a TW dependency tier.
The flow doesn't hardcode what to do — it queries TW:

```
currentStep logic:
  1. Query: task status:pending depends.none: +UNBLOCKED
     → These are the tasks with all dependencies satisfied
  2. Pick the highest-priority unblocked task
  3. Execute it (via subagent or direct action)
  4. Mark it done in TW: task <uuid> done
  5. TW's dependency engine unblocks the next tier
  6. Repeat until no pending tasks remain
```

This means the plan can be modified by editing TW at any time.
Add a task, change a dependency, reprioritize — TaskFlow adapts
because it re-reads TW state each step.

### 3. Waiting states

TaskFlow enters `waiting` when:
- A task has tag `+USER_ACTION` or `+USER_INPUT` → waiting on D
- A task requires browser access → waiting on D
- A subagent run is in progress → waiting on completion

```
waitJson examples:

{
  "kind": "user_input",
  "twUuid": "fa1a7b31-...",
  "question": "Calendar sync policy: read-only, bidirectional, or none?",
  "channel": "webchat"
}

{
  "kind": "subagent",
  "twUuid": "e9d3e070-...",
  "childSessionKey": "agent:coder:subagent:reconcile-download-stack",
  "task": "Reconcile download-stack runtime to quadlet/systemd"
}
```

### 4. stateJson tracks TW task completion

```json
{
  "completedTasks": ["<uuid1>", "<uuid2>"],
  "currentTwUuid": "<uuid of task being worked>",
  "blockedOnUser": [],
  "subagentRuns": {}
}
```

### 5. Child tasks = subagent runs

For each TW task that requires execution (not just a user action):
```
taskFlow.runTask({
  flowId: created.flowId,
  runtime: "subagent",
  childSessionKey: "agent:coder:subagent:<tw-uuid-short>",
  task: "<TW task description + annotations as context>",
  status: "running"
})
```

When the subagent completes:
```bash
task <uuid> done
task <uuid> annotate "COMPLETED 2026-04-18 by subagent <session-key>"
```

Then TaskFlow resumes, queries TW for the next unblocked task, and continues.

### 6. The execution loop

```
┌─────────────────────────────────────────┐
│         TaskFlow Execution Loop         │
│                                         │
│  1. Query TW: pending + unblocked       │
│  2. If none → finish flow               │
│  3. If +USER_ACTION → setWaiting()      │
│  4. If +USER_INPUT → setWaiting()       │
│  5. Otherwise → runTask() via subagent  │
│  6. On completion → task <uuid> done    │
│  7. Go to 1                             │
│                                         │
└─────────────────────────────────────────┘
```

### 7. TW tags that TaskFlow understands

| Tag | Meaning for TaskFlow |
|-----|---------------------|
| `+USER_ACTION` | Requires D to do something physical (browser login, send message) |
| `+USER_INPUT` | Requires D to make a decision |
| `+fix_needed` | Agent-executable — spawn subagent |
| `+quadlet` | Agent-executable — involves quadlet file editing |
| `+phase0` through `+phase5` | Phase tags for reporting/grouping (not for ordering — ordering comes from depends:) |
| `+verify` | Agent-executable — run checks and report |
| `+cleanup` | Agent-executable — file/config cleanup |

### 8. How TW naturally creates the phase ordering

With the depends: chains wired by tw-stabilization-plan.sh:

```
UNBLOCKED FIRST (Phase 0):
  Merge conflicts         (no deps)
  ReadOnly fix            (no deps)
  Pin images              (no deps)
  PUID/PGID               (no deps)
  Duplicate HealthCmd     (no deps)
  Recover daily notes     (no deps)
  Postgres/redis verify   (no deps)

UNBLOCKED AFTER PHASE 0 (Phase 1):
  Download-stack reconcile (depends: merge-conflicts, readonly, pin-images, pg-redis-verify)

UNBLOCKED AFTER PHASE 1 (Phase 2+3, parallel):
  SAB wizard fix          (depends: download-stack)
  qBit auth recovery      (depends: download-stack)
  FlareSolverr routing    (depends: download-stack)

UNBLOCKED AFTER PHASE 2+3 (Phase 4):
  Prowlarr search test    (depends: SAB wizard + qBit auth)

UNBLOCKED AFTER PHASE 4 (Phase 5):
  Cron cleanup            (depends: Prowlarr)
  Prowlarr add indexers   (depends: Prowlarr)
  Prowlarr app sync       (depends: Prowlarr)
  Mylar3 indexer          (depends: Prowlarr)
  Bazarr verify           (depends: Prowlarr)

UNBLOCKED AFTER PROWLARR APP SYNC:
  Lidarr root folder      (depends: Prowlarr app sync)
  Readarr root folder     (depends: Prowlarr app sync)

ALWAYS AVAILABLE (no stabilization deps):
  P10.6-P10.9 bridge tests (+USER_ACTION)
  P16.4 Nextcloud admin   (+USER_ACTION)
  P17.5 Calendar policy   (+USER_INPUT)
  P14.5 PKM restore       (deferred)
  P8.9/P8.11 inference    (manual launch window)
  P20.4/P20.5 gaming      (low priority)
  P23.* dashboard          (internal deps only)
  roadmap.acp/*            (backlog)
  roadmap.devx/*           (backlog)
```

TW's own dependency engine produces this ordering.
TaskFlow just walks it.

## Implementation

The TaskFlow flow will be created when D says "go".
It will:
1. Create a managed flow via `api.runtime.tasks.flow`
2. Query TW for the first unblocked batch
3. Spawn subagents for Phase 0 tasks (parallel, they have no inter-deps)
4. As each completes, mark done in TW
5. When Phase 0 is clear, TW unblocks Phase 1
6. Continue until stable

The flow can be inspected at any time via `getTaskSummary(flowId)`.
It can be paused via `setWaiting()` and resumed via `resume()`.
It can be cancelled via `requestCancel()`.

## What this means for D

- Want to reprioritize? `task <uuid> modify priority:H` — TaskFlow picks it up next loop.
- Want to add a task? `task add ... depends:<uuid>` — it enters the graph naturally.
- Want to skip something? `task <uuid> done` — dependents unblock.
- Want to pause everything? TaskFlow `requestCancel()` — TW state is preserved.

TW is the bible. TaskFlow reads it.
