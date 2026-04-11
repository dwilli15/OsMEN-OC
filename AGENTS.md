# OsMEN-OC Agent Context

## Project Identity

OsMEN-OC is a Python 3.13 agent orchestration platform for Ubuntu 26.04 LTS.
This repo contains the execution engine; OpenClaw (Node.js, `npm install -g openclaw`) is the control plane dependency.

## What This Repo Contains

| Layer        | Directory     | Purpose                                                       |
| ------------ | ------------- | ------------------------------------------------------------- |
| Core library | `core/`       | Shared Python package (config, models, bus, memory, DB pools) |
| Agents       | `agents/`     | YAML manifests + thin Python runners                          |
| Gateway      | `gateway/`    | FastAPI app (REST + MCP + WebSocket bridge)                   |
| Quadlets     | `quadlets/`   | Rootless Podman systemd unit files                            |
| Config       | `config/`     | YAML config, SOPS-encrypted secrets                           |
| Scripts      | `scripts/`    | bootstrap.sh, deploy.sh, maintenance cron                     |
| Tests        | `tests/`      | pytest suite, one test per module minimum                     |
| Migrations   | `migrations/` | Numbered SQL files (001*, 002*, ...)                          |

## Key Architectural Decisions

1. **Rootless Podman only** — no Docker, no docker-compose. All containers run as a rootless user via systemd Quadlets.
2. **Single Python package** — everything imports from `core.*`. No util/ grab-bags. No circular imports.
3. **Agent manifests are YAML** — agents are data (YAML), not code. Each manifest declares tools, risk level, model tier, schedule.
4. **MCP auto-registration** — gateway reads agent YAML manifests at startup and exposes their tools as MCP endpoints automatically.
5. **Event-driven** — Redis Streams EventBus with typed EventEnvelope. Components communicate via events, not direct calls.
6. **Three-tier memory** — Redis (working) → PostgreSQL+pgvector (structured) → ChromaDB (RAG). Promotion/decay between tiers.
7. **Approval gate** — four risk levels (low/medium/high/critical). medium+ requires human approval via OpenClaw.
8. **No abstractions for one-time ops** — no AbstractAgent, no BaseService. Concrete implementations only.

## Active Agents

| Agent               | Risk   | Schedule          | Purpose                                        |
| ------------------- | ------ | ----------------- | ---------------------------------------------- |
| daily_brief         | low    | cron 07:00        | AM/PM check-in, daily briefing                 |
| knowledge_librarian | low    | event-driven      | Web scraping, transcription, chunking          |
| media_organization  | medium | event-driven      | Plex transfers, VPN audit, download monitoring |
| boot_hardening      | high   | cron weekly       | UFW, fail2ban, LUKS, Secure Boot               |
| focus_guardrails    | low    | cron 09-22 hourly | ADHD focus management, break reminders         |
| taskwarrior_sync    | low    | cron \*/15        | Taskwarrior ↔ Google Calendar sync             |
| system_monitor      | medium | cron \*/5 + event | Hardware metrics, power/fan control, GPU routing, NPU status |
| research            | low    | event-driven      | Web research, RAG queries, fact-checking       |

## Communication

- OpenClaw → OsMEN-OC: WebSocket at `ws://127.0.0.1:18789`
- Internal: Redis Streams (channel prefix `osmen.`)
- External: Tailscale mesh (no port forwarding)
