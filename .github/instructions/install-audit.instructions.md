---
description: "Ground-truth verification of install phases against actual system state"
applyTo: "temp_1st_install/**"
---

# Install Audit Skill

When asked to "audit", "verify", "reality check", or "ground truth" an install phase,
use the install-audit skill at `.github/skills/install-audit/SKILL.md`.

## Quick Reference

- **Agent:** `@install-audit` — invoke from Copilot Chat
- **Skill:** `.github/skills/install-audit/SKILL.md` — full methodology (5-phase pipeline)
- **Dispatch prompt:** `openclaw/state/install-audit-dispatch.md` — self-contained prompt for OpenClaw
- **Vault:** `vault/` — unified record store (logs permanent, backups 15-day retention)

## Capabilities

- Full edit access to existing files (backup-before-edit to `vault/backups/`)
- Full read/run access — terminals, tests, services, git, TW
- Creates fix tasks in TW for discovered problems (never fixes bugs directly)
- No git commits — baseline verification only
- No file create/move/delete (except vault writes)

## Taskwarrior Integration

All audit findings are recorded as TW annotations (1-3 sentences each):
- `AUDIT CONFIRMED [timestamp]: {evidence + integration context}`
- `AUDIT REACTIVATED [timestamp]: {what failed + impact}`
- `AUDIT COMPLETED [timestamp]: {evidence + why it wasn't marked}`
- New fix tasks tagged `+audit_finding +fix_needed` with priority H/M/L

## When to Use

- After completing a phase, before moving to the next
- When resuming from a handoff (trust nothing from prior sessions)
- When the installer and the record disagree
- Periodically as a health check on the full install

## Future: Sr-Level Auditor

TW task 238 tracks the evolution to a sr-level auditor with fix, commit, regression, and CI capabilities.
