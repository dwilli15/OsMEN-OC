#!/usr/bin/env python3
"""Verify Plex Media Server health."""
import os, requests

PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "NaxyQSk5i2fnKQyctmQg")

def check():
    issues = []
    try:
        r = requests.get(f"{PLEX_URL}/identity", timeout=5,
                         headers={"Accept": "application/json"})
        if r.status_code != 200:
            issues.append(f"Identity endpoint returned {r.status_code}")
        else:
            data = r.json().get("MediaContainer", {})
            print(f"Plex: v{data.get('version', 'unknown')} (claimed={data.get('claimed', '?')})")
    except requests.ConnectionError:
        issues.append("Cannot connect to Plex")
        return issues

    r = requests.get(f"{PLEX_URL}/library/sections",
                     headers={"X-Plex-Token": PLEX_TOKEN, "Accept": "application/json"},
                     timeout=5)
    data = r.json().get("MediaContainer", {})
    sections = data.get("Directory", [])
    print(f"Libraries: {len(sections)}")
    for sec in sections:
        print(f"  {sec['title']}: {sec.get('type','?')}")

    if not sections:
        issues.append("No libraries configured")

    return issues

if __name__ == "__main__":
    issues = check()
    if issues:
        print("\nISSUES:")
        for i in issues:
            print(f"  - {i}")
    else:
        print("\nAll checks passed")
