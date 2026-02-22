# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ProctorAI is a macOS-only multimodal AI productivity tool. It periodically screenshots your screen, sends images to Gemini 2.5 Flash-Lite via the Google GenAI SDK, and intervenes with a full-screen popup when it detects procrastination. The user defines their task, allowed behaviors, and what counts as procrastination before each session.

## Running

```bash
./run.sh                    # Launch PyQt5 GUI (uses uv run)
uv run python src/main.py   # Direct CLI mode (reads task spec from stdin)
```

CLI flags: `--tts`, `--voice NAME`, `--delay_time N`, `--initial_delay N`, `--countdown_time N`, `--user_name NAME`

## Dependencies

Managed via `uv` with `pyproject.toml`. No requirements.txt.

```bash
uv sync                     # Install all dependencies
uv sync --group dev         # Include dev dependencies (pytest)
```

## Testing

```bash
uv run pytest               # Run all tests
```

Tests live in `tests/`. Uses pytest + pytest-mock.

## Architecture

```
user_interface.py (PyQt5 GUI)
  └→ spawns main.py as subprocess, pipes task spec via stdin

main.py (core loop)
  1. Read task spec from stdin
  2. Wait initial_delay, then loop:
     a. utils.take_screenshots() → macOS screencapture, all monitors
     b. encode_image_720p() → downsize to 720p for faster API calls
     c. _check_screen() → single Gemini API call returns determination + heckler message
     d. If procrastinating → show popup, play TTS, run countdown
     e. Log determination, reasoning + screenshots to logs/<session>/session.jsonl

procrastination_event.py (Tkinter)
  - Full-screen popup: shows heckler message (user closes manually)
  - Countdown timer window

utils.py
  - take_screenshots(): macOS `screencapture` command
  - encode_image_720p(): downsize screenshots for faster API calls
  - TTS via Eleven Labs API, playback via sounddevice

config_prompts.yaml
  - Combined system/user prompts for single-call screen check
```

## Key Design Details

- **Two GUI frameworks**: PyQt5 for main app, Tkinter for procrastination popup (separate process context)
- **Single API call**: determination + heckler message in one Gemini call (~1.5s per cycle)
- **Audit logging**: each session saves screenshots and a JSONL log to `logs/<timestamp>/` (includes task spec, determination reasoning)
- **Settings persistence**: `settings.json` (gitignored, created at runtime)
- **Platform**: macOS only (screencapture, PyObjC)

## Environment Variables

- `GOOGLE_API_KEY` (required)
- `ELEVEN_LABS_API_KEY` (required for TTS feature)
