# Project Brief

OsMEN-OC is a Python 3.13 agent orchestration platform for Ubuntu 26.04 LTS.
It runs on a Ryzen AI 9 365 / 64 GB / RTX 5070 8GB workstation with NPU, Vulkan,
CUDA, and CPU compute targets.

The repo is the execution engine. OpenClaw is the control surface.
PostgreSQL is the authoritative store. Markdown is the cognitive view.

**Taskwarrior is the execution ledger.** Run `task list project:osmen` for the backlog.

## Mandates

- Rootless Podman only.
- Agent manifests are YAML data, not code.
- MCP auto-registration from manifests at startup.
- Event-driven via Redis Streams with typed EventEnvelope.
- Four-tier approval gate.
- PostgreSQL writes, markdown as generated view.
- No framework lock-in. No monolithic super agent.
- No assumption that all agents are cloud models.
