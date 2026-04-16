# Resume Lane — osmen.install::p19-orchestration

**Resume ID**: `resume.osmen.install.p19.orchestration.2026-04-14`
**Resume Lane**: `osmen.install::p19-orchestration`
**Pointer Role**: `primary_execution`
**Last handoff**: [2026-04-14_235950_handoff.md](2026-04-14/2026-04-14_235950_handoff.md)
**Taskwarrior query**: `task project:osmen.install.p19 list`

## Scope

Build the orchestration spine behind the existing gateway, event bus, bridge, manifests, and MemoryHub.

## Repo Reality

- `core/orchestration/` does not exist yet
- existing anchors are the gateway, Redis Streams bus, bridge protocol, approval gate, MemoryHub, and Taskwarrior queue/sync path
- transport surfaces are not the source of truth; typed workflow state must be

## Verified Preconditions

- the reconciliation ledger confirmed 12 failing tests, 20 unhealthy containers, and 6 failing user services before any new P19 code was written
- the next executable tranche is the Tier 1 stabilization set in `temp_1st_install/RECONCILIATION_LEDGER.md`
- do not treat these as architecture blockers, but do clear or explicitly defer them before expanding the orchestration surface

## Recommended Build Order

1. Stabilization gate from the reconciliation ledger: timer service definitions, quadlet hardening, Plex handler tests, backup env-path alignment
2. `P19.1` package skeleton
3. `P19.7` typed orchestration models
4. `P19.2`, `P19.3`, `P19.5` registry, ledger, session
5. `P19.4` migration SQL once the ledger shape is real
6. `P19.6` router over `config/compute-routing.yaml`
7. `P19.10b` and `P19.10c` bridge protocol and gateway wiring
8. `P19.8`, `P19.9`, `P19.10`, `P19.10a` workflow, discussion, watchdogs, adapter
9. `P19.10d`, `P19.10e`, `P19.11` memory bridge and generated views
10. `P19.12`, `P19.13` config/schema and policy docs
11. verification and commit tasks last

## Next 1-3 Actions

1. Execute or explicitly defer the Tier 1 stabilization tranche captured in the reconciliation ledger.
2. Start P19 by creating `core/orchestration/` and the typed model layer once that tranche is green.
3. Keep P19 grounded in the current repo interfaces, and treat P17 as dependent/support work rather than a substitute runtime.

## Blockers

- no architecture blocker on structure; this remains the current critical path after the stabilization tranche
- later verification tasks remain blocked until the spine exists
