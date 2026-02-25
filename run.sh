#!/bin/bash
# Source profiles for PATH + API keys (dcli/Dashlane)
export PATH="/opt/homebrew/bin:/usr/local/bin:/Users/julianmoncarz/.local/bin:$PATH"
# Try zprofile first (non-interactive), fall back to zshrc
source "$HOME/.zprofile" 2>/dev/null || true
source "$HOME/.zshrc" 2>/dev/null || true
set -a; source .env 2>/dev/null; set +a
open -gja Messages
exec uv run python src/main.py --tts --delay_time 60
