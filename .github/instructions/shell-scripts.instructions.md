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

1. Install apt packages: python3-dev python3-venv podman podman-compose taskwarrior lm-sensors smartmontools restic age ffmpeg git curl
2. Create Python venv + `pip install -e .[dev]`
3. Verify Podman rootless (subuid/subgid), enable podman.socket
4. Deploy quadlets + timers (via `scripts/deploy_quadlets.sh`)
5. Check for age key → deploy SOPS secrets if present
6. Start core services (PG, Redis, ChromaDB), wait for healthy
7. Run SQL migrations
8. Verify with `podman ps`

### Deploy Script

`scripts/deploy_quadlets.sh` symlinks all files from `quadlets/` into `~/.config/containers/systemd/` and runs `systemctl --user daemon-reload`.
