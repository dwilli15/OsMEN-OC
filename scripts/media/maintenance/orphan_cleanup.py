#!/usr/bin/env python3
"""Find files not in any Plex library — potential orphans."""
import os, requests
from pathlib import Path

PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "NaxyQSk5i2fnKQyctmQg")
HEADERS = {"X-Plex-Token": PLEX_TOKEN, "Accept": "application/json"}

MEDIA_ROOTS = [
    Path("/run/media/dwill/plex/Media/TV"),
    Path("/run/media/dwill/plex/Media/Movies"),
    Path("/run/media/dwill/plex/Media/Anime"),
]

def get_plex_files():
    """Get all files known to Plex."""
    plex_files = set()
    r = requests.get(f"{PLEX_URL}/library/sections", headers=HEADERS)
    for sec in r.json().get("MediaContainer", {}).get("Directory", []):
        sr = requests.get(f"{PLEX_URL}/library/sections/{sec['key']}/all", headers=HEADERS)
        for item in sr.json().get("MediaContainer", {}).get("Metadata", []):
            for media in item.get("Media", []):
                for part in media.get("Part", []):
                    plex_files.add(part.get("file", ""))
    return plex_files

def find_orphans():
    plex_files = get_plex_files()
    print(f"Plex tracks {len(plex_files)} files")
    orphans = []
    for root in MEDIA_ROOTS:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if not f.is_file():
                continue
            if str(f) not in plex_files:
                orphans.append(f)
    print(f"Orphaned files: {len(orphans)}")
    for o in orphans[:20]:
        print(f"  {o}")
    if len(orphans) > 20:
        print(f"  ... and {len(orphans) - 20} more")
    return orphans

if __name__ == "__main__":
    find_orphans()
