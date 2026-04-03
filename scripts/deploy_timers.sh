#!/usr/bin/env bash
# scripts/deploy_timers.sh — Deploy user-level systemd timers and services.
#
# Idempotent: safe to run multiple times.  Symlinks all files from timers/
# into ~/.config/systemd/user/ then enables+starts the timer units.
#
# Usage:
#   scripts/deploy_timers.sh [--dry-run]
#
# Prerequisites:
#   - systemd user session must be running (loginctl enable-linger <user>)
#   - restic must be installed for the backup timer to succeed
#   - ~/.config/osmen/restic.env must exist with RESTIC_REPOSITORY and
#     RESTIC_PASSWORD_FILE variables (created during bootstrap)
#
# Validation note:
#   Syntax of this script is checked with: bash -n scripts/deploy_timers.sh
#   Timer/service unit syntax can be verified with:
#     systemd-analyze verify ~/.config/systemd/user/osmen-db-backup.timer

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_info()  { echo "[INFO]  $*"; }
log_warn()  { echo "[WARN]  $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMERS_SRC="${REPO_ROOT}/timers"
TIMERS_DEST="${HOME}/.config/systemd/user"

DRY_RUN=false
for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
check_prerequisites() {
  if ! command -v systemctl &>/dev/null; then
    log_error "systemctl not found — this script requires systemd."
    exit 1
  fi

  if ! systemctl --user status &>/dev/null; then
    log_warn "User systemd session may not be running."
    log_warn "Run: loginctl enable-linger \$(whoami)  then re-login."
  fi

  if [[ ! -d "${TIMERS_SRC}" ]]; then
    log_error "Timers source directory not found: ${TIMERS_SRC}"
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
deploy_timers() {
  log_info "Creating destination directory: ${TIMERS_DEST}"
  ${DRY_RUN} || mkdir -p "${TIMERS_DEST}"

  local count=0
  while IFS= read -r -d '' src_file; do
    local filename
    filename="$(basename "${src_file}")"
    local dest_file="${TIMERS_DEST}/${filename}"

    if [[ -L "${dest_file}" && "$(readlink -f "${dest_file}")" == "$(readlink -f "${src_file}")" ]]; then
      log_info "  already linked: ${filename}"
    else
      log_info "  linking: ${filename} -> ${dest_file}"
      if ! ${DRY_RUN}; then
        ln -sf "$(readlink -f "${src_file}")" "${dest_file}"
      fi
      (( count++ )) || true
    fi
  done < <(find "${TIMERS_SRC}" -maxdepth 1 -type f \
    \( -name '*.timer' -o -name '*.service' \) -print0 | sort -z)

  if (( count == 0 )); then
    log_info "All timer/service files already in place — no changes."
  else
    log_info "${count} timer/service file(s) linked."
  fi
}

reload_and_enable() {
  if ${DRY_RUN}; then
    log_info "[dry-run] Would run: systemctl --user daemon-reload"
    log_info "[dry-run] Would enable+start timer units."
    return
  fi

  log_info "Reloading systemd user daemon..."
  systemctl --user daemon-reload

  # Enable and start each timer (idempotent).
  while IFS= read -r -d '' src_file; do
    local filename
    filename="$(basename "${src_file}")"
    log_info "  enabling+starting: ${filename}"
    systemctl --user enable --now "${filename}"
  done < <(find "${TIMERS_SRC}" -maxdepth 1 -name '*.timer' -print0 | sort -z)

  log_info "Timer status:"
  systemctl --user list-timers --all | grep osmen || true
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  log_info "=== OsMEN-OC Timer Deploy ==="
  ${DRY_RUN} && log_warn "Dry-run mode — no filesystem changes will be made."

  check_prerequisites
  deploy_timers
  reload_and_enable

  log_info "Done. Check timer schedule with:"
  log_info "  systemctl --user list-timers --all"
}

main "$@"
