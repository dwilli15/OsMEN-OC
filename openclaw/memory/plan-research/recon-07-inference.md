# RECON 07: LLM Inference Ecosystem Truth

**Date:** 2026-04-18  
**Agent:** Researcher

## Hardware

| Device | Type | Details |
|--------|------|---------|
| NVIDIA RTX 5070 Max-Q | dGPU | 8GB VRAM, Driver 595.58.03, CUDA 13.2. Currently used by Ollama (672MB), desktop apps (~1.3GB) |
| AMD Radeon 880M/890M (Strix) | iGPU | Display controller, no rocm-smi found. Vulkan ICD available (`radeon_icd.json`). Target for LM Studio Vulkan inference |
| `/dev/accel0` | NPU | AMD Ryzen AI NPU present. No RyzenAI-SW tooling found. No `dmesg` NPU entries captured |

## Runtime Summary Table

| Runtime | Status | Port | GPU Target | Models Available | Storage | Verdict |
|---------|--------|------|------------|-----------------|---------|---------|
| **Ollama** | ✅ Active (systemd, running 6h) | 11434 | NVIDIA RTX 5070 | gemma4:latest (8B Q4_K_M), qwen3.5:2b (2.3B Q8_0), nomic-embed-text (137M F16) | 12GB (`/usr/share/ollama/.ollama/`) | **Primary local LLM.** Working, serving embeddings for OpenClaw memory search + web search. Has osmen-override.conf drop-in. |
| **LM Studio** | ⚠️ Installed, server OFF | 1234 (when running) | AMD Vulkan (Radeon 880M iGPU) | No models downloaded (`~/.cache/lm-studio/` missing) | ~0 | **Not operational.** Binary at `~/.lmstudio/bin/lms`, quadlet service exists (`osmen-inference-lmstudio.service`) but no models and server stopped. Designed for offloading inference to AMD iGPU when NVIDIA is busy (gaming). |
| **Lemonade** | ✅ Active (PID 12331) | 13305 (main), 8001 (sd-cpp), 8002 (flm/ASR) | AMD ROCm (sd-cpp) / CPU (flm) | 16 models total — see below | N/A (no sudo) | **Multi-modal Swiss army knife.** LLM inference, TTS, image gen, ASR, embeddings, upscaling — all local. |

## Lemonade Models (16 total, port 13305)

### LLM (llama.cpp recipe)
| Model | Size | Notes |
|-------|------|-------|
| Qwen3-Coder-30B-A3B-Instruct (Q4_K_M) | 18.6GB | Hot/coding/tool-calling |
| GLM-4.7-Flash (Q4_K_M) | 16.9GB | Custom, at `/opt/osmen/models/` |
| gemma-4-26B-A4B-it (Q4_K_M) | 15.6GB | Custom |

### FLM (Fast LLM, AMD-optimized)
| Model | Size | Notes |
|-------|------|-------|
| qwen3.5:4b | 5.2GB | Vision + reasoning + tool-calling |
| qwen3-tk:4b | 3.1GB | Reasoning + tool-calling |
| translategemma:4b | 4.5GB | Vision (translation) |
| qwen3:0.6b | 0.66GB | Reasoning |
| embed-gemma:300m | 0.62GB | Embeddings |

### Audio
| Model | Size | Notes |
|-------|------|-------|
| whisper-v3:turbo | 0.62GB | ASR (running on port 8002) |
| kokoro-v1 | 0.34GB | TTS (11 voices, 24kHz) |
| LFM2.5-Audio-1.5B (Q8_0) | 1.16GB | Audio model |
| LFM2.5-Audio-1.5B tokenizer | 72MB | — |
| LFM2.5-Audio-1.5B vocoder | 192MB | — |

### Image
| Model | Size | Notes |
|-------|------|-------|
| SD-Turbo | 5.2GB | Image gen (sd-cpp, port 8001, running) |
| RealESRGAN-x4plus | 64MB | Upscaling |
| RealESRGAN-x4plus-anime | 17MB | Anime upscaling |

### Other
| Model | Size | Notes |
|-------|------|-------|
| LFM2.5-1.2B-Instruct (Q8_0) | 1.16GB | Custom |

## OpenClaw Inference Config

### Default model: `zai/glm-5-turbo` (cloud, ZhipuAI API)
### Fallback chain: `openai-codex/gpt-5.4-mini` → `ollama/gemma4:latest` → `ollama/kimi-k2.5:cloud` → `ollama/minimax-m2.5:cloud`

### Main agent: `zai/glm-5.1` (cloud) with fallbacks to `gpt-5.4-mini` → `ollama/gemma4` → cloud ollama models → `glm-5-turbo`

### Subagents (researcher, coder, reviewer, auditor): all use `zai/glm-5-turbo`

### Available providers:
| Provider | Type | Models |
|----------|------|--------|
| **zai** (ZhipuAI) | Cloud API | glm-5.1, glm-5, glm-5-turbo, glm-5v-turbo, glm-4.7, glm-4.7-flash, glm-4.7-flashx, glm-4.6, glm-4.6v, glm-4.5, glm-4.5-air, glm-4.5-flash, glm-4.5v |
| **ollama** | Local (NVIDIA) | gemma4:latest, kimi-k2.5:cloud, minimax-m2.5:cloud, glm-5:cloud |
| **github-copilot** | Cloud (token) | claude-opus-4.6, gpt-5.4 |
| **openai-codex** | Cloud (OAuth) | gpt-5.4-mini (fallback only) |

### Memory search: Ollama nomic-embed-text (local)
### Web search: Ollama experimental + OpenAI Codex cached

## Coding Tools

| Tool | Path | Status |
|------|------|--------|
| VS Code Insiders | `/usr/bin/code-insiders` | ✅ Running (137MB VRAM) |
| Claude Code | `~/.linuxbrew/bin/claude` | ✅ Installed |
| OpenCode | `~/.linuxbrew/bin/opencode` | ✅ Installed |

No `opencode.json` found in project root.

## NPU Status

- `/dev/accel0` exists — AMD Ryzen AI NPU is present
- No RyzenAI-SW or onnxruntime-ryzen packages found
- **Untapped potential** — no software leverages the NPU currently

---

## Recommendations

### What's Working Well
1. **Ollama + NVIDIA** — Solid primary local inference. Embeddings power OpenClaw memory search and web search. gemma4:latest as fallback is good.
2. **Lemonade** — Incredibly comprehensive. TTS, image gen, ASR, embeddings, LLM, upscaling all in one. sd-cpp and flm servers actively running.
3. **Cloud stack (ZhipuAI + Copilot + OpenAI)** — Strong multi-provider setup with good fallback chain. ZhipuAI models are cheap and capable.

### What's Redundant
1. **LM Studio** — Installed with a quadlet service but zero models and server off. It was designed to offload to AMD iGPU via Vulkan, but Lemonade's FLM models already serve the same purpose (AMD-optimized inference). **Recommendation:** Either commit to using it (download models, enable service) or remove it to reduce confusion. The quadlet mentions FFXIV offloading which is a valid use case — keep the service file but document intent.
2. **Dual embedding models** — Both Ollama (`nomic-embed-text`) and Lemonade (`embed-gemma-300m`) have embedding models. OpenClaw uses Ollama's. Lemonade's is available for other purposes.

### What D Should Focus On
1. **Activate the NPU** — `/dev/accel0` is sitting idle. RyzenAI-SW could offload lightweight models (embedding, small TTS) and free GPU resources. Worth investigating.
2. **Decide on LM Studio** — It's the only runtime with zero models. Either give it a purpose or remove it.
3. **Lemonade's LLM models are huge** — Qwen3-Coder-30B (18.6GB), GLM-4.7-Flash (16.9GB), gemma-4-26B (15.6GB) are competing with the same NVIDIA GPU Ollama uses. Understand which runtime gets priority when both want GPU memory.
4. **Cloud cost awareness** — GLM-5-turbo at $1.2/$4 per M tokens with 200K context adds up fast for subagents. Consider routing more subagent work to local Ollama/Lemonade models.
