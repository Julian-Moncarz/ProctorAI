# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ProctorAI is a macOS-only multimodal AI productivity tool. It runs as a background daemon that periodically screenshots your screen, sends images to Gemini 2.5 Flash-Lite via the Google GenAI SDK, and intervenes with a full-screen Tkinter popup + optional TTS heckling when it detects you're off-task. Tasks are pulled automatically from a Notion database (filtered to "Must be done this week", not Done).

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
     c. _check_screen() → single Gemini API call → {determination, reasoning, heckler_message}
     d. If procrastinating → Tkinter popup + optional TTS + countdown
     e. Log to logs/<session>/session.jsonl

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

config_prompts.yaml
  - System/user prompts for the single-call screen check
```

## Key Design Details

- **No GUI**: runs headless as a daemon; Tkinter is only used for procrastination popups
- **Single API call**: determination + heckler message in one Gemini call (~1.5s per cycle)
- **Notion integration**: tasks auto-refresh from Notion every 10 minutes; no manual task entry
- **Audit logging**: each session saves screenshots + JSONL log to `logs/<timestamp>/`
- **Graceful shutdown**: handles SIGTERM/SIGINT via threading.Event
- **Platform**: macOS only (screencapture, PyObjC)

## Environment Variables

- `GOOGLE_API_KEY` (required) — Gemini API
- `NOTION_TOKEN` (required) — Notion integration token
- `ELEVEN_LABS_API_KEY` (required for TTS)
