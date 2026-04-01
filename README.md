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
git clone git@github.com:dwilli15/OsMEN-OC.git
cd OsMEN-OC
scripts/bootstrap.sh
```

## License

Apache 2.0
