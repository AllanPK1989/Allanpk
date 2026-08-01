# Midjourney Prompting Guide

Midjourney is not an instruction-follower. It is an aesthetic engine you nudge. Prompts
that work here are short, evocative and concrete - the opposite of the paragraph-length
specifications that Gemini and GPT Image reward.

## The shape of a prompt

```
[image URLs] [subject], [action], [environment], [light], [composition], [medium] [--params]
```

```
a lone lighthouse keeper climbing an iron stair, storm light through salt-glazed
glass, low angle, 35mm, muted maritime palette --ar 2:3 --style raw --s 200
```

Rules that hold up:

- **15-40 words.** Past that, concepts start averaging into mush. If you need more
  control, use parameters and references, not more adjectives.
- **Front-load.** Earlier terms carry more weight. Lead with the subject.
- **Commas separate concepts**, not clauses. `a knight, rain-soaked armour, dawn fog`
  reads better than a flowing sentence.
- **Concrete nouns beat adjectives.** "brutalist concrete stairwell" beats "cool
  architectural vibe".
- **Never write exclusions in prose.** "an empty street, no people" reliably produces
  people. Use `--no people`.

## Genre starting points

**Photorealism**
```
--style raw --s 0-100
```
Add real camera language: `85mm f/1.4`, `Portra 400`, `overcast diffuse light`,
`three-quarter view`. Naming a film stock does more than "photorealistic" ever will.

**Editorial / commercial**
```
--style raw off, --s 250-400, plus a --sref for the house look
```
The default aesthetic is an asset here; keep Raw off and lean on a style reference for
consistency.

**Illustration and anime**
```
--niji 6 --style expressive
```
`original` for the classic look, `cute` for softer, `scenic` for backgrounds and
environments.

**Graphic / logo / flat vector**
```
flat vector, minimal, two-colour, white background --style raw --s 50 --no gradients, shadows, text
```
Midjourney cannot render reliable text. For anything with real lettering, generate the
mark here and set type elsewhere - or use Nano Banana Pro / GPT Image instead.

**Textures and materials**
```
--tile --style raw --s 0
```
Seamless, unstylised, ready for a material pipeline.

**Concept art / world building**
```
--s 400-750 --c 20-40 --w 250
```
Let it wander. High chaos gives four genuinely different directions per job.

## Style references and consistency

`--sref` is the highest-leverage parameter in Midjourney. It transfers palette, lighting,
rendering technique and mood - **not** subject or composition.

```
a fishing village at dusk --sref https://cdn.example/look.jpg --sw 400
```

- `--sw 0-100`: a hint. `200-500`: clearly the same visual world. `700-1000`: heavy,
  sometimes overrides the subject.
- Multiple URLs blend styles: `--sref urlA urlB`.
- `--sref random` rolls a random style and prints a reusable style code - a fast way to
  find a look you couldn't have described.
- **Moodboards** (trained in the web app on a set of images) are the durable version of
  this for a long project: a named style you can apply without pasting URLs.

Workflow for a consistent series: generate one hero image → use its URL as `--sref` for
every subsequent prompt → hold `--sw` constant → vary only the subject text.

## Character consistency

Ranked by strength:

1. **`--oref` + `--ow 400-600`** (V7 only) - the strongest identity lock, works for
   people, animals and objects.
2. **`--cref` + `--cw`** - available on V8.x. `--cw 0` keeps the face and frees the
   outfit; `--cw 100` locks face, hair and clothes. Stronger on stylised characters than
   on photoreal faces.
3. **Description discipline** - repeat the same invariant clause in every prompt: "a
   woman in her forties, close-cropped silver hair, thin scar through the left eyebrow,
   olive field jacket". Cheap, and it stacks with the above.
4. **Seed reuse** - only holds while the rest of the prompt is unchanged. Fragile.

## The editor beats re-rolling

Re-rolling a prompt changes everything. The web editor changes one thing:

- **Vary Region** - inpaint a selected area with a new prompt. The correct tool for
  "everything is right except the hands / the sign / the sky".
- **Pan** and **Zoom Out** - extend the canvas in a direction, keeping what exists.
- **Upscale (Subtle / Creative)** - Subtle preserves detail, Creative reinterprets it.
- **Retexture** - keep the geometry and composition, change materials and lighting.
- **Remix** - re-run with an edited prompt against the same composition.

Reach for these before rewriting the prompt.

## Draft Mode economics

`--draft` gives 24 low-resolution images for roughly half the fast-hour cost of one
standard job. The workflow it enables:

1. `--draft` with a broad prompt and `--c 30` → 24 directions
2. Pick one, note what worked
3. Rerun that exact prompt without `--draft`, optionally `--q 2`
4. Finish in the editor

`--sref random` inside a draft job gives 24 *different styles* at once - the fastest way
to find a look.

## Debugging

| Symptom | Fix |
|---|---|
| Too generic / "Midjourney-looking" | `--style raw`, drop `--s` to 0-100 |
| Ignored half the prompt | Shorten it. Move the key concept to the front. Add `::` weight. |
| Four near-identical images | Raise `--c` to 25-50 |
| Subject drifts across a series | Add `--sref` (look) and `--cref`/`--oref` (identity) |
| Stretched or duplicated subjects | `--ar` is too extreme; stay within 2:1 |
| Text is gibberish | Expected - Midjourney cannot render reliable text. Set type externally, or switch models. |
| Too tame | Raise `--w` to 250-750, or `--exp 20` |
| Right image, one bad area | Vary Region in the editor, not a re-roll |
| Burning through fast hours | `--draft` for exploration; Relax mode for bulk |

## What to reach for another model instead

- **Editing a photo the user supplies** - Midjourney's image prompts are stylistic
  influence, not faithful edits. Use Nano Banana.
- **Text in the image** - Nano Banana Pro or GPT Image.
- **Exact dimensions or transparent backgrounds** - OpenAI `gpt-image-2`.
- **Anything programmatic** - Midjourney has no public API, and the third-party bridges
  violate its ToS.
