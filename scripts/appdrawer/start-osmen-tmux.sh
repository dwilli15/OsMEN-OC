#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/dwill/dev"
SESSION_NAME="osmen"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMUX_CONF="$SCRIPT_DIR/tmux-osmen.conf"

# --- Ensure PATH includes all expected binary locations ---
# Ghostty's -e mode starts with a minimal PATH that omits shell init paths
for dir in \
  /home/linuxbrew/.linuxbrew/bin \
  /home/linuxbrew/.linuxbrew/sbin \
  /home/dwill/.linuxbrew/bin \
  /home/dwill/.linuxbrew/sbin \
  /home/dwill/.local/bin; do
  if [[ -d "$dir" ]] && [[ ":$PATH:" != *":$dir:"* ]]; then
    export PATH="$dir:$PATH"
  fi
done

# --- Resolve binaries ---
CLAUDE_CMD="$(command -v claude 2>/dev/null)" || true
OPENCODE_CMD="$(command -v opencode 2>/dev/null)" || true

# OpenCode "yolo" = auto-approve all tool calls via env var
export OPENCODE_PERMISSION='{"*":"allow"}'

if [[ -z "$CLAUDE_CMD" ]]; then
  echo "ERROR: claude binary not found in PATH" >&2
  echo "Press Ctrl+C to close." >&2
  exec bash
fi

if [[ -z "$OPENCODE_CMD" ]]; then
  echo "WARN: opencode binary not found in PATH" >&2
fi

# --- Attach to existing session if it exists ---
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  exec tmux -f "$TMUX_CONF" attach-session -t "$SESSION_NAME"
fi

# --- Create new session ---
# Window 0: Claude
tmux -f "$TMUX_CONF" new-session -d -s "$SESSION_NAME" -c "$PROJECT_DIR" -n "Claude" \
  -e PATH="$PATH" -e OPENCODE_PERMISSION="$OPENCODE_PERMISSION"
tmux send-keys -t "$SESSION_NAME:0" "$CLAUDE_CMD --permission-mode bypassPermissions --verbose" C-m

# Window 1: OpenCode
if [[ -n "$OPENCODE_CMD" ]]; then
  tmux new-window -t "$SESSION_NAME" -c "$PROJECT_DIR" -n "OpenCode"
  tmux send-keys -t "$SESSION_NAME:1" "OPENCODE_PERMISSION='{\"*\":\"allow\"}' $OPENCODE_CMD --print-logs" C-m
fi

# Select Claude tab as active
tmux select-window -t "$SESSION_NAME:0"

# Attach
exec tmux -f "$TMUX_CONF" attach-session -t "$SESSION_NAME"
