#!/usr/bin/env python3
"""Generate images from text prompts using HuggingFace Inference API."""

import argparse
import os
import sys
import time
import urllib.error
import urllib.request
import json

DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
HF_API_BASE = "https://router.huggingface.co/hf-inference/models"


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


def get_token() -> str:
    _load_env_file()
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print(
            "Error: HF_TOKEN not set. "
            "Add HF_TOKEN=hf_... to your group's .env file and restart nanoclaw. "
            "Get a token at https://huggingface.co/settings/tokens "
            "(create a fine-grained token with 'Make calls to Inference Providers' permission).",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def generate(prompt: str, model: str, output_path: str, token: str) -> None:
    url = f"{HF_API_BASE}/{model}"
    payload = json.dumps({"inputs": prompt}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "image/png",
    }

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                image_bytes = resp.read()
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 503:
                if attempt < max_retries:
                    wait = 20 * attempt
                    print(
                        f"Model is loading (503), retrying in {wait}s... (attempt {attempt}/{max_retries})",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    continue
                print(
                    f"Error: Model still loading after {max_retries} attempts. "
                    "Try again in a minute.",
                    file=sys.stderr,
                )
                sys.exit(1)
            elif e.code == 429:
                print(
                    "Error: Rate limit exceeded (429). Wait a moment and try again.",
                    file=sys.stderr,
                )
                sys.exit(1)
            elif e.code == 401:
                print(
                    "Error: Unauthorized (401). Check that HF_TOKEN is valid and has "
                    "'Make calls to Inference Providers' permission.",
                    file=sys.stderr,
                )
                sys.exit(1)
            else:
                print(f"Error: HTTP {e.code} — {body}", file=sys.stderr)
                sys.exit(1)
        except urllib.error.URLError as e:
            print(f"Error: Network error — {e.reason}", file=sys.stderr)
            sys.exit(1)

    with open(output_path, "wb") as f:
        f.write(image_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="generate-image.sh",
        description="Generate an image from a text prompt using HuggingFace Inference API.",
    )
    parser.add_argument("prompt", help="Text description of the image to generate")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"HuggingFace model ID (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: /tmp/generated-<timestamp>.png)",
    )
    args = parser.parse_args()

    token = get_token()

    output_path = args.output or f"/tmp/generated-{int(time.time())}.png"

    generate(args.prompt, args.model, output_path, token)
    print(output_path)


if __name__ == "__main__":
    main()
