# Ptyxis Launcher Handoff — 2026-04-11 20:14 UTC

## Task

Fix the OsMEN app-drawer launcher so clicking it opens exactly **ONE Ptyxis terminal window** with **TWO tabs**: Claude Code (tab 1) and OpenCode (tab 2). No blank tabs, no extra windows.

## Current Symptom (latest live test)

Three windows appear:
1. A blank terminal window
2. A window with 2 tabs: OpenCode (functional) + 1 blank tab
3. A window with Claude (functional)

Both Claude and OpenCode are alive and working — the only problem is window/tab placement.

## Trace from Latest Launch

File: `/tmp/claude_osmen_launcher_20260411_201438.log`

```
launch-tabs (pid 198075)  → exec ptyxis --new-window -- script --launch-tabs-inner
launch-tabs-inner (pid 198171) → fires ptyxis --tab for OpenCode, then runs Claude
opencode-only (pid 198214) → starts opencode (functional)
```

The `launch-tabs-inner` mode fires `ptyxis --tab` from inside the new window, but the tab still lands in the wrong place because Ptyxis hasn't transferred focus to the new window yet.

## Root Cause (proven)

`ptyxis --tab` ALWAYS targets whichever Ptyxis window currently has focus. When the script `exec`s into a new Ptyxis window and immediately fires `ptyxis --tab` from inside it, that window hasn't received focus yet. The tab lands in whatever was previously focused.

## What Works (proven manually)

This exact sequence, typed from a terminal, reliably produces 1 window with 2 tabs:

```bash
ptyxis --new-window -T "Tab1" -- bash -c 'echo TAB1; sleep 300' &
sleep 0.5
ptyxis --tab -T "Tab2" -- bash -c 'echo TAB2; sleep 300' &
```

The 0.5s sleep gives Ptyxis time to create+focus the new window before `--tab` fires. User confirmed: **1 window, 2 tabs, no blanks.**

## Why the Script Can't Use That Pattern

The script currently uses `exec ptyxis --new-window -- script --launch-tabs-inner` which **replaces the shell process** with ptyxis. There's no "outside" process left to sleep 0.5s and fire `--tab`.

An earlier attempt tried:
```bash
ptyxis --new-window -- script --claude-only &
sleep 0.5
ptyxis --tab -- script --opencode-only &
```
This failed because when the user already has OTHER Ptyxis windows open, the `--tab` targeted one of those instead of the new one.

## Key Files

| File | Path | Lines |
|------|------|-------|
| Launcher script | `/home/dwill/dev/OsMEN-OC/scripts/appdrawer/start-claude-osmen.sh` | 1023 |
| Desktop entry (repo) | `/home/dwill/dev/OsMEN-OC/scripts/appdrawer/claude-osmen.desktop` | 10 |
| Desktop entry (installed) | `/home/dwill/.local/share/applications/claude-osmen.desktop` | 10 |
| Latest trace log | `/tmp/claude_osmen_launcher_20260411_201438.log` | — |
| OpenCode config | `/home/dwill/.config/opencode/opencode.json` | — |

## Script Architecture (current, 5 modes)

| Mode flag | What it does |
|-----------|-------------|
| `--launch-tabs` | Outer entry: `exec ptyxis --new-window -- script --launch-tabs-inner <passthrough-args>` |
| `--launch-tabs-inner` | Inside new window: fires `ptyxis --tab` for OpenCode, then falls through to Claude |
| `--claude-only` | Runs Claude CLI with all configured args (team, agents, model, etc.) |
| `--opencode-only` | Runs OpenCode CLI (no special flags, holds terminal after exit) |
| *(none)* | Standalone Claude launcher with banner |

Desktop entry calls: `start-claude-osmen.sh --launch-tabs --project-dir /home/dwill/dev`

## Environment

| Item | Value |
|------|-------|
| OS | Ubuntu 26.04 LTS, Wayland, GNOME |
| Terminal | Ptyxis (GNOME default) |
| Ptyxis CLI flags | `--new-window`, `--tab`, `--tab-with-profile UUID`, `-d DIR`, `-T TITLE`, `-x CMD`, `-- CMD` |
| Ptyxis D-Bus | `org.gnome.Ptyxis` at `/org/gnome/Ptyxis`. Actions: `new-window`, `new-tab`. **NO per-window object paths. NO way to target a specific window.** |
| Window tools | **No wmctrl, no xdotool** (Wayland). Only `gdbus` available. |
| Claude CLI | `/home/dwill/.local/bin/claude` — Node.js wrapper, v2.1.101 |
| OpenCode CLI | `/home/dwill/.local/bin/opencode` — Node.js wrapper, v1.4.3 |
| Node.js | `/home/linuxbrew/.linuxbrew/bin/node` (Homebrew). **NOT in default GUI PATH.** |
| User | `dwill` on `Ubu-OsMEN` |
| Workspace | `/home/dwill/dev` |
| Repo branch | `install/fresh-setup-20260407` |

## Hard Constraints

- **NO `--dangerously-skip-permissions` for OpenCode** — that flag doesn't exist, causes exit code 1
- **NO Docker** — Podman only per project rules
- **NO interactive prompts** in the launcher (removed intentionally, defaults: teams ON, no resume prompt)
- `Terminal=false` in the desktop entry — the script manages its own terminal
- Must work from GNOME app drawer (minimal PATH, no login shell)
- Keep the existing `--claude-only` and `--opencode-only` modes working for standalone use

## Approaches to Consider

### 1. `ptyxis --standalone` + immediate `--tab`
`ptyxis -s --new-window -- claude-cmd` starts a **new Ptyxis instance** (not D-Bus activated). This new instance might be the only one where `--tab` can target. But then `--tab` might try to D-Bus activate the main instance instead.

### 2. Wrapper script that manages focus timing
A small wrapper that:
1. Does `ptyxis --new-window -T "Claude OSMEN" &` (no command = blank default shell)
2. Sleeps 0.5s
3. `ptyxis --tab -T "OpenCode" -- script --opencode-only`
4. In the original blank tab, it somehow gets replaced with Claude
Problem: no way to send a command to the already-open blank tab.

### 3. tmux inside one Ptyxis window
Open one Ptyxis window running tmux with two panes:
```bash
ptyxis --new-window -- tmux new-session -d -s osmen 'script --claude-only' \; split-window -h 'script --opencode-only' \; attach
```
Avoids Ptyxis tab-targeting entirely. Downside: tmux inside ptyxis is a different UX.

### 4. D-Bus introspection for tab creation
```bash
gdbus introspect --session --dest org.gnome.Ptyxis --object-path /org/gnome/Ptyxis
```
There may be a `new-tab` action that accepts a window identifier. Worth investigating.

### 5. Single-process approach
The script runs as Claude, and spawns OpenCode in a background tmux/screen session. Only one Ptyxis tab needed. User switches to OpenCode via tmux keybind. Simplest architecturally.

### 6. Profile-based approach
Create a Ptyxis profile that auto-runs OpenCode, then use `--tab-with-profile UUID`. Requires one-time profile setup.

## What NOT To Do

- Don't add `--dangerously-skip-permissions` to the OpenCode invocation
- Don't add interactive `read` prompts
- Don't create Docker/compose files
- Don't try `xdotool` or `wmctrl` (Wayland, not available)
- Don't assume `ptyxis --tab` will target a specific window — it won't
