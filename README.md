# ProctorAI👁️
## 🔍 Overview
ProctorAI is a multimodal AI that watches your screen and calls you out if it sees you procrastinating. Proctor works by taking screenshots of your computer every few seconds (at a specified interval) and feeding them into OpenAI's gpt-5-nano. If ProctorAI determines that you are not focused, it will take control of your screen and yell at you with a personalized message. After making you pledge to stop procrastinating, ProctorAI will then give you 15 seconds to close the source of procrastination or will continue to bug you.

<p align="center">
  <img src="./assets/demo.gif" alt="Project demo" width="400">
</p>

***An intelligent system that knows what does and doesn't count as procrastination.*** Compared to traditional site blockers, ProctorAI is *intelligent* and capable of understanding nuanced workflows. *This makes a big difference*. Before every Proctor session, the user types out their session specification, where they explicitly tell Proctor what they're planning to work on, what behaviors are allowed during the session, and what behaviors are not allowed. Thus, Proctor can handle nuanced rules such as "I'm allowed to go on YouTube, but only to watch Karpathy's lecture on Makemore". No other productivity software can handle this level of flexibility.

<p align="center">
  <img src="./assets/slap.png" alt="Description of the image" width="350">
</p>
<p align="center" style="color: gray; font-size: 11px;">
  ProctorAI aims to be this woman, but available all the time, snarkier, and with full context of your work.
</p>

***It's alive!*** A big design goal with Proctor is that it should *feel alive*. In my experience, I tend not to break the rules because I can intuitively *feel* the AI watching me--just like how test-takers are much less likely to cheat when they can *feel* the proctor of an exam watching them.

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
- `src/procrastination_event.py`: contains methods for displaying the popup when the user is caught procrastinating as well as the timer telling the user to leave what they were doing
- `src/utils.py`: functions for taking screenshots, tts, etc
- `src/config_prompts.yaml`: all prompts used in the LLM scaffolded system

As the program runs, it'll create a `settings.json` file and a `screenshots` folder in the root directory. If TTS is enabled, it'll also write `yell_voice.mp3` to the `src` folder.

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
- logging, time-tracking, & summary statistics
- improve chat feature and give model greater awareness of state/context
- having a drafts folder for prompts so you don't have to re-type it out if you're doing the same task as you were the other day
- mute all other sounds on computer when the TTS plays (so it isn't drowned out by music)
