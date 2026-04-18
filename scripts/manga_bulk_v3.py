#!/usr/bin/env python3
"""OsMEN-OC Manga Bulk Downloader v3 - Handles both NZB (SABnzbd) and torrents (qBittorrent)."""

import json
import sys
import time
import hashlib
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote

PROWLARR_KEY = "72844585a87d45239efce069e1ed73a8"
SABNZBD_KEY = "28f95b5a838e4421af5d32dfaa58303d"

PROWLARR_URL = "http://127.0.0.1:9696"
SABNZBD_URL = "http://127.0.0.1:8082"
QBIT_URL = "http://127.0.0.1:9090"
QBIT_COOKIE_FILE = "/tmp/qbit_manga_cookie.txt"

MANGA_LIST = Path("/home/dwill/dev/OsMEN-OC/state/manga_list_300.txt")
REPORT = Path("/home/dwill/dev/OsMEN-OC/state/manga_download_report.txt")

qbit_cookie = None

def sab_add_nzb(nzb_url):
    """Add NZB to SABnzbd (no category - use default)."""
    try:
        url = f"{SABNZBD_URL}/api?mode=addurl&name={quote(nzb_url)}&apikey={SABNZBD_KEY}"
        resp = urlopen(Request(url), timeout=10)
        return "true" in resp.read().decode().lower()
    except:
        return False

def search(query):
    """Search Prowlarr."""
    url = f"{PROWLARR_URL}/api/v1/search?apikey={PROWLARR_KEY}&query={quote(query)}&limit=20"
    try:
        resp = urlopen(Request(url), timeout=20)
        return json.loads(resp.read())
    except:
        return []

def is_good(title):
    """Filter out non-manga."""
    t = title.lower()
    if any(x in t for x in ['.mkv', '.mp4', '.avi', 'xxx', 'hentai', '+18']):
        return False
    if any(x in t for x in ['v5.4', 'professional.edition', 'keygen']):
        return False
    return True

def pick_best(results):
    """Pick best manga result."""
    scored = []
    for r in results:
        title = r.get("title", "")
        if not is_good(title):
            continue
        score = 0
        idx = r.get("indexer", "")
        if idx == "NZBgeek":
            score += 100
        # Deprioritize Nyaa (magnet-only, SABnzbd can't use)
        if idx == "Nyaa":
            score += 0
        # Prefer results with actual downloadUrl
        if r.get("downloadUrl"):
            score += 150
        t = title.lower()
        if any(c in t for c in ['vol', 'v01', 'v1-', 'complete', 'batch']):
            score += 50
        if any(c in t for c in ['manga', 'comic', 'yen.press', 'viz', 'kodansha', 'cbz']):
            score += 30
        score += min(r.get("size", 0) // (100*1024*1024), 20)
        r["_score"] = score
        scored.append(r)
    scored.sort(key=lambda x: (-x["_score"], -x.get("size", 0)))
    return scored[0] if scored else None

def qbit_login():
    """Login to qBittorrent with permanent password."""
    try:
        data = "username=admin\def qbit_login():password=osmen2024".encode()
        req = Request(f"{QBIT_URL}/api/v2/auth/login", data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urlopen(req, timeout=10)
        cookie = resp.headers.get("Set-Cookie", "").split(";")[0]
        if cookie:
            with open(QBIT_COOKIE_FILE, "w") as f:
                f.write(cookie)
            return True
    except:
        pass
    return False


    """Login to qBittorrent."""
    import subprocess
    # Try current temp password first
    try:
        # Get temp password from logs
        logs = subprocess.check_output(['podman', 'logs', 'osmen-media-qbittorrent'], text=True, stderr=subprocess.STDOUT)
        import re
        m = re.search(r'A temporary password is provided for this session: (\S+)', logs)
        if m:
            pwd = m.group(1)
            data = f'username=admin&password={pwd}'.encode()
            req = Request(f'{QBIT_URL}/api/v2/auth/login', data=data, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            resp = urlopen(req, timeout=10)
            cookie = resp.headers.get('Set-Cookie', '').split(';')[0]
            if cookie:
                with open(QBIT_COOKIE_FILE, 'w') as f:
                    f.write(cookie)
                return True
    except:
        pass
    return False

def qbit_add_magnet(magnet):
    """Add magnet link to qBittorrent."""
    try:
        with open(QBIT_COOKIE_FILE) as f:
            cookie = f.read().strip()
        if not cookie:
            if not qbit_login():
                return False
            with open(QBIT_COOKIE_FILE) as f:
                cookie = f.read().strip()
        data = f'urls={quote(magnet)}'.encode()
        req = Request(f'{QBIT_URL}/api/v2/torrents/add', data=data, method='POST')
        req.add_header('Cookie', cookie)
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        resp = urlopen(req, timeout=10)
        return 'Ok' in resp.read().decode()
    except:
        return False

def download(result):
    """Download via SABnzbd (NZB) or qBittorrent (torrent)."""
    dl_url = result.get('downloadUrl', '')
    guid = result.get('guid', '')
    proto = result.get('protocol', '')
    
    # NZB - send to SABnzbd via Prowlarr proxy
    if proto == 'usenet' and dl_url:
        return sab_add_nzb(dl_url)
    
    # Torrent with .torrent file URL - SABnzbd can handle via Prowlarr proxy
    if proto == 'torrent' and dl_url:
        return sab_add_nzb(dl_url)
    
    # Magnet link only - use qBittorrent
    if guid and guid.startswith('magnet:'):
        return qbit_add_magnet(guid)
    
    return False

def main():
    titles = [l.strip() for l in MANGA_LIST.read_text().splitlines() if l.strip()]
    total = len(titles)
    
    print(f"📚 Starting manga download for {total} titles...")
    print(f"   NZB -> SABnzbd (NZB only - qBittorrent auth broken)")
    print(f"   VPN: Privado Amsterdam")
    print()
    
    found = []
    not_found = []
    errors = []
    
    for i, title in enumerate(titles, 1):
        query = title + " manga"
        results = search(query)
        
        # If no results with downloadUrl, try without "manga"
        if results and not any(r.get("downloadUrl") for r in results):
            results2 = search(title)
            # Merge and dedupe
            seen = set(r.get("title","") for r in results)
            for r in results2:
                if r.get("title","") not in seen and r.get("downloadUrl"):
                    results.append(r)
        
        if not results or not any(r.get("downloadUrl") for r in results):
            not_found.append(title)
            time.sleep(1)
            continue
        
        best = pick_best(results)
        if not best:
            not_found.append(title)
            time.sleep(1)
            continue
        
        if download(best):
            size_mb = best.get("size", 0) // (1024*1024)
            idx = best.get("indexer", "?")
            found.append(f"{title} ({size_mb}MB, {idx})")
            print(f"  [{i:3d}/{total}] ✅ {title[:45]:45s} {size_mb:>5d}MB {idx}")
        else:
            errors.append(title)
            print(f"  [{i:3d}/{total}] ❌ {title[:45]:45s} queue failed")
        
        time.sleep(2)
        
        if i % 25 == 0:
            print(f"  --- {i}/{total}: ✅{len(found)} ❌{len(not_found)} ⚠{len(errors)} ---")
    
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
