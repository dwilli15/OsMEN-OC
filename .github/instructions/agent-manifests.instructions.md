---
applyTo: "agents/**/*.yaml"
---

## Agent Manifest Conventions

Each file in `agents/` defines one agent. The gateway scans these at startup to auto-register MCP tools.

### Required Schema

```yaml
agent_id: <unique_snake_case>
name: <Human Readable Name>
model_tier: <cloud-primary|local-medium|local-small|haiku>
capabilities: [<list of capability strings>]
description: <one-line description>
tools:
  - name: <tool_name>
    description: <what the tool does>
    parameters:
      <param_name>:
        type: <string|integer|boolean|array>
        required: <true|false>
        description: <param description>
        enum: [<optional allowed values>]
    risk_level: <low|medium|high|critical>
```

### Risk Levels

- `low`: Auto-execute + log (read-only operations, health checks)
- `medium`: Execute + log + include in daily summary (writes, transfers)
- `high`: Queue for human approval via Telegram notification (deletions, config changes)
- `critical`: BLOCK until human confirms via Telegram + Discord (security operations, destructive actions)

### Agents to Create

1. `daily_brief.yaml` — Daily briefing generation (model_tier: cloud-primary)
2. `knowledge_librarian.yaml` — Knowledge ingest, scraping, transcription (model_tier: cloud-primary)
3. `media_steward.yaml` — Media transfer, library health, VPN audit (model_tier: local-medium)
4. `system_monitor.yaml` — Hardware monitoring, thermal, storage (model_tier: local-small)
5. `focus_guard.yaml` — ADHD tracking, productivity (model_tier: cloud-primary)
6. `research.yaml` — Web research, RAG queries (model_tier: cloud-primary)
