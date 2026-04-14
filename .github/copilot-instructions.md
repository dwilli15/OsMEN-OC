# OsMEN-OC Project Instructions

## Identity

- **Project**: OsMEN-OC (OS Management and Engagement Network — OpenClaw edition)
- **License**: Apache 2.0
- **Runtime**: Python 3.13, Ubuntu 26.04 LTS
- **Containers**: Rootless Podman + systemd Quadlets (NEVER Docker)
- **Legacy name "Jarvis"**: RETIRED — never reference anywhere

## Architecture: Two-Plane Design

| Plane     | Product                              | Runtime     | Owns                                                                     |
| --------- | ------------------------------------ | ----------- | ------------------------------------------------------------------------ |
| Control   | OpenClaw (`npm install -g openclaw`) | Node.js     | Channel ingress, trust policy, session routing, operator interaction     |
| Execution | OsMEN-OC (THIS repo)                 | Python 3.13 | Pipeline execution, tools, bridge logic, memory, Podman services, timers |

Data flow: User → OpenClaw (Telegram/Discord) → WebSocket `ws://127.0.0.1:18789` → OsMEN-OC executes → results back.

**OpenClaw is a dependency installed during bootstrap** (`npm install -g openclaw`). This repo owns the bridge (`core/bridge/`) and config (`config/openclaw.yaml`).

## Critical Rules (violations = reject PR)

1. **No legacy**: Zero references to "Jarvis", Docker Compose, docker-compose.yml, n8n, or Langflow.
2. **Podman only**: ALL containers defined as rootless Podman Quadlet `.container` files. Never `docker run`.
3. **Two-plane boundary**: OpenClaw = user interaction (NOT in this repo). OsMEN-OC = execution engine.
4. **Package structure**: `core/` = installable Python package. `config/` = YAML truth store read at runtime.
5. **MCP auto-registration**: Gateway scans `agents/*.yaml` on startup, registers each tool as MCP endpoint. MUST be implemented, not stubbed.
6. **Approval gate wired**: Every tool invocation passes through `core/approval/gate.py`. No tool executes without risk assessment.
7. **Typed events**: Event bus uses `EventEnvelope` dataclass. Never pass raw `dict` on the bus.
8. **VPN pod architecture**: Download stack = single Podman `.pod`. gluetun + qBittorrent + SABnzbd share gluetun's network namespace.
9. **Sentence-safe chunking**: `core/memory/chunking.py` NEVER splits mid-sentence.
10. **GLM API**: Base URL `https://api.z.ai/api/coding/paas/v4` (Coding API). Error 1302 = rate limit → 2 min backoff → auto-downgrade.
11. **Ubuntu 26.04**: Dracut (not initramfs-tools), sudo-rs (not sudo), chrony (not systemd-timesyncd).
12. **Bootstrap works**: `scripts/bootstrap.sh` must be idempotent and bring the system to operational on a fresh clone.

## Python Conventions

- Python 3.13, type hints on all function signatures, `asyncio` for I/O
- `pathlib.Path` for files, `loguru` for logging, `httpx` for HTTP, `pydantic` for schemas
- Google-style docstrings
- Import order: stdlib → third-party → local
- Tests: `pytest` + `pytest-anyio` (NOT pytest-asyncio). Marker: `@pytest.mark.anyio`
- Config: YAML loaded via `core/utils/config.py` with `${ENV_VAR}` interpolation

## Naming Conventions

- Podman containers: `osmen-{profile}-{service}` (e.g. `osmen-core-postgres`, `osmen-media-sonarr`)
  - **Exception:** Plex runs natively via `.deb` package (`plexmediaserver` systemd service), not in a container.
- Podman networks: `osmen-{profile}.network` (e.g. `osmen-core.network`, `osmen-media.network`)
- Podman slices: `user-osmen-{slice}.slice` (e.g. `user-osmen-inference.slice`)
- Redis stream keys: `events:{domain}:{category}` (e.g. `events:media:download_complete`)
- Redis working memory: `mem:working:{agent}:{key}`
- Config files: lowercase, hyphens, `.yaml` extension
- Python: snake_case modules, PascalCase classes, UPPER_SNAKE constants

## Hardware (verified — hardcode in config/hardware.yaml)

```yaml
cpu: { model: "Ryzen AI 9 365", cores: 12, threads: 24, arch: zen5, npu: xdna2 }
ram: 32GB
gpus:
  nvidia:
    {
      model: "RTX 5070 Laptop",
      vram: 8GB,
      driver: "580+",
      cuda: "13.0",
      role: "cuda-inference, rendering, gaming",
    }
  amd:
    {
      model: "Radeon 780M",
      vram: shared,
      driver: amdgpu,
      role: "display, vulkan-inference",
    }
npu: { model: "XDNA 2", driver: amdxdna, status: experimental, fallback: cpu }
storage:
  nvme0n1: { size: 954GB, label: Windows, policy: DO_NOT_TOUCH }
  nvme1n1:
    {
      size: 932GB,
      label: Linux,
      layout: "1GB EFI + 150GB / + 780GB /home",
      encryption: LUKS,
    }
gpu_conflict_rule: "if ffxiv_dx11 on nvidia → route inference to amd_vulkan or cpu"
```

## What to NEVER Create

- `.env` files (use local SOPS-encrypted YAML under `~/.config/osmen/secrets/`; commit only templates in `config/secrets/`)
- `data/` or `logs/` directories (created at runtime)
- Actual secrets or age private keys
- Docker Compose files
- `requirements.txt` (use `pyproject.toml`)

## Build & Test Commands

```bash
# Bootstrap (first run)
scripts/bootstrap.sh

# Test
python -m pytest tests/ -q --timeout=15

# Lint
ruff check core/ tests/

# Type check
mypy core/ --ignore-missing-imports

# Deploy quadlets
scripts/deploy_quadlets.sh

# Status
make status
```
