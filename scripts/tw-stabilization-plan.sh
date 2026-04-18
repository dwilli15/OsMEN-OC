#!/usr/bin/env bash
# OsMEN-OC Stabilization — TW Mutations
# Generated: 2026-04-18 00:40 CDT
#
# This script IS the plan. TW is the bible.
# Every task here is real, fully described, properly placed in the
# existing project schema, and wired with depends: chains.
#
# Run with: bash scripts/tw-stabilization-plan.sh
# Review first. No stubs.
set -euo pipefail

echo "=== PHASE 0: CLOSE DEAD TASKS ==="
echo "Closing stale, duplicate, completed, and test-artifact tasks..."

# P22.17 Tailscale mesh — deprecated, non-critical, every audit says close it
task 6b27359c-ebf6-45af-9782-06cb6460dbe6 done rc.confirmation=off <<< 'y' || true
task 6b27359c-ebf6-45af-9782-06cb6460dbe6 annotate "CLOSED 2026-04-18: Tailscale intentionally non-critical. Installed but dormant. Formally deprecated per operator + 4 audit passes." 2>/dev/null || true

# Handoff 2026-04-17 — superseded by 2026-04-18 handoff
task d22320ce-5486-41d6-b984-c4f9ff3f3aca done rc.confirmation=off <<< 'y' || true
task d22320ce-5486-41d6-b984-c4f9ff3f3aca annotate "CLOSED 2026-04-18: Superseded by osmen-handoff-2026-04-18.md. VPN split routing claim was wrong — VPN egress verified correct." 2>/dev/null || true

# COMICS-029 manga torrents — annotation says completed
task 3fba28e2-5c89-49da-b2a3-8d1b6e6f929e done rc.confirmation=off <<< 'y' || true
task 3fba28e2-5c89-49da-b2a3-8d1b6e6f929e annotate "CLOSED 2026-04-18: 15 series completed via aria2c/Nyaa.si. ~8.4GB downloaded." 2>/dev/null || true

# COMICS-019 manga download running — process finished (49 downloaded, 23 failed)
task c717e915-* done rc.confirmation=off <<< 'y' || true
task c717e915-* annotate "CLOSED 2026-04-18: MangaDex bulk download complete. 49/72 downloaded, 23 failed (external-only). Process exited cleanly." 2>/dev/null || true

# Download found manga via SABnzbd — done, 104 volumes downloaded
task 20efc869-* done rc.confirmation=off <<< 'y' || true
task 20efc869-* annotate "CLOSED 2026-04-18: 104 Yen Press volumes downloaded via SABnzbd+Eweka. PDFs copied to manga library." 2>/dev/null || true

# P16.4 duplicate — 780c92a0 is a duplicate of 22c73013
task 780c92a0-d2d9-4f3f-a1a6-5a3fcac09005 done rc.confirmation=off <<< 'y' || true
task 780c92a0-d2d9-4f3f-a1a6-5a3fcac09005 annotate "CLOSED 2026-04-18: Duplicate of 22c73013 (P16.4 Configure Nextcloud admin). Keeping the original." 2>/dev/null || true

# Test artifacts — delete, not done
task f162f741-* delete rc.confirmation=off <<< 'y' || true
task 6ed59689-* delete rc.confirmation=off <<< 'y' || true
task 9f9b49e8-* delete rc.confirmation=off <<< 'y' || true
task 64c31656-* delete rc.confirmation=off <<< 'y' || true

echo ""
echo "=== PHASE 0: CONSOLIDATE FRAGMENTED PROJECTS ==="
echo "Moving Comics/* and manga/* into osmen.media.pipeline with proper tags..."

# Comics tasks → osmen.media.pipeline +comics
for uuid in \
  58a28e05-* \
  596f59ac-* \
  e3777ec3-* \
  f4052196-* \
  c717e915-* \
  3fba28e2-*; do
  task "$uuid" modify project:osmen.media.pipeline +comics rc.confirmation=off 2>/dev/null || true
done

# Manga tasks → osmen.media.pipeline +manga
for uuid in \
  2916dbc4-* \
  20efc869-* \
  cd799283-* \
  f9da6576-* \
  2e9c45da-*; do
  task "$uuid" modify project:osmen.media.pipeline +manga rc.confirmation=off 2>/dev/null || true
done

echo ""
echo "=== PHASE 0: FIX STALE ANNOTATIONS ==="
echo "Correcting 'Blocked on P19' lies and VPN split routing misconceptions..."

# Fix "Blocked on P19" — P19 completed 2026-04-16
for uuid in \
  e82cf34f-f6a9-4180-a7e8-f9170aaf587d \
  a65adb44-84c2-4cfb-9e32-d14c9a8fd3ca \
  6d075a81-3caf-4c87-95e5-90f9e6f41955 \
  a50716ac-69e6-4495-94ab-877565242c80 \
  193228cf-dd53-4672-9afc-57063a773a5a \
  e1b155e7-c027-4d22-bc5b-f45727cf6595 \
  2d27cc01-71fb-4fba-b736-9c06cc4292dd \
  063fb19f-342a-4daf-9613-c6def0f8d3f7 \
  698baa34-892d-4301-bb3e-29af419c334d; do
  task "$uuid" annotate "CORRECTED 2026-04-18: P19 orchestration spine COMPLETED 2026-04-16. This task is no longer blocked on P19. Re-evaluate independently." 2>/dev/null || true
done

# Fix COMICS-024 VPN misconception
task 596f59ac-* annotate "CORRECTED 2026-04-18: Not 'VPN split routing' — the actual fix is adding FIREWALL_OUTBOUND_SUBNETS to gluetun config to allow local subnet access. VPN egress routing is verified correct." 2>/dev/null || true

# Fix COMICS-028 same misconception
task e3777ec3-* annotate "CORRECTED 2026-04-18: Same root cause as COMICS-024. Fix is FIREWALL_OUTBOUND_SUBNETS in gluetun, not split routing." 2>/dev/null || true

echo ""
echo "=== ADD NEW TASKS — PHASE 0: PREREQUISITES ==="
echo "These must complete before any container work. No dependencies on other new tasks."

# Merge conflicts
MERGE_CONFLICTS_UUID=$(task add \
  "Resolve git merge conflicts in 5 core quadlets (chromadb, network, postgres, redis, core-slice) — keep HEAD versions" \
  project:osmen.maint priority:H \
  +fix_needed +quadlet +phase0 \
  rc.verbose=nothing 2>&1 | grep -oP '[0-9a-f-]{36}' || true)
echo "Created merge-conflicts task"

# Store UUIDs for dependency wiring
task +LATEST annotate "Files: osmen-core-chromadb.container, osmen-core.network, osmen-core-postgres.container, osmen-core-redis.container, user-osmen-core.slice. All have <<<<<<< HEAD markers. Keep HEAD version (correct \$\${VAR} escaping, 10.89.0.0/24 subnet). Without this fix, systemctl --user daemon-reload cannot generate any quadlet units." 2>/dev/null || true

# ReadOnly fix
task add \
  "Fix ReadOnly=true on 20+ container quadlets — add Tmpfs=/tmp or remove ReadOnly where linuxserver.io images need writable temp dirs" \
  project:osmen.maint priority:H \
  +fix_needed +quadlet +phase0 \
  rc.verbose=nothing
task +LATEST annotate "Affected: chromadb (comment says removed but directive still present), postgres, redis, caddy, gateway, bazarr, lidarr, mylar3, radarr, readarr, sonarr, plex, sabnzbd, prowlarr, qbittorrent, tautulli, grafana, uptimekuma, portall, prometheus, kometa. For linuxserver.io images, either add Tmpfs=/tmp alongside ReadOnly=true, or remove ReadOnly=true entirely." 2>/dev/null || true

# Pin floating images
task add \
  "Pin 3 floating container images — SABnzbd :latest→:4.5.1, Komga-comics :latest→stable+remove AutoUpdate=registry, Readarr :nightly→stable" \
  project:osmen.media.pipeline priority:H \
  +fix_needed +quadlet +phase0 \
  rc.verbose=nothing
task +LATEST annotate "SABnzbd :latest caused wizard regression when container recreated with newer image. Komga-comics is the ONLY container with AutoUpdate=registry — remove it. Readarr :nightly is reckless for persistent service." 2>/dev/null || true

# PUID/PGID
task add \
  "Add PUID=1000 PGID=1000 to 6+ linuxserver.io container quadlets missing user mapping" \
  project:osmen.maint priority:M \
  +fix_needed +quadlet +phase0 \
  rc.verbose=nothing
task +LATEST annotate "Missing on: Sonarr, Radarr, Lidarr, SABnzbd, Bazarr, Mylar3, Readarr. Only Prowlarr currently sets PUID/PGID. Without these, containers run as root inside, causing permission mismatches on mounted volumes." 2>/dev/null || true

# Duplicate HealthCmd
task add \
  "Remove duplicate HealthCmd directives from chromadb, postgres, redis quadlets — Podman uses last-wins, first is dead code" \
  project:osmen.maint priority:L \
  +fix_needed +quadlet +phase0 \
  rc.verbose=nothing

# Recover daily notes
task add \
  "Recover openclaw/memory/2026-04-16.md from git history — original content overwritten with duplicate manga session data" \
  project:osmen.maint priority:M \
  +fix_needed +phase0 \
  rc.verbose=nothing
task +LATEST annotate "Original had critical records: memory maintenance implementation, 859 test results, cron fix root cause, RustDesk notes, model fallback disaster, P13-P22 completion status, fstab entries, PR #46 info. Run: git show HEAD:openclaw/memory/2026-04-16.md > /tmp/recovery.md and merge." 2>/dev/null || true

# Verify postgres/redis units
task add \
  "Verify postgres and redis systemd user units load after daemon-reload — currently showing not-found despite symlinks existing" \
  project:osmen.maint priority:H \
  +fix_needed +phase0 \
  rc.verbose=nothing
task +LATEST annotate "Both osmen-core-postgres.service and osmen-core-redis.service show not-found in systemctl --user. Symlinks exist in ~/.config/containers/systemd/ and point to real files. Root cause is likely the git merge conflicts blocking the quadlet generator. Should resolve after merge conflict fix + daemon-reload." 2>/dev/null || true

echo ""
echo "=== ADD NEW TASKS — PHASE 2: SAB WIZARD ==="

task add \
  "Fix SABnzbd wizard regression — ensure config volume persistence so sabnzbd.ini survives container restarts" \
  project:osmen.media.pipeline priority:H \
  +fix_needed +phase2 \
  rc.verbose=nothing
task +LATEST annotate "Live audit 2026-04-18 23:50: http://127.0.0.1:8082/ redirects to /wizard/ and page title is 'SABnzbd Quick-Start Wizard'. API still answers version 4.5.5. Root cause per research: SABnzbd enters wizard when /config/sabnzbd.ini is missing or unreadable. Verify osmen-sab-config.volume mounts correctly to /config after download-stack reconciliation. Re-complete wizard with Eweka (news.eweka.nl:563 SSL, 50 connections). Backup config after completion." 2>/dev/null || true

echo ""
echo "=== ADD NEW TASKS — PHASE 4: FLARESOLVERR ROUTING ==="

task add \
  "Add FIREWALL_OUTBOUND_SUBNETS=10.89.0.0/24,192.168.4.0/24 to gluetun container environment for FlareSolverr + local service access" \
  project:osmen.media.pipeline priority:M \
  +fix_needed +phase4 \
  rc.verbose=nothing
task +LATEST annotate "FlareSolverr is deployed as osmen-media-flaresolverr on port 8191 and works standalone. Prowlarr inside the VPN pod cannot reach it because gluetun blocks local subnet traffic. This one env var addition fixes COMICS-024 and COMICS-028. Also enables arr apps outside the pod to reach download clients via the shared osmen-media.network." 2>/dev/null || true

echo ""
echo "=== ADD NEW TASKS — INFRASTRUCTURE GAPS ==="

# Fix komga-comics quadlet
task add \
  "Fix malformed osmen-media-komga-comics.container quadlet — add Unit section, pin image version, use named volume, add health check" \
  project:osmen.media.pipeline priority:M \
  +fix_needed +quadlet \
  rc.verbose=nothing
task +LATEST annotate "Current file is missing [Unit] section (no After/Requires), uses :latest tag, has hardcoded paths (/home/dwill/media/comics instead of %h/media/comics), uses hardcoded config path instead of named volume, has AutoUpdate=registry with :latest (uncontrolled updates), and no health check." 2>/dev/null || true

# Git working tree reconciliation
task add \
  "Commit stabilization changes to git — quadlet fixes, new scripts, updated docs. One clean reconciliation commit after stabilization completes." \
  project:osmen.maint priority:M \
  +cleanup +git \
  rc.verbose=nothing
task +LATEST annotate "Working tree has 10 modified files (quadlets, scripts, docs, memory) and 15+ untracked files (new quadlets, acquisition scripts, handoff docs, state artifacts). Commit intentional improvements, gitignore or remove temp files. Do AFTER stabilization so the commit represents a known-good state." 2>/dev/null || true

echo ""
echo "=== MODIFY EXISTING TASKS — FIX PRIORITIES AND DESCRIPTIONS ==="

# Prowlarr search: demote from H to M (blocked on earlier phases)
task f35bf91c-870d-4d92-8ad1-8db945b0feaf modify priority:M rc.confirmation=off
task f35bf91c-870d-4d92-8ad1-8db945b0feaf annotate "PRIORITY CHANGE 2026-04-18: Demoted H→M. Cannot diagnose search behavior until download-stack is reconciled, SAB wizard is fixed, and qBit auth is recovered. Depends on phases 1-3." 2>/dev/null || true

# Manga library setup: demote from H to L (operational, not install-critical)
task 2916dbc4-* modify priority:L rc.confirmation=off 2>/dev/null || true
task 2916dbc4-* annotate "PRIORITY CHANGE 2026-04-18: Demoted H→L. This is operational content acquisition, not install-critical. Bulk download finished (49/72 from MangaDex + 104 Yen Press + 15 Nyaa torrents). Remaining work is post-processing." 2>/dev/null || true

echo ""
echo "=== WIRE DEPENDENCY CHAINS ==="
echo "This is where the 6-phase ordering gets encoded into TW's depends: field."
echo ""
echo "Phase ordering:"
echo "  Phase 0 (prerequisites) → no deps, first to run"
echo "  Phase 1 (download-stack, e9d3e070) → depends on phase 0 merge-conflict + postgres/redis verify"
echo "  Phase 2 (SAB wizard, new) → depends on phase 1"
echo "  Phase 3 (qBit auth, 39477865) → depends on phase 1"
echo "  Phase 4 (Prowlarr, f35bf91c) → depends on phase 2 + phase 3"
echo "  Phase 5 (TW cleanup, e94c22a8) → depends on phase 4"
echo ""
echo "NOTE: depends: wiring requires UUIDs of the newly created tasks."
echo "Run the ADD commands above first, then use 'task <filter> uuids' to get them."
echo ""

# We need the UUIDs of newly created tasks to wire deps.
# This section must be run AFTER the adds above.

echo "Fetching UUIDs for newly created tasks..."
MERGE_UUID=$(task +phase0 +quadlet description.contains:'merge conflicts' uuids 2>/dev/null | tr -d '\n')
READONLY_UUID=$(task +phase0 +quadlet description.contains:'ReadOnly' uuids 2>/dev/null | tr -d '\n')
PIN_UUID=$(task +phase0 +quadlet description.contains:'Pin 3' uuids 2>/dev/null | tr -d '\n')
PUID_UUID=$(task +phase0 +quadlet description.contains:'PUID' uuids 2>/dev/null | tr -d '\n')
PG_REDIS_UUID=$(task +phase0 description.contains:'postgres and redis systemd' uuids 2>/dev/null | tr -d '\n')
SAB_WIZARD_UUID=$(task +phase2 description.contains:'SABnzbd wizard' uuids 2>/dev/null | tr -d '\n')
FLARESOLVERR_UUID=$(task +phase4 description.contains:'FIREWALL_OUTBOUND' uuids 2>/dev/null | tr -d '\n')

echo "  merge-conflicts: $MERGE_UUID"
echo "  readonly-fix:    $READONLY_UUID"
echo "  pin-images:      $PIN_UUID"
echo "  puid-pgid:       $PUID_UUID"
echo "  pg-redis-verify: $PG_REDIS_UUID"
echo "  sab-wizard:      $SAB_WIZARD_UUID"
echo "  flaresolverr:    $FLARESOLVERR_UUID"

# Phase 1 depends on Phase 0 critical items
if [ -n "$MERGE_UUID" ] && [ -n "$PG_REDIS_UUID" ] && [ -n "$READONLY_UUID" ] && [ -n "$PIN_UUID" ]; then
  echo "Wiring Phase 1 (download-stack e9d3e070) depends on Phase 0..."
  task e9d3e070-b177-409f-9cff-6762ab8ba326 modify \
    depends:"$MERGE_UUID","$PG_REDIS_UUID","$READONLY_UUID","$PIN_UUID" \
    rc.confirmation=off
fi

# Phase 2 (SAB wizard) depends on Phase 1
if [ -n "$SAB_WIZARD_UUID" ]; then
  echo "Wiring Phase 2 (SAB wizard) depends on Phase 1..."
  task "$SAB_WIZARD_UUID" modify \
    depends:e9d3e070-b177-409f-9cff-6762ab8ba326 \
    rc.confirmation=off
fi

# Phase 3 (qBit auth) depends on Phase 1
echo "Wiring Phase 3 (qBit auth 39477865) depends on Phase 1..."
task 39477865-8454-4864-9ccd-2431def4e173 modify \
  depends:e9d3e070-b177-409f-9cff-6762ab8ba326 \
  rc.confirmation=off

# Phase 4 (Prowlarr f35bf91c) depends on Phase 2 + Phase 3
if [ -n "$SAB_WIZARD_UUID" ]; then
  echo "Wiring Phase 4 (Prowlarr f35bf91c) depends on Phase 2 + Phase 3..."
  task f35bf91c-870d-4d92-8ad1-8db945b0feaf modify \
    depends:"$SAB_WIZARD_UUID",39477865-8454-4864-9ccd-2431def4e173 \
    rc.confirmation=off
fi

# Phase 4 FlareSolverr depends on Phase 1 (needs stable gluetun)
if [ -n "$FLARESOLVERR_UUID" ]; then
  echo "Wiring FlareSolverr depends on Phase 1..."
  task "$FLARESOLVERR_UUID" modify \
    depends:e9d3e070-b177-409f-9cff-6762ab8ba326 \
    rc.confirmation=off
fi

# Phase 5 (cron cleanup e94c22a8) depends on Phase 4
echo "Wiring Phase 5 (cleanup e94c22a8) depends on Phase 4..."
task e94c22a8-6505-4950-97d2-d2951320b9a5 modify \
  depends:f35bf91c-870d-4d92-8ad1-8db945b0feaf \
  rc.confirmation=off

# Media pipeline tasks depend on Prowlarr stabilization
echo "Wiring media pipeline tasks to depend on Prowlarr stabilization..."
for uuid in \
  d5d7e885-62f9-4537-bcd8-7c57452968f3 \
  3550426b-d80a-4261-b25f-d968be16bffa \
  2fca00f8-3fca-4189-8aaa-3882d5cded56; do
  task "$uuid" modify depends:f35bf91c-870d-4d92-8ad1-8db945b0feaf rc.confirmation=off 2>/dev/null || true
done

# Lidarr/Readarr root folder depends on Prowlarr app sync
task 7c09fe94-4bfb-4fa9-8778-5f26d396913a modify depends:3550426b-d80a-4261-b25f-d968be16bffa rc.confirmation=off 2>/dev/null || true
task 64b22a1f-ad3d-4556-bb20-75cc5dae6757 modify depends:3550426b-d80a-4261-b25f-d968be16bffa rc.confirmation=off 2>/dev/null || true

# Bazarr verify depends on arr stack being stable
task de9510c8-7d59-4da3-87a7-63a6cf9ccd20 modify depends:f35bf91c-870d-4d92-8ad1-8db945b0feaf rc.confirmation=off 2>/dev/null || true

# COMICS-024/028 depend on FlareSolverr routing fix
if [ -n "$FLARESOLVERR_UUID" ]; then
  task 596f59ac-* modify depends:"$FLARESOLVERR_UUID" rc.confirmation=off 2>/dev/null || true
  task e3777ec3-* modify depends:"$FLARESOLVERR_UUID" rc.confirmation=off 2>/dev/null || true
fi

echo ""
echo "=== VERIFY FINAL STATE ==="
echo ""
task status:pending project:osmen.install count rc.verbose=nothing
echo " install tasks pending"
task status:pending project:osmen.media.pipeline count rc.verbose=nothing
echo " media pipeline tasks pending"
task status:pending project:osmen.maint count rc.verbose=nothing
echo " maintenance tasks pending"
task status:pending count rc.verbose=nothing
echo " TOTAL tasks pending"
echo ""
echo "=== DEPENDENCY GRAPH (text) ==="
task status:pending depends.any: rc.verbose=nothing rc.report.list.columns=id,depends,description rc.report.list.labels=ID,Deps,Description list 2>/dev/null || true
echo ""
echo "Done. TW is the plan. TaskFlow executes it."
