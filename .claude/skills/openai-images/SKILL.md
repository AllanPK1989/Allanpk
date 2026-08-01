---
name: openai-images
description: Image generation and editing with OpenAI's Images API - DALL-E 2, DALL-E 3, and the GPT Image models (gpt-image-2, gpt-image-1.5, gpt-image-1, gpt-image-1-mini). Use this skill when asked to generate, create, edit, inpaint, mask, or produce variations of an image with DALL-E, GPT Image, or the OpenAI API; when an image needs a transparent background, an exact pixel size, or a masked region change; or when image generation must run inside an OpenAI-based pipeline or agent loop. Triggers on DALL-E, DALL·E, gpt-image, OpenAI image generation, image edits, inpainting with a mask, or image variations.
---

# OpenAI Images - DALL·E and GPT Image

## Overview

OpenAI's image line has two generations. **DALL·E 2 and 3** are the older prompt-in,
image-out models. **GPT Image** (`gpt-image-1` onwards) is the current line: it inherits
the language model's world knowledge and instruction-following, accepts multiple input
images, and does masked editing properly.

Use GPT Image unless you have a specific reason not to. DALL·E 3 remains useful for its
`vivid`/`natural` style switch and its prompt-rewriting behaviour; DALL·E 2 is only worth
touching for the `/variations` endpoint, which nothing else implements.

What this line does better than the alternatives:

- **Transparent backgrounds** - `background=transparent`, genuinely alpha-cut assets
- **Exact pixel dimensions** - arbitrary `WIDTHxHEIGHT` on `gpt-image-2`, not just presets
- **True masked inpainting** - you supply a mask PNG, not a prose description of the region
- **Input fidelity control** - `input_fidelity=high` preserves faces, logos and fine detail
- **Fits an existing OpenAI pipeline** - same key, same billing, callable as a tool

## Setup

```bash
export OPENAI_API_KEY="sk-..."          # https://platform.openai.com/api-keys
export OPENAI_BASE_URL="..."            # optional, for a gateway or proxy
```

GPT Image models require **organisation verification** on the OpenAI platform. A `403`
that mentions the model is almost always that, not a bad key.

`scripts/openai_image.py` is standard library only - nothing to install.

## Models

| Alias | Model ID | Use it for |
|---|---|---|
| `best` *(default)* | `gpt-image-2` | Everything. Arbitrary sizes up to 3840×2160, best quality. |
| `pinned` | `gpt-image-2-2026-04-21` | Production, when output must not drift under a model update. |
| `mid` | `gpt-image-1.5` | Cheaper GPT Image; the default for the edits endpoint. |
| `mini` | `gpt-image-1-mini` | Bulk, drafts, thumbnails. |
| `legacy` | `gpt-image-1` | Reproducing earlier results. |
| `chatgpt` | `chatgpt-image-latest` | The model behind ChatGPT's image tool. |
| `dalle3` | `dall-e-3` | `--style vivid/natural`; automatic prompt expansion. |
| `dalle2` | `dall-e-2` | `/variations` only. |

`scripts/openai_image.py models` lists what your key can actually reach.

## Usage

```bash
S=.claude/skills/openai-images/scripts/openai_image.py

# text -> image
$S generate "A brass sextant on a navigator's chart, morning window light, 85mm" \
  -o out/sextant.png --size 1536x1024 --quality high

# transparent-background asset
$S generate "A flat vector maple leaf icon, single colour, centred" \
  --background transparent --output-format png -o out/leaf.png

# masked edit - transparent pixels in the mask mark what changes
$S edit "a brass reading lamp on the desk, matching the room's warm light" \
  -i room.png --mask lamp_region.png -o out/room_lamp.png

# compose across several inputs, preserving detail from them
$S edit "place the product from the first image on the desk in the second" \
  -i product.png -i desk.png --input-fidelity high -o out/staged.png

# DALL-E 3 with its style switch
$S generate "a mountain village at dusk" -m dalle3 --style natural --quality hd -o out/village.png
```

Flags: `--size` (`1024x1024 | 1536x1024 | 1024x1536 | auto`, or any `WxH` on `gpt-image-2`
with both dimensions divisible by 16, ratio within 1:3–3:1, max 3840×2160), `--quality`
(`low/medium/high/auto`; `standard/hd` on DALL·E 3), `--background`, `--output-format`
(`png/jpeg/webp`), `--output-compression`, `--moderation`, `-n` (1–10; DALL·E 3 is 1 only),
`--dry-run`.

The script warns when you pass a DALL·E-only parameter to a GPT Image model or vice versa,
rather than letting the API 400 on you.

## Masks

The mask is the feature people get wrong. It is a **PNG with an alpha channel**, the same
dimensions as the input image. **Transparent pixels are the region that gets regenerated**;
opaque pixels are preserved. It is not a black-and-white mask, and the polarity is the
opposite of what most people guess.

```bash
# make a mask: fully transparent rectangle over the area to change
python3 -c "
from PIL import Image
img = Image.open('room.png').convert('RGBA')
mask = Image.new('RGBA', img.size, (0, 0, 0, 255))   # opaque = keep
mask.paste((0, 0, 0, 0), (420, 180, 700, 520))       # transparent = regenerate
mask.save('lamp_region.png')"
```

Without a mask, the whole image is regenerated from the input as a reference - which is
often what you want for a restyle, and never what you want for a spot fix.

## Prompting

GPT Image rewards specification the way its language models do - it will follow a detailed
brief rather than averaging it. Give it structure:

- **Subject, then composition, then light, then medium.** "A cast-iron skillet on a marble
  counter, three-quarter view, hard morning light from the left, shot on 50mm, editorial
  food photography."
- **Be explicit about layout.** "Centred, with clear margin on all sides", "subject in the
  lower third", "flat lay, top-down". It honours these.
- **Text works.** Quote the string exactly and describe the type. GPT Image renders short
  strings reliably; long paragraphs still break.
- **Say the medium.** "photograph" vs "3D render" vs "flat vector illustration" vs
  "watercolour" produces genuinely different output.
- **DALL·E 3 rewrites your prompt** before generating and returns the rewrite as
  `revised_prompt` (the script prints it). To suppress most of it, prefix with:
  "I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail,
  just use it AS-IS:". GPT Image does not do this.

Genre recipes, edit patterns and a debugging table: `references/prompting_guide.md`.
Endpoints, every parameter, response shapes, errors and pricing:
`references/api_reference.md`.

## Choosing between this and the other image skills

| Need | Skill |
|---|---|
| Transparent background, exact dimensions, masked inpainting | **openai-images** |
| Conversational multi-turn editing, best text rendering, cheapest | `nano-banana` |
| Best-looking output, taste-driven exploration | `midjourney` (no API - prompts only) |
| Already inside an OpenAI agent/tool loop | **openai-images** |

## Limits and refusals

- No photoreal images of identifiable real people in fabricated situations, no
  impersonation, no forged documents. OpenAI also blocks living-artist style requests by
  name and most public-figure likenesses at the API level.
- GPT Image outputs carry **C2PA content credentials**. There is no opt-out. Mention this
  when provenance or licensing comes up.
- `moderation=low` relaxes filtering somewhat; it does not disable it.
- Billing is per image and scales with quality and size - a `high`-quality 4K image is
  many times the cost of a `low` 1024×1024. Say so before firing off `-n 10 --quality high`.
