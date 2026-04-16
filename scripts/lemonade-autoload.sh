#!/usr/bin/env bash
# lemonade-autoload.sh — Load default NPU model into Lemonade after server start.
# Called by osmen-lemonade-autoload.service (systemd oneshot).
set -euo pipefail

LEMONADE_HOST="${LEMONADE_HOST:-127.0.0.1}"
LEMONADE_PORT="${LEMONADE_PORT:-13305}"
MODEL="${LEMONADE_DEFAULT_MODEL:-qwen3.5-4b-FLM}"
MAX_WAIT=30

# Wait for Lemonade to be ready.
for i in $(seq 1 "$MAX_WAIT"); do
    if lemonade status --host "$LEMONADE_HOST" --port "$LEMONADE_PORT" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Load the default model.
echo "Loading default NPU model: ${MODEL}"
lemonade load "$MODEL" --host "$LEMONADE_HOST" --port "$LEMONADE_PORT"
echo "Model loaded successfully."
