#!/usr/bin/env python3
"""Trigger Plex library scan via API."""
import sys, os, requests

PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "NaxyQSk5i2fnKQyctmQg")

def scan_all():
    requests.post(f"{PLEX_URL}/library/sections/all/refresh",
                   headers={"X-Plex-Token": PLEX_TOKEN})
    print("Library scan triggered for all sections")

def scan_section(section_id):
    requests.post(f"{PLEX_URL}/library/sections/{section_id}/refresh",
                   headers={"X-Plex-Token": PLEX_TOKEN})
    print(f"Library scan triggered for section {section_id}")

def list_sections():
    r = requests.get(f"{PLEX_URL}/library/sections",
                     headers={"X-Plex-Token": PLEX_TOKEN})
    for sec in r.json().get("MediaContainer", {}).get("Directory", []):
        print(f"  {sec['key']}: {sec['title']} ({sec.get('type','?')})")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_sections()
    elif len(sys.argv) > 1:
        scan_section(sys.argv[1])
    else:
        scan_all()
