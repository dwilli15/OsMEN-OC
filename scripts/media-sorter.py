#!/usr/bin/env python3
"""
OsMEN Media Sorter — SABnzbd download to library pipeline.

Scans SABnzbd's completed downloads, categorizes content (manga, western comics,
eBooks), moves to the appropriate library directory, removes junk files, and
deduplicates.

Usage:
    python3 scripts/media-sorter.py [--dry-run] [--source DIR] [--manga DIR] [--comics DIR] [--ebooks DIR]

Intended to be run after SABnzbd completes downloads. Can be wired as a
SABnzbd post-processing script or run on a timer.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("media-sorter")

# ── Category detection ──────────────────────────────────────────────────────

MANGA_KEYWORDS = [
    re.compile(k, re.I)
    for k in [
        r"\bmanga\b",
        r"\byen[- ]press\b",
        r"\bkodansha\b",
        r"\bviz[- ]media\b",
        r"\bseven[- ]seas\b",
        r"\bdark[- ]horse\b.*(manga|comic|vol)",
        r"\bvertical\b.*(comic|inc\b)",
        r"\bvolumes?\s*\d",
        r"\bv\d{2}",
        r"\bvol\.\s*\d",
        r"\bdigital\s*sd\b",
        r"\bkg\s*manga\b",
        r"\blfp[- ]dcp\b",
        r"\b(japan|anime|manga|shonen|shoujo|seinen|light\s*novel|manhwa|manhua)\b",
        r"\b(retail\s*comic|hybrid\s*comic)\b.*(?:yen|kodansha|viz|seven|dark\s*horse)",
        r"one[- ]?piece|naruto|bleach|dragon[- ]?ball|attack.on.titan|demon[- ]?slayer|"
        r"my[- ]?hero[- ]?academia|vinland|promised.neverland|sword.art|rezero|"
        r"goblin[- ]?slayer|komi|rascal.does.not|no.game.no.life|executioner|"
        r"brunhild|holy.grail.of.eris|girl.i.saved|once.upon.a.witch|"
        r"rascal.does.not.dream|apothecary.diaries|berserk|sailor.moon|"
        r"exorcist|shirayukihime|hanayome|fire.force|chainsaw.man|jujutsu|"
        r"spy.x.family|dandadan|blue.box|kaiju.no|dr.stone|boku.no.hero",
    ]
]

WESTERN_COMICS_KEYWORDS = [
    re.compile(k, re.I)
    for k in [
        r"\bdc\b",
        r"\bmarvel\b",
        r"\bbatman\b",
        r"\bsuperman\b",
        r"\bconstantine\b",
        r"\bjustice\s*league\b",
        r"\bflash\b.*(comics?\b|\d)",
        r"\bgreen\s*lantern\b",
        r"\bwonder\s*woman\b",
        r"\baquaman\b",
        r"\bspider[- ]?man\b",
        r"\bavenger\b",
        r"\bx[- ]?men\b",
        r"\biron\s*man\b",
        r"\bcaptain\s*america\b",
        r"\bhulk\b",
        r"\bthor\b.*(marvel|comic)",
        r"\bdeadpool\b",
        r"\bwolverine\b",
        r"\binvincible\b.*(comic|image)",
        r"\bwalking\s*dead\b",
        r"\bsaga\b.*(comic|image|vaughan)",
        r"\bspawn\b",
        r"\bimage\s*comics\b",
        r"\bzone[- ]empire\b",
        r"\bson\s*of\s*ultron[- ]empire\b",
        r"\b(?:digital|dcp|empire|minutemen|nomad|the\.group)\b.*\b(?:dc|marvel)\b",
        r"\bfcbd\b",
        r"\b0[- ]day\b",
        r"\bprez[- ]",
        r"\bdarkness\b.*(comic|top\s*cow|image)",
        r"\bwitchblade\b",
        r"\bartifacts\b.*(top\s*cow)",
        r"\bhellblazer\b",
        r"\bswamp\s*thing\b",
        r"\bphantom\s*stranger\b",
        r"\bdoom\s*patrol\b",
        r"\banimal\s*man\b",
        r"\bcatwoman\b",
        r"\bdeathstroke\b",
        r"\bbizarro\b",
        r"\bomega\s*men\b",
        r"\btrinity\s*of\s*sin\b",
        r"\bbuffy\b",
        r"\brobin\b.*(2015|2016|digital)",
        r"\bzodiac\s*starforce\b",
        r"\bnightwing\b",
        r"\bharley\s*quinn\b",
        r"\bsuicide\s*squad\b",
        r"\bteen\s*titans\b",
        r"\bgreen\s*arrow\b",
        r"\bblack\s*canary\b",
        r"\bstar\s*fire\b",
        r"\braven\b.*(dc|titans|comic)",
        r"\bfirestorm\b",
        r"\bblue\s*beetle\b",
        r"\bquestion\b.*(dc|comic)",
        r"\blobo\b",
        r"\bgotham\s*academy\b",
        r"\bdoctor\s*who\b",
        r"\bgrayson\b.*(2014|2015|2016|digital)",
        r"\bklrion\b",
        r"\bhitman\b.*(dc|lobo)",
        r"\bauthority\b.*(lobo|dc)",
        # Scan groups strongly associated with western comics
        r"\b(?:empire|minutemen|dcp|oroboros|thatguy|nomad|mephisto|cypher|blackmanta|glorith|pyrate)\b.*\b(?:digital|dc|marvel|comic)\b",
        # Generic digital comic issue pattern: "Title 001 20xx Digital"
        r"\b\d{4}\s+(?:digital|digital-)\b",
    ]
]

JUNK_EXTENSIONS = {".diz", ".nfo", ".exe", ".nzb", ".htm", ".html", ".php", ".url"}
# Files that are likely metadata/sample, not actual content
JUNK_PATTERNS = [re.compile(p, re.I) for p in [r"sample[- ]", r"\bsubscribe\b"]]


def classify_dir(dirname: str) -> str:
    """Classify a download directory as manga, western_comics, ebooks, or unknown."""
    name = dirname.replace(".", " ").replace("_", " ").replace("-", " ").lower()

    manga_score = sum(1 for p in MANGA_KEYWORDS if p.search(name))
    western_score = sum(1 for p in WESTERN_COMICS_KEYWORDS if p.search(name))

    if manga_score > western_score and manga_score >= 1:
        return "manga"
    if western_score >= 1:
        return "western_comics"
    # Fallback: check file contents
    return "unknown"


def is_junk_file(path: Path) -> bool:
    """Check if a file is junk (metadata, sample, executable)."""
    if path.suffix.lower() in JUNK_EXTENSIONS:
        return True
    name = path.name.lower()
    return any(p.search(name) for p in JUNK_PATTERNS)


def clean_dir(dirpath: Path, dry_run: bool = False) -> int:
    """Remove junk files from a directory tree. Returns bytes freed."""
    freed = 0
    for f in dirpath.rglob("*"):
        if f.is_file() and is_junk_file(f):
            size = f.stat().st_size
            freed += size
            if dry_run:
                log.info(f"  [DRY] Junk: {f.name} ({size:,} bytes)")
            else:
                f.unlink()
    return freed


def find_duplicates(dirs: list[Path]) -> dict[str, list[Path]]:
    """Find directories that likely contain the same content (different scan groups)."""
    groups: dict[str, list[Path]] = {}
    for d in dirs:
        # Normalize: strip scan group tags, whitespace variations, casing
        name = d.name
        # Remove common scan group suffixes
        for pattern in [r"\s*\.\d+$", r"\s+\([^(]+\)$", r"\s*[-_]\s*$"]:
            name = re.sub(pattern, "", name)
        name = re.sub(r"[-_.]+", " ", name).strip().lower()
        # Group by first 30 chars (usually enough to identify the title)
        key = name[:30]
        groups.setdefault(key, []).append(d)
    return {k: v for k, v in groups.items() if len(v) > 1}


def pick_best(duplicates: list[Path]) -> Path:
    """From duplicate dirs, pick the best one (largest total size = most complete)."""
    best = max(duplicates, key=lambda d: sum(f.stat().st_size for f in d.rglob("*") if f.is_file()))
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description="OsMEN Media Sorter")
    parser.add_argument("--dry-run", action="store_true", help="Preview without moving files")
    parser.add_argument("--source", default=None, help="Source directory (SABnzbd complete)")
    parser.add_argument("--manga", default="/mnt/other-media/Manga", help="Manga library dir")
    parser.add_argument("--comics", default="/mnt/other-media/Media/Other/Comics", help="Western comics dir")
    parser.add_argument("--ebooks", default="/mnt/other-media/Media/Other/eBooks", help="eBooks dir")
    parser.add_argument("--delete-duplicates", action="store_true", help="Delete lesser duplicates")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Default source: SABnzbd complete folder
    source = Path(args.source) if args.source else Path(
        Path.home(),
        ".local/share/containers/storage/volumes/osmen-sab-config.volume/_data/Downloads/complete",
    )

    manga_dir = Path(args.manga)
    comics_dir = Path(args.comics)
    ebooks_dir = Path(args.ebooks)

    if not source.exists():
        log.error(f"Source directory not found: {source}")
        return 1

    # Gather all subdirectories
    subdirs = sorted(d for d in source.iterdir() if d.is_dir())
    # Also include loose files in source (not in subdirs)
    loose_files = [f for f in source.iterdir() if f.is_file()]

    log.info(f"Scanning {len(subdirs)} directories in {source}")

    # Phase 1: Classify
    categories: dict[str, list[Path]] = {"manga": [], "western_comics": [], "ebooks": [], "unknown": []}
    for d in subdirs:
        cat = classify_dir(d.name)
        categories[cat].append(d)

    log.info(f"Classification: {len(categories['manga'])} manga, "
             f"{len(categories['western_comics'])} western comics, "
             f"{len(categories['unknown'])} unknown")

    # Phase 2: Deduplicate
    for cat in ["manga", "western_comics"]:
        dupes = find_duplicates(categories[cat])
        if dupes:
            log.info(f"Found {len(dupes)} duplicate groups in {cat}")
            for key, group in dupes.items():
                best = pick_best(group)
                losers = [d for d in group if d != best]
                log.info(f"  Dupes: keeping '{best.name}', {len(losers)} lesser copies")
                if args.delete_duplicates and not args.dry_run:
                    for loser in losers:
                        log.info(f"    Deleting: {loser.name}")
                        shutil.rmtree(loser)
                        categories[cat].remove(loser)
                elif args.dry_run:
                    for loser in losers:
                        log.info(f"    [DRY] Would delete: {loser.name}")

    # Phase 3: Clean junk files
    total_junk = 0
    for cat in categories:
        for d in categories[cat]:
            freed = clean_dir(d, dry_run=args.dry_run)
            total_junk += freed
    if total_junk:
        log.info(f"Cleaned {total_junk / 1024 / 1024:.1f} MB of junk files")

    def _move_dir(src: Path, dest: Path, label: str) -> bool:
        """Move directory using rsync+rm for cross-drive performance."""
        if dest.exists():
            log.warning(f"  Skip (exists): {src.name}")
            return False
        size = sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
        if args.dry_run:
            log.info(f"  [DRY] {label}: {src.name} → {dest} ({size / 1024 / 1024:.0f} MB)")
            return True
        # Use rsync for cross-device moves (much faster than shutil for large dirs)
        try:
            # Check if same filesystem
            if os.stat(src).st_dev == os.stat(dest.parent).st_dev:
                shutil.move(str(src), str(dest))
            else:
                result = subprocess.run(
                    ["rsync", "-a", "--remove-source-files", str(src) + "/", str(dest) + "/"],
                    capture_output=True, text=True, timeout=3600,
                )
                if result.returncode != 0:
                    log.error(f"  rsync failed for {src.name}: {result.stderr}")
                    return False
                # Clean up empty source dir
                subprocess.run(["find", str(src), "-type", "d", "-empty", "-delete"], timeout=60)
                # Remove the source dir itself if empty
                try:
                    src.rmdir()
                except OSError:
                    pass
        except Exception as e:
            log.error(f"  Move failed for {src.name}: {e}")
            return False
        log.info(f"  {label}: {src.name} ({size / 1024 / 1024:.0f} MB)")
        return True

    # Phase 4: Move to libraries
    moved = {"manga": 0, "western_comics": 0, "ebooks": 0, "unknown": 0}
    moved_bytes = {"manga": 0, "western_comics": 0, "ebooks": 0, "unknown": 0}

    for d in categories["manga"]:
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        if _move_dir(d, manga_dir / d.name, "Manga"):
            moved["manga"] += 1
            moved_bytes["manga"] += size

    for d in categories["western_comics"]:
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        if _move_dir(d, comics_dir / d.name, "Comics"):
            moved["western_comics"] += 1
            moved_bytes["western_comics"] += size

    # Phase 5: Handle unknowns — leave in place, log for review
    if categories["unknown"]:
        log.info(f"{len(categories['unknown'])} unclassified items left in source:")
        for d in categories["unknown"]:
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            log.info(f"  UNKNOWN: {d.name} ({size / 1024 / 1024:.0f} MB)")

    # Summary
    total_moved = sum(moved.values())
    total_bytes = sum(moved_bytes.values())
    log.info(f"{'[DRY RUN] ' if args.dry_run else ''}Summary: "
             f"{total_moved} items ({total_bytes / 1024 / 1024 / 1024:.1f} GB) — "
             f"{moved['manga']} manga, {moved['western_comics']} comics, "
             f"{len(categories['unknown'])} unknown")

    return 0


if __name__ == "__main__":
    sys.exit(main())
