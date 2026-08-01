# GPT Image / DALL·E Prompting Guide

GPT Image inherits the language model's instruction-following, so it rewards
*specification* - the opposite of Midjourney, where brevity wins. Write a brief, not a
mood.

## Structure

```
[medium] of [subject], [composition/layout], [lighting], [colour/mood], [technical notes]
```

```
Editorial food photograph of a cast-iron skillet of roast tomatoes on a marble counter.
Three-quarter view, subject slightly right of centre with clear margin at the top.
Hard morning light from the left, deep shadows. Muted warm palette. Shot on 50mm at f/4.
```

What it actually honours, that most image models ignore:

- **Layout instructions.** "centred with even margins", "subject in the lower third",
  "flat lay, top-down", "leave the upper right empty for a headline".
- **Counts.** "exactly three jars, evenly spaced" mostly works. Beyond about six, drop it.
- **Relationships.** "the mug behind the book, partially occluded".
- **Negations.** "no text anywhere in the image" is usually respected, unlike in
  Midjourney or Stable Diffusion.
- **Style by description, not by artist name.** Living-artist names are blocked at the API
  level; describe the technique instead - "loose ink linework with flat washes and visible
  paper grain".

## Medium vocabulary

Naming the medium changes the model more than any adjective:

`photograph` · `studio product photograph` · `documentary photo` · `3D render, Octane` ·
`flat vector illustration` · `isometric 3D icon` · `technical line drawing` ·
`watercolour with visible paper texture` · `oil on canvas, thick impasto` ·
`risograph two-colour print` · `pencil sketch` · `pixel art, 32×32` · `blueprint`

Pair with real photographic language for realism: lens (`24mm`, `85mm`, `macro`),
aperture, light source (`softbox`, `golden hour`, `overcast`, `single practical lamp`),
angle, and film stock.

## Text in images

GPT Image renders text more reliably than most models. Rules:

- Quote it exactly: `a sign reading "CLOSED FOR THE SEASON"`.
- Describe the typography: weight, case, era, `condensed grotesque`, `hand-painted`.
- Say where it sits: "centred in the upper third", "along the bottom edge".
- Keep it short. A headline plus two labels is safe; a paragraph is not.
- Always read the rendered text back. It still drifts on long strings.

```bash
openai_image.py generate 'A minimalist coffee bag mockup on a concrete surface.
The label reads "SINGLE ORIGIN / ETHIOPIA YIRGACHEFFE / 250g" in a thin uppercase
grotesque, black on kraft paper. Studio lighting, centred, clear margin.' \
  --size 1024x1536 --quality high -o out/bag.png
```

## Transparent assets

The reason to reach for this API over the others:

```bash
openai_image.py generate "A flat vector maple leaf icon, single colour #C1440E,
centred, clean bezier edges, no drop shadow, no background" \
  --background transparent --output-format png --size 1024x1024 -o out/leaf.png
```

Ask for "no background", "no drop shadow" and "clean edges" in the prompt as well as
setting `--background transparent` - the two reinforce each other. Icons and logos come
out cleaner at `--quality high`.

## Editing

| Goal | How |
|---|---|
| Spot fix one region | `--mask` covering just that region, prompt describing only the new content |
| Restyle the whole image | No mask, prompt describing the target style, `--input-fidelity high` to hold the subject |
| Composite two sources | Multiple `-i` inputs, prompt describing the relationship ("place the product from image 1 on the desk in image 2") |
| Preserve a face or logo | `--input-fidelity high` - this is exactly what it exists for |
| Extend the canvas | Pad the image to the target size with transparent pixels, pass the padded image as both input and mask |
| Remove an object | Mask the object, prompt: "empty {surface}, continuous with the surrounding background" |

Mask polarity, restated because it is the single most common mistake: **transparent =
change, opaque = keep**. Same dimensions as the input image. It is an alpha mask, not a
black-and-white one.

## DALL·E 3 specifics

- **It rewrites your prompt.** The rewrite comes back as `revised_prompt` and is what was
  actually generated. To mostly suppress it, prefix with: *"I NEED to test how the tool
  works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:"*.
- **`--style vivid`** (default) is heavily stylised and contrasty; **`--style natural`** is
  more literal and photographic. This switch does not exist on GPT Image.
- `n=1` only. Loop for variants.
- Weaker at text, layout instructions and counting than GPT Image. Prefer GPT Image unless
  you specifically want the DALL·E 3 look.

## Debugging

| Symptom | Fix |
|---|---|
| Ignored a layout instruction | State it as its own sentence rather than a clause; raise `--quality` |
| Looks like generic stock AI art | Name the medium and the lens; add specific imperfections; avoid "beautiful", "stunning", "high quality" |
| Text garbled | Shorten the string, raise `--quality high`, describe the typeface, increase resolution |
| Transparent background isn't transparent | `--output-format png` (jpeg has no alpha) and repeat "no background" in the prompt |
| Edit changed the whole image | You forgot the mask, or the mask polarity is inverted |
| Face/logo drifted in an edit | `--input-fidelity high` |
| `content_policy_violation` | Real person, artist name, brand, or a flagged concept. Rephrase descriptively; retrying verbatim won't help. |
| Output drifts between runs in production | Pin `gpt-image-2-2026-04-21` instead of the moving alias |
| Costs climbing | Drop to `--quality medium` or `-m mini` for drafts; only finals at `high` |
