# /nano-banana-generate

Nano Banana - Generate or edit an image

## Description

Generates an image from a text prompt, or edits/composites images you supply, using
Google's Gemini image models (Nano Banana) via the `nano_banana.py` script from the
`nano-banana` skill.

## Usage

```bash
/nano-banana-generate a photoreal brass sextant on a navigator's chart
/nano-banana-generate remove the coffee cup from desk.jpg
```

## Implementation

Runs `.claude/skills/nano-banana/scripts/nano_banana.py generate` with a prompt built
from the request:

```bash
.claude/skills/nano-banana/scripts/nano_banana.py generate "<prompt>" \
  [-i input.png ...] -o out/image.png [-m flash|lite|pro] [-a 16:9] [-s 2K] [-n 3]
```

Requires `GEMINI_API_KEY` in the environment (https://aistudio.google.com/apikey).

## Notes

- Write the prompt as prose with lens, lighting and mood - not as a tag list
- Pass `-i` once per reference image; 2-3 references stay reliable
- For edits, state explicitly what must stay unchanged
- Use `-m pro` for dense text, fine detail, or 2K/4K output
- Surface the finished file to the user, and report the prompt that produced it
- See `.claude/skills/nano-banana/references/prompting_guide.md` for recipes
