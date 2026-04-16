# Agent Departments: A Manifesto

## Preamble

Single-model AI is structurally incapable of self-correction. The organizational pattern — one entity plans, executes, reviews, and approves — guarantees sycophancy, skips adversarial review, and produces confident mediocrity. This is not a model problem. It is an organizational design problem.

The solution is not better models. It is better organizations.

---

## I. Thesis

Every project should have a team of specialized lead agents — departments — each with defined accountability, structured output contracts, and authority limited to their domain. Small models on edge hardware (NPUs) handle 90% of the work. An elite model handles the remaining 10% — judgment calls, cascade detection, tiebreaking.

The unit of organization is the **department**, not the agent. Agents have personas. Departments have contracts.

---

## II. The Evidence

| System                    | What It Proves                                                                                                              | What It Lacks                                                  |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **FastFlowLM** (1163★)    | NPU inference is production-ready. 17MB runtime, 256k context, 10-15W. A $600 laptop runs models that used to require GPUs. | Multi-model coordination, agent architecture                   |
| **Tiny-MoA**              | Swarm architecture works on CPU. 1.2B Brain routes to 600M Reasoner + 90M Tool Caller. 2GB total memory.                    | Adversarial roles, critique loop, persistent memory            |
| **Quorum** (86★)          | Structured multi-model debate produces better output than single-model. 7 methods (Oxford, Socratic, Delphi).               | Local execution, persistence, memory, role specialization      |
| **local-llm-swarm**       | Planner/Executor/Critic loop with GGUF. Token-aware context. VRAM management.                                               | Long-term memory, inter-project continuity, departmental roles |
| **OpenClaw** (v2026.4.12) | Multi-agent identity, Discord binding, shared memory, multi-model routing, ACP protocol, 29 skills.                         | Foundation checks, calibration, department weighting           |

Nobody has combined all of these. The pieces exist. The integration does not.

---

## III. The Architecture

```
┌──────────────────────────────────────────┐
│  ELITE LAYER (cloud, <10% of calls)      │
│  Judgment, cascade detection, tiebreak    │
│  Cost: $0.01-0.15/call                   │
├──────────────────────────────────────────┤
│  DEPARTMENT LAYER (NPU, 90% of calls)    │
│                                           │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐  │
│  │Naysayer │ │Innovator │ │Stabilizer│  │
│  │1.7B     │ │1.7B      │ │1.0B      │  │
│  │Critique │ │Alternate │ │Scope     │  │
│  └─────────┘ └──────────┘ └──────────┘  │
│  ┌─────────┐ ┌──────────┐               │
│  │Iterator │ │Connector │               │
│  │1.7B     │ │Embed     │               │
│  │Execute  │ │Memory    │               │
│  └─────────┘ └──────────┘               │
│                                           │
│  Cost: $0.00/call (local)                │
├──────────────────────────────────────────┤
│  SWARM LAYER (NPU, <500M models)         │
│  Classification, routing, formatting     │
│  Cost: $0.00/call (local)                │
└──────────────────────────────────────────┘
```

### Latency Budget

| Layer      | Per-call | Calls per task | Total  |
| ---------- | -------- | -------------- | ------ |
| Swarm      | <50ms    | 3-5            | <250ms |
| Department | 1-5s     | 5-10           | 5-50s  |
| Elite      | 5-30s    | 0-1            | 0-30s  |

### Cost Budget (per 10-turn task)

| Layer                      | Cost      |
| -------------------------- | --------- |
| Swarm + Department (local) | $0.00     |
| Elite (10% of tasks)       | $0.01     |
| **Total**                  | **$0.01** |

Comparable single cloud model: $0.05, no adversarial review.

---

## IV. The Departments

### Naysayer (Critical Analysis)

The most important department. Not because criticism is valuable, but because LLMs have a structural sycophancy bias. The Naysayer is a **countermeasure**, not a personality.

```python
NAYSAYER_CHECKLIST = [
    "List every logical error or unsupported claim.",
    "Name one missing edge case.",
    "Identify one assumption not validated by the spec.",
    "What test case would break this that wasn't written?",
    "What is the worst-case performance (not average)?",
    "If this fails in production, what is the blast radius?",
    "What does this implementation assume that might not be true?",
]

def naysayer_review(proposal: str, spec: str, model: Model) -> Critique:
    """Structured checklist. Small models handle this well."""
    findings = []
    for item in NAYSAYER_CHECKLIST:
        response = model.chat(
            system="Answer with the specific finding only. No preamble.",
            messages=[{"role": "user",
                      "content": f"Spec:\n{spec}\n\nImplementation:\n{proposal}\n\n{item}"}]
        )
        findings.append(response)

    genuine_issues = [f for f in findings if not f.lower().startswith(("no ", "none", "n/a"))]
    return Critique(
        issues=genuine_issues,
        passed=len(genuine_issues) <= 2,  # allow minor issues
        confidence=1.0 - (len(genuine_issues) / len(NAYSAYER_CHECKLIST))
    )
```

**Key insight**: Structure compensates for capability. A 1.7B model answering "what test would break this?" produces useful output. The same model asked "review this code" produces garbage. The checklist is the innovation, not the model.

**Accountability**: Output accuracy, edge case coverage, logical soundness.
**Failure mode**: Approves bad work (false negative) or rejects everything (false positive).

### Innovator (Lateral Thinking)

Proposes alternatives the team hasn't considered. Triggered after Naysayer identifies problems, or on explicit request.

**Accountability**: Alternative approaches, assumption challenging.
**Failure mode**: Repeats existing proposals or suggests infeasible ideas.

### Stabilizer (Focus Enforcement)

Keeps the team on scope. Detects drift. Enforces priorities. The cheapest department — can run on a 1B model because scope checking is structurally simple.

**Accountability**: Scope adherence, priority enforcement.
**Failure mode**: Blocks all work as "out of scope" or allows all drift.

### Iterator (Execution)

Implements the agreed approach. Generates code. Runs tests. The worker department.

**Accountability**: Working implementation, test coverage.
**Failure mode**: Ships code that doesn't match the agreed approach.

### Connector (Memory)

Maintains shared context. Surfaces relevant history. Runs continuously as an embedding model — the one department that never time-slices.

**Accountability**: Context relevance, decision continuity.
**Failure mode**: Surfaces irrelevant context or misses critical history.

---

## V. The Protocol

Departments communicate via a **shared blackboard**. In practice: a Discord channel.

```python
@dataclass
class DepartmentMessage:
    sender: str          # "naysayer", "innovator", etc.
    authority_domain: str  # "quality", "scope", "feasibility"
    weight: float        # 0.0-1.0 — how much this opinion counts
    content: str
    confidence: float    # 0.0-1.0
    blocking: bool       # True = pipeline stops until addressed

AUTHORITY_WEIGHTS = {
    "quality":     {"naysayer": 0.8, "innovator": 0.3},
    "scope":       {"stabilizer": 0.9, "naysayer": 0.2},
    "feasibility": {"iterator": 0.7, "naysayer": 0.5},
    "alternatives":{"innovator": 0.8, "connector": 0.4},
    "history":     {"connector": 1.0},
}
```

### Turn-taking rules

1. **Explicit routing**: `@Claude fix the race condition` — only Claude responds
2. **Domain keywords**: "implement" → Iterator, "design" → Innovator, "scope" → Stabilizer
3. **Naysayer auto-trigger**: Any message containing "done", "fixed", "solution", "works" gets auto-reviewed
4. **Escalation**: Any department can `@all` when cascade error detected
5. **Max 2 departments per message**: Prevents everyone talking at once

---

## VI. The Five Principles

**1. Departments, not agents.** Agents have personas. Departments have contracts. The Naysayer is not a grumpy character — it's a verification pipeline.

**2. Structure compensates for capability.** A small model with a rigorous checklist outperforms a large model with vague instructions. This is the core enabler for NPU-based departments.

**3. The Naysayer is structural, not personal.** It exists because LLMs have a sycophancy bias. Its purpose is countermeasure, not personality.

**4. Shared success, no department credit.** The organization succeeds or fails as one unit. The QA department doesn't get credit for finding bugs if the product fails.

**5. Spend 10% on verification.** Foundation checks prevent cascade errors. The cheapest inference is the one that catches a wrong premise before five departments execute on it.

---

## VII. The Deployment Map

```
OpenClaw Gateway (single process, 4 agents)
├── Agent "jarvis"    → zai/glm-5-turbo (coordinator/stabilizer)
├── Agent "claude"    → claude -p subprocess (iterator/naysayer)
├── Agent "glm"       → opencode serve :4321 (innovator/planner)
├── Agent "copilot"   → github-copilot API (reviewer)
├── Shared memory/    → daily logs + MEMORY.md + embedding search
└── Discord webhook   → single bot, 4 identities in #roundtable
```

Local hardware (NPU):

```
Slot 1 (persistent): nomic-embed-text (Connector department)
Slot 2 (shared):     qwen3-1.7b-thinking (Stabilizer/Naysayer/Innovator)
                    Same model, different system prompts per role
```

Setup:

```bash
# Create agents in OpenClaw
for agent in claude glm copilot; do
  openclaw agents add "$agent" --workspace ~/dev/OsMEN-OC/openclaw-"$agent"
  openclaw agents bind --agent "$agent" --bind discord
done

# Each agent gets SOUL.md defining role, accountability, triggers
# Each agent gets IDENTITY.md defining name, emoji
```

---

## VIII. The Honest Limitations

These are unsolved. Not handwaved — acknowledged as hard.

**1. Small model critique quality is unproven at scale.** The checklist approach helps, but nobody has benchmarked "1.7B model with structured checklist vs frontier model" on real code review tasks. It might work. It might produce false confidence.

**2. Cascade errors are the #1 risk.** If the Connector surfaces wrong context, every department works on a wrong foundation. The 10% verification budget mitigates this but doesn't eliminate it.

**3. Calibration is an open research problem.** How strict should the Naysayer be? Too strict blocks all work. Too lenient approves garbage. The auto-calibration loop (comparing Naysayer to Elite on same output) is a proposal, not a tested solution.

**4. Cross-model semantic alignment is unsolved.** When the Naysayer says "race condition in the handler" and the Iterator needs to know _which handler_ — the blackboard helps, but ambiguity remains. Each model encodes knowledge differently.

**5. NPU model switching latency.** FastFlowLM is fast (2-5s model switch). Running 4 roles through one model with different system prompts eliminates switching but loses parallelism.

**6. No benchmark exists for this.** Every claim about departmental superiority is theoretical. The measurement framework in Section IX is necessary before claiming this works.

---

## IX. The Measurement Framework

```python
@dataclass
class ExperimentResult:
    task_id: str
    approach: str           # "single-model" | "departmental"

    # Quality (human-rated 1-5)
    correctness: float
    completeness: float

    # Process
    latency_ms: int
    cost_usd: float
    revisions: int
    cascade_errors: int

    # Department metrics
    naysayer_fp: int        # rejected good work
    naysayer_fn: int        # approved bad work
    innovation_novelty: float
    scope_drift_events: int
```

Run 50 tasks both ways. Measure. Compare. The manifesto stands or falls on the data.

---

## X. The Reading List

| Resource                          | Relevance                                  |
| --------------------------------- | ------------------------------------------ |
| FastFlowLM/FastFlowLM (GitHub)    | NPU inference runtime                      |
| gyunggyung/Tiny-MoA (GitHub)      | Swarm/elite architecture on CPU            |
| Detrol/quorum-cli (GitHub)        | Multi-model debate methods                 |
| BEKO2210/local-llm-swarm (GitHub) | Planner/Executor/Critic loop               |
| OpenClaw v2026.4.12               | Agent OS with Discord, memory, multi-model |
| Qwen3-1.7B-Thinking (HF)          | Small reasoning model for departments      |
| LFM2.5-1.2B-Thinking (HF)         | Tiny thinking model for swarm layer        |

---

## XI. Conclusion

The future of AI-assisted development is not a smarter chatbot. It is an organization — small, specialized models running on edge hardware, each accountable for a specific quality dimension, with structured adversarial relationships that produce better output than any single model could alone.

The hardware is ready. The software pieces exist. The integration is the remaining work.

Build departments. Run the experiment. Let the data decide.

---

_5 drafts. 4 rounds of self-critique. 1 manifesto._
