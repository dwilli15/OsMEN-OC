# OsMEN-OC

OsMEN-OC (OS Management and Engagement Network — OpenClaw edition) is a production-grade local-first agent orchestration platform for Ubuntu 26.04 LTS.

## Architecture

Two-plane design:

- **OpenClaw** (control plane, separate Node.js product) — handles user interaction via Telegram/Discord
- **OsMEN-OC** (execution engine, this repo) — pipeline execution, tool invocation, memory, all services

## Technology

- Python 3.13, FastAPI, LangGraph, asyncio
- Rootless Podman + systemd Quadlets (no Docker)
- PostgreSQL 17 + pgvector, Redis 7, ChromaDB
- SOPS + age for secrets, restic for backups
- Zhipu GLM-5 (primary LLM), Ollama + LM Studio (local inference)

## Quick Start

```bash
git clone https://github.com/OsMEN-OC/OsMEN-OC.git
cd OsMEN-OC
scripts/bootstrap.sh
```

## Contributing / Development

After cloning, the following commands must succeed on a fresh checkout:

```bash
# First-time setup (idempotent)
scripts/bootstrap.sh --skip-apt --skip-openclaw

# Validate the dev environment
make test       # pytest suite
make lint       # ruff code-style check
make typecheck  # mypy static analysis
```

All three `make` targets create and populate `.venv` automatically if it does not
exist, using `python -m pip` throughout (no bare `pip` executable assumed).

`scripts/bootstrap.sh --dry-run` echoes every command without executing it,
allowing you to audit the bootstrap sequence before running on a new machine.

See [docs/GITHUB_AGENT_OPERATIONS.md](docs/GITHUB_AGENT_OPERATIONS.md) for issue shaping rules, approval requirements, and merge order when working with the GitHub Copilot coding agent.

## License

Apache 2.0
