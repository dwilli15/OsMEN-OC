"""Resource Watchdog — stale resources, orphan files, duplicate configs, broken symlinks."""

from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _file_hash(path: Path, block_size: int = 65536) -> str:
    h = hashlib.blake2b(digest_size=16)
    with path.open("rb") as f:
        while block := f.read(block_size):
            h.update(block)
    return h.hexdigest()


class ResourceWatchdog:
    """Scan directories for resource hygiene issues."""

    def __init__(
        self,
        roots: list[Path] | None = None,
        *,
        exclude: set[str] | None = None,
    ) -> None:
        self.roots = roots or [Path.cwd()]
        self.exclude = exclude or {
            ".git", ".venv", "node_modules", "__pycache__",
            ".mypy_cache", ".pytest_cache", ".ruff_cache",
            "dist", "build", ".eggs",
        }

    def _should_skip(self, path: Path) -> bool:
        return any(part in self.exclude for part in path.parts)

    def scan_broken_symlinks(self) -> list[dict[str, str]]:
        broken: list[dict[str, str]] = []
        for root in self.roots:
            for path in root.rglob("*"):
                if self._should_skip(path):
                    continue
                if path.is_symlink() and not path.exists():
                    broken.append({
                        "path": str(path),
                        "target": os.readlink(path),
                        "type": "broken_symlink",
                    })
        return broken

    def scan_duplicates(self, *, min_size: int = 100) -> list[dict[str, Any]]:
        hash_map: dict[str, list[str]] = defaultdict(list)
        for root in self.roots:
            for path in root.rglob("*"):
                if self._should_skip(path):
                    continue
                if not path.is_file() or path.is_symlink():
                    continue
                try:
                    if path.stat().st_size < min_size:
                        continue
                except OSError:
                    continue
                try:
                    h = _file_hash(path)
                    hash_map[h].append(str(path))
                except (OSError, PermissionError):
                    continue
        return [
            {"hash": h, "paths": paths, "type": "duplicate", "count": len(paths)}
            for h, paths in hash_map.items()
            if len(paths) > 1
        ]

    def scan_stale(self, *, max_age_days: int = 90) -> list[dict[str, Any]]:
        cutoff = datetime.now(UTC).timestamp() - (max_age_days * 86400)
        stale: list[dict[str, Any]] = []
        for root in self.roots:
            for path in root.rglob("*"):
                if self._should_skip(path):
                    continue
                if not path.is_file():
                    continue
                try:
                    if path.stat().st_mtime < cutoff:
                        stale.append({
                            "path": str(path),
                            "age_days": int((datetime.now(UTC).timestamp() - path.stat().st_mtime) / 86400),
                            "type": "stale",
                        })
                except (OSError, PermissionError):
                    continue
        return stale

    def full_scan(self) -> dict[str, Any]:
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "roots": [str(r) for r in self.roots],
            "broken_symlinks": self.scan_broken_symlinks(),
            "duplicates": self.scan_duplicates(),
            "stale_files": self.scan_stale(),
        }
        report["summary"] = {
            "broken_symlinks": len(report["broken_symlinks"]),
            "duplicate_groups": len(report["duplicates"]),
            "stale_files": len(report["stale_files"]),
        }
        return report
