#!/usr/bin/env python3
"""
MangaDex manga downloader — downloads chapters and packs into CBZ files.
Uses only Python stdlib (no Pillow or external deps needed).
Fixes: urllib.parse.urlencode for proper URL encoding.
"""
import urllib.request
import urllib.parse
import json
import zipfile
import os
import sys
import time
import re
import tempfile

BASE_URL = "https://api.mangadex.org"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
RATE_LIMIT = 1.0


def api_get(path, params=None):
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        url = BASE_URL + path + "?" + qs
    else:
        url = BASE_URL + path
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def search_manga(title, limit=5):
    data = api_get("/manga", {"title": title, "limit": str(limit),
                               "includes[]": "cover_art",
                               "contentRating[]": "safe"})
    results = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        titles = attrs.get("title", {})
        name = titles.get("en") or titles.get("ja-ro") or list(titles.values())[0] if titles else "?"
        results.append({"id": item["id"], "title": name, "status": attrs.get("status", "?")})
    time.sleep(RATE_LIMIT)
    return results


def get_downloadable_chapters(manga_id, lang="en"):
    """Get chapters that have actual downloadable pages (not external links)."""
    chapters = []
    offset = 0
    while True:
        data = api_get("/manga/" + manga_id + "/feed", {
            "translatedLanguage[]": lang,
            "limit": "500",
            "offset": str(offset),
            "order[chapter]": "asc",
            "includes[]": "scanlation_group",
        })
        batch = data.get("data", [])
        if not batch:
            break
        for ch in batch:
            attrs = ch.get("attributes", {})
            if attrs.get("externalUrl"):
                continue
            if attrs.get("pages", 0) == 0:
                continue
            chapters.append({"id": ch["id"], "chapter": attrs.get("chapter", "?")})
        offset += 500
        time.sleep(RATE_LIMIT)
        if len(batch) < 500:
            break
    return chapters


def download_chapter_as_cbz(chapter_id, chapter_num, output_dir, manga_title):
    """Download chapter images and pack into CBZ."""
    server = api_get("/at-home/server/" + chapter_id)
    base = server.get("baseUrl", "")
    hash_val = server["chapter"]["hash"]
    pages = server["chapter"].get("dataSaver", [])
    if not pages:
        pages = server["chapter"].get("data", [])

    if not pages:
        print("    No pages found", flush=True)
        return False

    tmpdir = tempfile.mkdtemp()
    img_count = 0

    for i, page in enumerate(pages):
        img_url = base + "/data-saver/" + hash_val + "/" + page
        try:
            req = urllib.request.Request(img_url,
                headers={"User-Agent": USER_AGENT, "Referer": "https://mangadex.org/"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            ext = os.path.splitext(page)[1] or ".jpg"
            fpath = os.path.join(tmpdir, "%04d%s" % (i + 1, ext))
            with open(fpath, "wb") as f:
                f.write(data)
            img_count += 1
        except Exception as e:
            print("    Page %d failed: %s" % (i + 1, e), flush=True)
        time.sleep(0.3)

    if img_count == 0:
        os.rmdir(tmpdir)
        return False

    # Create CBZ
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', manga_title)[:80]
    cbz_name = "%s_c%s.cbz" % (safe_title, chapter_num)
    cbz_path = os.path.join(output_dir, cbz_name)
    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_STORED) as zf:
        for fname in sorted(os.listdir(tmpdir)):
            zf.write(os.path.join(tmpdir, fname), fname)

    size_mb = os.path.getsize(cbz_path) / 1048576
    print("    Saved: %s (%.1fMB, %d pages)" % (cbz_name, size_mb, img_count), flush=True)

    # Cleanup
    for fname in os.listdir(tmpdir):
        os.unlink(os.path.join(tmpdir, fname))
    os.rmdir(tmpdir)
    return True


def download_manga(manga_id, output_dir, lang="en", max_chapters=0):
    info = api_get("/manga/" + manga_id, {"includes[]": "cover_art"})
    attrs = info.get("data", {}).get("attributes", {})
    titles = attrs.get("title", {})
    title = titles.get("en") or titles.get("ja-ro") or list(titles.values())[0] if titles else "Unknown"

    print("\nDownloading: %s" % title, flush=True)
    manga_dir = os.path.join(output_dir, re.sub(r'[\\/:*?"<>|]', '_', title)[:80])
    os.makedirs(manga_dir, exist_ok=True)

    chapters = get_downloadable_chapters(manga_id, lang)
    print("  Found %d downloadable chapters" % len(chapters), flush=True)

    if max_chapters > 0:
        chapters = chapters[:max_chapters]

    ok = 0
    for ch in chapters:
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:80]
        existing = os.path.join(manga_dir, "%s_c%s.cbz" % (safe_title, ch["chapter"]))
        if os.path.exists(existing):
            print("  Skipping chapter %s (exists)" % ch["chapter"], flush=True)
            ok += 1
            continue

        if download_chapter_as_cbz(ch["id"], ch["chapter"], manga_dir, title):
            ok += 1
        time.sleep(RATE_LIMIT)

    print("  Complete: %d/%d chapters" % (ok, len(chapters)), flush=True)
    return ok


def search_and_download(query, output_dir, lang="en", max_chapters=0):
    results = search_manga(query, limit=3)
    if not results:
        print("No results for: %s" % query, flush=True)
        return False
    r = results[0]
    print("Found: %s (status: %s)" % (r["title"], r["status"]), flush=True)
    return download_manga(r["id"], output_dir, lang, max_chapters)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mangadex_dl.py <title> [output_dir] [max_chapters]")
        print("Example: python3 mangadex_dl.py 'Silent Witch' /path/to/manga 3")
        sys.exit(1)

    query = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "/run/media/dwill/Other_Media/Manga"
    maxch = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    search_and_download(query, outdir, "en", maxch)
