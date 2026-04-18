---
name: osmen-image-gen
description: "Generate images via OsMEN's SD-Turbo engine on Lemonade sd-cpp server. Use when: user asks to create an image, generate a picture, draw something, or produce visual content. Calls the OpenAI-compatible /v1/images/generations endpoint. On-demand server startup supported."
metadata:
  {
    "openclaw":
      {
        "emoji": "🎨",
        "requires": { "bins": ["lemonade"] },
      },
  }
---

# OsMEN Image Generation (SD-Turbo via Lemonade sd-cpp)

Generate images from text prompts using Stable Diffusion Turbo, served by
Lemonade's sd-cpp backend.

## When to Use

- User asks to create, generate, or draw an image
- User needs visual content from a text description
- User wants to see what something looks like
- Any request involving image generation

## Endpoint

```
POST http://127.0.0.1:13395/v1/images/generations
```

OpenAI-compatible endpoint. The sd-cpp server starts on demand.

## Server Lifecycle

The image gen server is NOT always running. Follow this pattern:

### 1. Check if server is up

```bash
curl -sf http://127.0.0.1:13395/v1/models > /dev/null 2>&1 && echo "UP" || echo "DOWN"
```

### 2. Start server if down

```bash
lemonade run SD-Turbo --sdcpp cpu 2>/dev/null &
```

Wait for the server to respond (poll every 2s, max 120s):

```bash
for i in $(seq 1 60); do
  curl -sf http://127.0.0.1:13395/v1/models > /dev/null 2>&1 && break
  sleep 2
done
```

### 3. Generate image

```bash
curl -s http://127.0.0.1:13395/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "SD-Turbo",
    "prompt": "A sunset over mountains, digital art",
    "n": 1,
    "size": "512x512"
  }' \
  | python3 -c "
import json, sys, base64
from pathlib import Path
data = json.load(sys.stdin)
img = data['data'][0]
if 'b64_json' in img:
    Path('/tmp/gen_image.png').write_bytes(base64.b64decode(img['b64_json']))
    print('Saved: /tmp/gen_image.png')
elif 'url' in img:
    print(f'URL: {img[\"url\"]}')
"
```

### 4. Show the image

```bash
xdg-open /tmp/gen_image.png 2>/dev/null || echo "Image at /tmp/gen_image.png"
```

## Parameters

- `model`: Always `SD-Turbo` (default)
- `prompt`: Text description of the desired image
- `n`: Number of images to generate (default 1, max 4)
- `size`: Image dimensions — `256x256`, `512x512` (default), or `768x768`
- `response_format`: `b64_json` (default) or `url`

## Output

Default output directory: `~/.local/share/osmen/images/`

```bash
mkdir -p ~/.local/share/osmen/images
```

## Available Models

| Model | Notes |
|-------|-------|
| `SD-Turbo` | Default, fast single-step generation, good for drafts |
| `Flux-2-Klein-4B` | Higher quality, slower, may need to download first |

To use Flux: `lemonade run Flux-2-Klein-4B --sdcpp cpu`

## Notes

- CPU-based generation (no GPU required, but CUDA is faster if available)
- SD-Turbo is single-step: fast (~2-5s on modern CPU) but lower quality
- For higher quality, use Flux-2-Klein-4B (slower, ~30-60s)
- The server auto-stops after idle timeout — restart if needed
- All generation is local/offline — no cloud calls
