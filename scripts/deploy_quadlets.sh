#!/usr/bin/env bash
# scripts/deploy_quadlets.sh — Deploy rootless Podman Quadlet unit files.
#
# Idempotent: safe to run multiple times.  Symlinks all files from quadlets/
# into ~/.config/containers/systemd/ then reloads the user daemon.
#
# Usage:
#   scripts/deploy_quadlets.sh [--dry-run]
#
# Compatibility note:
#   Quadlet support was introduced in Podman 4.4 (Podman systemd --help will
#   show the "quadlet" sub-command when available).  This script checks for
#   that before proceeding.
#
# Service exposure policy (initial phase):
#   All containers bind only to 127.0.0.1 — no LAN exposure.
#   Access from other machines is via Tailscale mesh only.
#
# Monitoring stack:
#   Omitted in first-install pass; add monitoring quadlets later.

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_info()  { echo "[INFO]  $*"; }
log_warn()  { echo "[WARN]  $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
QUADLETS_SRC="${REPO_ROOT}/quadlets"
QUADLETS_DEST="${HOME}/.config/containers/systemd"

DRY_RUN=false
for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
check_prerequisites() {
  if ! command -v podman &>/dev/null; then
    log_error "podman not found — install podman 4.4+ before running this script."
    exit 1
  fi

  local podman_version
  podman_version=$(podman --version | awk '{print $3}')
  local major minor
  major=$(echo "$podman_version" | cut -d. -f1)
  minor=$(echo "$podman_version" | cut -d. -f2)

  # Quadlet was introduced in Podman 4.4
  if (( major < 4 || ( major == 4 && minor < 4 ) )); then
    log_error "Podman >= 4.4 required for Quadlet support (found ${podman_version})."
    exit 1
  fi

  # Confirm quadlet generator exists (provides 'podman systemd --help')
  if ! /usr/lib/podman/quadlet --help &>/dev/null && \
     ! /usr/libexec/podman/quadlet --help &>/dev/null; then
    log_warn "Quadlet generator binary not found at standard paths; proceeding anyway."
    log_warn "Run 'podman systemd --help' to verify Quadlet support on this system."
  fi

  if [[ ! -d "${QUADLETS_SRC}" ]]; then
    log_error "Quadlets source directory not found: ${QUADLETS_SRC}"
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
deploy_quadlets() {
  log_info "Creating destination directory: ${QUADLETS_DEST}"
  ${DRY_RUN} || mkdir -p "${QUADLETS_DEST}"

  local count=0
  while IFS= read -r -d '' src_file; do
    local filename
    filename="$(basename "${src_file}")"
    local dest_file="${QUADLETS_DEST}/${filename}"

    if [[ -L "${dest_file}" && "$(readlink -f "${dest_file}")" == "$(readlink -f "${src_file}")" ]]; then
      log_info "  already linked: ${filename}"
    else
      log_info "  linking: ${filename} -> ${dest_file}"
      if ! ${DRY_RUN}; then
        ln -sf "$(readlink -f "${src_file}")" "${dest_file}"
      fi
      (( count++ )) || true
    fi
  done < <(find "${QUADLETS_SRC}" -maxdepth 1 -type f \
    \( -name '*.container' -o -name '*.network' -o -name '*.volume' \
       -o -name '*.pod' -o -name '*.kube' \) -print0 | sort -z)

  if (( count == 0 )); then
    log_info "All quadlet files already in place — no changes."
  else
    log_info "${count} quadlet file(s) linked."
  fi
}

reload_daemon() {
  if ${DRY_RUN}; then
    log_info "[dry-run] Would run: systemctl --user daemon-reload"
    return
  fi
  log_info "Reloading systemd user daemon..."
  systemctl --user daemon-reload
  log_info "Daemon reloaded."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  log_info "=== OsMEN-OC Quadlet Deploy ==="
  ${DRY_RUN} && log_warn "Dry-run mode — no filesystem changes will be made."

  check_prerequisites
  deploy_quadlets
  reload_daemon

  log_info "Done. Enable services with:"
  log_info "  systemctl --user start osmen-core-postgres osmen-core-redis osmen-core-chromadb"
}

main "$@"
