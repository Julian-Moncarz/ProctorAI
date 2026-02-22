from pathlib import Path
from datetime import datetime
import subprocess

from AppKit import NSScreen
import sounddevice as sd
import soundfile as sf
import requests
from pydub import AudioSegment
import os

_SRC_DIR = Path(__file__).parent
_PROJECT_DIR = _SRC_DIR.parent

xi_api_key = os.environ.get('ELEVEN_LABS_API_KEY')

VOICES = {
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Arnold": "VR6AewLTigWG4xSOukaG",
    "Emily": "LcfcDJNUP1GQjkzn1xUU",
    "Harry": "SOYHLrjzK2X1ezoPC6cr",
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Patrick": "ODq5zmih8GrVes37Dizd",
}


def get_number_of_screens():
    return len(NSScreen.screens())


def take_screenshots():
    """Takes screenshots of each monitor and returns a list of dicts with filepath and timestamp."""
    num_screens = get_number_of_screens()
    if num_screens == 0:
        print("Error: No screens detected.")
        return []

    screenshots_dir = _PROJECT_DIR / "screenshots"
    screenshots = []
    for screen in range(1, num_screens + 1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_filepath = screenshots_dir / f"screen_{screen}_{timestamp}.png"
        result = subprocess.run(
            ["screencapture", "-x", f"-D{screen}", str(save_filepath)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Warning: screencapture failed for display {screen}: {result.stderr}")
            continue
        if not save_filepath.exists():
            print(f"Warning: screenshot file not created for display {screen}")
            continue
        screenshots.append({"filepath": str(save_filepath), "timestamp": timestamp})
    return screenshots


def get_text_to_speech(text, voice="Harry"):
    if voice not in VOICES:
        raise ValueError(f"Unknown voice '{voice}'. Available: {list(VOICES.keys())}")

    CHUNK_SIZE = 1024
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICES[voice]}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": xi_api_key,
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
    }
    response = requests.post(url, json=data, headers=headers, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"Eleven Labs TTS failed (HTTP {response.status_code}): {response.text[:200]}")

    voice_path_mp3 = _SRC_DIR / "yell_voice.mp3"
    with open(voice_path_mp3, 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)

    voice_path_wav = _SRC_DIR / "yell_voice.wav"
    audio = AudioSegment.from_mp3(voice_path_mp3)
    audio.export(voice_path_wav, format="wav")
    return str(voice_path_wav)


def play_text_to_speech(voice_file):
    data, samplerate = sf.read(voice_file)
    sd.play(data, samplerate)
    sd.wait()
