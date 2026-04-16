# Operator Profile — D

## Preferences
- Communication: Telegram primary, Discord secondary
- Model preference: zai/glm-5.1 for main, reasoning-capable for complex tasks
- Pipeline philosophy: Everything through OpenClaw — no standalone scripts
- Output style: Concise, direct, no filler
- Approval policy: High/critical risk tools require explicit approval

## Hardware Context
- Host: Ubu-OsMEN (HP OMEN, RTX 5070 Laptop GPU, 8GB VRAM)
- OS: Ubuntu (kernel 7.0.0-14-generic, x64)
- GPU: NVIDIA RTX 5070 Laptop (driver 595.58.03)
- Storage: External Plex media drive, NVMe for system

## Communication Channels
- Telegram: @dwillnow (primary, direct)
- Discord: @deewill (secondary)
- Timezone: America/Chicago

## Key Decisions
- Plex: Native install (no containers)
- Containerization: Podman only (no Docker)
- Secrets: SOPS-encrypted YAML at ~/.config/osmen/secrets/
- Orchestration: Pool-external lifecycle (caller owns asyncpg.Pool)
