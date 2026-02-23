# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ProctorAI is a macOS-only multimodal AI productivity tool. It runs as a background daemon that periodically screenshots your screen, sends images to Claude Haiku 4.5 via the Anthropic SDK, and intervenes with a full-screen Tkinter popup + optional TTS heckling when it detects you're off-task. Tasks are pulled automatically from a Notion database (filtered to "Must be done this week", not Done).

## Running

```bash
./run.sh                    # Launch with TTS, 60s delay (uses uv run)
uv run python src/main.py   # Direct run, no TTS
```

CLI flags: `--tts`, `--voice NAME`, `--delay_time N`, `--countdown_time N`, `--user_name NAME`

## Dependencies

Managed via `uv` with `pyproject.toml`. No requirements.txt.

```bash
uv sync                     # Install all dependencies
uv sync --group dev         # Include dev dependencies (pytest)
```

## Testing

```bash
uv run pytest               # Run all tests
uv run pytest tests/test_cycle.py -k "test_name"  # Single test
```

Tests live in `tests/`. Uses pytest + pytest-mock.

## Architecture

```
main.py (core loop)
  1. Fetch weekly tasks from Notion via notion_tasks.py (cached 10min)
  2. Loop every delay_time seconds:
     a. take_screenshots() → macOS screencapture, all monitors
     b. encode_image_720p() → downsize for faster API calls
     c. _check_screen() → Claude Haiku 4.5 API call (tool_use) → {determination, reasoning, heckler_message}
     d. Loads memory.md each cycle for preferences/rules
     e. If procrastinating → Tkinter popup + optional TTS + countdown
     f. Log to logs/<session>/session.jsonl

notion_tasks.py
  - Queries Notion API for tasks with Timing="Must be done this week" and Status≠Done
  - 10-minute in-memory cache

procrastination_event.py (Tkinter)
  - Full-screen popup with heckler message
  - Countdown timer window

utils.py
  - take_screenshots(): macOS `screencapture` command
  - encode_image_720p(): downsize to 720p
  - TTS via Eleven Labs API, playback via sounddevice

memory.md (gitignored)
  - Persistent memory: user preferences, behavior rules, corrections
  - All prompt logic lives here — edit to change ProctorAI's behavior
  - Raycast script (edit-proctor-memory.sh) opens it quickly

config_prompts.yaml
  - Minimal system/user prompts that point to memory.md for rules
```

## Key Design Details

- **No GUI**: runs headless as a daemon; Tkinter is only used for procrastination popups
- **Single API call**: determination + heckler message via Claude tool_use (~1-2s per cycle)
- **Notion integration**: tasks auto-refresh from Notion every 10 minutes; no manual task entry
- **Persistent memory**: memory.md is loaded every cycle, edit to change behavior/rules
- **Audit logging**: each session saves screenshots + JSONL log to `logs/<timestamp>/`
- **Graceful shutdown**: handles SIGTERM/SIGINT via threading.Event
- **Platform**: macOS only (screencapture, PyObjC)

## Environment Variables

- `ANTHROPIC_API_KEY` (required) — Claude API
- `NOTION_TOKEN` (required) — Notion integration token
- `ELEVEN_LABS_API_KEY` (required for TTS)
