# RECON-08: OpenClaw + Gateway + Channels Truth

**Date:** 2026-04-18 03:25 CDT  
**Agent:** auditor (subagent)

---

## Gateway Status

| Item | Value |
|------|-------|
| Version | OpenClaw 2026.4.15 (041266a) |
| Node.js | v24.14.1 |
| Install method | npm global (`/home/linuxbrew/.linuxbrew/lib`) |
| Gateway mode | local, loopback, port 18789 |
| Gateway service | systemd — installed, enabled, running (pid 7093) |
| Node service | systemd — **not installed** |
| Tailscale | off |
| Update channel | stable |
| Update status | up to date (npm latest 2026.4.15) |
| Dashboard | http://127.0.0.1:18789/ |
| Hostname | Ubu-OsMEN (192.168.4.21) |
| OS | linux 7.0.0-14-generic (x64) |
| Memory | 25 files, 202 chunks, vector ready, FTS ready, cache on (267) |
| Sessions | 334 active, 5 stores |
| Tasks | 19 active, 94 issues, 3 audit errors, 103 warn, 573 tracked |

---

## Channel Health Matrix

| Channel | Enabled | Config Token | State | Health Probe | Latency | Bot Identity |
|---------|---------|-------------|-------|-------------|---------|-------------|
| Discord | ✅ ON | MTQ4…VEus (len 72) | OK | OK | 471ms | @jarvis:default |
| Telegram | ✅ ON | 8734…Daxs (len 46) | OK | OK | 199ms | @OsMEN_OC_bot:default |
| Signal | ❌ | — | — | — | — | — |
| WhatsApp | ❌ | — | — | — | — | — |
| Slack | ❌ (plugin disabled) | — | — | — | — | — |

### Channel Config Details

**Discord:**
- groupPolicy: **open** (security concern — see below)
- allowBots: true
- intents: guildMembers, presence
- replyToMode: all
- status: invisible
- streaming: progress
- configWrites: true
- dmPolicy: pairing
- slash commands: ephemeral
- autoPresence: enabled
- agentComponents: enabled

**Telegram:**
- groups: `*` → requireMention: true
- dmPolicy: pairing
- allowFrom: `*` (wildcard)
- streaming: progress
- configWrites: true
- native commands + native skills: enabled
- trustedLocalFileRoots: /home

### Security Audit Findings (from `openclaw status --deep`)

**3 CRITICAL:**
1. Open groupPolicy with elevated tools enabled (Discord `groupPolicy="open"`)
2. Open groupPolicy with runtime/filesystem tools exposed
3. Discord security warning — open policy allows any channel to trigger

**3 WARN:**
1. Reverse proxy headers not trusted
2. Some `gateway.nodes.denyCommands` entries are ineffective (using non-exact command names)
3. Potential multi-user setup detected (Telegram `allowFrom="*"`, Discord open)

---

## Agent Definitions

5 agents configured:

| Agent ID | Name | Model | Skills | Tools | Workspace |
|----------|------|-------|--------|-------|-----------|
| main | (default) | zai/glm-5.1 | 32 skills (full suite) | full + browser, canvas, message, gateway, nodes, agents_list, tts | `/home/dwill/dev/OsMEN-OC/openclaw` |
| auditor | Install Auditor | zai/glm-5-turbo | github, taskflow | full + browser | `/home/dwill/dev/OsMEN-OC/openclaw/auditor` |
| researcher | Researcher | zai/glm-5-turbo | github | full + browser | (default) |
| coder | Coder | zai/glm-5-turbo | github, coding-agent, skill-creator | full + browser, canvas | (default) |
| reviewer | Reviewer | zai/glm-5-turbo | github, gh-issues | full + browser | (default) |

### Default Model Config
- Primary: zai/glm-5-turbo (203k ctx)
- Fallbacks: openai-codex/gpt-5.4-mini, ollama/gemma4:latest, ollama/kimi-k2.5:cloud, ollama/minimax-m2.5:cloud
- Subagents: maxSpawnDepth=3, allowAgents=*

### Auth Profiles
- zai:default — api_key
- github-copilot:github — token
- openai-codex:fantasyunravels@gmail.com — oauth
- ollama:default — api_key
- copilot-proxy:local — token (plugin disabled)

### Workspace Bootstrap Files (auditor workspace)
- AGENTS.md: ✅ Populated (dispatch prompt reference)
- SOUL.md: ✅ Populated (methodical/skeptical persona)
- USER.md: ❌ **Not populated** (template only)
- IDENTITY.md: ❌ **Not populated** (template only)

---

## Cron Jobs

1 job defined in `~/.openclaw/cron/jobs.json`:

| ID | Agent | Schedule | Status | Last Run | Notes |
|----|-------|----------|--------|----------|-------|
| heckler-reviewer-300s | reviewer | every 300s (5min) | ✅ ok | 2026-04-18 ~03:20 CDT | Isolated session, light context, 90s timeout, announce to last channel |

---

## npm Global Packages

| Package | Version |
|---------|---------|
| openclaw | 2026.4.15 |
| @anthropic-ai/claude-code | 2.1.104 |
| @steipete/oracle | 0.9.0 |
| @steipete/summarize | 0.13.0 |
| bash-language-server | 5.6.0 |
| clawhub | 0.9.0 |
| corepack | 0.34.6 |
| mcporter | 0.8.1 |
| npm | 11.11.0 |
| opencode-ai | 1.4.11 |
| pyright | 1.1.408 |

---

## ~/.openclaw/ Directory Structure

```
agents/          browser/        canvas/         completions/    credentials/     cron/
delivery-queue/  devices/        exec-approvals.json  flows/      identity/        logs/
media/           memory/         openclaw.json (+ 4 .bak files)  qqbot/           subagents/
tasks/           telegram/       update-check.json
```

**Canvas:** Single `index.html` present (default embed page).  
**Config backups:** 4 `.bak` files, most recent at 2026-04-17 20:14.

---

## Model Provider Summary

| Provider | Base URL | API Type | Models |
|----------|----------|----------|--------|
| zai | api.z.ai | openai-completions | 13 models (glm-5.1 through glm-4.5v) |
| ollama | 127.0.0.1:11434 | ollama | 4 models (gemma4, kimi-k2.5, minimax-m2.5, glm-5 — all cloud-tagged) |
| github-copilot | (default) | (token) | claude-opus-4.6, gpt-5.4 |
| openai-codex | (default) | (oauth) | gpt-5.4-mini (fallback only) |

### Plugins Enabled
ollama, github-copilot, xai, zai, openai, browser, telegram

### Plugins Disabled
copilot-proxy, gemini, gifgrep, peekaboo, sag, 1password, apple-notes, apple-reminders, bear-notes, blucli, camsnap, xurl, wacli, voice-call, trello, things-mac, spotify-player, sonoscli, songsee, slack, ordercli, openai-whisper, notion, imsg, eightctl, bluebubbles, openai-whisper-api, session-logs

---

## Config Completeness Assessment

### ✅ Solid
- Gateway running, systemd-managed, reachable
- Both channels (Discord + Telegram) connected and health-checked
- 5 agents defined with distinct roles
- Cron operational with active reviewer loop
- Memory system active (25 files, 202 chunks, vector + FTS)
- Config version tracked, backups present
- Multiple model providers with fallback chain

### ⚠️ Concerns
- **3 CRITICAL security findings** — Discord open groupPolicy with elevated tools is the top risk
- **Discord `groupPolicy="open"`** allows any guild channel to trigger the bot with elevated tools
- **Telegram `allowFrom="*"`** — no access restriction
- **USER.md and IDENTITY.md not populated** for auditor workspace
- **Many disabled skills/plugins** — may indicate incomplete setup or intentional pruning
- **No Node service** (systemd) — only gateway service installed
- **denyCommands entries ineffective** — non-exact command names
- **Heartbeat** only active for main agent (30m); all others disabled

### ❌ Missing / Gaps
- No Signal, WhatsApp, or other channel integrations
- Canvas only has default index.html (no custom embeds)
- No MCP servers configured (`"mcp": {}`)
