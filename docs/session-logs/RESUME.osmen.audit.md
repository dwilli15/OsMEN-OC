# Resume Lane — osmen.audit

**Resume ID**: `resume.osmen.audit.resource-consolidation.2026-04-14`
**Resume Lane**: `osmen.audit::resource-consolidation`
**Pointer Role**: `parallel_execution`
**Last handoff / dispatch**: [install-audit-dispatch.md](/home/dwill/dev/OsMEN-OC/openclaw/state/install-audit-dispatch.md)
**Taskwarrior query**: `task project:osmen.audit list`

## Scope

Resource consolidation, stale-file cleanup, spec import, MemoryHub follow-through, and repo hygiene work discovered during the audit pass.

## Repo Reality

- this lane is real and already task-shaped
- it is not the default critical path while P19 is still unbuilt
- several audit tasks are cleanup/consolidation work, not feature delivery

## Entry Guidance

1. Use the audit dispatch for evidence standards.
2. Treat this lane as verification and consolidation, not as a place to freestyle architecture.
3. Prefer tasks that reduce repo confusion for future agents: spec placement, duplicate path cleanup, config authority, MemoryHub follow-through.

## Good Starting Areas

- copy/import canonical specs into repo-owned locations
- clarify authority between duplicated config/skill/agent surfaces
- wire durable memory surfaces into MemoryHub instead of leaving them as orphan markdown

## Blockers

- some audit tasks depend on decisions made while building P19
