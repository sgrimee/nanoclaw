#!/bin/bash
# Auto-install tricount deps into persistent group venv on first use
VENV=/workspace/group/.venv
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! "$VENV/bin/python" -c "import httpx, cryptography" 2>/dev/null; then
  uv venv "$VENV" 2>/dev/null
  uv pip install --python "$VENV/bin/python" httpx cryptography >&2
fi

PYTHONPATH="$SKILL_DIR" "$VENV/bin/python" "$SKILL_DIR/tricount_cli.py" "$@"
