# Midjourney Parameter Reference

Parameters go at the **end** of the prompt, after the text. Image prompt URLs go at the
**start**, before the text. Verify anything surprising against the official Parameter List
at `docs.midjourney.com` - Midjourney ships changes frequently and the docs site blocks
scripted fetching, so this table is maintained by hand.

## Model selection

| Parameter | Values | Notes |
|---|---|---|
| `--v` | `8.2`, `8.1`, `8`, `7`, `6.1`, `6` | Model version. Omit to use your account default (V8.2 as of Aug 2026). |
| `--niji` | `6`, or bare | Anime/illustration model. Mutually exclusive with `--v`. |
| `--style raw` | flag | Reduces Midjourney's default aesthetic pass. Best lever for photorealism and literal prompt-following. |
| `--style` (niji) | `cute`, `expressive`, `original`, `scenic` | niji-only style presets. |
| `--p` | flag, or a profile code | Personalization - applies your trained taste profile. Needs ~40 ranked image pairs to activate. |
| `--preview` | flag | V8.2 early-access aesthetics pass. |
| `--exp` | `0-100` | Experimental aesthetics. `10-25` with `--s 100-200` is a controlled boost; high values get chaotic. |

## Composition and variance

| Parameter | Range | Default | Notes |
|---|---|---|---|
| `--ar W:H` | ~1:2 to 2:1 | `1:1` | Beyond 2:1, expect stretched subjects and duplicated elements. `--ar 3:2` photo, `--ar 16:9` banner, `--ar 2:3` poster, `--ar 9:16` phone. |
| `--s` / `--stylize` | `0-1000` | `100` | Weight of Midjourney's house aesthetic against your prompt. `0-50` literal and plain; `100-250` balanced; `500+` gorgeous and unfaithful. |
| `--c` / `--chaos` | `0-100` | `0` | How different the four initial images are from each other. `0` = four variations on one idea; `50+` = four different ideas. |
| `--w` / `--weird` | `0-3000` | `0` | Unconventional, off-kilter aesthetics. Start at `250`. Fights with high `--s`. |
| `--q` | `1`, `2`, `4` | `1` | GPU time per job. `2` helps dense texture and detail; `4` rarely justifies the cost. |
| `--seed` | `0-4294967295` | random | Same seed + same prompt + same version reproduces an image. Changing any word breaks it. |
| `--stop` | `10-100` | `100` | Halt generation early for a blurrier, less resolved result. |
| `--tile` | flag | off | Seamlessly tiling output, for textures and patterns. |
| `--repeat` / `--r` | `1-40` | `1` | Runs the job N times. Pro/Mega plans only. Bills per run. |
| `--no` | comma list | - | Exclusions: `--no text, watermark, people`. Always prefer this to writing "no X" in the prose. |
| `--draft` | flag | off | Draft Mode (V8.1+): 24 low-resolution images at half the fast-hour cost. Explore here, then rerun the winner without it. |
| `--video` | flag | off | Animates the result into a short clip. |

## References

| Parameter | Companion | Range | Notes |
|---|---|---|---|
| `--sref URL` | `--sw` | `0-1000`, default `100` | **Style** reference - palette, lighting, rendering, mood. Not subject. Accepts multiple URLs, `random`, or a saved style code. Highest-value parameter for series consistency. |
| `--cref URL` | `--cw` | `0-100`, default `100` | **Character** reference. `--cw 0` locks the face only (outfit and setting free to change); `--cw 100` locks face, hair and clothing. Works best on stylised characters, less well on photoreal faces. |
| `--oref URL` | `--ow` | `0-1000`, default `100` | **Omni Reference** - strongest subject/object lock, works on people, animals and objects. **V7 only; not supported on the V8 series as of mid-2026.** `--ow 400-600` for a hard lock, `25-75` for influence only. |

`--sw`, `--cw` and `--ow` do nothing without their reference parameter. Multiple `--sref`
URLs blend styles; separate them with spaces.

## Prompt syntax (not parameters)

| Syntax | Meaning |
|---|---|
| `concept:: 2` | Explicit weight on a concept. `mountain:: 2 fog:: 1` makes mountain dominant. |
| `concept:: -0.5` | Negative weight. `--no` is clearer for straightforward exclusions. |
| `{a, b, c}` | Permutation - fans out into one job per combination. Each is billed. Nestable; combinations multiply fast. |
| `https://...` | Image prompt. Must appear before the text. Multiple URLs blend. |

## Version support notes

- `--oref` / `--ow`: V7 only.
- `--draft`: V8.1 and later.
- `--preview`: V8.2.
- `--cref` / `--cw`: V6 through V8.x (behaviour differs between them; V7 is generally
  stronger at identity).
- `--style raw`: V5.1 onwards.
- niji ignores most aesthetic parameters that assume the default model's look.

## Cost model

Midjourney bills **GPU time**, not images. A subscription includes a monthly pool of Fast
hours; Standard and above add unlimited Relax-mode generation (slower queue).

Rough relative cost per job: Draft Mode ≈ 0.5×, standard job = 1×, `--q 2` ≈ 2×,
`--repeat 4` = 4 jobs. Permutations bill per combination - `{a,b,c} {1,2,3}` is nine jobs,
not one.

## Plans and privacy

Outputs from paid plans are owned by the subscriber, but images are published to the
public community gallery by default. Stealth mode - keeping generations private - requires
the Pro plan or above. Raise this before anyone puts confidential product design,
unreleased branding, or client work through it.
