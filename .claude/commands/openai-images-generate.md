# /openai-images-generate

OpenAI Images - Generate or edit with GPT Image / DALL·E

## Description

Generates an image from a prompt, edits one with an optional mask, or composes across
several inputs, using OpenAI's Images API (`gpt-image-2`, `gpt-image-1.5`, `dall-e-3`).

Reach for this over the other image skills when you need a transparent background, an
exact pixel size, or true masked inpainting.

## Usage

```bash
/openai-images-generate a flat vector maple leaf icon, transparent background
/openai-images-generate edit room.png so the sky is storm clouds
```

## Implementation

Runs `.claude/skills/openai-images/scripts/openai_image.py`:

```bash
S=.claude/skills/openai-images/scripts/openai_image.py
$S generate "<prompt>" -o out/image.png --size 1536x1024 --quality high
$S edit "<prompt>" -i input.png [--mask region.png] [--input-fidelity high] -o out/edit.png
$S models
```

Requires `OPENAI_API_KEY` (https://platform.openai.com/api-keys). GPT Image models need
organisation verification — a `403` usually means that, not a bad key.

## Notes

- Masks are alpha PNGs: **transparent pixels are what changes**, opaque pixels are kept
- `--background transparent` needs `--output-format png` or `webp`
- `--input-fidelity high` preserves faces, logos and fine detail from input images
- `gpt-image-2` takes arbitrary `WxH` sizes (divisible by 16, ratio 1:3–3:1, max 3840x2160)
- Pin `gpt-image-2-2026-04-21` (`-m pinned`) when output must not drift between runs
- Surface the finished file to the user and report the prompt used
