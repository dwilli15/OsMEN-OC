#!/usr/bin/env python3
"""
Queue all staged DC comic NZBs to SABnzbd.
Run this after configuring a Usenet server in SABnzbd.

Usage: python3 queue_all_dc_comics.py [--sab-url URL] [--sab-key KEY]
"""
import json
import os
import sys
import glob
import urllib.request
import urllib.parse
import base64
import time

DEFAULT_SAB_URL = "http://127.0.0.1:8082/api"
DEFAULT_SAB_KEY = "28f95b5a838e4421af5d32dfaa58303d"

def queue_nzb_file(sab_url, sab_key, nzb_path):
    """Upload an NZB file to SABnzbd."""
    with open(nzb_path, "rb") as f:
        nzb_data = f.read()
    
    boundary = "----PythonBoundary" + str(int(time.time()))
    body = (
        "--" + boundary + "\r\n"
        'Content-Disposition: form-data; name="apikey"\r\n\r\n'
        + sab_key + "\r\n"
        "--" + boundary + "\r\n"
        'Content-Disposition: form-data; name="mode"\r\n\r\n'
        "addfile\r\n"
        "--" + boundary + "\r\n"
        'Content-Disposition: form-data; name="name"; filename="' + os.path.basename(nzb_path) + '"\r\n'
        "Content-Type: application/x-nzb\r\n\r\n"
    ).encode() + nzb_data + ("\r\n--" + boundary + "--\r\n").encode()
    
    req = urllib.request.Request(sab_url, data=body, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get("status", False)
    except Exception as e:
        return False

def main():
    sab_url = DEFAULT_SAB_URL
    sab_key = DEFAULT_SAB_KEY
    
    # Parse args
    for i, arg in enumerate(sys.argv):
        if arg == "--sab-url" and i + 1 < len(sys.argv):
            sab_url = sys.argv[i + 1]
        elif arg == "--sab-key" and i + 1 < len(sys.argv):
            sab_key = sys.argv[i + 1]
    
    # Check SABnzbd is running
    try:
        req = urllib.request.Request(sab_url + "?apikey=" + sab_key + "&mode=version")
        with urllib.request.urlopen(req, timeout=5) as resp:
            info = json.loads(resp.read())
            print("SABnzbd v%s connected" % info.get("version", "?"))
    except Exception as e:
        print("ERROR: Cannot connect to SABnzbd: %s" % e)
        sys.exit(1)
    
    # Find all NZB files
    nzb_dirs = ["/tmp/dc-nzbs-staging", "/tmp/dc-nzbs"]
    nzb_files = []
    for d in nzb_dirs:
        if os.path.isdir(d):
            nzb_files.extend(glob.glob(os.path.join(d, "**", "*.nzb"), recursive=True))
    
    if not nzb_files:
        print("No NZB files found in %s" % nzb_dirs)
        sys.exit(1)
    
    print("Found %d NZB files to queue" % len(nzb_files))
    
    # Queue them
    ok = 0
    fail = 0
    for i, nzb in enumerate(nzb_files):
        if queue_nzb_file(sab_url, sab_key, nzb):
            ok += 1
            rel = os.path.relpath(nzb, "/tmp")
            print("  [%d/%d] OK: %s" % (i + 1, len(nzb_files), rel[:70]))
        else:
            fail += 1
            rel = os.path.relpath(nzb, "/tmp")
            print("  [%d/%d] FAIL: %s" % (i + 1, len(nzb_files), rel[:70]))
        time.sleep(0.3)
    
    print("\nQueued: %d, Failed: %d" % (ok, fail))
    if fail > 0:
        print("Some NZBs failed to queue. Check SABnzbd logs.")

if __name__ == "__main__":
    main()
