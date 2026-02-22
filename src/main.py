
import time
import os
import sys
import json
import base64
import signal
import shutil
import yaml
import threading
import concurrent.futures
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from procrastination_event import ProcrastinationEvent
from utils import take_screenshots, get_text_to_speech, play_text_to_speech

# Validate config
_config_path = Path(__file__).parent / 'config_prompts.yaml'
if not _config_path.exists():
    print(f"Error: config file not found at {_config_path}", file=sys.stderr)
    sys.exit(1)
with open(_config_path, 'r') as file:
    config = yaml.safe_load(file)

_required_keys = {
    "system_prompt", "user_prompt",
    "system_prompt_heckler", "user_prompt_heckler",
    "system_prompt_pledge", "user_prompt_pledge",
    "system_prompt_countdown", "user_prompt_countdown",
}
_missing = _required_keys - set(config.keys())
if _missing:
    print(f"Error: config_prompts.yaml missing keys: {_missing}", file=sys.stderr)
    sys.exit(1)

# Validate API key
if not os.environ.get('OPENAI_API_KEY'):
    print("Error: OPENAI_API_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)
client = OpenAI()

API_TIMEOUT = 60
_shutdown = threading.Event()


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def determine_productivity(user_spec, image_filepaths):
    """Single API call with structured output to determine productive/procrastinating."""
    encoded_images = [encode_image(fp) for fp in image_filepaths]
    user_content = [
        {"type": "text", "text": config["user_prompt"].format(user_spec=user_spec)},
        *[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}} for img in encoded_images]
    ]

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": config["system_prompt"]},
            {"role": "user", "content": user_content}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "determination",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "determination": {
                            "type": "string",
                            "enum": ["productive", "procrastinating"]
                        }
                    },
                    "required": ["determination"],
                    "additionalProperties": False
                }
            }
        },
        timeout=API_TIMEOUT,
    )

    result = json.loads(response.choices[0].message.content)
    return result["determination"]


def make_api_call(role, user_prompt, system_prompt=None, image_paths=None):
    user_content = user_prompt
    if image_paths:
        encoded_images = [encode_image(fp) for fp in image_paths]
        user_content = [
            {"type": "text", "text": user_prompt},
            *[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}} for img in encoded_images]
        ]

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=messages,
        timeout=API_TIMEOUT,
    )
    return {"result": response.choices[0].message.content, "role": role}


def parallel_api_calls(api_params):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(make_api_call, p["role"], p["user_prompt"], p.get("system_prompt"), p.get("image_paths"))
            for p in api_params
        ]
        return [f.result(timeout=API_TIMEOUT * 2) for f in concurrent.futures.as_completed(futures, timeout=API_TIMEOUT * 2)]


def procrastination_sequence(user_spec, user_name, tts, voice, countdown_time, image_filepaths):
    api_params = [
        {"role": "heckler", "user_prompt": config["user_prompt_heckler"].format(user_spec=user_spec, user_name=user_name), "system_prompt": config["system_prompt_heckler"].format(user_name=user_name), "image_paths": image_filepaths},
        {"role": "countdown", "user_prompt": config["user_prompt_countdown"].format(user_spec=user_spec), "system_prompt": config["system_prompt_countdown"], "image_paths": image_filepaths}
    ]

    api_results = parallel_api_calls(api_params)

    heckler_message = countdown_message = ""
    for api_result in api_results:
        if api_result["role"] == "heckler":
            heckler_message = api_result["result"]
        elif api_result["role"] == "countdown":
            countdown_message = api_result["result"]

    if tts:
        try:
            voice_file = get_text_to_speech(heckler_message, voice)
            tts_thread = threading.Thread(target=play_text_to_speech, args=(voice_file,))
            tts_thread.start()
        except Exception as e:
            print(f"Warning: TTS failed, continuing without audio: {e}")

    procrastination_event = ProcrastinationEvent()
    procrastination_event.show_popup(heckler_message)
    procrastination_event.play_countdown(countdown_time, brief_message=f"You have {countdown_time} seconds to close {countdown_message.strip()}")

    return heckler_message, "", countdown_message.strip()


def process_one_cycle(user_spec, tts, voice, countdown_time, user_name, log_dir):
    """Run one screenshot-check-respond cycle. Returns the determination string."""
    screenshots = take_screenshots()
    filepaths = [shot["filepath"] for shot in screenshots]

    if not filepaths:
        print("Warning: No screenshots captured, skipping cycle.")
        return "skipped"

    try:
        determination = determine_productivity(user_spec, filepaths)
        print(f"Determination: {determination}")

        heckler_msg = pledge_msg = countdown_msg = None
        if determination == "procrastinating":
            heckler_msg, pledge_msg, countdown_msg = procrastination_sequence(
                user_spec, user_name, tts, voice, countdown_time, filepaths
            )
    finally:
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
    }
    if determination == "procrastinating":
        entry["heckler"] = heckler_msg
        entry["pledge"] = pledge_msg
        entry["countdown_word"] = countdown_msg
    with open(log_dir / "session.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")

    return determination


def main(tts=False, voice="Patrick", delay_time=0, initial_delay=0, countdown_time=15, user_name="Procrastinator"):
    os.makedirs(Path(__file__).parent.parent / "screenshots", exist_ok=True)

    log_dir = Path(__file__).parent.parent / "logs" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)

    user_spec = input()

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
