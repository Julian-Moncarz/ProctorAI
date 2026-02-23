#!/bin/bash
set -a; source .env 2>/dev/null; set +a
open -gja Messages
uv run python src/main.py --tts --delay_time 60
