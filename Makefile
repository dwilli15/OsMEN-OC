.PHONY: bootstrap test lint typecheck status

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# ---------------------------------------------------------------------------
# bootstrap — first-install / idempotent setup
# ---------------------------------------------------------------------------
bootstrap:
	bash scripts/bootstrap.sh

# ---------------------------------------------------------------------------
# test — run the pytest suite
# ---------------------------------------------------------------------------
test: $(VENV)/bin/pytest
	$(VENV)/bin/pytest tests/ -q --timeout=15

# ---------------------------------------------------------------------------
# lint — ruff code style and import checks
# ---------------------------------------------------------------------------
lint: $(VENV)/bin/ruff
	$(VENV)/bin/ruff check core/ tests/

# ---------------------------------------------------------------------------
# typecheck — mypy static type analysis
# ---------------------------------------------------------------------------
typecheck: $(VENV)/bin/mypy
	$(VENV)/bin/mypy core/ --ignore-missing-imports

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
	@[ -d $(VENV) ] || python3 -m venv $(VENV)
	$(PIP) install --quiet -e ".[dev]"
