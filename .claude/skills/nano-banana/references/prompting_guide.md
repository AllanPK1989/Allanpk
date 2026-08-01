# Nano Banana Prompting Guide

Gemini image models read prose. Write like you are briefing a photographer or an
illustrator, not like you are filling slots in a diffusion prompt.

## The shape of a good prompt

Five elements, in roughly this order. You rarely need all five.

1. **Subject** - what it is, specifically. "A 1960s Braun kitchen scale" not "a scale".
2. **Action / state** - what it is doing, or how it sits in the frame.
3. **Environment** - where it is, what surrounds it.
4. **Light and camera** - the single biggest quality lever. Lens, aperture, light source,
   direction, time of day, angle.
5. **Medium and mood** - photograph / oil painting / vector flat / isometric 3D, plus
   emotional register.

```
A 1960s Braun kitchen scale sitting on a scratched enamel counter, dial catching the
light. Late afternoon sun through a slatted blind lays hard stripes across the counter.
Shot on 50mm at f/2.8, shallow depth of field, warm Kodak Portra colour. Quiet,
domestic, slightly nostalgic.
```

## Things that help

**Positive phrasing.** Describe the desired state. "An empty boardwalk at sunrise" beats
"a boardwalk with no people" - naming a thing tends to summon it.

**Art-direction vocabulary.** These actually steer the model:

- Lens: `24mm wide angle`, `50mm`, `85mm portrait`, `macro`, `tilt-shift`, `fisheye`
- Aperture / focus: `f/1.4 shallow depth of field`, `f/16 deep focus`, `bokeh`
- Light: `softbox key light`, `golden hour`, `overcast diffuse`, `rim light`, `chiaroscuro`,
  `practical neon`, `single candle`
- Angle: `low angle hero shot`, `top-down flat lay`, `three-quarter view`, `eye level`,
  `dutch angle`
- Film / grade: `Portra 400`, `Ektachrome`, `high-contrast black and white`, `teal-orange grade`
- Medium: `oil on canvas with visible impasto`, `flat vector illustration`, `risograph
  two-colour print`, `isometric 3D render`, `technical pen line art`, `watercolour wash`

**Naming the subject correctly.** The model's world knowledge is deep - "a Chemex pour-over
brewer" produces a Chemex; "a coffee thing" produces mush. When working from a reference
image, tell it what the object *is*.

**Scale words for realism.** "Slight dust on the surfaces", "fine scratches near the
handle", "uneven wear on the edge" push output away from the clean-CGI look.

## Things that don't help

- Quality stuffing: `8k, ultra detailed, masterpiece, trending on artstation`. Wasted tokens.
- Tag lists: `castle, night, moon, fog, cinematic`. It reads as prose, so give it prose.
- Negative-prompt syntax (`--no people`, `((not blurry))`). There is no negative prompt
  field; write exclusions as plain sentences and only when truly needed.
- Weights and parentheses emphasis (`(red car:1.4)`). Meaningless here.

## Editing an existing image

Pass the image with `-i` and describe the change. The critical move is **naming what must
not change**:

```bash
nano_banana.py generate \
  "Change the car's paint to matte forest green. Keep the wheels, background, reflections,
   camera angle and lighting exactly as they are." \
  -i car.jpg -o out/car_green.png
```

Common edit patterns:

| Goal | Prompt shape |
|---|---|
| Remove an object | "Remove the {object}. Fill the space with background consistent with its surroundings. Change nothing else." |
| Add an object | "Add a {object} on the {location}. Match the existing lighting direction, shadow softness and perspective." |
| Local restyle | "Restyle only the {region} as {style}. Leave the rest of the image untouched." |
| Background swap | "Replace the background with {scene}. Keep the subject's edges, pose and lighting; adjust only the spill light to match the new scene." |
| Restore / de-noise | "Restore this damaged photograph: repair the creases and tears, remove dust and scratches, recover natural skin tones. Do not add or remove any content." |
| Colourise | "Colourise this black and white photograph with period-accurate, muted natural colour. Preserve all detail and grain." |
| Upscale-ish | "Re-render this image at higher fidelity: sharpen fine detail, recover texture in the fabric, keep composition identical." + `--size 2K --model pro` |

Iterate one change per round. Feed the previous output back in as `-i`.

## Multi-image composition

Up to about three reference images stay reliable. Refer to them by position:

```
Take the handbag from the first image and place it on the model in the second image,
hanging naturally from her shoulder. Match the second image's lighting and grain.
```

Useful splits: *subject + environment*, *product + style reference*, *character sheet +
new pose*, *room photo + furniture catalogue shot*.

## Text inside images

Nano Banana's headline strength. Rules:

- Quote the exact string: `a neon sign reading "COLD BEER"`.
- Describe the typography: weight, case, era, `condensed grotesque`, `hand-painted script`,
  `letterpress`.
- Keep strings short. A headline plus a couple of labels is reliable; a paragraph is not.
- Say where it goes: "centred in the upper third", "along the bottom edge".
- Use `--model pro` for dense text, infographics, multi-line layouts, and any language
  other than English.
- Always re-read the rendered text. Long strings still drift.

```bash
nano_banana.py generate \
  'A minimalist coffee bag mockup. Label reads "SINGLE ORIGIN / ETHIOPIA YIRGACHEFFE /
   250g" in a thin uppercase grotesque, black on kraft paper. Studio lighting, 4:5 crop.' \
  --model pro -a 4:5 -o out/bag.png
```

## Consistency across a series

Use `--system` to hold style constant, and re-feed a canonical reference image:

```bash
nano_banana.py generate "The same fox now sitting by a campfire at night" \
  -i fox_reference.png \
  --system "Children's book illustration: soft gouache texture, warm limited palette of
            ochre, teal and cream, thick outlines, no gradients." \
  -o out/fox_campfire.png
```

For characters, describe the invariants explicitly the first time (hair, clothing, build,
distinguishing marks) and keep that sentence in every subsequent prompt.

## Technical drawing / sketch -> photoreal

The failure mode: reference numerals, leader lines and dimension arrows get rendered as
physical decals on the object. Structure the prompt in three blocks:

1. **Geometry is spec** - "reproduce the drawing's proportions, layout and part positions
   faithfully; same number of modules, same frame structure."
2. **Materials and scene** - what it is made of, how it is lit, where it sits.
3. **Annotation is not the object** - "omit every reference numeral, leader line, arrow,
   callout, dimension line and title block; render only the physical machine."

`scripts/sketch_to_photo.py` builds exactly this; `--print-prompt` shows it for tuning.

The same three-block structure works for wireframe -> UI mockup, floor plan -> interior
render, and concept sketch -> product photo.

## Aspect ratio cheat sheet

| Ratio | Use |
|---|---|
| `1:1` | Avatars, icons, social tiles |
| `4:5` | Instagram portrait, packaging mockups |
| `2:3` / `3:4` | Posters, book covers, portrait product shots |
| `3:2` / `4:3` | Classic photography, catalogue shots, equipment |
| `16:9` | Hero banners, slides, video stills, thumbnails |
| `21:9` | Cinematic wides, wide website headers |
| `9:16` | Phone wallpapers, stories, vertical video |

## Debugging bad output

| Symptom | Fix |
|---|---|
| Looks like generic CGI | Add lens/aperture/light-source detail; ask for imperfections and dust; say "photograph, not a render". |
| Ignored part of the prompt | Split into rounds - generate the base, then edit in the missing element. |
| Edit changed the whole image | Add an explicit invariant list ("keep X, Y, Z identical"). |
| Text is garbled | Shorten the string, switch to `--model pro`, describe the typeface, raise `--size`. |
| Wrong object identity | Name the object precisely; add a reference image with `-i`. |
| Composition drifts across a series | Move style into `--system` and re-feed a reference image. |
| No image returned at all | Safety refusal - the script prints `finishReason` and any model text. Rephrase; don't retry verbatim. |
