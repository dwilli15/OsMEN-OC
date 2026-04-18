#!/usr/bin/env python3
"""
Fix TV Show and Anime folder + episode naming for Plex compliance.
Runs on /run/media/dwill/plex/Media/TV/ and /run/media/dwill/plex/Media/Anime/
NTFS3 filesystem — colons and apostrophes are safe.

Usage:
  python3 fix_tv_anime_naming.py --dry-run   # Preview changes
  python3 fix_tv_anime_naming.py              # Execute
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

TV_BASE = Path("/run/media/dwill/plex/Media/TV")
ANIME_BASE = Path("/run/media/dwill/plex/Media/Anime")

# ── TV FOLDER RENAMES ──────────────────────────────────────────────
TV_FOLDER_RENAMES = {
    "Agatha Christies Seven Dials (2025)": "Agatha Christie's Seven Dials (2025)",
    "Agents of SHIELD (2013)": "Marvel's Agents of S.H.I.E.L.D. (2013)",
    "Big Bang Theory (2007)": "The Big Bang Theory (2007)",
    "CIA. (2026)": "CIA (2026)",
    "Daredevil Born Again (2025)": "Daredevil: Born Again (2025)",
    "House MD (2004)": "House (2004)",
    "Monarch Legacy of Monsters (2023)": "Monarch: Legacy of Monsters (2023)",
    "Spartacus - House of Ashur (2025)": "Spartacus: House of Ashur (2025)",
    "Star Trek - Deep Space Nine (1993)": "Star Trek: Deep Space Nine (1993)",
    "Star Trek - Enterprise (2001)": "Star Trek: Enterprise (2001)",
    "Star Trek - Lower Decks (2020)": "Star Trek: Lower Decks (2020)",
    "Star Trek - Picard (2020)": "Star Trek: Picard (2020)",
    "Star Trek - Short Treks (2018)": "Star Trek: Short Treks (2018)",
    "Star Trek - Starfleet Academy (2025)": "Star Trek: Starfleet Academy (2025)",
    "Star Trek - Strange New Worlds (2022)": "Star Trek: Strange New Worlds (2022)",
    "Star Trek - The Animated Series (1973)": "Star Trek: The Animated Series (1973)",
    "Star Trek - The Next Generation (1987)": "Star Trek: The Next Generation (1987)",
    "Star Trek - The Original Series (1966)": "Star Trek: The Original Series (1966)",
    "Star Trek - Voyager (1995)": "Star Trek: Voyager (1995)",
    "Star Trek Discovery (2017)": "Star Trek: Discovery (2017)",
    "Star Wars Tales of the Underworld (2025)": "Star Wars: Tales of the Underworld (2025)",
    "The Last of Us": "The Last of Us (2023)",
    "The Croods Family Tree (2021)": "The Croods: Family Tree (2021)",
}

# ── ANIME FOLDER RENAMES ───────────────────────────────────────────
ANIME_FOLDER_RENAMES = {
    "Avatar The Last Airbender (2005)": "Avatar: The Last Airbender (2005)",
    "Secrets of the Silent Witch (2023)": "Secrets of the Silent Witch (2025)",
}

# ── EPISODE CLEANUP RULES ──────────────────────────────────────────
# Shows with scene-format episode filenames that need cleaning
# Uses NEW folder names (after rename). Script resolves old→new automatically.
SCENE_SHOWS = {
    "Marvel's Agents of S.H.I.E.L.D. (2013)",
    "DTF St. Louis (2026)",
    "The Continental (2023)",
    "The Croods: Family Tree (2021)",
    "The Diplomat (2023)",
    "The Night Manager (2016)",
    "True Lies (2023)",
}

# Shows with lowercase s01e01 that need S01E01
LOWERCASE_SHOWS = {
    "3 Body Problem (2024)",
    "Star Trek: Deep Space Nine (1993)",
    "Star Trek: Enterprise (2001)",
    "Star Trek: Lower Decks (2020)",
    "Star Trek: Picard (2020)",
    "Star Trek: Short Treks (2018)",
    "Star Trek: Starfleet Academy (2025)",
    "Star Trek: Strange New Worlds (2022)",
    "Star Trek: The Animated Series (1973)",
    "Star Trek: The Next Generation (1987)",
    "Star Trek: The Original Series (1966)",
    "Star Trek: Voyager (1995)",
    "Star Trek: Discovery (2017)",
    "The Lord of the Rings: The Rings of Power (2022)",
    "Fallout (2024)",
    "Hunter x Hunter (2011)",
    "Secrets of the Silent Witch (2025)",
}

# Build reverse map: new_name → old_name (for resolving pre-rename paths)
ALL_FOLDER_RENAMES = {**TV_FOLDER_RENAMES, **ANIME_FOLDER_RENAMES}
REVERSE_RENAMES = {v: k for k, v in ALL_FOLDER_RENAMES.items()}


def resolve_show_dir(show_name: str, bases: list[Path]) -> Path | None:
    """Find show directory using new name first, then fall back to old name."""
    for base in bases:
        new_path = base / show_name
        if new_path.exists():
            return new_path
        # Check old name (before folder rename)
        old_name = REVERSE_RENAMES.get(show_name)
        if old_name:
            old_path = base / old_name
            if old_path.exists():
                return old_path
    return None

# Anime with group tags in filenames
ANIME_TAG_SHOWS = {
    "Monogatari Series (2009)": {
        "pattern": r"^\[MTBB\]\s*",
        "prefix": "Monogatari Series",
    },
    "My Hero Academia (2016)": {
        "pattern": r"^\[Anime Time\]\s*",
        "prefix": "My Hero Academia",
    },
    "Neon Genesis Evangelion (1995)": {
        "pattern": r"^\[Anime Time\]\s*",
        "prefix": "Neon Genesis Evangelion",
    },
    "The Apothecary Diaries (2023)": {
        "pattern": r"^\[DB\]\s*",
        "prefix": "The Apothecary Diaries",
    },
}


def parse_episode_id(filename: str) -> tuple[int, int] | None:
    """Extract (season, episode) from filename."""
    # Match S01E01, s01e01, 1x01, S1E1, etc.
    m = re.search(r'[Ss](\d{1,2})[Ee](\d{1,2})', filename)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(\d{1,2})x(\d{1,2})', filename)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def clean_scene_filename(filename: str, show_name: str) -> str | None:
    """Clean scene-format filename to Show - S01E01.ext"""
    ep = parse_episode_id(filename)
    if not ep:
        return None
    season, episode = ep
    ext = Path(filename).suffix
    return f"{show_name} - S{season:02d}E{episode:02d}{ext}"


def fix_lowercase_sxxexx(filename: str) -> str:
    """Fix lowercase s01e01 to S01E01 in filename."""
    return re.sub(r'[s](\d{1,2})[e](\d{1,2})', lambda m: f'S{m.group(1)}E{m.group(2)}', filename)


def clean_anime_filename(filename: str, show_name: str, pattern: str) -> str | None:
    """Strip group tags from anime filename, normalize to Show - S01E01.ext or keep as-is."""
    # Strip the group tag prefix
    stripped = re.sub(pattern, '', filename).strip()

    # Try to extract episode number
    ep = parse_episode_id(stripped)
    if ep:
        season, episode = ep
        ext = Path(filename).suffix
        # Remove hash tags like [346DABB1], version markers like v2
        clean = re.sub(r'\s*\[[\da-fA-F]+\]', '', stripped)
        clean = re.sub(r'v\d+', '', clean)
        return f"{show_name} - S{season:02d}E{episode:02d}{ext}"

    # Some anime files don't have S01E01 — they might be movies or specials
    # For movies in a Movies/ folder, just strip the tag
    return None


def rename_folder(base: Path, old_name: str, new_name: str, dry_run: bool) -> bool:
    old_path = base / old_name
    new_path = base / new_name
    if not old_path.exists():
        print(f"  ⚠ SKIP (not found): {old_name}")
        return False
    if new_path.exists():
        print(f"  ⚠ SKIP (target exists): {new_name}")
        return False
    print(f"  📁 {old_name}")
    print(f"     → {new_name}")
    if not dry_run:
        old_path.rename(new_path)
    return True


def rename_episode(file_path: Path, new_name: str, dry_run: bool) -> bool:
    if file_path.name == new_name:
        return False
    new_path = file_path.parent / new_name
    if new_path.exists():
        print(f"    ⚠ SKIP (exists): {new_name}")
        return False
    print(f"    🎬 {file_path.name}")
    print(f"       → {new_name}")
    if not dry_run:
        file_path.rename(new_path)
    return True


def main():
    parser = argparse.ArgumentParser(description="Fix Plex TV/Anime naming")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"{'='*60}")
    print(f"  Plex TV/Anime Naming Fix — {mode}")
    print(f"{'='*60}\n")

    folder_count = 0
    file_count = 0

    # ── Phase 1: TV Folder Renames ─────────────────────────────────
    print("▶ Phase 1: TV Show Folder Renames")
    print(f"  ({len(TV_FOLDER_RENAMES)} renames)\n")
    for old, new in TV_FOLDER_RENAMES.items():
        if rename_folder(TV_BASE, old, new, args.dry_run):
            folder_count += 1
    print()

    # ── Phase 2: Anime Folder Renames ──────────────────────────────
    print("▶ Phase 2: Anime Folder Renames")
    print(f"  ({len(ANIME_FOLDER_RENAMES)} renames)\n")
    for old, new in ANIME_FOLDER_RENAMES.items():
        if rename_folder(ANIME_BASE, old, new, args.dry_run):
            folder_count += 1
    print()

    # ── Phase 3: Scene-format Episode Cleanup ──────────────────────
    print("▶ Phase 3: Scene-format Episode Filename Cleanup\n")
    for show_name in SCENE_SHOWS:
        show_dir = resolve_show_dir(show_name, [TV_BASE, ANIME_BASE])
        if not show_dir:
            print(f"  ⚠ Show not found: {show_name}")
            continue
        print(f"  📂 {show_name}")
        for f in sorted(show_dir.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix not in (".mkv", ".mp4", ".avi"):
                continue
            new_name = clean_scene_filename(f.name, show_name)
            if new_name and new_name != f.name:
                if rename_episode(f, new_name, args.dry_run):
                    file_count += 1
        print()

    # ── Phase 4: Lowercase s01e01 → S01E01 ────────────────────────
    print("▶ Phase 4: Lowercase s01e01 → S01E01 Fix\n")
    for show_name in LOWERCASE_SHOWS:
        show_dir = resolve_show_dir(show_name, [TV_BASE, ANIME_BASE])
        if not show_dir:
            print(f"  ⚠ Show not found: {show_name}")
            continue
        has_issues = False
        for f in sorted(show_dir.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix not in (".mkv", ".mp4", ".avi", ".srt"):
                continue
            if re.search(r'[s](\d{1,2})[e](\d{1,2})', f.name):
                new_name = fix_lowercase_sxxexx(f.name)
                if new_name != f.name:
                    if not has_issues:
                        print(f"  📂 {show_name}")
                        has_issues = True
                    if rename_episode(f, new_name, args.dry_run):
                        file_count += 1
        print()

    # ── Phase 5: Anime Group Tag Cleanup ───────────────────────────
    print("▶ Phase 5: Anime Group Tag Cleanup\n")
    for show_name, config in ANIME_TAG_SHOWS.items():
        show_dir = resolve_show_dir(show_name, [ANIME_BASE, TV_BASE])
        if not show_dir:
            print(f"  ⚠ Show not found: {show_name}")
            continue
        pattern = config["pattern"]
        prefix = config["prefix"]
        print(f"  📂 {show_name}")
        for f in sorted(show_dir.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix not in (".mkv", ".mp4", ".avi"):
                continue
            if re.search(pattern, f.name):
                new_name = clean_anime_filename(f.name, prefix, pattern)
                if new_name and new_name != f.name:
                    if rename_episode(f, new_name, args.dry_run):
                        file_count += 1
        print()

    # ── Summary ────────────────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  Summary ({mode})")
    print(f"  Folders renamed: {folder_count}")
    print(f"  Files renamed:   {file_count}")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n  Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
