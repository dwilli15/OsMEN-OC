#!/usr/bin/env python3
"""Bulk runner for manga_downloader.py"""
import subprocess, sys, time

LIST = "/home/dwill/dev/OsMEN-OC/state/manga_list_300.txt"
SCRIPT = "/home/dwill/dev/OsMEN-OC/scripts/manga_downloader.py"
REPORT = "/home/dwill/dev/OsMEN-OC/state/manga_download_report.txt"

with open(LIST) as f:
    titles = [line.strip() for line in f if line.strip()]

found = []
not_found = []
errors = []

total = len(titles)
for i, title in enumerate(titles, 1):
    print(f"[{i}/{total}] Searching: {title}")
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, "--search", title, "--download"],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout + result.stderr
        print(f"  -> {output.strip()[-200:]}")
        
        if result.returncode == 0 and ("queued" in output.lower() or "sent" in output.lower() or "download" in output.lower()):
            found.append(title)
        else:
            not_found.append(title)
    except Exception as e:
        print(f"  -> ERROR: {e}")
        errors.append(f"{title}: {e}")
    
    time.sleep(3)

# Write report
with open(REPORT, "w") as f:
    f.write(f"MANGA DOWNLOAD REPORT\n")
    f.write(f"Date: 2026-04-16\n")
    f.write(f"Total titles: {total}\n")
    f.write(f"Found & Queued: {len(found)}\n")
    f.write(f"Not Found: {len(not_found)}\n")
    f.write(f"Errors: {len(errors)}\n")
    f.write(f"---\nNOT FOUND TITLES:\n")
    for t in not_found:
        f.write(f"- {t}\n")
    f.write(f"---\nERRORS:\n")
    for e in errors:
        f.write(f"- {e}\n")

print(f"\nDone! Found: {len(found)}, Not found: {len(not_found)}, Errors: {len(errors)}")
print(f"Report: {REPORT}")
