#!/usr/bin/env bash
set -euo pipefail

prepend_existing_path() {
  local dir="$1"

  if [[ ! -d "$dir" ]]; then
    return 0
  fi

  case ":$PATH:" in
    *":$dir:"*) ;;
    *) PATH="$dir:$PATH" ;;
  esac
}

prepend_existing_path "$HOME/.local/bin"
prepend_existing_path "$HOME/.linuxbrew/bin"
prepend_existing_path "$HOME/.linuxbrew/sbin"
prepend_existing_path "/home/linuxbrew/.linuxbrew/bin"
prepend_existing_path "/home/linuxbrew/.linuxbrew/sbin"

declare -a ORIGINAL_ARGS=("$@")

TRACE_FILE="${CLAUDE_OSMEN_TRACE_FILE:-}"

if [[ -z "$TRACE_FILE" ]]; then
  TRACE_FILE="${TMPDIR:-/tmp}/claude_osmen_launcher_$(date '+%Y%m%d_%H%M%S').log"
fi

export CLAUDE_OSMEN_TRACE_FILE="$TRACE_FILE"

touch "$TRACE_FILE"

trace() {
  local mode="launcher"

  if [[ "$LAUNCH_TABS" -eq 1 ]]; then
    mode="launch-tabs"
  elif [[ "$LAUNCH_TABS_INNER" -eq 1 ]]; then
    mode="launch-tabs-inner"
  elif [[ "$HOST_WINDOW" -eq 1 ]]; then
    mode="host-window"
  elif [[ "$CLAUDE_ONLY" -eq 1 ]]; then
    mode="claude-only"
  elif [[ "$OPENCODE_ONLY" -eq 1 ]]; then
    mode="opencode-only"
  fi

  printf '[%s] pid=%s ppid=%s mode=%s cwd=%s %s\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" \
    "$$" \
    "$PPID" \
    "$mode" \
    "$PWD" \
    "$*" >>"$TRACE_FILE"
}

PROJECT_DIR="${PROJECT_DIR:-/home/dwill/dev}"
LAUNCH_TABS=0
LAUNCH_TABS_INNER=0
HOST_WINDOW=0
CLAUDE_ONLY=0
OPENCODE_ONLY=0
AUTO_UPDATE=0
SKIP_UPDATE=0
MODEL="opus"
PERMISSION_MODE="bypassPermissions"
EFFORT=""
SESSION_NAME=""
SESSION_PROMPT=""
RESUME_VALUE=""
CONTINUE_SESSION=0
NEW_SESSION=0
FORK_SESSION=0
SESSION_ID=""
SYSTEM_PROMPT=""
SYSTEM_PROMPT_FILE=""
APPEND_SYSTEM_PROMPT_FILE=""
SETTINGS_VALUE=""
STRICT_MCP_CONFIG=0
IDE=0
CHROME=0
NO_CHROME=0
ENABLE_AUTO_MODE=0
BRIEF=0
BARE=0
TEAMMATE_MODE=""
REMOTE_TASK=""
REMOTE_CONTROL=0
REMOTE_CONTROL_NAME=""
TELEPORT=0
TOOLS_VALUE=""
WORKTREE_VALUE=""
TMUX_MODE=0
DEBUG_FILTER=""
DEBUG_FILE=""
ACTIVATE_TEAM=0
NO_TEAM=0
DISABLE_SLASH_COMMANDS=0
INIT_MODE=0
INIT_ONLY_MODE=0
CLAUDE_CMD=""
TEAM_ENABLED=0

declare -a ADD_DIRS=()
declare -a PLUGIN_DIRS=()
declare -a MCP_CONFIGS=()
declare -a ALLOWED_TOOLS=()
declare -a DISALLOWED_TOOLS=()
declare -a EXTRA_ARGS=()
declare -a SESSION_ARGS=()

usage() {
  cat <<'EOF'
Usage: start-claude-osmen.sh [options] [-- extra claude args]

Wrapper options:
  --launch-tabs
  --host-window
  --claude-only
  --opencode-only
  --project-dir PATH
  --auto-update
  --skip-update
  --model NAME
  --permission-mode MODE
  --effort LEVEL
  --name SESSION_NAME
  --resume SESSION_ID_OR_NAME
  --continue
  --new-session
  --fork-session
  --session-id UUID
  --system-prompt TEXT
  --system-prompt-file PATH
  --append-system-prompt-file PATH
  --settings PATH_OR_JSON
  --add-dir PATH
  --plugin-dir PATH
  --mcp-config PATH_OR_JSON
  --strict-mcp-config
  --ide
  --chrome
  --no-chrome
  --enable-auto-mode
  --brief
  --bare
  --teammate-mode auto|in-process|tmux
  --remote TASK
  --remote-control [NAME]
  --teleport
  --allowed-tools RULE
  --disallowed-tools RULE
  --tools CSV
  --worktree NAME
  --tmux
  --debug-filter FILTER
  --debug-file PATH
  --activate-team
  --no-team
  --disable-slash-commands
  --init
  --init-only
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --launch-tabs)
      LAUNCH_TABS=1
      shift
      ;;
    --launch-tabs-inner)
      LAUNCH_TABS_INNER=1
      shift
      ;;
    --host-window)
      HOST_WINDOW=1
      shift
      ;;
    --claude-only)
      CLAUDE_ONLY=1
      shift
      ;;
    --opencode-only)
      OPENCODE_ONLY=1
      NEW_SESSION=1
      NO_TEAM=1
      shift
      ;;
    --project-dir)
      PROJECT_DIR="$2"
      shift 2
      ;;
    --auto-update|-u)
      AUTO_UPDATE=1
      shift
      ;;
    --skip-update)
      SKIP_UPDATE=1
      shift
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --permission-mode)
      PERMISSION_MODE="$2"
      shift 2
      ;;
    --effort)
      EFFORT="$2"
      shift 2
      ;;
    --name)
      SESSION_NAME="$2"
      shift 2
      ;;
    --resume)
      RESUME_VALUE="$2"
      shift 2
      ;;
    --continue)
      CONTINUE_SESSION=1
      shift
      ;;
    --new-session)
      NEW_SESSION=1
      shift
      ;;
    --fork-session)
      FORK_SESSION=1
      shift
      ;;
    --session-id)
      SESSION_ID="$2"
      shift 2
      ;;
    --system-prompt)
      SYSTEM_PROMPT="$2"
      shift 2
      ;;
    --system-prompt-file)
      SYSTEM_PROMPT_FILE="$2"
      shift 2
      ;;
    --append-system-prompt-file)
      APPEND_SYSTEM_PROMPT_FILE="$2"
      shift 2
      ;;
    --settings)
      SETTINGS_VALUE="$2"
      shift 2
      ;;
    --add-dir)
      ADD_DIRS+=("$2")
      shift 2
      ;;
    --plugin-dir)
      PLUGIN_DIRS+=("$2")
      shift 2
      ;;
    --mcp-config)
      MCP_CONFIGS+=("$2")
      shift 2
      ;;
    --strict-mcp-config)
      STRICT_MCP_CONFIG=1
      shift
      ;;
    --ide)
      IDE=1
      shift
      ;;
    --chrome)
      CHROME=1
      shift
      ;;
    --no-chrome)
      NO_CHROME=1
      shift
      ;;
    --enable-auto-mode)
      ENABLE_AUTO_MODE=1
      shift
      ;;
    --brief)
      BRIEF=1
      shift
      ;;
    --bare)
      BARE=1
      shift
      ;;
    --teammate-mode)
      TEAMMATE_MODE="$2"
      shift 2
      ;;
    --remote)
      REMOTE_TASK="$2"
      shift 2
      ;;
    --remote-control)
      REMOTE_CONTROL=1
      if [[ $# -gt 1 && "$2" != --* ]]; then
        REMOTE_CONTROL_NAME="$2"
        shift 2
      else
        shift
      fi
      ;;
    --teleport)
      TELEPORT=1
      shift
      ;;
    --allowed-tools)
      ALLOWED_TOOLS+=("$2")
      shift 2
      ;;
    --disallowed-tools)
      DISALLOWED_TOOLS+=("$2")
      shift 2
      ;;
    --tools)
      TOOLS_VALUE="$2"
      shift 2
      ;;
    --worktree)
      WORKTREE_VALUE="$2"
      shift 2
      ;;
    --tmux)
      TMUX_MODE=1
      shift
      ;;
    --debug-filter)
      DEBUG_FILTER="$2"
      shift 2
      ;;
    --debug-file)
      DEBUG_FILE="$2"
      shift 2
      ;;
    --activate-team)
      ACTIVATE_TEAM=1
      shift
      ;;
    --no-team)
      NO_TEAM=1
      shift
      ;;
    --disable-slash-commands)
      DISABLE_SLASH_COMMANDS=1
      shift
      ;;
    --init)
      INIT_MODE=1
      shift
      ;;
    --init-only)
      INIT_ONLY_MODE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA_ARGS+=("$@")
      break
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

resolve_script_path() {
  python3 - <<'PY' "${BASH_SOURCE[0]}"
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

build_child_args() {
  local arg

  for arg in "${ORIGINAL_ARGS[@]}"; do
    case "$arg" in
      --launch-tabs|--launch-tabs-inner|--host-window|--claude-only|--opencode-only)
        continue
        ;;
      *)
        printf '%s\0' "$arg"
        ;;
    esac
  done
}

launch_tabs() {
  local script_path="$1"
  local -a child_args=()
  local arg

  while IFS= read -r -d '' arg; do
    child_args+=("$arg")
  done < <(build_child_args)

  require_command ptyxis

  # ------------------------------------------------------------------
  # Ptyxis gives a stripped-down "command terminal" when you pass
  # -- COMMAND or -x CMD. No tab bar, no +tab button.
  #
  # Fix: use ptyxis profiles with custom-command set. Profiles
  # appear as normal shell tabs with full UI (tab bar, +button).
  # ------------------------------------------------------------------

  local claude_uuid opencode_uuid
  claude_uuid=$(ptyxis_ensure_profile "Claude OSMEN" "${script_path} --claude-only ${child_args[*]}")

  trace "opening new window with claude profile uuid=$claude_uuid"
  # --new-window --tab-with-profile opens a new window with that profile's tab
  ptyxis --new-window -d "$PROJECT_DIR" --tab-with-profile "$claude_uuid" &
  disown

  trace "sleeping 1.5s to let new window gain focus"
  sleep 1.5

  if [[ -n "$OPENCODE_CMD" ]]; then
    opencode_uuid=$(ptyxis_ensure_profile "OpenCode" "${script_path} --opencode-only --project-dir ${PROJECT_DIR}")
    trace "opening opencode tab with profile uuid=$opencode_uuid"
    ptyxis --tab -d "$PROJECT_DIR" --tab-with-profile "$opencode_uuid" &
    disown
  fi

  trace "launch-tabs parent exiting"
  exit 0
}

# Ensure a Ptyxis profile exists with the given label and custom command.
# Prints the profile UUID to stdout.
ptyxis_ensure_profile() {
  local label="$1"
  local cmd="$2"

  local existing_uuids
  existing_uuids=$(gsettings get org.gnome.Ptyxis profile-uuids 2>/dev/null || echo "@as []")
  existing_uuids="${existing_uuids#@as }"

  # Look for existing profile with matching label
  local uuid
  for uuid in $(echo "$existing_uuids" | tr -d "[]'," | tr -s ' '); do
    [[ -z "$uuid" ]] && continue
    local plabel
    plabel=$(gsettings get "org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/profiles/${uuid}/" label 2>/dev/null | tr -d "'")
    if [[ "$plabel" == "$label" ]]; then
      trace "reusing existing profile uuid=$uuid label=$label"
      local ppath="org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/profiles/${uuid}/"
      gsettings set "$ppath" use-custom-command true 2>/dev/null
      gsettings set "$ppath" custom-command "$cmd" 2>/dev/null
      gsettings set "$ppath" login-shell false 2>/dev/null
      echo "$uuid"
      return 0
    fi
  done

  # Generate new UUID (32 hex chars)
  uuid=$(uuidgen 2>/dev/null | tr -d '-' | tr '[:upper:]' '[:lower:]' | cut -c1-32)
  [[ -z "$uuid" ]] && uuid="$(od -x /dev/urandom | head -2 | tr -d ' ' | tr -d '\n' | cut -c1-32)"

  local ppath="org.gnome.Ptyxis.Profile:/org/gnome/Ptyxis/profiles/${uuid}/"
  trace "creating new profile uuid=$uuid label=$label"

  gsettings set "$ppath" label "$label" 2>/dev/null
  gsettings set "$ppath" use-custom-command true 2>/dev/null
  gsettings set "$ppath" custom-command "$cmd" 2>/dev/null
  gsettings set "$ppath" login-shell false 2>/dev/null

  # Register UUID in profile list
  local current
  current=$(gsettings get org.gnome.Ptyxis profile-uuids 2>/dev/null || echo "@as []")
  current="${current#@as }"
  # Append
  if [[ "$current" == "[]" ]]; then
    gsettings set org.gnome.Ptyxis profile-uuids "['${uuid}']" 2>/dev/null
  else
    gsettings set org.gnome.Ptyxis profile-uuids "${current%]}, '${uuid}']" 2>/dev/null
  fi

  echo "$uuid"
}

run_opencode_tab() {
  if [[ -z "$OPENCODE_CMD" ]]; then
    trace "opencode command missing"
    echo "OpenCode CLI not found." >&2
    echo "Terminal remains open - press Ctrl+D or type 'exit' to close."
    exec bash
  fi

  trace "starting opencode command=$OPENCODE_CMD args=${EXTRA_ARGS[*]}"

  set +e
  "$OPENCODE_CMD" "${EXTRA_ARGS[@]}"
  local opencode_exit=$?
  set -e

  trace "opencode exited code=$opencode_exit"

  echo
  echo "OpenCode session ended (exit code: $opencode_exit)."
  echo "Terminal remains open - press Ctrl+D or type 'exit' to close."
  exec bash
}

print_banner() {
  echo
  echo "==========================================="
  echo "  Claude Code Launcher: OsMEN System"
  echo "  Project: $PROJECT_DIR"
  echo "  Skills: osmen-config, siyuan-integration, taskwarrior-sync, vector-query"
  echo "  Models: opus=GLM-5.1 sonnet=GLM-4.7 haiku=GLM-4.7flashx"
  echo "==========================================="
}

resolve_node_cmd() {
  local resolved=""
  local nvm_candidates=()
  local candidates=()

  if [[ -n "${NODE_BIN:-}" ]] && [[ -x "${NODE_BIN}" ]]; then
    printf '%s\n' "${NODE_BIN}"
    return 0
  fi

  resolved="$(command -v node 2>/dev/null || true)"
  if [[ -n "$resolved" ]] && [[ -x "$resolved" ]]; then
    printf '%s\n' "$resolved"
    return 0
  fi

  shopt -s nullglob
  nvm_candidates=("$HOME"/.nvm/versions/node/*/bin/node)
  shopt -u nullglob
  if [[ "${#nvm_candidates[@]}" -gt 0 ]]; then
    printf '%s\n' "${nvm_candidates[@]}" | sort -V | tail -n 1
    return 0
  fi

  candidates=(
    "$HOME/.linuxbrew/bin/node"
    "/home/linuxbrew/.linuxbrew/bin/node"
    "$HOME/.local/bin/node"
    "/usr/local/bin/node"
    "/usr/bin/node"
  )

  for resolved in "${candidates[@]}"; do
    if [[ -x "$resolved" ]]; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done

  return 1
}

resolve_claude_cmd() {
  local resolved=""
  local npm_prefix=""
  local nvm_candidates=()

  if [[ -n "${CLAUDE_BIN:-}" ]] && [[ -x "${CLAUDE_BIN}" ]]; then
    printf '%s\n' "${CLAUDE_BIN}"
    return 0
  fi

  resolved="$(command -v claude 2>/dev/null || true)"
  if [[ -n "$resolved" ]] && [[ -x "$resolved" ]]; then
    printf '%s\n' "$resolved"
    return 0
  fi

  if command -v npm >/dev/null 2>&1; then
    npm_prefix="$(npm -g config get prefix 2>/dev/null || true)"
    if [[ -n "$npm_prefix" && -x "$npm_prefix/bin/claude" ]]; then
      printf '%s\n' "$npm_prefix/bin/claude"
      return 0
    fi
  fi

  shopt -s nullglob
  nvm_candidates=("$HOME"/.nvm/versions/node/*/bin/claude)
  shopt -u nullglob
  if [[ "${#nvm_candidates[@]}" -gt 0 ]]; then
    printf '%s\n' "${nvm_candidates[@]}" | sort -V | tail -n 1
    return 0
  fi

  if [[ -x "$HOME/.local/bin/claude" ]]; then
    printf '%s\n' "$HOME/.local/bin/claude"
    return 0
  fi

  if [[ -x "/usr/local/bin/claude" ]]; then
    printf '%s\n' "/usr/local/bin/claude"
    return 0
  fi

  if [[ -x "/usr/bin/claude" ]]; then
    printf '%s\n' "/usr/bin/claude"
    return 0
  fi

  return 1
}

resolve_opencode_cmd() {
  local resolved=""
  local npm_prefix=""
  local nvm_candidates=()

  if [[ -n "${OPENCODE_BIN:-}" ]] && [[ -x "${OPENCODE_BIN}" ]]; then
    printf '%s\n' "${OPENCODE_BIN}"
    return 0
  fi

  resolved="$(command -v opencode 2>/dev/null || true)"
  if [[ -n "$resolved" ]] && [[ -x "$resolved" ]]; then
    printf '%s\n' "$resolved"
    return 0
  fi

  if command -v npm >/dev/null 2>&1; then
    npm_prefix="$(npm -g config get prefix 2>/dev/null || true)"
    if [[ -n "$npm_prefix" && -x "$npm_prefix/bin/opencode" ]]; then
      printf '%s\n' "$npm_prefix/bin/opencode"
      return 0
    fi
    if [[ -n "$npm_prefix" && -x "$npm_prefix/bin/opencode-ai" ]]; then
      printf '%s\n' "$npm_prefix/bin/opencode-ai"
      return 0
    fi
  fi

  shopt -s nullglob
  nvm_candidates=("$HOME"/.nvm/versions/node/*/bin/opencode "$HOME"/.nvm/versions/node/*/bin/opencode-ai)
  shopt -u nullglob
  if [[ "${#nvm_candidates[@]}" -gt 0 ]]; then
    printf '%s\n' "${nvm_candidates[@]}" | sort -V | tail -n 1
    return 0
  fi

  if [[ -x "$HOME/.local/bin/opencode" ]]; then
    printf '%s\n' "$HOME/.local/bin/opencode"
    return 0
  fi

  if [[ -x "$HOME/.local/bin/opencode-ai" ]]; then
    printf '%s\n' "$HOME/.local/bin/opencode-ai"
    return 0
  fi

  return 1
}

resolve_dir() {
  local target="$1"
  [[ -z "$target" ]] && return 0
  if [[ ! -d "$target" ]]; then
    echo "Directory not found: $target" >&2
    exit 1
  fi
  (cd "$target" && pwd)
}

resolve_file() {
  local target="$1"
  [[ -z "$target" ]] && return 0
  if [[ ! -f "$target" ]]; then
    echo "File not found: $target" >&2
    exit 1
  fi
  python3 - <<'PY' "$target"
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

resolve_path_or_json() {
  local target="$1"
  [[ -z "$target" ]] && return 0
  if [[ -e "$target" ]]; then
    python3 - <<'PY' "$target"
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
  else
    printf '%s\n' "$target"
  fi
}

run_update_if_needed() {
  local log_path="$1"
  if [[ "$SKIP_UPDATE" -eq 1 || "$AUTO_UPDATE" -ne 1 ]]; then
    printf '[%s] [UPDATE] skipped inline launcher update\n' "$(date '+%Y-%m-%d %H:%M:%S')" >>"$log_path" || true
    return 0
  fi

  echo
  echo "Checking for Claude Code updates..."
  local update_output
  update_output="$("$CLAUDE_CMD" update 2>&1 || true)"
  printf '[%s] [UPDATE] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$update_output" >>"$log_path" || true

  shopt -s nocasematch
  if [[ "$update_output" =~ already\ up.to.date|no\ update|up\ to\ date ]]; then
    echo "Claude Code is up to date."
    shopt -u nocasematch
    return 0
  fi

  if [[ "$AUTO_UPDATE" -eq 1 && "$update_output" =~ available|found ]]; then
    echo "Auto-updating Claude Code..."
    "$CLAUDE_CMD" update >/dev/null 2>&1 || true
  fi
  shopt -u nocasematch
}

choose_session_prompt() {
  if [[ "$CONTINUE_SESSION" -eq 1 && "$NEW_SESSION" -eq 1 ]]; then
    echo "Use either --continue or --new-session, not both." >&2
    exit 1
  fi

  if [[ -n "$RESUME_VALUE" ]]; then
    SESSION_PROMPT="RESUMING: Continue a named or explicit session."
    SESSION_ARGS=(--resume "$RESUME_VALUE")
    [[ "$FORK_SESSION" -eq 1 ]] && SESSION_ARGS+=(--fork-session)
    return 0
  fi

  if [[ "$CONTINUE_SESSION" -eq 1 ]]; then
    SESSION_PROMPT="RESUMING: Continue from your last session in this workspace."
    SESSION_ARGS=(--continue)
    [[ "$FORK_SESSION" -eq 1 ]] && SESSION_ARGS+=(--fork-session)
    return 0
  fi

  if [[ "$NEW_SESSION" -eq 1 ]]; then
    SESSION_PROMPT="NEW SESSION: Start fresh in this workspace."
    SESSION_ARGS=()
    return 0
  fi

  if [[ -n "$SESSION_ID" ]]; then
    SESSION_PROMPT="RESUMING: Reusing a fixed session identifier."
    SESSION_ARGS=(--session-id "$SESSION_ID")
    return 0
  fi

  if [[ ! -t 0 ]]; then
    SESSION_PROMPT="NEW SESSION: Non-interactive shell detected, defaulting to a fresh session."
    SESSION_ARGS=()
    return 0
  fi

  SESSION_PROMPT="AUTO SESSION: Launcher skips resume prompts; use in-app resume if needed."
  SESSION_ARGS=()
}

choose_team_mode() {
  if [[ "$ACTIVATE_TEAM" -eq 1 && "$NO_TEAM" -eq 1 ]]; then
    echo "Use either --activate-team or --no-team, not both." >&2
    exit 1
  fi

  if [[ "$ACTIVATE_TEAM" -eq 1 ]]; then
    TEAM_ENABLED=1
    return 0
  fi

  if [[ "$NO_TEAM" -eq 1 ]]; then
    TEAM_ENABLED=0
    return 0
  fi

  TEAM_ENABLED=1
}

# Resolve claude first so its directory is authoritative on PATH.
# This prevents the node directory prepend from shadowing the intended claude binary.
CLAUDE_CMD="$(resolve_claude_cmd || true)"
if [[ -z "$CLAUDE_CMD" ]]; then
  echo "Required command not found: claude" >&2
  echo "Looked in PATH, npm global prefix, $HOME/.nvm/versions/node/*/bin/claude, $HOME/.local/bin/claude, /usr/local/bin/claude, /usr/bin/claude" >&2
  exit 1
fi
export PATH="$(dirname "$CLAUDE_CMD"):$PATH"
trace "resolved claude=$CLAUDE_CMD"

NODE_CMD="$(resolve_node_cmd || true)"
if [[ -z "$NODE_CMD" ]]; then
  echo "Required command not found: node" >&2
  echo "Looked in PATH, $HOME/.nvm/versions/node/*/bin/node, $HOME/.linuxbrew/bin/node, /home/linuxbrew/.linuxbrew/bin/node, /usr/local/bin/node, /usr/bin/node" >&2
  exit 1
fi
# Only prepend node's dir if it is not already claude's dir (avoids redundant prepend).
if [[ "$(dirname "$NODE_CMD")" != "$(dirname "$CLAUDE_CMD")" ]]; then
  prepend_existing_path "$(dirname "$NODE_CMD")"
fi
trace "resolved node=$NODE_CMD trace_file=$TRACE_FILE"

SCRIPT_PATH="$(resolve_script_path)"

if [[ "$LAUNCH_TABS" -eq 1 && "$CLAUDE_ONLY" -eq 1 ]]; then
  echo "Use either --launch-tabs or --claude-only, not both." >&2
  exit 1
fi

if [[ "$LAUNCH_TABS" -eq 1 && "$OPENCODE_ONLY" -eq 1 ]]; then
  echo "Use either --launch-tabs or --opencode-only, not both." >&2
  exit 1
fi

if [[ "$LAUNCH_TABS" -eq 1 && "$HOST_WINDOW" -eq 1 ]]; then
  echo "Use either --launch-tabs or --host-window, not both." >&2
  exit 1
fi

if [[ "$HOST_WINDOW" -eq 1 && "$CLAUDE_ONLY" -eq 1 ]]; then
  echo "Use either --host-window or --claude-only, not both." >&2
  exit 1
fi

if [[ "$HOST_WINDOW" -eq 1 && "$OPENCODE_ONLY" -eq 1 ]]; then
  echo "Use either --host-window or --opencode-only, not both." >&2
  exit 1
fi

if [[ "$CLAUDE_ONLY" -eq 1 && "$OPENCODE_ONLY" -eq 1 ]]; then
  echo "Use either --claude-only or --opencode-only, not both." >&2
  exit 1
fi

require_command python3

if [[ "$CHROME" -eq 1 && "$NO_CHROME" -eq 1 ]]; then
  echo "Use either --chrome or --no-chrome, not both." >&2
  exit 1
fi

if [[ -n "$SYSTEM_PROMPT" && -n "$SYSTEM_PROMPT_FILE" ]]; then
  echo "Use either --system-prompt or --system-prompt-file, not both." >&2
  exit 1
fi

if [[ "$TMUX_MODE" -eq 1 && -z "$WORKTREE_VALUE" ]]; then
  echo "--tmux requires --worktree." >&2
  exit 1
fi

PROJECT_DIR="$(resolve_dir "$PROJECT_DIR")"
trace "resolved project_dir=$PROJECT_DIR"
SYSTEM_PROMPT_FILE="$(resolve_file "$SYSTEM_PROMPT_FILE")"
APPEND_SYSTEM_PROMPT_FILE="$(resolve_file "$APPEND_SYSTEM_PROMPT_FILE")"
SETTINGS_VALUE="$(resolve_path_or_json "$SETTINGS_VALUE")"

for i in "${!ADD_DIRS[@]}"; do
  ADD_DIRS[$i]="$(resolve_dir "${ADD_DIRS[$i]}")"
done

for i in "${!PLUGIN_DIRS[@]}"; do
  PLUGIN_DIRS[$i]="$(resolve_dir "${PLUGIN_DIRS[$i]}")"
done

for i in "${!MCP_CONFIGS[@]}"; do
  MCP_CONFIGS[$i]="$(resolve_path_or_json "${MCP_CONFIGS[$i]}")"
done

if [[ -z "$DEBUG_FILE" ]]; then
  DEBUG_FILE="${TMPDIR:-/tmp}/claude_osmen_$(date '+%Y%m%d_%H%M%S').log"
fi

if [[ "$OPENCODE_ONLY" -eq 0 && "$HOST_WINDOW" -eq 0 ]]; then
  run_update_if_needed "$DEBUG_FILE"
  choose_session_prompt
  choose_team_mode
fi

if [[ "$HOST_WINDOW" -eq 1 || "$CLAUDE_ONLY" -eq 1 || "$LAUNCH_TABS_INNER" -eq 1 ]]; then
  choose_session_prompt
  choose_team_mode
fi

trace "session_args=${SESSION_ARGS[*]} team_enabled=$TEAM_ENABLED host_window=$HOST_WINDOW launch_tabs=$LAUNCH_TABS"

read -r -d '' AGENTS_JSON <<'JSON' || true
{
  "osmen-config": {
    "description": "OsMEN configuration specialist for YAML config, service definitions, and runtime settings.",
    "prompt": "You are the OsMEN config specialist. Focus on safe configuration changes and validation. Do not edit secrets unless asked.",
    "model": "sonnet"
  },
  "siyuan-integration": {
    "description": "SiYuan PKM integration specialist for OsMEN.",
    "prompt": "You specialize in SiYuan PKM integration, metadata mapping, and safe note sync workflows.",
    "model": "sonnet"
  },
  "taskwarrior-sync": {
    "description": "Taskwarrior sync specialist for task ingestion and tagging.",
    "prompt": "You specialize in Taskwarrior sync rules, task ingestion, tagging, and daily briefing inputs.",
    "model": "sonnet"
  },
  "vector-query": {
    "description": "Vector memory specialist for ChromaDB and RAG queries.",
    "prompt": "You specialize in ChromaDB collection design, retrieval strategies, and RAG query tuning.",
    "model": "sonnet"
  },
  "@main": {
    "description": "Orchestrator for the OsMEN workspace",
    "prompt": "You are @main, the OsMEN orchestrator. Route work to specialists when that will improve speed or quality, then integrate their results.",
    "model": "opus"
  }
}
JSON

read -r -d '' THINKING_PROMPT <<'EOF' || true
THINKING PROTOCOL

VERTICAL: What is the exact state, all call sites, edge cases, and minimal safe change?
LATERAL: What adjacent systems, follow-on impacts, and reviewer questions matter here?
Document both analyses before making non-trivial changes.
EOF

APPEND_PROMPT=$(cat <<EOF
You are working in the OsMEN System workspace ($PROJECT_DIR).
Focus on local AI assistant architecture, SiYuan PKM integration,
Taskwarrior task management, and vector database operations.
Z.AI GLM integration active: opus=GLM-5.1, sonnet=GLM-4.7, haiku=GLM-4.7flashx.

$SESSION_PROMPT

$THINKING_PROMPT
EOF
)

export ANTHROPIC_DEFAULT_OPUS_MODEL="glm-5.1"
export ANTHROPIC_DEFAULT_SONNET_MODEL="glm-4.7"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="glm-4.7flashx"

if [[ "$TEAM_ENABLED" -eq 1 ]]; then
  export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
  export CLAUDE_MEDIA_TEAM_ORCHESTRATION=1
  trace "team orchestration enabled"
else
  export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0
  unset CLAUDE_MEDIA_TEAM_ORCHESTRATION || true
  trace "team orchestration disabled"
fi

declare -a CLAUDE_ARGS=(
  --append-system-prompt "$APPEND_PROMPT"
  --setting-sources "project,local,user"
  --permission-mode "$PERMISSION_MODE"
  --allow-dangerously-skip-permissions
  --debug-file "$DEBUG_FILE"
  --verbose
  --agent "@main"
  --agents "$AGENTS_JSON"
)

[[ -n "$SYSTEM_PROMPT" ]] && CLAUDE_ARGS+=(--system-prompt "$SYSTEM_PROMPT")
[[ -n "$SYSTEM_PROMPT_FILE" ]] && CLAUDE_ARGS+=(--system-prompt-file "$SYSTEM_PROMPT_FILE")
[[ -n "$APPEND_SYSTEM_PROMPT_FILE" ]] && CLAUDE_ARGS+=(--append-system-prompt-file "$APPEND_SYSTEM_PROMPT_FILE")
[[ -n "$EFFORT" ]] && CLAUDE_ARGS+=(--effort "$EFFORT")
[[ -n "$SESSION_NAME" ]] && CLAUDE_ARGS+=(--name "$SESSION_NAME")
[[ -n "$REMOTE_TASK" ]] && CLAUDE_ARGS+=(--remote "$REMOTE_TASK")
[[ "$REMOTE_CONTROL" -eq 1 ]] && CLAUDE_ARGS+=(--remote-control)
[[ -n "$REMOTE_CONTROL_NAME" ]] && CLAUDE_ARGS+=("$REMOTE_CONTROL_NAME")
[[ "$TELEPORT" -eq 1 ]] && CLAUDE_ARGS+=(--teleport)
[[ "$ENABLE_AUTO_MODE" -eq 1 ]] && CLAUDE_ARGS+=(--enable-auto-mode)
[[ "$IDE" -eq 1 ]] && CLAUDE_ARGS+=(--ide)
[[ "$CHROME" -eq 1 ]] && CLAUDE_ARGS+=(--chrome)
[[ "$NO_CHROME" -eq 1 ]] && CLAUDE_ARGS+=(--no-chrome)
[[ "$BRIEF" -eq 1 ]] && CLAUDE_ARGS+=(--brief)
[[ "$BARE" -eq 1 ]] && CLAUDE_ARGS+=(--bare)
[[ -n "$TEAMMATE_MODE" ]] && CLAUDE_ARGS+=(--teammate-mode "$TEAMMATE_MODE")
[[ "$STRICT_MCP_CONFIG" -eq 1 ]] && CLAUDE_ARGS+=(--strict-mcp-config)
[[ -n "$SETTINGS_VALUE" ]] && CLAUDE_ARGS+=(--settings "$SETTINGS_VALUE")
[[ -n "$TOOLS_VALUE" ]] && CLAUDE_ARGS+=(--tools "$TOOLS_VALUE")
[[ -n "$WORKTREE_VALUE" ]] && CLAUDE_ARGS+=(--worktree "$WORKTREE_VALUE")
[[ "$TMUX_MODE" -eq 1 ]] && CLAUDE_ARGS+=(--tmux)
[[ -n "$DEBUG_FILTER" ]] && CLAUDE_ARGS+=(--debug "$DEBUG_FILTER")
[[ "$DISABLE_SLASH_COMMANDS" -eq 1 ]] && CLAUDE_ARGS+=(--disable-slash-commands)
[[ "$INIT_MODE" -eq 1 ]] && CLAUDE_ARGS+=(--init)
[[ "$INIT_ONLY_MODE" -eq 1 ]] && CLAUDE_ARGS+=(--init-only)

for dir in "${ADD_DIRS[@]}"; do
  CLAUDE_ARGS+=(--add-dir "$dir")
done

for dir in "${PLUGIN_DIRS[@]}"; do
  CLAUDE_ARGS+=(--plugin-dir "$dir")
done

for cfg in "${MCP_CONFIGS[@]}"; do
  CLAUDE_ARGS+=(--mcp-config "$cfg")
done

for tool in "${ALLOWED_TOOLS[@]}"; do
  CLAUDE_ARGS+=(--allowedTools "$tool")
done

for tool in "${DISALLOWED_TOOLS[@]}"; do
  CLAUDE_ARGS+=(--disallowedTools "$tool")
done

CLAUDE_ARGS+=("${SESSION_ARGS[@]}")
CLAUDE_ARGS+=("${EXTRA_ARGS[@]}")

cd "$PROJECT_DIR"

OPENCODE_CMD="$(resolve_opencode_cmd || true)"

if [[ "$LAUNCH_TABS" -eq 1 ]]; then
  launch_tabs "$SCRIPT_PATH"
  exit 0
fi

if [[ "$OPENCODE_ONLY" -eq 1 ]]; then
  print_banner
  echo "Debug log: $DEBUG_FILE"
  echo "Trace log: $TRACE_FILE"
  echo "Node binary: $NODE_CMD"
  if [[ -n "$OPENCODE_CMD" ]]; then
    echo "OpenCode binary: $OPENCODE_CMD"
  else
    echo "OpenCode binary: not found"
  fi
  run_opencode_tab
fi

# --host-window is deprecated; treat it as claude-only
if [[ "$HOST_WINDOW" -eq 1 ]]; then
  trace "host-window mode deprecated, falling through to claude launcher"
fi

# --launch-tabs-inner: DEPRECATED — kept as fallback.
# The launch_tabs() function now uses background + sleep + --tab instead.
if [[ "$LAUNCH_TABS_INNER" -eq 1 ]]; then
  if [[ -n "$OPENCODE_CMD" ]] && command -v ptyxis >/dev/null 2>&1; then
    trace "WARN: launch-tabs-inner is deprecated, sleeping before opencode tab"
    sleep 1
    ptyxis --tab -d "$PROJECT_DIR" -T "OpenCode" -- "$SCRIPT_PATH" --opencode-only --project-dir "$PROJECT_DIR" &
    disown
  fi
fi

print_banner
echo "Debug log: $DEBUG_FILE"
echo "Trace log: $TRACE_FILE"
echo "Node binary: $NODE_CMD"
echo "Claude binary: $CLAUDE_CMD"
if [[ -n "$OPENCODE_CMD" ]]; then
  echo "OpenCode binary: $OPENCODE_CMD"
else
  echo "OpenCode binary: not found"
fi
echo "Launching model: $MODEL"
echo
trace "starting claude model=$MODEL args=${CLAUDE_ARGS[*]}"

set +e
"$CLAUDE_CMD" "${CLAUDE_ARGS[@]}" --model "$MODEL"
first_exit=$?
set -e
trace "claude exited code=$first_exit"

if [[ "$MODEL" == "opus" ]] && [[ -f "$DEBUG_FILE" ]]; then
  if grep -Eiq 'rate.?limit|overload|too many requests|429' "$DEBUG_FILE"; then
    echo
    echo "Detected an Opus overload. Relaunching on Sonnet..."
    exec "$CLAUDE_CMD" "${CLAUDE_ARGS[@]}" --model sonnet
  fi
fi

echo
echo "Claude session ended (exit code: $first_exit)."

echo "Terminal remains open - press Ctrl+D or type 'exit' to close."
exec bash
