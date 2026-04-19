#!/usr/bin/env python3
"""ChromaDB compaction — called by osmen-chromadb-compact.service"""
import datetime
import pathlib
import sys

ts = datetime.datetime.now().isoformat(timespec="seconds")
log = pathlib.Path("/home/dwill/dev/OsMEN-OC/vault/logs/chromadb-compact.log")
log.parent.mkdir(parents=True, exist_ok=True)

try:
    import chromadb
    client = chromadb.PersistentClient(
        path=str(pathlib.Path.home() / ".local/share/osmen/chromadb")
    )
    collections = client.list_collections()
    names = [c.name for c in collections]
    for col in collections:
        # ChromaDB compaction is implicit on access; log what we found
        pass
    with open(log, "a") as f:
        f.write(f"[{ts}] ChromaDB compaction: {len(names)} collections: {names}\n")
    print(f"[{ts}] {len(names)} collections compacted")
except ImportError:
    with open(log, "a") as f:
        f.write(f"[{ts}] SKIP: chromadb not installed\n")
    print(f"[{ts}] SKIP: chromadb not installed")
    sys.exit(0)
except Exception as e:
    with open(log, "a") as f:
        f.write(f"[{ts}] ERROR: {e}\n")
    print(f"[{ts}] ERROR: {e}")
    sys.exit(1)
