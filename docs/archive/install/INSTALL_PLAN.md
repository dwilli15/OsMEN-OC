# OsMEN-OC First Install Plan — Comprehensive Multi-Phase Checklist
# Generated: 2026-04-07 | Branch: install/fresh-setup-20260407
# System: Ubuntu 26.04 (Resolute Raccoon), Python 3.13.12, Ryzen AI 9 365
# Scope: FULL — 23 phases, ~271 steps, 30+ services, NO deferrals, NO stubs, phase execution matrix, step-detail rubric
# Source: temp_preplancleanos.txt + osmen-oc-scaffold-prompt.md

# EXECUTION MODEL
- This file is the canonical operator runbook for the `install/fresh-setup-20260407` branch.
- All install-session artifacts, temporary outputs, logs, and preserved plan snapshots stay under `/home/dwill/dev/OsMEN-OC/temp_1st_install/`.
- Every executed step must append a timestamped result line to `install.log` in the form: `[ISO8601] P{N}.{X} — command summary — result — verification evidence`.
- Every phase begins with a briefing and explicit approval, then runs straight through except at tagged interaction points.
- Rootless-first remains the default posture. Use `pkexec` only at steps explicitly tagged `[PKEXEC]` or where verification proves escalation is unavoidable.
- Use `python3.13` explicitly for all venv and Python bootstrap work. Do not rely on bare `python3` on this host.
- Any mismatch between verified host state and this plan must be resolved in favor of verified host state, with the plan updated before proceeding.
- Reusable repo changes get committed on the install branch in phase-sized chunks. Machine-local secrets, live tokens, and private env files never get committed.

# INTERACTION TAGS
- `[PKEXEC]` — expect a PolicyKit password dialog or privileged file mutation.
- `[USER INPUT]` — the operator needs a concrete value such as a token, auth code, path, or provider choice.
- `[USER ACTION]` — the user must complete a browser, desktop, or service-side action outside the terminal.
- `[USER DECISION]` — the user must choose between supported install paths, storage locations, or provider options.
- `[INTERACTIVE]` — the step launches an interactive CLI or wizard that should be driven live.
- `[SHARED SYSTEM]` — the step affects external/shared state such as GitHub, messaging bridges, or pushed branches.

# STANDARD PHASE EXIT CONTRACT
- Command execution is not enough; each phase exits only after the listed validation probes pass.
- Host-state mutations must have a corresponding evidence command recorded in `install.log`.
- Repo-state mutations must leave `git status --short` understandable and scoped to the current phase.
- If a phase contains a reboot-sensitive change, the exit gate includes a post-reboot verification item before continuing.
- Any fallback path used during a phase must be written back into the repo or plan so the install remains reproducible.

# INSTALL SESSION ARTIFACT MAP
- `INSTALL_PLAN.md` — current canonical runbook.
- `INSTALL_PLAN_v1_172steps.md` — preserved earlier version for delta review only.
- `install.log` — timestamped execution ledger; authoritative record of what really ran.
- `SESSION_INIT.md` — baseline machine truth captured at session start.
- `AUDIT_FINDINGS.md` — pre-install defects, constraints, and verified corrections.
- `temp_preplancleanos.txt` — canonical expectation source for the full stack and pitfall registry.

# PHASE PROFILE SNAPSHOT

## P0 Profile — Repo Readiness
- Intent: freeze the branch baseline, capture pre-install corrections, and ensure the repo is safe to mutate.
- Touches: git config, commit history, tracked install artifacts.
- Exit evidence: clean working tree, correct branch, known commit hash in log.

## P1 Profile — Host Baseline + GPU Truth
- Intent: establish truthful package, driver, bootloader, SSH, and storage state before higher-level tooling.
- Touches: apt package database, initramfs/dracut config, sshd config, fstab, bootloader state.
- Exit evidence: `nvidia-smi`, Vulkan device enumeration, `lsmod | grep amdxdna`, SSH key auth, mount test.

## P2 Profile — Userland Tooling + Hardware Control
- Intent: install operator-facing binaries and power/fan/network tooling that later phases assume already exist.
- Touches: `~/.local/bin`, Tailscale state, TLP services, nbfc-linux config, PATH setup.
- Exit evidence: version probes for sops/OpenClaw/Tailscale/TLP/gh/ruff plus route sanity for Tailscale.

## P3 Profile — Python Dev Baseline
- Intent: make the repo executable and testable with the pinned interpreter and dev dependencies.
- Touches: `.venv`, editable install metadata, Python package cache.
- Exit evidence: import test, pytest, ruff, mypy, and a clean phase-specific commit if fixes were needed.

## P4 Profile — Podman Runtime Envelope
- Intent: confirm rootless Podman works and impose hard resource ceilings before inference/media services exist.
- Touches: subuid/subgid, user podman socket, slice unit files, systemd user daemon state.
- Exit evidence: rootless=true, cgroup v2 confirmed, container smoke test, four slices visible to systemd.

## P5 Profile — Quadlet Registration
- Intent: stage every service unit in systemd without prematurely starting containers that still lack secrets.
- Touches: quadlet directories, network definitions, service registration.
- Exit evidence: 25+ units visible, correctly named, and still stopped/disabled unless explicitly static.

## P6 Profile — Secret Plane
- Intent: create the complete secret set for databases, VPN, SiYuan, Plex, and encrypted repo backups.
- Touches: Podman secret store, `~/.config/sops/age`, `~/.config/osmen/secrets/.sops.yaml`, local encrypted backup files.
- Exit evidence: expected secret count, successful SOPS decrypt, age key backed up and documented.

## P7 Profile — Core Data Plane
- Intent: bring up PostgreSQL, Redis, and ChromaDB as the minimum viable execution substrate.
- Touches: container images, persistent volumes, migrations, pgvector extension state.
- Exit evidence: service health, SQL schema visibility, vector extension present, restart persistence proven.

## P8 Profile — Inference Plane
- Intent: stand up CUDA-backed Ollama and Vulkan-backed LM Studio with verified routing boundaries.
- Touches: inference quadlets/services, model cache, compute-routing config.
- Exit evidence: model list, 768-dim embedding response, GPU visibility in each runtime, routing notes updated.

## P9 Profile — Runtime Configuration + Gateway
- Intent: bind live credentials and local service endpoints into OsMEN-OC and validate the gateway/MCP surface.
- Touches: `~/.config/osmen/env`, setup marker, gateway runtime, `config/openclaw.yaml`.
- Exit evidence: health endpoint, MCP tool list, readiness checks, gateway logs showing dependency state.

## P10 Profile — Control Plane Bridges
- Intent: bring OpenClaw online and verify bidirectional Telegram/Discord integration plus approval routing.
- Touches: Node global install path, OpenClaw config, messaging credentials, bridge connections.
- Exit evidence: WS handshake, message send/receive, approval notification roundtrip.

## P11 Profile — VPN Download Pod
- Intent: enforce VPN-first download isolation with gluetun owning the shared network namespace.
- Touches: pod definition, gluetun env file, qBittorrent/SABnzbd config volumes, download directories.
- Exit evidence: VPN IP mismatch from home IP, no DNS leak, no IPv6 leak, clients reachable only through the pod.

## P12 Profile — Arr Automation
- Intent: wire indexers and media managers to the VPN-bound download clients.
- Touches: media quadlets, arr API keys, internal service wiring.
- Exit evidence: all four services healthy and cross-connected with live API tests.

## P13 Profile — Media Serving
- Intent: expose Plex, enrich metadata with Kometa, and capture usage/transfer events with Tautulli.
- Touches: Plex config, GPU passthrough, media library mounts, webhook wiring.
- Exit evidence: Plex UI, claimed server, Tautulli UI, webhook event observed downstream.

## P14 Profile — PKM / RAG Path
- Intent: convert SiYuan and file ingestion into a working chunk→embed→store→retrieve loop.
- Touches: SiYuan workspace, ConvertX, memory modules, Chroma collections.
- Exit evidence: end-to-end ingest test returns relevant chunks with embeddings stored in both structured and vector tiers.

## P15 Profile — Voice Stack
- Intent: make transcription and speech generation usable from the local runtime with multiple engines.
- Touches: `.venv` audio deps, local model cache, `core/voice`, `config/voice`.
- Exit evidence: STT transcript quality acceptable, TTS WAV output intelligible, dispatcher module functional.

## P16 Profile — Operator Infrastructure
- Intent: provide file sync, reverse proxying, service dashboards, and low-friction local service discovery.
- Touches: Nextcloud, Caddy config, `/etc/hosts`, Uptime Kuma, Portall.
- Exit evidence: proxied URLs resolve, dashboards reachable, monitors configured for all major services.

## P17 Profile — Task System
- Intent: reconnect Taskwarrior to the event bus and optional calendar sync without blocking local task operations.
- Touches: Taskwarrior hooks, queue worker, task config, optional Google credentials.
- Exit evidence: task add emits an event, hooks do not block on dependency failure, sync worker processes queue.

## P18 Profile — Automation + Recovery
- Intent: make backups, maintenance, and health checks repeatable without manual babysitting.
- Touches: timer units, backup script, restic repo, memory maintenance and DB upkeep jobs.
- Exit evidence: seven timers registered, backup script runs cleanly, at least one restic snapshot exists.

## P19 Profile — Real Code Completion
- Intent: close the remaining implementation gap between scaffold and working system using repo-native code.
- Touches: core hardware/inference/knowledge/media/notifications/orchestration modules plus matching tests/config.
- Exit evidence: real modules present, tests added, full `make check` passes without stubs.

## P20 Profile — Gaming Safety Envelope
- Intent: validate that the laptop still serves its gaming role and that inference respects that constraint.
- Touches: Steam/XIVLauncher installs, GPU routing policy, compute-routing documentation.
- Exit evidence: FFXIV visible on NVIDIA, inference fallback works under VRAM pressure.

## P21 Profile — Optional Observability Plane
- Intent: make Prometheus/Grafana available on demand without bloating the always-on baseline.
- Touches: monitoring quadlets, scrape config, dashboards, Caddy routes.
- Exit evidence: metrics visible when started, units cleanly stop when not needed, no port conflicts remain.

## P22 Profile — Closure + Audit
- Intent: prove the install is real, reproducible, and ready for handoff or review.
- Touches: full service set, pitfall checks, git history, remote branch, PR metadata.
- Exit evidence: every critical service probe passes, PF01-PF20 reviewed, branch pushed, PR prepared.

# PHASE EXECUTION MATRIX

| Phase | Start Gate | Exit Gate | Rollback |
|-------|------------|-----------|----------|
| P0 | Repository is clean enough to record baseline state | Branch identity, commit history, and install artifacts are aligned | Reset only local notes; do not rewrite historical install evidence |
| P1 | Host is booted into Ubuntu 26.04 and rootless-first posture is available | Apt packages, GPU/NPU, SSH, bootloader, and mount checks all pass | Revert config files and package installs that changed host truth |
| P2 | Core host packages are present and PATH is sane | sops/OpenClaw/Tailscale/TLP/nbfc/gh/ruff are available and versioned | Remove local binaries or mask services that were added for trial installs |
| P3 | Python 3.13 is available for venv creation | Editable install, tests, lint, and type checks are green | Delete `.venv` and reinstall from source state if needed |
| P4 | Podman package and subuid/subgid are ready | Rootless Podman works with slice limits and container smoke test | Delete only user-level podman config and reapply slices |
| P5 | Quadlet targets and directories exist | All quadlet units are registered but not started | Remove generated symlinks and reload the systemd user daemon |
| P6 | Secret strategy is decided and age key handling is available | All required Podman secrets and encrypted config files exist | Delete incorrect secrets, regenerate age key, re-encrypt configs |
| P7 | Images are reachable and secrets exist | PostgreSQL, Redis, and ChromaDB are healthy and migrated | Stop containers, remove volumes only if initial provisioning failed |
| P8 | Core data plane is stable | Ollama and LM Studio expose the expected APIs and models | Stop inference services and remove only trial models if necessary |
| P9 | Environment values are collected | Wizard writes env, gateway starts, MCP tools enumerate | Re-run wizard and overwrite generated local config files only |
| P10 | OpenClaw and messaging credentials are ready | Bridges exchange messages and approval flow is exercised | Disable bridge services and clear only local connector config |
| P11 | VPN credentials and download directories exist | gluetun owns the pod namespace and leak checks pass | Tear down the pod and recreate only the download-stack units |
| P12 | Download clients can reach the VPN pod | Prowlarr, Sonarr, Radarr, and Bazarr are cross-wired | Stop arr services and reapply only service-specific API config |
| P13 | Media libraries and Plex claim data are ready | Plex, Kometa, and Tautulli are reachable and tied together | Remove transient media service config; keep library data intact |
| P14 | PKM workspace and vector services are reachable | SiYuan, ConvertX, embeddings, ingest, and retrieval all work | Stop PKM services, preserve workspace, redo ingest config |
| P15 | Python audio deps and model access exist | STT and TTS round-trips succeed with at least one engine per direction | Uninstall optional audio extras and retain the core venv |
| P16 | Reverse proxy and hostnames are ready | Nextcloud, Caddy, Uptime Kuma, and Portall are reachable | Stop infrastructure services and revert hostname mappings only |
| P17 | Taskwarrior data and Redis queue path exist | task events flow through the queue and optional calendar sync works | Remove hook scripts and queue files, preserve task history |
| P18 | Backup targets and repo location are known | Timers fire, restic snapshots exist, and maintenance jobs are registered | Disable timers and delete only generated unit files or bad repo pointers |
| P19 | Runtime services already exist | Core modules, tests, and configs are real and executable | Revert the module commit set; do not rewrite the service plan |
| P20 | GPU drivers and game runtime are present | FFXIV runs while inference respects VRAM policy | Remove game launch wrappers and restore routing config only |
| P21 | Monitoring remains opt-in | Prometheus and Grafana can start cleanly when needed | Leave them disabled and remove only the monitoring config if broken |
| P22 | Everything above has already been validated | Pitfall audit, push, and PR are complete | Fix forward on the branch; do not lose verified install evidence |

# STEP DETAIL RUBRIC

Use this rubric for every numbered step below. The step text is intentionally compact, but each step is executed as a full mini-procedure with the following fields:

- **Command**: the exact shell, wizard, or browser action to run.
- **Expected output**: the version string, health response, file permission, log line, or UI state that proves success.
- **Failure triage**: the first likely cause class to inspect if the command fails; always check dependency order, permissions, network reachability, and service state before guessing.
- **Rollback note**: the local-only undo action if the step creates a bad state. Prefer re-running the step cleanly over inventing a new workaround.
- **Evidence**: a timestamped summary line must be appended to `install.log` for the completed step.

When a step already names a `Verify`, `Expected`, or `Check` outcome, treat that line as the authoritative success condition. If a step has no explicit success text, use the phase exit gate plus the relevant service health check as the success condition.

Failure triage order for this plan:
1. Binary or package missing
2. Wrong interpreter or PATH
3. Permission or ownership problem
4. Service not started or wrong unit target
5. Config file missing or malformed
6. Network/authentication failure
7. Runtime health check failure

Verification style for this plan:
- Prefer exact version probes over vague "it works" checks.
- Prefer health endpoints, `systemctl --user status`, `podman ps`, or `curl -sf` over manual assumptions.
- Prefer log evidence from `journalctl --user` or service-specific logs when a health check is ambiguous.
- Prefer explicit file mode checks for credentials and local secret material.

# ═══════════════════════════════════════════════════════════════════════
# PHASE 0: Repository & Git Identity ✅ COMPLETE
# Prereq: None | Output: Clean branch ready for commits
# Status: DONE — commit 281c213 on install/fresh-setup-20260407
# ═══════════════════════════════════════════════════════════════════════

## P0.1 ✅ Configure git user.name
## P0.2 ✅ Configure git user.email
## P0.3 ✅ Stage pre-install fixes (bootstrap.sh, Makefile, .gitignore, migrations)
## P0.4 ✅ Commit pre-install fixes
## P0.5 ✅ Verify commit on branch
## P0.6 ✅ Verify working tree clean
## P0.7 ✅ Log Phase 0 results

# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: System Packages + GPU Drivers
# Prereq: Phase 0 | Output: All apt packages installed, GPUs verified
# Elevation: pkexec required for apt operations
# Steps: 15 (P1.1–P1.15)
# ═══════════════════════════════════════════════════════════════════════

## P1.1 Update apt cache [PKEXEC]
- Command: `pkexec apt-get update -qq`
- GUI password dialog will appear

## P1.2 Install core system packages [PKEXEC]
- Command:
  ```
  pkexec apt-get install -y --no-install-recommends \
    python3-dev python3-venv \
    podman podman-compose \
    taskwarrior lm-sensors smartmontools \
    restic age nftables \
    ffmpeg build-essential \
    git curl wget htop tmux vim neovim jq \
    openssh-server
  ```
- Note: python3.13, git may already be present — apt will skip

## P1.3 Verify NVIDIA driver + CUDA
- Command: `nvidia-smi`
- Expected: RTX 5070 Laptop, Driver 580+, CUDA 13.0, ~8151 MiB VRAM
- If missing: `pkexec apt-get install -y nvidia-driver-580` + reboot

## P1.4 NVIDIA modules in initramfs (LUKS critical) [PKEXEC]
- Pitfall PF01: LUKS + NVIDIA early loading conflict
- Command:
  ```
  echo "nvidia nvidia_modeset nvidia_uvm nvidia_drm" | pkexec tee /etc/modules-load.d/nvidia.conf
  pkexec update-initramfs -u
  ```
- Note: Ubuntu 26.04 uses Dracut — may need `pkexec dracut -f` instead
- Verify after reboot: `lsmod | grep nvidia_drm`

## P1.5 Verify AMD iGPU + Vulkan
- Command: `lspci -k | grep -A3 "Display controller"`
- Expected: AMD Radeon 780M with amdgpu driver
- Also: `vulkaninfo 2>/dev/null | grep deviceName` → both GPUs listed
- If issues: `pkexec apt-get install --reinstall firmware-amd-graphics mesa-vulkan-drivers`

## P1.6 Check NPU / AMD XDNA 2
- Command: `lspci | grep -i xdna`
- Command: `lsmod | grep amdxdna`
- Expected: amdxdna module loaded (kernel 7.0)
- Pitfall PF02: May need out-of-tree module from AMD repo
- If not loaded: `pkexec modprobe amdxdna` — mark experimental, CPU fallback always available

## P1.7 Verify dual boot GRUB
- Command: `grep -c menuentry /boot/grub/grub.cfg` (should show multiple entries)
- Check: Ubuntu and Windows Boot Manager entries exist
- If Windows missing: `GRUB_DISABLE_OS_PROBER=false` in /etc/default/grub → `pkexec update-grub`

## P1.8 SSH hardening [PKEXEC]
- Restore ~/.ssh/ from backup if available
- Verify: `ssh -T git@github.com` (key auth)
- Harden sshd_config:
  ```
  pkexec sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
  pkexec sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
  ```
- Enable: `pkexec systemctl enable --now sshd`

## P1.9 Windows drive on-demand mount [PKEXEC]
- Command:
  ```
  pkexec mkdir -p /mnt/windows
  ```
- Add to fstab: `UUID=<blkid-of-nvme0n1p3> /mnt/windows ntfs3 ro,noauto,nofail,x-gvfs-show 0 0`
- Test: `pkexec mount /mnt/windows && ls /mnt/windows && pkexec umount /mnt/windows`

## P1.10 Verify python3.13-venv
- Command: `python3.13 -m venv --help >/dev/null 2>&1 && echo OK`
- If broken: `pkexec apt-get install -y python3.13-venv`

## P1.11 Verify Node.js available
- Command: `node --version && npm --version`
- If missing: will install in Phase 2

## P1.12 Verify all package installs
- Commands:
  ```
  podman --version
  task --version
  sensors --version
  smartctl --version
  restic version
  age --version
  ffmpeg -version | head -1
  jq --version
  ```

## P1.13 Install npm if not bundled
- Command: `which npm || pkexec apt-get install -y npm`

## P1.14 Install Node.js v22 LTS (if system version too old)
- Check: `node --version` — need v22+
- If too old: download from nodejs.org to ~/.local/lib/ or use volta/nvm
- Verify: `node --version` → v22.x

## P1.15 Commit any system-level config changes to repo
- Stage and commit any modified config files

### PAUSE POINT 1 — All apt packages verified, GPUs confirmed

# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: Userland Tools + Hardware Management
# Prereq: Phase 1 | Output: sops, Tailscale, TLP, nbfc ready
# Steps: 12 (P2.1–P2.12)
# ═══════════════════════════════════════════════════════════════════════

## P2.1 Install sops
- Check apt: `apt-cache show sops 2>/dev/null`
- If not in apt:
  ```
  curl -Lo ~/.local/bin/sops https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64
  chmod +x ~/.local/bin/sops
  ```
- Verify: `sops --version`

## P2.2 Install OpenClaw
- Command: `npm install -g openclaw`
- If npm publication is unavailable, install from a source checkout under `~/.local/share/openclaw-src`, build the CLI locally, and place the resulting executable on PATH so the control-plane dependency is still satisfied in this install pass.
- Verify: `openclaw --version`

## P2.3 Install Tailscale
- Command: `curl -fsSL https://tailscale.com/install.sh | sh`
- Bring up: `pkexec tailscale up` (login as dwilli15@github) [USER ACTION — browser auth]
- Verify: `tailscale status` → shows this machine
- Pitfall PF15: Tailscale routing must NOT interfere with gluetun VPN

## P2.4 Install TLP power management [PKEXEC]
- Command: `pkexec apt-get install -y tlp tlp-rdw`
- Enable: `pkexec systemctl enable --now tlp`
- Mask conflict: `pkexec systemctl mask power-profiles-daemon`
- Verify: `pkexec tlp-stat -s` → active
- Pitfall PF20: TLP and power-profiles-daemon conflict

## P2.5 Install nbfc-linux (fan control)
- Check apt: `apt-cache show nbfc-linux 2>/dev/null`
- If not available: build from source (https://github.com/nbfc-linux/nbfc-linux)
- Configure: `nbfc config -s "HP Omen"` (or closest match)
- Verify: `nbfc status` → fan readings
- Pitfall PF10: HP Omen BIOS may fight fan control

## P2.6 Verify PATH includes ~/.local/bin
- Check: `echo $PATH | tr ':' '\n' | grep -E '\.local/bin|\.npm'`
- If missing: `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc`

## P2.7 Install gh CLI (if not present)
- Check: `gh --version`
- If missing: `pkexec apt-get install -y gh` or download from GitHub releases
- Auth: `gh auth status` — should already be authenticated as dwilli15

## P2.8 Verify Taskwarrior
- Command: `task --version`
- Already installed in P1.2

## P2.9 Install pipx (for isolated Python tools)
- Command: `python3.13 -m pip install --user pipx`
- Verify: `pipx --version`

## P2.10 Install ruff (linter, outside venv for global use)
- Command: `pipx install ruff`
- Verify: `ruff --version`

## P2.11 Verify all tools
- Run comprehensive check:
  ```
  sops --version && tailscale version && tlp-stat -b 2>/dev/null | head -1 && \
  gh --version | head -1 && ruff --version
  ```

## P2.12 Commit tool configuration files
- Stage any new config files, commit on install branch

### PAUSE POINT 2 — CLI tools and hardware management ready

# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: Python Environment
# Prereq: Phase 1 (python3-dev) | Output: .venv with all deps, tests green
# Steps: 8 (P3.1–P3.8)
# ═══════════════════════════════════════════════════════════════════════

## P3.1 Create .venv with Python 3.13
- Command: `python3.13 -m venv .venv`
- Verify: `.venv/bin/python --version` → 3.13.x
- CRITICAL: Never use bare `python3` (system 3.14.3)

## P3.2 Bootstrap pip
- Command: `.venv/bin/python -m pip install --upgrade pip`

## P3.3 Install OsMEN-OC (editable + dev extras)
- Command: `.venv/bin/python -m pip install -e ".[dev]"`
- Installs: fastapi, uvicorn, pydantic, pyyaml, loguru, httpx, anyio, cronsim,
            websockets, pytest, ruff, mypy, pytest-cov, types-PyYAML
- Also install lang* stack: `.venv/bin/pip install langchain langchain-community langgraph`
  These are execution-engine dependencies for workflow orchestration (LangGraph)
  and tool/prompt abstraction (LangChain). LangFlow is a separate containerized service (P14).

## P3.4 Verify core import
- Command: `.venv/bin/python -c "import core; print(core.__version__)"`
- Expected: `0.1.0`

## P3.5 Run test suite
- Command: `.venv/bin/python -m pytest tests/ -q --timeout=15`
- Expected: All pass
- If failures: diagnose and fix before proceeding

## P3.6 Run linter
- Command: `.venv/bin/python -m ruff check core/ tests/`
- Expected: Clean (0 violations)

## P3.7 Run type checker
- Command: `.venv/bin/python -m mypy core/ --ignore-missing-imports`
- Expected: Clean or expected warnings only

## P3.8 Commit any fixes from test/lint/typecheck
- If changes needed: fix, test, commit

### PAUSE POINT 3 — Dev environment fully green

# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: Rootless Podman + cgroup Resource Slices
# Prereq: Phase 1 (podman) | Output: Podman rootless + 4 resource slices
# Steps: 10 (P4.1–P4.10)
# ═══════════════════════════════════════════════════════════════════════

## P4.1 Verify subuid/subgid [PKEXEC if missing]
- Check: `grep "^$(whoami):" /etc/subuid /etc/subgid`
- If missing:
  ```
  pkexec usermod --add-subuids 100000-165535 "$(whoami)"
  pkexec usermod --add-subgids 100000-165535 "$(whoami)"
  ```

## P4.2 Enable podman socket
- Command: `systemctl --user enable --now podman.socket`
- Verify: `systemctl --user is-active podman.socket`

## P4.3 Verify rootless podman
- Command: `podman info --format '{{.Host.Security.Rootless}}'`
- Expected: `true`

## P4.4 Test container execution
- Command: `podman run --rm docker.io/library/alpine:3.20 echo "Podman works"`
- Clean up: `podman image rm docker.io/library/alpine:3.20`

## P4.5 Verify cgroup v2
- Command: `stat -fc %T /sys/fs/cgroup` → `cgroup2fs`
- Also: `podman info --format '{{.Host.CgroupVersion}}'` → `v2`

## P4.6 Create slice: user-osmen-inference.slice
- File: `quadlets/slices/user-osmen-inference.slice`
- Content: `[Slice]\nMemoryMax=16G\nCPUQuota=800%`
- Pitfall PF12: Ollama will eat all RAM without this cap

## P4.7 Create slice: user-osmen-services.slice
- File: `quadlets/slices/user-osmen-services.slice`
- Content: `[Slice]\nMemoryMax=4G\nCPUQuota=400%`

## P4.8 Create slice: user-osmen-media.slice
- File: `quadlets/slices/user-osmen-media.slice`
- Content: `[Slice]\nMemoryMax=4G\nCPUQuota=200%`

## P4.9 Create slice: user-osmen-background.slice
- File: `quadlets/slices/user-osmen-background.slice`
- Content: `[Slice]\nMemoryMax=1G\nCPUQuota=100%`

## P4.10 Deploy slices + reload systemd
- Copy slices to ~/.config/systemd/user/ (or via deploy script)
- Command: `systemctl --user daemon-reload`
- Verify: `systemctl --user list-unit-files | grep osmen.*slice`

### PAUSE POINT 4 — Podman rootless + resource limits confirmed

# ═══════════════════════════════════════════════════════════════════════
# PHASE 5: Quadlet Unit Deployment (All Profiles — NOT Started)
# Prereq: Phase 4 | Output: All quadlet units registered in systemd
# Steps: 8 (P5.1–P5.8)
# ═══════════════════════════════════════════════════════════════════════

## P5.1 Create target directories
- Commands:
  ```
  mkdir -p ~/.config/containers/systemd
  mkdir -p ~/.config/systemd/user
  ```

## P5.2 Create Podman networks
- Commands:
  ```
  podman network create osmen-core
  podman network create osmen-media
  ```
- Write quadlet network files: `quadlets/core/osmen-core.network`, `quadlets/media/osmen-media.network`

## P5.3 Write all quadlet files — core profile
- Files in `quadlets/core/`:
  - osmen-core-postgres.container
  - osmen-core-redis.container
  - osmen-core-chromadb.container
  - osmen-core-siyuan.container
  - osmen-core-langflow.container (port 7860, PostgreSQL backend, Slice=user-osmen-services.slice)
  - osmen-core-nextcloud.container
  - osmen-core-caddy.container
  - osmen-core-gateway.container
  - osmen-core.network
  - user-osmen-core.slice (alias → user-osmen-services.slice)

## P5.4 Write all quadlet files — inference profile
- Files in `quadlets/inference/`:
  - osmen-inference-ollama.container (Device=nvidia.com/gpu=all)
  - osmen-inference-lmstudio.service (native binary, not container)

## P5.5 Write all quadlet files — media profile
- Files in `quadlets/media/`:
  - download-stack.pod (ports: 9090, 8082)
  - osmen-media-gluetun.container (VPN gateway)
  - osmen-media-qbittorrent.container (in download-stack pod)
  - osmen-media-sabnzbd.container (in download-stack pod)
  - osmen-media-plex.container (Device=nvidia.com/gpu=all for HW transcoding)
  - osmen-media-prowlarr.container
  - osmen-media-sonarr.container
  - osmen-media-radarr.container
  - osmen-media-bazarr.container
  - osmen-media-kometa.container
  - osmen-media-tautulli.container
  - osmen-media.network

## P5.6 Write all quadlet files — librarian profile
- Files in `quadlets/librarian/`:
  - osmen-librarian-convertx.container
  - osmen-librarian-whisper.container (use this when GPU-backed containerized transcription is desired; local venv transcription in Phase 15 still remains mandatory)
  - osmen-librarian-kavita.container (port 5000, book/comic/manga server)
  - osmen-librarian-audiobookshelf.container (port 13378, audiobook + podcast server)

## P5.7 Write all quadlet files — monitoring profile
- Files in `quadlets/monitoring/`:
  - osmen-monitoring-uptimekuma.container
  - osmen-monitoring-portall.container
  - osmen-monitoring-prometheus.container (disabled by default)
  - osmen-monitoring-grafana.container (disabled by default)

## P5.8 Deploy quadlets + reload systemd
- Command: `scripts/deploy_quadlets.sh --dry-run` (review)
- Then: `scripts/deploy_quadlets.sh` (live)
- Reload: `systemctl --user daemon-reload`
- Verify: `systemctl --user list-unit-files | grep osmen`
- Expected: 25+ units registered, ALL in "disabled" or "static" state
- DO NOT START any services yet — secrets needed first

### PAUSE POINT 5 — All units registered, nothing started

# ═══════════════════════════════════════════════════════════════════════
# PHASE 6: Secrets & Credentials
# Prereq: Phase 5 | Output: All Podman secrets created, SOPS configured
# Steps: 12 (P6.1–P6.12)
# Interactive: Decisions + credentials required
# ═══════════════════════════════════════════════════════════════════════

## P6.1 Generate age keypair [USER DECISION: auto-gen or import]
- Command: `mkdir -p ~/.config/sops/age && age-keygen -o ~/.config/sops/age/keys.txt`
- Pitfall PF17: BACK UP this key — losing it = losing all encrypted secrets
- Display public key for .sops.yaml

## P6.2 Create local SOPS config at ~/.config/osmen/secrets/.sops.yaml
- Content:
  ```yaml
  creation_rules:
    - path_regex: \.enc\.yaml$
      age: <public-key-from-P6.1>
  ```

## P6.3 Create Podman secret: osmen-postgres-password
- Command: `openssl rand -base64 32 | podman secret create osmen-postgres-password -`

## P6.4 Create Podman secret: osmen-postgres-user
- Command: `echo -n "osmen" | podman secret create osmen-postgres-user -`

## P6.5 Create Podman secret: osmen-postgres-db
- Command: `echo -n "osmen" | podman secret create osmen-postgres-db -`

## P6.6 Create Podman secret: osmen-redis-password
- Command: `openssl rand -base64 32 | podman secret create osmen-redis-password -`

## P6.7 Create Podman secret: osmen-chromadb-token
- Command: `openssl rand -base64 32 | podman secret create osmen-chromadb-token -`

## P6.8 Create Podman secret: VPN credentials [USER INPUT]
- User provides Privado VPN WireGuard private key
- Command: `echo -n "<key>" | podman secret create osmen-vpn-private-key -`
- Also: `echo -n "<endpoint>" | podman secret create osmen-vpn-endpoint -`

## P6.9 Create Podman secret: Plex claim token [USER INPUT]
- User gets claim token from https://plex.tv/claim
- Command: `echo -n "<token>" | podman secret create osmen-plex-claim -`

## P6.10 Create Podman secret: SiYuan auth code [USER INPUT]
- User chooses an auth code
- Command: `echo -n "<code>" | podman secret create osmen-siyuan-auth -`

## P6.10a Create Podman secret: OpenClaw gateway token
- Command: `openssl rand -base64 32 | podman secret create osmen-openclaw-gateway-token -`
- This is the `OPENCLAW_GATEWAY_TOKEN` referenced in the scaffold prompt and bridge config

## P6.10b Store GH_TOKEN as SOPS-managed secret
- `gh auth` (P2.7) handles CLI auth but the token must also be available as a SOPS secret
  for CI runners, deploy scripts, and automated issue creation
- Command: `gh auth token | sops --encrypt --input-type raw --output ~/.config/osmen/secrets/gh-token.enc.yaml /dev/stdin`
- Verify: `sops -d ~/.config/osmen/secrets/gh-token.enc.yaml`

## P6.10c Clarify OSMEN_APP_PG_PASSWORD vs osmen-postgres-password [USER DECISION]
- The canonical spec lists both `OSMEN_APP_PG_PASSWORD` and the generic postgres password
- If they are the same secret: document the name mapping and move on
- If separate (e.g., app-level vs superuser): create a second Podman secret:
  `openssl rand -base64 32 | podman secret create osmen-app-pg-password -`

## P6.11 Verify all Podman secrets
- Command: `podman secret ls`
- Expected: 13+ secrets with `osmen-` prefix

## P6.12 Encrypt secrets to SOPS for git backup
- Create `~/.config/osmen/secrets/api-keys.enc.yaml` with SOPS encryption
- Verify: `sops -d ~/.config/osmen/secrets/api-keys.enc.yaml` decrypts correctly
- Repo keeps only `config/secrets/*.template.yaml` files with placeholder values

## P6.13 Export local credential kit for hard-copy backup
- Command: `scripts/secrets/export_credential_kit.sh`
- Output: `~/.local/share/osmen/credential-kit/<timestamp>/credential-kit.txt`
- Operator action: print and store offline alongside the age key backup

### PAUSE POINT 6 — All secrets in place, ready to start services

# ═══════════════════════════════════════════════════════════════════════
# PHASE 7: Core Services (PostgreSQL, Redis, ChromaDB)
# Prereq: Phase 6 | Output: Core data services running + healthy
# Steps: 14 (P7.1–P7.14)
# ═══════════════════════════════════════════════════════════════════════

## P7.1 Pull PostgreSQL image
- Command: `podman pull docker.io/pgvector/pgvector:pg17`

## P7.2 Pull Redis image
- Command: `podman pull docker.io/library/redis:7.2.5-alpine`

## P7.3 Pull ChromaDB image
- Command: `podman pull docker.io/chromadb/chroma:0.5.23`

## P7.4 Start PostgreSQL
- Command: `systemctl --user start osmen-core-postgres`

## P7.5 Start Redis
- Command: `systemctl --user start osmen-core-redis`

## P7.6 Start ChromaDB
- Command: `systemctl --user start osmen-core-chromadb`

## P7.7 Wait for health (all three, up to 90s)
- Command: `podman ps --format "table {{.Names}}\t{{.Status}}"`
- Expected: All three show "healthy"
- Debug: `journalctl --user -u osmen-core-<service> --no-pager -n 50`

## P7.8 Verify PostgreSQL connectivity
- Command: `podman exec osmen-core-postgres pg_isready -U osmen -d osmen`

## P7.9 Verify Redis connectivity
- Command: `podman exec osmen-core-redis redis-cli ping` → PONG

## P7.10 Verify ChromaDB heartbeat
- Command: `curl -sf http://127.0.0.1:8000/api/v1/heartbeat`

## P7.11 Run SQL migrations
- Command: `podman exec -i osmen-core-postgres psql -U osmen -d osmen < migrations/001_initial_schema.sql`
- Verify: `podman exec osmen-core-postgres psql -U osmen -d osmen -c '\dt'`
- Expected tables: audit_trail, audit_archive, schema_version

## P7.12 Enable pgvector extension
- Command: `podman exec osmen-core-postgres psql -U osmen -d osmen -c "CREATE EXTENSION IF NOT EXISTS vector;"`
- Verify: `podman exec osmen-core-postgres psql -U osmen -d osmen -c "SELECT extname FROM pg_extension WHERE extname='vector';"`

## P7.13 Verify data persistence
- Restart: `systemctl --user restart osmen-core-postgres`
- Wait healthy, then: `podman exec osmen-core-postgres psql -U osmen -d osmen -c 'SELECT * FROM schema_version;'`
- Expected: Row with version=1 survives restart

## P7.14 Commit migration/schema changes
- Stage and commit any new/modified migration files

### PAUSE POINT 7 — Core data services running and healthy

# ═══════════════════════════════════════════════════════════════════════
# PHASE 8: Inference Stack (Ollama + LM Studio)
# Prereq: Phase 7 | Output: Local inference with CUDA + Vulkan, embedding model ready
# Steps: 12 (P8.1–P8.12)
# ═══════════════════════════════════════════════════════════════════════

## P8.1 Pull Ollama image
- Command: `podman pull docker.io/ollama/ollama:latest`

## P8.2 Write osmen-inference-ollama.container quadlet
- Must include: `Device=nvidia.com/gpu=all`, Slice=user-osmen-inference.slice
- Volume: osmen-ollama-models
- Port: 11434
- Network: osmen-core

## P8.3 Start Ollama with CUDA GPU access
- Command: `systemctl --user start osmen-inference-ollama`
- Verify: `podman exec osmen-inference-ollama nvidia-smi` → GPU visible inside container

## P8.4 Pull nomic-embed-text model (768-dim embeddings)
- Command: `podman exec osmen-inference-ollama ollama pull nomic-embed-text`
- This is the primary embedding model for all RAG operations

## P8.5 Pull llama3.2:3b model (small local LLM)
- Command: `podman exec osmen-inference-ollama ollama pull llama3.2:3b`

## P8.5a Install Open WebUI (optional, manual-launch only)
- Command: `podman pull ghcr.io/open-webui/open-webui:main`
- DO NOT auto-start — zero resources unless explicitly opened
- Launch manually: `podman run --rm -p 3080:8080 -e OLLAMA_BASE_URL=http://127.0.0.1:11434 ghcr.io/open-webui/open-webui:main`
- Provides browser-based chat UI for Ollama models
- No quadlet — manual-only per canonical spec

## P8.6 Verify Ollama API
- Command: `curl -sf http://127.0.0.1:11434/api/tags | python3.13 -m json.tool`
- Expected: Both models listed

## P8.7 Install LM Studio headless
- Download from https://lmstudio.ai/ to ~/.local/lib/lm-studio/
- Or install via AppImage

## P8.8 Create osmen-inference-lmstudio.service
- systemd user service (not container — native binary)
- Exposes OpenAI-compatible API on port 1234
- Slice: user-osmen-inference.slice
- Vulkan inference on AMD 780M iGPU

## P8.9 Verify LM Studio API
- Command: `curl -sf http://127.0.0.1:1234/v1/models | python3.13 -m json.tool`

## P8.10 Test embedding generation
- Command:
  ```
  curl -s http://127.0.0.1:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"test"}' | python3.13 -c "import sys,json; d=json.load(sys.stdin); print(f'dims={len(d[\"embedding\"])}')"
  ```
- Expected: `dims=768`

## P8.11 Test inference routing (CUDA → Vulkan fallback)
- Verify Ollama uses NVIDIA CUDA: `nvidia-smi` shows ollama process
- Verify LM Studio uses AMD Vulkan: check LM Studio logs for Vulkan device
- Document GPU routing in config/compute-routing.yaml

## P8.12 Commit inference quadlets + config
- Stage and commit inference quadlet files

### PAUSE POINT 8 — Local inference operational (CUDA + Vulkan)

# ═══════════════════════════════════════════════════════════════════════
# PHASE 9: Setup Wizard + Gateway Validation
# Prereq: Phase 7+8 | Output: Config written, gateway running, MCP tools registered
# Steps: 15 (P9.1–P9.15)
# Interactive: API keys, tokens, paths required
# ═══════════════════════════════════════════════════════════════════════

## P9.1 Gather ZAI API key [USER INPUT]
- URL: https://open.bigmodel.cn — sign up, get API key
- Base URL: `https://api.z.ai/api/coding/paas/v4`
- Error 1302 = rate limit → 2 min backoff → auto-downgrade

## P9.2 Gather Telegram bot token [USER ACTION]
- Open Telegram → @BotFather → `/newbot` → get token
- Verify: `curl https://api.telegram.org/bot<TOKEN>/getMe`

## P9.3 Gather Telegram chat ID [USER ACTION]
- Add bot to target group → get chat ID

## P9.4 Gather Discord bot token [USER INPUT, conditional if Discord bridge is enabled in this install pass]
- Discord Dev Portal → New Application → Bot → token
- OAuth2 invite with bot+applications.commands scopes

## P9.5 Gather Discord guild ID [USER INPUT, conditional if Discord bridge is enabled in this install pass]
- Enable Developer Mode in Discord → right-click server → Copy ID

## P9.6 Gather Plex library root [USER DECISION]
- Default: `/home/dwill/media/plex`
- Create: `mkdir -p /home/dwill/media/{plex,staging}`

## P9.7 Gather download staging dir [USER DECISION]
- Default: `/home/dwill/downloads`
- Create: `mkdir -p ~/downloads/{pending,active,complete,torrents}`

## P9.8 Gather Google Calendar creds [USER INPUT, conditional if calendar sync is enabled in this install pass]
- Google Cloud Console → OAuth → download JSON

## P9.9 Run setup wizard [INTERACTIVE]
- Command: `.venv/bin/python -m core.setup`
- Wizard prompts for each field with defaults
- Writes: `~/.config/osmen/env` (chmod 600)
- Creates: `~/.config/osmen/.setup_complete`

## P9.10 Verify env file permissions
- Command: `stat -c '%a' ~/.config/osmen/env` → `600`

## P9.11 Verify DSNs match running services
- postgres_dsn → 127.0.0.1:5432, user osmen
- redis_url → 127.0.0.1:6379
- chromadb → 127.0.0.1:8000

## P9.12 Start gateway
- Command: `set -a && source ~/.config/osmen/env && set +a`
- Then: `.venv/bin/python -m uvicorn core.gateway.app:app --reload --host 127.0.0.1 --port 8080`

## P9.13 Health check
- Command: `curl -s http://127.0.0.1:8080/health | python3.13 -m json.tool`
- Expected: `{"status": "ok", ...}`

## P9.14 MCP tools listing
- Command: `curl -s http://127.0.0.1:8080/mcp/tools | python3.13 -m json.tool`
- Expected: 32+ tools from agent manifests

## P9.15 Verify event bus + bridge status
- Check logs for "EventBus connected" or "EventBus: noop fallback"
- Bridge to OpenClaw: expected to fail if OpenClaw not running yet — OK

### PAUSE POINT 9 — Core platform verified

# ═══════════════════════════════════════════════════════════════════════
# PHASE 10: OpenClaw + Messaging Bridges
# Prereq: Phase 9 | Output: OpenClaw running, Telegram+Discord wired
# Steps: 10 (P10.1–P10.10)
# ═══════════════════════════════════════════════════════════════════════

## P10.1 Verify Node.js v22 installed
- Command: `node --version` → v22.x

## P10.2 Install OpenClaw
- Command: `npm install -g openclaw`
- If registry installation is unavailable, immediately switch to source-based install so Phase 10 still ends with a working control plane and verified bridge.

## P10.2a Restore or install openclaw-keyring
- The `openclaw-keyring` binary reads credentials from GNOME keyring for OpenClaw
- Restore from backup: `cp <backup>/openclaw-keyring ~/.local/bin/openclaw-keyring && chmod +x ~/.local/bin/openclaw-keyring`
- If no backup: build from OpenClaw source or create a shim that reads from `~/.config/osmen/env`
- Verify: `~/.local/bin/openclaw-keyring --version` or test credential retrieval

## P10.3 Configure OpenClaw
- Verify config/openclaw.yaml has correct WebSocket URL (ws://127.0.0.1:18789)
- Set up channel mappings (Telegram, Discord)

## P10.4 Start OpenClaw service
- Command: `systemctl --user enable --now openclaw-gateway.service` (or manual start)
- Verify: `curl -I http://127.0.0.1:18789/`

## P10.5 Verify WebSocket bridge
- Start gateway, check logs: "OpenClaw bridge connected"
- If OpenClaw not available: bridge auto-reconnects with backoff — OK

## P10.6 Test Telegram send [USER ACTION]
- Command: `curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage?chat_id=${TELEGRAM_CHAT_ID}&text=OsMEN-OC+online"`
- Verify: message appears in Telegram chat

## P10.7 Test Telegram receive
- Send message TO bot in Telegram → verify gateway logs show incoming

## P10.8 Test Discord bot [USER ACTION, conditional if Discord bridge is enabled]
- Verify bot appears online in Discord server
- Send test message from OsMEN-OC → Discord channel

## P10.9 Test approval flow
- Trigger a medium-risk tool → verify notification appears in Telegram
- Approve via Telegram → verify tool executes

## P10.10 Commit OpenClaw config
- Stage and commit config changes

### PAUSE POINT 10 — Communication channels wired

# ═══════════════════════════════════════════════════════════════════════
# PHASE 11: VPN + Download Stack Pod
# Prereq: Phase 7 | Output: gluetun VPN pod with qBittorrent + SABnzbd
# Steps: 16 (P11.1–P11.16)
# Architecture: Single Podman pod, shared gluetun network namespace
# ═══════════════════════════════════════════════════════════════════════

## P11.1 Pull gluetun image
- Command: `podman pull docker.io/qmcgaw/gluetun:latest`

## P11.2 Pull qBittorrent image
- Command: `podman pull docker.io/linuxserver/qbittorrent:latest`

## P11.3 Pull SABnzbd image
- Command: `podman pull docker.io/linuxserver/sabnzbd:latest`

## P11.4 Write download-stack.pod quadlet
- Ports: 9090 (qBit WebUI), 8082 (SABnzbd WebUI)
- All containers share gluetun's network namespace

## P11.5 Write osmen-media-gluetun.container quadlet
- Image: qmcgaw/gluetun
- Pod: download-stack
- Env: VPN_SERVICE_PROVIDER=privado, VPN_TYPE=wireguard
- Secrets: VPN private key via Podman secret
- Health: curl ifconfig.me (IP must differ from home IP)

## P11.6 Write osmen-media-qbittorrent.container quadlet
- Image: linuxserver/qbittorrent
- Pod: download-stack (shares gluetun network)
- Volume: osmen-qbit-config, ~/downloads/
- Depends: After=osmen-media-gluetun.service, Requires=osmen-media-gluetun.service

## P11.7 Write osmen-media-sabnzbd.container quadlet
- Image: linuxserver/sabnzbd
- Pod: download-stack
- Volume: osmen-sab-config, ~/downloads/
- Depends: After=osmen-media-gluetun.service

## P11.8 Configure VPN credentials [USER INPUT]
- User provides Privado WireGuard config
- Write env file: `~/.config/containers/systemd/osmen-media-gluetun.env` (chmod 0600)
- Pitfall PF06: NOT in git, managed via SOPS

## P11.9 Create download directories
- Command: `mkdir -p ~/downloads/{pending,active,complete,torrents}`

## P11.10 Start gluetun
- Command: `systemctl --user start download-stack` (or pod unit)

## P11.11 Verify VPN IP (not home IP)
- Command: `podman exec osmen-media-gluetun curl -s ifconfig.me`
- Must show VPN IP, NOT home IP
- Pitfall PF04: DNS leak check

## P11.12 Verify DNS (no leak)
- Command: `podman exec osmen-media-gluetun cat /etc/resolv.conf`
- Must NOT show ISP DNS servers

## P11.13 Verify IPv6 disabled
- Command: `podman exec osmen-media-gluetun curl -6 ifconfig.me 2>&1`
- Must FAIL — Pitfall PF05

## P11.14 Start qBittorrent
- Command: `systemctl --user start osmen-media-qbittorrent`
- Verify: `curl -sf http://127.0.0.1:9090` → WebUI loads

## P11.15 Start SABnzbd
- Command: `systemctl --user start osmen-media-sabnzbd`
- Verify: `curl -sf http://127.0.0.1:8082` → WebUI loads

## P11.16 Verify download stack survives reboot
- Pitfall PF07: Test auto-start after reboot
- Enable: `systemctl --user enable download-stack osmen-media-gluetun osmen-media-qbittorrent osmen-media-sabnzbd`

### PAUSE POINT 11 — VPN download stack operational

# ═══════════════════════════════════════════════════════════════════════
# PHASE 12: Arr Stack (Prowlarr, Sonarr, Radarr, Bazarr)
# Prereq: Phase 11 | Output: Indexer + media managers wired to download clients
# Steps: 12 (P12.1–P12.12)
# ═══════════════════════════════════════════════════════════════════════

## P12.1 Pull Prowlarr image
- Command: `podman pull docker.io/linuxserver/prowlarr:latest`

## P12.2 Pull Sonarr image
- Command: `podman pull docker.io/linuxserver/sonarr:latest`

## P12.3 Pull Radarr image
- Command: `podman pull docker.io/linuxserver/radarr:latest`

## P12.4 Pull Bazarr image
- Command: `podman pull docker.io/linuxserver/bazarr:latest`

## P12.5 Write all arr quadlet files
- `quadlets/media/osmen-media-prowlarr.container` (port 9696)
- `quadlets/media/osmen-media-sonarr.container` (port 8989)
- `quadlets/media/osmen-media-radarr.container` (port 7878)
- `quadlets/media/osmen-media-bazarr.container` (port 6767)
- All on osmen-media network, Slice=user-osmen-media.slice

## P12.6 Start all arr services
- Command: `systemctl --user start osmen-media-{prowlarr,sonarr,radarr,bazarr}`
- Verify all healthy: `podman ps --filter name=osmen-media`

## P12.7 Configure Prowlarr indexers [USER ACTION]
- Open http://127.0.0.1:9696 in browser
- Add indexer sources
- Get API key for downstream connections

## P12.8 Connect Prowlarr → Sonarr/Radarr
- In Prowlarr UI: Settings → Apps → add Sonarr + Radarr
- Use internal network addresses (osmen-media network)

## P12.9 Configure download clients in Sonarr/Radarr
- Settings → Download Clients → add qBittorrent (port 9090 via pod)
- Settings → Download Clients → add SABnzbd (port 8082 via pod)

## P12.10 Configure Bazarr subtitle sources
- Open http://127.0.0.1:6767
- Connect to Sonarr + Radarr
- Add subtitle providers

## P12.11 Verify all arr services healthy
- Prowlarr: `curl -sf http://127.0.0.1:9696/api/v1/health?apikey=...`
- Sonarr: `curl -sf http://127.0.0.1:8989/api/v3/health?apikey=...`
- Radarr: `curl -sf http://127.0.0.1:7878/api/v3/health?apikey=...`
- Bazarr: `curl -sf http://127.0.0.1:6767/api/system/health?apikey=...`

## P12.12 Commit arr quadlet files
- Stage and commit all arr quadlets

### PAUSE POINT 12 — Media automation stack wired

# ═══════════════════════════════════════════════════════════════════════
# PHASE 13: Plex + Kometa + Tautulli
# Prereq: Phase 12 | Output: Plex serving media, Kometa metadata, Tautulli analytics
# Steps: 10 (P13.1–P13.10)
# ═══════════════════════════════════════════════════════════════════════

## P13.1 Pull Plex image
- Command: `podman pull docker.io/plexinc/pms-docker:latest`

## P13.2 Pull Kometa image
- Command: `podman pull docker.io/kometateam/kometa:latest`

## P13.3 Pull Tautulli image
- Command: `podman pull docker.io/tautulli/tautulli:latest`

## P13.4 Write Plex quadlet (NVIDIA GPU passthrough)
- `quadlets/media/osmen-media-plex.container`
- Device=nvidia.com/gpu=all (HW transcoding)
- Network: osmen-media (+ host for DLNA if needed)
- Port: 32400
- Volumes: osmen-plex-config, media library paths
- Slice: user-osmen-media.slice

## P13.5 Write Kometa quadlet
- `quadlets/media/osmen-media-kometa.container`
- Runs on built-in scheduler (daily 3 AM)
- Slice: user-osmen-background.slice

## P13.6 Write Tautulli quadlet
- `quadlets/media/osmen-media-tautulli.container`
- Port: 8181
- Slice: user-osmen-background.slice
- Webhooks → Redis Streams event bus for transfer pipeline

## P13.7 Start Plex + claim server [USER ACTION]
- Command: `systemctl --user start osmen-media-plex`
- Browser: https://app.plex.tv/desktop → claim server
- Verify: `curl -sf http://127.0.0.1:32400/web`

## P13.8 Configure Plex libraries [USER DECISION]
- Movies, TV Shows, Music, etc.
- Point to media directories

## P13.9 Start Kometa + Tautulli
- Command: `systemctl --user start osmen-media-{kometa,tautulli}`
- Verify Tautulli: `curl -sf http://127.0.0.1:8181`

## P13.10 Verify Tautulli webhook → Redis event bus
- Configure webhook in Tautulli → point to OsMEN-OC gateway
- Test: play media → verify event appears in Redis stream

### PAUSE POINT 13 — Media stack fully operational

# ═══════════════════════════════════════════════════════════════════════
# PHASE 14: PKM + Knowledge Pipeline (SiYuan, Obsidian, Langflow, ConvertX, Books, Embeddings, RAG)
# Prereq: Phase 7+8 | Output: Knowledge ingestion pipeline end-to-end
# Steps: 24 (P14.1–P14.24)
# ═══════════════════════════════════════════════════════════════════════

## P14.1 Pull SiYuan image
- Command: `podman pull docker.io/b3log/siyuan:latest`

## P14.2 Write osmen-core-siyuan.container quadlet
- Volume: bind ~/dev/pkm/ as workspace
- Port: 6806
- Network: osmen-core
- Slice: user-osmen-services.slice
- Env: SIYUAN_ACCESS_AUTH_CODE from Podman secret

## P14.3 Start SiYuan
- Command: `systemctl --user start osmen-core-siyuan`

## P14.4 Verify SiYuan API [USER ACTION — verify web UI]
- Command: `curl -sf http://127.0.0.1:6806`
- Browser: open http://127.0.0.1:6806 → enter auth code → verify workspace

## P14.5 Restore PKM data from backup (if available)
- If backup exists: restore ~/dev/pkm/ contents

## P14.5a Install Obsidian (ACP-capable PKM)
- Install via Flatpak: `flatpak install md.obsidian.Obsidian`
- Or via AppImage: download from https://obsidian.md/download → place in ~/.local/bin/
- Vault location: `~/dev/pkm/obsidian/` (sibling to SiYuan workspace)
- Create vault: `mkdir -p ~/dev/pkm/obsidian/`
- Obsidian is ACP-capable — agents can read/write notes via the Obsidian Local REST API plugin
- Verify: launch Obsidian → create vault at ~/dev/pkm/obsidian/ → confirm opens

## P14.5b Configure Obsidian for agent access
- Install community plugin: "Local REST API" (enables HTTP API on localhost:27124)
- Enable the plugin, set API key (store in SOPS: `config/secrets/obsidian-api-key.enc.yaml`)
- Verify: `curl -sf http://127.0.0.1:27124 -H "Authorization: Bearer <key>"`
- This is the ACP bridge surface — OsMEN-OC agents read/write Obsidian notes via this API
- SiYuan and Obsidian operate side-by-side: SiYuan for structured PKM, Obsidian for markdown-native workflows

## P14.5c Pull Langflow image
- Command: `podman pull docker.io/langflowai/langflow:latest`

## P14.5d Write osmen-core-langflow.container quadlet
- Port: 7860
- Network: osmen-core
- Slice: user-osmen-services.slice
- Env: LANGFLOW_DATABASE_URL=postgresql://osmen:<password>@osmen-core-postgres:5432/langflow
- Note: Langflow needs its own PG database — create in P7.11 migrations or ad-hoc:
  `podman exec osmen-core-postgres psql -U osmen -c "CREATE DATABASE langflow;"`

## P14.5e Start Langflow + verify
- Command: `systemctl --user start osmen-core-langflow`
- Verify: `curl -sf http://127.0.0.1:7860/health`
- Browser: open http://127.0.0.1:7860 → verify flow editor loads
- Langflow provides visual LangChain/LangGraph workflow design

## P14.5f Pull Kavita image (book/comic/manga server)
- Command: `podman pull docker.io/jvmilazz0/kavita:latest`

## P14.5g Write osmen-librarian-kavita.container quadlet
- Port: 5000
- Network: osmen-core
- Slice: user-osmen-background.slice
- Volume: ~/media/books/ (bind mount for library)
- `mkdir -p ~/media/{books,comics,manga}`

## P14.5h Start Kavita + configure [USER ACTION]
- Command: `systemctl --user start osmen-librarian-kavita`
- Verify: `curl -sf http://127.0.0.1:5000`
- Browser: create admin account, add library paths

## P14.5i Pull Audiobookshelf image (audiobook + podcast server)
- Command: `podman pull docker.io/advplyr/audiobookshelf:latest`

## P14.5j Write osmen-librarian-audiobookshelf.container quadlet
- Port: 13378
- Network: osmen-core
- Slice: user-osmen-background.slice
- Volumes: ~/media/audiobooks/, ~/media/podcasts/
- `mkdir -p ~/media/{audiobooks,podcasts}`

## P14.5k Start Audiobookshelf + configure [USER ACTION]
- Command: `systemctl --user start osmen-librarian-audiobookshelf`
- Verify: `curl -sf http://127.0.0.1:13378`
- Browser: create admin account, add library paths

## P14.6 Pull ConvertX image
- Command: `podman pull docker.io/c4illin/convertx:latest`

## P14.7 Write osmen-librarian-convertx.container quadlet
- Port: 3000
- Network: osmen-core
- Slice: user-osmen-background.slice

## P14.8 Start ConvertX
- Command: `systemctl --user start osmen-librarian-convertx`
- Verify: `curl -sf http://127.0.0.1:3000`

## P14.9 Write core/memory/embeddings.py (REAL implementation)
- Connects to Ollama nomic-embed-text (port 11434)
- Generates 768-dim embeddings
- Batch embedding support
- Stores in PostgreSQL pgvector + ChromaDB

## P14.10 Write core/knowledge/ingest.py (REAL implementation)
- File ingestion pipeline: detect type → extract text → chunk → embed → store
- Supported: PDF, EPUB, Markdown, HTML, plain text
- Uses sentence-safe chunking from core/memory/chunking.py

## P14.11 Write core/memory/lateral.py (REAL implementation)
- Cross-collection similarity search
- Lateral bridge: find related chunks across different collections
- Uses pgvector cosine similarity

## P14.12 Create ChromaDB collections
- Collections: documents, transcripts, notes, web_pages
- Command: Use ChromaDB API to create collections with metadata

## P14.13 Test ingest pipeline end-to-end
- Test: file → chunk → embed → store → retrieve
- Verify: query returns relevant chunks with similarity scores

## P14.14 Commit PKM quadlets + core modules
- Stage and commit all new files (SiYuan, Obsidian config, Langflow, Kavita, Audiobookshelf, ConvertX, knowledge modules)

### PAUSE POINT 14 — Knowledge pipeline operational (SiYuan + Obsidian + Langflow + books + RAG)

# ═══════════════════════════════════════════════════════════════════════
# PHASE 15: Voice Pipeline (STT + TTS)
# Prereq: Phase 3 (Python venv) | Output: Bidirectional voice
# Steps: 10 (P15.1–P15.10)
# ═══════════════════════════════════════════════════════════════════════

## P15.1 Install faster-whisper in .venv
- Command: `.venv/bin/pip install faster-whisper`
- Add `pyannote.audio` only when speaker diarization is explicitly required for this workstation; base STT remains mandatory with `faster-whisper`.

## P15.2 Download Whisper model
- Command: `.venv/bin/python -c "from faster_whisper import WhisperModel; m = WhisperModel('small'); print('OK')"`
- Model cached to ~/.cache/huggingface/

## P15.3 Test STT: audio → text
- Record or provide test audio file
- Transcribe and verify output accuracy

## P15.4 Install Piper TTS (agent voice, alerts)
- Command: `.venv/bin/pip install piper-tts`
- Download voice model: `piper --download-dir ~/.local/share/osmen/models/piper`

## P15.5 Download Piper voice model
- Model: en_US-lessac-medium (good quality, fast)
- Test: `echo "Hello OsMEN" | piper --model en_US-lessac-medium --output_file /tmp/test.wav`

## P15.6 Test TTS: text → audio → playback
- Verify WAV output is intelligible
- Play: `aplay /tmp/test.wav` or `paplay /tmp/test.wav`

## P15.7 Install Pocket TTS (voice cloning, audiobooks)
- Command: `.venv/bin/pip install pocket-tts inflect scipy`
- HuggingFace auth may be needed for voice cloning models

## P15.8 Install Kokoro TTS (longform backup)
- Command: `.venv/bin/pip install kokoro`
- Verify: `.venv/bin/python -c "import kokoro; print('OK')"`

## P15.9 Write core/voice/ module (REAL implementation)
- `core/voice/__init__.py`
- `core/voice/stt.py` — WhisperModel wrapper, streaming support
- `core/voice/tts.py` — Multi-engine TTS dispatcher (Piper primary, Pocket for cloning, Kokoro for longform)
- Config: `config/voice/tts.yaml` and `config/voice/stt.yaml`

## P15.10 Commit voice modules
- Stage and commit core/voice/ + config/voice/

### PAUSE POINT 15 — Voice pipeline bidirectional

# ═══════════════════════════════════════════════════════════════════════
# PHASE 16: Infrastructure (Nextcloud, Caddy, Uptime Kuma, Portall)
# Prereq: Phase 7 | Output: Reverse proxy, monitoring dashboard, file sync
# Steps: 16 (P16.1–P16.16)
# ═══════════════════════════════════════════════════════════════════════

## P16.1 Pull Nextcloud image
- Command: `podman pull docker.io/library/nextcloud:production-fpm`
- Use production-fpm (lightweight, no Apache)

## P16.2 Write osmen-core-nextcloud.container quadlet
- Network: osmen-core
- Volumes: osmen-nextcloud-data
- Env: POSTGRES_HOST=osmen-core-postgres, REDIS_HOST=osmen-core-redis
- Pitfall PF13: UserNS=keep-id:uid=33,gid=33 for www-data
- Pitfall PF14: Pin version tag, do NOT use :latest

## P16.3 Start Nextcloud
- Command: `systemctl --user start osmen-core-nextcloud`

## P16.4 Configure Nextcloud admin [USER ACTION]
- Browser: complete initial setup wizard
- No Office suite, no Talk — file sync + CalDAV + Tasks + WebDAV only

## P16.5 Wire Nextcloud → PostgreSQL + Redis
- Verify: Nextcloud uses osmen-core-postgres for DB
- Verify: Nextcloud uses osmen-core-redis for cache/locking

## P16.6 Pull Caddy image
- Command: `podman pull docker.io/library/caddy:2-alpine`

## P16.7 Write Caddyfile with *.osmen.local routes
- Create `config/Caddyfile`:
  ```
  plex.osmen.local { reverse_proxy localhost:32400 }
  nextcloud.osmen.local { reverse_proxy localhost:8080 }
  siyuan.osmen.local { reverse_proxy localhost:6806 }
  grafana.osmen.local { reverse_proxy localhost:3000 }
  uptimekuma.osmen.local { reverse_proxy localhost:3001 }
  langflow.osmen.local { reverse_proxy localhost:7860 }
  kavita.osmen.local { reverse_proxy localhost:5000 }
  audiobookshelf.osmen.local { reverse_proxy localhost:13378 }
  portall.osmen.local { reverse_proxy localhost:3080 }
  ```

## P16.8 Write osmen-core-caddy.container quadlet
- Network: osmen-core, osmen-media (dual-homed)
- Ports: 80, 443
- Volume: Caddyfile from repo

## P16.9 Start Caddy, verify reverse proxy
- Command: `systemctl --user start osmen-core-caddy`
- Verify: `curl -sf http://127.0.0.1:80`

## P16.10 Configure /etc/hosts for .osmen.local [PKEXEC]
- Add entries: `127.0.0.1 plex.osmen.local nextcloud.osmen.local siyuan.osmen.local ...`
- Or configure systemd-resolved for .osmen.local domain

## P16.11 Pull Uptime Kuma image
- Command: `podman pull docker.io/louislam/uptime-kuma:latest`

## P16.12 Write osmen-monitoring-uptimekuma.container quadlet
- Port: 3001
- Volume: osmen-uptimekuma-data
- Network: osmen-core

## P16.13 Start Uptime Kuma, configure monitors
- Command: `systemctl --user start osmen-monitoring-uptimekuma`
- Browser: http://127.0.0.1:3001 → create admin account [USER ACTION]
- Add monitors for ALL services (PG, Redis, ChromaDB, Ollama, Plex, etc.)
- Alert channels: Telegram (primary), Discord (secondary)

## P16.14 Write osmen-monitoring-portall.container quadlet
- Port: 3080
- Shows all active services and ports

## P16.15 Start Portall
- Command: `systemctl --user start osmen-monitoring-portall`
- Verify: `curl -sf http://127.0.0.1:3080`

## P16.16 Commit infrastructure quadlets + config
- Stage and commit all infrastructure files

### PAUSE POINT 16 — Infrastructure layer complete

# ═══════════════════════════════════════════════════════════════════════
# PHASE 17: Taskwarrior + Calendar Sync
# Prereq: Phase 1 (taskwarrior) + Phase 7 (Redis) | Output: Task system wired
# Steps: 8 (P17.1–P17.8)
# ═══════════════════════════════════════════════════════════════════════

## P17.1 Restore ~/.taskrc and ~/.task/ from backup
- If backup available: restore Taskwarrior data
- If fresh: `task config data.location ~/.task`

## P17.2 Verify task count
- Command: `task count` → returns number

## P17.3 Configure custom UDAs
- Commands:
  ```
  task config uda.energy.type string
  task config uda.energy.label Energy
  task config uda.energy.values high,medium,low
  ```

## P17.4 Write Taskwarrior hook for Redis queue
- Hook writes to local queue (SQLite or file), async worker processes
- Pitfall PF18: hooks must NEVER block if Redis/Nextcloud is down
- File: ~/.task/hooks/on-add-osmen.py, on-modify-osmen.py

## P17.5 Configure Google Calendar sync [USER INPUT, conditional if calendar sync is enabled]
- Categories synced: work, appointment, deadline → auto-create calendar events
- Categories skipped: chore, quick → no calendar event
- Requires GOOGLE_CALENDAR_CREDENTIALS_PATH

## P17.6 Write core/tasks/sync.py (REAL implementation)
- Taskwarrior ↔ Redis event bus ↔ Google Calendar
- Async worker polls queue every 5 seconds

## P17.7 Test: task add → event bus → calendar
- Create task: `task add "Test OsMEN sync" project:osmen`
- Verify: event appears in Redis stream
- If Calendar configured: verify event created

## P17.8 Commit task modules
- Stage and commit core/tasks/ + hooks

### PAUSE POINT 17 — Task management wired

# ═══════════════════════════════════════════════════════════════════════
# PHASE 18: Timers + Backup (restic + all 7 timers)
# Prereq: Phase 7 | Output: Automated backup, maintenance, monitoring timers
# Steps: 14 (P18.1–P18.14)
# ═══════════════════════════════════════════════════════════════════════

## P18.1 Initialize restic backup repo [USER DECISION: location]
- Options: local (Windows partition via mount), Nextcloud WebDAV, external USB
- Command: `restic init --repo /mnt/windows/backup/osmen`
- Or: `restic init --repo rclone:nextcloud:backup/osmen`

## P18.2 Write scripts/backup.sh (REAL implementation)
- Pitfall PF16: pg_dump ALL databases FIRST, then restic
- Backup targets: ~/.ssh, ~/.gnupg, ~/.config/sops, config/, quadlets/, ChromaDB data, SiYuan workspace
- Verify: script enforces pg_dump-before-restic ordering

## P18.3 Deploy osmen-db-backup.timer (daily 02:30)
- Timer + service unit for database backup

## P18.4 Deploy osmen-memory-maintenance.timer
- Runs core/memory/maintenance.py (promotion/decay between tiers)

## P18.5 Deploy osmen-smart-check.timer
- SMART disk health monitoring via smartctl

## P18.6 Deploy osmen-health-report.timer
- Daily health summary → Telegram notification

## P18.7 Deploy osmen-vpn-audit.timer
- Periodic VPN leak checks (DNS, IPv6)

## P18.8 Deploy osmen-db-vacuum.timer
- PostgreSQL VACUUM ANALYZE on schedule

## P18.9 Deploy osmen-chromadb-compact.timer
- ChromaDB compaction for storage efficiency

## P18.10 Reload systemd, verify all timers
- Command: `systemctl --user daemon-reload`
- Verify: `systemctl --user list-timers --all | grep osmen`
- Expected: 7 timers registered

## P18.11 Test backup script manually
- Command: `bash scripts/backup.sh --dry-run` (if supported)
- Then: `bash scripts/backup.sh`

## P18.12 Verify restic snapshot created
- Command: `restic -r <repo> snapshots`
- Expected: at least 1 snapshot

## P18.13 Back up age key to restic + offline
- Verify: `~/.config/sops/age/keys.txt` is in restic backup
- Pitfall PF17: Losing this key = losing all encrypted secrets

## P18.14 Commit timer units + scripts
- Stage and commit timers/ + scripts/backup.sh

### PAUSE POINT 18 — Backup and maintenance automated

# ═══════════════════════════════════════════════════════════════════════
# PHASE 19: Core Python Modules (REAL implementations)
# Prereq: All services running | Output: Full execution engine code
# Steps: 16 (P19.1–P19.16)
# MANDATE: Write REAL, working code — port from previous OSMEN where available
# SSH: armad@192.168.7.246:c:\dev\osmen for previous implementations
# ═══════════════════════════════════════════════════════════════════════

## P19.1 Write core/hardware/gpu.py
- GPU detection (NVIDIA + AMD), VRAM monitoring, device enumeration
- GPU routing logic: FFXIV on NVIDIA → route inference to AMD Vulkan or CPU
- Pitfall PF11: FFXIV + inference GPU conflict management

## P19.2 Write core/hardware/thermal.py
- TLP integration (power profiles)
- nbfc-linux integration (fan control profiles: silent/balanced/performance)
- Temperature monitoring via lm-sensors

## P19.3 Write core/inference/router.py
- Three-tier routing: Ollama CUDA → LM Studio Vulkan → GLM cloud API
- VRAM-aware: check nvidia-smi before routing to CUDA
- Auto-downgrade on failure/overload

## P19.4 Write core/inference/model_selector.py
- Port from previous OSMEN: `ssh armad@192.168.7.246 "type c:\\dev\\osmen\\core\\orchestration\\model_selector.py"`
- ModelSelector with tiers, auto-downgrade, GLM config
- Error 1302 handling (rate limit → 2 min backoff)

## P19.5 Write core/knowledge/scraper.py
- Playwright-based web scraping
- Pitfall PF03: --shm-size=2g in container
- Extract text, clean HTML, prepare for chunking

## P19.6 Write core/media/transfer.py
- Plex library integration
- Tautulli webhook processing
- Media file organization (staging → library)

## P19.7 Write core/media/vpn_audit.py
- VPN health checks: IP verification, DNS leak detection, IPv6 leak
- Pitfalls PF04, PF05: automated verification

## P19.8 Write core/notifications/dispatch.py
- Multi-channel dispatcher: Telegram (primary), Discord (secondary)
- Approval notifications for medium+ risk operations
- Pitfall PF19: max 1 reminder per window (no nag loop)

## P19.9 Write core/orchestration/coordinator.py
- Event-driven orchestration
- Port relevant logic from previous OSMEN coordinator_graph.py

## P19.10 Write core/memory/maintenance.py
- Promotion: Redis working → PostgreSQL structured (on access count threshold)
- Decay: PostgreSQL → archive (on age/staleness)
- ChromaDB compaction trigger

## P19.10a Write core/acp/ — Agent Communication Protocol (BeeAI ACP-SDK)
- Install: `.venv/bin/pip install acp-sdk`
- `core/acp/__init__.py`
- `core/acp/server.py` — ACP server exposing OsMEN-OC agents as ACP-addressable services
  - Bind to 127.0.0.1:18101 (first agent), 18102+ for additional agents
  - JSON-over-loopback transport, no external orchestrator
  - Register each agent manifest as an ACP-callable agent
- `core/acp/client.py` — Custom ACP client for agent-to-agent communication
  - Agents send structured requests to peer agents via ACP
  - Supports request/response and fire-and-forget patterns
  - Used by orchestrator to delegate subtasks between agents
- `core/acp/bridge.py` — Bridge between ACP and OsMEN-OC event bus
  - ACP messages emit EventEnvelope on Redis Streams
  - EventBus events can trigger ACP calls to other agents
  - Taskwarrior bridge: agents create/query tasks via ACP → Taskwarrior hook
- `core/acp/obsidian.py` — Obsidian ACP bridge
  - Read/write Obsidian vault notes via Local REST API (127.0.0.1:27124)
  - Agents use this to store research, daily briefs, knowledge artifacts in Obsidian
- Config: `config/acp.yaml` — agent addresses, transport settings, bridge mappings
- Tests: `tests/test_acp.py` — server, client, bridge, Obsidian round-trip

## P19.10b Write core/credentials/broker.py — System-wide credential broker
- `core/credentials/__init__.py`
- `core/credentials/broker.py` — Unified credential access for all OsMEN-OC components
  - Reads from: SOPS-encrypted YAML → Podman secrets → GNOME keyring (fallback)
  - Provides: `get_credential(name) → str` with caching and audit logging
  - All credential access flows through this broker — no direct env reads in business logic
  - Logs credential access (name only, never values) to audit trail
- `core/credentials/rotate.py` — Scheduled credential rotation triggers
  - Auto-regenerate DB passwords, API keys on configurable schedule
  - Emit event on rotation for dependent services to refresh
- Config: `config/credentials.yaml` — credential names, sources, rotation policy
- Tests: `tests/test_credentials.py`

## P19.10c Write core/pipelines/circuit_breaker.py — Circuit breaker for pipeline steps
- `core/pipelines/circuit_breaker.py`
  - States: closed (normal) → open (failing, skip calls) → half-open (probe)
  - Configurable failure threshold, recovery timeout, probe interval
  - Per-step breaker state stored in Redis (survives restarts)
  - Integrates with existing retry logic in runner.py
- Config: add `circuit_breaker:` section to `config/pipelines.yaml`
  - Per-step override: `circuit_breaker: {threshold: 5, timeout_seconds: 300}`
- Tests: `tests/test_circuit_breaker.py`

## P19.10d Add hypothesis property-based tests
- Install: `.venv/bin/pip install hypothesis`
- `tests/test_properties.py`:
  - EventEnvelope: round-trip serialization for arbitrary payloads
  - Bridge protocol: fuzz message parsing with valid/invalid JSON
  - Chunking: sentence-safe splitting never produces empty chunks
  - Config loader: arbitrary YAML with ${ENV_VAR} interpolation
- These complement the existing contract tests in test_contracts.py

## P19.10e Write core/gateway/metrics.py — Code-level observability
- `core/gateway/metrics.py`
  - Expose `/metrics` endpoint (Prometheus format)
  - Instrument: EventBus publish/consume latency, ApprovalGate decision counts,
    PipelineRunner step duration, inference router selection counts
  - Use `prometheus_client` library (lightweight, no OTel dependency yet)
  - Install: `.venv/bin/pip install prometheus-client`
- Wire into `app.py` lifespan
- Config: `config/metrics.yaml` — enable/disable, port, prefix
- Tests: `tests/test_metrics.py`

## P19.11 Write core/memory/embeddings.py (if not done in P14)
- Verify embeddings module is complete and tested

## P19.12 Write additional agent runners
- Ensure all 8 agents have functional Python runners, not just YAML manifests
- daily_brief, knowledge_librarian, media_organization, boot_hardening,
  focus_guardrails, taskwarrior_sync, system_monitor, research

## P19.13 Write missing config files
- `config/llm/providers.yaml` — LLM provider config (Ollama, LM Studio, GLM)
- `config/media/ingestion.yaml` — Media ingestion rules
- `config/media/library.yaml` — Library paths and naming
- `config/services.yaml` — Service registry with ports and health URLs
- `config/backup.yaml` — Backup targets and schedules
- `config/notifications.yaml` — Channel config and priority routing
- `config/checkin.yaml` — Daily brief schedule and content
- `config/taskwarrior.yaml` — UDA definitions, sync rules
- `config/thermal.yaml` — Fan profiles, temp thresholds

## P19.14 Write tests for all new modules
- One test file per module minimum
- Use pytest + pytest-anyio
- Real assertions, not stubs

## P19.15 Run full test suite
- Command: `make check` (test + lint + typecheck)
- ALL must pass

## P19.16 Commit all core modules
- Stage and commit in logical units

### PAUSE POINT 19 — Execution engine fully implemented

# ═══════════════════════════════════════════════════════════════════════
# PHASE 20: Gaming (Steam + FFXIV)
# Prereq: Phase 1 (GPU drivers) | Output: FFXIV running on NVIDIA
# Steps: 6 (P20.1–P20.6)
# ═══════════════════════════════════════════════════════════════════════

## P20.1 Install Steam [USER ACTION]
- Options: `pkexec apt-get install -y steam` or Flatpak
- May require multilib/i386 packages

## P20.2 Enable Proton compatibility
- Steam → Settings → Compatibility → Enable Steam Play for all titles

## P20.3 Install XIVLauncher
- Options: Flatpak (`flatpak install dev.goats.xivlauncher`) or manual install
- Configure: Wine prefix, game path

## P20.4 Verify FFXIV runs on NVIDIA
- Launch FFXIV → check `nvidia-smi` → ffxiv_dx11.exe should appear
- Expected: ~700-800 MiB VRAM idle, up to 2-3 GB in heavy scenes

## P20.5 Test GPU conflict rule
- Run FFXIV + Ollama inference simultaneously
- Verify: Ollama respects remaining VRAM
- Pitfall PF11: When FFXIV active → large inference should route to AMD Vulkan or CPU

## P20.6 Document GPU routing in config
- Update config/compute-routing.yaml with verified conflict rules

### PAUSE POINT 20 — Gaming operational

# ═══════════════════════════════════════════════════════════════════════
# PHASE 21: Monitoring (Prometheus + Grafana — opt-in)
# Prereq: Phase 7 | Output: Observability stack ready (not auto-started)
# Steps: 6 (P21.1–P21.6)
# ═══════════════════════════════════════════════════════════════════════

## P21.1 Write osmen-monitoring-prometheus.container quadlet
- Disabled by default (not auto-started)
- Port: 9090 (must not conflict with qBit — use different binding or only start when needed)
- Scrape config for all OsMEN services

## P21.2 Write osmen-monitoring-grafana.container quadlet
- Disabled by default
- Port: 3000 (via Caddy: grafana.osmen.local)

## P21.3 Write Prometheus scrape config
- `config/prometheus.yml` — targets for all services with metrics endpoints

## P21.4 Write Grafana dashboards
- Pre-configured dashboards for: system resources, Podman containers, inference stats, media pipeline

## P21.5 Test: start both, verify metrics
- Command: `systemctl --user start osmen-monitoring-{prometheus,grafana}`
- Verify: Grafana at http://grafana.osmen.local shows data
- Then stop: `systemctl --user stop osmen-monitoring-{prometheus,grafana}`

## P21.6 Commit monitoring quadlets + config
- Stage and commit (units disabled by default)

### PAUSE POINT 21 — Monitoring ready, not auto-started

# ═══════════════════════════════════════════════════════════════════════
# PHASE 22: Final Verification + Pitfall Audit + PR
# Prereq: All phases complete | Output: PR-ready branch, all systems verified
# Steps: 20 (P22.1–P22.20)
# ═══════════════════════════════════════════════════════════════════════

## P22.1 Full test suite
- Command: `make check` (test + lint + typecheck)
- ALL must pass with 0 failures

## P22.2 System services audit
- Command: `podman ps --format "table {{.Names}}\t{{.Status}}"`
- Expected: All containers running and healthy

## P22.3 PostgreSQL verification
- `podman exec osmen-core-postgres psql -U osmen -d osmen -c "SELECT version();"`
- `podman exec osmen-core-postgres psql -U osmen -d osmen -c '\dt'`

## P22.4 Redis verification
- `podman exec osmen-core-redis redis-cli ping` → PONG

## P22.5 ChromaDB verification
- `curl -sf http://127.0.0.1:8000/api/v1/heartbeat`

## P22.6 Gateway health
- `curl -sf http://127.0.0.1:8080/health`

## P22.6a Gateway /ready (dependency health matrix)
- `curl -sf http://127.0.0.1:8080/ready` → JSON with postgres, redis, chromadb status
- ALL dependencies must show `"ok": true`

## P22.6b Dead-letter endpoint
- `curl -sf http://127.0.0.1:8080/events/dead-letter` → returns dead-letter queue contents
- Must respond 200 even if empty

## P22.6c /metrics endpoint (Prometheus)
- `curl -sf http://127.0.0.1:8080/metrics` → Prometheus text format
- Must include: eventbus_*, approval_*, pipeline_* metric families

## P22.7 MCP tools count
- `curl -sf http://127.0.0.1:8080/mcp/tools | python3.13 -c "import sys,json; print(len(json.load(sys.stdin)))"`
- Expected: 32+ tools

## P22.8 Ollama models
- `curl -sf http://127.0.0.1:11434/api/tags`
- Expected: nomic-embed-text, llama3.2:3b

## P22.9 VPN IP check
- `podman exec osmen-media-gluetun curl -s ifconfig.me`
- Must show VPN IP

## P22.10 DNS leak check
- `podman exec osmen-media-gluetun cat /etc/resolv.conf`
- Must NOT show ISP DNS

## P22.11 All arr services health
- Prowlarr (9696), Sonarr (8989), Radarr (7878), Bazarr (6767) — all responding

## P22.12 Plex accessible
- `curl -sf http://127.0.0.1:32400/web` → Plex UI loads

## P22.13 SiYuan accessible
- `curl -sf http://127.0.0.1:6806` → SiYuan responds

## P22.13a Obsidian API accessible
- `curl -sf http://127.0.0.1:27124` → Obsidian Local REST API responds
- Requires Obsidian running with Local REST API plugin enabled

## P22.13b Langflow accessible
- `curl -sf http://127.0.0.1:7860/health` → Langflow health check

## P22.13c Kavita accessible
- `curl -sf http://127.0.0.1:5000` → Kavita responds

## P22.13d Audiobookshelf accessible
- `curl -sf http://127.0.0.1:13378` → Audiobookshelf responds

## P22.14 Nextcloud accessible
- Verify Nextcloud responds through Caddy reverse proxy

## P22.15 Caddy reverse proxy
- Test: `curl -sf http://plex.osmen.local` → proxied to Plex

## P22.16 Uptime Kuma monitors
- `curl -sf http://127.0.0.1:3001` → all monitors green

## P22.17 Tailscale mesh
- `tailscale status` → connected, reachable from other devices

## P22.18 Pitfall audit (PF01–PF20)
- Verify EVERY pitfall in the registry:
  - PF01: `lsmod | grep nvidia_drm` ✓
  - PF02: `lsmod | grep amdxdna` ✓ (or documented as experimental)
  - PF04: DNS in gluetun → no ISP ✓
  - PF05: IPv6 curl fails in gluetun ✓
  - PF06: No VPN creds in git ✓
  - PF07: VPN auto-starts after reboot ✓
  - PF12: MemoryMax set in inference slice ✓
  - PF13: Nextcloud UID mapping correct ✓
  - PF15: Tailscale doesn't capture gluetun traffic ✓
  - PF16: Backup script pg_dumps before restic ✓
  - PF17: age key backed up ✓
  - PF18: task add doesn't block when Redis down ✓
  - PF20: Only TLP or power-profiles-daemon active ✓

## P22.18a Codebase hardening verification (already implemented — confirm still working)
- CI security: `grep -q bandit .github/workflows/ci.yml` → present
- CI pip-audit: `grep -q pip-audit .github/workflows/ci.yml` → present
- CI coverage gate: `grep -q cov-fail-under .github/workflows/ci.yml` → 80%
- CI quadlet validation: `grep -q quadlet .github/workflows/ci.yml` → present
- Async ChromaDB: `grep -q add_documents_async core/memory/store.py` → present
- SSRF hardening: `grep -q _validate_ingest_url core/gateway/builtin_handlers.py` → present
- Contract tests: `python -m pytest tests/test_contracts.py -v` → all pass
- Dead-letter replay: `grep -q read_dead_letters core/events/bus.py` → present
- Handler error→500: `grep -q 500 core/gateway/app.py` → error mapping present
- Pipeline retries: `grep -q backoff core/pipelines/runner.py` → exponential backoff present
- Cronsim parsing: `grep -q cronsim core/pipelines/runner.py` → present
- Makefile DX: `make -n check` → target exists (test + lint + typecheck)

## P22.18b ACP verification
- ACP server responds: `curl -sf http://127.0.0.1:18101/health` → ACP agent alive
- Agent-to-agent call: test script sends ACP request → receives response
- EventBus bridge: ACP message → Redis Stream event → verify with `redis-cli XLEN`
- Obsidian bridge: ACP → Obsidian REST API round-trip test

## P22.18c Credential broker verification
- `python -c "from core.credentials.broker import get_credential; print(get_credential('osmen-postgres-password') is not None)"`
  → True (credential resolved without direct env access)
- Audit log: verify credential access logged (name only, no values)

## P22.19 Final commit
- Stage all remaining changes
- Command: `git add -A && git commit -m "feat: first install complete — all systems operational"`
- Verify: `git log --oneline` shows logical commit history

## P22.20 Push branch + create PR [SHARED SYSTEM]
- Command: `git push -u origin install/fresh-setup-20260407`
- Create PR against main (via gh CLI or GitHub web)
- PR description: summarize all 22 phases, services running, pitfall audit results

### ═══ INSTALL COMPLETE ═══════════════════════════════════════════════
