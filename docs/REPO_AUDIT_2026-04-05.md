# OsMEN-OC Repository Audit (2026-04-05)

## Scope

This audit reviewed the full repository tree (`core/`, `agents/`, `config/`, `scripts/`, `quadlets/`, `timers/`, `tests/`, and `docs/`) with a focus on security, reliability, operational readiness, and testability.

## Methodology

1. **Repository-wide file inventory and spot checks**
2. **Static review of high-risk paths** (tool ingress, pipeline scheduling, bridge/eventing, config loading)
3. **Automated checks where environment allowed**
4. **Cross-check against previous outside audit report**

## Commands executed

- `rg --files -g 'AGENTS.md'`
- `rg --files | head -n 200`
- `pytest -q`
- `ruff check .`
- `mypy core gateway tests`
- `make test`
- `rg -n "TODO|FIXME|XXX|noqa|except Exception|eval\(|subprocess|yaml\.load\(|pickle|md5|shell=True|follow_redirects=True|sleep\(60\)" core tests scripts config docs pyproject.toml`
- Multiple targeted `sed -n` inspections for key modules

## Executive summary

The codebase is in stronger shape than the previous outside audit suggested. Several formerly critical issues are already addressed (URL pre-validation, content-type/size limits, full cron parser integration via `cronsim`, handler errors mapped to HTTP error responses, and async wrappers for Chroma interactions).

However, one **high-priority security issue** remains and two **medium-priority hardening gaps** should be scheduled soon.

---

## Verified findings

### 1) High: Redirect-based SSRF bypass in `ingest_url`

**Status:** Resolved  
**Location:** `core/gateway/builtin_handlers.py`

At the time of audit, the concern was that `ingest_url` validated the *initial* hostname/IP but could follow redirects to private/link-local/internal targets. Upon inspection the handler already uses `follow_redirects=False` and manually re-validates every `Location` hop via `_validate_ingest_url` before issuing the next request. The hop count is capped at `_MAX_REDIRECT_HOPS` (5).

**Regression tests added** (`tests/test_handlers.py`, `TestBuiltinIngestUrl`):
- Redirect to `127.0.0.1` (loopback IP)
- Redirect to `169.254.169.254` (link-local / cloud metadata endpoint)
- Redirect to `10.0.0.1` (RFC1918 class A)
- Redirect to `172.16.0.1` (RFC1918 class B)
- Multi-hop chain terminating at `192.168.0.10` (private)
- Chain exceeding the maximum redirect-hop limit

---

### 2) Medium: Config file path trust boundary is broad

**Status:** Verified  
**Location:** `core/utils/config.py`

`load_config()` accepts absolute or relative paths and resolves relative paths from current working directory without enforcing an allowed root or explicit path allowlist.

**Why this matters:** Today this is mostly internal-call-site controlled, but this becomes risky if a future API/CLI allows external path input.

**Recommendation:**
- Add path confinement to repo root (or explicit trusted directories).
- Reject symlink escapes and unexpected absolute paths unless explicitly whitelisted.

---

### 3) Medium: Tooling/runtime mismatch can block test execution in non-3.13 environments

**Status:** Verified in this environment  
**Location:** `pyproject.toml`, `tests/`, Make targets

Project requires Python 3.13, but in this environment commands executed under Python 3.10 fail collection due to `datetime.UTC` import usage and missing package resolution under bare `pytest` invocation.

**Why this matters:** If CI/automation drifts from 3.13, test signal becomes noisy or unavailable.

**Recommendation:**
- Ensure CI enforces Python 3.13 explicitly.
- Keep invoking tests through the project venv (`make test`) and document a strict interpreter preflight check.

---

## Improvements already present (compared to prior external report)

The following appear fixed in current code:

- URL ingest now enforces hostname/IP pre-validation and response-size/content-type gates.
- Cron matching now uses `cronsim` for full expression semantics.
- Handler execution failures now return explicit HTTP 500 `handler_error` payloads.
- Chroma store calls from handlers are async (`add_documents_async`, `query_async`) rather than blocking the event loop directly.
- Added `/ready` endpoint and `/events/dead-letter` operator endpoint.

---

## Priority action plan

1. **Immediate (P1):** close redirect-based SSRF bypass in `ingest_url`.
2. **Sprint (P2):** constrain config path loading to trusted roots.
3. **Ops hygiene:** enforce Python 3.13 in all automation entry points and CI matrix.
4. **Testing:** add explicit regression tests for redirect-hop validation behavior.
