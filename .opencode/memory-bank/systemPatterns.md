# System Patterns

## Architecture

```
Discord ←→ Bot Identities ←→ Transport Adapters
     ←→ OsMEN Orchestration Core
     ←→ Redis Event Bus + Approval Gate + PostgreSQL Ledger
     ←→ Model Backends (cloud thinkers, local workers, NPU swarm)
```

## Existing Extension Points (on disk, verified)

- `core/events/envelope.py` — EventEnvelope, EventPriority, Redis stream derivation
- `core/bridge/protocol.py` — BridgeInboundMessage / BridgeOutboundMessage
- `core/bridge/ws_client.py` — Reconnecting WebSocket to OpenClaw
- `core/approval/gate.py` — Four-tier approval with human callback
- `core/pipelines/runner.py` — Topological sort, cron/events, retry, approval
- `core/gateway/mcp.py` — MCP tool auto-registration from manifests
- `core/memory/hub.py` — PostgreSQL + pgvector, documents, chunks, entries, hybrid search
- `config/compute-routing.yaml` — Rule-based routing (nvidia/vulkan/npu/cpu)

## Build Target: `core/orchestration/` (does not exist yet)

See `task project:osmen.install.p19 list` for the 23 tasks.

## Security Patterns

- 1:1 agent-to-bot identity. Agents process only @mentions or A2A protocol.
- Identity allowlists enforced at transport layer.
- Anti-storm controls are mechanical code, not prompts.
- Urgency/interruption is deterministic ACP, not LLM self-policing.
- Every moderation action yields a receipt.
