"""Benchmark vision models: gpt-5-nano vs Groq Llama 4 Scout vs Gemini 2.5 Flash-Lite.
All trials run in parallel. Saves all outputs."""
import time, sys, os, json, statistics
import concurrent.futures
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from utils import take_screenshots, encode_image_720p
import yaml

with open("src/config_prompts.yaml") as f:
    config = yaml.safe_load(f)

TRIALS = 3
USER_SPEC = "Working on code in VS Code. Procrastination = YouTube, Reddit, Twitter, social media."
USER_NAME = "User"

SYSTEM_PROMPT = config["system_prompt_combined"].format(user_name=USER_NAME)
USER_PROMPT = config["user_prompt_combined"].format(user_spec=USER_SPEC, user_name=USER_NAME)

SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "determination": {"type": "string", "enum": ["productive", "procrastinating"]},
        "heckler_message": {"type": "string"},
    },
    "required": ["reasoning", "determination", "heckler_message"],
    "additionalProperties": False,
}

# Gemini doesn't support additionalProperties
SCHEMA_GEMINI = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "determination": {"type": "string", "enum": ["productive", "procrastinating"]},
        "heckler_message": {"type": "string"},
    },
    "required": ["reasoning", "determination", "heckler_message"],
}

# Capture screenshot
print("Capturing screenshot...")
screenshots = take_screenshots()
fp = screenshots[0]["filepath"]
encoded_720p = encode_image_720p(fp)
print(f"  720p payload: {len(encoded_720p) // 1024}KB\n")


def trial_openai(model, b64):
    """Trial for OpenAI-compatible APIs (OpenAI, Groq)."""
    from openai import OpenAI

    if model.startswith("meta-llama"):
        client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
    else:
        client = OpenAI()

    img_obj = {"url": f"data:image/png;base64,{b64}"}

    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": USER_PROMPT},
                {"type": "image_url", "image_url": img_obj},
            ]},
        ],
        response_format={"type": "json_schema", "json_schema": {
            "name": "screen_check", "strict": True, "schema": SCHEMA,
        }},
        timeout=60,
    )
    elapsed = time.perf_counter() - t0
    content = json.loads(resp.choices[0].message.content)
    usage = resp.usage
    return {
        "time": elapsed,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "content": content,
    }


def trial_gemini(b64):
    """Trial for Gemini via google-genai SDK."""
    from google import genai
    from google.genai import types
    import base64 as b64_mod

    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

    image_bytes = b64_mod.b64decode(b64)

    t0 = time.perf_counter()
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            types.Content(role="user", parts=[
                types.Part(text=SYSTEM_PROMPT + "\n\n" + USER_PROMPT),
                types.Part(inline_data=types.Blob(mime_type="image/png", data=image_bytes)),
            ]),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SCHEMA_GEMINI,
        ),
    )
    elapsed = time.perf_counter() - t0

    content = json.loads(response.text)
    usage = response.usage_metadata
    return {
        "time": elapsed,
        "prompt_tokens": usage.prompt_token_count if usage else None,
        "completion_tokens": usage.candidates_token_count if usage else None,
        "content": content,
    }


# Define all models to test
models = {
    "gpt-5-nano (OpenAI)": lambda: trial_openai("gpt-5-nano", encoded_720p),
    "Llama 4 Scout (Groq)": lambda: trial_openai("meta-llama/llama-4-scout-17b-16e-instruct", encoded_720p),
    "Gemini 2.5 Flash-Lite": lambda: trial_gemini(encoded_720p),
}

# Check which APIs are available
available = {}
if os.environ.get("OPENAI_API_KEY"):
    available["gpt-5-nano (OpenAI)"] = models["gpt-5-nano (OpenAI)"]
else:
    print("SKIP: OPENAI_API_KEY not set")

if os.environ.get("GROQ_API_KEY"):
    available["Llama 4 Scout (Groq)"] = models["Llama 4 Scout (Groq)"]
else:
    print("SKIP: GROQ_API_KEY not set")

if os.environ.get("GOOGLE_API_KEY"):
    available["Gemini 2.5 Flash-Lite"] = models["Gemini 2.5 Flash-Lite"]
else:
    print("SKIP: GOOGLE_API_KEY not set")

if not available:
    print("ERROR: No API keys set. Need at least one of OPENAI_API_KEY, GROQ_API_KEY, GOOGLE_API_KEY")
    sys.exit(1)

# Fire ALL trials for ALL models in parallel
total_calls = len(available) * TRIALS
print(f"=== VISION MODEL BENCHMARK ({TRIALS} trials × {len(available)} models = {total_calls} calls, ALL parallel) ===\n")

all_futures = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=total_calls) as ex:
    for name, fn in available.items():
        all_futures[name] = [ex.submit(fn) for _ in range(TRIALS)]

    all_results = {}
    for name, futures in all_futures.items():
        results = []
        for i, f in enumerate(futures):
            try:
                r = f.result(timeout=120)
                results.append(r)
            except Exception as e:
                print(f"  ERROR: {name} trial {i+1}: {e}")
                results.append({"time": None, "error": str(e)})
        all_results[name] = results

# Print summary table
print(f"\n{'Model':<30} {'Median':>7} {'Mean':>7} {'Min':>7} {'Max':>7} {'Prompt':>7} {'Comp':>6}")
print("-" * 82)
for name in available:
    results = [r for r in all_results[name] if r.get("time") is not None]
    if not results:
        print(f"{name:<30} {'ERROR':>7}")
        continue
    times = [r["time"] for r in results]
    prompt_toks = [r["prompt_tokens"] for r in results if r.get("prompt_tokens")]
    comp_toks = [r["completion_tokens"] for r in results if r.get("completion_tokens")]
    print(f"{name:<30} {statistics.median(times):>6.2f}s {statistics.mean(times):>6.2f}s {min(times):>6.2f}s {max(times):>6.2f}s {int(statistics.mean(prompt_toks)):>7} {int(statistics.mean(comp_toks)):>6}")

# Print all responses
print("\n\n=== FULL RESPONSES ===\n")
for name in available:
    for i, r in enumerate(all_results[name]):
        if r.get("error"):
            print(f"--- {name} | Trial {i+1} | ERROR: {r['error']} ---\n")
            continue
        c = r["content"]
        print(f"--- {name} | Trial {i+1} | {r['time']:.2f}s | prompt={r.get('prompt_tokens')} comp={r.get('completion_tokens')} ---")
        print(f"  determination: {c.get('determination')}")
        print(f"  reasoning ({len(c.get('reasoning',''))} chars): {c.get('reasoning','')}")
        print(f"  heckler ({len(c.get('heckler_message',''))} chars): {c.get('heckler_message','')}")
        print()

os.remove(fp)
