#!/bin/zsh
# Wrapper for launchd — loads API keys from Dashlane vault, then runs ProctorAI
export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:/Users/julianmoncarz/.local/bin:$PATH"

_dcli_tmp=$(mktemp)
dcli note -o json 2>/dev/null > "$_dcli_tmp"
export ANTHROPIC_API_KEY=$(jq -r '.[] | select(.title=="ANTHROPIC_API_KEY") | .content' "$_dcli_tmp")
export ELEVEN_LABS_API_KEY=$(jq -r '.[] | select(.title=="ELEVEN_LABS_API_KEY") | .content' "$_dcli_tmp")
export NOTION_TOKEN=$(jq -r '.[] | select(.title=="NOTION_TOKEN") | .content' "$_dcli_tmp")
rm -f "$_dcli_tmp"

cd /Users/julianmoncarz/Projects/apps/ProctorAI
exec /Users/julianmoncarz/.local/bin/uv run python src/main.py --tts --delay_time 60
