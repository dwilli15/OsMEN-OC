# Pull Request

## Summary

<!-- One or two sentences describing what this PR does and why. -->

## Linked Issue

Closes #<!-- issue number -->

## Scope Check

<!-- Confirm the PR stays within the boundaries declared in the linked issue. -->

- [ ] All changed files are listed in the issue's **In Scope** section
- [ ] No files from the issue's **Out of Scope** section were modified
- [ ] No Docker Compose files, `.env` files, or references to "Jarvis" were introduced
- [ ] No new secrets committed in plaintext

## Validation

<!-- Paste the output of each command below. -->

**Tests**
```
python -m pytest tests/ -q
```
<details><summary>Output</summary>

```
<!-- paste output here -->
```
</details>

**Lint**
```
python -m ruff check core/ tests/
```
<details><summary>Output</summary>

```
<!-- paste output here -->
```
</details>

**Type-check**
```
python -m mypy core/ --ignore-missing-imports
```
<details><summary>Output</summary>

```
<!-- paste output here -->
```
</details>

## Checklist

- [ ] CI is green (pytest + ruff + mypy)
- [ ] New or modified code has corresponding tests
- [ ] Async functions use `@pytest.mark.anyio` in tests
- [ ] Pydantic models used for data crossing module boundaries
- [ ] Approval gate (`core/approval/gate.py`) is wired for any new tool invocations
- [ ] No `latest` image tags in any quadlet changes
- [ ] Docs updated if behaviour changed

## Notes for Reviewer

<!-- Anything the reviewer should pay special attention to. -->
