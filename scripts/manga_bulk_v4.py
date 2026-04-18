#!/usr/bin/env python3
"""OsMEN-OC Manga Bulk Downloader v4 - Clean version with NZB + torrent support."""

import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote

PROWLARR_KEY = "72844585a87d45239efce069e1ed73a8"
SABNZBD_KEY = "28f95b5a838e4421af5d32dfaa58303d"
QBIT_URL = "http://127.0.0.1:9090"
QBIT_USER = "admin"
QBIT_PASS = "osmen2024"

PROWLARR_URL = "http://127.0.0.1:9696"
SABNZBD_URL = "http://127.0.0.1:8082"

MANGA_LIST = Path("/home/dwill/dev/OsMEN-OC/state/manga_list_300.txt")
REPORT = Path("/home/dwill/dev/OsMEN-OC/state/manga_download_report.txt")

qbit_sid = None

def qbit_login():
    """Login to qBittorrent and cache SID."""
    global qbit_sid
    try:
        data = f"username={QBIT_USER}&password={QBIT_PASS}".encode()
        req = Request(f"{QBIT_URL}/api/v2/auth/login", data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urlopen(req, timeout=10)
        body = resp.read().decode().strip()
        if body == "Ok.":
            qbit_sid = resp.headers.get("Set-Cookie", "").split(";")[0]
            return True
        return False
    except Exception as e:
        print(f"  qBit login error: {e}", file=sys.stderr)
        return False

def qbit_add_magnet(magnet):
    """Add magnet to qBittorrent."""
    global qbit_sid
    if not qbit_sid and not qbit_login():
        return False
    try:
        data = f"urls={quote(magnet)}".encode()
        req = Request(f"{QBIT_URL}/api/v2/torrents/add", data=data, method="POST")
        req.add_header("Cookie", qbit_sid)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urlopen(req, timeout=10)
        return "Ok" in resp.read().decode()
    except Exception as e:
        # Session might have expired, re-login once
        if qbit_login():
            return qbit_add_magnet(magnet)
        return False

def sab_add_url(dl_url):
    """Add NZB or .torrent URL to SABnzbd via Prowlarr proxy."""
    try:
        url = f"{SABNZBD_URL}/api?mode=addurl&name={quote(dl_url)}&apikey={SABNZBD_KEY}"
        resp = urlopen(Request(url), timeout=10)
        return "true" in resp.read().decode().lower()
    except:
        return False

def search(query):
    """Search Prowlarr for results."""
    url = f"{PROWLARR_URL}/api/v1/search?apikey={PROWLARR_KEY}&query={quote(query)}&limit=20"
    try:
        resp = urlopen(Request(url), timeout=20)
        return json.loads(resp.read())
    except:
        return []

def is_good(title):
    """Filter out non-manga results."""
    t = title.lower()
    if any(x in t for x in ['.mkv', '.mp4', '.avi', '.wmv', '.ts', 'xxx', 'hentai', '+18', 'porn']):
        return False
    if any(x in t for x in ['keygen', 'professional.edition', 'v5.4', 'x264', 'x265', '1080p', '720p', 'bdrip']):
        return False
    return True

def pick_best(results):
    """Score and pick the best result."""
    scored = []
    for r in results:
        title = r.get("title", "")
        if not is_good(title):
            continue
        score = 0
        idx = r.get("indexer", "")
        proto = r.get("protocol", "")
        
        # Prefer NZB (reliable downloads via Eweka when configured)
        if proto == "usenet":
            score += 100
        # Prefer NZBgeek specifically
        if idx == "NZBgeek":
            score += 50
        # Prefer results with downloadUrl (can use Prowlarr proxy)
        if r.get("downloadUrl"):
            score += 30
        # Prefer packs/batches (more content per download)
        t = title.lower()
        if any(c in t for c in ['vol', 'v01', 'v1-', 'complete', 'batch', 'v1-']):
            score += 40
        # Prefer manga/comic keywords
        if any(c in t for c in ['manga', 'comic', 'yen.press', 'viz', 'kodansha', 'cbz', 'seven.seas']):
            score += 20
        # Prefer larger files
        score += min(r.get("size", 0) // (100 * 1024 * 1024), 20)
        
        r["_score"] = score
        scored.append(r)
    
    scored.sort(key=lambda x: (-x["_score"], -x.get("size", 0)))
    return scored[0] if scored else None

def download(result):
    """Route download to correct client."""
    proto = result.get("protocol", "")
    dl_url = result.get("downloadUrl", "")
    guid = result.get("guid", "")
    
    # NZB or .torrent via Prowlarr proxy -> SABnzbd
    if dl_url:
        return sab_add_url(dl_url)
    
    # Magnet link -> qBittorrent
    if guid and guid.startswith("magnet:"):
        return qbit_add_magnet(guid)
    
    return False

def main():
    titles = [l.strip() for l in MANGA_LIST.read_text().splitlines() if l.strip()]
    total = len(titles)
    
    print(f"📚 Starting manga download for {total} titles...")
    print(f"   NZB/.torrent → SABnzbd | Magnet → qBittorrent")
    print(f"   VPN: Privado Amsterdam")
    print()
    
    # Login to qBittorrent
    if not qbit_login():
        print("WARNING: qBittorrent login failed - magnet links won't work")
    
    found = []
    not_found = []
    errors = []
    
    for i, title in enumerate(titles, 1):
        query = title + " manga"
        results = search(query)
        
        # If no results with downloadable content, try without "manga"
        if results and not any(r.get("downloadUrl") or (r.get("guid", "").startswith("magnet:")) for r in results):
            results2 = search(title)
            seen = set(r.get("title", "") for r in results)
            for r in results2:
                if r.get("title", "") not in seen:
                    results.append(r)
        
        best = pick_best(results)
        if not best:
            not_found.append(title)
            time.sleep(1)
            continue
        
        if download(best):
            size_mb = best.get("size", 0) // (1024 * 1024)
            idx = best.get("indexer", "?")
            proto = best.get("protocol", "?")
            found.append(f"{title} ({size_mb}MB, {idx}, {proto})")
            print(f"  [{i:3d}/{total}] ✅ {title[:45]:45s} {size_mb:>5d}MB {idx}")
        else:
            errors.append(title)
            print(f"  [{i:3d}/{total}] ❌ {title[:45]:45s} queue failed")
        
        time.sleep(2)
        
        if i % 25 == 0:
            print(f"  --- {i}/{total}: ✅{len(found)} ❌{len(not_found)} ⚠️{len(errors)} ---")
    
    # Report
    rpt = f"MANGA DOWNLOAD REPORT\nDate: {time.strftime('%Y-%m-%d %H:%M')}\n"
    rpt += f"Total: {total} | Queued: {len(found)} | Not found: {len(not_found)} | Errors: {len(errors)}\n\n"
    rpt += f"QUEUED ({len(found)}):\n"
    for f in found:
        rpt += f"  ✅ {f}\n"
    rpt += f"\nNOT FOUND ({len(not_found)}):\n"
    for nf in not_found:
        rpt += f"  ❌ {nf}\n"
    if errors:
        rpt += f"\nERRORS ({len(errors)}):\n"
        for e in errors:
            rpt += f"  ⚠️  {e}\n"
    
    REPORT.write_text(rpt)
    print(f"\n{'='*60}")
    print(f"Done! ✅{len(found)} | ❌{len(not_found)} | ⚠️{len(errors)}")
    print(f"Report: {REPORT}")

if __name__ == "__main__":
    main()
