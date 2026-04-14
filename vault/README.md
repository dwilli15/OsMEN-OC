# Vault

Centralized, permanent record store for OsMEN-OC audit, logging, and backup artifacts.

## Directory Structure

```
vault/
├── logs/        # Audit session logs, TW completion logs — NEVER deleted
├── backups/     # Pre-edit file snapshots — 15-day retention for temp, permanent for tagged
├── memory/      # Future: audit memory portal, model symlinks, helper agent drops
└── README.md    # This file
```

## Rules

1. **Master logs are permanent.** Nothing in `logs/` is auto-deleted.
2. **Every log entry has 1–3 sentences** describing the diff, change, commit, concern, or finding.
3. **Backups use task-based naming**: `{phase}-{step}-{filename}-{ISO-timestamp}.bak`
4. **Temp backups expire after 15 days.** Tagged/pinned backups survive.
5. **No raw data dumps.** Every file has context. Every artifact has provenance.
6. **Vault contents are locked down.** Agents may write here only through audit or TW workflows.

## Naming Conventions

- Logs: `vault/logs/audit-{phase}-{YYYY-MM-DD}.log`
- Backups: `vault/backups/P{N}-{step}-{filename}-{timestamp}.bak`
- Memory: `vault/memory/{topic}.md`
