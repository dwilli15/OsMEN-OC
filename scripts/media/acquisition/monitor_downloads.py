#!/usr/bin/env python3
"""Watch download dirs for completed items and report status."""
import time, os
from pathlib import Path

DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "/home/dwill/Downloads"))
MEDIA_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.m4v', '.mp3', '.flac', '.m4b',
                    '.epub', '.cbz', '.cbr'}

def scan():
    """Scan downloads for media files."""
    if not DOWNLOAD_DIR.exists():
        print(f"Download dir not found: {DOWNLOAD_DIR}")
        return []

    media_files = []
    for f in DOWNLOAD_DIR.rglob("*"):
        if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS:
            size_mb = f.stat().st_size / (1024 * 1024)
            media_files.append((f, size_mb))

    if media_files:
        print(f"Found {len(media_files)} media files in downloads:")
        for f, size in sorted(media_files, key=lambda x: -x[1]):
            print(f"  {size:.1f} MB  {f.name}")
    else:
        print("No media files in downloads")
    return media_files

if __name__ == "__main__":
    scan()
