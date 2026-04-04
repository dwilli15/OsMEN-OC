#!/usr/bin/env bash
# scripts/bootstrap.sh
#
# Master first-install / re-run bootstrap for OsMEN-OC.
# Idempotent: safe to run multiple times on a fresh or existing system.
#
# Prerequisites: Ubuntu 26.04 LTS, user 'armad', sudo-rs available.
#
# Usage:
#   scripts/bootstrap.sh [--skip-apt] [--skip-openclaw] [--dry-run]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
SKIP_APT=false
SKIP_OPENCLAW=false
DRY_RUN=false

# ── Logging helpers ──────────────────────────────────────────────────────────
log_info()  { echo "[INFO]  $*"; }
log_warn()  { echo "[WARN]  $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; exit 1; }

# ── Argument parsing ─────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --skip-apt)      SKIP_APT=true ;;
    --skip-openclaw) SKIP_OPENCLAW=true ;;
    --dry-run)       DRY_RUN=true ;;
    *) log_error "Unknown argument: $arg" ;;
  esac
done

# ── Helper: run or echo depending on dry-run mode ────────────────────────────
run() {
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[DRY-RUN] $*"
  else
    "$@"
  fi
}

# ── Step 1: System packages ───────────────────────────────────────────────────
install_apt_packages() {
  if [[ "${SKIP_APT}" == "true" ]]; then
    log_info "Skipping apt package installation (--skip-apt)."
    return
  fi

  log_info "Installing system packages..."
  run sudo apt-get update -qq
  run sudo apt-get install -y --no-install-recommends \
    python3-dev \
    python3-venv \
    nodejs \
    npm \
    podman \
    podman-compose \
    taskwarrior \
    lm-sensors \
    smartmontools \
    restic \
    age \
    ffmpeg \
    git \
    curl \
    jq
  log_info "System packages installed."
}

# ── Step 2: OpenClaw (control plane dependency) ───────────────────────────────
install_openclaw() {
  if [[ "${SKIP_OPENCLAW}" == "true" ]]; then
    log_info "Skipping OpenClaw installation (--skip-openclaw)."
    return
  fi

  if command -v openclaw &>/dev/null; then
    log_info "OpenClaw already installed: $(openclaw --version 2>/dev/null || true)"
    return
  fi

  log_info "Installing OpenClaw control plane..."
  run npm install -g openclaw
  log_info "OpenClaw installed."
}

# ── Step 3: Python virtualenv ─────────────────────────────────────────────────
setup_python_venv() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    log_info "Creating Python virtual environment at ${VENV_DIR}..."
    run python3 -m venv "${VENV_DIR}"
  else
    log_info "Python venv already exists at ${VENV_DIR}."
  fi

  # Verify pip is usable inside the venv.  On some Ubuntu 26.04 images the
  # python3-venv package ships without ensurepip, leaving pip absent.
  if [[ "${DRY_RUN}" == "false" ]]; then
    if ! "${VENV_DIR}/bin/python" -m pip --version &>/dev/null; then
      log_info "pip not found in venv; attempting to bootstrap via ensurepip..."
      if ! "${VENV_DIR}/bin/python" -m ensurepip --upgrade 2>/dev/null; then
        log_warn "Fix: sudo apt-get install -y python3-pip, then re-run bootstrap."
        log_error "ensurepip is unavailable and pip is missing from the venv."
      fi
    fi
    log_info "pip OK: $("${VENV_DIR}/bin/python" -m pip --version)"
  fi

  log_info "Installing Python package in editable mode (with dev extras)..."
  run "${VENV_DIR}/bin/python" -m pip install --quiet --upgrade pip
  run "${VENV_DIR}/bin/python" -m pip install --quiet -e "${REPO_ROOT}[dev]"
  log_info "Python environment ready."
}

# ── Step 4: Rootless Podman setup ─────────────────────────────────────────────
setup_rootless_podman() {
  log_info "Verifying rootless Podman configuration..."

  local uid
  uid="$(id -u)"
  if ! grep -q "^${USER}:" /etc/subuid 2>/dev/null; then
    log_warn "No subuid entry for ${USER}. Adding one..."
    run sudo usermod --add-subuids 100000-165535 "${USER}"
  fi
  if ! grep -q "^${USER}:" /etc/subgid 2>/dev/null; then
    log_warn "No subgid entry for ${USER}. Adding one..."
    run sudo usermod --add-subgids 100000-165535 "${USER}"
  fi

  log_info "Enabling podman.socket for user session..."
  run systemctl --user enable --now podman.socket || true
  log_info "Rootless Podman configured."
}

# ── Step 5: Deploy Quadlets ───────────────────────────────────────────────────
deploy_quadlets() {
  log_info "Deploying Podman Quadlet units..."
  if [[ "${DRY_RUN}" == "true" ]]; then
    run "${REPO_ROOT}/scripts/deploy_quadlets.sh" --dry-run
  else
    run "${REPO_ROOT}/scripts/deploy_quadlets.sh"
  fi
}

# ── Step 6: Deploy Timers ─────────────────────────────────────────────────────
deploy_timers() {
  log_info "Deploying systemd timers..."
  if [[ "${DRY_RUN}" == "true" ]]; then
    run "${REPO_ROOT}/scripts/deploy_timers.sh" --dry-run
  else
    run "${REPO_ROOT}/scripts/deploy_timers.sh"
  fi
}

# ── Step 7: SOPS / age secrets ────────────────────────────────────────────────
deploy_secrets() {
  local age_key="${HOME}/.config/sops/age/keys.txt"
  if [[ ! -f "${age_key}" ]]; then
    log_warn "age key not found at ${age_key}. Skipping secret decryption."
    log_warn "Generate a key with: age-keygen -o ${age_key}"
    return
  fi

  log_info "Decrypting SOPS secrets..."
  local secrets_dir="${REPO_ROOT}/config/secrets"
  local dest_dir="${HOME}/.config/osmen/secrets"
  run mkdir -p "${dest_dir}"

  for enc_file in "${secrets_dir}"/*.enc.yaml; do
    [[ -e "${enc_file}" ]] || continue
    local base
    base="$(basename "${enc_file}" .enc.yaml)"
    log_info "  Decrypting ${base}.enc.yaml → ${dest_dir}/${base}.env"
    if [[ "${DRY_RUN}" == "false" ]]; then
      sops --decrypt --output-type dotenv "${enc_file}" \
          > "${dest_dir}/${base}.env" || log_warn "Failed to decrypt ${enc_file}"
    else
      echo "[DRY-RUN] sops --decrypt --output-type dotenv ${enc_file} > ${dest_dir}/${base}.env"
    fi
  done
  log_info "Secrets decrypted."
}

# ── Step 8: Start core services ───────────────────────────────────────────────
start_core_services() {
  log_info "Starting core services (postgres, redis, chromadb)..."
  run systemctl --user start \
    osmen-core-postgres \
    osmen-core-redis \
    osmen-core-chromadb || true

  log_info "Waiting for services to become healthy (up to 60s)..."
  local start_seconds=${SECONDS}
  local all_healthy=false
  while [[ $(( SECONDS - start_seconds )) -lt 60 ]]; do
    if systemctl --user is-active --quiet osmen-core-postgres \
       && systemctl --user is-active --quiet osmen-core-redis \
       && systemctl --user is-active --quiet osmen-core-chromadb; then
      all_healthy=true
      break
    fi
    sleep 3
  done

  if [[ "${all_healthy}" == "false" ]]; then
    log_warn "Not all core services reported active within 60s. Check with:"
    log_warn "  systemctl --user status osmen-core-postgres osmen-core-redis osmen-core-chromadb"
  else
    log_info "All core services active."
  fi
}

# ── Step 9: SQL migrations ────────────────────────────────────────────────────
run_migrations() {
  local migrations_dir="${REPO_ROOT}/migrations"
  if [[ ! -d "${migrations_dir}" ]]; then
    log_info "No migrations/ directory found — skipping."
    return
  fi

  log_info "Running SQL migrations..."
  for sql_file in "${migrations_dir}"/[0-9]*.sql; do
    [[ -e "${sql_file}" ]] || continue
    local migration_name
    migration_name="$(basename "${sql_file}")"
    log_info "  Applying ${migration_name}..."
    run podman exec -i osmen-core-postgres \
        psql -U "${POSTGRES_USER:-osmen}" -d "${POSTGRES_DB:-osmen}" \
        < "${sql_file}" || log_warn "Migration ${migration_name} failed (may already be applied)"
  done
  log_info "Migrations complete."
}

# ── Step 10: Final verification ───────────────────────────────────────────────
verify_installation() {
  log_info "Final verification..."
  if command -v podman &>/dev/null; then
    log_info "Podman containers:"
    podman ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || true
  fi
  if command -v openclaw &>/dev/null; then
    log_info "OpenClaw version: $(openclaw --version 2>/dev/null || echo 'unknown')"
  else
    log_warn "openclaw not found in PATH."
  fi
  log_info "Bootstrap complete."
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  log_info "=== OsMEN-OC Bootstrap ==="
  if [[ "${DRY_RUN}" == "true" ]]; then
    log_warn "Dry-run mode: most commands will only be echoed."
  fi

  install_apt_packages
  install_openclaw
  setup_python_venv
  setup_rootless_podman
  deploy_quadlets
  deploy_timers
  deploy_secrets

  if [[ "${DRY_RUN}" == "false" ]]; then
    start_core_services
    run_migrations
    verify_installation
  fi

  log_info "=== Bootstrap finished successfully ==="
}

main "$@"
