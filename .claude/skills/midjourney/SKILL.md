---
name: midjourney
description: Prompt craft and workflow for Midjourney image generation (V8.x, niji), covering parameters (--ar, --s, --sref, --cref, --oref, --chaos, --weird, --exp, --draft), style references, character consistency, permutation batches, the web editor (vary region, pan, zoom, retexture), and moodboards/personalization. Use this skill when asked to write, fix, improve or batch Midjourney prompts, choose Midjourney parameters, reproduce a style across images, or decide between Midjourney and an API-driven image model. Midjourney has no public API - this skill produces paste-ready prompts, it does not generate images.
---

# Midjourney

## Overview

Midjourney is the aesthetics-first image generator: strongest default look of any model,
weakest at instruction-following and text rendering. You steer it with a short evocative
prompt plus parameters, not with paragraphs of specification.

**It has no public API.** Prompts are run in the web app (midjourney.com/imagine) or the
Discord bot; access is subscription-only, from ~$10/month. An enterprise-gated developer
API has been referenced but is not generally available, and the third-party "Midjourney
API" services all automate the Discord bot in violation of Midjourney's Terms of Service -
do not build on them or recommend them.

So the deliverable from this skill is **a prompt the user pastes**, plus the reasoning
behind the parameter choices. If the user needs images generated programmatically in this
session, say so plainly and point at the `nano-banana` or `openai-images` skill instead.

## Choosing Midjourney over an API model

| Want | Use |
|---|---|
| Best-looking result, exploratory, taste-driven | Midjourney |
| Editing a specific image, holding everything else stable | Nano Banana |
| Correct text inside the image | Nano Banana Pro, or GPT Image |
| Programmatic generation in a pipeline | Nano Banana or OpenAI Images |
| Transparent backgrounds, exact dimensions | OpenAI Images (`gpt-image-2`) |

## Model versions (as of August 2026)

| Version | Status |
|---|---|
| **V8.2** | Default since 24 July 2026. Bolder, more sophisticated aesthetics; improved Personalization. `--preview` opts into its early-access aesthetic pass. |
| V8.1 | Released 14 April 2026; introduced Draft Mode. |
| V8 | Early-access alpha, 17 March 2026. |
| V7 | Previous generation. **Still the only line supporting `--oref` (Omni Reference).** |
| niji 6 | Anime/illustration model. Own style set: `cute`, `expressive`, `original`, `scenic`. |

Midjourney ships changes fast and `docs.midjourney.com` blocks scripted fetches, so treat
the tables here as a working reference and check the official Parameter List page when
something behaves unexpectedly.

## Usage

```bash
S=.claude/skills/midjourney/scripts/mj_prompt.py

# build a prompt
$S build "a brass sextant on a navigator's chart, morning window light" \
  --ar 3:2 --style raw --s 150 --no text,watermark

# style + character lock across a series
$S build "the same explorer at a campfire" \
  --sref https://cdn.example/style.jpg --sw 400 \
  --cref https://cdn.example/face.jpg --cw 40

# lint a prompt before it burns GPU minutes
$S check "a cat --ar 3:2 --s 2000 --oref http://x.jpg --v 8.2"
#   ERROR --s 2000 is out of range (0-1000, default 100)
#   ERROR --oref is not supported on the V8 series. Add --v 7, or use --sref/--cref.

# expand a permutation batch
$S permute "a {red,blue} car in {rain,fog} --ar 16:9"
```

The linter catches the mistakes that actually cost money: out-of-range values, `--oref` on
V8, `--niji` mixed with `--v`, weights with no matching reference, image prompts placed
after the text, and extreme aspect ratios.

## Prompt structure

Midjourney reads short prose, weighted toward the front. A reliable order:

```
[image prompt URLs] [subject] [action/pose] [environment] [lighting] [composition/lens] [medium/style] [--parameters]
```

```
a brass sextant on a weathered navigator's chart, morning light through a
porthole, shallow depth of field, 85mm, muted film grain --ar 3:2 --style raw --s 150
```

Key differences from Gemini/GPT-Image prompting:

- **Shorter is better.** 15-40 words is the sweet spot. Long specifications get averaged
  away rather than followed.
- **Commas separate concepts**, and earlier concepts weigh more. `::` sets explicit
  weights (`forest:: 2 fog:: 1`); a negative weight is the old way to exclude, but `--no`
  is clearer.
- **No negative prompt in prose.** "no people" summons people. Use `--no people`.
- **Parameters do the work** that prose does in other models - aspect, stylisation,
  variance, and style/character references.

## The parameters that matter most

| Parameter | Range | What it actually does |
|---|---|---|
| `--ar W:H` | up to ~2:1 | Aspect ratio. Beyond 2:1 you get stretching and repeated elements. |
| `--s` (stylize) | 0-1000, default 100 | How hard Midjourney pushes its own aesthetic over your prompt. Low = literal, high = pretty but unfaithful. |
| `--style raw` | flag | Turns off the house look. The single best lever for photorealism and for prompts you want followed literally. |
| `--c` (chaos) | 0-100 | Spread across the four initial images. High = wildly different concepts. |
| `--w` (weird) | 0-3000 | Unconventional aesthetics. Pairs badly with high `--s`. |
| `--sref URL` | + `--sw 0-1000` | Style reference. The workhorse for a consistent look across a series. `--sref random` rolls a style. |
| `--cref URL` | + `--cw 0-100` | Character reference. `--cw 0` = face only (lets you change outfit), `100` = face, hair and clothes. |
| `--oref URL` | + `--ow 0-1000` | Omni Reference - strongest subject lock. **V7 only.** `--ow 400-600` for hard character lock, `25-75` for a hint. |
| `--exp` | 0-100 | Experimental aesthetics. `--exp 10-25` with `--s 100-200` is a good controlled boost. |
| `--q` | 1, 2, 4 | GPU time per job. `--q 2` helps texture-heavy work; rarely worth 4. |
| `--draft` | flag | Draft Mode: 24 low-res images for half the fast-hours. Explore, then rerun the winner at full quality. |
| `--no x,y` | list | Exclusions. |
| `--seed n` | 0-4294967295 | Reproducibility - same seed + same prompt + same version = same image. |
| `--tile` | flag | Seamlessly tiling texture. |
| `--p [code]` | flag/code | Personalization - applies your trained taste profile. |

Full table with defaults, version support and interaction notes:
`references/parameter_reference.md`.

## Workflows

**Explore then commit.** `--draft` for 24 cheap options → pick a direction → rerun that
prompt without `--draft`, maybe with `--q 2`. This is the biggest cost saver Midjourney
offers.

**Lock a look across a series.** Generate one image you like, use its URL as `--sref` for
everything after it, and keep `--sw` constant. Moodboards (trained on a set of images in
the web app) do the same job more durably for long projects.

**Lock a character.** V7 + `--oref` + `--ow 400-600` is the strongest option. On V8.x you
are limited to `--cref`/`--cw`, plus describing the invariant features in every prompt.

**Refine in the editor, not the prompt.** The web editor's Vary Region (inpaint), Pan,
Zoom Out, Upscale and Retexture handle localised fixes far better than re-rolling a whole
prompt. Re-rolling changes everything; editing changes one thing.

**Batch with permutations.** `{a,b,c}` in a prompt fans out into separate jobs - each one
billed. The `permute` subcommand refuses to expand past 40 by default for that reason.

More on style references, moodboards, editor mechanics and genre recipes:
`references/prompting_guide.md`.

## Working with the user

- Deliver the prompt in a copyable block, and say which knob to turn if the result misses:
  too generic → `--style raw`, lower `--s`; too literal/flat → raise `--s`; too samey →
  raise `--c`; wrong subject identity → add `--cref`/`--sref`.
- Explain non-obvious parameter choices in one line each. Don't dump the whole table.
- Never claim to have generated a Midjourney image. There is no API; the user runs it.
- Midjourney's ToS: paid subscribers own their outputs, images from free/trial usage and
  all images made under a non-Pro plan are public in the community gallery by default.
  Stealth mode requires the Pro plan or above. Mention this for anything confidential.
