#!/usr/bin/env bash
# scripts/deploy_quadlets.sh — Deploy rootless Podman Quadlet unit files
# Idempotent: symlinks existing files, reloads daemon.
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_info()  { echo "[quadlets] INFO  $*"; }
log_warn()  { echo "[quadlets] WARN  $*" >&2; }
log_error() { echo "[quadlets] ERROR $*" >&2; }

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUADLETS_SRC="$REPO_ROOT/quadlets"
QUADLETS_DEST="${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd"

log_info "Source:      $QUADLETS_SRC"
log_info "Destination: $QUADLETS_DEST"

# ---------------------------------------------------------------------------
# Precondition: quadlets directory must exist
# ---------------------------------------------------------------------------
if [ ! -d "$QUADLETS_SRC" ]; then
    log_warn "No quadlets/ directory found at $QUADLETS_SRC — nothing to deploy."
    exit 0
fi

# ---------------------------------------------------------------------------
# Create destination directory
# ---------------------------------------------------------------------------
mkdir -p "$QUADLETS_DEST"

# ---------------------------------------------------------------------------
# Symlink all Quadlet files
# ---------------------------------------------------------------------------
DEPLOYED=0
# Use find to safely enumerate all supported Quadlet unit types
while IFS= read -r -d '' unit_file; do

    unit_name="$(basename "$unit_file")"
    dest_link="$QUADLETS_DEST/$unit_name"

    if [ -L "$dest_link" ] && [ "$(readlink -f "$dest_link")" = "$(readlink -f "$unit_file")" ]; then
        log_info "  ✓ $unit_name (already linked)"
    else
        ln -sf "$unit_file" "$dest_link"
        log_info "  → Linked $unit_name"
    fi
    DEPLOYED=$((DEPLOYED + 1))
done < <(find "$QUADLETS_SRC" -maxdepth 1 \
    \( -name "*.container" -o -name "*.network" -o -name "*.volume" \
       -o -name "*.pod"   -o -name "*.slice"   -o -name "*.kube" \) \
    -print0 2>/dev/null | sort -z)

if [ "$DEPLOYED" -eq 0 ]; then
    log_warn "No Quadlet unit files found in $QUADLETS_SRC — nothing to deploy."
fi

# ---------------------------------------------------------------------------
# Reload systemd user daemon
# ---------------------------------------------------------------------------
if command -v systemctl &>/dev/null; then
    if systemctl --user &>/dev/null 2>&1; then
        log_info "Reloading systemd user daemon..."
        systemctl --user daemon-reload
        log_info "daemon-reload complete."
    else
        log_warn "systemd user session not available; skipping daemon-reload."
    fi
else
    log_warn "systemctl not found; skipping daemon-reload."
fi

log_info "Quadlet deployment complete ($DEPLOYED unit(s) processed)."
