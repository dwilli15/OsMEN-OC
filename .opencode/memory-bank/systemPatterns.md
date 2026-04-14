# System Patterns

## Architecture Layers

```
Discord Guild(s)  ←→  Bot Identities  ←→  Transport Adapters
       ←→  OsMEN Orchestration Core
       ←→  Redis Event Bus + Task Ledger + Markdown Memory + Approval Gate
       ←→  Model Backends (cloud thinkers, local workers, NPU swarm)
```

## Extension Points (existing, verified on disk)

- `core/events/envelope.py` — EventEnvelope with domain, category, payload,
  source, correlation_id, priority, Redis stream_key derivation.
- `core/bridge/protocol.py` — BridgeInboundMessage / BridgeOutboundMessage
  (Pydantic, currently minimal — type + correlation_id + payload dict).
- `core/bridge/ws_client.py` — Reconnecting WebSocket client to OpenClaw
  (exponential backoff, 89 lines, handles BridgeInboundMessage deserialization).
- `core/approval/gate.py` — ApprovalGate with four risk levels, runtime risk
  overrides, async human approval callback, timeout/deny on HIGH, indefinite
  block on CRITICAL.
- `core/pipelines/runner.py` — PipelineRunner with topological sort, cron and
  event-triggered execution, retry with backoff, approval gate integration.
- `core/gateway/mcp.py` — MCP tool registry, auto-registration from agent
  manifests.
- `core/memory/hub.py` — MemoryHub: PostgreSQL + pgvector, document/chunk
  storage, cosine similarity search, hybrid RRF search, structured agent memory
  entries with importance scoring and access counting.
- `core/memory/store.py` — ChromaStore: ChromaDB REST v1 client (legacy,
  still functional).
- `core/memory/lateral.py` — LateralBridge: cross-collection similarity search.
- `config/compute-routing.yaml` — Rule-based compute routing (nvidia, amd_vulkan,
  npu, cpu) with priority ordering, fallback chains, verified provider endpoints.

## Required New Subsystem: `core/orchestration/`

The codex spec defines these logical modules (not yet built):

- `registry.py` — Agent registry with identity, capabilities, backend profile,
  policy bundle, Discord account mapping.
- `session.py` — Session namespace management with policy epoch tracking and
  freshness preflight.
- `router.py` — Mode A / Mode B routing, speaker selection, turn management.
- `discussion.py` — Structured debate mechanics (claim, attack, repair, reframe,
  narrow, synthesize, handoff).
- `workflow.py` — WorkflowGraph with PipelineNode and DiscussionNode,
  status machine (submitted → triaged → scoped → decomposed → running →
  challenged → verifying → awaiting_human → approved → published → aborted).
- `watchdogs.py` — Storm detection, novelty gating, velocity gating, stale
  session detection, receipt verification.
- `ledger.py` — Workflow state, work items, claims, receipts, urgency scoring.
- `discord_adapter.py` — Lightweight Discord transport satisfying AgentTransport
  Protocol (ingest, send, cancel, refresh).

## Key Design Patterns

- Agent manifests are YAML — agents are data, not code.
- MCP auto-registration at gateway startup.
- Control plane (registry, sessions, policy, ledger, routing) is authoritative.
  Data plane (Discord messages, reactions, threads, artifacts) is view only.
- ACP-style bridge: session-oriented, bidirectional, explicit admission and
  receipt semantics.
- Urgency is computed from detectors, not vibes. Deterministic scoring
  (0-100) maps to UrgencyCategory → EventPriority.
- Interrupts are first-class events with authority hierarchy and mechanical
  effects (cancel generation, suppress reply, convert to private note).

## Security Patterns

- 1:1 agent-to-bot identity mapping at identity layer, 1:N at backend layer.
- Discord Message Content Intent disabled for execution-capable bots.
- Agents process only @mentions or secure A2A protocol messages.
- Identity allowlists (`allowFrom`) enforced at transport layer.
- No bot gets Discord Administrator permission.
- Urgency/interruption enforcement is deterministic ACP, not LLM self-policing.
- Every moderation or mutating action yields a receipt — claims without
  receipts are auto-invalidated.
