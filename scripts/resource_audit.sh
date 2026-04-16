#!/usr/bin/env bash
# resource_audit.sh — Scan repo + external dirs, produce inventory report.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_DIR="$REPO_ROOT/vault/logs"
REPORT="$REPORT_DIR/resource-audit-$(date +%Y%m%dT%H%M%S).json"
mkdir -p "$REPORT_DIR"

echo "=== OsMEN-OC Resource Audit ===" >&2
echo "Scanning: $REPO_ROOT" >&2

python3 << PY
import json, sys
sys.path.insert(0, "$REPO_ROOT")
from pathlib import Path
from core.orchestration.watchdogs.resource_watchdog import ResourceWatchdog

roots = [
    Path("$REPO_ROOT"),
    Path.home() / ".config" / "opencode",
    Path.home() / ".claude",
]
wd = ResourceWatchdog(roots=roots)
report = wd.full_scan()

# Write report
with open("$REPORT", "w") as f:
    json.dump(report, f, indent=2)

s = report["summary"]
print(f"Broken symlinks: {s['broken_symlinks']}")
print(f"Duplicate groups: {s['duplicate_groups']}")
print(f"Stale files (>90d): {s['stale_files']}")
print(f"Report: $REPORT")
PY
