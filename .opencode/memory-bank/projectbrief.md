# Project Brief

OsMEN-OC is a Python 3.13 agent orchestration platform for Ubuntu 26.04 LTS.
It provides the execution engine for multi-agent AI collaboration with local
inference, Discord-based human interaction, and structured workflow management.

The system runs on a Ryzen AI 9 365 / 64 GB / RTX 5070 8GB workstation with
NPU (XDNA2), Vulkan (Radeon 780M iGPU), CUDA (RTX 5070 dGPU), and CPU compute
targets. OpenClaw (Node.js) is the control-plane dependency for Discord/Telegram
bridging and ACP session management.

The repo is the execution engine. OpenClaw is the control surface.
Markdown is the shared cognitive substrate. PostgreSQL is the authoritative store.

## Core Mandates

- Rootless Podman only — no Docker, no docker-compose.
- Agent manifests are YAML data, not code.
- MCP auto-registration from agent manifests at gateway startup.
- Event-driven via Redis Streams with typed EventEnvelope.
- Four-tier approval gate (low/medium/high/critical).
- No vector DB as sole memory authority — markdown + PostgreSQL + pgvector together.
- No framework lock-in to OpenClaw, AutoGen, or CrewAI.
- No monolithic super agent.
- No assumption that all agents are cloud models.
