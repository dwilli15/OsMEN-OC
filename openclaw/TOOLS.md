# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Image Generation (Lemonade sd-cpp)

- Server: http://127.0.0.1:13305
- Default model: `Flux-2-Klein-4B` (quality, supports edit+variation)
- Fast model: `SD-Turbo` (single-step, lower quality)
- Upscale: `RealESRGAN-x4plus` (⚠️ 500 on CPU, needs GPU)
- CPU limits: 512x512 safe, 1024x1024 OOMs
- Endpoints: `/v1/images/generations`, `/v1/images/edits`, `/v1/images/variations`, `/v1/images/upscale`
- max_loaded_models=2 (allows Klein + ESRGAN coexistence)
- Output dir: `~/.local/share/osmen/images/`

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
