#!/bin/bash
# Auto-install music-assistant-client into a persistent group venv on first use
VENV="/workspace/group/.venv/music-assistant"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$VENV" ]; then
  uv venv "$VENV" 2>/dev/null
fi

if [ ! -f "$VENV/.installed" ]; then
  uv pip install --python "$VENV/bin/python" music-assistant-client >&2
  touch "$VENV/.installed"
fi

exec "$VENV/bin/python" "$SCRIPT_DIR/music_cli.py" "$@"
