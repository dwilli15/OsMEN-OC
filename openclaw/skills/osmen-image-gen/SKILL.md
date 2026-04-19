---
name: osmen-image-gen
description: "Generate, edit, vary, and upscale images via OsMEN's local SD models on Lemonade sd-cpp server. Use when: user asks to create/edit/modify/upscale an image, generate a picture, draw something, or produce visual content."
metadata:
  {
    "openclaw":
      {
        "emoji": "🎨",
        "requires": { "bins": ["lemonade"] },
      },
  }
---

# OsMEN Image Generation & Editing (Lemonade sd-cpp)

Local image generation, editing, variations, and upscaling via Lemonade's sd-cpp backend.

## When to Use

- User asks to create, generate, or draw an image → **Generation**
- User asks to edit, modify, change, inpaint an image → **Edit**
- User asks for a variation of an image → **Variation**
- User asks to upscale/enlarge an image → **Upscale**

## Endpoint

```
Base: http://127.0.0.1:13305
```

OpenAI-compatible endpoints. The server starts on demand.

## Server Lifecycle

### 1. Check if server is up

```bash
curl -sf http://127.0.0.1:13305/v1/models > /dev/null 2>&1 && echo "UP" || echo "DOWN"
```

### 2. Start server if down

```bash
nohup lemonade run Flux-2-Klein-4B --sdcpp cpu > /tmp/lemonade-sd.log 2>&1 &
```

Wait for the server to respond (poll every 3s, max 180s):

```bash
for i in $(seq 1 60); do
  curl -sf http://127.0.0.1:13305/v1/models > /dev/null 2>&1 && break
  sleep 3
done
```

### 3. Set max loaded models (allows multiple models simultaneously)

```bash
lemonade config set max_loaded_models=2
```

## Available Models

| Model | Type | Notes |
|-------|------|-------|
| `SD-Turbo` | generation | Fast single-step (~2-5s CPU), lower quality |
| `Flux-2-Klein-4B` | generation + edit | Higher quality, slower (~30-60s CPU), supports edits |
| `RealESRGAN-x4plus` | upscale | 4x upscaling (currently returns 500 on CPU — may need GPU) |
| `RealESRGAN-x4plus-anime` | upscale | 4x upscaling optimized for anime |

## 1. Image Generation

```bash
curl -s http://127.0.0.1:13305/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Flux-2-Klein-4B",
    "prompt": "A sunset over mountains, digital art",
    "n": 1,
    "size": "512x512"
  }' \
  | python3 -c "
import json, sys, base64
from pathlib import Path
data = json.load(sys.stdin)
if 'data' in data:
    img = data['data'][0]
    out = Path('/home/dwill/.local/share/osmen/images/gen_output.png')
    if 'b64_json' in img:
        out.write_bytes(base64.b64decode(img['b64_json']))
        print(f'Saved: {out}')
    elif 'url' in img:
        print(f'URL: {img[\"url\"]}')
else:
    print(json.dumps(data, indent=2))
"
```

### Parameters

- `model`: `SD-Turbo` (fast) or `Flux-2-Klein-4B` (quality)
- `prompt`: Text description
- `n`: Number of images (default 1, max 4)
- `size`: `256x256`, `512x512` (safe for CPU), `768x768`, `1024x1024` (may OOM on CPU)
- `response_format`: `b64_json` (default) or `url`

### Size Guidance (CPU)

- **256x256**: Fast, safe, good for drafts
- **512x512**: Good balance, ~30-60s on CPU
- **768x768**: May work, slower
- **1024x1024**: Likely OOM on CPU-only, may work with GPU

## 2. Image Editing (Inpainting)

Edit an existing image with a text prompt. Optionally provide a mask to specify which areas to modify.

```bash
curl -s --max-time 600 -X POST http://127.0.0.1:13305/v1/images/edits \
  -F "model=Flux-2-Klein-4B" \
  -F "prompt=change the background to a dark haunted castle" \
  -F "image=@/path/to/source_image.png" \
  -F "size=256x256" \
  | python3 -c "
import json, sys, base64
from pathlib import Path
data = json.load(sys.stdin)
if 'data' in data and 'b64_json' in data['data'][0]:
    out = Path('/home/dwill/.local/share/osmen/images/edited_output.png')
    out.write_bytes(base64.b64decode(data['data'][0]['b64_json']))
    print(f'Saved: {out}')
else:
    print(json.dumps(data, indent=2)[:500])
"
```

### With Mask (Targeted Inpainting)

Provide a PNG mask where **white pixels** = areas to modify, **black pixels** = areas to preserve.

```bash
# Create a mask programmatically
python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (256, 256), (0, 0, 0))  # Black = preserve
draw = ImageDraw.Draw(img)
draw.rectangle([50, 50, 200, 200], fill=(255, 255, 255))  # White = modify center
img.save('/tmp/mask.png')
"

curl -s --max-time 600 -X POST http://127.0.0.1:13305/v1/images/edits \
  -F "model=Flux-2-Klein-4B" \
  -F "prompt=add a glowing crystal in the center" \
  -F "image=@/path/to/source.png" \
  -F "mask=@/tmp/mask.png" \
  -F "size=256x256" \
  | python3 -c "..."
```

### Parameters (multipart/form-data)

- `model`: `Flux-2-Klein-4B` (only model that supports edits currently)
- `prompt`: What to change
- `image`: Source image file (required)
- `mask`: PNG mask, white=modify, black=preserve (optional — no mask = modify entire image)
- `size`: Output dimensions (match source or specify)

## 3. Image Variations

Generate a variation of an existing image.

```bash
curl -s --max-time 600 -X POST http://127.0.0.1:13305/v1/images/variations \
  -F "model=Flux-2-Klein-4B" \
  -F "image=@/path/to/source.png" \
  -F "size=256x256" \
  | python3 -c "
import json, sys, base64
from pathlib import Path
data = json.load(sys.stdin)
if 'data' in data and 'b64_json' in data['data'][0]:
    out = Path('/home/dwill/.local/share/osmen/images/variation_output.png')
    out.write_bytes(base64.b64decode(data['data'][0]['b64_json']))
    print(f'Saved: {out}')
else:
    print(json.dumps(data, indent=2)[:500])
"
```

### Parameters (multipart/form-data)

- `model`: `Flux-2-Klein-4B`
- `image`: Source image file (required)
- `size`: Output dimensions

## 4. Image Upscaling (⚠️ Experimental on CPU)

> **Note**: The `/v1/images/upscale` endpoint with RealESRGAN currently returns 500 errors on CPU-only setups. This may require GPU. As a workaround, use Python + PIL for simple scaling, or generate at higher resolution from the start.

```bash
# If it works (GPU):
curl -s --max-time 300 -X POST http://127.0.0.1:13305/v1/images/upscale \
  -F "model=RealESRGAN-x4plus" \
  -F "image=@/path/to/source.png"
```

### CPU Upscale Workaround (simple resize)

```bash
python3 -c "
from PIL import Image
from pathlib import Path
img = Image.open('/path/to/source.png')
upscaled = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
upscaled.save('/path/to/upscaled.png')
print(f'Upscaled to {upscaled.width}x{upscaled.height}')
"
```

## Output Directory

Default output directory: `~/.local/share/osmen/images/`

```bash
mkdir -p ~/.local/share/osmen/images
```

## Troubleshooting

### OOM / SIGKILL
- Reduce `size` (try 256x256 or 512x512)
- CPU-only has limited RAM for large images
- Kill and restart: `pkill -9 -f "sd-server"`, wait for lemond to respawn

### Timeout
- Klein at 512x512 takes ~30-60s on CPU
- Klein at 1024x1024 will likely timeout/OOM
- Use `--max-time 600` in curl for longer waits

### Server Won't Start
- Check `lemonade status`
- Kill orphan processes: `pkill -f "lemonade.*sd-cpp"`
- Restart: `lemonade run Flux-2-Klein-4B --sdcpp cpu`

### Model Not Downloaded
- Models auto-download on first `run` or `pull`
- SD-Turbo: ~5GB
- Flux-2-Klein-4B: ~15GB
- Pre-download: `lemonade pull Flux-2-Klein-4B`
