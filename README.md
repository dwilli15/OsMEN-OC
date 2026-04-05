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

## Database Configuration

OsMEN-OC stores the audit trail and pipeline state in PostgreSQL with pgvector.
Two options are supported:

### Option A — Self-hosted (default)

The default setup runs `osmen-core-postgres` (`pgvector/pgvector:pg17`) as a
rootless Podman container inside the `osmen-core.network` namespace.
Bootstrap starts it automatically. Export one variable before starting the gateway:

```bash
export DATABASE_URL="postgresql://osmen:<password>@127.0.0.1:5432/osmen"
```

### Option B — Supabase free tier

No local Postgres container needed. Create a free project at
[supabase.com](https://supabase.com) (pgvector is enabled by default), then
export **one** variable:

```bash
export SUPABASE_DB_URL="postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres"
```

The gateway automatically uses `SUPABASE_DB_URL` as a fallback when
`DATABASE_URL` is absent — no other code or config changes required.

> **Note**: Supabase free projects auto-pause after 7 days of inactivity.
> For always-on production use, keep the self-hosted Podman container (Option A).

## Quick Start

```bash
git clone git@github.com:dwilli15/OsMEN-OC.git
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
