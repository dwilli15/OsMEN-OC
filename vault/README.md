# vault/ — Agent Audit & Memory Artifacts

## Structure
- `backups/` — Pre-edit snapshots from reviewer/auditor agents. Auto-cleanup after 15 days.
- `logs/` — Audit session logs. Permanent.
- `memory/` — Memory artifacts from agent sessions. Synced to MemoryHub via scripts/sync_memory_bank.py.

## Integration
- `vault/memory/` contents are ingested into MemoryHub (PostgreSQL + pgvector) via the memory pipeline.
- `vault/backups/` are auto-cleaned by the maintenance module (15-day retention).
- `vault/logs/` are permanent and can be recalled via MemoryHub.
