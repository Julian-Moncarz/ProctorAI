# ProctorAI

Forked and updated for personal use

## 🔍 Overview
ProctorAI is a multimodal AI that watches your screen and calls you out if it sees you procrastinating. Proctor works by taking screenshots of your computer every few seconds (at a specified interval) and feeding them into Google's Gemini 2.5 Flash-Lite. If ProctorAI determines that you are not focused, it will take control of your screen and yell at you with a personalized message, then give you 15 seconds to close the source of procrastination or will continue to bug you.

**Why Gemini 2.5 Flash-Lite?** We benchmarked gpt-5-nano, Groq Llama 4 Scout, and Gemini 2.5 Flash-Lite. Gemini gives us ~1.5s per-cycle latency (down from ~23s on gpt-5-nano) at the lowest cost ($0.10/$0.40 per 1M tokens) — cheap enough to run checks every couple of seconds. Screenshots are downsized to 720p before sending, which we verified preserves all text readability (window titles, URLs, tab names) while cutting payload size by 6x.

## 🚀 Setup and Installation
To start the GUI, just type ./run.sh. You might get some popups asking to allow terminal access to certain utilities, which you should enable. The current implementation requires macOS.

```
git clone https://github.com/jam3scampbell/ProctorAI
cd ProctorAI
uv sync
./run.sh
```

You need the following environment variables:
- `GOOGLE_API_KEY` (required — get one free at https://aistudio.google.com/apikey)
- `ELEVEN_LABS_API_KEY` (required for TTS feature)

## 🔁 Auto-Start on Login (macOS)

ProctorAI will launch automatically on login and **respawn if killed** (`KeepAlive` is enabled). You can't escape it until you unload the agent.

**Prerequisites:**
- Run `uv sync` first to install dependencies
- Grant **Screen Recording** permission to Terminal (or whichever app launches it) in System Settings > Privacy & Security > Screen Recording — otherwise screenshots will be blank

**Steps:**

1. Create the LaunchAgents directory (if it doesn't exist) and copy the plist:
```bash
mkdir -p ~/Library/LaunchAgents
cp com.proctorai.plist ~/Library/LaunchAgents/com.proctorai.plist
```

2. Edit `~/Library/LaunchAgents/com.proctorai.plist` and replace:
   - `PROCTORAI_PATH` with the absolute path to your ProctorAI directory (e.g. `/Users/you/ProctorAI`)
   - `HOME_DIR` with your home directory (e.g. `/Users/you`) — needed so launchd can find `uv`
   - `YOUR_GOOGLE_API_KEY` and `YOUR_ELEVEN_LABS_API_KEY` with your actual API keys

3. Load the agent:
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.proctorai.plist
```

The GUI will now appear on every login and respawn if killed. To stop:
```bash
launchctl bootout gui/$(id -u)/com.proctorai
```

## ⚙️ Options/Settings
The following can all be toggled in the settings page or used as CLI flags to `main.py`:
| | |
|------------------|---------------------------------------------------------------------------------------------------------|
| `tts`            | Enable Eleven Labs text-to-speech                                                           |
| `voice`          | Select the voice of Eleven Labs speaker                                                               |
| `delay_time`     | The amount of time between each screenshot                                                                   |
| `initial_delay`  | The amount of time to wait before Proctor starts watching your screen (useful for giving you time to open what you want to work on)                                                            |
| `countdown_time` | The amount of time Proctor gives to close the source of procrastination                                                            |
| `user_name`      | Enter your name to make the experience more personalized                                                       |


## 🎯 Understanding This Repository

Right now, basically all functionality is contained in the following files:
- `src/main.py`: contains the main control loop that takes screenshots, calls the model, and initiates procrastination events
- `src/user_interface.py`: runs the GUI written in PyQt5
- `src/procrastination_event.py`: displays the full-screen popup when the user is caught procrastinating and the countdown timer
- `src/utils.py`: functions for taking screenshots, tts, etc
- `src/config_prompts.yaml`: all prompts used in the LLM scaffolded system

As the program runs, it'll create a `settings.json` file, a `screenshots` folder, and a `logs/` directory (with per-session timestamped subdirectories containing archived screenshots and a `session.jsonl` audit log). If TTS is enabled, it'll also write `yell_voice.mp3` to the `src` folder.

## 🧪 Testing

```bash
uv run pytest
```

Tests live in `tests/`.

## 🌐 Roadmap and Future Improvements
This project is still very much under active development. Some features I'm hoping to add next:
- finetuning a LLaVA model specifically for the task/distribution
- scheduling sessions, have it start running when you open your computer
- make it extremely annoying to quit the program (at least until the user finishes their pre-defined session)
- ~~logging, time-tracking, & summary statistics~~ (basic audit logging added)
- summary statistics dashboard
- improve chat feature and give model greater awareness of state/context
- having a drafts folder for prompts so you don't have to re-type it out if you're doing the same task as you were the other day
- mute all other sounds on computer when the TTS plays (so it isn't drowned out by music)
