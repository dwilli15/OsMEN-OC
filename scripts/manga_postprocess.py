#!/usr/bin/env python3
"""
OsMEN-OC Manga Post-Processor
Monitors SABnzbd completed downloads and moves manga files to Kavita library.

Usage:
  python3 manga_postprocess.py          # Process all completed downloads
  python3 manga_postprocess.py --watch  # Continuously watch for new completions
"""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote

SABNZBD_URL = "http://127.0.0.1:8082"
SABNZBD_KEY = "28f95b5a838e4421af5d32dfaa58303d"
MANGA_DIR = Path("/home/dwill/media/manga")
COMPLETE_DIR = Path("/home/dwill/Downloads/complete")
INCOMPLETE_DIR = Path("/home/dwill/Downloads/incomplete")

def get_sabnzbd_history():
    """Get completed downloads from SABnzbd history."""
    url = f"{SABNZBD_URL}/api?mode=history&apikey={SABNZBD_KEY}&limit=100&category=manga"
    try:
        req = Request(url)
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("history", {}).get("slots", [])
    except Exception as e:
        print(f"Error getting history: {e}", file=sys.stderr)
        return []

def sanitize_title(title):
    """Clean up a manga title for use as a directory name."""
    # Remove common release tags
    name = re.sub(r'\[.*?\]', '', title)
    name = re.sub(r'\(.*?\)', '', name)
    name = re.sub(r'[._-]', ' ', name)
    name = re.sub(r'\s+(vol|volume|v)\.?\s*\d+.*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+(ch|chapter)\.?\s*\d+.*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+(manga|comic|ebook|digital|retail).*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+(Yen\s*Press|VIZ|Kodansha|Seven\s*Seas).*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()
    # Title case
    name = name.title()
    return name

def find_files(directory):
    """Recursively find manga files (CBZ, CBR, ZIP, PDF, EPUB)."""
    extensions = {'.cbz', '.cbr', '.zip', '.pdf', '.epub', '.png', '.jpg', '.jpeg', '.webp', '.avif'}
    files = []
    if not directory.exists():
        return files
    for root, dirs, filenames in os.walk(directory):
        for f in filenames:
            if Path(f).suffix.lower() in extensions:
                files.append(Path(root) / f)
    return files

def process_download(slot):
    """Process a single completed download."""
    name = slot.get("nzb_name", slot.get("name", ""))
    status = slot.get("status", "")
    
    if status != "Completed":
        return False
    
    # Find the completed files
    # SABnzbd stores completed files in complete_dir/category/
    completed_path = COMPLETE_DIR / "manga"
    if not completed_path.exists():
        # Try without category subfolder
        completed_path = COMPLETE_DIR
    
    # Search for the job folder
    job_name = slot.get("nzb_name", "").replace('/', '_')
    job_dir = None
    
    # Try common patterns
    for candidate in [completed_path / job_name, completed_path / name]:
        if candidate.exists():
            job_dir = candidate
            break
    
    # If no exact match, search for files containing the name
    if not job_dir:
        for d in completed_path.iterdir():
            if d.is_dir() and any(kw in d.name.lower() for kw in name.lower().split()):
                job_dir = d
                break
    
    if not job_dir:
        print(f"  ⚠️  Could not find download dir for: {name[:60]}")
        return False
    
    files = find_files(job_dir)
    if not files:
        print(f"  ⚠️  No manga files found in: {job_dir}")
        return False
    
    # Create target directory in manga library
    manga_name = sanitize_title(name)
    target_dir = MANGA_DIR / manga_name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Move files
    moved = 0
    for f in files:
        dest = target_dir / f.name
        if dest.exists():
            print(f"  ⚠️  Skipping existing: {f.name}")
            continue
        shutil.move(str(f), str(dest))
        moved += 1
    
    if moved > 0:
        print(f"  ✅ {manga_name}: moved {moved} files")
        # Clean up empty source directory
        try:
            if job_dir.exists() and not any(job_dir.iterdir()):
                job_dir.rmdir()
                # Try to clean up parent if empty too
                if job_dir.parent.exists() and job_dir.parent != COMPLETE_DIR:
                    try:
                        job_dir.parent.rmdir()
                    except OSError:
                        pass
        except OSError:
            pass
        return True
    else:
        return False

def process_all():
    """Process all completed manga downloads."""
    print("📦 Processing completed manga downloads...")
    history = get_sabnzbd_history()
    
    if not history:
        print("  No completed downloads found.")
        return
    
    processed = 0
    for slot in history:
        if process_download(slot):
            processed += 1
    
    print(f"\n📊 Processed {processed}/{len(history)} downloads")
    return processed

def watch_mode(interval=60):
    """Continuously watch for new completed downloads."""
    print(f"👁️  Watching for completed downloads (check every {interval}s)...")
    last_count = 0
    while True:
        try:
            history = get_sabnzbd_history()
            current_count = len([s for s in history if s.get("status") == "Completed"])
            
            if current_count > last_count:
                print(f"\n📦 New completions detected: {current_count - last_count}")
                process_all()
                last_count = current_count
            else:
                last_count = current_count
            
            # Also check SABnzbd queue
            queue_url = f"{SABNZBD_URL}/api?mode=queue&apikey={SABNZBD_KEY}"
            req = Request(queue_url)
            with urlopen(req, timeout=10) as resp:
                queue = json.loads(resp.read())
            queue_size = queue.get("queue", {}).get("noofslots", 0)
            if queue_size > 0:
                print(f"  📥 Queue: {queue_size} items downloading...")
            
        except KeyboardInterrupt:
            print("\n👋 Stopped watching.")
            break
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
        
        time.sleep(interval)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="OsMEN-OC Manga Post-Processor")
    parser.add_argument("--watch", "-w", action="store_true", help="Watch mode")
    parser.add_argument("--interval", "-i", type=int, default=60, help="Check interval (seconds)")
    args = parser.parse_args()
    
    if args.watch:
        watch_mode(args.interval)
    else:
        process_all()

if __name__ == "__main__":
    main()
