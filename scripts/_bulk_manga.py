#!/usr/bin/env python3
"""
Bulk manga downloader - uses nsenter to reach Prowlarr inside gluetun's network namespace.
"""
import json, sys, time, xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.parse import quote
from urllib.error import HTTPError, URLError

PROWLARR_KEY = "72844585a87d45239efce069e1ed73a8"
SABNZBD_URL = "http://127.0.0.1:8082"
SABNZBD_KEY = "28f95b5a838e4421af5d32dfaa58303d"
NZBGEEK_KEY = "TvhZpWlqHU7ekUND5ShYVWQvRldQ5FIB"
NZBGEEK_CATS = "7020,7030,7000"

# Prowlarr now directly accessible on 127.0.0.1:9696 via download-stack pod

def prowlarr_get(url):
    """Make HTTP GET to Prowlarr."""
    full = f"http://127.0.0.1:9696{url}"
    try:
        with urlopen(full, timeout=25) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        return ''

def search_prowlarr(query):
    url = f"/api/v1/search?apikey={PROWLARR_KEY}&query={quote(query)}&limit=50"
    try:
        data = json.loads(prowlarr_get(url))
        results = []
        for r in data:
            title = r.get("title", "")
            cats = [c.get("name", "").lower() for c in r.get("categories", [])]
            if any(kw in title.lower() for kw in ["manga", "yen.press", "viz", "kodansha", "seven.seas", "comic", "cbz", "epub", "vol.", "volume", "chapter"]):
                results.append(r)
            elif "books" in cats or "literature" in cats:
                if r not in results:
                    results.append(r)
        return results
    except Exception as e:
        print(f"  Prowlarr error: {e}", file=sys.stderr)
        return []

def search_nzbgeek_direct(query):
    url = f"https://api.nzbgeek.info/api?t=search&q={quote(query)}&cat={NZBGEEK_CATS}&apikey={NZBGEEK_KEY}&limit=50"
    try:
        req = Request(url)
        with urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        results = []
        for item in root.findall(".//item"):
            title_el = item.find("title")
            if title_el is None:
                continue
            title = title_el.text or ""
            enc = item.find("enclosure")
            size = int(enc.get("length", 0)) if enc is not None else 0
            link_el = item.find("link")
            link = link_el.text if link_el is not None else ""
            results.append({"title": title, "size": size, "downloadUrl": link, "indexer": "NZBgeek", "guid": item.findtext("guid", "")})
        return results
    except Exception as e:
        print(f"  NZBgeek error: {e}", file=sys.stderr)
        return []

def send_to_sabnzbd(nzb_url, title, category="manga"):
    url = f"{SABNZBD_URL}/api?mode=addurl&name={quote(nzb_url)}&apikey={SABNZBD_KEY}&cat={category}"
    try:
        req = Request(url)
        with urlopen(req, timeout=15) as resp:
            result = resp.read().decode("utf-8")
        return "ok" in result.lower()
    except Exception as e:
        print(f"  SABnzbd error: {e}", file=sys.stderr)
        return False

def search_and_download(query):
    """Search and download best result. Returns: 'queued', 'not_found', 'error'"""
    # Check if Prowlarr has any indexers configured
    prowlarr_results = search_prowlarr(query)
    nzbgeek_results = search_nzbgeek_direct(query)

    all_results = []
    for r in prowlarr_results:
        all_results.append({
            "title": r.get("title", ""),
            "size": r.get("size", 0),
            "indexer": r.get("indexer", "?"),
            "downloadUrl": r.get("downloadUrl", r.get("guid", "")),
            "seeders": r.get("seeders", 0),
        })
    all_results.extend(nzbgeek_results)

    # Dedup
    seen = set()
    unique = []
    for r in all_results:
        key = r["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Sort: prefer NZB over torrent, then larger packs
    unique.sort(key=lambda x: (0 if x["indexer"] == "NZBgeek" else 1, -x["size"]))

    if not unique:
        return "not_found", None

    best = unique[0]
    size_mb = best["size"] // (1024 * 1024)
    proto = "NZB" if best["indexer"] == "NZBgeek" else "Torrent"
    print(f"  Best: [{proto}] {size_mb}MB | {best['title'][:70]}")

    if send_to_sabnzbd(best["downloadUrl"], best["title"]):
        return "queued", best["title"]
    else:
        return "error", best["title"]

def main():
    with open("/home/dwill/dev/OsMEN-OC/state/manga_list_300.txt") as f:
        titles = [line.strip() for line in f if line.strip()]

    total = len(titles)
    queued = []
    not_found = []
    errors = []

    print(f"Starting bulk download of {total} manga titles...")
    
    # Quick check - verify Prowlarr is reachable and has indexers
    try:
        indexers = json.loads(prowlarr_get(f"/api/v1/indexer?apikey={PROWLARR_KEY}"))
        if not indexers:
            print("WARNING: Prowlarr has no indexers configured! Results will be limited to NZBgeek direct.")
        else:
            enabled = [i["name"] for i in indexers if i.get("enable")]
            print(f"Prowlarr indexers enabled: {', '.join(enabled[:5])}{'...' if len(enabled) > 5 else ''}")
    except Exception as e:
        print(f"WARNING: Could not check Prowlarr indexers: {e}")

    for i, title in enumerate(titles, 1):
        print(f"\n[{i}/{total}] {title}")
        status, detail = search_and_download(title)
        if status == "queued":
            queued.append(title)
            print(f"  ✅ Queued: {detail}")
        elif status == "not_found":
            not_found.append(title)
            print(f"  ❌ Not found")
        else:
            errors.append(f"{title}: {detail}")
            print(f"  ⚠️ Error: {detail}")
        
        if i % 10 == 0:
            print(f"\n  --- Progress: {len(queued)} queued, {len(not_found)} not found, {len(errors)} errors ---")
        
        time.sleep(3)

    # Get SABnzbd queue size
    try:
        q_url = f"{SABNZBD_URL}/api?mode=queue&output=json&apikey={SABNZBD_KEY}"
        with urlopen(q_url, timeout=10) as resp:
            qdata = json.loads(resp.read())
        queue_size = qdata.get("queue", {}).get("noofslots", 0)
    except:
        queue_size = "?"
    
    report = f"""MANGA DOWNLOAD REPORT
Date: 2026-04-16
Total titles: {total}
Found & Queued: {len(queued)}
Not Found: {len(not_found)}
Errors: {len(errors)}
Queue Size: {queue_size}
---
NOT FOUND TITLES:
"""
    for t in not_found:
        report += f"- {t}\n"
    report += f"""---
ERRORS:
"""
    for e in errors:
        report += f"- {e}\n"

    with open("/home/dwill/dev/OsMEN-OC/state/manga_download_report.txt", "w") as f:
        f.write(report)
    
    print(f"\n{'='*60}")
    print(f"DONE! Queued: {len(queued)}, Not found: {len(not_found)}, Errors: {len(errors)}")
    print(f"Report: /home/dwill/dev/OsMEN-OC/state/manga_download_report.txt")

if __name__ == "__main__":
    main()
