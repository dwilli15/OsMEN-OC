# Handoff Plan — Retire Opus/GPT Roster, Stand Up GLM-Only Final-Sweep Team
**Date:** 2026-04-18  
**Audience:** OpenClaw `main` (current Opus 4.6) — execute this plan, then hand control to the new GLM team.  
**Author:** Copilot (planning only; no execution performed)  
**Source data:** [osmen-state-of-play-2026-04-18.md](osmen-state-of-play-2026-04-18.md), [handoff-data/](handoff-data/), [openclaw-protocols.md](handoff-data/openclaw-protocols.md)

---

## 0. Why this handoff

- Opus/GPT roster is burning ~$33.60 / 72h on the disabled `heckler-reviewer-300s` cron alone; full main-agent operation is materially more.
- GLM endpoints (Z.AI Coding API) are already wired and proven via the `basic` agent (`zai/glm-4.7-flash`).
- Remaining install/config work is **mostly mechanical**: 67 TW tasks, 17 known issues, 8 D-blocked items. Top reasoning is needed only for ~5 design calls — well within GLM 5.1 range.
- Goal: finish the OsMEN-OC install sweep on a sustainable model budget, and prove the two-plane architecture works end-to-end on local-first GLM.

---

## 1. Phase A — Debrief & Close Existing Roster

Execute in this order. Each agent gets a final structured debrief written to `openclaw/memory/agent-debriefs/<agent-id>-2026-04-18.md` **before** disabling.

### A.1 Debrief template (apply to every agent below)
For each agent, the outgoing instance must produce a single markdown file with these sections:
1. **Scope owned** — what this agent was responsible for
2. **Work completed** — concrete artifacts (commits, files, services), with links
3. **Work in flight** — anything started but not finished, with current state and next step
4. **Open questions / unresolved decisions** — must include who can decide
5. **Lessons learned** — what to keep doing / stop doing in the GLM team
6. **Handoff target** — which new GLM agent inherits this scope (see §2)
7. **Artifacts to preserve** — paths under `openclaw/<agent-id>/` worth archiving

Save to: `openclaw/memory/agent-debriefs/<agent-id>-2026-04-18.md`

### A.2 Roster to retire (in order)

| Order | Agent | Current model | Action | Notes |
|---|---|---|---|---|
| 1 | `reviewer` | gpt-5.4 | Debrief → disable | Lowest risk, no in-flight writes |
| 2 | `researcher` | gpt-5.4 | Debrief → disable | Read-only, dump open research threads |
| 3 | `auditor` | gpt-5.4 | Debrief → disable | **Export full audit trail**: `audit-2026-04-18-72h.md` + any unmerged findings |
| 4 | `coder` | gpt-5.4 | Debrief → disable | **Critical**: capture 3 uncommitted changes + 5 unpushed commits state before close |
| 5 | `main` | claude-opus-4.6 | Debrief → demote to passive last | Owns Telegram/Discord/webchat — replaced last so user channel never goes dark |
| 6 | `basic` | zai/glm-4.7-flash | **Keep as-is** | Already GLM; fold into new team as `quick` |

### A.3 Pre-close checklist (before disabling any agent)
- [ ] All scratch files in `openclaw/<agent-id>/` committed or explicitly discarded
- [ ] Any open MCP sessions / browser tabs / canvases closed
- [ ] No active cron job references the agent (`~/.openclaw/cron/jobs.json`)
- [ ] Debrief md exists and is readable
- [ ] State-of-play doc updated to reflect the closure

### A.4 Disable mechanism
Per [openclaw-protocols.md §1](handoff-data/openclaw-protocols.md):
```jsonc
// ~/.openclaw/openclaw.json → agents.list[n]
{ "id": "reviewer", "enabled": false, "retired_at": "2026-04-18", "successor": "gamma" }
```
Then: `openclaw gateway restart` after the **full batch** (not per-agent — minimizes restart churn).

---

## 2. Phase B — Stand Up GLM-Only Team

### B.1 Team composition

| New ID | Model | Tier | Inherits from | Primary scope |
|---|---|---|---|---|
| `alpha` | `zai/glm-5.1` | top | `main` (channels) + design calls | User-facing channel ingress (Telegram/Discord/webchat); top-of-stack reasoning; final-call decisions; approval-gate medium+ adjudication |
| `beta` | `zai/glm-5-turbo` | top-fast | `coder` | Code writes, refactors, container builds, quadlet edits, git commits. Owns the install sweep work bucket. |
| `gamma` | `zai/glm-4.7-flash` | mid | `auditor` + `researcher` | Read-only verification, log scrubbing, doc lookup, RAG queries, install audit re-runs |
| `delta` | `zai/glm-4.7-flashx` | fast | `reviewer` + `basic` | Cheap PR/diff review, formatting checks, TW task hygiene, status pings |

Rationale:
- **4 agents, not 5** — `auditor`+`researcher` collapse to one read-only role (`gamma`) since both used the same model and overlapped heavily. Fewer agents = simpler cron, lower drift.
- `basic` is folded into `delta` (same effective model class; one role is enough).
- `alpha` keeps the channel sockets so Telegram/Discord stay live during the cutover.

### B.2 OpenClaw config edits (`~/.openclaw/openclaw.json`)

```jsonc
"agents.list": [
  { "id": "alpha", "model": "zai/glm-5.1",        "tools": "full",  "skills": ["channels","approval","decision"], "identity": "openclaw/alpha/IDENTITY.md" },
  { "id": "beta",  "model": "zai/glm-5-turbo",    "tools": "full",  "skills": ["coder","quadlet","git"],          "identity": "openclaw/beta/IDENTITY.md" },
  { "id": "gamma", "model": "zai/glm-4.7-flash",  "tools": "read",  "skills": ["audit","research","rag"],         "identity": "openclaw/gamma/IDENTITY.md" },
  { "id": "delta", "model": "zai/glm-4.7-flashx", "tools": "limited","skills": ["review","tw-hygiene","status"],  "identity": "openclaw/delta/IDENTITY.md" }
]
```

### B.3 Workspace seeding
For each new agent, create `openclaw/<id>/` with:
- `IDENTITY.md` — name, model, scope, do-not-touch list, escalation path to `alpha`
- `USER.md` — copy of operator preferences (D's working style, approval thresholds)
- `AGENTS.md` — pointer to OsMEN-OC/AGENTS.md and this handoff plan
- `MEMORY.md` — empty seed; agent fills as it works

### B.4 Auth & routing verification (must pass before first task)
- [ ] `auth.profiles.zai` token valid (test: `openclaw auth test zai`)
- [ ] `https://api.z.ai/api/coding/paas/v4` reachable from host
- [ ] Rate-limit handler (error 1302 → 2 min backoff → auto-downgrade) confirmed in `core/approval/gate.py`
- [ ] Env shim exports updated in [scripts/appdrawer/start-claude-osmen.sh](../../scripts/appdrawer/start-claude-osmen.sh#L960):
  ```bash
  export ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5.1"
  export ANTHROPIC_DEFAULT_SONNET_MODEL="glm-4.7-flash"
  export ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-4.7-flashx"
  ```
- [ ] `openclaw gateway restart` clean (no agent-init errors in journal)

### B.5 Smoke test (gate before Phase C)
Run **one low-risk task per new agent**, in this order:
1. `delta`: TW hygiene — `task list project:osmen.maint` and post a count to status channel
2. `gamma`: re-run `audit-2026-04-18-72h` against current state, diff against the saved report
3. `beta`: pick the smallest TW task tagged `+low-risk`, complete + commit
4. `alpha`: send a manual ping to D via Telegram bridge, await ack

If any smoke step fails → **halt, do not proceed to Phase C**. Roll back affected agent's model to `zai/glm-4.7-flash` (known-good) and report.

---

## 3. Phase C — Final Install/Config Sweep (the work the new team owns)

Buckets ranked by D-impact and dependency order. Each bucket has an owner agent.

### C.1 Critical security (owner: `beta`, verify: `gamma`) — DO FIRST
| TW | Item | Blocker |
|---|---|---|
| T0.3 | UFW firewall enable | D approval (sudo) |
| — | qBittorrent 5.1.0 auth broken | None — `beta` to patch container env |
| — | Prowlarr hardcoded indexer IPs | None — `beta` to template via env |
| — | `AGE-SECRET-KEY` committed to git | **STOP-THE-LINE**: rotate, scrub history, force-push (D approval required) |

### C.2 Container stabilization (owner: `beta`)
- Plex + Kometa restart loop — root-cause via journal, fix quadlet
- 9 containers ReadOnly without Tmpfs — add tmpfs mounts per [quadlet-files.instructions.md](../../.github/instructions/quadlet-files.instructions.md)
- Komga 112% CPU — investigate library scan settings
- chromadb-compact timer broken — fix `OnCalendar=` syntax

### C.3 Bridge / comms (owner: `alpha`, blocker: D)
- P10.6–P10.9: live Telegram + Discord round-trip tests (D must send messages)
- Approval flow end-to-end: `beta` proposes → `alpha` routes to D → D acks → `beta` executes

### C.4 Media pipeline (owner: `gamma` audit → `beta` fix)
- 70 corrupt files (64 CBR, 3 PDF, 2 CBZ) — `gamma` produces fix list, `beta` runs repair
- Library org pass — `beta` (after manga fixes complete)
- 125 GB volume cleanup (T6.2) — D approval required

### C.5 Monitoring / dashboard (owner: `beta`, low priority)
- P23.1–P23.8 Homepage widget chain — 8 sequential tasks, all L priority

### C.6 ACP / external agent ingress (owner: `beta`)
- 9 tasks now unblocked per P19 — VS Code, Claude Code, OpenCode, OpenClaw relay endpoints
- Each ingress point gets a smoke test by `gamma` before marking done

### C.7 Calendar / PKM / decisions (owner: `alpha`, blocker: D)
- P17.5 calendar sync policy decision (bidirectional vs read-only) — D
- P14 PKM restore — `beta` after policy locked

### C.8 Roadmap / future-work (defer)
- T7+ multi-agent Discord, backups, Pangolin, cloud drive — **out of scope for this sweep**, leave as L-priority TW tasks

---

## 4. D-Action Queue (must clear before Phase C completes)

| # | Item | Bucket | Asks |
|---|---|---|---|
| 1 | Approve UFW hardening (sudo) | C.1 | `task T0.3 done` after run |
| 2 | Approve `AGE-SECRET-KEY` rotation + git history rewrite | C.1 | Confirm "rotate + force-push" |
| 3 | Approve 125 GB volume cleanup | C.4 | Confirm target paths |
| 4 | Approve SABnzbd target drive (T6.3) | C.4 | Drive selection |
| 5 | Send Telegram test message | C.3 | Triggers P10.6 |
| 6 | Send Discord mention | C.3 | Triggers P10.7 |
| 7 | Acknowledge approval flow test | C.3 | P10.8–P10.9 |
| 8 | Calendar sync policy decision | C.7 | P17.5 |

---

## 5. Cron / Cost Guardrails

After cutover, `~/.openclaw/cron/jobs.json` should contain **only**:
- `delta-tw-hygiene` — every 30 min, `task list +PENDING limit:5` posted to status
- `gamma-state-of-play-refresh` — daily 06:00, regenerate state-of-play doc

**Do not re-enable**:
- `heckler-reviewer-300s` (was burning $33.60/72h)
- `subagent-nudge`

Hard cost ceiling: alert if 24h Z.AI spend > $5. Set in approval gate.

---

## 6. Rollback Plan

If GLM team fails smoke (B.5) or first 24h shows degraded output:
1. Re-enable `main` agent with model rolled back to `claude-opus-4.6`
2. Disable `alpha` (keep workspace for forensics)
3. Leave `beta`/`gamma`/`delta` enabled but `tools: "read"` only
4. Post incident note to `openclaw/memory/incidents/` and ping D

Rollback should take < 5 min: it's two JSON edits + one gateway restart.

---

## 7. Success Criteria (close-out)

This handoff is "done" when:
- [ ] All 5 Opus/GPT agents disabled, debriefs archived
- [ ] 4 GLM agents pass B.5 smoke
- [ ] All C.1 critical-security items closed
- [ ] All 8 D-action items resolved
- [ ] State-of-play doc regenerated and pending TW count ≤ 30
- [ ] 7-day cost trail shows < $50 total Z.AI spend
- [ ] One full week with zero gateway restarts triggered by agent failure

---

## 8. Open questions for D before Phase A starts

1. Keep `main` agent ID as `main` and just swap model, or fully retire it and use `alpha` as the new primary? (Plan assumes the latter — cleaner audit trail.)
2. Confirm channel ownership stays in OpenClaw (not migrated to OsMEN-OC bridge yet).
3. Approve cost ceiling at $5/24h, or different threshold?
4. Any agent in the current roster you want preserved verbatim (e.g. `auditor` for the install audit re-runs)?

---

**Next concrete action for OpenClaw `main`:** read this file, answer §8, then begin Phase A.1 debriefs starting with `reviewer`.
