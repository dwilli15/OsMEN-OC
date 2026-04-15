# Tech Context

## Hardware

Ryzen AI 9 365 (10C/20T) / 64 GB DDR5 / Radeon 880M iGPU (Vulkan) / RTX 5070 8GB (CUDA) / XDNA2 NPU

## Inference Providers

| Provider  | Endpoint | Compute        | Models                                                               |
| --------- | -------- | -------------- | -------------------------------------------------------------------- |
| Ollama    | :11434   | CUDA           | gemma4, llama3.2:3b, qwen3.5:2b, nomic-embed-text                    |
| LM Studio | :1234    | Vulkan         | glm-4.7-flash, gemma-4-26b, lfm2 variants                            |
| Lemonade  | :13305   | Vulkan+NPU+CPU | Qwen3-Coder-30B, Qwen3.5-4B, kokoro-v1, whisper-v3-turbo, qwen3-0.6b |
| ZAI Cloud | api.z.ai | Cloud          | GLM 5.1, GLM 4.7, GLM 4.7flashx                                      |

## Control Plane

- OpenClaw v2026.4.12 on port 18789 (systemd service)
- 19 models, 29 skills configured
- Agent workspace: `openclaw/`

## Tooling

- Wave Terminal: 5 local models, ZAI GLM 5.1 default, tools working
- Claude Code MCP bridge: `~/.local/share/claude-bridge/server.mjs`
- OpenCode: `~/.config/opencode/opencode.json`

## Secrets

- `~/.config/osmen/env` — runtime tokens (DO NOT COMMIT)
- `~/.config/osmen/secrets/` — local backups
- Wave secrets store broken — API keys inline in `waveai.json`

## Known Issues

- Wave secrets store: encryption mismatch between wsh and Electron
- `core/memory/store.py` L72, L94: type annotation violations
- `core/pipelines/runner.py` L448: None attribute access
- FLM GA runtime is Windows-focused — use Lemonade `flm` recipe on Ubuntu
