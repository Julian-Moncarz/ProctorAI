
import time
import os
import base64
import yaml
import threading
import concurrent.futures

from openai import OpenAI
from procrastination_event import ProcrastinationEvent
from utils import take_screenshots, get_text_to_speech, play_text_to_speech


with open(os.path.dirname(__file__)+'/config_prompts.yaml', 'r') as file:
    config = yaml.safe_load(file)

client = OpenAI()


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
        }
    )

    import json
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
    )
    return {"result": response.choices[0].message.content, "role": role}


def parallel_api_calls(api_params):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(make_api_call, p["role"], p["user_prompt"], p.get("system_prompt"), p.get("image_paths"))
            for p in api_params
        ]
        return [f.result() for f in concurrent.futures.as_completed(futures)]


def procrastination_sequence(user_spec, user_name, tts, voice, countdown_time, image_filepaths):
    api_params = [
        {"role": "heckler", "user_prompt": config["user_prompt_heckler"].format(user_spec=user_spec, user_name=user_name), "system_prompt": config["system_prompt_heckler"].format(user_name=user_name), "image_paths": image_filepaths},
        {"role": "pledge", "user_prompt": config["user_prompt_pledge"].format(user_spec=user_spec, user_name=user_name), "system_prompt": config["system_prompt_pledge"], "image_paths": image_filepaths},
        {"role": "countdown", "user_prompt": config["user_prompt_countdown"].format(user_spec=user_spec), "system_prompt": config["system_prompt_countdown"], "image_paths": image_filepaths}
    ]

    api_results = parallel_api_calls(api_params)

    heckler_message = pledge_message = countdown_message = ""
    for api_result in api_results:
        if api_result["role"] == "heckler":
            heckler_message = api_result["result"]
        elif api_result["role"] == "pledge":
            pledge_message = api_result["result"]
        elif api_result["role"] == "countdown":
            countdown_message = api_result["result"]

    if tts:
        voice_file = get_text_to_speech(heckler_message, voice)
        tts_thread = threading.Thread(target=play_text_to_speech, args=(voice_file,))
        tts_thread.start()

    procrastination_event = ProcrastinationEvent()
    procrastination_event.show_popup(heckler_message, pledge_message)
    procrastination_event.play_countdown(countdown_time, brief_message=f"You have {countdown_time} seconds to close " + countdown_message.strip())


def main(tts=False, voice="Patrick", delay_time=0, initial_delay=0, countdown_time=15, user_name="Procrastinator"):
    os.makedirs(os.path.dirname(os.path.dirname(__file__)) + "/screenshots", exist_ok=True)

    user_spec = input()

    time.sleep(initial_delay)

    while True:
        screenshots = take_screenshots()
        filepaths = [shot["filepath"] for shot in screenshots]

        determination = determine_productivity(user_spec, filepaths)
        print(f"Determination: {determination}")

        if determination == "procrastinating":
            procrastination_sequence(user_spec, user_name, tts, voice, countdown_time, filepaths)

        # Delete screenshots after use
        for fp in filepaths:
            try:
                os.remove(fp)
            except OSError:
                pass

        time.sleep(delay_time)


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
