#!/usr/bin/env python3
"""Audit tool for Plex naming violations — scan all media and report issues."""
import sys
import re
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))
from plex_naming import MediaType, check_tv_path, check_movie_path

MEDIA_ROOTS = {
    Path("/run/media/dwill/plex/Media/TV"): MediaType.TV,
    Path("/run/media/dwill/plex/Media/Movies"): MediaType.MOVIE,
    Path("/run/media/dwill/plex/Media/Anime"): MediaType.TV,
    Path("/run/media/dwill/TV_Anime_OFlow/Media/TV"): MediaType.TV,
    Path("/run/media/dwill/TV_Anime_OFlow/Media/Anime"): MediaType.TV,
}


def scan(root, media_type):
    """Scan a root directory for naming violations."""
    total = issues_count = 0
    issues = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix in ('.txt', '.jpg', '.nfo', '.srt'):
            continue
        total += 1
        checks = check_tv_path if media_type == MediaType.TV else check_movie_path
        found = checks(p)
        if found:
            issues_count += 1
            for issue in found:
                issues.append(f"  {p.relative_to(root)}: {issue}")
    return total, issues_count, issues


def main():
    grand_total = grand_issues = 0
    for root, mtype in MEDIA_ROOTS.items():
        if not root.exists():
            print(f"SKIP: {root} (not mounted)")
            continue
        print(f"\n{mtype.value.upper()}: {root}")
        total, issue_count, issues = scan(root, mtype)
        grand_total += total
        grand_issues += issue_count
        print(f"  Files: {total}, Issues: {issue_count}")
        if issues and len(issues) <= 50:
            for i in issues:
                print(i)
        elif issues:
            for i in issues[:20]:
                print(i)
            print(f"  ... and {len(issues) - 20} more")

    if grand_total:
        pct = grand_issues / grand_total * 100
        print(f"\n{'='*60}")
        print(f"TOTAL: {grand_total} files, {grand_issues} issues ({pct:.1f}% violation rate)")
    else:
        print("No files found")


if __name__ == "__main__":
    main()
