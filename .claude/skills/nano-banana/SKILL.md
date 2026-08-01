---
name: nano-banana
description: Image generation and editing with Google's Nano Banana models (Gemini image models - gemini-3.1-flash-image, gemini-3-pro-image, gemini-2.5-flash-image) via the Gemini API. Use this skill when asked to generate, create, render, edit, retouch, restyle, upscale, or composite an image; to turn a sketch, CAD drawing, wireframe or screenshot into a photoreal render; to produce textures, hero images, mockups, diagrams, or product shots; or to place text inside an image. Triggers on Nano Banana, Nano Banana Pro, Gemini image generation, image-to-image, inpainting-by-prompt, character consistency, or "make me a picture of".
---

# Nano Banana - Gemini Image Generation

## Overview

"Nano Banana" is the nickname for Google's Gemini image models. They are conversational
image models, not diffusion prompt-slot models: you talk to them in full sentences, hand
them reference images, and iterate by asking for changes.

What they are unusually good at, relative to other image models:

- **Editing an image you supply** - change one thing, keep everything else pixel-stable
- **Text inside images** - signage, labels, packaging, UI, posters that read correctly
- **Multi-image composition** - blend 2-3 references (this product, that room, this style)
- **Consistency** - the same character/object across a series of images
- **World knowledge** - it understands what a "torque wrench" or "Bundt pan" actually is

Every output carries an invisible SynthID watermark. That is unavoidable and is worth
mentioning if the user asks about provenance.

## Setup

Needs a Gemini API key - free tier included, no billing required to start.

```bash
export GEMINI_API_KEY="..."   # https://aistudio.google.com/apikey
```

The scripts in `scripts/` are standard library only - nothing to install. If the key is
missing, say so and stop; do not silently fake an image or substitute a different tool.

## Model selection

| Alias | Model ID | Use it for |
|---|---|---|
| `flash` *(default)* | `gemini-3.1-flash-image` | Everyday generation and editing. Fast, cheap, strong. |
| `lite` | `gemini-3.1-flash-lite-image` | Bulk work, drafts, thumbnails, tight budgets. |
| `pro` | `gemini-3-pro-image` | Fine detail, dense text, infographics, 2K/4K output, hardest edits. |
| `legacy` | `gemini-2.5-flash-image` | The original Nano Banana. Only for reproducing older results. |

Model IDs move. `scripts/nano_banana.py models` asks the API what the key can actually
reach - run it before assuming an ID is wrong.

## Core usage

```bash
S=.claude/skills/nano-banana/scripts

# text -> image
$S/nano_banana.py generate "A weathered brass sextant on a navigator's chart, \
morning window light, shallow depth of field, 85mm" -o out/sextant.png -a 3:2

# edit an existing image (this is the workhorse mode)
$S/nano_banana.py generate "Remove the coffee cup from the desk, keep everything \
else exactly as it is" -i desk.jpg -o out/desk_clean.png

# compose from multiple references
$S/nano_banana.py generate "Place the chair from the first image into the room from \
the second, matching the room's lighting and perspective" -i chair.png -i room.jpg -o out/staged.png

# 4K poster with real typography
$S/nano_banana.py generate "Concert poster reading 'MIDNIGHT SIGNAL - Oct 14 - The Vault', \
bold condensed sans, high-contrast duotone" --model pro --size 4K -a 2:3 -o out/poster.png

# three variants to choose from
$S/nano_banana.py generate "..." -n 3 -o out/logo.png
```

Flags worth knowing: `-a/--aspect` (`1:1 2:3 3:2 3:4 4:3 4:5 5:4 9:16 16:9 21:9`),
`-s/--size` (`512 1K 2K 4K`; 2K/4K on `pro`), `--system` for persistent style rules
across a series, `--dry-run` to inspect the request.

## Sketch or drawing -> photoreal

A dedicated wrapper, because the naive prompt fails in a specific way: technical drawings
carry reference numerals and leader lines, and the model happily renders those *onto the
physical object*. The wrapper's prompt separates geometry (copy faithfully) from the
annotation layer (discard entirely).

```bash
$S/sketch_to_photo.py drawing.png -o out/machine.png \
  --subject "7-station automated adhesive dispensing machine with pneumatic cylinders \
and a touchscreen HMI, on a castored steel cabinet" \
  --preset factory

$S/sketch_to_photo.py drawing.png --print-prompt   # inspect/tune the prompt first
```

Presets: `studio`, `factory`, `workshop`, `white`. Naming the subject in plain words
matters more than any other single lever - the model renders what it recognises, so
"7-station dispensing machine" beats "the thing in the picture".

## How to actually prompt these models

**Describe a scene, don't list tags.** "A vintage typewriter on a cluttered writer's desk,
late afternoon light raking across the keys" outperforms `typewriter, desk, vintage, 8k,
masterpiece`. Booru-style tag soup and quality-word stuffing ("8k, ultra HD, masterpiece")
are diffusion-era habits that do nothing here.

**Say what you want, not what you don't.** "An empty street at dawn" works; "a street with
no people" often puts people in. The one exception is annotation-stripping on drawings,
where an explicit exclusion earns its place.

**Use photographic and art-direction vocabulary.** Lens (35mm/85mm/macro), aperture,
lighting (softbox, golden hour, rim light), angle (low, three-quarter, top-down), film
stock, medium (oil on canvas, vector flat, isometric 3D). This is the highest-leverage
part of a prompt.

**For text in images, quote it exactly.** `a sign reading "OPEN 24 HOURS"`. Keep it short,
describe the type style, and use `--model pro` when the text is dense or small.

**For edits, name the invariant.** "Change only the wall colour to sage green - keep the
furniture, lighting and camera position identical." Without that, the model redraws the
whole frame.

**Iterate conversationally.** Feed the output back with `-i` and ask for one change at a
time. Three focused rounds beat one 400-word prompt.

Full recipes, per-genre templates and failure patterns: `references/prompting_guide.md`.
API details, response shape, limits and pricing: `references/api_reference.md`.

## Working with the user

- **Show the result.** After generating, surface the file with `SendUserFile` (or the
  environment's equivalent) rather than only printing a path.
- **Offer variants when taste is involved** - logos, hero images, anything subjective.
  One shot is fine for a literal, well-specified render.
- **Report the prompt you used.** Users refine prompts, not pixels.
- **Cost awareness.** Roughly $0.03-0.04 per 1K/2K image on flash, ~$0.13 on pro
  (~$0.24 at 4K). Don't fire off `-n 8` at 4K on `pro` without saying so.

## Limits and refusals

- No photoreal images of identifiable real people in fabricated situations, no impersonation,
  no forged documents/receipts/IDs, no deceptive "real photo" content of events that
  didn't happen. If the request is for a prop or a test, that doesn't change it.
- Safety filters return no image and a `finishReason`; the script surfaces it. Rephrase
  rather than retrying identically.
- Long verbatim text, precise charts with real data, and exact colour matching are still
  weak spots - use `pro`, and check the output rather than trusting it.
- Free-tier daily image quotas are small. `429` means quota, not a bug.
