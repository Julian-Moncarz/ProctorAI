
import time
import os
import sys
import json
import signal
import shutil
import yaml
import threading
from datetime import datetime
from pathlib import Path

import base64 as b64_mod
from google import genai
from google.genai import types
from procrastination_event import ProcrastinationEvent
from utils import take_screenshots, encode_image_720p, get_text_to_speech, play_text_to_speech

# Validate config
_config_path = Path(__file__).parent / 'config_prompts.yaml'
if not _config_path.exists():
    print(f"Error: config file not found at {_config_path}", file=sys.stderr)
    sys.exit(1)
with open(_config_path, 'r') as file:
    config = yaml.safe_load(file)

_required_keys = {"system_prompt_combined", "user_prompt_combined"}
_missing = _required_keys - set(config.keys())
if _missing:
    print(f"Error: config_prompts.yaml missing keys: {_missing}", file=sys.stderr)
    sys.exit(1)

# Validate API key
if not os.environ.get('GOOGLE_API_KEY'):
    print("Error: GOOGLE_API_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)
client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])

API_TIMEOUT = 60
_shutdown = threading.Event()


_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "determination": {"type": "string", "enum": ["productive", "procrastinating"]},
        "heckler_message": {"type": "string"},
    },
    "required": ["reasoning", "determination", "heckler_message"],
}


def _check_screen(user_spec, user_name, encoded_images):
    """Single API call: determine productivity and generate heckler message if procrastinating."""
    image_parts = [
        types.Part(inline_data=types.Blob(mime_type="image/png", data=b64_mod.b64decode(img)))
        for img in encoded_images
    ]
    prompt = config["system_prompt_combined"].format(user_name=user_name) + "\n\n" + config["user_prompt_combined"].format(user_spec=user_spec, user_name=user_name)

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[types.Content(role="user", parts=[types.Part(text=prompt), *image_parts])],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
        ),
    )
    return json.loads(response.text)


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
        if tts:
            try:
                voice_file = get_text_to_speech(heckler_msg, voice)
                tts_thread = threading.Thread(target=play_text_to_speech, args=(voice_file,))
                tts_thread.start()
            except Exception as e:
                print(f"Warning: TTS failed, continuing without audio: {e}")

        procrastination_event = ProcrastinationEvent()
        procrastination_event.show_popup(heckler_msg)
        procrastination_event.play_countdown(countdown_time, brief_message=f"You have {countdown_time} seconds to get back to work")

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


def main(tts=False, voice="Patrick", delay_time=0, initial_delay=0, countdown_time=15, user_name="Procrastinator"):
    os.makedirs(Path(__file__).parent.parent / "screenshots", exist_ok=True)

    log_dir = Path(__file__).parent.parent / "logs" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)

    user_spec = input()

    # Log task spec at session start
    with open(log_dir / "session.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": datetime.now().isoformat(timespec="seconds"), "type": "session_start", "task_spec": user_spec}) + "\n")

    signal.signal(signal.SIGTERM, lambda *_: _shutdown.set())
    signal.signal(signal.SIGINT, lambda *_: _shutdown.set())

    time.sleep(initial_delay)

    while not _shutdown.is_set():
        try:
            process_one_cycle(user_spec, tts, voice, countdown_time, user_name, log_dir)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in cycle: {e}")
            time.sleep(5)  # back off on error
            continue
        time.sleep(delay_time)

    print("Shutting down.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tts", help="Enable heckling", action="store_true")
    parser.add_argument("--voice", help="Set voice", default="Patrick", type=str)
    parser.add_argument("--delay_time", help="Set delay time", default=0, type=int)
    parser.add_argument("--initial_delay", help="Initial delay so user can open relevant apps", default=0, type=int)
    parser.add_argument("--countdown_time", help="Set countdown time", default=15, type=int)
    parser.add_argument("--user_name", help="Set user name", default="Procrastinator", type=str)

    args = parser.parse_args()
    main(tts=args.tts, voice=args.voice, delay_time=args.delay_time, initial_delay=args.initial_delay, countdown_time=args.countdown_time, user_name=args.user_name)
