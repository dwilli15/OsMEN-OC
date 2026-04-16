# osmen-inference-providers.md
# Reference: Non-containerized inference providers managed outside Podman.
# These run as native processes or cloud APIs — not quadlet-managed.
#
# Claude Code (Anthropic)
#   Binary: ~/.claude/local/claude
#   Config: ~/.claude/settings.json
#   Model: claude-opus-4-20250514 (primary coding agent)
#   No systemd unit — launched on demand from terminal/VS Code
#
# OpenCode
#   Binary: ~/.local/bin/opencode
#   Config: ~/.opencode/config.json
#   Providers: GLM (ZhipuAI), Ollama (local), LM Studio (local)
#   No systemd unit — launched on demand
#
# GLM / ZhipuAI Cloud API
#   Base URL: https://api.z.ai/api/coding/paas/v4
#   Auth: ZAI_API_KEY env var (via SOPS-encrypted config)
#   Models: glm-5-turbo (primary), glm-4-flash (fallback)
#   Error 1302 = rate limit → 2 min backoff → auto-downgrade
#
# OpenClaw
#   Runtime: Node.js systemd user service (openclaw.service)
#   Config: ~/.openclaw/openclaw.json
#   Channels: Telegram + Discord
#   Gateway: ws://127.0.0.1:18789
#   Status: RUNNING (pre-installed, verified P10 partial)
