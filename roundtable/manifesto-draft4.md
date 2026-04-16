# Agent Departments: A Manifesto

## Draft 4 — Deployment, Discord, and the Integration Map

### Round 4 Self-Critique

Drafts 1-3 built the theory. Draft 4 asks: can this actually be deployed today, on current hardware, with current software?

Findings from Round 4 research:

- CrewAI (48,869★) proves multi-agent role assignment works at scale. But it's cloud-first, Python-only, and each "agent" is a prompt, not a persistent process with identity.
- Quorum (86★) proves structured multi-model debate produces better output. But it's session-based, no persistence, no memory.
- Tiny-MoA proves the swarm/elite split works on CPU. But no adversarial roles.
- OpenClaw has 80% of the infrastructure. The 20% gap is foundation checks, calibration, measurement.
- Discord webhooks allow a single bot to post as multiple identities — no need for 4 bot tokens.

**New insight**: The deployment doesn't need 4 separate processes. It needs 1 OpenClaw process with 4 agents, posting via webhooks to the same channel.

---

## 14. The Deployment Architecture (New)

```
┌─────────────────────────────────────────────────────┐
│                    DISCORD                           │
│  Channel: #roundtable                               │
│                                                     │
│  🤖 Jarvis (OpenClaw agent "main")                  │
│  🧠 Claude (OpenClaw agent "claude" → claude -p)   │
│  💻 GLM (OpenClaw agent "glm" → opencode serve)     │
│  🔬 Copilot (OpenClaw agent "copilot" → GH API)    │
│                                                     │
│  All post via webhooks from single OpenClaw instance │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              OpenClaw Gateway :18789                 │
│                                                     │
│  Agent "jarvis"    → zai/glm-5-turbo (coordinator)  │
│  Agent "claude"    → claude-code subprocess          │
│  Agent "glm"       → opencode serve :4321            │
│  Agent "copilot"   → github-copilot API              │
│                                                     │
│  Shared: memory/, MEMORY.md, embedding search        │
│  Shared: Discord channel history (blackboard)        │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              LOCAL NPU / CPU                         │
│                                                     │
│  FastFlowLM: qwen3-1.7b (NPU)                       │
│  Ollama: gemma4, llama3.2 (GPU/CPU)                 │
│  Embedding: nomic-embed-text (NPU, persistent)       │
└─────────────────────────────────────────────────────┘
```

### Why This Works

1. **One process, four agents**: OpenClaw's agent system already supports this. Each agent has its own workspace, sessions, identity, SOUL.md, IDENTITY.md.

2. **Webhooks for identity**: Discord webhooks let one bot token post as different usernames. No need for 4 Discord applications.

3. **Mixed backends**: OpenClaw's model routing already handles ZAI, Ollama, GitHub Copilot. Adding Claude Code as a subprocess (via `claude -p`) is the same pattern as the existing `coding-agent` skill.

4. **Shared memory**: All agents write to the same `memory/` directory. The embedding search (nomic-embed-text) provides semantic retrieval across all agents' outputs.

### Setup Commands

```bash
# 1. Add agents to OpenClaw
openclaw agents add claude --workspace ~/dev/OsMEN-OC/openclaw-claude
openclaw agents add glm --workspace ~/dev/OsMEN-OC/openclaw-glm
openclaw agents add copilot --workspace ~/dev/OsMEN-OC/openclaw-copilot

# 2. Set identities
openclaw agents set-identity --agent claude --name "Claude" --emoji "🧠"
openclaw agents set-identity --agent glm --name "GLM" --emoji "💻"
openclaw agents set-identity --agent copilot --name "Copilot" --emoji "🔬"

# 3. Bind all to same Discord channel
openclaw agents bind --agent jarvis --bind discord
openclaw agents bind --agent claude --bind discord
openclaw agents bind --agent glm --bind discord
openclaw agents bind --agent copilot --bind discord

# 4. Create SOUL.md per agent (role definition)
```

### SOUL.md Examples

**Claude (Execution Authority)**:

```markdown
# SOUL.md — Claude Department

## Role

You are the Execution department. You write, test, and ship code.

## Accountability

- Working implementations that match the agreed approach
- Test coverage for edge cases the Naysayer identified
- Honest assessment of what you can and cannot implement

## When to respond

- When implementation is needed
- When the Naysayer's critique requires a code fix
- When asked directly via @Claude

## When to stay silent

- Architecture debates (that's GLM's domain)
- Scope discussions (that's Jarvis's domain)
- When you have nothing new to add

## Red lines

- Never ship code you haven't mentally tested
- Never say "this should work" — prove it
- Never implement without understanding the Naysayer's critique
```

**GLM (Architecture + Planning)**:

```markdown
# SOUL.md — GLM Department

## Role

You are the Architecture department. You design, plan, and evaluate approaches.

## Accountability

- Architecture decisions with clear trade-off analysis
- Identifying simpler alternatives the team hasn't considered
- Ensuring approaches are feasible before implementation starts

## When to respond

- When a new task requires an approach decision
- When the current approach is failing and alternatives are needed
- When asked directly via @GLM

## When to stay silent

- Implementation details (that's Claude's domain)
- Unless the implementation deviates from the agreed architecture
```

---

## 15. The Turn-Taking Protocol (Refined)

Not round-robin. Not everyone responds to everything. **Three triggers**:

1. **Explicit routing**: `@Claude fix the race condition` — only Claude responds
2. **Domain trigger**: Keywords match department accountability (automatic)
3. **Escalation**: Any department can `@all` when it detects a cascade error

```python
class TurnRouter:
    """Decides which department(s) should respond to a message."""

    DOMAIN_KEYWORDS = {
        "claude": ["implement", "code", "bug", "fix", "test", "deploy", "run", "execute"],
        "glm": ["architecture", "design", "approach", "pattern", "trade-off", "compare", "plan"],
        "jarvis": ["scope", "priority", "schedule", "decide", "remember", "context", "status"],
        "copilot": ["refactor", "optimize", "edge case", "type", "lint", "format", "review"],
    }

    def route(self, message: str, mentions: list[str]) -> list[str]:
        # Explicit mentions take priority
        if mentions:
            return mentions

        # Domain keyword matching
        message_lower = message.lower()
        scores = {}
        for dept, keywords in self.DOMAIN_KEYWORDS.items():
            scores[dept] = sum(1 for kw in keywords if kw in message_lower)

        # Respond if score > 0, but max 2 departments per message
        # (avoids everyone talking at once)
        active = [d for d, s in sorted(scores.items(), key=lambda x: -x[1]) if s > 0]
        return active[:2]

    def should_naysayer_review(self, message: str, context: str) -> bool:
        """Naysayer reviews any message that contains a claim or implementation."""
        claim_indicators = ["here's", "solution", "fixed", "works", "done", "implemented"]
        return any(kw in message.lower() for kw in claim_indicators)
```

---

## 16. The Five Principles (Summary)

1. **Departments, not agents.** Agents have personas. Departments have contracts.

2. **Structure compensates for capability.** A small model with a rigorous checklist beats a large model with vague instructions.

3. **The Naysayer is structural, not personal.** It exists because LLMs have a sycophancy bias, not because criticism is inherently valuable.

4. **Shared success, no department credit.** The organization succeeds or fails as one unit.

5. **Spend 10% on verification.** Foundation checks prevent cascade errors. The cheapest inference is the one that catches a wrong premise before 5 departments execute on it.

---

## 17. Open Questions (Honest Assessment)

These are genuinely unsolved:

1. **Can 1.7B models do useful critique with structured checklists?** Theoretically yes. Empirically unproven at scale.

2. **Does departmental AI actually outperform single-model on real tasks?** Quorum's debate methods suggest yes for reasoning tasks. No data for implementation tasks.

3. **How to calibrate the Naysayer without human feedback?** The Elite calibration loop in Draft 2 is a proposal, not a tested solution.

4. **Cross-model semantic alignment?** When the Naysayer says "race condition in the handler" and the Iterator needs to know _which handler_ — the shared blackboard helps, but ambiguity remains.

5. **NPU model switching latency?** FastFlowLM is fast but switching between 4 models still has measurable delay. Time-slicing may not be fast enough for interactive use.

---

_Draft 4 complete. Round 5 will produce the final manifesto: a single coherent document synthesizing all research, structured as a concise logical argument with code, principles, and honest limitations._
