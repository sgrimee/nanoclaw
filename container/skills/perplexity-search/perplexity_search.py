#!/usr/bin/env python3
"""Search the web using Perplexity AI's sonar models."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_MODEL = "sonar-pro"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def _load_env_file() -> None:
    """Load /workspace/env-dir/env into os.environ if it exists (fallback for Bash env gaps)."""
    env_file = "/workspace/env-dir/env"
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        pass


def get_api_key() -> str:
    _load_env_file()
    key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not key:
        print(
            "Error: PERPLEXITY_API_KEY not set. "
            "Add PERPLEXITY_API_KEY=pplx-... to groups/global/.env (shared) "
            "or your group's .env file.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def search(query: str, model: str, api_key: str) -> None:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": query}],
    }).encode("utf-8")

    req = urllib.request.Request(
        PERPLEXITY_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 401:
            print(
                "Error: Unauthorized (401). Check that PERPLEXITY_API_KEY is valid.",
                file=sys.stderr,
            )
        elif e.code == 429:
            print("Error: Rate limit exceeded (429). Wait a moment and try again.", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.code} — {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Network error — {e.reason}", file=sys.stderr)
        sys.exit(1)

    content = data["choices"][0]["message"]["content"]
    citations = data.get("citations", [])

    print(content)
    if citations:
        print("\nSources:")
        for i, url in enumerate(citations, 1):
            print(f"[{i}] {url}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="perplexity-search.sh",
        description="Search the web using Perplexity AI.",
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=["sonar", "sonar-pro", "sonar-reasoning"],
        help=f"Perplexity model (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    api_key = get_api_key()
    search(args.query, args.model, api_key)


if __name__ == "__main__":
    main()
