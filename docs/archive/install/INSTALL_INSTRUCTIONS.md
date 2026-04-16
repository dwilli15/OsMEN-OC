# First Install Instructions — Session-Specific

These instructions apply ONLY during the first install of OsMEN-OC.
They are scoped to the `install/fresh-setup-20260407` branch and the
`temp_1st_install/` ephemeral directory.

## Workflow Rules

1. **No blind installs** — Every `apt-get install`, `pip install`, `npm install`,
   or `pkexec` command MUST be presented to the user and approved before execution.
2. **Pause at phase boundaries** — Each phase ends with a verification step.
   Do not advance to the next phase until the user confirms.
3. **Log everything** — Append significant command outputs and decisions to
   `temp_1st_install/install.log` for traceability.
4. **Python version** — System is 3.14.3; project Makefile enforces 3.13.
   Resolve before creating .venv (install python3.13 or patch Makefile).
5. **Secrets** — Never generate, store, or display secrets without user
   direction. Podman secrets are created interactively.
6. **Rollback awareness** — Before any system change, note the rollback
   path in the log (e.g., "can undo with `apt-get remove`").
7. **Commit discipline** — Commit logical units on the install branch.
   First commit: git identity + pkexec patch.
8. **temp_1st_install/** — Ephemeral. Must be in `.gitignore`. Will be
   deleted or archived after install is complete.
9. **Service startup order** — Secrets → Quadlets → PostgreSQL → Redis →
   ChromaDB → Migrations → Gateway.
10. **Extended services (Phase 11)** — Each sub-service is independent.
    Install one at a time, verify, then move to next. User chooses order.

## Phase Dependency Graph

```
Phase 0 (git identity)
  └→ Phase 1 (apt packages)
       └→ Phase 2 (userland tools: sops, openclaw)
       └→ Phase 3 (python .venv)
            └→ Phase 4 (rootless podman)
                 └→ Phase 5 (quadlet deployment)
                      └→ Phase 6 (secrets)
                           └→ Phase 7 (core services)
                                └→ Phase 8 (timers)
                                └→ Phase 9 (setup wizard)
                                     └→ Phase 10 (gateway validation)
                                          └→ Phase 11 (extended services)
                                               └→ Phase 12 (final verification)
```

## Files to Track

| File | Purpose |
|------|---------|
| `temp_1st_install/SESSION_INIT.md` | System state at session start |
| `temp_1st_install/INSTALL_INSTRUCTIONS.md` | This file |
| `temp_1st_install/INSTALL_PLAN.md` | Detailed multi-phase checklist |
| `temp_1st_install/install.log` | Running log of commands and outputs |
| `temp_1st_install/decisions.md` | User decisions and rationale |
