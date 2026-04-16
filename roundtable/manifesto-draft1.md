# Agent Departments: A Manifesto

## Draft 1 — Structural Outline

### Thesis

Single-model AI is a dead end for complex work. The future is departmentalized agents: small, specialized models on edge hardware (NPUs) doing the bulk work, elite models handling judgment calls, and structured adversarial roles ensuring quality. Not a chatbot. An organization.

### Outline

1. **The Problem**: One model, one context window, one set of biases
2. **The Evidence**: What exists now (FastFlowLM, Tiny-MoA, Quorum, local-llm-swarm)
3. **The Architecture**: Departments, not agents
4. **The Roles**: Naysayer, Innovator, Stabilizer, Iterator, Connector
5. **The Hardware Reality**: NPU swarms on $500 laptops
6. **The Protocol**: How departments communicate
7. **The Anti-Patterns**: What fails and why
8. **The Implementation**: Code patterns
9. **The Economics**: Cost models
10. **The Challenges**: Brutal honesty about what doesn't work yet

### Draft 1 Body

---

## 1. The Problem

A single LLM is a generalist forced into every role. It plans, executes, reviews, and approves its own work. This is the structural equivalent of a one-person company — no checks, no specialization, no adversarial pressure toward quality.

Symptoms:

- Confident wrong answers (no internal dissent)
- Lazy shortcuts (no critic demanding rigor)
- Missing alternatives (no lateral thinker proposing other paths)
- Scope creep (no stabilizer enforcing focus)
- Forgotten context (no connector maintaining shared memory)

## 2. The Evidence

Real systems exist. They prove the concept while exposing the gaps.

**FastFlowLM** — Runs LLMs on AMD Ryzen AI NPUs. 17MB runtime, 20-second install, 256k context. No GPU needed. Power: 10-15W vs 300W for a GPU. Implication: a laptop can run 3-4 small models simultaneously on NPU+CPU.

**Tiny-MoA** — Proves the swarm thesis. 1.2B "Brain" model routes tasks to a 600M Reasoner and 90M Tool Caller. Total memory: 2GB. Runs on CPU. The Brain delegates; workers execute. Works. But: no adversarial pressure, no critic, no disagreement mechanism.

**Quorum** — Proves multi-model debate works. 7 methods (Oxford, Socratic, Delphi, etc.). Models argue, reach consensus. But: all models are cloud APIs, all expensive, no persistence, no memory between sessions, no role specialization beyond debate positions.

**local-llm-swarm** — Planner/Executor/Critic loop with GGUF models. Token-aware context packing. VRAM management. Closest to the vision. But: single-loop, no persistent departments, no long-term memory, no inter-project continuity.

What none of them do: combine edge hardware swarms with structured adversarial departments and persistent memory.

## 3. The Architecture

```
┌─────────────────────────────────────────┐
│            ELITE LAYER                   │
│   (Cloud API, when needed)               │
│   Judgment calls, final review,          │
│   tiebreaking, novel synthesis           │
├─────────────────────────────────────────┤
│         DEPARTMENT LAYER                 │
│   (NPU/Local models, always running)     │
│                                          │
│   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│   │Critiq│ │Innov.│ │Stabl.│ │Iter. │  │
│   │1.5B  │ │1.5B  │ │1.5B  │ │1.5B  │  │
│   └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘  │
│      └────────┴────────┴────────┘       │
│              Shared Blackboard           │
├─────────────────────────────────────────┤
│           SWARM LAYER                    │
│   (NPU micro-models, <500M params)       │
│   Classification, routing, formatting,   │
│   search, summarization, translation     │
└─────────────────────────────────────────┘
```

Each layer has different latency, cost, and capability profiles. The swarm layer runs at <50ms. The department layer at 1-5s. The elite layer at 5-30s.

## 4. The Roles

### Naysayer (Critical Analysis Department)

- **Model**: Local 1.5B reasoning model
- **Job**: Find flaws. Never approve on first pass.
- **Output format**: Structured critique
- **Anti-pattern**: "This looks good" — this is a failure
- **Insurance against**: Inaccuracy, laziness, superficial analysis

```python
NAYSAYER_SYSTEM = """You are the Critical Analysis department.
Your job is to find what is WRONG, MISSING, or LAZY in the proposed work.

For every output you review, you MUST identify:
1. At least one logical error or unsupported claim
2. At least one missing edge case
3. At least one assumption that wasn't validated
4. A confidence score (0-100) with specific reasons for uncertainty

If you cannot find genuine issues, say "INSUFFICIENT DEPTH — need more
context or a harder problem." NEVER say "looks good."

Format your response as:
- FLAW: [specific error]
- GAP: [missing consideration]
- ASSUMPTION: [unvalidated claim]
- CONFIDENCE: [0-100] because [reasons]"""
```

### Innovator (Lateral Thinking Department)

- **Model**: Local 1.5B creative model
- **Job**: Propose alternatives the team hasn't considered
- **Trigger**: After Naysayer identifies problems, or on explicit request
- **Anti-pattern**: Repeating what was already proposed

### Stabilizer (Focus Department)

- **Model**: Local 1.5B instruction-following model
- **Job**: Keep the team on scope. Detect drift. Enforce priorities.
- **Trigger**: Continuous. Interrupts when scope violation detected.

### Iterator (Execution Department)

- **Model**: Local coding/extraction model
- **Job**: Implement the agreed approach. Generate code. Run tests.
- **Trigger**: After Naysayer approves (conditionally) and Stabilizer confirms scope

### Connector (Memory Department)

- **Model**: Embedding model + retrieval
- **Job**: Maintain shared context. Link to prior decisions. Surface relevant history.
- **Trigger**: Before every department turn

## 5. The Hardware Reality

| Hardware                     | What it runs                     | Power  | Cost                    |
| ---------------------------- | -------------------------------- | ------ | ----------------------- |
| AMD Ryzen AI NPU (XDNA2)     | 1-2 x 1.5B models simultaneously | 10-15W | Included in $600 laptop |
| Apple M-series Neural Engine | 1-2 x 1.5B models simultaneously | 10-20W | Included in $999 Mac    |
| Intel Core Ultra NPU         | 1 x 1.5B model                   | 10-15W | Included in $700 laptop |
| NVIDIA RTX 4060              | 4-6 x 1.5B models                | 115W   | $300 add-in             |
| Cloud API (per call)         | Frontier model                   | N/A    | $0.01-0.15 per call     |

FastFlowLM proves NPU inference is production-ready. A single laptop can run the entire department layer without a GPU.

## 6. The Protocol

Departments communicate via a **shared blackboard** — a structured message bus:

```python
@dataclass
class DepartmentMessage:
    sender: str          # "naysayer", "innovator", etc.
    turn: int            # sequential turn counter
    message_type: str    # "critique", "proposal", "scope_check", "implementation"
    content: str
    confidence: float    # 0.0-1.0
    references: list[str]  # IDs of messages this responds to
    blocking: bool       # True = stops pipeline until addressed

class Blackboard:
    """Shared state between departments. Append-only log."""
    messages: list[DepartmentMessage]

    def get_context_for(self, department: str, last_n: int = 10) -> str:
        """Each department sees filtered, relevant context."""
        relevant = [m for m in self.messages[-last_n:]
                    if m.sender != department]  # don't repeat own output
        return format_messages(relevant)
```

Turn order is NOT round-robin. It's **event-driven**:

1. User submits task → Blackboard
2. Connector surfaces relevant history
3. Innovator proposes approach (or Iterator drafts)
4. Naysayer critiques
5. Stabilizer checks scope
6. If Naysayer blocks → back to relevant department
7. If all pass → Elite layer reviews (optional)
8. Output delivered

## 7. The Anti-Patterns

**Anti-pattern 1: Democratic voting.** Agents shouldn't vote. They have different expertise. The Naysayer's "no" carries more weight on quality than the Innovator's "yes."

**Anti-pattern 2: Equal context.** Every agent doesn't need every message. The Naysayer doesn't need creative inspiration; it needs the proposed output and the spec.

**Anti-pattern 3: Fixed turn order.** Not every task needs all departments. A quick formatting task shouldn't trigger a full Naysayer review.

**Anti-pattern 4: Cloud-first routing.** The whole point is that 90% of work runs locally on NPUs. Cloud APIs are the exception, not the default.

**Anti-pattern 5: Persistent personality.** Departments aren't chatbots with personas. They're structured functions with defined inputs, outputs, and failure modes.

## 8. The Implementation

```python
class Department:
    """Base class for a department in the agent organization."""

    def __init__(self, name: str, model_path: str, system_prompt: str):
        self.name = name
        self.model = load_gguf_model(model_path, n_ctx=4096)
        self.system_prompt = system_prompt

    def process(self, blackboard: Blackboard) -> DepartmentMessage:
        context = blackboard.get_context_for(self.name)
        response = self.model.chat(
            system=self.system_prompt,
            messages=[{"role": "user", "content": context}]
        )
        return self.parse_output(response)

class NaysayerDepartment(Department):
    def __init__(self):
        super().__init__(
            name="naysayer",
            model_path="models/qwen3-1.7b-q4_k_m.gguf",
            system_prompt=NAYSAYER_SYSTEM
        )

    def parse_output(self, response: str) -> DepartmentMessage:
        flaws = extract_section(response, "FLAW")
        gaps = extract_section(response, "GAP")
        confidence = extract_confidence(response)

        return DepartmentMessage(
            sender="naysayer",
            turn=0,  # set by blackboard
            message_type="critique",
            content=response,
            confidence=confidence,
            references=[],
            blocking=(confidence < 0.5)  # blocks pipeline if low confidence
        )

class AgentOrganization:
    """The full department structure."""

    def __init__(self):
        self.departments = {
            "naysayer": NaysayerDepartment(),
            "innovator": InnovatorDepartment(),
            "stabilizer": StabilizerDepartment(),
            "iterator": IteratorDepartment(),
            "connector": ConnectorDepartment(),
        }
        self.blackboard = Blackboard()
        self.elite = EliteLayer(api_key=get_api_key())  # cloud fallback

    def execute(self, task: str) -> str:
        # Phase 1: Context
        self.departments["connector"].process(self.blackboard)

        # Phase 2: Initial approach
        proposal = self.departments["innovator"].process(self.blackboard)
        self.blackboard.append(proposal)

        # Phase 3: Critique loop
        for _ in range(3):  # max 3 revision cycles
            critique = self.departments["naysayer"].process(self.blackboard)
            self.blackboard.append(critique)

            if not critique.blocking:
                break

            # Revise based on critique
            revision = self.departments["iterator"].process(self.blackboard)
            self.blackboard.append(revision)

        # Phase 4: Scope check
        scope = self.departments["stabilizer"].process(self.blackboard)
        self.blackboard.append(scope)

        # Phase 5: Elite review (if needed)
        if any(m.confidence < 0.7 for m in self.blackboard.messages[-5:]):
            elite_review = self.elite.review(self.blackboard.get_context_for("elite"))
            self.blackboard.append(elite_review)

        return self.blackboard.messages[-1].content
```

## 9. The Economics

For a typical development task (10 department turns):

| Layer             | Calls | Cost/Call         | Total   | Latency    |
| ----------------- | ----- | ----------------- | ------- | ---------- |
| Swarm (<500M)     | 20    | $0.00 (local)     | $0.00   | <50ms each |
| Department (1-2B) | 10    | $0.00 (local/NPU) | $0.00   | 1-5s each  |
| Elite (cloud)     | 0-2   | $0.01-0.15        | $0-0.30 | 5-30s each |

Total: $0.00-0.30 per task vs $0.05-0.50 for single cloud model doing the same work with no adversarial review.

## 10. The Challenges (Draft 1 — Honest Assessment)

**Challenge 1: Small models are genuinely worse.** A 1.5B model will miss things a frontier model catches. The Naysayer department running on a small model might approve bad code because it can't reason well enough to find the flaw. This is the fundamental tension — cheap local models may provide false confidence.

**Challenge 2: Context window limits.** Each department only sees filtered context. Critical information may be filtered out. The Connector department must be excellent at summarization, and small models are bad at summarization.

**Challenge 3: No one has built this end-to-end.** The pieces exist but nobody has combined NPU swarm + structured departments + persistent memory + elite fallback into a working system. There will be integration bugs nobody has encountered yet.

**Challenge 4: Latency stacking.** 3 revision cycles × 2 departments = 6 local model calls. At 2s each, that's 12 seconds before output. Users may not wait.

**Challenge 5: The Naysayer problem.** A sufficiently strict Naysayer blocks everything. A sufficiently lenient Naysayer approves everything. Calibrating "how critical is critical enough" is an unsolved problem.

**Challenge 6: Multi-model coordination is harder than it looks.** Each model has different formatting, different failure modes, different token limits. The blackboard abstraction leaks.

---

_Draft 1 complete. Round 2 will challenge these findings with new research into: failure calibration, small model reasoning limits, and whether departments actually improve output quality vs a single good model._
