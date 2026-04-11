.PHONY: bootstrap test lint typecheck status dev fmt check up down logs clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PYTHON_REQUIRED := 3.13

# ---------------------------------------------------------------------------
# bootstrap — first-install / idempotent setup
# ---------------------------------------------------------------------------
bootstrap:
	bash scripts/bootstrap.sh

# ---------------------------------------------------------------------------
# test — run the pytest suite
# ---------------------------------------------------------------------------
test: $(VENV)/bin/pytest verify-python
	$(PYTHON) -m pytest tests/ -q --timeout=15

# ---------------------------------------------------------------------------
# lint — ruff code style and import checks
# ---------------------------------------------------------------------------
lint: $(VENV)/bin/ruff verify-python
	$(PYTHON) -m ruff check core/ tests/

# ---------------------------------------------------------------------------
# typecheck — mypy static type analysis
# ---------------------------------------------------------------------------
typecheck: $(VENV)/bin/mypy verify-python
	$(PYTHON) -m mypy core/ --ignore-missing-imports

# ---------------------------------------------------------------------------
# status — show running Podman containers and OpenClaw version
# ---------------------------------------------------------------------------
status:
	@echo "=== Podman containers ==="
	@podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" 2>/dev/null || \
	    echo "(podman not available)"
	@echo ""
	@echo "=== OpenClaw version ==="
	@openclaw --version 2>/dev/null || echo "(openclaw not installed)"
	@echo ""
	@echo "=== Python venv ==="
	@$(PYTHON) --version 2>/dev/null || echo "(venv not created — run: make bootstrap)"

# ---------------------------------------------------------------------------
# Internal: ensure venv tools are available
# ---------------------------------------------------------------------------
$(VENV)/bin/pytest $(VENV)/bin/ruff $(VENV)/bin/mypy: pyproject.toml
	@[ -d $(VENV) ] || python3.13 -m venv $(VENV)
	$(PYTHON) -m pip install --quiet -e ".[dev]"

# ---------------------------------------------------------------------------
# verify-python — fail fast if local venv is not on required interpreter
# ---------------------------------------------------------------------------
verify-python:
	@$(PYTHON) -c 'import sys; req=(3,13); cur=sys.version_info[:2];\
print(f"Python {cur[0]}.{cur[1]}");\
ok=(cur==req);\
print("ERROR: OsMEN-OC requires Python 3.13 in .venv." if not ok else "");\
raise SystemExit(0 if ok else 1)'

# ---------------------------------------------------------------------------
# dev — run gateway with auto-reload (uvicorn)
# ---------------------------------------------------------------------------
dev: $(VENV)/bin/pytest
	$(PYTHON) -m uvicorn core.gateway.app:app --reload --host 127.0.0.1 --port 8080

# ---------------------------------------------------------------------------
# fmt — auto-fix lint issues
# ---------------------------------------------------------------------------
fmt: $(VENV)/bin/ruff
	$(PYTHON) -m ruff check core/ tests/ --fix
	$(PYTHON) -m ruff format core/ tests/

# ---------------------------------------------------------------------------
# check — run test + lint + typecheck in one pass
# ---------------------------------------------------------------------------
check: test lint typecheck

# ---------------------------------------------------------------------------
# up / down / logs — manage Podman quadlet services
# ---------------------------------------------------------------------------
up:
	systemctl --user start osmen-core-redis osmen-core-postgres osmen-core-chromadb 2>/dev/null || \
	    echo "(systemd user units not installed — see quadlets/)"

down:
	systemctl --user stop osmen-core-redis osmen-core-postgres osmen-core-chromadb 2>/dev/null || \
	    echo "(systemd user units not installed)"

logs:
	@journalctl --user -u osmen-core-redis -u osmen-core-postgres -u osmen-core-chromadb \
	    --no-pager -n 50 2>/dev/null || echo "(journalctl not available)"

# ---------------------------------------------------------------------------
# clean — remove build artifacts and caches
# ---------------------------------------------------------------------------
clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache *.egg-info dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
