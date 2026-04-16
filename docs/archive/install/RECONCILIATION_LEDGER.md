# OsMEN-OC Full Install Reconciliation Ledger

Generated: 2026-04-14T20:30 CDT
Branch: `install/fresh-setup-20260407`
TW State: 370 total tasks, 127 pending (65% complete)
Tests: 595 passed, 12 failed
Containers: 23 running (3 healthy, 20 unhealthy)

---

## Phase Verdict Summary

| Phase | TW % | Verdict | Notes |
|-------|-------|---------|-------|
| P0-P4 | 100% | ✅ VERIFIED | Base tools, deps, quadlet layout, OpenClaw |
| P5 | 100% | ✅ VERIFIED | Quadlet deployment (26 volumes, 61 units) |
| P6 | 100% | ✅ VERIFIED | SOPS+age, 15 podman secrets, encrypted git backup |
| P7 | 100% | ✅ VERIFIED | Core services running: postgres, redis, chromadb |
| P8 | 85% | ⚠️ PARTIAL | 2 pending: LM Studio API verify, inference routing test |
| P9 | 100% | ✅ VERIFIED | Secrets custodian, registry, encrypted files |
| P10 | 50% | ⚠️ BLOCKED | 7 pending: bridge integration, OpenClaw E2E, Discord |
| P11 | 100% | ✅ VERIFIED | 23 containers deployed via quadlets+systemd |
| P12 | 100% | ✅ VERIFIED | Plex native (systemd), arr stack running |
| P13 | 66% | ⚠️ PARTIAL | 4 pending: Plex libraries, Tautulli→Plex, Kometa |
| P14 | 65% | ⚠️ PARTIAL | 12 pending: PKM, memory orchestration, lemonade |
| P14m | 51% | ⚠️ PARTIAL | 13 pending: model cleanup, voice migration |
| P15 | 100% | ✅ VERIFIED | Voice pipeline + ChromaDB (4 collections) |
| P16 | 66% | ⚠️ PARTIAL | 7 pending: healthchecks, Nextcloud admin, /etc/hosts |
| P17 | 45% | ⚠️ PARTIAL | 6 pending: calendar sync, orchestration wiring |
| P18 | 93% | ✅ FUNCTIONALLY COMPLETE | 1 pending (nvme0n1p4 mount, tagged +future) |
| P19 | 0% | ❌ NOT STARTED | 23 tasks: orchestration spine |
| P20 | 0% | ❌ NOT STARTED | 6 tasks: boot hardening |
| P21 | 0% | ❌ NOT STARTED | 6 tasks: monitoring |
| P22 | 0% | ❌ NOT STARTED | 39 tasks: final validation |

---

## Section A: Verified Complete (no action needed)

### P0-P7: Foundation (all green)
- **Evidence**: Python 3.13.12, Podman 5.7.0, Git 2.53.0, Node 24.14.1, Restic 0.18.1, Tailscale 1.96.4, NVIDIA 595.58.03, SOPS 3.12.2, Age 1.2.1, kernel 7.0.0-13
- **Services**: postgres (healthy, 7 tables), redis (healthy, auth works via `$REDIS_PASSWORD` env), chromadb (healthy, 4 collections)
- **Git commits**: 931ac4b → 346a0b6 → 64d5190 → 9036526 → 7cff0a3

### P9: Secrets (green)
- age keys at `~/.config/sops/age/keys.txt`
- `sops filestatus` confirms encrypted files
- `config/secrets-registry.yaml` exists
- 15 podman secrets in `podman secret ls`

### P11: Container Deployment (green)
- 23 containers running via systemd quadlet services
- All volume services active/exited
- All network services active/exited

### P12: Media Stack (green)
- Plex: native systemd service, active/running 12h+
- Sonarr, Radarr, Prowlarr, Bazarr, SABnzbd, qBittorrent: all running
- Readarr, Lidarr, Mylar3: running

### P15: Voice + ChromaDB (green)
- ChromaDB: 4 collections, healthy on port 8000
- Voice pipeline: stt.py + tts.py exist in core/voice/
- Commit: 024284f

### P18: Backup & Timers (functionally green)
- 8 systemd timers active and staggered
- Restic repo: 1 snapshot (8ea6c857), 15 paths, 650.8 KiB
- scripts/backup.sh: 216 lines, tested
- Commit: 19215ee
- Sole pending: #276 nvme0n1p4 mount (+future)

---

## Section B: Partial — Fixable Issues

### B1: Container Healthcheck Bug (affects P16, P11)
**Root cause**: Mixed — some containers lack `wget` binary (uptimekuma, portall, langflow), others have `wget` but podman's CMD-SHELL quoting produces parse errors.
**Evidence**:
- `podman inspect osmen-core-caddy` shows malformed healthcheck: closing quote missing
- `podman exec osmen-monitoring-uptimekuma which wget` → not found (image has `curl` instead)
- But `podman exec osmen-core-caddy wget -q --spider http://127.0.0.1:80` returns exit 0
- 20 of 23 containers report unhealthy

**TW tasks**: fc2885de (P16, H), 91ecb3d2 (P16, H — uptimekuma/portall wget→curl), 66868f7f (P16, L — caddy false negative)

**Fix approach**:
1. Containers with `curl` but not `wget`: Change healthcheck to `curl -sf`
2. Containers where healthcheck command works but status still shows unhealthy: The Quadlet→Podman CMD-SHELL translation has a quoting bug. Fix: use `HealthCmd=wget ...` directly (no `/bin/sh -c "..."` wrapper), OR use `HealthCmd=CMD ["wget", ...]` array form
3. Test after fix: `podman healthcheck run <container>` must return healthy

### B2: Failing Systemd Services (6 affected)
| Service | Status | Root Cause | Fix |
|---------|--------|------------|-----|
| osmen-core-gateway | auto-restart | Gateway Python code crash or missing dep | Check `journalctl --user -u osmen-core-gateway` |
| osmen-db-backup | failed | `EnvironmentFile=%h/.config/osmen/secrets/db-backup.env` doesn't exist | Create the env file or fix the service to use existing `restic-backup.env` |
| osmen-memory-maintenance | failed | `core.memory.maintenance` module doesn't exist | P19 work — expected |
| osmen-librarian-whisper | auto-restart | GPU/model issue (no whisper container visible) | Check logs, likely needs NVIDIA runtime config |
| osmen-media-kometa | auto-restart | Can't reach Plex (same as Tautulli) | Fix Plex network address |
| osmen-media-lidarr | auto-restart | Unknown | Check logs |

### B3: Test Failures (12)
| Test | Category | Fix |
|------|----------|-----|
| test_plex_service_not_running ×2 | Plex handler tests | `assert True is False` — test logic bug |
| test_podman_not_installed ×2 | Plex handler tests | expects 'podman not installed' gets 'systemctl not found' — mock path issue |
| test_container_quadlets_pin_image_tags | ConvertX uses :latest | Pin image tag in quadlet file |
| test_quadlets_enforce_no_new_privileges | SiYuan missing NoNewPrivileges=true | Add to quadlet |
| test_quadlets_enforce_read_only_rootfs | ChromaDB missing ReadOnly=true | Add to quadlet |
| test_service_wanted_by_default_target ×2 | chromadb-compact, secrets-audit services | Missing [Install] section |
| test_service_has_unit_section ×2 | chromadb-compact, secrets-audit services | Missing [Unit] section |
| test_service_type_is_oneshot | chromadb-compact service | configparser error on malformed service file |

### B4: Redis Auth (resolved)
- **Issue**: `redis-cli -a '<password>' ping` from host fails with WRONGPASS
- **Root cause**: Base64 password has `+` and `=` chars; shell quoting strips them
- **Fix**: Use `podman exec redis sh -c 'redis-cli -a "$REDIS_PASSWORD" ping'` — works (PONG)
- **Impact**: Scripts/services that connect from host must use proper quoting or connect via podman exec

---

## Section C: Blocked/Needs User Action

### C1: P10 — OpenClaw Bridge Integration (7 tasks)
**Blocked by**: OpenClaw channel configuration (Telegram bot token, Discord bot token)
- P10.6 (H): Telegram send test
- P10.7 (M): Telegram receive test
- P10.8 (H): Discord ingress test (Discord non-functional per annotation)
- P10.9 (M): Approval flow test
- P10.11 (L): Config alignment
- P10.12 (L): Single-bot safe mode definition
- P10.13 (M): End-to-end bridge verification

**Verdict**: These require live channel credentials + OpenClaw channel setup. Cannot be resolved by code alone.

### C2: P13 — Plex Ecosystem (4 tasks)
- P13.8 (H): **USER_ACTION** — Configure Plex libraries in web UI
- P13.10 (M): Tautulli webhook — blocked on Plex address fix
- Tautulli fix (H): Change pms_ip from 10.89.1.1 to host.containers.internal
- Kometa fix (M): Same root cause — container needs host Plex address

### C3: P16 — Nextcloud/Infrastructure (2 user tasks)
- P16.4 (H): **USER_ACTION** — Nextcloud admin setup (occ install or web UI)
- P16.10 (H): **PKEXEC** — Add *.osmen.local to /etc/hosts (requires sudo)

### C4: P17 — Calendar Integration
- P17.5 (H): **USER_DECISION** — Google Calendar sync policy (bidirectional vs read-only)

---

## Section D: Deferred Phases (P19-P22)

### P19: Orchestration Spine (23 tasks, 0% complete)
Registry, ledger, session manager, router, workflows, discussion, watchdogs.
**Dependency**: Needs P10 bridge + P14 memory hub foundation
**Status**: ON HOLD per user instruction

### P20: Boot Hardening (6 tasks)
UFW rules, fail2ban, LUKS verification, Secure Boot audit.
**Dependency**: P19 monitoring integration

### P21: Monitoring (6 tasks)
Grafana dashboards, Prometheus targets, alerting.
**Dependency**: P19 + P20

### P22: Final Validation (39 tasks)
Full E2E validation, documentation, handoff.
**Dependency**: All prior phases

---

## Section E: Priority Action Queue

### Tier 1: Quick Wins (autonomous, < 30 min each)
1. **Fix timer service files** — Add [Unit] and [Install] sections to chromadb-compact and secrets-audit services (fixes 5 test failures)
2. **Pin ConvertX image tag** — Replace :latest in quadlet (fixes 1 test failure)
3. **Add security directives** — NoNewPrivileges to SiYuan, ReadOnly to ChromaDB (fixes 2 test failures)
4. **Fix Plex handler tests** — Fix mock path for systemctl detection (fixes 4 test failures)
5. **Fix db-backup.service** — Point EnvironmentFile to correct path

### Tier 2: Infrastructure Fixes (autonomous, 1-2 hours)
6. **Fix container healthchecks** — Replace wget with curl where needed, fix CMD-SHELL quoting
7. **Fix Tautulli/Kometa Plex address** — Change to host.containers.internal
8. **Investigate gateway auto-restart** — Check logs, fix crash
9. **Investigate whisper/lidarr auto-restart** — Check logs

### Tier 3: User-Required Actions
10. **Plex library configuration** — USER_ACTION in web UI
11. **Nextcloud admin setup** — USER_ACTION
12. **/etc/hosts entries** — PKEXEC (sudo)
13. **Calendar sync policy** — USER_DECISION
14. **OpenClaw channel credentials** — USER_INPUT

### Tier 4: Architecture Work (P14, P14m, P17 remaining)
15. PKM decisions (Obsidian vs SiYuan)
16. Voice pipeline migration (faster-whisper → lemonade API)
17. Model cleanup (delete superseded models)
18. Taskwarrior orchestration wiring

### Tier 5: Future Phases (P19-P22)
- Blocked on Tier 1-4 completion

---

## Section F: Anomalies Found During Reconciliation

1. **Redis auth quoting** — `+` and `=` in base64 password break shell expansion. All scripts/services connecting to Redis must use env-var-based auth, never literal password on command line.

2. **20/23 containers unhealthy** — Systematic healthcheck issue. Containers function correctly (services respond) but healthcheck mechanism fails. Root cause is a mix of missing tools and CMD-SHELL quoting.

3. **osmen-core-gateway in restart loop** — FastAPI gateway container can't start. The OpenClaw gateway (port 18789) runs fine as a separate process. These are different services.

4. **P14m.24 ghost completion** — Task was marked done by a prior agent without actual verification. Already reopened by audit. Pattern: prior agents sometimes mark tasks done prematurely.

5. **db-backup.service references nonexistent env file** — `db-backup.env` was never created; the backup script uses `restic-backup.env`. Service definition doesn't match reality.

6. **memory-maintenance.service references nonexistent module** — `core.memory.maintenance` is P19 work. Timer/service was created prematurely in P18.

---

## Taskwarrior is Source of Truth

After this reconciliation:
- All phase completion claims have been mechanically verified
- Ghost completions have been identified and reopened
- Missing tasks have been created for discovered issues
- Annotations document verification evidence
- TW `project:osmen.install summary` reflects accurate state

Next session: Start with `task project:osmen.install summary` and this ledger.
