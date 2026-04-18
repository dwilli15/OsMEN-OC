---
name: osmen-tts
description: "Generate speech audio via OsMEN's Kokoro TTS engine on Lemonade Server. Use when: user asks for text-to-speech, voice output, reading text aloud, or audio generation. Calls the OpenAI-compatible /v1/audio/speech endpoint on localhost:13305. Supports multiple voices and languages via kokoro-v1."
metadata:
  {
    "openclaw":
      {
        "emoji": "🎙️",
        "requires": { "services": ["http://127.0.0.1:13305"] },
      },
  }
---

# OsMEN TTS (Kokoro via Lemonade Server)

Generate speech from text using the kokoro-v1 model served by Lemonade Server.

## When to Use

- User asks to hear text spoken aloud
- User needs an audio file from text
- User asks for voice output or narration
- Any request involving text-to-speech

## Endpoint

```
POST http://127.0.0.1:13305/v1/audio/speech
```

OpenAI-compatible endpoint. The kokoro-v1 model is already loaded.

## Usage

### Generate speech (curl)

```bash
curl -s http://127.0.0.1:13305/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro-v1",
    "input": "Hello, this is a test.",
    "voice": "af_heart",
    "response_format": "wav"
  }' \
  --output /tmp/tts_output.wav
```

### Parameters

- `model`: Always `kokoro-v1`
- `input`: The text to speak (plain string)
- `voice`: Voice preset name. Available voices include:
  - `af_heart` (default, warm female)
  - `af_bella` (clear female)
  - `af_nicole` (calm female)
  - `af_sarah` (professional female)
  - `af_sky` (bright female)
  - `am_adam` (deep male)
  - `am_michael` (warm male)
  - `bf_emma` (British female)
  - `bf_isabella` (British female)
  - `bm_george` (British male)
  - `bm_lewis` (British male)
- `response_format`: `wav` (default), `mp3`, or `pcm`
- `speed`: Float, 0.5-2.0 (default 1.0)

### Play the result

```bash
# Via paplay (PulseAudio/PipeWire)
paplay /tmp/tts_output.wav

# Via ffplay (ffmpeg)
ffplay -autoexit -nodisp /tmp/tts_output.wav
```

### Long text

For text longer than ~2000 characters, split into paragraphs and generate
separate files, then concatenate:

```bash
# Generate segments
curl -s http://127.0.0.1:13305/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro-v1","input":"First paragraph.","voice":"af_heart"}' \
  --output /tmp/tts_seg1.wav

# Concatenate with ffmpeg
ffmpeg -f concat -safe 0 \
  -i <(printf "file '/tmp/tts_seg1.wav'\nfile '/tmp/tts_seg2.wav'\n") \
  -c copy /tmp/tts_combined.wav
```

## Prerequisites

- Lemonade Server running with kokoro-v1 model loaded
- Check: `curl -s http://127.0.0.1:13305/v1/models | grep kokoro`
- If not running: see OsMEN docs for starting Lemonade Server

## Notes

- This is a local, offline TTS engine (no cloud calls)
- The kokoro-v1 model is 82M parameters, runs on CPU
- Sample rate: 24000 Hz
- For Piper TTS (legacy): use model `piper` on OsMEN's TTS module directly
