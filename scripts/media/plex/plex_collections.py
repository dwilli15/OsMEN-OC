#!/usr/bin/env python3
"""Manage Plex collections via API."""
import sys, os, json, requests

PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "NaxyQSk5i2fnKQyctmQg")
HEADERS = {"X-Plex-Token": PLEX_TOKEN, "Accept": "application/json"}

def list_collections(section_id=None):
    if section_id:
        r = requests.get(f"{PLEX_URL}/library/sections/{section_id}/collections", headers=HEADERS)
    else:
        r = requests.get(f"{PLEX_URL}/library/sections/all", headers=HEADERS)
        for sec in r.json().get("MediaContainer", {}).get("Directory", []):
            print(f"\n=== {sec['title']} ===")
            cr = requests.get(f"{PLEX_URL}/library/sections/{sec['key']}/collections", headers=HEADERS)
            for col in cr.json().get("MediaContainer", {}).get("Metadata", []):
                print(f"  {col['title']} ({col.get('leafCount', '?')} items)")
        return

    for col in r.json().get("MediaContainer", {}).get("Metadata", []):
        print(f"  {col['title']} ({col.get('leafCount', '?')} items)")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_collections(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        list_collections()
