# GitHub Agent Operations

This document explains how the OsMEN-OC maintainer works with the GitHub Copilot coding agent: how to shape issues, what the agent is and is not permitted to do, how PRs are reviewed, and the order in which agent-generated PRs are merged.

---

## 1. Purpose

The GitHub Copilot coding agent handles bounded, well-defined implementation tasks while the maintainer focuses on architecture, risk assessment, and final approval. This document is the single source of truth for that collaboration.

---

## 2. Issue Shaping

Every task assigned to the coding agent starts as a GitHub issue using the **Copilot Task** template (`.github/ISSUE_TEMPLATE/copilot-task.yml`).

### Required fields

| Field | Purpose |
|---|---|
| **Summary** | One or two sentences; defines the observable outcome |
| **In Scope** | Explicit list of files/modules the agent may touch |
| **Out of Scope** | Files/modules the agent must not change |
| **Acceptance Criteria** | Numbered, verifiable conditions |
| **Verification Commands** | Exact shell commands; agent must run them and paste output |
| **Risk Level** | Highest risk level among all operations in the task |

### Shaping rules

1. **One concern per issue.** An issue that touches more than three top-level modules is too broad — split it.
2. **No ambiguous verbs.** Write "add", "remove", "rename", "extract", not "improve" or "refactor".
3. **Acceptance criteria are shell-verifiable.** If you can't write a `pytest` assertion or a `grep` check for it, the criterion is too vague.
4. **Declare the risk level up front.** The agent uses this to decide whether to queue tool invocations for human approval.
5. **Never assign critical-risk tasks to the agent without explicit maintainer supervision.** Schedule a live review session instead.

---

## 3. Approval Rules

Approval requirements are enforced by `core/approval/gate.py` at runtime and by the PR review process at development time.

| Risk Level | Agent behaviour | PR review requirement |
|---|---|---|
| `low` | Execute and log | Single maintainer approval |
| `medium` | Execute, log, include in daily summary | Single maintainer approval + passing CI |
| `high` | Queue for human approval via Telegram notification | Maintainer approval + second reviewer if available |
| `critical` | Block until human confirms via Telegram **and** Discord | Must NOT be auto-merged; requires synchronous maintainer review |

### PR approval checklist (maintainer)

Before approving any agent-generated PR:

- [ ] All acceptance criteria from the linked issue are satisfied
- [ ] CI is green (pytest + ruff + mypy — see `.github/workflows/ci.yml`)
- [ ] Scope is contained: no files outside the **In Scope** list were modified
- [ ] No plaintext secrets, no Docker references, no "Jarvis" references
- [ ] For `high`/`critical` tasks: approval gate is wired for every new tool invocation
- [ ] Quadlet changes pin image tags (no `:latest`)

---

## 4. Merge Order

When multiple agent PRs are open at the same time, merge in this order to minimise conflicts:

1. **Infrastructure / quadlet changes** — these rarely conflict with Python code
2. **Core library changes** (`core/`) — other PRs may depend on these
3. **Gateway changes** (`gateway/`) — depends on `core/`
4. **Agent manifest changes** (`agents/`) — purely declarative, low conflict risk
5. **Test-only changes** — merge last to pick up any API changes from earlier PRs
6. **Docs / config changes** — merge any time; no code dependencies

If two PRs in the same category are open, merge the one with lower risk level first.

**Never merge a PR while another PR that touches the same module is open.** Close or pause the second PR first, then rebase it after the first is merged.

---

## 5. What the Agent Must Not Do

The following are hard constraints enforced by code review and CI:

- Introduce Docker Compose files, `.env` files, or `requirements.txt`
- Reference "Jarvis" anywhere
- Use `docker run` or `docker-compose` commands
- Commit plaintext secrets
- Use `:latest` image tags in quadlets
- Bypass `core/approval/gate.py` for tool invocations
- Pass raw `dict` on the event bus (use `EventEnvelope`)
- Split sentences mid-word in `core/memory/chunking.py`
- Change files declared **Out of Scope** in the linked issue

Violations are grounds for immediate PR closure without merge.

---

## 6. CI Pipeline

The CI pipeline (`.github/workflows/ci.yml`) runs on every PR and on every push to `main`:

```
python -m pytest tests/ -q
python -m ruff check core/ tests/
python -m mypy core/ --ignore-missing-imports
```

A failing CI pipeline blocks merge. Do not override CI failures without a documented reason in the PR comments.

---

## 7. Running Checks Locally

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Tests
python -m pytest tests/ -q

# Lint
python -m ruff check core/ tests/

# Type-check
python -m mypy core/ --ignore-missing-imports
```

---

## 8. Escalation

If the agent produces a PR that:

- Fails CI and the fix is not obvious
- Touches files outside its declared scope
- Introduces code that bypasses the approval gate

→ Close the PR, add a comment explaining why, and reshape the issue before re-assigning.

If the same task fails twice, the maintainer should implement it manually.
