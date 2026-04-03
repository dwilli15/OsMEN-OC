#!/usr/bin/env bash
# scripts/bootstrap.sh — OsMEN-OC first-install bootstrap
# Idempotent: safe to run multiple times on the same machine.
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_info()  { echo "[bootstrap] INFO  $*"; }
log_warn()  { echo "[bootstrap] WARN  $*" >&2; }
log_error() { echo "[bootstrap] ERROR $*" >&2; }

require_cmd() {
    command -v "$1" &>/dev/null || {
        log_error "Required command '$1' not found. Aborting."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Resolve repository root (works from any directory)
# ---------------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
log_info "Repository root: $REPO_ROOT"

# ---------------------------------------------------------------------------
# Step 1 — System packages
# ---------------------------------------------------------------------------
log_info "Installing system packages..."
PACKAGES=(
    python3-dev python3-venv
    nodejs npm
    podman
    taskwarrior
    lm-sensors smartmontools
    restic
    age
    ffmpeg
    git curl
)

if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends "${PACKAGES[@]}" || \
        log_warn "Some packages may have failed — continuing."
else
    log_warn "apt-get not found; skipping system package installation."
fi

# ---------------------------------------------------------------------------
# Step 2 — OpenClaw (control-plane dependency)
# ---------------------------------------------------------------------------
log_info "Installing OpenClaw (control plane)..."
if command -v npm &>/dev/null; then
    if ! command -v openclaw &>/dev/null; then
        npm install -g openclaw || log_warn "openclaw install failed — may not be published yet."
    else
        log_info "openclaw already installed: $(openclaw --version 2>/dev/null || true)"
    fi
else
    log_warn "npm not found; skipping OpenClaw installation."
fi

# ---------------------------------------------------------------------------
# Step 3 — Python virtual environment
# ---------------------------------------------------------------------------
VENV_DIR="$REPO_ROOT/.venv"
log_info "Setting up Python virtual environment at $VENV_DIR..."
require_cmd python3

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

log_info "Installing Python package in editable mode with dev extras..."
pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"

# ---------------------------------------------------------------------------
# Step 4 — Verify Podman rootless prerequisites
# ---------------------------------------------------------------------------
log_info "Checking Podman rootless prerequisites..."
if command -v podman &>/dev/null; then
    SUBUID_OK=false
    SUBGID_OK=false
    CURRENT_USER="${USER:-$(id -un)}"

    grep -q "^${CURRENT_USER}:" /etc/subuid 2>/dev/null && SUBUID_OK=true
    grep -q "^${CURRENT_USER}:" /etc/subgid 2>/dev/null && SUBGID_OK=true

    if $SUBUID_OK && $SUBGID_OK; then
        log_info "Podman rootless prerequisites OK (subuid/subgid configured)."
    else
        log_warn "Podman rootless not fully configured for user '${CURRENT_USER}'."
        log_warn "Run: sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 ${CURRENT_USER}"
        log_warn "Continuing — some quadlet services may not start."
    fi

    # Enable podman.socket for user session if systemd is available
    if command -v systemctl &>/dev/null && systemctl --user &>/dev/null 2>&1; then
        systemctl --user enable --now podman.socket 2>/dev/null || \
            log_warn "Could not enable podman.socket for user session."
    fi
else
    log_warn "podman not found; skipping rootless prerequisite check."
fi

# ---------------------------------------------------------------------------
# Step 5 — Deploy Quadlets
# ---------------------------------------------------------------------------
log_info "Deploying systemd Quadlets..."
if [ -f "$REPO_ROOT/scripts/deploy_quadlets.sh" ]; then
    bash "$REPO_ROOT/scripts/deploy_quadlets.sh"
else
    log_warn "deploy_quadlets.sh not found; skipping Quadlet deployment."
fi

# ---------------------------------------------------------------------------
# Step 6 — SOPS secrets (optional, requires age key)
# ---------------------------------------------------------------------------
AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
if [ -f "$AGE_KEY_FILE" ]; then
    log_info "age key found at $AGE_KEY_FILE — secrets can be decrypted."
else
    log_warn "age key not found at $AGE_KEY_FILE."
    log_warn "Encrypted config/secrets/ files will not be decrypted until the key is present."
fi

# ---------------------------------------------------------------------------
# Step 7 — Verify core services (advisory, non-fatal)
# ---------------------------------------------------------------------------
log_info "Checking core service availability (advisory)..."
for svc in osmen-core-postgres osmen-core-redis osmen-core-chromadb; do
    if command -v podman &>/dev/null && podman ps --filter "name=${svc}" --format "{{.Names}}" 2>/dev/null | grep -q "${svc}"; then
        log_info "  ✓ ${svc} is running"
    else
        log_warn "  ✗ ${svc} is not running (start with: systemctl --user start ${svc})"
    fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
log_info "Bootstrap complete."
log_info "Next steps:"
log_info "  1. Activate venv:  source .venv/bin/activate"
log_info "  2. Run tests:      python -m pytest tests/ -q"
log_info "  3. Start services: systemctl --user start osmen-core-postgres osmen-core-redis"
