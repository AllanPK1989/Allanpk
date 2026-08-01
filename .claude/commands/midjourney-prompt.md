# /midjourney-prompt

Midjourney - Build, lint or batch a prompt

## Description

Assembles a paste-ready Midjourney prompt with the right parameters, lints an existing
prompt for mistakes that cost GPU minutes, or expands `{a,b}` permutation syntax into the
full job list.

Midjourney has no public API. This produces a prompt string for the user to run in the web
app or Discord — it does not generate images.

## Usage

```bash
/midjourney-prompt a brass sextant on a navigator's chart, photoreal
/midjourney-prompt check this: a cat --ar 3:2 --s 2000 --oref x.jpg --v 8.2
```

## Implementation

Runs `.claude/skills/midjourney/scripts/mj_prompt.py`:

```bash
S=.claude/skills/midjourney/scripts/mj_prompt.py
$S build "<text>" --ar 3:2 --style raw --s 150 --no text,watermark
$S check "<existing prompt>"
$S permute "a {red,blue} car --ar 16:9"
```

## Notes

- Keep the descriptive text to 15–40 words; parameters do the rest of the work
- `--style raw` plus low `--s` for photorealism; raise `--s` for the house aesthetic
- `--sref` for a consistent look across a series, `--cref`/`--oref` for character identity
- `--oref` is V7 only — the linter flags it on V8
- `--draft` first (24 cheap images), then rerun the winner at full quality
- See `.claude/skills/midjourney/references/parameter_reference.md` for the full table
