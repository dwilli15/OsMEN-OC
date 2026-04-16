#!/usr/bin/env bash
# scripts/backup.sh — OsMEN-OC comprehensive backup script
# Enforces PF16: pg_dump ALL databases BEFORE restic snapshot.
# Run manually or via osmen-db-backup.service timer.
set -euo pipefail

# ─── Configuration ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${REPO_ROOT}/vault/logs/backup-$(date +%Y-%m-%d).log"
DUMP_DIR="${HOME}/.local/share/osmen/db-dumps"
TIMESTAMP="$(date -Iseconds)"

# Source restic credentials
ENV_FILE="${HOME}/.config/osmen/secrets/restic-backup.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "FATAL: Missing restic env file: $ENV_FILE" >&2
    exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"

# Verify required env vars
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY not set in $ENV_FILE}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD not set in $ENV_FILE}"

# ─── Flags ──────────────────────────────────────────────────────────
DRY_RUN=false
VERBOSE=false
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --verbose|-v) VERBOSE=true ;;
        --help|-h)
            echo "Usage: backup.sh [--dry-run] [--verbose]"
            echo "  --dry-run   Show what would be backed up without doing it"
            echo "  --verbose   Show detailed output"
            exit 0
            ;;
    esac
done

# ─── Helpers ────────────────────────────────────────────────────────
log() {
    local msg="[${TIMESTAMP}] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

fail() {
    log "FATAL: $1"
    exit 1
}

run_or_dry() {
    if $DRY_RUN; then
        log "DRY-RUN: $*"
    else
        "$@"
    fi
}

# ─── Pre-flight checks ─────────────────────────────────────────────
mkdir -p "$DUMP_DIR" "$(dirname "$LOG_FILE")"

log "Backup started — repo: ${RESTIC_REPOSITORY}"
$DRY_RUN && log "*** DRY RUN MODE — no changes will be made ***"

# Verify restic repo is accessible
if ! restic snapshots --latest 1 > /dev/null 2>&1; then
    fail "Cannot access restic repository at ${RESTIC_REPOSITORY}"
fi
log "Restic repo verified: accessible"

# ─── Phase 1: Database dumps (PF16 — BEFORE restic) ────────────────
log "Phase 1: Database dumps"

# PostgreSQL dump via podman
PG_CONTAINER="osmen-core-postgres"
if podman ps --format '{{.Names}}' 2>/dev/null | grep -q "^${PG_CONTAINER}$"; then
    PG_DUMP_FILE="${DUMP_DIR}/postgres-osmen-$(date +%Y%m%d_%H%M%S).sql.gz"
    log "Dumping PostgreSQL from ${PG_CONTAINER}..."
    run_or_dry bash -c "podman exec ${PG_CONTAINER} pg_dumpall -U osmen | gzip > '${PG_DUMP_FILE}'"
    if [[ -f "$PG_DUMP_FILE" ]] && [[ -s "$PG_DUMP_FILE" ]]; then
        log "PostgreSQL dump: ${PG_DUMP_FILE} ($(du -h "$PG_DUMP_FILE" | cut -f1))"
    elif ! $DRY_RUN; then
        log "WARNING: PostgreSQL dump may be empty: ${PG_DUMP_FILE}"
    fi
else
    log "SKIP: PostgreSQL container ${PG_CONTAINER} not running"
fi

# Redis BGSAVE via podman
REDIS_CONTAINER="osmen-core-redis"
if podman ps --format '{{.Names}}' 2>/dev/null | grep -q "^${REDIS_CONTAINER}$"; then
    log "Triggering Redis BGSAVE on ${REDIS_CONTAINER}..."
    if ! $DRY_RUN; then
        BEFORE=$(podman exec "$REDIS_CONTAINER" redis-cli LASTSAVE 2>/dev/null || echo "0")
        podman exec "$REDIS_CONTAINER" redis-cli BGSAVE > /dev/null 2>&1
        for i in $(seq 1 30); do
            AFTER=$(podman exec "$REDIS_CONTAINER" redis-cli LASTSAVE 2>/dev/null || echo "0")
            [[ "$AFTER" != "$BEFORE" ]] && break
            sleep 2
        done
        log "Redis BGSAVE completed"
    fi
else
    log "SKIP: Redis container ${REDIS_CONTAINER} not running"
fi

log "Phase 1 complete — database dumps done before restic"

# ─── Phase 2: Restic backup ────────────────────────────────────────
log "Phase 2: Restic backup"

# Backup targets — critical paths that must be preserved
BACKUP_PATHS=(
    "${HOME}/.ssh"
    "${HOME}/.gnupg"
    "${HOME}/.config/sops"
    "${HOME}/.config/osmen/secrets"
    "${REPO_ROOT}/config"
    "${REPO_ROOT}/quadlets"
    "${REPO_ROOT}/agents"
    "${REPO_ROOT}/migrations"
    "${REPO_ROOT}/timers"
    "${REPO_ROOT}/vault/logs"
    "${REPO_ROOT}/vault/memory"
    "$DUMP_DIR"
)

# Optional targets — include if they exist
OPTIONAL_PATHS=(
    "${HOME}/.local/share/siyuan"
    "${HOME}/.config/osmen/env"
    "${REPO_ROOT}/openclaw/memory"
    "${REPO_ROOT}/openclaw/state"
)

# Build the path list, filtering to paths that actually exist
EXISTING_PATHS=()
for p in "${BACKUP_PATHS[@]}"; do
    if [[ -e "$p" ]]; then
        EXISTING_PATHS+=("$p")
    else
        log "WARNING: Backup target missing: $p"
    fi
done

for p in "${OPTIONAL_PATHS[@]}"; do
    if [[ -e "$p" ]]; then
        EXISTING_PATHS+=("$p")
        $VERBOSE && log "Including optional: $p"
    fi
done

if [[ ${#EXISTING_PATHS[@]} -eq 0 ]]; then
    fail "No backup targets exist — nothing to back up"
fi

log "Backing up ${#EXISTING_PATHS[@]} paths..."
$VERBOSE && printf '  %s\n' "${EXISTING_PATHS[@]}"

run_or_dry restic backup \
    --tag osmen,nightly \
    --exclude-caches \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='*.tmp' \
    "${EXISTING_PATHS[@]}"

log "Phase 2 complete — restic backup created"

# ─── Phase 3: Retention policy ─────────────────────────────────────
log "Phase 3: Applying retention policy"

run_or_dry restic forget \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 3 \
    --prune \
    --tag osmen,nightly

log "Phase 3 complete — old snapshots pruned"

# ─── Phase 4: Integrity check ──────────────────────────────────────
log "Phase 4: Integrity verification"

# Check a random 5% subset of data to catch silent corruption
run_or_dry restic check --read-data-subset=5%

log "Phase 4 complete — integrity check passed"

# ─── Phase 5: Cleanup old dumps ────────────────────────────────────
log "Phase 5: Cleaning up old database dumps"

# Keep only last 7 days of local dump files
if ! $DRY_RUN; then
    CLEANED=$(find "$DUMP_DIR" -name "*.sql.gz" -mtime +7 -delete -print | wc -l)
    log "Removed ${CLEANED} dump files older than 7 days"
fi

# ─── Summary ───────────────────────────────────────────────────────
if ! $DRY_RUN; then
    LATEST=$(restic snapshots --latest 1 --json 2>/dev/null | python3.13 -c "
import json, sys
snaps = json.load(sys.stdin)
if snaps:
    s = snaps[0]
    print(f\"ID: {s['short_id']}  Time: {s['time'][:19]}  Paths: {len(s.get('paths', []))}  Tags: {','.join(s.get('tags', []))}\")" 2>/dev/null || echo "Could not read snapshot metadata")
    log "Latest snapshot: ${LATEST}"
fi

log "Backup complete — all phases finished successfully"
