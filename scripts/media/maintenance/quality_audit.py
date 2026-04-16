#!/usr/bin/env python3
"""Report file quality (resolution, codec) across media library."""
import re, json, subprocess
from pathlib import Path
from collections import Counter

ROOTS = [
    Path("/run/media/dwill/plex/Media/TV"),
    Path("/run/media/dwill/plex/Media/Movies"),
    Path("/run/media/dwill/plex/Media/Anime"),
]

res_counter = Counter()
codec_counter = Counter()
ext_counter = Counter()

def guess_quality(filename):
    """Guess quality from filename without ffprobe."""
    fn = filename.lower()
    if '2160p' in fn or '4k' in fn or 'uhd' in fn:
        return '4K'
    if '1080p' in fn:
        return '1080p'
    if '720p' in fn:
        return '720p'
    if '480p' in fn:
        return '480p'
    return 'unknown'

def audit():
    total = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if not f.is_file() or f.suffix in ('.txt', '.jpg', '.nfo', '.srt'):
                continue
            total += 1
            ext_counter[f.suffix] += 1
            res_counter[guess_quality(f.name)] += 1
            # Guess codec from extension
            if f.suffix == '.mkv':
                codec_counter['MKV (likely H264/H265)'] += 1
            elif f.suffix == '.mp4':
                codec_counter['MP4'] += 1
            elif f.suffix == '.avi':
                codec_counter['AVI'] += 1

    print(f"Total media files: {total}")
    print(f"\nBy resolution:")
    for k, v in res_counter.most_common():
        print(f"  {k}: {v} ({v/total*100:.1f}%)")
    print(f"\nBy container:")
    for k, v in ext_counter.most_common():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    audit()
