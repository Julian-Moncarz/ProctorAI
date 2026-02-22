import sys
import os
from unittest.mock import MagicMock

# Mock modules that aren't installed or are heavy/platform-specific in test env
for mod_name in ["cv2", "AppKit", "audioop", "pyaudioop"]:
    sys.modules.setdefault(mod_name, MagicMock())

# Set a dummy API key so OpenAI() doesn't fail at import time
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")

# Add src/ to path so we can import modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest


@pytest.fixture
def fake_image(tmp_path):
    """Create a tiny valid PNG file for testing."""
    import base64
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
        "nGP4z8BQDwAEgAF/pooBPQAAAABJRU5ErkJggg=="
    )
    img_path = tmp_path / "test_screen.png"
    img_path.write_bytes(png_data)
    return str(img_path)


