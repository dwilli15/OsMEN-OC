#!/usr/bin/env python3
"""OsMEN-OC Manga Bulk Downloader v2 - Simplified, no strict filtering."""

import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote

PROWLARR_URL = "http://127.0.0.1:9696"
PROWLARR_KEY = "72844585a87d45239efce069e1ed73a8"
SABNZBD_URL = "http://127.0.0.1:8082"
SABNZBD_KEY = "28f95b5a838e4421af5d32dfaa58303d"
MANGA_LIST = Path("/home/dwill/dev/OsMEN-OC/state/manga_list_300.txt")
REPORT = Path("/home/dwill/dev/OsMEN-OC/state/manga_download_report.txt")

def search_prowlarr(query):
    """Search Prowlarr - return all results sorted by size desc."""
    url = f"{PROWLARR_URL}/api/v1/search?apikey={PROWLARR_KEY}&query={quote(query)}&limit=30"
    try:
        with urlopen(Request(url), timeout=20) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return []

def queue_nzb(nzb_url, title):
    """Send NZB/torrent to SABnzbd."""
    url = f"{SABNZBD_URL}/api?mode=addurl&name={quote(nzb_url)}&apikey={SABNZBD_KEY}&cat=manga"
    try:
        with urlopen(Request(url), timeout=10) as resp:
            return "ok" in resp.read().decode().lower()
    except:
        return False

def is_manga_result(title):
    """Loose filter - just exclude obvious non-manga."""
    t = title.lower()
    # Exclude anime/video
    video_exts = ['.mkv', '.mp4', '.avi', '.wmv', '.ts']
    if any(t.endswith(ext) for ext in video_exts):
        return False
    # Exclude XXX
    if any(x in t for x in ['xxx', 'porn', 'hentai', '+18']):
        return False
    # Exclude software
    if any(x in t for x in ['v5.4', 'professional.edition', 'keygen', 'crack']):
        return False
    return True

def pick_best(results, query):
    """Pick the best manga result. Prefer: NZB > torrent, larger packs, English."""
    query_words = set(query.lower().split())
    
    manga_results = []
    for r in results:
        title = r.get("title", "")
        if not is_manga_result(title):
            continue
        # Score: prefer NZB, prefer larger, prefer title match
        score = 0
        if r.get("indexer", "") == "NZBgeek":
            score += 100
        # Prefer results with volume numbers (packs)
        if any(c in title.lower() for c in ['vol', 'v01', 'v1-', 'complete']):
            score += 50
        # Prefer results with manga/comic keywords
        if any(c in title.lower() for c in ['manga', 'comic', 'yen.press', 'viz', 'kodansha', 'cbz', 'epub']):
            score += 30
        # Prefer larger files (likely more content)
        size = r.get("size", 0)
        score += min(size // (100 * 1024 * 1024), 20)  # cap at 20 for ~2GB+
        
        r["_score"] = score
        manga_results.append(r)
    
    if not manga_results:
        return None
    
    manga_results.sort(key=lambda x: (-x["_score"], -x.get("size", 0)))
    return manga_results[0]

def main():
    titles = [l.strip() for l in MANGA_LIST.read_text().splitlines() if l.strip()]
    total = len(titles)
    
    found = []
    not_found = []
    errors = []
    
    for i, title in enumerate(titles, 1):
        query = title + " manga"
        results = search_prowlarr(query)
        
        if not results:
            not_found.append(title)
            if i % 20 == 0:
                print(f"  [{i}/{total}] Queue: {len(found)} | NotFound: {len(not_found)}")
            time.sleep(1.5)
            continue
        
        best = pick_best(results, title)
        if not best:
            not_found.append(title)
            time.sleep(1.5)
            continue
        
        dl_url = best.get("downloadUrl") or best.get("guid", "")
        if not dl_url:
            not_found.append(title)
            continue
        
        if queue_nzb(dl_url, best["title"]):
            size_mb = best.get("size", 0) // (1024 * 1024)
            found.append(f"{title} ({size_mb}MB, {best.get('indexer', '?')})")
            print(f"  [{i}/{total}] ✅ {title[:50]} - {size_mb}MB via {best.get('indexer', '?')}")
        else:
            errors.append(f"{title}: queue failed")
            print(f"  [{i}/{total}] ❌ {title[:50]} - queue failed")
        
        time.sleep(2)
        
        if i % 25 == 0:
            print(f"  --- Progress: {i}/{total} | Found: {len(found)} | Missing: {len(not_found)} | Errors: {len(errors)}")
    
    # Write report
    report = f"""MANGA DOWNLOAD REPORT
Date: {time.strftime('%Y-%m-%d %H:%M')}
Total titles: {total}
Found & Queued: {len(found)}
Not Found: {len(not_found)}
Errors: {len(errors)}

QUEUED ({len(found)}):
"""
    for f in found:
        report += f"  ✅ {f}\n"
    
    report += f"\nNOT FOUND ({len(not_found)}):\n"
    for nf in not_found:
        report += f"  ❌ {nf}\n"
    
    if errors:
        report += f"\nERRORS ({len(errors)}):\n"
        for e in errors:
            report += f"  ⚠️  {e}\n"
    
    REPORT.write_text(report)
    print(f"\n{'='*60}")
    print(f"Done! Queued: {len(found)} | Not found: {len(not_found)} | Errors: {len(errors)}")
    print(f"Report: {REPORT}")

if __name__ == "__main__":
    main()
