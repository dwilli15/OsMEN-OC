# Outline

1. Scope, assumptions, and non-goals.
2. Existing OsMEN-OC anchors that this design extends.
3. Baseline patterns: OpenClaw swarm, AutoGen, CrewAI, Agentic Dispatch lessons.
4. Recommended target architecture.
5. Runtime entities and configuration model.
6. Discord identity model and ACP-style bridge interfaces.
7. Workflow model: Mode A and Mode B.
8. Memory model: markdown-first shared cognition with structured indexing.
9. Urgency, interruption, escalation, and human oversight.
10. Swarm-on-NPU plus elite-agent hierarchy.
11. Deployment patterns and resource tradeoffs on Ryzen AI 9 365 / 64 GB / RTX 5070 8 GB.
12. Failure containment, enforcement, and observability.
13. Normative source anchors.

# Scope

## Objective

Integrate deep multi-agent orchestration into OsMEN-OC so that multiple AI agents, each with its own Discord bot identity, can co-occupy shared Discord servers/channels and operate in two modes:

- Mode A: cooperative team execution for research, strategy, planning, implementation guidance, and iterative refinement.
- Mode B: adversarial or critical discussion for debate, critique, idea dissection, stress testing, and brainstorming.

The design MUST be implementation-ready, MUST fit the current OsMEN-OC execution-engine architecture, and MUST not depend on a single framework.

## Non-goals

- No monolithic “super agent”.
- No vector database as the sole memory authority.
- No free-for-all bot chatter.
- No framework lock-in to OpenClaw, AutoGen, or CrewAI.
- No assumption that all agents are cloud models.
- No assumption that NPU runtimes available on Windows are natively available on Ubuntu without an adapter.

## Assumptions

- OsMEN-OC remains Python-first and event-driven.
- Discord is a control surface and social substrate, not the authoritative state store.
- Markdown files remain the primary shared cognitive surface for cross-agent continuity.
- PostgreSQL/Redis already present in OsMEN-OC remain the authoritative structured stores.
- Existing OsMEN-OC primitives in [core/events/envelope.py](/home/dwill/dev/OsMEN-OC/core/events/envelope.py:1), [core/bridge/protocol.py](/home/dwill/dev/OsMEN-OC/core/bridge/protocol.py:1), [core/approval/gate.py](/home/dwill/dev/OsMEN-OC/core/approval/gate.py:1), [core/pipelines/runner.py](/home/dwill/dev/OsMEN-OC/core/pipelines/runner.py:1), [core/gateway/mcp.py](/home/dwill/dev/OsMEN-OC/core/gateway/mcp.py:1), and [config/compute-routing.yaml](/home/dwill/dev/OsMEN-OC/config/compute-routing.yaml:1) are extended, not replaced.

# Existing OsMEN Anchors

## Architectural fit

OsMEN-OC already has the right substrate.

- `EventEnvelope` already gives `domain`, `category`, `payload`, `source`, `correlation_id`, and `priority`.
- `BridgeInboundMessage` and `BridgeOutboundMessage` already define a typed bridge shell.
- `ApprovalGate` already defines four risk levels and a human approval path.
- `PipelineRunner` already provides cron and event-triggered execution.
- agent manifests are already YAML and already map tools plus model tiers.
- compute-routing already expresses `nvidia`, `amd_vulkan`, `npu`, and `cpu` targets.

The orchestration layer SHOULD therefore be added as a new logical subsystem, not a separate platform.

## Required extension points

OsMEN-OC SHOULD add an orchestration layer with the following logical modules:

- `core/orchestration/registry.py`
- `core/orchestration/session.py`
- `core/orchestration/router.py`
- `core/orchestration/discussion.py`
- `core/orchestration/workflow.py`
- `core/orchestration/watchdogs.py`
- `core/orchestration/ledger.py`
- `core/orchestration/discord_adapter.py`

This is a spec name map, not an implementation plan.

## Manifest extension model

Current agent manifests SHOULD be extended with orchestration, backend, Discord, and memory fields.

```yaml
agent_id: naysayer
name: Naysayer
model_tier: local-small

capabilities:
  - critique
  - contradiction-detection
  - evidence-check

description: Critical reviewer for shared-thread work.

orchestration:
  default_mode: debate
  roles: [critic, verifier]
  public_reply_policy: summoned_or_triggered
  max_public_turns_per_workflow: 2
  novelty_gate: strict
  can_interrupt_for:
    - contradiction
    - safety
    - stale_state
  must_verify_claim_types:
    - factual
    - architectural
    - policy

backend:
  provider: fastflowlm_compatible
  model: qwen3-0.6b-FLM
  supports_tools: false
  supports_cancel: true
  latency_class: low
  cost_class: local

discord:
  bot_account_id: naysayer
  presence_template: "reviewing"
  allowed_channels:
    - war_room
    - debate_pit
  permissions_profile: reviewer

memory:
  strategy: markdown_plus_ledger
  read_surfaces:
    - task_brief
    - debate_log
    - decision_log
  write_surfaces:
    - critique_cards
    - receipts
```

# Baseline Patterns

## OpenClaw swarm pattern

The OpenClaw pattern contributes five useful ideas.

- One bot identity per agent.
- Shared Discord channels as coordination substrate.
- ACP sessions bound to channels or threads.
- markdown-based shared memory and workspace-local policy.
- cron/heartbeat metabolism and approval flows.

Strengths:

- socially legible identities.
- thread binding and persistent conversation routing.
- native Discord approvals and presence.
- excellent human-in-the-loop ergonomics.

Weaknesses:

- conversation-first systems need explicit anti-storm control.
- policy-on-disk is not policy-in-context.
- queue behavior can create simultaneous responses if not tightly bounded.
- enforcement agents are useless without real permissions and receipt verification.

OsMEN SHOULD adopt the social and ACP binding model, but SHOULD NOT let routing or workflow state live only inside chat sessions.

## AutoGen contribution

AutoGen contributes the correct abstraction for discussion nodes.

- manager-selected speaker flow.
- topic/subscription mental model.
- handoff-based termination.
- save/load team state.

Use AutoGen-like mechanics for open deliberation:

- explicit next-speaker selection.
- hard termination conditions.
- resumable discussion state.
- agent topics rather than direct pairwise spaghetti.

Do not copy the full framework. Copy the control pattern.

## CrewAI contribution

CrewAI contributes the correct abstraction for structured work.

- structured state objects.
- sequential and hierarchical task execution.
- router nodes.
- guardrails with retry.
- explicit human-input checkpoints.

Use CrewAI-like mechanics for deterministic segments:

- decomposition.
- research pipelines.
- synthesis and validation.
- artifact progression from v1 to vN.

Do not force open debate into a rigid pipeline.

## Agentic Dispatch lessons

A seven-agent shared-gateway experiment produced the exact failures this system must prevent.

- simultaneous response storms.
- policy cascades.
- enforcement collapse.
- temporal drift.
- stale-state posting.

The core lessons are structural.

- `collect` queueing plus simultaneous broadcast can make all agents answer in parallel.
- a policy file written later does not help sessions that never refreshed.
- an enforcement agent without actual Discord permissions becomes more noise.
- human presence at critical moments materially improved outcomes.
- novelty gates, receipt gates, session refresh, and real timeout authority matter more than extra prose in prompts.

Therefore OsMEN MUST treat public bot speech as a scarce resource, not as a default behavior.

# Target Architecture

## Recommended topology

Recommended default: one OsMEN orchestration core, many bot identities, mixed transport adapters.

```text
Discord Guild(s)
  <->
Bot Identities
  <->
Transport Adapters
  <->
OsMEN Orchestration Core
  <->
Redis Event Bus + Task Ledger + Markdown Memory + Approval Gate
  <->
Model Backends
  - cloud thinkers
  - local workers
  - NPU swarm
```

## Core rule

A logical agent and a Discord bot are 1:1 at the identity layer and 1:N at the backend layer.

Meaning:

- every agent gets its own Discord application, token, presence, permissions, and session namespace.
- multiple agents MAY share the same underlying model backend with different prompts, policies, and memory surfaces.
- different transport adapters MAY represent the same orchestration semantics.

## Transport classes

Three transport classes MUST be supported.

- `openclaw_full_agent`
  - separate OpenClaw runtime per agent or per small cluster.
  - native Discord bindings, ACP, native approvals.
- `openclaw_multi_agent_gateway`
  - one OpenClaw gateway hosting many agents with multi-agent routing and ACP bindings.
- `lightweight_discord_adapter`
  - Python or TypeScript bot handling Discord I/O only, delegating all orchestration to OsMEN APIs.

Recommended hybrid:

- elite agents or tool-heavy coding agents use `openclaw_full_agent` or `openclaw_multi_agent_gateway`.
- swarm critics, watchdogs, summarizers, and curators use `lightweight_discord_adapter`.

## Control plane vs data plane

Control plane:

- agent registry
- session registry
- policy bundles
- task ledger
- approval decisions
- moderation authority
- backend routing
- cost and urgency policy

Data plane:

- Discord messages
- reactions
- threads
- artifacts
- claims
- receipts
- summaries
- verification notes

The control plane MUST be authoritative. Discord is only a view and input channel.

# Runtime Entities

## Entity model

```python
class AgentDefinition(BaseModel):
    agent_id: str
    role: str
    capabilities: list[str]
    backend_profile: str
    discord_account_id: str
    memory_strategy: str
    policy_bundle_id: str

class BotIdentity(BaseModel):
    discord_account_id: str
    app_id: str
    guild_permissions: list[str]
    presence_mode: str
    transport_kind: str

class Workflow(BaseModel):
    workflow_id: str
    mode: Literal["team", "debate"]
    objective: str
    status: str
    owner_agent_id: str
    steward_agent_id: str
    urgency_score: int
    policy_epoch: str
    created_at: datetime

class WorkItem(BaseModel):
    work_item_id: str
    workflow_id: str
    type: str
    assigned_agent_id: str
    artifact_id: str | None
    status: str
    dependencies: list[str]
    deadline_at: datetime | None

class Claim(BaseModel):
    claim_id: str
    workflow_id: str
    artifact_id: str
    author_agent_id: str
    claim_type: str
    text: str
    evidence_refs: list[str]
    confidence: float
    verification_state: str
    expires_at: datetime | None

class Receipt(BaseModel):
    receipt_id: str
    action_type: str
    actor_agent_id: str
    platform: str
    platform_object_id: str
    status: Literal["ok", "failed"]
    raw_ref: str
```

## Workflow status model

Use one workflow ledger for both modes.

Allowed states:

- `submitted`
- `triaged`
- `scoped`
- `decomposed`
- `running`
- `challenged`
- `verifying`
- `awaiting_human`
- `approved`
- `published`
- `aborted`

Public Discord posting is allowed only in `running`, `challenged`, `verifying`, and `published`.

## Session namespace

Use deterministic keys.

- `conversation_key = discord:<guild_id>:<channel_id>:<thread_id|main>`
- `session_key = agent:<agent_id>:<conversation_key>`
- `policy_epoch = sha256(policy_bundle_contents)`
- `workflow_key = wf:<workflow_id>`

A session whose `policy_epoch` does not match the current workflow or channel policy bundle is stale.

# Discord Identity Model And Bridge Interfaces

## Discord server layout

One or more Discord servers MAY be used. Each server SHOULD define channel classes, not ad hoc channels.

Required channel classes:

- intake
- team work
- debate
- approvals
- ops/alerts
- archive

Recommended pattern:

- top-level channel receives task intake.
- each workflow gets a Discord thread.
- almost all multi-agent work happens inside the thread.
- top-level channels stay low-noise.
- watchdog and approval chatter goes to ops or approval channels, not the main work thread.

## Permission profiles

Do not give every bot the same rights.

Profiles:

- `observer`: read, react.
- `worker`: read, send, thread create, react.
- `reviewer`: worker + message reference, no moderation.
- `steward`: reviewer + manage threads.
- `enforcer`: steward + manage messages/moderate members.
- `approver_proxy`: DM delivery of approvals, no public posting unless configured.

No bot SHOULD have `Administrator`.

## Public speech policy

Default rule: bots are silent unless one of these is true.

- directly mentioned
- currently assigned owner
- currently holds the workflow driver token
- watchdog condition exceeded threshold
- human explicitly requested multi-agent discussion
- steward requested a critique turn

This rule is mandatory. It is the primary anti-storm control.

## ACP-style bridge contract

“ACP-style” in this spec means a session-oriented, bidirectional control bridge with explicit admission and receipt semantics.

Bridge requirements:

- every inbound Discord event is normalized into a typed bridge event.
- every outbound bot action is a typed request with receipt handling.
- every session is explicitly addressable by `session_key`.
- every action can be cancelled, preempted, or escalated.
- every mutating or moderating action passes through admission control.

## Inbound schema

Extend the current bridge shell, do not replace it.

```python
class BridgeInboundMessage(BaseModel):
    type: str
    correlation_id: str | None
    payload: dict[str, Any]

# payload for discord.message.created
{
  "platform": "discord",
  "guild_id": "123",
  "channel_id": "456",
  "thread_id": "789",
  "message_id": "999",
  "conversation_key": "discord:123:456:789",
  "author": {
    "platform_user_id": "321",
    "display_name": "deewill",
    "is_bot": False
  },
  "mentions": ["agent:critic", "agent:steward"],
  "reply_to_message_id": "998",
  "attachments": [],
  "text": "...",
  "received_at": "2026-04-14T16:00:00Z",
  "policy_epoch": "sha256:...",
  "mode_hint": "team"
}
```

Required event types:

- `discord.message.created`
- `discord.message.edited`
- `discord.reaction.added`
- `discord.thread.created`
- `discord.thread.archived`
- `discord.member.timeout_applied`
- `discord.approval.clicked`
- `discord.presence.changed`
- `bridge.session.refresh_required`

## Outbound schema

```python
class BridgeOutboundMessage(BaseModel):
    type: str
    correlation_id: str | None
    payload: dict[str, Any]

# payload for discord.message.send
{
  "target_agent_id": "critic",
  "conversation_key": "discord:123:456:789",
  "workflow_id": "wf_01",
  "visibility": "public",
  "reply_to_message_id": "999",
  "content": "...",
  "artifact_ref": "tasks/wf_01/artifact.v2.md#summary",
  "claim_refs": ["cl_11", "cl_12"],
  "requires_receipt": true
}
```

Required outbound types:

- `discord.message.send`
- `discord.message.react`
- `discord.thread.create`
- `discord.presence.set`
- `discord.approval.request`
- `discord.moderation.timeout`
- `session.cancel`
- `session.refresh`
- `workflow.pause`
- `workflow.resume`

## Adapter interface

All transport classes MUST satisfy the same interface.

```python
class AgentTransport(Protocol):
    async def ingest(self, event: BridgeInboundMessage) -> None: ...
    async def send(self, event: BridgeOutboundMessage) -> Receipt: ...
    async def cancel(self, session_key: str, reason: str) -> None: ...
    async def refresh(self, session_key: str, policy_epoch: str) -> None: ...
```

# Workflow Model

## Shared orchestration primitive

OsMEN SHOULD implement a reusable `WorkflowGraph` with two node families.

- `PipelineNode`
  - deterministic, owner-assigned, guardrailed, retryable.
- `DiscussionNode`
  - turn-based, speaker-selected, termination-bounded.

A workflow may alternate between them.

Example:

```text
Intake
-> TriagePipeline
-> PlanPipeline
-> ResearchDiscussion
-> SynthesisPipeline
-> CritiqueDiscussion
-> VerificationPipeline
-> PublishPipeline
```

## Mode A: cooperative team execution

Mode A is the default for productive work.

Required roles:

- `steward`
- `planner`
- `researcher`
- `worker`
- `critic`
- `verifier`

Behavioral rules:

- one steward owns public coherence.
- one planner decomposes.
- workers and researchers mostly write to artifacts, not chat.
- critics and verifiers gate publication.
- only steward or explicitly assigned owner publishes synthesis to the shared thread.

Task decomposition contract:

- every workflow begins with `TaskBrief`.
- planner emits `WorkItem`s with owner, expected artifact, dependencies, evidence needs, and deadline.
- workers update artifact versions.
- steward recomposes from artifact versions, never from raw chat only.

Artifact contract:

- each artifact is versioned.
- each artifact version carries claims.
- claims requiring evidence cannot reach `published` without verification.

## Mode B: debate, critique, brainstorming

Mode B is not “everyone talks”. It is structured adversarial conversation.

Required roles:

- `proposer`
- `naysayer`
- `lateral_innovation`
- `stable_focus`
- `iteration_steward`
- `verifier`

Turn mechanics:

- proposer states the current thesis or option set.
- naysayer attacks rigor, evidence, missing context, laziness.
- lateral agent proposes orthogonal reframing.
- stable focus blocks scope drift.
- verifier scores evidence or contradiction.
- iteration steward updates the current version of the thesis.

Hard limits:

- max public turns per agent per cycle: 1
- max turns per cycle: 6
- max cycles before either synthesis or human escalation: 3

Allowed move types:

- `claim`
- `attack`
- `repair`
- `reframe`
- `narrow`
- `synthesize`
- `handoff`

Any other move type is suppressed or rewritten into one of the above.

## Prompt and routing encoding

Roles MUST be encoded both in prompt policy and in routing policy.

Prompt policy encodes:

- mission
- allowed move types
- mandatory checks
- silence conditions
- escalation conditions

Routing policy encodes:

- who is allowed to reply publicly
- when a role is auto-triggered
- when a role stays private
- what artifacts each role reads and writes

Examples:

- naysayer auto-triggers on `artifact_published`, `high_confidence_claim`, or `contradiction_detected`.
- stable focus auto-triggers on branch explosion or topic drift.
- lateral innovation auto-triggers only when current options converge too early or when requested.
- iteration steward always writes the canonical version marker.

# Memory Model

## Primary principle

Shared markdown is the primary collaborative memory surface. Structured stores index it. Vector search is optional and secondary.

This follows the strongest part of the OpenClaw/discord-agent-swarm pattern while avoiding “the vector DB knows the truth”.

## Memory layers

Layer 1: raw transcript and receipts.

- Discord events mirrored into Postgres and JSONL.
- immutable.
- never summarized in place.

Layer 2: markdown working memory.

- per workflow directory.
- human-readable.
- agent-readable.
- version-controlled if desired.

Layer 3: structured task ledger.

- workflow state.
- work items.
- claims.
- receipts.
- verification status.
- urgency metrics.

Layer 4: optional semantic index.

- pgvector or similar over markdown fragments and structured claims.
- discovery only, never authority.

## Workflow memory layout

```text
swarm/
  policies/
  decision-log.md
  workflows/
    wf_01/
      brief.md
      state.yaml
      debate.md
      evidence.md
      artifact.v1.md
      artifact.v2.md
      claims.jsonl
      receipts.jsonl
      summary.md
  agents/
    critic/scratch.md
    planner/scratch.md
```

## Memory access policy

- public-facing agents MUST read `brief.md`, `summary.md`, and current `artifact.vN.md` before speaking.
- agents SHOULD NOT read the full raw transcript unless explicitly needed.
- memory curator agents compress transcript into `summary.md`.
- decision log entries MUST be append-only and timestamped.
- policy files MUST be hashed into `policy_epoch`.

## Temporal drift control

Every speaking session MUST perform a freshness preflight.

Freshness preflight checks:

- current `policy_epoch`
- current artifact version
- current decision-log cursor
- current summary revision
- whether the last session load predates a policy or artifact change

If stale:

- public posting is blocked
- private draft allowed
- orchestrator emits `session.refresh`
- if refresh fails, escalate to human or steward

This is the main temporal-drift control.

# Urgency, Interruption, And Human Oversight

## Formal urgency schema

Keep `EventPriority`, add a numeric urgency score.

```python
class UrgencyCategory(StrEnum):
    BACKGROUND = "background"
    NORMAL = "normal"
    IMPORTANT = "important"
    HIGH = "high"
    CRITICAL = "critical"
    PREEMPT = "preempt"

class UrgencyAssessment(BaseModel):
    score: int  # 0..100
    category: UrgencyCategory
    reasons: list[str]
    computed_by: list[str]
```

Mapping:

- `0-19`: background
- `20-39`: normal
- `40-59`: important
- `60-79`: high
- `80-89`: critical
- `90-100`: preempt

Map to current OsMEN `EventPriority`:

- background -> low
- normal/important -> normal
- high -> high
- critical/preempt -> critical

## Urgency inputs

Urgency is computed from detectors, not vibes.

Suggested weights:

- direct human mention: `+20`
- explicit human interrupt: `+40`
- contradiction against accepted artifact: `+25`
- stale session or stale policy: `+30`
- policy violation or moderation risk: `+40`
- high disagreement across models: `+20`
- critical-path blocked dependency: `+20`
- duplicate public replies forming storm: `+35`
- claimed action without receipt: `+35`
- safety or security concern: `+50`

Cap at `100`.

## Interrupt semantics

Interrupts MUST be first-class events.

```json
{
  "type": "session.cancel",
  "payload": {
    "target_session_key": "agent:critic:discord:123:456:789",
    "workflow_id": "wf_01",
    "reason": "contradiction_detected",
    "urgency_score": 92,
    "requested_by": "watchdog_storm"
  }
}
```

Interrupt authority:

- human
- enforcer
- steward
- watchdogs with threshold permission
- approval gate for high-risk mutation

Interrupt effects:

- cancel in-flight generation if backend supports cancellation.
- suppress queued public reply.
- convert reply to private note if safe.
- request fresh context reload.
- if moderation or safety-related, freeze workflow until receipt or human decision.

## Human oversight points

Human presence is mandatory at these points.

- high or critical risk tool execution.
- moderation actions in Discord.
- unresolved disagreement after 3 debate cycles.
- final publication marked authoritative or externally actionable.
- policy bundle change affecting a live workflow.
- repeated stale-session failures.
- cross-model verification deadlock.

If human is unavailable:

- workflow downgrades to advisory-only.
- no authoritative final answer.
- no external side effects.
- no moderation action except pre-approved emergency policy.

# Swarm Plus Elite Hierarchy

## Core pattern

Use many cheap, small agents for filtering and detection. Use one or two expensive agents for synthesis and decision.

Swarm agents:

- duplicate detector
- contradiction detector
- source extractor
- memory curator
- relevance filter
- log analyzer
- policy freshness checker
- lightweight critic
- cost watchdog
- queue watchdog

Elite agents:

- strategic planner
- final synthesizer
- arbitration judge
- high-context researcher
- final implementation-guidance writer

## Interface between swarm and elite

Swarm agents MUST emit structured notes, not freeform essays.

```python
class SwarmNote(BaseModel):
    note_id: str
    workflow_id: str
    target_ref: str
    note_type: str
    score: float
    tags: list[str]
    summary: str
    evidence_refs: list[str]
```

Elite agents consume:

- current artifact
- current summary
- top swarm notes
- claim table
- disagreement table
- cost/time budget

Elite agents emit `DecisionPacket`.

```python
class DecisionPacket(BaseModel):
    workflow_id: str
    decision_type: str
    chosen_option: str
    rationale: str
    required_followups: list[str]
    verification_requirements: list[str]
```

## Why this hierarchy works

- swarm notes reduce context bloat.
- swarm diversity catches shallow mistakes early.
- elite agents do not waste tokens on scanning raw transcript noise.
- cross-model verification becomes cheap because most checks are local.
- context loss is reduced because curators maintain small, fresh summaries.
- hallucinations are reduced because final synthesis sees contradiction and evidence annotations, not only one model’s chain of thought.

## fastflowlm and Ubuntu reality

Inference from current public FastFlowLM materials: GA runtime and install path are Windows 11-focused, with official docs currently centered on Windows installers and Ryzen AI NPUs. OsMEN-OC targets Ubuntu 26.04. Therefore the spec SHOULD treat “fastflowlm/NPU swarm” as a runtime class, not a hard binary dependency.

Normative consequence:

- the orchestration layer MUST target an OpenAI-compatible local inference endpoint.
- `fastflowlm`, Lemonade `flm`, or any equivalent NPU-first server MAY satisfy that endpoint.
- swarm roles should be backend-agnostic as long as latency and cost class match.

# Deployment Patterns And Resource Tradeoffs

## Hardware baseline

Target machine:

- AMD Ryzen AI 9 365
- 10 CPU cores / 20 threads
- 64 GB RAM
- Radeon 880M iGPU
- RTX 5070 8 GB
- 50 TOPS NPU class on Ryzen AI 300 platform

Local OsMEN config already assumes:

- NPU for small and medium inference, embeddings, transcription.
- NVIDIA for large models.
- Vulkan or CPU fallback.

## Pattern comparison

| Pattern | Processes | Estimated extra RAM | Isolation | Complexity | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Thin bots + one OsMEN orchestrator | 1 Python core + N small bot adapters | ~0.8-2.0 GB total, plus model servers | Medium | Medium | Default |
| One OpenClaw gateway with many agents + OsMEN | 1 Python core + 1 Node gateway | ~1.5-3.0 GB total, plus model servers | Medium | Medium-high | Best if ACP/thread binding features are central |
| One OpenClaw instance per agent | 1 Python core + N Node runtimes | ~0.3-0.7 GB per agent, inferred estimate | High | High | Only for strict isolation or divergent tool policy |

RAM figures above are engineering estimates; OpenClaw docs do not publish official per-instance idle memory numbers.

## Backend allocation strategy

Recommended backend classes:

- `swarm_local_fast`
  - 0.6B-1B class models
  - NPU preferred
  - tasks: tagging, duplication, contradiction hints, summary compression
- `worker_local_medium`
  - 2B-4B class models
  - NPU or Vulkan
  - tasks: first-pass drafting, structured critique, evidence extraction
- `gpu_local_large`
  - 7B-9B quantized class on 8 GB VRAM when feasible
  - tasks: local fallback synthesis, multimodal, larger-context local review
- `cloud_elite`
  - best available frontier models
  - tasks: strategic decomposition, tie-break, final answer, high-context synthesis

## Practical concurrency on this hardware

Recommended hot-set:

- one NPU small model for watchdogs and critics
- one NPU medium model for worker tasks
- one embedding or transcription service on NPU only if latency budget permits
- one GPU model only when not competing with gaming or other graphical loads
- one or two cloud thinkers on demand

On this box, the NPU SHOULD be treated as a serialized or lightly multiplexed specialist, not as a free-for-all many-model host. A queue over one or two hot models is preferable to many cold starts.

## Recommended topology for OsMEN

Best fit:

- lightweight Discord bots for `critic`, `focus`, `curator`, `steward`, `watchdog_*`
- one OpenClaw-backed `research_elite`
- optional one OpenClaw-backed `implementation_guide`
- OsMEN core owns workflow ledger, policy epochs, urgency, and receipts
- OpenClaw agents integrate through ACP sessions or normalized bridge messages

# Failure Containment And Enforcement

## Mandatory anti-storm controls

1. Driver token.
Only one agent may produce unsummoned public synthesis in a workflow at a time.

2. Novelty gate.
Before public send, compare against recent public messages. If semantic overlap is high and no new evidence exists, suppress.

3. Velocity gate.
Cap public bot messages per workflow and per minute. On breach, auto-switch to steward-only or human-only.

4. Mention gate.
Direct mentions route only to mentioned agents plus steward.

5. Silent default.
If an agent has useful but non-urgent analysis, it writes a note, not a public reply.

## Mandatory anti-cascade controls

- only one policy owner may discuss policy in a live workflow thread.
- all other policy discussion is redirected to a policy channel or artifact.
- debate nodes must end with implementation handoff or decision marker.
- guardrails must run before a policy-like response becomes public.

## Mandatory enforcement controls

- moderation-capable enforcer bot has actual Discord permissions.
- every moderation or mutating action MUST yield a receipt.
- text claiming enforcement without receipt is invalid and auto-corrected to `attempted_unverified`.
- watchers monitor receipt absence and escalate immediately.

## Mandatory freshness controls

- session refresh required after policy bundle change.
- session refresh required after artifact major version change if session has pending public output.
- long-idle sessions require preflight before posting.
- watchdog triggers on stale `policy_epoch`.

## Human presence requirements

Loaded policy, real enforcement, human presence at critical points:

- policies MUST be materialized into the live session bundle, not only stored on disk.
- enforcement MUST be mechanical, not narrated.
- humans MUST witness or approve critical transitions.

This triad is non-optional.

## Observability and SLOs

Minimum metrics:

- public bot messages per workflow
- duplicate suppressions
- stale-session blocks
- session refresh count
- interrupt count by reason
- disagreement score per workflow
- receipt failure count
- approval latency
- time-to-human-escalation
- token usage per agent and backend
- NPU queue depth
- cloud spend per workflow

Suggested SLOs:

- zero public moderation claims without receipts
- zero authoritative publishes from stale sessions
- fewer than 2 unsanctioned bot public replies within 5 seconds in the same workflow
- critical interrupts applied in under 2 seconds median
- verification on 100% of factual or architectural final claims

# Normative Source Anchors

## External

1. OpenClaw configuration reference: multi-account routing, thread bindings, ACP bindings, queue modes.  
https://docs.openclaw.ai/gateway/configuration-reference

2. OpenClaw Discord channel docs: auto presence, approvals, ACP bindings in Discord.  
https://docs.openclaw.ai/channels/discord

3. OpenClaw ACP CLI docs: session mapping, agent-scoped session keys, bridge behavior.  
https://docs.openclaw.ai/cli/acp

4. AutoGen group chat pattern: manager-selected speaker, topic-based protocol.  
https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/design-patterns/group-chat.html

5. AutoGen teams and human-in-the-loop termination.  
https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/teams.html  
https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html

6. AutoGen state save/load for resumable teams.  
https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/state.html

7. CrewAI flows: structured state, persistence, router nodes.  
https://docs.crewai.com/en/concepts/flows

8. CrewAI processes: sequential and hierarchical execution.  
https://docs.crewai.com/en/concepts/processes

9. CrewAI tasks: guardrails and retry semantics.  
https://docs.crewai.com/en/concepts/tasks

10. CrewAI human input on execution.  
https://docs.crewai.com/en/learn/human-input-on-execution

11. Discord rate limits and thread behavior.  
https://docs.discord.com/developers/topics/rate-limits  
https://docs.discord.com/developers/resources/channel  
https://docs.discord.com/developers/topics/threads

12. Discord privileged message-content intent.  
https://docs.discord.com/developers/events/gateway  
https://support-dev.discord.com/hc/en-us/articles/4404772028055-Message-Content-Privileged-Intent-FAQ

13. FastFlowLM official materials: NPU-first runtime, OpenAI-compatible server, Windows-centric install path, benchmark ranges.  
https://fastflowlm.com/  
https://docs.fastflowlm.com/install.html  
https://fastflowlm.com/benchmarks/

14. AMD Ryzen AI 9 365 official product page and Ryzen AI 300 announcement.  
https://www.amd.com/en/products/processors/laptop/ryzen/ai-300-series/amd-ryzen-ai-9-365.html  
https://www.amd.com/en/newsroom/press-releases/2024-6-2-amd-unveils-next-gen-zen-5-ryzen-processors-to-p.html

15. Externalization in LLM Agents: memory, skills, protocols, harness engineering as the system layer.  
https://arxiv.org/abs/2604.08224

16. Agent Control Protocol: stateful admission control, anomaly accumulation, cooldown, deviation collapse.  
https://arxiv.org/abs/2603.18829

17. OpenClaw security taxonomy: cross-layer trust failure and need for unified policy boundaries.  
https://arxiv.org/abs/2603.27517

18. Agentic Dispatch shared-gateway case study: response storms, policy cascade, temporal drift, enforcement collapse.  
https://the-agentic-dispatch.com/la-bande-a-bonnot-paper/

## Local OsMEN anchors

- Event envelope: [core/events/envelope.py](/home/dwill/dev/OsMEN-OC/core/events/envelope.py:1)
- Bridge protocol: [core/bridge/protocol.py](/home/dwill/dev/OsMEN-OC/core/bridge/protocol.py:1)
- OpenClaw WebSocket bridge client: [core/bridge/ws_client.py](/home/dwill/dev/OsMEN-OC/core/bridge/ws_client.py:1)
- Approval gate: [core/approval/gate.py](/home/dwill/dev/OsMEN-OC/core/approval/gate.py:1)
- Pipeline runner: [core/pipelines/runner.py](/home/dwill/dev/OsMEN-OC/core/pipelines/runner.py:1)
- Manifest scanner and MCP registry: [core/gateway/mcp.py](/home/dwill/dev/OsMEN-OC/core/gateway/mcp.py:1)
- Gateway app lifecycle: [core/gateway/app.py](/home/dwill/dev/OsMEN-OC/core/gateway/app.py:1)
- Compute routing: [config/compute-routing.yaml](/home/dwill/dev/OsMEN-OC/config/compute-routing.yaml:1)
- OpenClaw bridge config: [config/openclaw.yaml](/home/dwill/dev/OsMEN-OC/config/openclaw.yaml:1)

This specification’s key decision is simple: Discord is the visible multiplayer surface, markdown is the shared cognitive substrate, OsMEN is the authoritative orchestrator, small local agents do most of the watching and filtering, and elite agents are reserved for synthesis, arbitration, and final judgment. That combination matches the repo, matches the hardware, and directly addresses the observed failure modes of shared-agent systems.
