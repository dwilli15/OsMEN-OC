# OsMEN-OC Master Execution Plan
## Complete Stabilization + Install + Configuration Roadmap
## Generated: 2026-04-18 04:23 CDT by Opus 4.6 (main agent)
## Source of truth: Taskwarrior | Execution engine: TaskFlow | 101 pending tasks

---

# META

## How this works
1. **Taskwarrior IS the plan.** Every task below is a real TW entry with a live UUID.
2. **TaskFlow is the engine.** It reads TW's `depends:` graph, picks unblocked tasks, spawns subagents, marks done.
3. **This file is the comprehensive view.** It contains every task, every sub-step, every command, every verification, every failure mode.
4. **If TW changes, regenerate this file.** `task status:pending export` → rebuild.

## D's decisions (LOCKED IN — do not re-ask)
- Download-stack: **(a) quadlet/systemd**
- qBittorrent: **(b) nuke and recreate**
- Nextcloud: **(a) commit**
- Calendar: **(b) bidirectional**
- PKM: **(c) fresh start**

## Model routing (LOCKED IN)
| Tier | Role | Model | Fallback |
|------|------|-------|----------|
| 🔴 Orchestration | main agent (config/install/orchestration) | `github-copilot/claude-opus-4.6` | `zai/glm-5.1` → `zai/glm-5-turbo` |
| 🟡 General | sub-agents (coder, researcher, reviewer, auditor) | `github-copilot/gpt-5.4` | `zai/glm-5-turbo` |
| 🟢 Basic | lightweight tasks (file ops, formatting, lookups) | `zai/glm-4.7-flash` | — |

## Current state (HONEST — from 10-agent recon + live TW)
- **Running:** 5 containers + Plex native + Ollama + Lemonade + OpenClaw
- **Not deployed:** 21 planned services (all arr apps, all monitoring, core DB/cache, Nextcloud, etc.)
- **Broken:** SABnzbd (wizard loop), qBittorrent (auth locked out), 3 exited containers
- **Blocking everything:** 5 merge conflicts + 4 missing slices + ReadOnly on 20+ quadlets
- **Security gap:** No firewall, SSH/Plex exposed to 0.0.0.0
- **Actual completion:** ~25% of total install/config vision
- **Estimated work to stable:** 12-18 hours of agent time, ~30 min of D's time

---

# DEPENDENCY GRAPH (7 tiers, 101 tasks)

```
═══════════════════════════════════════════════════════════════════
TIER 0 — UNBLOCK (no dependencies, start immediately)
═══════════════════════════════════════════════════════════════════
│
├── T0.1 [a8f55536] Resolve 5 git merge conflicts ──────────────┐
├── T0.2 [d217b0fc] Create 4 missing slice definitions ─────────┤
├── T0.3 [5054f274] Enable UFW firewall ──────────────────────── │ (independent)
├── T0.4 [a79d71f9] Fix ReadOnly=true on 20+ quadlets ──────────┤
├── T0.5 [23ee5db3] Pin 3 floating images ──────────────────────┤
├── T0.6 [5d93c34c] Add PUID/PGID to linuxserver containers ───┤
├── T0.7 [a785e86f] Remove duplicate HealthCmd directives ──────┤
├── T0.8 [2e7e22f7] Recover daily notes from git ───────────────┤
└── T0.9 [aa97a670] daemon-reload + verify units ───────────────┘
         ▲ depends: T0.1, T0.2, T0.4
         │
═══════════════════════════════════════════════════════════════════
TIER 1 — CORE SERVICES (depends: T0.9)
═══════════════════════════════════════════════════════════════════
│
├── T1.1 [a19101e3] Deploy PostgreSQL ───────────────────────────┐
├── T1.2 [2c73a3e6] Deploy Redis ───────────────────────────────┤
└── T1.3 [c08949ac] Deploy Caddy reverse proxy ─────────────────┘
         │
═══════════════════════════════════════════════════════════════════
TIER 2 — DOWNLOAD STACK (depends: T0.9 + T0.5)
═══════════════════════════════════════════════════════════════════
│
├── e9d3e070 Reconcile download-stack to systemd ───────────────┐
│   ├── T2.2 [ec589dc6] Fix SABnzbd wizard regression           │
│   ├── 39477865 qBittorrent auth: nuke + recreate              │
│   └── T3.4 [b30e0a61] FIREWALL_OUTBOUND_SUBNETS for gluetun  │
│                                                                │
═══════════════════════════════════════════════════════════════════
TIER 3 — ARR STACK (depends: SAB + qBit done)
═══════════════════════════════════════════════════════════════════
│
├── f35bf91c Prowlarr search retest/fix ────────────────────────┐
│   ├── T3.1 [40195403] Deploy Sonarr                           │
│   ├── T3.2 [2c5036fc] Deploy Radarr                           │
│   ├── T3.3 [0e432174] Deploy Lidarr/Readarr/Bazarr/Mylar3    │
│   ├── d5d7e885 Add torrent indexers to Prowlarr               │
│   ├── 2fca00f8 Mylar3 NZB indexer                             │
│   ├── 3550426b Prowlarr app sync to Lidarr+Readarr            │
│   ├── 7c09fe94 Lidarr root folder                             │
│   ├── 64b22a1f Readarr root folder                            │
│   └── de9510c8 Bazarr verify sync                             │
│                                                                │
═══════════════════════════════════════════════════════════════════
TIER 4 — LIBRARIAN + MONITORING (depends: T0.9)
═══════════════════════════════════════════════════════════════════
│
├── T4.1 [5f96950f] Deploy librarian services (Kavita, Komga,   │
│   Audiobookshelf, ConvertX, Whisper)                          │
├── T4.2 [b192eba3] Deploy monitoring (Grafana, Prometheus,     │
│   Uptime Kuma, Portall)                                       │
└── T4.3 [f52aa05c] Deploy Homepage dashboard (depends: T4.2)   │
         │
═══════════════════════════════════════════════════════════════════
TIER 5 — CORE APPS (depends: PostgreSQL + Redis)
═══════════════════════════════════════════════════════════════════
│
├── T5.1 [efccd48a] Deploy Nextcloud                            │
│   └── P16.4 [22c73013] Configure Nextcloud admin (USER_ACTION)
├── T5.2 [01f9770d] Deploy SiYuan + Langflow + ChromaDB         │
│                                                                │
═══════════════════════════════════════════════════════════════════
TIER 6 — CLEANUP (no strict deps, run after main work)
═══════════════════════════════════════════════════════════════════
│
├── T6.1 [044d82e5] Fix broken ~/media/ symlinks                │
├── T6.2 [458d5c39] Clean duplicate volumes (reclaim 172GB)     │
├── T6.3 [54356b8e] Move 125GB SABnzbd volume off root NVMe    │
├── T6.4 [146420d5] Fix sdc2 double-mount                       │
├── T6.5 [41d07875] Git commit all stabilization changes        │
├── e94c22a8 Clean stale cron jobs (depends: f35bf91c)          │
├── 73148b16 Baseline git repos (after stabilization)           │
│                                                                │
═══════════════════════════════════════════════════════════════════
TIER 7 — POST-STABILIZATION FEATURES
═══════════════════════════════════════════════════════════════════
│
├── T7.1 [65198fea] Paperless-ngx (depends: PG + Redis)
├── T7.2 [a7405a34] Multi-agent Discord team
├── T7.3 [8bc9470a] Calendar bidirectional sync
├── T7.4 [341da7b2] PKM architecture (depends: SiYuan)
├── T7.5 [5dbe60ec] BentoPDF
├── T7.6 [3ea8737a] Miniflux RSS (depends: PostgreSQL)
├── T7.7 [6fc1d092] Pangolin eval
├── T7.8 [aeb8836e] Restic/Borgmatic backups
├── T7.9 [2e0788ce] OpenClaw security tightening
│                                                                │
═══════════════════════════════════════════════════════════════════
PARALLEL TRACKS (independent, run anytime)
═══════════════════════════════════════════════════════════════════
│
├── BRIDGE TESTS (USER_ACTION — D must send messages)
│   ├── P10.6 [50f22dd9] Telegram send test
│   ├── P10.7 [abc7220e] Telegram receive test
│   ├── P10.8 [361efaf5] Discord mention test
│   └── P10.9 [a1eaea82] Approval flow test
│
├── USER DECISIONS
│   ├── P17.5 [fa1a7b31] Calendar sync policy (USER_INPUT)
│   └── P14.5 [b2ea175b] PKM restore (blocked on OneDrive audit)
│
├── INFERENCE (manual launch window)
│   ├── P8.9 [c068808e] Verify LM Studio API
│   └── P8.11 [361bd3e3] Test CUDA→Vulkan fallback
│
├── GAMING (low priority)
│   ├── P20.4 [602db610] Verify FFXIV on NVIDIA
│   └── P20.5 [35d9b694] Test GPU conflict rule
│
├── MEDIA PIPELINE BACKLOG (wait for download-stack stabilization)
│   ├── 2916dbc4 Manga library bulk download
│   ├── f4052196 Komga rescan + dedup
│   ├── 596f59ac COMICS-024 VPN local access
│   ├── e3777ec3 COMICS-028 FlareSolverr access
│   ├── 58a28e05 COMICS-015 Final comics verification
│   ├── cd799283 Post-process downloads for Kavita
│   ├── f9da6576 Verify Kavita library
│   ├── 2e9c45da Document manga setup
│   ├── 3fba28e2 Manga torrent downloads
│   └── 8bcebe2e Consider FlareSolverr container
│
├── ACP ROADMAP (P19 done, annotations need fixing)
│   ├── 798b75c2 Design external-agent ingress
│   ├── e82cf34f Define cross-runtime envelope schema
│   ├── a65adb44 Implement external-agent relay
│   ├── 6d075a81 Test external-agent handoff
│   ├── 193228cf VS Code Insiders integration
│   ├── e1b155e7 Claude Code ACP adapter
│   ├── 2d27cc01 OpenCode ACP adapter
│   └── f69cbf10 OpenClaw external-agent registration
│
├── DEVX CLEANUP (P19 done, unblocked)
│   ├── 9333bd4c Audit Claude + OpenCode integrations
│   ├── 063fb19f Review plugin set
│   ├── 0ca93f69 Prune stale agent definitions
│   └── ecb0d650 Inventory MCP servers/tools
│
├── DASHBOARD PLAN (P23.1-8 chain)
│   ├── P23.1 [834f2eb7] Podman API bridge
│   ├── P23.2 [06fe98f9] Homepage quadlet (depends: P23.1)
│   ├── P23.3 [cfef7b11] Service generator (depends: P23.2)
│   ├── P23.4 [7b821f02] Build homepage config (depends: P23.3)
│   ├── P23.5 [fc9ca136] Secrets strategy (depends: P23.4)
│   ├── P23.6 [56dcf547] Caddy proxy wiring (depends: P23.2)
│   ├── P23.7 [acb3c046] Deploy + verify (depends: P23.5 + P23.6)
│   └── P23.8 [1494649f] Commit + document (depends: P23.7)
│
├── CONFIGURE (unblocked)
│   ├── 698baa34 opencode.json prompt tuning
│   ├── ae32e5fc Sync lemonade-server stack
│   └── a50716ac Update opencode.json plugins
│
├── STORAGE HEALTH + SECURITY
│   ├── 1c786063 SMART: nvme0n1 (Windows)
│   ├── 057251c8 SMART: nvme1n1 (Linux)
│   ├── fe3003f3 SMART: sda (plex)
│   ├── 4ca99894 SMART: sdb (TV_Anime)
│   ├── d9bff796 SMART: sdc (Other_Media)
│   ├── 7561267c Encrypt Windows drive
│   └── 4739ffa0 Verify LUKS on Linux drive
│
├── MAINTENANCE
│   ├── 51785f5a Cron job to purge old logs
│   └── 0b2c4082 Spend $300 Google Cloud credits
```

---

# DETAILED TASK BREAKDOWN — EVERY STEP, EVERY COMMAND

## ═══════════════════════════════════════════
## TIER 0 — UNBLOCK (9 tasks, ~1-2 hours)
## ═══════════════════════════════════════════

These have zero dependencies. TaskFlow starts here. Multiple can run in parallel via sub-agents.

---

### T0.1 Resolve git merge conflicts in 5 core quadlets
**UUID:** `a8f55536-738a-4789-9488-88c51db8f401`
**Priority:** H | **Project:** osmen.maint | **Tags:** fix_needed, quadlet, tier0
**Depends on:** nothing
**Agent:** coder (gpt-5.4)

#### What's broken
5 quadlet files contain `<<<<<<< HEAD` markers from an incomplete merge. Systemd's quadlet generator will refuse to process them. **Nothing systemd-managed will start until these are fixed.**

#### Affected files
1. `quadlets/core/osmen-core-chromadb.container`
2. `quadlets/core/osmen-core.network`
3. `quadlets/core/osmen-core-postgres.container`
4. `quadlets/core/osmen-core-redis.container`
5. `quadlets/core/user-osmen-core.slice`

#### Exact steps
```bash
# For each file, resolve by keeping HEAD version
cd ~/dev/OsMEN-OC
for file in \
  quadlets/core/osmen-core-chromadb.container \
  quadlets/core/osmen-core.network \
  quadlets/core/osmen-core-postgres.container \
  quadlets/core/osmen-core-redis.container \
  quadlets/core/user-osmen-core.slice; do
  # Extract HEAD side (between <<<<<<< HEAD and =======)
  sed -i '/^<<<<<<< HEAD$/,/^=======$/{/^<<<<<<< HEAD$/d; /^=======$/d}; /^=======$/,/^>>>>>>>>/{d}' "$file"
done
```

Alternative (cleaner): use `git checkout --ours` for each file:
```bash
git checkout --ours quadlets/core/osmen-core-chromadb.container
git checkout --ours quadlets/core/osmen-core.network
git checkout --ours quadlets/core/osmen-core-postgres.container
git checkout --ours quadlets/core/osmen-core-redis.container
git checkout --ours quadlets/core/user-osmen-core.slice
git add quadlets/core/
```

#### Verification
```bash
# Must return zero results
grep -r '<<<<<<< HEAD\|>>>>>>>\|=======' quadlets/core/ | wc -l
# Each file should be valid systemd unit
systemd-analyze verify quadlets/core/*.container 2>&1 || echo "Some warnings expected (missing slices)"
```

#### Failure modes
- **Conflict markers in non-obvious places:** Some files may have nested conflicts. Check each file manually after automated resolution.
- **HEAD version has wrong variable escaping:** HEAD versions should have `$${VAR}` (double-dollar) for quadlet escaping. If they have `${VAR}`, the variable will be expanded at generate time instead of runtime.
- **Files are binary or corrupted:** `file quadlets/core/*` should all be "ASCII text".

#### TW closure
```bash
task a8f55536 done
task a8f55536 annotate "Resolved 5 merge conflicts via git checkout --ours. HEAD versions kept. Verified no conflict markers remain."
```

#### TaskFlow state transition
- Before: `step = "tier0_prerequisites"`, `stateJson.currentTwUuid = "a8f55536"`
- After: `stateJson.completedTasks.push("a8f55536")`, TW marks done, T0.9 may unblock

---

### T0.2 Create 4 missing systemd slice definitions
**UUID:** `d217b0fc-49c9-4e16-9fcd-fd7b923eb9f3`
**Priority:** H | **Project:** osmen.maint | **Tags:** fix_needed, quadlet, tier0
**Depends on:** nothing
**Agent:** coder (gpt-5.4)

#### What's broken
20+ container quadlets reference `Slice=` directives pointing to 4 slice files that **do not exist**:
- `user-osmen-services.slice`
- `user-osmen-media.slice`
- `user-osmen-background.slice`
- `user-osmen-inference.slice`

Without these slices, systemd cannot place containers in cgroups. Containers will fail to start even after merge conflicts are fixed.

#### Exact steps
```bash
cd ~/dev/OsMEN-OC/quadlets

# Create each slice as a systemd user slice
cat > core/user-osmen-services.slice << 'EOF'
[Unit]
Description=OsMEN Service Slice
Before=slices.target

[Slice]
MemoryAccounting=yes
CPUAccounting=yes
EOF

cat > media/user-osmen-media.slice << 'EOF'
[Unit]
Description=OsMEN Media Processing Slice
Before=slices.target

[Slice]
MemoryAccounting=yes
CPUAccounting=yes
EOF

cat > core/user-osmen-background.slice << 'EOF'
[Unit]
Description=OsMEN Background Tasks Slice
Before=slices.target

[Slice]
MemoryAccounting=yes
CPUAccounting=yes
EOF

cat > inference/user-osmen-inference.slice << 'EOF'
[Unit]
Description=OsMEN Inference/AI Slice
Before=slices.target

[Slice]
MemoryAccounting=yes
CPUAccounting=yes
EOF
```

**Note:** Placement depends on where the referencing containers live. Verify:
```bash
# Find which quadlets reference each slice
grep -r 'Slice=' quadlets/ | grep -v '.bak'
```
Place slices in the same directory as the containers that reference them, or in a shared location with symlinks.

#### Verification
```bash
# All 4 slices exist
ls -la quadlets/core/user-osmen-services.slice quadlets/media/user-osmen-media.slice
# Slices are valid systemd units
systemd-analyze verify quadlets/core/user-osmen-services.slice 2>&1
# No quadlet references a missing slice
for slice in $(grep -rh 'Slice=' quadlets/ | sed 's/.*=//' | sort -u); do
  find quadlets/ -name "$slice" -type f || echo "MISSING: $slice"
done
```

#### Failure modes
- **Slice name mismatch:** Quadlets may reference slightly different names. The `grep` check above catches this.
- **Wrong directory:** Slices must be in a directory that systemd's quadlet generator scans (`~/.config/containers/systemd/` or symlinks from there).
- **Slice syntax errors:** systemd-analyze will catch these.

#### TW closure
```bash
task d217b0fc done
task d217b0fc annotate "Created 4 slice definitions. Verified all Slice= references resolve."
```

---

### T0.3 Enable UFW with basic rules
**UUID:** `5054f274-8370-41d6-a9cb-32f05108d46c`
**Priority:** H | **Project:** osmen.maint | **Tags:** fix_needed, security, tier0
**Depends on:** nothing
**Agent:** coder (gpt-5.4) — **REQUIRES ELEVATED / sudo**

#### What's broken
iptables is wide open. UFW is inactive. SSH (22) and Plex (32400) are bound to 0.0.0.0. Any network the machine joins = full exposure.

#### Exact steps
```bash
# Check current state
sudo ufw status verbose
sudo iptables -L -n | head -20

# Set defaults
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (critical — don't lock yourself out)
sudo ufw allow 22/tcp comment 'SSH'

# Allow Plex
sudo ufw allow 32400/tcp comment 'Plex Media Server'

# Allow localhost
sudo ufw allow from 127.0.0.0/8

# Allow local subnet (for container networking, samba, etc.)
sudo ufw allow from 10.89.0.0/24 comment 'OsMEN container network'
sudo ufw allow from 192.168.0.0/16 comment 'Local network'

# Enable
sudo ufw enable

# Verify
sudo ufw status numbered
```

#### Verification
```bash
# UFW active
sudo ufw status | head -1  # Should say "Status: active"
# SSH still works (test from another terminal before closing this one!)
# Plex accessible from local network
curl -s http://localhost:32400/identity | head -5
# External ports blocked (test from phone on same WiFi, different subnet)
```

#### Failure modes
- **Lockout risk:** ALWAYS test SSH from a second terminal before closing the session. If locked out, need physical access or cloud console.
- **Plex remote access breaks:** Plex uses 32400 for discovery + streaming. If D wants remote Plex access, also need 32400/udp and possibly Plex relay port.
- **Container networking breaks:** Podman uses NAT. UFW may interfere. If containers can't reach internet after UFW enable, add: `sudo ufw allow in on cni-podman0` or use iptables rules for the podman bridge.

#### TW closure
```bash
task 5054f274 done
task 5054f274 annotate "UFW enabled. Rules: allow 22/tcp (SSH), 32400/tcp (Plex), 10.89.0.0/24 (containers), 192.168.0.0/16 (LAN). Default deny incoming."
```

---

### T0.4 Fix ReadOnly=true on 20+ container quadlets
**UUID:** `a79d71f9-908e-4249-baff-982b1fee68e1`
**Priority:** H | **Project:** osmen.maint | **Tags:** fix_needed, quadlet, tier0
**Depends on:** nothing
**Agent:** coder (gpt-5.4)

#### What's broken
20+ quadlets have `ReadOnly=true` but most linuxserver.io images need writable `/tmp`. Some have a comment saying ReadOnly was removed but the directive remains. Chromadb quadlet even has contradictory comment + directive.

#### Affected containers
chromadb, postgres, redis, caddy, gateway, bazarr, lidarr, mylar3, radarr, readarr, sonarr, sabnzbd, prowlarr, qbittorrent, tautulli, grafana, uptimekuma, portall, prometheus, kometa

#### Exact steps
```bash
cd ~/dev/OsMEN-OC/quadlets

# Strategy: For linuxserver.io images → add Tmpfs=/tmp alongside ReadOnly
# For images where ReadOnly was "intentionally removed" per comments → remove the directive
# For database/cache services (postgres, redis, chromadb) → remove ReadOnly (they need /tmp, /run, /var)

# Step 1: Find all quadlets with ReadOnly
grep -rl 'ReadOnly=true' quadlets/ | sort

# Step 2: For each, check if it's linuxserver.io
for file in $(grep -rl 'ReadOnly=true' quadlets/); do
  image=$(grep '^Image=' "$file" | head -1)
  if echo "$image" | grep -qi 'linuxserver\|lscr.io'; then
    # Add Tmpfs=/tmp after ReadOnly line if not already present
    if ! grep -q 'Tmpfs=/tmp' "$file"; then
      sed -i '/^ReadOnly=true/a Tmpfs=/tmp' "$file"
    fi
  else
    # Remove ReadOnly entirely (database/cache/gateway services)
    sed -i '/^ReadOnly=true/d' "$file"
  fi
done

# Step 3: Verify
for file in $(grep -rl 'ReadOnly=true' quadlets/ 2>/dev/null); do
  echo "Still has ReadOnly: $file"
  echo "  Image: $(grep '^Image=' "$file")"
  echo "  Has Tmpfs: $(grep 'Tmpfs' "$file")"
done
```

#### Verification
```bash
# No quadlet has ReadOnly without Tmpfs for linuxserver images
for f in $(grep -rl 'ReadOnly=true' quadlets/); do
  image=$(grep '^Image=' "$f" | head -1)
  if echo "$image" | grep -qi 'linuxserver\|lscr.io'; then
    grep -q 'Tmpfs=/tmp' "$f" && echo "OK: $f" || echo "FAIL: $f (ReadOnly but no Tmpfs)"
  fi
done
```

#### Failure modes
- **ReadOnly was there for security hardening:** Some containers (prometheus, grafana) genuinely don't need /tmp writes. Keep ReadOnly + add Tmpfs=/tmp as a safety net.
- **Container fails on startup with "read-only filesystem":** Check logs with `journalctl --user -u <service>` and add specific Tmpfs mounts as needed.

#### TW closure
```bash
task a79d71f9 done
task a79d71f9 annotate "Fixed ReadOnly on 20+ quadlets. Linuxserver.io: added Tmpfs=/tmp. Database/cache/gateway: removed ReadOnly. Verified no linuxserver image has ReadOnly without Tmpfs."
```

---

### T0.5 Pin 3 floating container images
**UUID:** `23ee5db3-08f6-4574-8318-3c5e64381529`
**Priority:** H | **Project:** osmen.media.pipeline | **Tags:** fix_needed, quadlet, tier0
**Depends on:** nothing
**Agent:** coder (gpt-5.4)

#### What's broken
3 containers are running on floating tags that can change without warning:
1. SABnzbd: `:latest` → unpredictable, wizard regression may be image version issue
2. Komga: `:latest` + `AutoUpdate=registry` → container updates itself on restart!
3. Readarr: `:nightly` → bleeding edge, not suitable for production

#### Exact steps
```bash
cd ~/dev/OsMEN-OC/quadlets

# 1. SABnzbd: pin to current stable
# Check what version is currently pulled
podman inspect osmen-media-sabnzbd --format '{{.Image}}' 2>/dev/null || echo "Container not running"
# Edit quadlet
sed -i 's|Image=.*sabnzbd.*:latest|Image=lscr.io/linuxserver/sabnzbd:4.5.1|' media/osmen-media-sabnzbd.container

# 2. Komga: pin to stable, remove AutoUpdate
sed -i 's|Image=.*komga.*:latest|Image=ghcr.io/gotson/komga:1.x|' media/osmen-media-komga-comics.container
# Remove AutoUpdate line entirely
sed -i '/^AutoUpdate=/d' media/osmen-media-komga-comics.container

# 3. Readarr: pin to stable (not nightly)
sed -i 's|Image=.*readarr.*:nightly|Image=ghcr.io/hotio/readarr:stable|' media/osmen-media-readarr.container

# Verify
grep -E '^Image=' media/osmen-media-sabnzbd.container
grep -E '^Image=' media/osmen-media-komga-comics.container
grep -E '^Image=' media/osmen-media-readarr.container
# Should show pinned versions, no :latest or :nightly
```

#### Verification
```bash
# No quadlet references :latest or :nightly
grep -r ':latest\|:nightly' quadlets/ | grep '^Image=' || echo "All pinned"
# No AutoUpdate directives remain
grep -r 'AutoUpdate=' quadlets/ && echo "WARNING: AutoUpdate still present" || echo "OK: No AutoUpdate"
```

#### Failure modes
- **Pinned version doesn't exist on registry:** Check available tags on Docker Hub / GHCR first. `skopeo list-tags docker://lscr.io/linuxserver/sabnzbd` or use the registry web UI.
- **Image ID changes break existing config volumes:** SABnzbd config should be compatible across minor versions. Readarr stable → nightly config is usually backward-compatible.

#### TW closure
```bash
task 23ee5db3 done
task 23ee5db3 annotate "Pinned SABnzbd to :4.5.1, Komga to stable (removed AutoUpdate), Readarr to :stable. Verified no :latest/:nightly/AutoUpdate remain."
```

---

### T0.6 Add PUID=1000 PGID=1000 to linuxserver.io containers
**UUID:** `5d93c34c-22c4-4a82-a391-b4e36f6ddc13`
**Priority:** M | **Project:** osmen.maint | **Tags:** fix_needed, quadlet, tier0
**Depends on:** nothing
**Agent:** coder (gpt-5.4)

#### What's broken
6+ linuxserver.io containers run as root inside the container because PUID/PGID isn't set:
- Sonarr, Radarr, Lidarr, SABnzbd, Bazarr, Mylar3, Readarr, qBittorrent

This means files they create on mounted volumes are owned by root, not by D (uid 1000).

#### Exact steps
```bash
cd ~/dev/OsMEN-OC/quadlets

# For each linuxserver quadlet missing PUID/PGID
for file in media/osmen-media-{sonarr,radarr,lidarr,sabnzbd,bazarr,mylar3,readarr,qbittorrent}.container; do
  if [ -f "$file" ]; then
    # Add PUID/PGID under [Container] section if not present
    if ! grep -q 'Environment=PUID=' "$file"; then
      sed -i '/\[Container\]/a Environment=PUID=1000\nEnvironment=PGID=1000' "$file"
    fi
  fi
done
```

#### Verification
```bash
# Every linuxserver quadlet has PUID/PGID
for f in $(grep -rl 'lscr.io\|linuxserver' quadlets/); do
  echo "=== $f ==="
  grep 'Environment=PUID\|Environment=PGID' "$f" || echo "  MISSING PUID/PGID"
done
```

#### TW closure
```bash
task 5d93c34c done
task 5d93c34c annotate "Added PUID=1000 PGID=1000 to all linuxserver.io containers. Verified all have user mapping."
```

---

### T0.7 Remove duplicate HealthCmd directives
**UUID:** `a785e86f-c881-4e78-8f6b-c9357c0f1e77`
**Priority:** L | **Project:** osmen.maint | **Tags:** fix_needed, quadlet, tier0
**Depends on:** nothing
**Agent:** coder (gpt-5.4)

#### What's broken
chromadb, postgres, and redis quadlets have duplicate `HealthCmd` lines. Systemd will use the last one, but it's confusing and may cause unexpected behavior.

#### Exact steps
```bash
# For each affected file, keep only the correct health check
# chromadb: curl http://localhost:8000/api/v1/heartbeat
# postgres: pg_isready -U postgres -d postgres
# redis: redis-cli ping

# Remove duplicates — keep last occurrence (systemd behavior)
for file in \
  core/osmen-core-chromadb.container \
  core/osmen-core-postgres.container \
  core/osmen-core-redis.container; do
  
  # Count HealthCmd lines
  count=$(grep -c '^HealthCmd=' "$file" 2>/dev/null || echo 0)
  if [ "$count" -gt 1 ]; then
    # Keep only the last HealthCmd line
    awk '!seen[$0]++ || !/^HealthCmd=/' "$file" > "$file.tmp"
    # Actually: reverse, dedupe HealthCmd, reverse back
    tac "$file" | awk '!h && /^HealthCmd=/ { print; h=1; next } !/^HealthCmd=/' | tac > "$file.tmp"
    mv "$file.tmp" "$file"
    echo "Deduplicated HealthCmd in $file"
  fi
done
```

#### Verification
```bash
# No file has duplicate HealthCmd
for f in quadlets/core/osmen-core-{chromadb,postgres,redis}.container; do
  count=$(grep -c '^HealthCmd=' "$f" 2>/dev/null || echo 0)
  echo "$f: $count HealthCmd lines"
done
```

#### TW closure
```bash
task a785e86f done
task a785e86f annotate "Removed duplicate HealthCmd from chromadb, postgres, redis quadlets."
```

---

### T0.8 Recover daily notes from git history
**UUID:** `2e7e22f7-58d8-40e0-9314-59a42d3a8c9c`
**Priority:** M | **Project:** osmen.maint | **Tags:** fix_needed, tier0
**Depends on:** nothing
**Agent:** basic (glm-4.7-flash) — simple file recovery

#### What's broken
`openclaw/memory/2026-04-16.md` was overwritten with duplicate manga session data. Original contained: memory maintenance notes, 859 test results, cron fix details, P13-P22 completions.

#### Exact steps
```bash
cd ~/dev/OsMEN-OC

# Find the last commit that had the correct content
git log --oneline -- openclaw/memory/2026-04-16.md | head -5

# Extract original content
git show HEAD~3:openclaw/memory/2026-04-16.md > /tmp/2026-04-16-original.md

# Compare with current
diff /tmp/2026-04-16-original.md openclaw/memory/2026-04-16.md

# If the original has unique content worth recovering, merge them
# Keep both: original content + any new valid additions
cat /tmp/2026-04-16-original.md > openclaw/memory/2026-04-16.md
# Then append any unique new content that was added after overwrite
```

#### Verification
```bash
# File should contain non-manga content (859, cron, P13-P22)
grep -c '859\|cron\|P1[3-9]\|P2[0-2]' openclaw/memory/2026-04-16.md
```

#### TW closure
```bash
task 2e7e22f7 done
task 2e7e22f7 annotate "Recovered 2026-04-16.md from git history. Original memory maintenance + 859 + P13-P22 content restored."
```

---

### T0.9 daemon-reload + verify all units generate
**UUID:** `aa97a670-f172-4435-a780-02fe5e997d2b`
**Priority:** H | **Project:** osmen.maint | **Tags:** fix_needed, tier0
**Depends on:** T0.1 (merge conflicts), T0.2 (slices), T0.4 (ReadOnly)
**Agent:** coder (gpt-5.4)
**⚠️ GATE TASK — This unblocks Tier 1, Tier 2, Tier 3, Tier 4, Tier 5**

#### What this does
After all quadlet files are fixed, tell systemd to regenerate service units from all `.container`, `.volume`, `.network`, `.pod`, and `.slice` files. Then verify every expected unit exists.

#### Exact steps
```bash
# Reload systemd generator
systemctl --user daemon-reload

# Verify quadlet-generated units exist
systemctl --user list-unit-files | grep -E 'osmen-(core|media)' | sort

# Specifically check postgres and redis (currently "not-found")
systemctl --user list-unit-files | grep -E 'osmen-core-(postgres|redis)'
# Should show "enabled" or "static", NOT "not-found"

# Count: should match number of quadlet files
quadlet_count=$(find ~/dev/OsMEN-OC/quadlets -name '*.container' -o -name '*.volume' -o -name '*.network' -o -name '*.pod' | wc -l)
unit_count=$(systemctl --user list-unit-files | grep -c 'osmen-')
echo "Quadlet files: $quadlet_count, Generated units: $unit_count"

# Check for any failed generations
journalctl --user -u 'systemd-generator*' --since "5 minutes ago" --no-pager | grep -i 'error\|fail\|invalid'
```

#### Verification
```bash
# All critical units exist
for svc in osmen-core-postgres osmen-core-redis osmen-core-caddy download-stack-pod osmen-media-gluetun osmen-media-sabnzbd osmen-media-qbittorrent osmen-media-prowlarr; do
  systemctl --user list-unit-files "$svc.service" | grep -q "$svc" && echo "✅ $svc" || echo "❌ $svc MISSING"
done
```

#### Failure modes
- **"not-found" persists for some units:** The quadlet generator skips files with syntax errors. Re-check each failing file with `systemd-analyze verify`.
- **Symlinks broken:** Quadlet files are symlinked from `~/.config/containers/systemd/`. Verify: `ls -la ~/.config/containers/systemd/`
- **Generator version too old:** Quadlet features vary by podman version. `podman --version` should be ≥ 4.7.

#### TW closure
```bash
task aa97a670 done
task aa97a670 annotate "daemon-reload complete. All quadlet units generated. Postgres + Redis units now load. X quadlet files → Y generated units."
```

#### TaskFlow: THIS IS THE GATE
When T0.9 completes, TaskFlow queries TW for newly unblocked tasks:
- T1.1 PostgreSQL (was waiting on aa97a670)
- T1.2 Redis (was waiting on aa97a670)
- T1.3 Caddy (was waiting on aa97a670)
- e9d3e070 Download-stack reconciliation (was waiting on aa97a670 + 23ee5db3)
- T4.1 Librarian services (was waiting on aa97a670)
- T4.2 Monitoring stack (was waiting on aa97a670)
- T5.2 SiYuan + Langflow + ChromaDB (was waiting on a19101e3, which was waiting on aa97a670)

**→ TaskFlow should spawn multiple sub-agents in parallel for these.**

---

## ═══════════════════════════════════════════
## TIER 1 — CORE SERVICES (3 tasks, ~2-3 hours)
## ═══════════════════════════════════════════

All three depend only on T0.9. They can run **in parallel**.

---

### T1.1 Deploy PostgreSQL via quadlet
**UUID:** `a19101e3-70d0-41a9-8e03-41bbf9dd7634`
**Priority:** H | **Project:** osmen.install.p11 | **Tags:** deploy, tier1
**Depends on:** T0.9 [aa97a670]
**Agent:** coder (gpt-5.4)
**Blocks:** Nextcloud (T5.1), SiYuan/Langflow/ChromaDB (T5.2), Paperless-ngx (T7.1), Miniflux (T7.6)

#### Exact steps
```bash
# Start the service
systemctl --user start osmen-core-postgres.service

# Check status
systemctl --user status osmen-core-postgres.service

# Verify healthy (uses HealthCmd from quadlet)
systemctl --user show osmen-core-postgres.service -p ActiveState -p SubState

# Test connectivity
podman exec osmen-core-postgres pg_isready -U postgres -d postgres
# Should return: "/var/run/postgresql:5432 - accepting connections"

# Test from container network (other containers will connect this way)
podman exec osmen-core-postgres psql -U postgres -c "SELECT version();"

# Verify data volume
podman exec osmen-core-postgres ls -la /var/lib/postgresql/data/

# Check logs for any warnings
journalctl --user -u osmen-core-postgres.service --since "5 minutes ago" --no-pager
```

#### Post-deploy configuration
```bash
# Create application databases that downstream services will need
podman exec osmen-core-postgres psql -U postgres -c "CREATE DATABASE nextcloud;"
podman exec osmen-core-postgres psql -U postgres -c "CREATE DATABASE langflow;"
podman exec osmen-core-postgres psql -U postgres -c "CREATE DATABASE paperless;"

# Verify
podman exec osmen-core-postgres psql -U postgres -c "\l"
```

#### Verification checklist
- [ ] Service active (running)
- [ ] pg_isready returns accepting connections
- [ ] Can query SELECT version()
- [ ] Data volume populated
- [ ] nextcloud, langflow, paperless databases created
- [ ] No errors in journalctl

#### Failure modes
- **"data directory exists but is not empty":** Volume has leftover data. Either use it (if compatible) or wipe: `podman volume rm systemd-osmen-core-postgres-data`
- **Permission denied on volume:** PUID/PGID issue. Postgres runs as uid 999 inside container. Ensure volume is writable.
- **Port conflict:** If something else uses 5432, check quadlet's PublishPort and adjust.

#### TW closure
```bash
task a19101e3 done
task a19101e3 annotate "PostgreSQL deployed and healthy. Created DBs: nextcloud, langflow, paperless. pg_isready OK."
```

#### TaskFlow: This unblocks
- T5.1 Nextcloud (also needs T1.2 Redis)
- T5.2 SiYuan + Langflow + ChromaDB (needs T1.1 only)
- T7.1 Paperless-ngx (needs T1.1 + T1.2)
- T7.6 Miniflux (needs T1.1 only)

---

### T1.2 Deploy Redis via quadlet
**UUID:** `2c73a3e6-f8f4-490f-a74d-e33201bfdd0f`
**Priority:** H | **Project:** osmen.install.p11 | **Tags:** deploy, tier1
**Depends on:** T0.9 [aa97a670]
**Agent:** coder (gpt-5.4)
**Blocks:** Nextcloud (T5.1), Paperless-ngx (T7.1)

#### Exact steps
```bash
systemctl --user start osmen-core-redis.service
systemctl --user status osmen-core-redis.service

# Test connectivity
podman exec osmen-core-redis redis-cli ping
# Should return: PONG

# Test basic operations
podman exec osmen-core-redis redis-cli SET test_key "osmen_deployed"
podman exec osmen-core-redis redis-cli GET test_key
podman exec osmen-core-redis redis-cli DEL test_key

# Check persistence config
podman exec osmen-core-redis redis-cli CONFIG GET save
podman exec osmen-core-redis redis-cli INFO server | head -20

# Verify data volume
podman exec osmen-core-redis ls -la /data/

# Check logs
journalctl --user -u osmen-core-redis.service --since "5 minutes ago" --no-pager
```

#### Verification checklist
- [ ] Service active (running)
- [ ] redis-cli ping → PONG
- [ ] Can SET/GET/DEL keys
- [ ] Data volume populated
- [ ] No errors in journalctl

#### TW closure
```bash
task 2c73a3e6 done
task 2c73a3e6 annotate "Redis deployed and healthy. redis-cli ping OK. Basic SET/GET verified."
```

---

### T1.3 Deploy Caddy reverse proxy via quadlet
**UUID:** `c08949ac-7579-4b4a-a3b3-c63f2d3f5c7a`
**Priority:** M | **Project:** osmen.install.p11 | **Tags:** deploy, tier1
**Depends on:** T0.9 [aa97a670]
**Agent:** coder (gpt-5.4)

#### Exact steps
```bash
systemctl --user start osmen-core-caddy.service
systemctl --user status osmen-core-caddy.service

# Verify Caddy is listening
curl -sk https://localhost/ | head -20
# Or check the specific port from the quadlet
ss -tlnp | grep caddy

# Check Caddy config loaded
podman exec osmen-core-caddy caddy validate --config /etc/caddy/Caddyfile

# Check logs for TLS/cert issues
journalctl --user -u osmen-core-caddy.service --since "5 minutes ago" --no-pager
```

#### Verification checklist
- [ ] Service active (running)
- [ ] Caddy listening on expected port
- [ ] Caddyfile valid
- [ ] No TLS errors (self-signed is OK for .local)

#### TW closure
```bash
task c08949ac done
task c08949ac annotate "Caddy reverse proxy deployed. Caddyfile valid. Listening on configured port."
```

---

## ═══════════════════════════════════════════
## TIER 2 — DOWNLOAD STACK (3 tasks, ~2-3 hours)
## ═══════════════════════════════════════════

---

### e9d3e070 Reconcile download-stack to systemd
**UUID:** `e9d3e070-b177-409f-9cff-6762ab8ba326`
**Priority:** H | **Project:** osmen.install.p11 | **Tags:** fix_needed, install, phase11
**Depends on:** T0.5 [23ee5db3] + T0.9 [aa97a670]
**Agent:** coder (gpt-5.4)
**Blocks:** SAB wizard fix, qBittorrent auth, FlareSolverr routing

#### What's broken
The download stack (Gluetun VPN + SABnzbd + qBittorrent + Prowlarr) was created via `podman run`, not systemd/quadlet. These containers will NOT survive a reboot. Quadlet files exist but have never been used because of merge conflicts (now fixed).

#### Exact steps
```bash
# Step 1: Stop manually-created containers
podman pod stop download-stack 2>/dev/null
podman pod rm download-stack 2>/dev/null
# Clean up any orphan containers
podman rm -f osmen-media-gluetun osmen-media-sabnzbd osmen-media-qbittorrent osmen-media-prowlarr 2>/dev/null

# Step 2: Verify quadlet units exist (should be yes after T0.9)
systemctl --user list-unit-files | grep download-stack

# Step 3: Start the pod via systemd
systemctl --user start download-stack-pod.service

# Step 4: Start each container service
systemctl --user start osmen-media-gluetun.service
systemctl --user start osmen-media-sabnzbd.service
systemctl --user start osmen-media-qbittorrent.service
systemctl --user start osmen-media-prowlarr.service

# Step 5: Verify all 4 running
podman ps --pod | grep download-stack

# Step 6: Verify ports responding
curl -sf http://127.0.0.1:8082/ -o /dev/null && echo "SABnzbd ✅" || echo "SABnzbd ❌"
curl -sf http://127.0.0.1:9090/ -o /dev/null && echo "qBittorrent ✅" || echo "qBittorrent ❌"
curl -sf http://127.0.0.1:9696/ -o /dev/null && echo "Prowlarr ✅" || echo "Prowlarr ❌"
curl -sf http://127.0.0.1:8888/ -o /dev/null && echo "Gluetun proxy ✅" || echo "Gluetun proxy ❌"

# Step 7: Verify VPN egress
podman exec osmen-media-gluetun wget -qO- ifconfig.me
# Should return VPN IP, NOT home IP

# Step 8: Enable services for auto-start on boot
systemctl --user enable download-stack-pod.service
systemctl --user enable osmen-media-gluetun.service
systemctl --user enable osmen-media-sabnzbd.service
systemctl --user enable osmen-media-qbittorrent.service
systemctl --user enable osmen-media-prowlarr.service
```

#### Verification checklist
- [ ] All 4 containers running in download-stack pod
- [ ] All 4 ports responding (8082, 9090, 9696, 8888)
- [ ] VPN egress shows VPN IP
- [ ] All services enabled (survive reboot)
- [ ] `systemctl --user status download-stack-pod` shows active

#### Failure modes
- **Pod creation fails:** Pod may already exist with different config. `podman pod rm -f download-stack` and retry.
- **Container fails to start:** Check `journalctl --user -u osmen-media-<service>` for specific error. Common: volume mount failure, port conflict, image pull failure.
- **VPN doesn't connect:** Gluetun needs correct VPN credentials. Check env vars in quadlet. `podman logs osmen-media-gluetun` for VPN errors.
- **SABnzbd shows wizard:** Expected — T2.2 fixes this next.

#### TW closure
```bash
task e9d3e070 done
task e9d3e070 annotate "Download stack reconciled to systemd. All 4 containers running. VPN egress verified. Services enabled for boot."
```

#### TaskFlow: This unblocks
- T2.2 SABnzbd wizard fix [ec589dc6]
- qBittorrent auth recovery [39477865]
- T3.4 FlareSolverr routing [b30e0a61]

---

### T2.2 Fix SABnzbd wizard regression
**UUID:** `ec589dc6-481a-425c-b10a-402c0e933936`
**Priority:** H | **Project:** osmen.media.pipeline | **Tags:** fix_needed, tier2
**Depends on:** e9d3e070
**Agent:** coder (gpt-5.4) + D may need to interact with browser

#### What's broken
SABnzbd redirects to `/wizard/` on every restart. Root cause: `sabnzbd.ini` missing or unreadable in the config volume.

#### Exact steps
```bash
# Step 1: Check if config volume is mounted correctly
podman exec osmen-media-sabnzbd ls -la /config/
podman exec osmen-media-sabnzbd cat /config/sabnzbd.ini 2>&1 | head -5

# Step 2a: If sabnzbd.ini exists but wizard still shows
# The ini may be incomplete. Check its size:
podman exec osmen-media-sabnzbd wc -l /config/sabnzbd.ini

# Step 2b: If sabnzbd.ini is missing
# Need to complete wizard to generate it

# Step 3: Complete wizard via API (preferred over browser)
# First, check if SABnzbd API is accessible
curl -sf 'http://127.0.0.1:8082/api?mode=qstatus&output=json' | python3 -m json.tool 2>/dev/null || echo "API not ready, wizard mode active"

# Step 4: If wizard must be completed manually, prompt D
# D opens http://127.0.0.1:8082/wizard/ in browser
# Configure: Host: news.eweka.nl, Port: 563, SSL: yes, Connections: 50

# Step 5: After wizard completion, backup the config
podman exec osmen-media-sabnzbd cp /config/sabnzbd.ini /config/sabnzbd.ini.bak

# Step 6: Restart and verify wizard doesn't reappear
systemctl --user restart osmen-media-sabnzbd.service
sleep 5
curl -sf 'http://127.0.0.1:8082/' -o /dev/null -w '%{http_code}'
# Should NOT redirect to /wizard/

# Step 7: Verify API works
curl -sf 'http://127.0.0.1:8082/api?mode=qstatus&output=json' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Status: {d.get(\"status\",\"unknown\")}')"
```

#### Verification checklist
- [ ] /config/sabnzbd.ini exists and is non-empty
- [ ] Backup exists at /config/sabnzbd.ini.bak
- [ ] HTTP 200 at root (not redirect to /wizard/)
- [ ] API qstatus returns valid JSON

#### TW closure
```bash
task ec589dc6 done
task ec589dc6 annotate "SABnzbd wizard regression fixed. Config persists through restart. Eweka configured. API verified."
```

---

### 39477865 qBittorrent auth recovery: nuke + recreate
**UUID:** `39477865-8454-4864-9ccd-2431def4e173`
**Priority:** H | **Project:** osmen.media.pipeline | **Tags:** fix_needed
**Depends on:** e9d3e070
**Agent:** coder (gpt-5.4)

#### What's broken
qBittorrent WebUI auth is locked after PBKDF2 reset churn. D chose option (b): nuke config and start fresh.

#### Exact steps
```bash
# Step 1: Stop the container
systemctl --user stop osmen-media-qbittorrent.service

# Step 2: Find and clear the config volume
podman volume inspect systemd-osmen-qbit-config 2>/dev/null || podman volume inspect osmen-qbit-config 2>/dev/null
VOLUME_PATH=$(podman volume inspect systemd-osmen-qbit-config 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['Mountpoint'])" 2>/dev/null)

# Step 3: Nuke qBittorrent config files
sudo rm -rf "$VOLUME_PATH/qBittorrent_config/"*
sudo rm -rf "$VOLUME_PATH/.config/"* 2>/dev/null
sudo rm -rf "$VOLUME_PATH/.local/share/qBittorrent/"* 2>/dev/null
# Or more targeted:
sudo rm -f "$VOLUME_PATH"/qBittorrent_config/qBittorrent.conf
sudo rm -f "$VOLUME_PATH"/qBittorrent_config/config.json

# Step 4: Start container fresh
systemctl --user start osmen-media-qbittorrent.service

# Step 5: Check logs for temp password
sleep 5
podman logs osmen-media-qbittorrent 2>&1 | grep -i 'password\|admin\|temp' | tail -5
# qBittorrent 4.x generates a temp password on first run when none exists

# Step 6: Login with temp password
# Open http://127.0.0.1:9090 in browser
# Username: admin, Password: <temp from logs>
# Or try default: admin/adminadmin

# Step 7: Set new permanent password via WebUI
# Tools → Options → Web UI → Set password

# Step 8: Verify API login works
curl -sf 'http://127.0.0.1:9090/api/v2/auth/login' -d 'username=admin&password=<new_password>' -c /tmp/qbit-cookies.txt
curl -sf 'http://127.0.0.1:9090/api/v2/app/version' -b /tmp/qbit-cookies.txt
```

#### Verification checklist
- [ ] WebUI accessible at :9090
- [ ] Can login with new password
- [ ] API v2 auth/login returns "Ok."
- [ ] API v2/app/version returns version string

#### TW closure
```bash
task 39477865 done
task 39477865 annotate "qBittorrent auth recovered via nuke+recreate. New password set. API login verified."
```

#### TaskFlow: This unblocks
- f35bf91c Prowlarr search investigation (also needs ec589dc6 SAB fix)

---

### T3.4 Add FIREWALL_OUTBOUND_SUBNETS to gluetun
**UUID:** `b30e0a61-d180-42eb-8fd1-665dd53175b2`
**Priority:** M | **Project:** osmen.media.pipeline | **Tags:** fix_needed, tier3
**Depends on:** e9d3e070
**Agent:** coder (gpt-5.4)
**Fixes:** COMICS-024 [596f59ac], COMICS-028 [e3777ec3]

#### What's broken
Gluetun VPN blocks all non-VPN traffic. Containers in the VPN pod (Prowlarr, qBittorrent) can't reach local services like FlareSolverr. This also blocks COMICS-024 and COMICS-028.

#### Exact steps
```bash
# Add to gluetun quadlet under [Container] section
cd ~/dev/OsMEN-OC/quadlets
# Add FIREWALL_OUTBOUND_SUBNETS environment variable
if ! grep -q 'FIREWALL_OUTBOUND_SUBNETS' media/osmen-media-gluetun.container; then
  # Add after last Environment= line
  sed -i '/^\[Container\]/a Environment=FIREWALL_OUTBOUND_SUBNETS=10.89.0.0/24,192.168.0.0/16' media/osmen-media-gluetun.container
fi

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart osmen-media-gluetun.service

# Wait for VPN to reconnect
sleep 10

# Verify VPN still works
podman exec osmen-media-gluetun wget -qO- ifconfig.me

# Verify local access from pod
podman exec osmen-media-prowlarr curl -sf http://10.89.0.1:8191/health 2>/dev/null || echo "FlareSolverr not deployed yet, that's OK"
```

#### Verification
- [ ] Gluetun env has FIREWALL_OUTBOUND_SUBNETS
- [ ] VPN still connects (ifconfig.me shows VPN IP)
- [ ] Prowlarr can reach local subnet (when FlareSolverr exists)

#### TW closure
```bash
task b30e0a61 done
# Also close COMICS-024 and COMICS-028 since root cause is fixed
task 596f59ac done
task e3777ec3 done
task b30e0a61 annotate "Added FIREWALL_OUTBOUND_SUBNETS to gluetun. VPN pod can now reach local services. COMICS-024 and COMICS-028 root cause resolved."
```

---

## ═══════════════════════════════════════════
## TIER 3 — ARR STACK (9 tasks, ~2-3 hours)
## ═══════════════════════════════════════════

---

### f35bf91c Investigate Prowlarr search
**UUID:** `f35bf91c-870d-4d92-8ad1-8db945b0feaf`
**Priority:** M | **Project:** osmen.media.pipeline | **Tags:** fix_needed
**Depends on:** 39477865 (qBit auth) + ec589dc6 (SAB fix)
**Agent:** researcher (gpt-5.4)
**Blocks:** All downstream arr deployments (T3.1, T3.2, T3.3 + indexer tasks)

#### Exact steps
```bash
# Step 1: Test Prowlarr search after download-stack is stable
curl -sf 'http://127.0.0.1:9696/api/v1/search?query=test&indexerIds=-1' \
  -H 'X-Api-Key: <PROWLARR_API_KEY>' | python3 -m json.tool | head -20

# Step 2: If empty results, check each component:
# 2a: Are indexers configured?
curl -sf 'http://127.0.0.1:9696/api/v1/indexer' -H 'X-Api-Key: <KEY>' | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} indexers configured')"

# 2b: Are download clients connected?
curl -sf 'http://127.0.0.1:9696/api/v1/downloadclient' -H 'X-Api-Key: <KEY>' | python3 -m json.tool

# 2c: Check Prowlarr logs
podman logs osmen-media-prowlarr 2>&1 | tail -50 | grep -i 'error\|fail\|refused\|timeout'

# Step 3: If indexers exist but search returns empty, test individual indexer
curl -sf 'http://127.0.0.1:9696/api/v1/indexer/test' -H 'X-Api-Key: <KEY>' -X POST

# Step 4: Document findings
# The root cause will be one of:
# - Indexers not configured (need to add them)
# - Download clients not connected (need to rewire after auth fix)
# - Network issue (FlareSolverr not reachable → fixed by T3.4)
# - Prowlarr bug (rare, check version)
```

#### TW closure
```bash
task f35bf91c done
task f35bf91c annotate "Prowlarr search investigated. Root cause: <findings>. Resolution: <what was done>."
```

#### TaskFlow: This unblocks MASS
- T3.1 Sonarr [40195403]
- T3.2 Radarr [2c5036fc]
- T3.3 Lidarr/Readarr/Bazarr/Mylar3 [0e432174]
- Prowlarr torrent indexers [d5d7e885]
- Mylar3 NZB indexer [2fca00f8]
- Prowlarr app sync [3550426b]
- Cron cleanup [e94c22a8]

---

### T3.1 Deploy Sonarr
**UUID:** `40195403-b9bf-4a1e-b79d-a7e802d94859`
**Priority:** M | **Project:** osmen.media.pipeline | **Tags:** deploy, tier3
**Depends on:** f35bf91c
**Agent:** coder (gpt-5.4)

#### Exact steps
```bash
systemctl --user start osmen-media-sonarr.service
systemctl --user status osmen-media-sonarr.service

# Verify WebUI
curl -sf 'http://127.0.0.1:8989/' -o /dev/null && echo "Sonarr ✅" || echo "Sonarr ❌"

# Configure via API
# Set root folder
curl -sf 'http://127.0.0.1:8989/api/v3/rootfolder' -H 'X-Api-Key: <KEY>' -X POST -H 'Content-Type: application/json' -d '{"path":"/media/tv"}'

# Connect to Prowlarr
curl -sf 'http://127.0.0.1:8989/api/v3/notification' # verify connectivity

# Connect download clients (SABnzbd + qBittorrent)
# This is typically done through the UI or API

# Enable on boot
systemctl --user enable osmen-media-sonarr.service
```

#### TW closure
```bash
task 40195403 done
task 40195403 annotate "Sonarr deployed. Root folder /media/tv configured. Connected to Prowlarr."
```

---

### T3.2 Deploy Radarr
**UUID:** `2c5036fc-7918-4749-b738-c0edc1996d66`
**Priority:** M | **Project:** osmen.media.pipeline | **Tags:** deploy, tier3
**Depends on:** f35bf91c
**Agent:** coder (gpt-5.4)

#### Exact steps (same pattern as Sonarr)
```bash
systemctl --user start osmen-media-radarr.service
curl -sf 'http://127.0.0.1:7878/' -o /dev/null && echo "Radarr ✅" || echo "Radarr ❌"
# Root folder: /media/movies
# Connect to Prowlarr + download clients
systemctl --user enable osmen-media-radarr.service
```

#### TW closure
```bash
task 2c5036fc done
task 2c5036fc annotate "Radarr deployed. Root folder /media/movies. Connected to Prowlarr."
```

---

### T3.3 Deploy remaining arr apps
**UUID:** `0e432174-5d52-433f-9f9e-14ed07b1992d`
**Priority:** M | **Project:** osmen.media.pipeline | **Tags:** deploy, tier3
**Depends on:** f35bf91c
**Agent:** coder (gpt-5.4)

#### Covers: Lidarr, Readarr, Bazarr, Mylar3

```bash
# Start all
systemctl --user start osmen-media-lidarr.service
systemctl --user start osmen-media-readarr.service
systemctl --user start osmen-media-bazarr.service
systemctl --user start osmen-media-mylar3.service

# Verify ports
curl -sf http://127.0.0.1:8686/ -o /dev/null && echo "Lidarr ✅" || echo "Lidarr ❌"
curl -sf http://127.0.0.1:8787/ -o /dev/null && echo "Readarr ✅" || echo "Readarr ❌"
curl -sf http://127.0.0.1:6767/ -o /dev/null && echo "Bazarr ✅" || echo "Bazarr ❌"
curl -sf http://127.0.0.1:8090/ -o /dev/null && echo "Mylar3 ✅" || echo "Mylar3 ❌"

# Enable all
for svc in lidarr readarr bazarr mylar3; do
  systemctl --user enable osmen-media-$svc.service
done
```

#### TW closure
```bash
task 0e432174 done
task 0e432174 annotate "Lidarr, Readarr, Bazarr, Mylar3 all deployed and enabled."
```

---

### Downstream Prowlarr tasks (unblocked after f35bf91c)

These are all low-priority tasks that get unblocked when Prowlarr is verified working:

| UUID | Task | Agent |
|------|------|-------|
| d5d7e885 | Add torrent indexers (Anidex, 1337x, ACG.RIP) | coder (browser-based) |
| 2fca00f8 | Mylar3 NZB indexer | coder |
| 3550426b | Prowlarr app sync to Lidarr+Readarr | coder |
| 7c09fe94 | Lidarr root folder /media/music | basic |
| 64b22a1f | Readarr root folder /media/books | basic |
| de9510c8 | Bazarr verify Sonarr/Radarr sync | basic |
| 0f03c8c1 | Add private tracker accounts | USER_ACTION (D) |
| 8bcebe2e | Consider FlareSolverr container | researcher (evaluation only) |

Each follows the same pattern: start service → verify port → configure via API or WebUI → mark done in TW.

---

## ═══════════════════════════════════════════
## TIER 4 — LIBRARIAN + MONITORING (3 tasks, ~2-3 hours)
## ═══════════════════════════════════════════

---

### T4.1 Deploy librarian services
**UUID:** `5f96950f-bfd8-4a0e-86cb-93d2a1d9fd3f`
**Priority:** M | **Project:** osmen.install.p11 | **Tags:** deploy, tier4
**Depends on:** T0.9 [aa97a670]
**Agent:** coder (gpt-5.4)

#### Covers: Kavita, Komga, Audiobookshelf, ConvertX, Whisper

```bash
# Start all librarian services
for svc in kavita komga audiobookshelf convertx whisper; do
  systemctl --user start osmen-media-$svc.service 2>/dev/null || systemctl --user start osmen-core-$svc.service 2>/dev/null
done

# Verify ports
curl -sf http://127.0.0.1:2020/ -o /dev/null && echo "Kavita ✅" || echo "Kavita ❌"  # or whatever port
curl -sf http://127.0.0.1:8080/ -o /dev/null && echo "Komga ✅" || echo "Komga ❌"
# ... check each service's configured port

# Fix known issues:
# - Komga: malformed quadlet (missing Unit section) — check quadlet file
# - Kavita: needs library rescan at /manga-downloads mount
# - ConvertX: verify it can reach output directories

# Enable all
for svc in kavita komga audiobookshelf convertx whisper; do
  systemctl --user enable osmen-media-$svc.service 2>/dev/null || systemctl --user enable osmen-core-$svc.service 2>/dev/null
done
```

#### TW closure
```bash
task 5f96950f done
task 5f96950f annotate "All librarian services deployed: Kavita, Komga, Audiobookshelf, ConvertX, Whisper."
```

---

### T4.2 Deploy monitoring stack
**UUID:** `b192eba3-bed4-407c-b067-11ad4ec87641`
**Priority:** M | **Project:** osmen.install.p11 | **Tags:** deploy, tier4
**Depends on:** T0.9 [aa97a670]
**Agent:** coder (gpt-5.4)
**Blocks:** Homepage dashboard (T4.3)

#### Covers: Grafana, Prometheus, Uptime Kuma, Portall

```bash
# Start monitoring services
systemctl --user start osmen-core-grafana.service
systemctl --user start osmen-core-prometheus.service
systemctl --user start osmen-core-uptimekuma.service
systemctl --user start osmen-core-portall.service

# Verify each
curl -sf http://127.0.0.1:3000/ -o /dev/null && echo "Grafana ✅" || echo "Grafana ❌"  # default 3000
curl -sf http://127.0.0.1:9090/ -o /dev/null && echo "Prometheus ✅" || echo "Prometheus ❌"
# ... check configured ports

# Enable all
for svc in grafana prometheus uptimekuma portall; do
  systemctl --user enable osmen-core-$svc.service
done
```

#### TW closure
```bash
task b192eba3 done
task b192eba3 annotate "Monitoring stack deployed: Grafana, Prometheus, Uptime Kuma, Portall."
```

---

### T4.3 Deploy Homepage dashboard
**UUID:** `f52aa05c-3c94-4fae-baa1-b20f68792c42`
**Priority:** M | **Project:** osmen.dashboard.homepage | **Tags:** deploy, tier4
**Depends on:** T4.2 [b192eba3]
**Agent:** coder (gpt-5.4)

Depends on monitoring being up first for widget data. Provides D visibility into all services.

#### TW closure
```bash
task f52aa05c done
task f52aa05c annotate "Homepage dashboard deployed. All service widgets configured."
```

---

## ═══════════════════════════════════════════
## TIER 5 — CORE APPS (3 tasks, ~1-2 hours)
## ═══════════════════════════════════════════

---

### T5.1 Deploy Nextcloud
**UUID:** `efccd48a-f1fd-408a-a6cb-5a0739e3e6ff`
**Priority:** H | **Project:** osmen.install.p16 | **Tags:** deploy, tier5
**Depends on:** T1.1 [PostgreSQL] + T1.2 [Redis]
**Agent:** coder (gpt-5.4)
**Blocks:** P16.4 Nextcloud admin setup

```bash
systemctl --user start osmen-core-nextcloud.service
systemctl --user status osmen-core-nextcloud.service

# Verify
curl -sf http://127.0.0.1:8080/ -o /dev/null && echo "Nextcloud ✅" || echo "Nextcloud ❌"
# Check configured port in quadlet — may be different

# Enable
systemctl --user enable osmen-core-nextcloud.service
```

#### TW closure
```bash
task efccd48a done
task efccd48a annotate "Nextcloud deployed. Waiting for admin setup (P16.4)."
```

---

### P16.4 Configure Nextcloud admin
**UUID:** `22c73013-01b7-4a7f-9e0e-e46f74dd4fa0`
**Priority:** H | **Project:** osmen.install.p16 | **Tags:** USER_ACTION, install, phase16
**Depends on:** T5.1 [efccd48a]
**⚠️ USER_ACTION — D must complete admin setup in browser**

#### What D needs to do
1. Open Nextcloud URL in browser (http://127.0.0.1:<port> or via Caddy reverse proxy)
2. Create admin account (username + password)
3. Configure database connection (PostgreSQL: host=osmen-core-postgres, db=nextcloud, user=postgres)
4. Configure Redis cache (host=osmen-core-redis, port=6379)
5. Set trusted domains
6. Install recommended apps (Calendar, Contacts, etc.)

#### TW closure (after D confirms)
```bash
task 22c73013 done
task 22c73013 annotate "Nextcloud admin setup complete. Admin user created. DB + Redis connected."
```

---

### T5.2 Deploy SiYuan + Langflow + ChromaDB
**UUID:** `01f9770d-f906-44bc-b5bf-f70b9b5d4d31`
**Priority:** M | **Project:** osmen.install.p11 | **Tags:** deploy, tier5
**Depends on:** T1.1 [PostgreSQL]
**Agent:** coder (gpt-5.4)
**Blocks:** T7.4 PKM architecture

```bash
systemctl --user start osmen-core-siyuan.service
systemctl --user start osmen-core-langflow.service
systemctl --user start osmen-core-chromadb.service

# Verify each
# SiYuan: check port
# Langflow: check port
# ChromaDB: curl http://localhost:8000/api/v1/heartbeat

systemctl --user enable osmen-core-siyuan.service
systemctl --user enable osmen-core-langflow.service
systemctl --user enable osmen-core-chromadb.service
```

#### TW closure
```bash
task 01f9770d done
task 01f9770d annotate "SiYuan, Langflow, ChromaDB deployed and enabled."
```

---

## ═══════════════════════════════════════════
## TIER 6 — CLEANUP (7 tasks, ~1-2 hours)
## ═══════════════════════════════════════════

No strict dependency ordering. Run after main stabilization work.

---

### T6.1 Fix broken ~/media/ symlinks
**UUID:** `044d82e5-bc01-4daa-b47d-9ec82556c3d0`
**Agent:** coder

```bash
# Current: symlinks point to /run/media/dwill/... (auto-mount path)
# Should point to: /mnt/... (fstab mount path)
ls -la ~/media/
# Fix each symlink
for link in ~/media/*; do
  if [ -L "$link" ]; then
    target=$(readlink "$link")
    new_target=$(echo "$target" | sed 's|/run/media/dwill/|/mnt/|')
    if [ "$target" != "$new_target" ]; then
      ln -sfn "$new_target" "$link"
      echo "Fixed: $link → $new_target"
    fi
  fi
done
```

---

### T6.2 Clean duplicate volumes
**UUID:** `458d5c39-a312-4a86-9d45-2e1b3a7c6879`
**Agent:** coder — **can reclaim 172GB**

```bash
# List all volumes
podman volume ls

# Find duplicates (osmen-X vs systemd-osmen-X)
podman volume ls | grep -E 'osmen-' | sort

# Check which are in use
podman ps -a --format '{{.Names}}' | while read c; do
  podman inspect "$c" --format '{{range .Mounts}}{{.Name}} {{end}}' 2>/dev/null
done | tr ' ' '\n' | sort -u > /tmp/in-use-volumes.txt

# Remove unused duplicates
for vol in $(podman volume ls -q | grep '^osmen-'); do
  if ! grep -q "$vol" /tmp/in-use-volumes.txt; then
    echo "UNUSED: $vol ($(podman volume inspect "$vol" --format '{{.Mountpoint}}'))"
    # podman volume rm "$vol"  # uncomment to actually remove
  fi
done
```

---

### T6.3 Move SABnzbd volume off root NVMe
**UUID:** `54356b8e-bab1-4c71-97a7-0c84daeb05a0`
**Agent:** coder — **frees 125GB on root drive**

```bash
# Stop SABnzbd
systemctl --user stop osmen-media-sabnzbd.service

# Find target external drive with space
df -h /mnt/*

# Copy volume to external drive
SOURCE=$(podman volume inspect systemd-osmen-sab-config --format '{{.Mountpoint}}')
TARGET=/mnt/<external-drive>/sabnzbd-config/
rsync -av --progress "$SOURCE/" "$TARGET"

# Update quadlet to point to new location (bind mount instead of volume)
# OR: create a new volume at the external path and swap

# Restart and verify
systemctl --user start osmen-media-sabnzbd.service
```

---

### T6.4 Fix sdc2 double-mount
**UUID:** `146420d5-ecb3-4316-a7b3-20d3f4e5ed38`
**Agent:** coder

```bash
# Check current mounts
mount | grep sdc
findmnt | grep -i other_media

# Decide: keep /mnt/other-media (fstab) or /run/media/dwill/Other_Media (auto)
# fstab is more reliable for server use
# Remove the auto-mount entry or ensure only fstab path is used

# Update any container quadlets referencing the wrong path
grep -r '/run/media/dwill/Other_Media' quadlets/
# Replace with /mnt/other-media
```

---

### T6.5 Git commit all stabilization changes
**UUID:** `41d07875-a62b-429e-a8e2-b6c0c5d58c26`
**Agent:** coder

```bash
cd ~/dev/OsMEN-OC
git add -A
git status  # review before committing
git commit -m "stabilization: resolve merge conflicts, fix quadlets, deploy core services

- Resolved 5 git merge conflicts in core quadlets
- Created 4 missing systemd slice definitions
- Fixed ReadOnly on 20+ container quadlets
- Pinned floating container images
- Added PUID/PGID to linuxserver containers
- Deployed PostgreSQL, Redis, Caddy
- Reconciled download stack to systemd
- Fixed SABnzbd wizard regression
- Recovered qBittorrent auth
- Deployed arr stack, monitoring, librarian services
- Deployed Nextcloud, SiYuan, Langflow, ChromaDB"
```

---

### e94c22a8 Clean stale cron jobs
**UUID:** `e94c22a8-5ef8-47f0-a628-7a08e08e1d93`
**Depends on:** f35bf91c
**Agent:** basic

```bash
# List all OpenClaw cron jobs
openclaw cron list

# Identify manga/comics keepalive crons that are no longer needed
# Remove or disable them
```

---

### 73148b16 Baseline git repos
**UUID:** `73148b16-22f5-4264-9d54-5f25bb4b8e67`
**Agent:** basic

```bash
cd ~/dev/OsMEN-OC
git branch -a  # see all branches
git branch -d <stale-branches>  # delete local
git remote prune origin  # clean remote tracking
git push origin --delete <stale-branches>  # delete remote
git checkout main
git pull origin main
git status  # should be clean after T6.5
```

---

## ═══════════════════════════════════════════
## TIER 7 — POST-STABILIZATION (9 tasks)
## ═══════════════════════════════════════════

These are new features that depend on the base being stable. They run AFTER Tiers 0-6.

| UUID | Task | Depends on | Agent | Est. |
|------|------|------------|-------|------|
| 65198fea | T7.1 Paperless-ngx | PG + Redis | coder | 2-3h |
| a7405a34 | T7.2 Multi-agent Discord team | — | coder | 4-8h |
| 8bc9470a | T7.3 Calendar bidirectional | D decision | coder | 2-3h |
| 341da7b2 | T7.4 PKM architecture | SiYuan (T5.2) | coder | 4-8h |
| 5dbe60ec | T7.5 BentoPDF | — | coder | 1h |
| 3ea8737a | T7.6 Miniflux RSS | PostgreSQL | coder | 1h |
| 6fc1d092 | T7.7 Pangolin eval | — | researcher | 2h |
| aeb8836e | T7.8 Restic/Borgmatic backups | — | coder | 2-3h |
| 2e0788ce | T7.9 OpenClaw security | — | coder | 1-2h |

Each of these gets its own detailed sub-plan when it's time to execute. The pattern is the same: quadlet exists → start → configure → verify → enable → mark done.

---

## ═══════════════════════════════════════════
## PARALLEL TRACKS (detailed)
## ═══════════════════════════════════════════

### Bridge Tests (USER_ACTION — D must trigger)

| UUID | Task | What D does | Verify |
|------|------|-------------|--------|
| 50f22dd9 | P10.6 Telegram send | Send message to bot on Telegram | Agent receives + responds |
| abc7220e | P10.7 Telegram receive | Check if agent message arrives in Telegram | Message appears in chat |
| 361efaf5 | P10.8 Discord mention | @mention bot in Discord channel | Bot responds |
| a1eaea82 | P10.9 Approval flow | Trigger high-risk tool call | ApprovalGate prompts D |

### User Decisions

| UUID | Task | Decision needed | D's answer |
|------|------|-----------------|------------|
| fa1a7b31 | P17.5 Calendar policy | bidirectional vs operator-only | **(b) bidirectional** ← LOCKED IN |
| b2ea175b | P14.5 PKM restore | restore from backup? | **(c) fresh start** ← LOCKED IN |

### Inference (manual launch window)

| UUID | Task | Prerequisite | Notes |
|------|------|-------------|-------|
| c068808e | P8.9 LM Studio API | D starts LM Studio GUI | Verify at :1234/v1/models |
| 361bd3e3 | P8.11 CUDA→Vulkan fallback | LM Studio + Ollama running | Test routing rules |

### Storage Health + Security (background, low urgency)

| UUID | Task | Command | Risk |
|------|------|---------|------|
| 1c786063 | SMART nvme0n1 (Windows) | `sudo smartctl -a /dev/nvme0n1` | Read-only |
| 057251c8 | SMART nvme1n1 (Linux) | `sudo smartctl -a /dev/nvme1n1` | Read-only |
| fe3003f3 | SMART sda (plex 4.5T) | `sudo smartctl -a /dev/sda` | Read-only |
| 4ca99894 | SMART sdb (TV_Anime) | `sudo smartctl -a /dev/sdb` | Read-only |
| d9bff796 | SMART sdc (Other_Media) | `sudo smartctl -a /dev/sdc` | Read-only |
| 7561267c | Encrypt Windows drive | BitLocker setup | ⚠️ Destructive — ask D |
| 4739ffa0 | Verify LUKS Linux | `sudo cryptsetup luksDump /dev/nvme1n1p3` | Read-only |

### ACP Roadmap (P19 done — UNBLOCKED)

All 8 tasks had stale "Blocked on P19" annotations. P19 completed 2026-04-16. These need annotation updates:

| UUID | Task | Type | Annotation fix needed |
|------|------|------|----------------------|
| 798b75c2 | Design external-agent ingress | design | Remove "Blocked on P19" |
| e82cf34f | Define cross-runtime envelope schema | design | Remove "Blocked on P19" |
| a65adb44 | Implement external-agent relay | implement | Remove "Blocked on P19" |
| 6d075a81 | Test external-agent handoff | test | Remove "Blocked on P19" |
| 193228cf | VS Code Insiders integration | integration | Remove "Blocked on P19" |
| e1b155e7 | Claude Code ACP adapter | integration | Remove "Blocked on P19" |
| 2d27cc01 | OpenCode ACP adapter | integration | Remove "Blocked on P19" |
| f69cbf10 | OpenClaw external-agent registration | integration | Remove "Blocked on P19" |

TW command to fix annotations:
```bash
for uuid in 798b75c2 e82cf34f a65adb44 6d075a81 193228cf e1b155e7 2d27cc01 f69cbf10; do
  task "$uuid" annotate "CORRECTED 2026-04-18: P19 orchestration COMPLETED 2026-04-16. No longer blocked on P19."
done
```

### DevX Cleanup (P19 done — UNBLOCKED)

| UUID | Task | Action |
|------|------|--------|
| 9333bd4c | Audit Claude + OpenCode integrations | Remove "Blocked on P19" annotation |
| 063fb19f | Review plugin set | Remove "Blocked on P19" annotation |
| 0ca93f69 | Prune stale agent definitions | Remove "Blocked on P19" annotation |
| ecb0d650 | Inventory MCP servers/tools | Remove "Blocked on P19" annotation |

### Configure (unblocked)

| UUID | Task | Notes |
|------|------|-------|
| 698baa34 | opencode.json prompt tuning | Remove "Blocked on P19" — it's done |
| ae32e5fc | Sync lemonade-server stack | Verify Lemonade is running, configure providers |
| a50716ac | Update opencode.json plugins | Review current plugin list |

### Dashboard Plan (P23 chain — 8 tasks)

Self-contained dependency chain:
```
P23.1 [834f2eb7] Podman API bridge (no deps)
  → P23.2 [06fe98f9] Homepage quadlet
    → P23.3 [cfef7b11] Service generator
      → P23.4 [7b821f02] Build config
        → P23.5 [fc9ca136] Secrets strategy
    → P23.6 [56dcf547] Caddy proxy
      → P23.7 [acb3c046] Deploy + verify (needs P23.5 + P23.6)
        → P23.8 [1494649f] Commit + document
```

### Media Pipeline Backlog (wait for download-stack)

These 10 tasks are all blocked on download-stack stabilization. They're low priority until Tiers 0-2 complete.

| UUID | Task | Status |
|------|------|--------|
| 2916dbc4 | Manga bulk download | 94/299 series done, still running |
| f4052196 | Komga rescan + dedup | Waiting on Komga restart |
| 596f59ac | COMICS-024 VPN access | Root cause: FIREWALL_OUTBOUND_SUBNETS (fixed in T3.4) |
| e3777ec3 | COMICS-028 FlareSolverr | Same root cause as COMICS-024 |
| 58a28e05 | COMICS-015 final verification | Waiting on all downloads complete |
| cd799283 | Post-process for Kavita | Waiting on downloads |
| f9da6576 | Verify Kavita library | Waiting on Kavita container restart |
| 2e9c45da | Document manga setup | Waiting on completion |
| 3fba28e2 | Manga torrents from Nyaa | aria2c completed, further downloads blocked by qBit auth |
| 8bcebe2e | Consider FlareSolverr container | Evaluation only, FlareSolverr exists but can't be reached from VPN pod |

---

# TASKFLOW INTEGRATION

## Flow identity
```
controllerId: "osmen/install-stabilization"
goal: "Execute TW dependency graph to stable single-source-of-truth state"
currentStep: <derived from TW unblocked tier>
```

## Execution loop
```
1. Query TW: `task status:pending depends.none: +UNBLOCKED`
2. If none → flow is finished
3. If +USER_ACTION → setWaiting({kind: "user_action", twUuid: <uuid>})
4. If +USER_INPUT → setWaiting({kind: "user_input", twUuid: <uuid>})
5. Otherwise → spawn subagent with task description + context
6. On subagent completion → `task <uuid> done` + annotate
7. Go to 1
```

## Parallel execution strategy
```
TIER 0:  Spawn up to 4 subagents in parallel
  - coder: T0.1 + T0.2 (quadlet fixes)
  - coder: T0.4 (ReadOnly) + T0.5 (pin images) + T0.6 (PUID/PGID)
  - coder: T0.3 (UFW — needs elevated)
  - basic: T0.7 (HealthCmd) + T0.8 (daily notes)

TIER 1:  Spawn 3 in parallel (all depend on T0.9 only)
  - coder: T1.1 PostgreSQL
  - coder: T1.2 Redis
  - coder: T1.3 Caddy

TIER 2:  Spawn download-stack reconciliation, then SAB + qBit in parallel

TIER 3:  Spawn Prowlarr fix, then arr stack in parallel

TIER 4:  Spawn librarian + monitoring in parallel, Homepage after monitoring

TIER 5:  Spawn Nextcloud + SiYuan in parallel (different deps)

TIER 6:  Spawn cleanup tasks in parallel after main work
```

## stateJson
```json
{
  "completedTasks": [],
  "currentTwUuid": null,
  "blockedOnUser": [],
  "subagentRuns": {},
  "tierStatus": {
    "tier0": "pending",
    "tier1": "pending",
    "tier2": "pending",
    "tier3": "pending",
    "tier4": "pending",
    "tier5": "pending",
    "tier6": "pending",
    "tier7": "pending"
  },
  "startTime": "2026-04-18T09:23:00-05:00",
  "lastUpdated": "2026-04-18T09:23:00-05:00"
}
```

## Tags → TaskFlow action mapping

| Tag | Action | Subagent type |
|-----|--------|---------------|
| +USER_ACTION | setWaiting() → prompt D | — |
| +USER_INPUT | setWaiting() → prompt D | — |
| +fix_needed | runTask() → spawn coder | coder (gpt-5.4) |
| +deploy | runTask() → spawn coder | coder (gpt-5.4) |
| +cleanup | runTask() → spawn coder | coder (gpt-5.4) |
| +verify | runTask() → spawn researcher | researcher (gpt-5.4) |
| +security | runTask() → spawn coder (may need elevated) | coder (gpt-5.4) |
| +plan | skip (documentation only) | — |
| +quadlet | runTask() → spawn coder | coder (gpt-5.4) |

---

# PRE-EXECUTION CLEANUP (run before TaskFlow starts)

These TW maintenance tasks should run before the execution loop begins:

```bash
# 1. Fix stale "Blocked on P19" annotations (9 tasks)
for uuid in 798b75c2 e82cf34f a65adb44 6d075a81 193228cf e1b155e7 2d27cc01 f69cbf10 063fb19f; do
  task "$uuid" annotate "CORRECTED 2026-04-18: P19 COMPLETED 2026-04-16. No longer blocked."
done

# 2. Fix misleading VPN split routing annotations
task 596f59ac annotate "CORRECTED 2026-04-18: Fix is FIREWALL_OUTBOUND_SUBNETS in gluetun, not split routing."
task e3777ec3 annotate "CORRECTED 2026-04-18: Same root cause as COMICS-024. Fix is FIREWALL_OUTBOUND_SUBNETS."
task d22320ce annotate "CORRECTED 2026-04-18: VPN routing verified correct. Issue is Gluetun blocking local subnet, not split routing."

# 3. Demote Prowlarr search from H to M (can't diagnose until qBit + SAB are fixed)
task f35bf91c modify priority:M

# 4. Fix opencode.json prompt tuning annotation
task 698baa34 annotate "CORRECTED 2026-04-18: P19 COMPLETED. No longer blocked. Ready for prompt tuning."
```

---

# SUMMARY

## What this plan does
1. **Fixes the foundation** (merge conflicts, broken directives, floating images, missing slices)
2. **Secures the system** (UFW firewall, remove root containers, tighten OpenClaw)
3. **Restores systemd ownership** of all containers (reboot-safe)
4. **Deploys core infrastructure** (PostgreSQL, Redis, Caddy, monitoring)
5. **Stabilizes the download stack** (SABnzbd, qBittorrent, Prowlarr)
6. **Deploys the arr stack** (Sonarr, Radarr, Lidarr, Readarr, Bazarr, Mylar3)
7. **Deploys core apps** (Nextcloud, SiYuan, Langflow, ChromaDB)
8. **Cleans up** (volumes, symlinks, git, TW annotations)
9. **Enables new features** (Paperless-ngx, Discord multi-agent, PKM, backups)

## What it does NOT do (until D says so)
- No pod restructuring (topology is sound)
- No manga/comics pipeline expansion (wait for stabilization)
- No ACP implementation (design phase only)
- No encryption changes (destructive, needs D present)
- No LM Studio verification (needs D to launch GUI)

## Critical path: ~6-10 hours of agent work + ~30 min of D's time

## How to modify
- Reprioritize: `task <uuid> modify priority:H` → TaskFlow picks it up
- Add task: `task add ... depends:<uuid>` → enters graph naturally
- Skip task: `task <uuid> done` → dependents unblock
- Pause everything: TaskFlow `requestCancel()` → TW state preserved

---

*TW is the bible. TaskFlow reads it. This file is the comprehensive view. Generated by Opus 4.6 for D.*
