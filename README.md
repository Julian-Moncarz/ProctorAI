# ProctorAI

Forked and updated for personal use

## 🔍 Overview
ProctorAI is a multimodal AI that watches your screen and calls you out if it sees you procrastinating. Proctor works by taking screenshots of your computer every few seconds (at a specified interval) and feeding them into OpenAI's gpt-5-nano. If ProctorAI determines that you are not focused, it will take control of your screen and yell at you with a personalized message. After making you pledge to stop procrastinating, ProctorAI will then give you 15 seconds to close the source of procrastination or will continue to bug you.

## 🚀 Setup and Installation
To start the GUI, just type ./run.sh. You might get some popups asking to allow terminal access to certain utilities, which you should enable. The current implementation requires macOS.

```
git clone https://github.com/jam3scampbell/ProctorAI
cd ProctorAI
uv sync
./run.sh
```

You need the following environment variables:
- `OPENAI_API_KEY` (required)
- `ELEVEN_LABS_API_KEY` (required for TTS feature)

## 🔁 Auto-Start on Login (macOS)

To have ProctorAI launch automatically when you log in:

1. Copy the included plist template and fill in your paths/keys:
```bash
cp com.proctorai.plist ~/Library/LaunchAgents/com.proctorai.plist
```

2. Edit `~/Library/LaunchAgents/com.proctorai.plist` and replace:
   - `PROCTORAI_PATH` with the absolute path to your ProctorAI directory (e.g. `/Users/you/ProctorAI`)
   - `YOUR_OPENAI_API_KEY` and `YOUR_ELEVEN_LABS_API_KEY` with your actual API keys

3. Load the agent:
```bash
launchctl load ~/Library/LaunchAgents/com.proctorai.plist
```

The GUI will now appear on every login. To stop auto-starting:
```bash
launchctl unload ~/Library/LaunchAgents/com.proctorai.plist
```
