---
applyTo: "scripts/**/*.sh"
---

## Shell Script Conventions

- Shebang: `#!/usr/bin/env bash`
- `set -euo pipefail` at top of every script
- Functions for reusable logic
- `log_info()`, `log_warn()`, `log_error()` helper functions for consistent output
- Check prerequisites before doing work (binary exists, directory writable, service running)
- Idempotent: safe to run multiple times without side effects

### Bootstrap Script Requirements

`scripts/bootstrap.sh` is the master entry point. Must be idempotent. Steps:

1. Install apt packages: python3-dev python3-venv nodejs npm podman podman-compose taskwarrior lm-sensors smartmontools restic age ffmpeg git curl
2. Install OpenClaw: `npm install -g openclaw` (control plane dependency)
3. Create Python venv + `pip install -e .[dev]`
4. Verify Podman rootless (subuid/subgid), enable podman.socket
5. Deploy quadlets + timers (via `scripts/deploy_quadlets.sh`)
6. Check for age key → deploy SOPS secrets if present
7. Start core services (PG, Redis, ChromaDB), wait for healthy
8. Run SQL migrations
9. Verify with `podman ps` + `openclaw --version`

### Deploy Script

`scripts/deploy_quadlets.sh` symlinks all files from `quadlets/` into `~/.config/containers/systemd/` and runs `systemctl --user daemon-reload`.
