# Agent Departments: A Manifesto

## Draft 3 — Failure Modes and Measurable Reality

### Round 3 Self-Critique

Draft 2 added calibration and cascade errors. What it didn't address:

1. **No empirical evidence** that departmental AI actually outperforms single-model on real tasks
2. **No measurement framework** — how would you even know if departments are helping?
3. **The "soviet factory" problem** — departments optimizing their own metrics while the overall output degrades

This draft confronts the measurement gap directly.

---

## 9. The Measurement Problem (New Section)

There is no benchmark for "departmental AI quality." Existing benchmarks measure single-model performance on single tasks. Multi-agent quality is a different dimension entirely:

| What to measure      | How                                          | Difficulty    |
| -------------------- | -------------------------------------------- | ------------- |
| Final output quality | Human rating vs single-model baseline        | Easy but slow |
| Flaw detection rate  | Inject known flaws, measure detection        | Medium        |
| False positive rate  | Present known-good work, measure rejections  | Medium        |
| Cascade error rate   | Give wrong premise, measure propagation      | Hard          |
| Latency per task     | Wall clock from input to approved output     | Easy          |
| Cost per task        | Token/energy cost vs single-model equivalent | Easy          |
| Scope adherence      | Measure output against original spec         | Hard          |

**The minimum viable measurement**:

```python
@dataclass
class TaskResult:
    task_id: str
    approach: str          # "single-model" or "departmental"
    model_config: str      # what models were used

    # Quality metrics (human-rated 1-5)
    correctness: float     # Does it work?
    completeness: float    # Are edge cases handled?
    clarity: float         # Is it understandable?

    # Process metrics
    total_latency_ms: int
    total_cost_usd: float
    revision_count: int    # How many cycles before approval
    cascade_errors: int    # Times departments built on wrong foundation

    # Department metrics
    naysayer_false_positives: int   # rejected good work
    naysayer_false_negatives: int   # approved bad work
    innovator_novelty_score: float  # did it propose something new?
    stabilizer_drift_events: int    # times scope was violated

class ExperimentRunner:
    """A/B test: single model vs departmental organization."""

    def run_comparison(self, tasks: list[str], n: int = 50):
        results = []
        for task in tasks[:n]:
            # Single model baseline
            single = self.run_single_model(task)

            # Departmental approach
            dept = self.run_departmental(task)

            # Human-blind rating (both outputs shown in random order)
            rating = human_preference(single.output, dept.output)

            results.append(TaskResult(
                task_id=hash(task),
                approach="comparison",
                model_config=self.config_summary(),
                correctness=rating.correctness,
                completeness=rating.completeness,
                clarity=rating.clarity,
                total_latency_ms=dept.latency_ms,
                total_cost_usd=dept.cost_usd,
                revision_count=dept.revisions,
                cascade_errors=dept.cascades,
                naysayer_false_positives=dept.naysayer_fp,
                naysayer_false_negatives=dept.naysayer_fn,
                innovator_novelty_score=dept.innovation_score,
                stabilizer_drift_events=dept.drift_count,
            ))

        return results
```

**Honest assessment**: Nobody has run this experiment. Not with small local models. Not with structured departments. Every claim about multi-agent superiority is either theoretical or tested only with cloud APIs (Quorum). The NPU/department combo is unproven.

---

## 10. The Soviet Factory Problem

Each department optimizes for its own metric:

- Naysayer optimizes for "flaws found" → rejects everything
- Innovator optimizes for "novelty" → proposes infeasible ideas
- Stabilizer optimizes for "scope adherence" → blocks all expansion
- Iterator optimizes for "code written" → ships first draft

**Solution**: Departments don't have independent metrics. They share one metric: **final output quality as rated by the human**. No department gets credit for its intermediate output. The organization succeeds or fails together.

Implementation:

```python
class OrganizationalGoal:
    """All departments share the same success criteria."""

    success_metric: str = "human_satisfaction"  # 1-5 rating
    failure_threshold: float = 2.5              # below this = organizational failure

    def evaluate(self, output: str, spec: str) -> float:
        """
        Not per-department evaluation.
        The whole organization gets one score.
        """
        return self.human_rating(output, spec)
```

This mirrors how real organizations work: the QA department doesn't get credit for finding bugs if the product fails. The engineering team doesn't get credit for elegant code if it solves the wrong problem.

---

## 11. The Cascade Error Mitigation (Expanded)

Draft 2 identified cascade errors. Here's the mitigation strategy:

**Principle: Foundation checks before parallel execution.**

```python
class FoundationCheck:
    """Run BEFORE any department does substantive work."""

    def check(self, task: str, context: str) -> FoundationResult:
        # The Memory department's context retrieval is the most common
        # cascade source. Verify it before proceeding.

        checks = {
            "context_relevance": self.verify_context_relevance(task, context),
            "premise_validity": self.verify_premise(task),
            "scope_clarity": self.verify_scope(task),
        }

        return FoundationResult(
            safe=all(checks.values()),
            failed_checks=[k for k, v in checks.items() if not v],
            recommendation="proceed" if all(checks.values()) else "escalate_to_elite"
        )

    def verify_context_relevance(self, task: str, context: str) -> bool:
        """Cheap embedding similarity check. If context is unrelated, flag it."""
        task_embedding = self.embed(task)
        context_embedding = self.embed(context)
        similarity = cosine_similarity(task_embedding, context_embedding)
        return similarity > 0.3  # threshold from empirical testing

    def verify_premise(self, task: str) -> bool:
        """Ask a small model: 'Does this task contain assumptions that
        could be wrong?' If yes, escalate before executing."""
        response = self.small_model.chat(
            system="Answer only YES or NO. Is there an assumption in this "
                   "task that could be factually wrong?",
            messages=[{"role": "user", "content": task}]
        )
        return "NO" in response.upper()  # if YES, premise is questionable
```

**The 10% rule**: Spend 10% of total inference budget on verification. If the task costs 1000 tokens of department work, spend 100 tokens checking that the departments are working on the right thing.

---

## 12. OpenClaw as the Operating System

OpenClaw already implements 80% of the infrastructure needed:

| Manifesto Requirement         | OpenClaw Implementation                | Status           |
| ----------------------------- | -------------------------------------- | ---------------- |
| Multiple agents with identity | `openclaw agents add` with IDENTITY.md | ✅ Works         |
| Department role assignment    | SOUL.md per agent workspace            | ✅ Works         |
| Shared memory                 | `memory/` directory + embedding search | ✅ Works         |
| Channel routing               | `openclaw agents bind discord`         | ✅ Works         |
| Agent-to-agent communication  | `agentToAgent: enabled`                | ✅ Config exists |
| Discord as blackboard         | Full Discord bot with streaming        | ✅ Works         |
| Elite fallback                | Multi-model routing (ZAI + Copilot)    | ✅ Works         |
| Swarm layer (small models)    | Ollama integration + local models      | ✅ Works         |
| Structured turn-taking        | Configurable `replyToMode`             | ⚠️ Partial       |
| Foundation checks             | Not implemented                        | ❌ Missing       |
| Calibration loop              | Not implemented                        | ❌ Missing       |
| Quality measurement           | Not implemented                        | ❌ Missing       |
| Cross-department weighting    | Not implemented                        | ❌ Missing       |

The missing 20% is: foundation checks, calibration, measurement, and weighting. These are the hard problems that determine whether departmental AI actually works or is just expensive overhead.

---

## 13. The Honest Cost Model

For a 10-turn departmental task on local hardware:

| Component                    | Inference Calls | Tokens      | Time     | Cost      |
| ---------------------------- | --------------- | ----------- | -------- | --------- |
| Foundation check             | 3 (small)       | 500         | 2s       | $0.00     |
| Memory retrieval             | 1 (embed)       | 200         | 0.1s     | $0.00     |
| Innovator proposal           | 1 (1.7B)        | 1500        | 3s       | $0.00     |
| Naysayer checklist (7 items) | 7 (1.7B)        | 3500        | 14s      | $0.00     |
| Revision (if needed)         | 2 (1.7B)        | 3000        | 6s       | $0.00     |
| Stabilizer scope check       | 1 (1B)          | 500         | 1s       | $0.00     |
| Elite review (10% of tasks)  | 0.1 (cloud)     | 2000        | 5s       | $0.01     |
| **Total**                    | **~15 calls**   | **~11,200** | **~31s** | **$0.01** |

Comparable single cloud model (Claude Opus):

- 1 call, ~3000 tokens, ~5s, $0.05

**Departmental costs more time (31s vs 5s) but less money ($0.01 vs $0.05) and provides structured adversarial review that the single model doesn't.**

Is the 6x latency increase worth the 5x cost reduction + quality assurance? That depends on the task. For real-time chat: no. For code review, architecture decisions, documentation: probably yes.

---

_Draft 3 complete. Round 4 will research: practical deployment patterns, the role of Discord/webhook identity in departmental output, and emerging patterns from agent orchestration frameworks (CrewAI, LangGraph)._
