# Active Context

**Current branch**: install/fresh-setup-20260407
**Session**: 2026-04-14 — multi-agent architecture design complete

Immediate work: Build `core/orchestration/` subsystem. Eight modules defined in
the codex spec and this session's handoff report. Start with `registry.py` and
`ledger.py` (data models + PostgreSQL tables), then `session.py` (policy epoch
tracking), then `discord_adapter.py` (transport).

The merged architecture (manifesto insight + codex engineering + security
critique) is documented in:

- `docs/session-logs/2026-04-14/2026-04-14_234500_handoff.md`
- `roundtable/AGENT-DEPARTMENTS-MANIFESTO.md`
- `/home/dwill/Downloads/temp/Integrate_os/agent discussion/codex_.txt.md`

Key pivot from the critique: reject "markdown only" for shared state, reject
prompt-based urgency enforcement, disable Message Content Intent for execution
bots, implement identity allowlists.

Three build directives for next agent:

1. Memory: ACID-compliant write layer over PostgreSQL, markdown as generated view
2. Inference: Four-tier backend routing (swarm → worker → gpu → cloud)
3. Communication: Secure Discord adapter with mechanical anti-storm controls

## Resource Organization

Post-first-install resource audit completed. 25 Taskwarrior tasks in
`osmen.audit` project (AUDIT-001 through AUDIT-025). Full inventory at
`docs/POST_INSTALL_RESOURCE_ORGANIZATION.md`.

Critical consolidations identified:

- Dual skill dirs (~/.config/opencode/skill/ vs ~/.claude/skills/) — 95% duplicated
- Dual agent dirs (~/.config/opencode/agent/ vs ~/.claude/agents/) — identical
- Triple PIPELINE_CONNECTIONS.instructions.md in config/, core/, scripts/
- Codex spec stuck in ~/Downloads — needs copying to docs/specs/
- 12 temp_1st_install files from April install still in repo root
- OpenClaw config has 4 stale backup copies
- ChromaStore (store.py, lateral.py) should be deprecated for MemoryHub
- vault/ directory is an empty scaffold — wire it or remove it
