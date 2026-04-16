#!/usr/bin/env python3
"""Inventory handoffs, memory surfaces, and Taskwarrior state for reconciliation."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class FileRecord:
    path: str
    modified: str


def newest_files(root: Path, pattern: str, limit: int) -> list[FileRecord]:
    paths = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    records: list[FileRecord] = []
    for path in paths[:limit]:
        records.append(
            FileRecord(
                path=str(path),
                modified=datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            )
        )
    return records


def task_summary() -> dict[str, object]:
    if not shutil.which("task"):
        return {"available": False}
    try:
        result = subprocess.run(
            ["task", "export"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"available": True, "error": str(exc)}
    try:
        entries = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"available": True, "error": f"invalid JSON: {exc}"}

    pending = sum(1 for entry in entries if entry.get("status") == "pending")
    completed = sum(1 for entry in entries if entry.get("status") == "completed")
    waiting = sum(1 for entry in entries if entry.get("status") == "waiting")
    projects = sorted({entry.get("project") for entry in entries if entry.get("project")})
    return {
        "available": True,
        "total": len(entries),
        "pending": pending,
        "completed": completed,
        "waiting": waiting,
        "projects": projects[:20],
    }


def markdown_list(title: str, records: Iterable[FileRecord]) -> list[str]:
    lines = [f"## {title}"]
    any_rows = False
    for record in records:
        lines.append(f"- `{record.path}` ({record.modified})")
        any_rows = True
    if not any_rows:
        lines.append("- none found")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--format", choices=("markdown", "json"), default="json")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    report = {
        "workspace": str(workspace),
        "resume": newest_files(workspace, "docs/session-logs/RESUME.md", 1),
        "handoffs": newest_files(workspace, "docs/session-logs/*/*handoff.md", args.limit),
        "memory_bank": newest_files(workspace, ".opencode/memory-bank/*.md", args.limit),
        "openclaw_memory": newest_files(workspace, "openclaw/memory/*.md", args.limit),
        "openclaw_state": newest_files(workspace, "openclaw/state/*.md", args.limit),
        "taskwarrior": task_summary(),
    }

    if args.format == "json":
        print(json.dumps(report, indent=2))
        return 0

    lines = [f"# Context Audit", "", f"- workspace: `{workspace}`", ""]
    lines.extend(markdown_list("Resume", report["resume"]))
    lines.append("")
    lines.extend(markdown_list("Handoffs", report["handoffs"]))
    lines.append("")
    lines.extend(markdown_list("Memory Bank", report["memory_bank"]))
    lines.append("")
    lines.extend(markdown_list("OpenClaw Memory", report["openclaw_memory"]))
    lines.append("")
    lines.extend(markdown_list("OpenClaw State", report["openclaw_state"]))
    lines.append("")
    lines.append("## Taskwarrior")
    task_data = report["taskwarrior"]
    if not task_data.get("available"):
        lines.append("- `task` not available")
    elif task_data.get("error"):
        lines.append(f"- error: {task_data['error']}")
    else:
        lines.append(f"- total: {task_data['total']}")
        lines.append(f"- pending: {task_data['pending']}")
        lines.append(f"- completed: {task_data['completed']}")
        lines.append(f"- waiting: {task_data['waiting']}")
        projects = ", ".join(task_data["projects"]) or "none"
        lines.append(f"- sample projects: {projects}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
