---
mode: ask
description: "Complete file map for OsMEN-OC repo — absolute paths to every source, config, quadlet, test, script, and doc file"
---

# OsMEN-OC Complete File Map

Branch: `install/fresh-setup-20260407`
HEAD: `c31a44e`
Tests: 671 passed / 0 failed
Services: 27 running, 1 failed (osmen-memory-maintenance)

---

## Entry Points

```
/home/dwill/dev/OsMEN-OC/pyproject.toml
/home/dwill/dev/OsMEN-OC/Makefile
/home/dwill/dev/OsMEN-OC/AGENTS.md
/home/dwill/dev/OsMEN-OC/README.md
```

---

## Core Python Package (`core/`)

### Top Level
```
/home/dwill/dev/OsMEN-OC/core/__init__.py
/home/dwill/dev/OsMEN-OC/core/Containerfile
/home/dwill/dev/OsMEN-OC/core/PIPELINE_CONNECTIONS.instructions.md
```

### Approval Gate
```
/home/dwill/dev/OsMEN-OC/core/approval/__init__.py
/home/dwill/dev/OsMEN-OC/core/approval/gate.py
```

### Audit Trail
```
/home/dwill/dev/OsMEN-OC/core/audit/__init__.py
/home/dwill/dev/OsMEN-OC/core/audit/trail.py
```

### Bridge (WebSocket to OpenClaw)
```
/home/dwill/dev/OsMEN-OC/core/bridge/__init__.py
/home/dwill/dev/OsMEN-OC/core/bridge/protocol.py
/home/dwill/dev/OsMEN-OC/core/bridge/ws_client.py
```

### Event Bus (Redis Streams)
```
/home/dwill/dev/OsMEN-OC/core/events/__init__.py
/home/dwill/dev/OsMEN-OC/core/events/bus.py
/home/dwill/dev/OsMEN-OC/core/events/envelope.py
```

### Gateway (FastAPI + MCP — port 18788)
```
/home/dwill/dev/OsMEN-OC/core/gateway/__init__.py
/home/dwill/dev/OsMEN-OC/core/gateway/app.py
/home/dwill/dev/OsMEN-OC/core/gateway/builtin_handlers.py
/home/dwill/dev/OsMEN-OC/core/gateway/deps.py
/home/dwill/dev/OsMEN-OC/core/gateway/handlers.py
/home/dwill/dev/OsMEN-OC/core/gateway/mcp.py
```

### Knowledge / Ingest
```
/home/dwill/dev/OsMEN-OC/core/knowledge/__init__.py
/home/dwill/dev/OsMEN-OC/core/knowledge/ingest.py
```

### Memory (Redis → Postgres+pgvector → ChromaDB)
```
/home/dwill/dev/OsMEN-OC/core/memory/__init__.py
/home/dwill/dev/OsMEN-OC/core/memory/chunking.py
/home/dwill/dev/OsMEN-OC/core/memory/embeddings.py
/home/dwill/dev/OsMEN-OC/core/memory/hub.py
/home/dwill/dev/OsMEN-OC/core/memory/lateral.py
/home/dwill/dev/OsMEN-OC/core/memory/store.py
```

### Orchestration — DOES NOT EXIST YET (P19 primary lane)
```
/home/dwill/dev/OsMEN-OC/core/orchestration/   ← NOT CREATED — P19 builds this
```

### Pipelines
```
/home/dwill/dev/OsMEN-OC/core/pipelines/__init__.py
/home/dwill/dev/OsMEN-OC/core/pipelines/runner.py
```

### Secrets
```
/home/dwill/dev/OsMEN-OC/core/secrets/__init__.py
/home/dwill/dev/OsMEN-OC/core/secrets/audit_checks.py
/home/dwill/dev/OsMEN-OC/core/secrets/cli.py
/home/dwill/dev/OsMEN-OC/core/secrets/custodian.py
```

### Setup Wizard
```
/home/dwill/dev/OsMEN-OC/core/setup/__init__.py
/home/dwill/dev/OsMEN-OC/core/setup/__main__.py
/home/dwill/dev/OsMEN-OC/core/setup/wizard.py
```

### Taskwarrior Integration
```
/home/dwill/dev/OsMEN-OC/core/tasks/__init__.py
/home/dwill/dev/OsMEN-OC/core/tasks/queue.py
/home/dwill/dev/OsMEN-OC/core/tasks/sync.py
```

### Utils
```
/home/dwill/dev/OsMEN-OC/core/utils/__init__.py
/home/dwill/dev/OsMEN-OC/core/utils/config.py
/home/dwill/dev/OsMEN-OC/core/utils/exceptions.py
```

### Vision (VisionClient + ImageGenClient)
```
/home/dwill/dev/OsMEN-OC/core/vision/__init__.py
/home/dwill/dev/OsMEN-OC/core/vision/client.py
/home/dwill/dev/OsMEN-OC/core/vision/image_gen.py
```

### Voice (STT / TTS)
```
/home/dwill/dev/OsMEN-OC/core/voice/__init__.py
/home/dwill/dev/OsMEN-OC/core/voice/stt.py
/home/dwill/dev/OsMEN-OC/core/voice/tts.py
```

---

## Agent Manifests (`agents/`)

```
/home/dwill/dev/OsMEN-OC/agents/boot_hardening.yaml
/home/dwill/dev/OsMEN-OC/agents/daily_brief.yaml
/home/dwill/dev/OsMEN-OC/agents/focus_guardrails.yaml
/home/dwill/dev/OsMEN-OC/agents/knowledge_librarian.yaml
/home/dwill/dev/OsMEN-OC/agents/media_organization.yaml
/home/dwill/dev/OsMEN-OC/agents/research.yaml
/home/dwill/dev/OsMEN-OC/agents/secrets_custodian.yaml
/home/dwill/dev/OsMEN-OC/agents/system_monitor.yaml
/home/dwill/dev/OsMEN-OC/agents/taskwarrior_sync.yaml
/home/dwill/dev/OsMEN-OC/agents/vision_tools.yaml
```

---

## Config (`config/`)

```
/home/dwill/dev/OsMEN-OC/config/agents.yaml
/home/dwill/dev/OsMEN-OC/config/compute-routing.yaml
/home/dwill/dev/OsMEN-OC/config/hardware.yaml
/home/dwill/dev/OsMEN-OC/config/openclaw.yaml
/home/dwill/dev/OsMEN-OC/config/pipelines.yaml
/home/dwill/dev/OsMEN-OC/config/prometheus.yml
/home/dwill/dev/OsMEN-OC/config/secrets-registry.yaml
/home/dwill/dev/OsMEN-OC/config/PIPELINE_CONNECTIONS.instructions.md
/home/dwill/dev/OsMEN-OC/config/voice/stt.yaml
/home/dwill/dev/OsMEN-OC/config/voice/tts.yaml
```

### Secret Templates (commit-safe; real secrets at ~/.config/osmen/secrets/)
```
/home/dwill/dev/OsMEN-OC/config/secrets/api-keys.template.yaml
/home/dwill/dev/OsMEN-OC/config/secrets/gh-token.template.yaml
/home/dwill/dev/OsMEN-OC/config/secrets/oauth-tokens.template.yaml
```

---

## Quadlets (Rootless Podman Systemd Units)

### Core Stack
```
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core.network
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core-caddy.container
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core-chromadb.container
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core-gateway.container
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core-langflow.container
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core-nextcloud.container
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core-postgres.container
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core-redis.container
/home/dwill/dev/OsMEN-OC/quadlets/core/osmen-core-siyuan.container
```

### Inference
```
/home/dwill/dev/OsMEN-OC/quadlets/inference/osmen-inference-lmstudio.service
```

### Librarian Stack
```
/home/dwill/dev/OsMEN-OC/quadlets/librarian/osmen-librarian-audiobookshelf.container
/home/dwill/dev/OsMEN-OC/quadlets/librarian/osmen-librarian-convertx.container
/home/dwill/dev/OsMEN-OC/quadlets/librarian/osmen-librarian-kavita.container
/home/dwill/dev/OsMEN-OC/quadlets/librarian/osmen-librarian-whisper.container
```

### Media Stack
```
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media.network
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-bazarr.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-gluetun.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-kometa.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-lidarr.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-mylar3.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-plex.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-prowlarr.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-qbittorrent.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-radarr.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-readarr.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-sabnzbd.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-sonarr.container
/home/dwill/dev/OsMEN-OC/quadlets/media/osmen-media-tautulli.container
```

### Monitoring Stack
```
/home/dwill/dev/OsMEN-OC/quadlets/monitoring/osmen-monitoring-grafana.container
/home/dwill/dev/OsMEN-OC/quadlets/monitoring/osmen-monitoring-portall.container
/home/dwill/dev/OsMEN-OC/quadlets/monitoring/osmen-monitoring-prometheus.container
/home/dwill/dev/OsMEN-OC/quadlets/monitoring/osmen-monitoring-uptimekuma.container
```

### Deployed System Units (live, ~/.config/containers/systemd/)
```
~/.config/containers/systemd/   ← symlinked/copied from quadlets/ by deploy_quadlets.sh
```

---

## Timers (`timers/`)

```
/home/dwill/dev/OsMEN-OC/timers/osmen-chromadb-compact.service
/home/dwill/dev/OsMEN-OC/timers/osmen-chromadb-compact.timer
/home/dwill/dev/OsMEN-OC/timers/osmen-db-backup.service
/home/dwill/dev/OsMEN-OC/timers/osmen-db-backup.timer
/home/dwill/dev/OsMEN-OC/timers/osmen-db-vacuum.service
/home/dwill/dev/OsMEN-OC/timers/osmen-db-vacuum.timer
/home/dwill/dev/OsMEN-OC/timers/osmen-health-report.service
/home/dwill/dev/OsMEN-OC/timers/osmen-health-report.timer
/home/dwill/dev/OsMEN-OC/timers/osmen-memory-maintenance.service   ← FAILED — needs fix
/home/dwill/dev/OsMEN-OC/timers/osmen-memory-maintenance.timer
/home/dwill/dev/OsMEN-OC/timers/osmen-npu-autoload.service
/home/dwill/dev/OsMEN-OC/timers/osmen-secrets-audit.service
/home/dwill/dev/OsMEN-OC/timers/osmen-secrets-audit.timer
/home/dwill/dev/OsMEN-OC/timers/osmen-smart-check.service
/home/dwill/dev/OsMEN-OC/timers/osmen-smart-check.timer
/home/dwill/dev/OsMEN-OC/timers/osmen-vpn-audit.service
/home/dwill/dev/OsMEN-OC/timers/osmen-vpn-audit.timer
```

---

## Scripts (`scripts/`)

```
/home/dwill/dev/OsMEN-OC/scripts/bootstrap.sh
/home/dwill/dev/OsMEN-OC/scripts/deploy_quadlets.sh
/home/dwill/dev/OsMEN-OC/scripts/deploy_timers.sh
/home/dwill/dev/OsMEN-OC/scripts/backup.sh
/home/dwill/dev/OsMEN-OC/scripts/lemonade-autoload.sh
/home/dwill/dev/OsMEN-OC/scripts/secrets/export_credential_kit.sh
/home/dwill/dev/OsMEN-OC/scripts/appdrawer/start-claude-osmen.sh
/home/dwill/dev/OsMEN-OC/scripts/appdrawer/start-osmen-tmux.sh
/home/dwill/dev/OsMEN-OC/scripts/taskwarrior/on-add-osmen.py
/home/dwill/dev/OsMEN-OC/scripts/taskwarrior/on-modify-osmen.py
```

---

## Tests (`tests/`)

```
/home/dwill/dev/OsMEN-OC/tests/conftest.py
/home/dwill/dev/OsMEN-OC/tests/test_agent_manifests.py
/home/dwill/dev/OsMEN-OC/tests/test_approval.py
/home/dwill/dev/OsMEN-OC/tests/test_audit.py
/home/dwill/dev/OsMEN-OC/tests/test_bridge.py
/home/dwill/dev/OsMEN-OC/tests/test_contracts.py
/home/dwill/dev/OsMEN-OC/tests/test_core.py
/home/dwill/dev/OsMEN-OC/tests/test_events.py
/home/dwill/dev/OsMEN-OC/tests/test_gateway.py
/home/dwill/dev/OsMEN-OC/tests/test_handlers.py
/home/dwill/dev/OsMEN-OC/tests/test_hub.py
/home/dwill/dev/OsMEN-OC/tests/test_ingest.py
/home/dwill/dev/OsMEN-OC/tests/test_memory.py
/home/dwill/dev/OsMEN-OC/tests/test_pipelines.py
/home/dwill/dev/OsMEN-OC/tests/test_quadlets.py
/home/dwill/dev/OsMEN-OC/tests/test_secrets_custodian.py
/home/dwill/dev/OsMEN-OC/tests/test_setup.py
/home/dwill/dev/OsMEN-OC/tests/test_smoke.py
/home/dwill/dev/OsMEN-OC/tests/test_system_monitor.py
/home/dwill/dev/OsMEN-OC/tests/test_tasks.py
/home/dwill/dev/OsMEN-OC/tests/test_timers.py
/home/dwill/dev/OsMEN-OC/tests/test_vision.py
/home/dwill/dev/OsMEN-OC/tests/test_voice.py
/home/dwill/dev/OsMEN-OC/tests/test_ws_bridge.py
```

---

## Migrations (`migrations/`)

```
/home/dwill/dev/OsMEN-OC/migrations/001_initial_schema.sql
/home/dwill/dev/OsMEN-OC/migrations/002_unified_memory.sql
```

---

## Resume / Handoff Docs

```
/home/dwill/dev/OsMEN-OC/docs/session-logs/RESUME.md                             ← root dispatcher
/home/dwill/dev/OsMEN-OC/docs/session-logs/RESUME.osmen.install.p19.md           ← primary lane (P19)
/home/dwill/dev/OsMEN-OC/docs/session-logs/RESUME.osmen.install.p17.md           ← supporting lane (P17)
/home/dwill/dev/OsMEN-OC/docs/session-logs/RESUME.osmen.media.md                 ← media lane
/home/dwill/dev/OsMEN-OC/docs/session-logs/RESUME.osmen.audit.md                 ← audit lane
/home/dwill/dev/OsMEN-OC/docs/session-logs/2026-04-16/2026-04-16_handoff.md      ← LATEST handoff
/home/dwill/dev/OsMEN-OC/docs/session-logs/2026-04-14/2026-04-14_235950_handoff.md
/home/dwill/dev/OsMEN-OC/docs/session-logs/2026-04-14/2026-04-14_234500_handoff.md
```

---

## Memory Bank (`.opencode/memory-bank/`)

```
/home/dwill/dev/OsMEN-OC/.opencode/memory-bank/projectbrief.md
/home/dwill/dev/OsMEN-OC/.opencode/memory-bank/productContext.md
/home/dwill/dev/OsMEN-OC/.opencode/memory-bank/activeContext.md     ← current state
/home/dwill/dev/OsMEN-OC/.opencode/memory-bank/systemPatterns.md
/home/dwill/dev/OsMEN-OC/.opencode/memory-bank/techContext.md
/home/dwill/dev/OsMEN-OC/.opencode/memory-bank/progress.md          ← phase table
```

---

## GitHub Instructions / Copilot Context

```
/home/dwill/dev/OsMEN-OC/.github/copilot-instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/agent-manifests.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/config-files.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/install-audit.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/python-code.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/python-security-guidelines.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/python-test-guidelines.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/quadlet-files.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/secrets-lifecycle.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/shell-scripts.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/test-files.instructions.md
/home/dwill/dev/OsMEN-OC/.github/instructions/update-activity-workflow.instructions.md
/home/dwill/dev/OsMEN-OC/.github/workflows/ci.yml
```

---

## Install / Audit Artifacts

```
/home/dwill/dev/OsMEN-OC/temp_1st_install/INSTALL_PLAN.md
/home/dwill/dev/OsMEN-OC/temp_1st_install/install.log
/home/dwill/dev/OsMEN-OC/temp_1st_install/RECONCILIATION_LEDGER.md
/home/dwill/dev/OsMEN-OC/temp_1st_install/load_tasks.sh
/home/dwill/dev/OsMEN-OC/vault/logs/                                ← audit session logs
/home/dwill/dev/OsMEN-OC/vault/memory/                              ← cross-session insights
```

---

## Live Service Ports (Quick Reference)

| Service | Port | Notes |
|---------|------|-------|
| Gateway (MCP) | `127.0.0.1:18788` | 42 MCP tools, 10 agent manifests |
| OpenClaw bridge | `127.0.0.1:18789` | WebSocket ingress from OpenClaw |
| Lemonade (LLM) | `127.0.0.1:13305` | Local model API |
| Ollama | `127.0.0.1:11434` | Local model API |
| Redis | `127.0.0.1:6379` | Event bus + working memory |
| PostgreSQL | `127.0.0.1:5432` | Structured memory + pgvector |
| ChromaDB | `127.0.0.1:8001` | RAG vector store |
| Caddy | `127.0.0.1:443/80` | Reverse proxy → *.osmen.local |
| Nextcloud | via Caddy | `nextcloud.osmen.local` |
| SiYuan PKM | via Caddy | `siyuan.osmen.local` |
| Portall | via Caddy | `portall.osmen.local` |
| Grafana | via Caddy | `grafana.osmen.local` |
| Plex | `127.0.0.1:32400` | Native `.deb` install, not container |

---

## Quick Verification Commands

```bash
cd /home/dwill/dev/OsMEN-OC
source .venv/bin/activate

# Tests
python3.13 -m pytest tests/ -q --timeout=15

# Services
systemctl --user list-units 'osmen-*' --plain | grep -E 'running|failed'

# TW overview
task project:osmen.install summary

# Gateway
curl -s http://127.0.0.1:18788/health | python3 -m json.tool
curl -s http://127.0.0.1:18788/mcp/tools | python3 -c "import json,sys; t=json.load(sys.stdin); print(len(t),'tools')"

# Lint / type check
ruff check core/ tests/
mypy core/ --ignore-missing-imports
```
