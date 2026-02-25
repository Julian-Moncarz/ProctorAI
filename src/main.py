import time
import os
import sys
import json
import signal
import shutil
import yaml
import threading
import base64
from datetime import datetime
from pathlib import Path

import anthropic
from procrastination_event import ProcrastinationEvent
from utils import take_screenshots, encode_image_720p, get_text_to_speech, play_text_to_speech
from notion_tasks import get_weekly_tasks, format_task_list

# Validate config
_config_path = Path(__file__).parent / 'config_prompts.yaml'
if not _config_path.exists():
    print(f"Error: config file not found at {_config_path}", file=sys.stderr)
    sys.exit(1)
with open(_config_path, 'r') as file:
    config = yaml.safe_load(file)

# Validate API key
if not os.environ.get('ANTHROPIC_API_KEY'):
    print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)
client = anthropic.Anthropic()

_shutdown = threading.Event()

MEMORY_PATH = Path(__file__).parent.parent / "memory.md"


def _load_memory():
    """Load persistent memory file, return empty string if missing."""
    if MEMORY_PATH.exists():
        return MEMORY_PATH.read_text().strip()
    return "(No memory file found. Create memory.md in the project root to add preferences.)"


def _check_screen(user_spec, user_name, encoded_images):
    """Single API call: determine productivity and generate message if off-task."""
    memory = _load_memory()
    system_prompt = config["system_prompt"].format(user_name=user_name)
    user_prompt = config["user_prompt"].format(
        user_name=user_name, user_spec=user_spec, memory=memory
    )

    # Build content: text prompt + images
    content = [{"type": "text", "text": user_prompt}]
    for img in encoded_images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img},
        })

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
        tools=[{
            "name": "report",
            "description": "Report the productivity determination",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string", "description": "Brief reasoning about what you see on screen"},
                    "determination": {"type": "string", "enum": ["productive", "procrastinating"]},
                    "heckler_message": {"type": "string", "description": "Short punchy message (max 15 words) if procrastinating, empty string if productive"},
                },
                "required": ["reasoning", "determination", "heckler_message"],
            },
        }],
        tool_choice={"type": "tool", "name": "report"},
    )

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("No tool_use block in response")


def process_one_cycle(user_spec, tts, voice, countdown_time, user_name, log_dir):
    """Run one screenshot-check-respond cycle. Returns the determination string."""
    screenshots = take_screenshots()
    filepaths = [shot["filepath"] for shot in screenshots]

    if not filepaths:
        print("Warning: No screenshots captured, skipping cycle.")
        return "skipped"

    encoded_images = [encode_image_720p(fp) for fp in filepaths]
    result = _check_screen(user_spec, user_name, encoded_images)

    determination = result["determination"]
    reasoning = result["reasoning"]
    heckler_msg = result["heckler_message"]
    print(f"Determination: {determination} | Reasoning: {reasoning}")

    if determination == "procrastinating":
        # First detection: popup + TTS + shame texts (no window close yet)
        if tts:
            try:
                voice_file = get_text_to_speech(heckler_msg, voice)
                tts_thread = threading.Thread(target=play_text_to_speech, args=(voice_file,))
                tts_thread.start()
            except Exception as e:
                print(f"Warning: TTS failed, continuing without audio: {e}")

        ProcrastinationEvent().show_popup(heckler_msg)

        # Wait 10s, then recheck — only close window if STILL procrastinating
        print("Rechecking in 10 seconds...")
        time.sleep(10)
        recheck_screenshots = take_screenshots()
        recheck_filepaths = [s["filepath"] for s in recheck_screenshots]
        if recheck_filepaths:
            recheck_encoded = [encode_image_720p(fp) for fp in recheck_filepaths]
            recheck_result = _check_screen(user_spec, user_name, recheck_encoded)
            print(f"Recheck: {recheck_result['determination']} | {recheck_result['reasoning']}")
            if recheck_result["determination"] == "procrastinating":
                print("Still procrastinating — closing frontmost window.")
                import subprocess as _sp
                _sp.run(["osascript", "-e", '''
tell application "System Events"
    set frontApp to name of first application process whose frontmost is true
    tell application process frontApp
        try
            click menu item "Close Window" of menu "File" of menu bar 1
        on error
            try
                click menu item "Close Tab" of menu "File" of menu bar 1
            on error
                try
                    click menu item "Close" of menu "File" of menu bar 1
                end try
            end try
        end try
    end tell
end tell
'''])
            # Clean up recheck screenshots
            for fp in recheck_filepaths:
                try:
                    shutil.move(fp, log_dir / Path(fp).name)
                except OSError:
                    pass

    # Move screenshots to log dir
    saved_names = []
    for fp in filepaths:
        try:
            dest = log_dir / Path(fp).name
            shutil.move(fp, dest)
            saved_names.append(Path(fp).name)
        except OSError as e:
            print(f"Warning: could not move {fp} to log dir: {e}")

    # Append audit log entry
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "screenshots": saved_names,
        "determination": determination,
        "reasoning": reasoning,
    }
    if determination == "procrastinating":
        entry["heckler"] = heckler_msg
    with open(log_dir / "session.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")

    return determination


def main(tts=False, voice="Adam", delay_time=60, countdown_time=15, user_name="Julian"):
    os.makedirs(Path(__file__).parent.parent / "screenshots", exist_ok=True)

    log_dir = Path(__file__).parent.parent / "logs" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)

    tasks = get_weekly_tasks()
    user_spec = format_task_list(tasks)
    if not tasks:
        print("Warning: No 'Must be done this week' tasks found in Notion. Exiting.")
        sys.exit(0)
    print(f"Loaded {len(tasks)} weekly tasks from Notion:\n{user_spec}")

    # Log task spec at session start
    with open(log_dir / "session.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": datetime.now().isoformat(timespec="seconds"), "type": "session_start", "task_spec": user_spec}) + "\n")

    signal.signal(signal.SIGTERM, lambda *_: _shutdown.set())
    signal.signal(signal.SIGINT, lambda *_: _shutdown.set())

    while not _shutdown.is_set():
        try:
            # Refresh task list from Notion (cached, refreshes every 10 min)
            tasks = get_weekly_tasks()
            if tasks:
                user_spec = format_task_list(tasks)
            process_one_cycle(user_spec, tts, voice, countdown_time, user_name, log_dir)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in cycle: {e}")
            time.sleep(5)
            continue
        time.sleep(delay_time)

    print("Shutting down.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tts", help="Enable heckling", action="store_true")
    parser.add_argument("--voice", help="Set voice", default="Adam", type=str)
    parser.add_argument("--delay_time", help="Seconds between checks", default=60, type=int)
    parser.add_argument("--countdown_time", help="Set countdown time", default=15, type=int)
    parser.add_argument("--user_name", help="Set user name", default="Julian", type=str)

    args = parser.parse_args()
    main(tts=args.tts, voice=args.voice, delay_time=args.delay_time, countdown_time=args.countdown_time, user_name=args.user_name)
