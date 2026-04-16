#!/usr/bin/env bash
# scripts/deploy_quadlets.sh
#
# Deploys rootless Podman Quadlet unit files from quadlets/ into the
# systemd user unit directory (~/.config/containers/systemd/) and triggers
# a daemon-reload so the new or updated units are immediately visible.
#
# Idempotent: safe to run multiple times.  Existing symlinks are replaced
# atomically so a running daemon never sees a partially-written file.
#
# Usage:
#   scripts/deploy_quadlets.sh [--dry-run]
#
# Compatibility notes:
#   - Requires Podman >= 4.4.0 (Quadlet support built-in).
#   - "podman systemd --help" documents the $QUADLET_SEARCH_DIRS env var used
#     by the quadlet generator; we rely on the standard user search path
#     (~/.config/containers/systemd/) so no extra env is needed.
#   - "systemd-analyze verify" is run on every deployed unit where available;
#     failures are reported as warnings, not fatal errors, to support hosts
#     where systemd-analyze is not installed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUADLETS_SRC="${REPO_ROOT}/quadlets"
QUADLET_DEST="${HOME}/.config/containers/systemd"
DRY_RUN=false

# ── Logging helpers ──────────────────────────────────────────────────────────
log_info()  { echo "[INFO]  $*"; }
log_warn()  { echo "[WARN]  $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

# ── Argument parsing ─────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *) log_error "Unknown argument: $arg"; exit 1 ;;
  esac
done

# ── Prerequisite checks ──────────────────────────────────────────────────────
check_prerequisites() {
  if ! command -v podman &>/dev/null; then
    log_error "podman is not installed or not in PATH."
    exit 1
  fi

  local podman_version
  podman_version=$(podman --version | awk '{print $3}')
  log_info "Podman version: ${podman_version}"

  if ! command -v systemctl &>/dev/null; then
    log_error "systemctl is not available. Quadlets require a systemd user session."
    exit 1
  fi

  if [[ ! -d "${QUADLETS_SRC}" ]]; then
    log_error "quadlets/ directory not found at: ${QUADLETS_SRC}"
    exit 1
  fi
}

# ── Ensure destination directory exists ──────────────────────────────────────
ensure_dest_dir() {
  if [[ ! -d "${QUADLET_DEST}" ]]; then
    log_info "Creating ${QUADLET_DEST}"
    if [[ "${DRY_RUN}" == "false" ]]; then
      mkdir -p "${QUADLET_DEST}"
    fi
  fi
}

# ── Deploy (symlink) all quadlet files ───────────────────────────────────────
deploy_units() {
  local deployed=0
  local skipped=0

  # Walk every supported quadlet extension under quadlets/.
  while IFS= read -r -d '' unit_file; do
    local unit_name
    unit_name="$(basename "${unit_file}")"
    local link_target="${QUADLET_DEST}/${unit_name}"

    if [[ -L "${link_target}" ]] && [[ "$(readlink -f "${link_target}")" == "$(realpath "${unit_file}")" ]]; then
      log_info "Up-to-date: ${unit_name}"
      (( skipped++ )) || true
      continue
    fi

    log_info "Linking: ${unit_name} → ${link_target}"
    if [[ "${DRY_RUN}" == "false" ]]; then
      ln -sf "$(realpath "${unit_file}")" "${link_target}"
    fi
    (( deployed++ )) || true

    # Syntax-check via systemd-analyze if available.
    if command -v systemd-analyze &>/dev/null && [[ "${DRY_RUN}" == "false" ]]; then
      if ! systemd-analyze verify "${link_target}" 2>/dev/null; then
        log_warn "systemd-analyze verify reported issues for ${unit_name} (non-fatal)"
      fi
    fi
  done < <(find "${QUADLETS_SRC}" \
    \( -name "*.container" -o -name "*.network" -o -name "*.volume" \
<<<<<<< HEAD
       -o -name "*.pod"     -o -name "*.slice"  -o -name "*.service" \) \
=======
       -o -name "*.pod"     -o -name "*.slice"  \) \
>>>>>>> origin/main
    -print0)

  log_info "Deployed: ${deployed}  Already up-to-date: ${skipped}"
}

# ── Reload systemd user daemon ───────────────────────────────────────────────
reload_daemon() {
  log_info "Running: systemctl --user daemon-reload"
  if [[ "${DRY_RUN}" == "false" ]]; then
    systemctl --user daemon-reload
  fi
  log_info "Daemon reload complete."
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  log_info "=== OsMEN-OC Quadlet Deploy ==="
  if [[ "${DRY_RUN}" == "true" ]]; then
    log_warn "Dry-run mode: no files will be written."
  fi

  check_prerequisites
  ensure_dest_dir
  deploy_units
  reload_daemon

  log_info "=== Done. Core Quadlet units are registered with systemd. ==="
  log_info "To start core services run:"
  log_info "  systemctl --user start osmen-core-postgres osmen-core-redis osmen-core-chromadb"
}

main "$@"
