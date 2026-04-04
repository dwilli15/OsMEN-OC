#!/usr/bin/env bash
# scripts/deploy_timers.sh
#
# Deploys systemd timer + service unit pairs from timers/ into the user-level
# systemd unit directory (~/.config/systemd/user/) and enables/starts all
# timer units.
#
# Idempotent: safe to run multiple times.  Existing symlinks are replaced
# atomically.
#
# Usage:
#   scripts/deploy_timers.sh [--dry-run]
#
# Compatibility notes:
#   - "podman systemd --help" — timer units are plain systemd units (not Quadlet
#     units), so they do NOT live under ~/.config/containers/systemd/.  They
#     are deployed to ~/.config/systemd/user/ so systemd's user session picks
#     them up directly without involving the Podman Quadlet generator.
#   - Syntax validation: "bash -n scripts/deploy_timers.sh" checks this script.
#     For the unit files themselves "systemd-analyze verify <unit>" is run where
#     systemd-analyze is available; failures are warnings, not errors.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMERS_SRC="${REPO_ROOT}/timers"
TIMER_DEST="${HOME}/.config/systemd/user"
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
  if ! command -v systemctl &>/dev/null; then
    log_error "systemctl is not available. Timer deployment requires a systemd user session."
    exit 1
  fi

  if [[ ! -d "${TIMERS_SRC}" ]]; then
    log_error "timers/ directory not found at: ${TIMERS_SRC}"
    exit 1
  fi
}

# ── Ensure destination directory exists ──────────────────────────────────────
ensure_dest_dir() {
  if [[ ! -d "${TIMER_DEST}" ]]; then
    log_info "Creating ${TIMER_DEST}"
    if [[ "${DRY_RUN}" == "false" ]]; then
      mkdir -p "${TIMER_DEST}"
    fi
  fi
}

# ── Deploy (symlink) timer and service files ─────────────────────────────────
deploy_units() {
  local deployed=0
  local skipped=0

  while IFS= read -r -d '' unit_file; do
    local unit_name
    unit_name="$(basename "${unit_file}")"
    local link_target="${TIMER_DEST}/${unit_name}"

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

    # Syntax-check via systemd-analyze --user if available.
    # In dry-run mode verify the source file directly (no symlink exists yet).
    if command -v systemd-analyze &>/dev/null; then
      local verify_target
      if [[ "${DRY_RUN}" == "false" ]]; then
        verify_target="${link_target}"
      else
        verify_target="${unit_file}"
      fi
      if ! systemd-analyze verify --user "${verify_target}" 2>/dev/null; then
        log_warn "systemd-analyze verify --user reported issues for ${unit_name} (non-fatal)"
      fi
    fi
  done < <(find "${TIMERS_SRC}" \( -name "*.timer" -o -name "*.service" \) -print0)

  log_info "Deployed: ${deployed}  Already up-to-date: ${skipped}"
}

# ── Reload daemon and enable+start all timer units ───────────────────────────
reload_and_enable_timers() {
  log_info "Running: systemctl --user daemon-reload"
  if [[ "${DRY_RUN}" == "false" ]]; then
    systemctl --user daemon-reload
  fi

  while IFS= read -r -d '' timer_file; do
    local timer_name
    timer_name="$(basename "${timer_file}")"

    log_info "Enabling and starting: ${timer_name}"
    if [[ "${DRY_RUN}" == "false" ]]; then
      systemctl --user enable --now "${timer_name}"
    fi
  done < <(find "${TIMERS_SRC}" -name "*.timer" -print0)

  log_info "Timer reload complete."
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
  log_info "=== OsMEN-OC Timer Deploy ==="
  if [[ "${DRY_RUN}" == "true" ]]; then
    log_warn "Dry-run mode: no files will be written."
  fi

  check_prerequisites
  ensure_dest_dir
  deploy_units
  reload_and_enable_timers

  log_info "=== Done. Timers are registered and active. ==="
  log_info "Check timer status with:"
  log_info "  systemctl --user list-timers --all"
}

main "$@"
