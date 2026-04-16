# Agent Departments: A Manifesto

## Draft 2 — Challenging the Premises

### Round 2 Self-Critique

Draft 1 assumed: (1) small models can critique effectively, (2) the architecture is sound, (3) the main challenge is integration. Draft 2 challenges all three.

**Premise 1 challenged**: Can a 1.5B model actually do useful critique?

Reality: Qwen3-1.7B and Phi-4-mini (3.8B) are the best small reasoning models available. Qwen3-1.7B has thinking tokens — it can chain-reason. LFM2.5-1.2B-Thinking does the same. But: none of these models have been benchmarked specifically for critique quality. There's no "Critical Reasoning Benchmark for Sub-2B Models." We're extrapolating from general benchmarks.

**Insight**: The Naysayer department doesn't need to be smart. It needs to be _structured_. A dumb model with a rigorous checklist outperforms a smart model giving casual review.

**Premise 2 challenged**: Is the layered architecture actually correct?

Reality: Tiny-MoA proved that a 1.2B "Brain" can route to a 600M Reasoner. But routing accuracy drops sharply on ambiguous tasks. The department model assumes clean separation of concerns — real tasks don't respect department boundaries.

**Premise 3 challenged**: Is integration really the only missing piece?

Reality: The deeper problem is **shared state representation**. Each model encodes knowledge differently. When the Naysayer says "this function has a race condition," the Iterator needs to understand _which function_ and _what kind of race_. Cross-model semantic alignment is unsolved.

---

## Revised Manifesto (Draft 2)

### 1. Single-Model AI Is Structurally Bankrupt

Not because models are bad, but because the organizational pattern is wrong. One entity planning, executing, reviewing, and approving its own work has no internal pressure toward quality. This isn't a model capability problem — it's an organizational design problem.

The proof: Quorum (86★) shows that even having two mediocre models argue produces better results than one excellent model working alone. The debate structure, not model quality, drives the improvement.

### 2. The Correct Unit Is the Department, Not the Agent

An "agent" is too general. A "department" has:

- A defined function (not a persona)
- Structured input/output contracts
- Explicit failure modes
- Accountability for specific quality dimensions

```python
from dataclasses import dataclass
from enum import Enum

class DepartmentRole(Enum):
    CRITIQUE = "critique"       # Finds flaws, never approves first pass
    INNOVATION = "innovation"   # Proposes alternatives, breaks assumptions
    STABILITY = "stability"     # Enforces scope, prevents drift
    EXECUTION = "execution"     # Implements, tests, iterates
    MEMORY = "memory"           # Maintains context, surfaces history

@dataclass
class DepartmentSpec:
    role: DepartmentRole
    min_model_size: str         # "1.5B" — minimum for reliable output
    recommended_model: str      # "qwen3-1.7b-thinking"
    context_window: int         # tokens needed
    max_latency_ms: int         # acceptable response time
    failure_mode: str           # what "going wrong" looks like
    accountability: str         # what this department owns

DEPARTMENTS = {
    DepartmentRole.CRITIQUE: DepartmentSpec(
        role=DepartmentRole.CRITIQUE,
        min_model_size="1.5B",
        recommended_model="qwen3-1.7b-thinking",
        context_window=4096,
        max_latency_ms=5000,
        failure_mode="Approves bad work or rejects everything",
        accountability="Output accuracy, edge case coverage, logical soundness"
    ),
    DepartmentRole.INNOVATION: DepartmentSpec(
        role=DepartmentRole.INNOVATION,
        min_model_size="1.5B",
        recommended_model="phi-4-mini-instruct",
        context_window=4096,
        max_latency_ms=3000,
        failure_mode="Repeats existing proposals or proposes infeasible ideas",
        accountability="Alternative approaches, assumption challenging"
    ),
    DepartmentRole.STABILITY: DepartmentSpec(
        role=DepartmentRole.STABILITY,
        min_model_size="500M",
        recommended_model="gemma-3-1b-it",
        context_window=2048,
        max_latency_ms=2000,
        failure_mode="Blocks all work as 'out of scope' or allows all drift",
        accountability="Scope adherence, priority enforcement, time management"
    ),
    DepartmentRole.EXECUTION: DepartmentSpec(
        role=DepartmentRole.EXECUTION,
        min_model_size="1.5B",
        recommended_model="qwen3-1.7b-thinking",
        context_window=8192,
        max_latency_ms=10000,
        failure_mode="Produces code that doesn't match the agreed approach",
        accountability="Working implementation, test coverage, code quality"
    ),
    DepartmentRole.MEMORY: DepartmentSpec(
        role=DepartmentRole.MEMORY,
        min_model_size="100M",
        recommended_model="nomic-embed-text",
        context_window=8192,
        max_latency_ms=500,
        failure_mode="Surfaces irrelevant context or misses critical history",
        accountability="Context relevance, decision continuity, knowledge persistence"
    ),
}
```

### 3. The Naysayer Is the Most Important Department

Not because criticism is inherently valuable, but because LLMs have a structural bias toward agreement and sycophancy. Research consistently shows models tell users what they want to hear. The Naysayer department exists specifically as a structural countermeasure.

The Naysayer is not a "devil's advocate persona." It is a **verification pipeline**:

```python
class NaysayerPipeline:
    """Structured critique that doesn't depend on model brilliance."""

    CHECKLIST = [
        "Does every function have defined input/output types?",
        "Are all error paths handled? List them.",
        "What happens with empty input? Null input? Malformed input?",
        "Name one assumption the implementation makes that isn't in the spec.",
        "What is the worst-case performance? Not average — worst.",
        "If this fails in production, what is the blast radius?",
        "What test case would break this that the author didn't write?",
    ]

    def review(self, proposal: str, spec: str) -> CritiqueResult:
        # Run each checklist item as a separate inference call
        # Small models handle structured checklist items well
        # even when they fail at open-ended critique
        findings = []
        for item in self.CHECKLIST:
            response = self.model.chat(
                system="Answer only with the specific finding. No preamble.",
                messages=[{"role": "user",
                          "content": f"Spec: {spec}\nImplementation: {proposal}\n\n{item}"}]
            )
            findings.append(response)

        return CritiqueResult(
            findings=[f for f in findings if not f.startswith("No ")],
            passed=len([f for f in findings if f.startswith("No ")]) >= 5,
            # >= 5 "No issues found" out of 7 checklist items = conditional pass
        )
```

**Key insight from Round 2**: The checklist approach makes small models viable for critique. A 1.7B model answering "what test case would break this?" produces useful output. The same model asked "review this code" produces generic garbage. Structure compensates for capability.

### 4. The Hardware Thesis Is Real

FastFlowLM + NPU hardware numbers from Draft 1 are confirmed. But there's a nuance: NPU model switching has latency. You can't run 4 models simultaneously on one NPU — you time-slice them. FastFlowLM's `flm serve` switches models automatically, but switching takes 2-5 seconds.

**Revised architecture**: Run the Memory department (embedding model) continuously on NPU. Time-slice the other departments. The Stabilizer and Naysayer can share a model — they never run concurrently (Stabilizer runs pre-task, Naysayer runs post-draft).

```
NPU Time-Slice:
Slot 1 (persistent): nomic-embed-text (Memory department)
Slot 2 (shared):     qwen3-1.7b (Stabilizer → Naysayer → Innovator → Iterator)
                    Switches model input, not model weights
                    Stays hot — 2s switching becomes 0s

Elite Layer (rare):  Cloud API call only when confidence < threshold
```

### 5. The Blackboard Protocol Needs Weighting

Draft 1's blackboard treated all messages equally. Wrong. Different departments have different authority domains:

```python
@dataclass
class WeightedMessage(DepartmentMessage):
    authority_domain: str    # "quality", "scope", "feasibility", "memory"
    weight: float           # 0.0-1.0, how much this department's opinion counts

AUTHORITY = {
    # Domain:        (primary_authority, secondary)
    "quality":       ("naysayer", 0.8, "innovator", 0.3),
    "scope":         ("stabilizer", 0.9, "naysayer", 0.2),
    "feasibility":   ("execution", 0.7, "naysayer", 0.5),
    "alternatives":  ("innovator", 0.8, "memory", 0.4),
    "history":       ("memory", 1.0, "none", 0.0),
}
```

The Naysayer has 0.8 authority on quality. The Innovator has 0.3. This isn't democracy — it's weighted expertise.

### 6. The Real Challenge: Calibration

Draft 1 identified "the Naysayer problem" — too strict or too lenient. Draft 2 adds: **this is the single hardest problem and nobody has solved it.**

Calibration approaches to explore:

- **Threshold tuning**: Start strict, loosen based on false rejection rate
- **Elite calibration**: Periodically send Naysayer + Elite review of same output; measure agreement
- **Empirical baselines**: Run Naysayer on known-good and known-bad outputs; find the natural threshold

```python
class NaysayerCalibration:
    """Self-tuning critique strictness."""

    def __init__(self):
        self.false_rejection_rate = 0.0  # rejected good work
        self.false_approval_rate = 0.0   # approved bad work
        self.threshold = 0.5

    def calibrate(self, elite_judgment: bool, naysayer_judgment: bool):
        """After elite review, compare with naysayer's call."""
        if elite_judgment and not naysayer_judgment:
            self.false_rejection_rate += 0.1
        if not elite_judgment and naysayer_judgment:
            self.false_approval_rate += 0.1

        # Adjust threshold toward the axis with more errors
        if self.false_rejection_rate > self.false_approval_rate:
            self.threshold = max(0.3, self.threshold - 0.05)  # loosen
        elif self.false_approval_rate > self.false_rejection_rate:
            self.threshold = min(0.8, self.threshold + 0.05)  # tighten
```

### 7. The Failure Mode Nobody Talks About: Cascade Errors

If the Memory department surfaces wrong context, the Innovator proposes a flawed approach, the Naysayer critiques the right things about the wrong problem, the Stabilizer keeps scope on a task that shouldn't exist, and the Iterator perfectly implements garbage.

**This is the real risk of multi-agent systems.** Not that individual departments fail — but that they fail _coherently_, all working correctly on a wrong foundation.

Mitigation: The Elite layer's job isn't to do the work. It's to **spot cascade errors** — to check whether the foundation assumptions are correct before all departments execute in parallel on a bad premise.

### 8. Why Discord (or Any Chat) Is the Right Interface

Not because chat is trendy. Because:

- Thread-based conversations provide natural context grouping
- @mentions provide explicit routing (who should respond)
- Reactions provide lightweight feedback (the Naysayer can 👎 without writing a paragraph)
- History is append-only, which is the correct model for a blackboard
- Multiple identities (bots) with different names and avatars makes department output traceable
- Humans participate naturally — same interface, same rules

The protocol is: **a Discord channel IS the blackboard.**

---

_Draft 2 complete. Round 3 will research: cascade error mitigation strategies, multi-model semantic alignment, and whether departmental AI actually improves output quality in measurable ways._
