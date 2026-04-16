#!/usr/bin/env python3
"""Find duplicate episodes across drives by comparing filenames."""
import re
from pathlib import Path
from collections import defaultdict

ROOTS = [
    Path("/run/media/dwill/plex/Media/TV"),
    Path("/run/media/dwill/plex/Media/Movies"),
    Path("/run/media/dwill/plex/Media/Anime"),
    Path("/run/media/dwill/TV_Anime_OFlow/Media/TV"),
    Path("/run/media/dwill/TV_Anime_OFlow/Media/Anime"),
]

def normalize(name):
    """Normalize filename for comparison."""
    stem = Path(name).stem.lower()
    stem = re.sub(r'[.\-_]', ' ', stem)
    stem = re.sub(r'\s+', ' ', stem)
    # Strip quality/scene tags
    for tag in ('1080p', '720p', '480p', 'hevc', 'x264', 'x265', 'aac',
                'web dl', 'webrip', 'bluray', 'brrip', 'hdtv', 'complete'):
        stem = re.sub(rf'\b{tag}\b', '', stem)
    return stem.strip()

def find_duplicates():
    seen = defaultdict(list)
    for root in ROOTS:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if not f.is_file() or f.suffix in ('.txt', '.jpg', '.nfo', '.srt'):
                continue
            key = normalize(f.name)
            seen[key].append(str(f))

    dups = {k: v for k, v in seen.items() if len(v) > 1}
    if dups:
        print(f"Found {len(dups)} duplicate groups:")
        for key, paths in sorted(dups.items()):
            print(f"\n  {key}")
            for p in paths:
                print(f"    {p}")
    else:
        print("No duplicates found")
    return dups

if __name__ == "__main__":
    find_duplicates()
