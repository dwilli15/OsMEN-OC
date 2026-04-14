# Tech Context

## Hardware

- AMD Ryzen AI 9 365 (10C/20T)
- 64 GB DDR5 RAM
- AMD Radeon 880M iGPU (Vulkan)
- NVIDIA RTX 5070 8 GB (CUDA)
- AMD XDNA2 NPU (~50 TOPS class)

## OS & Runtime

- Ubuntu 26.04 LTS
- Python 3.13 (not 3.14 — the memory bank was wrong before)
- Rootless Podman 5.7, systemd user Quadlets
- Redis Streams for event bus
- PostgreSQL + pgvector for structured memory and semantic search

## Inference Providers (verified, from compute-routing.yaml)

| Provider        | Endpoint              | Compute        | Models                                                                                                                   |
| --------------- | --------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Ollama 0.20.3   | 127.0.0.1:11434       | CUDA/NVIDIA    | gemma4:latest, llama3.2:3b, qwen3.5:2b, nomic-embed-text                                                                 |
| LM Studio       | 127.0.0.1:1234        | Vulkan/AMD     | glm-4.7-flash, gemma-4-26b-a4b, lfm2-24b-a2b, lfm2.5-1.2b                                                                |
| Lemonade 10.2.0 | 127.0.0.1:13305       | Vulkan+NPU+CPU | Qwen3-Coder-30B, Qwen3.5-4B, qwen3.5-4b-FLM, qwen3-0.6b-FLM, qwen3-tk-4b-FLM, embed-gemma-300m-FLM, whisper-v3-turbo-FLM |
| ZAI Cloud       | api.z.ai (Coding API) | Cloud          | GLM 5.1, GLM 4.7, GLM 4.7flashx                                                                                          |

## NPU Performance (Qwen3-0.6B, verified P8 benchmarks)

- Vulkan: 77.96 tok/s decode, 24.61 tok/s prefill
- NPU: 73.35 tok/s decode, 56.40 tok/s prefill

## Control Plane

- OpenClaw v2026.4.12 running as systemd service on port 18789
- Auth token: configured in `~/.config/osmen/env`
- 19 models configured (13 ZAI, 4 Ollama, 2 GitHub Copilot)
- 29 skills including coding-agent, discord, taskflow, session-logs
- Agent workspace: `~/dev/OsMEN-OC/openclaw/`

## AI Tools in Use

- Wave Terminal: configured with 5 local models, ZAI GLM 5.1 default,
  tools enabled (6 working), cloud modes hidden
- Claude Code: MCP bridge at `~/.local/share/claude-bridge/server.mjs`
- OpenCode: config at `~/.config/opencode/opencode.json` with ZAI provider

## Secret Management

- Local SOPS backup -> Podman secret/runtime env -> Quadlet Secret= mapping
- `~/.config/osmen/env` holds runtime env vars (bot tokens, gateway token, DSN)
- `~/.config/osmen/secrets/` holds local secret backups
- `~/.config/sops/age/keys.txt` holds the age key
- Repo `config/secrets/` is template-only
- Wave Terminal secrets store is broken (encryption mismatch between wsh and
  Electron) — API keys placed inline in `waveai.json` as workaround

## FastFlowLM Note

FLM GA runtime is Windows-focused. Ubuntu NPU inference currently goes through
Lemonade Server's `flm` recipe. The spec treats "fastflowlm/NPU swarm" as a
runtime class, not a hard dependency — any OpenAI-compatible NPU endpoint works.
