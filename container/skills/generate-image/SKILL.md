---
name: generate-image
description: Generate images from text prompts using HuggingFace FLUX. Returns a file path to the generated PNG.
allowed-tools: Bash(generate-image:*)
---

# Generate Image

Create images from text prompts using the HuggingFace Inference API (FLUX.1-schnell by default).

Requires `HF_TOKEN` in `data/env/env`. Get one at https://huggingface.co/settings/tokens — create a fine-grained token with "Make calls to Inference Providers" permission.

## Quick start

Generate an image and send it:

```bash
img=$(generate-image.sh "a cat wearing a top hat")
mcp__nanoclaw__send_message(text="Here you go!", image_path="$img")
```

## Options

```bash
generate-image.sh "prompt"                          # default model (FLUX.1-schnell)
generate-image.sh "prompt" --model black-forest-labs/FLUX.1-dev   # higher quality, slower
generate-image.sh "prompt" --output /tmp/my-image.png             # custom output path
```

## Models

| Model | Quality | Speed |
|-------|---------|-------|
| `black-forest-labs/FLUX.1-schnell` (default) | High | Fast (~4 steps) |
| `black-forest-labs/FLUX.1-dev` | Higher | Slower |

## Notes

- Output is always a PNG file under `/tmp/`
- First call may take ~20s for model warm-up (503 = loading, the script retries automatically)
- Subsequent calls on the same model are much faster
- The script prints the output file path to stdout on success
