# Active Context

**Taskwarrior is the source of truth.** This file answers "what's going on?"
Run `task list project:osmen` to answer "what happens next?"

## Current State (2026-04-16)

- **Branch**: install/fresh-setup-20260407
- **HEAD**: c31a44e — fix(gateway): podman-only runtime + vision MCP handler wiring
- **TW**: 119 pending / 251 completed across 14 install sub-projects (67% complete)
- **Tests**: 671 passed, 0 failed (as of 2026-04-16)
- **Services**: 27 running, 1 failed (osmen-memory-maintenance.service), 0 inactive
- **Primary build lane**: P19 orchestration — 24 tasks pending, `core/orchestration/` doesn't exist yet
- **Blocked**: P22 verification (39 tasks) waiting on P19
- **User-blocked**: P10.6/P10.8 (Telegram/Discord creds), P13.8 (Plex libraries), P16.4 (Nextcloud admin), P17.5 (Calendar sync), P20.1 (Steam)

## Recent Session Work (2026-04-16)

- Gateway crash-loop fixed: Image resolution, port conflict (8080→18788), missing secret
- Vision MCP handlers wired: analyze_image, ocr_extract, generate_image callable via /mcp/tools/*/invoke
- NoopAuditTrail fallback added for containerized gateway without pg_pool
- Portall socket-proxy fixed: DOCKER_HOST env + User=1000:1000
- Podman-only: Dockerfile removed, Containerfile created
- Tasks 264 (gateway build) and 263 (portall socket-proxy) completed in TW
- Test suite grew from 664→671 (vision handler tests added)

## Phase Breakdown (Pending)

| Phase | Pending | Notes |
|-------|---------|-------|
| P22   | 39      | verification — blocked on P19 |
| P19   | 24      | orchestration spine — primary lane |
| P14m  | 13      | voice/model migration |
| P14   | 10      | memory hub completion |
| P10   | 7       | bridge — user-blocked (creds) |
| P21   | 6       | hardening/polish |
| P20   | 6       | desktop integration |
| P17   | 6       | taskwarrior ingress |
| P16   | 3       | infra (Nextcloud, hosts) |
| P13   | 2       | Plex ecosystem |
| P8    | 2       | inference routing |
| P18   | 1       | backup (NTFS mount) |
