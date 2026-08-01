# OpenAI Images API Reference

Base URL `https://api.openai.com/v1`, bearer auth with `OPENAI_API_KEY`.

## Endpoints

| Endpoint | Method | Body | Purpose |
|---|---|---|---|
| `/images/generations` | POST | JSON | Text → image |
| `/images/edits` | POST | multipart/form-data | Edit, inpaint with a mask, or compose several inputs |
| `/images/variations` | POST | multipart/form-data | Variations of one image. **`dall-e-2` only.** |

Image generation is also available as a **tool inside the Responses API**
(`{"type": "image_generation"}`), which is the right integration when the model should
decide when to produce an image mid-conversation, or when you want multi-turn refinement
with the conversation as context. The standalone Images endpoints are simpler for
one-shot generation.

## Models

```
gpt-image-2              gpt-image-2-2026-04-21   gpt-image-1.5
gpt-image-1              gpt-image-1-mini         chatgpt-image-latest
dall-e-3                 dall-e-2
```

`gpt-image-2` is a moving alias that picks up upgrades; `gpt-image-2-2026-04-21` is the
pinned snapshot for when visual consistency across a project matters more than quality
improvements. GPT Image models require **organisation verification**.

## Parameters

### /images/generations

| Parameter | Models | Values | Notes |
|---|---|---|---|
| `prompt` | all | string | Max 32000 chars for GPT Image, 4000 for `dall-e-3`, 1000 for `dall-e-2`. |
| `model` | all | see above | Defaults to `dall-e-2` if omitted - always set it explicitly. |
| `n` | all | 1-10 | `dall-e-3` supports `n=1` only. |
| `size` | all | `1024x1024`, `1536x1024`, `1024x1536`, `auto`; `dall-e-3`: `1024x1024`, `1792x1024`, `1024x1792`; `dall-e-2`: `256x256`, `512x512`, `1024x1024` | `gpt-image-2` also accepts arbitrary `WIDTHxHEIGHT`: divisible by 16, aspect between 1:3 and 3:1, max 3840×2160. |
| `quality` | all | GPT Image: `low`, `medium`, `high`, `auto`; `dall-e-3`: `standard`, `hd` | Drives both cost and latency. |
| `background` | GPT Image | `transparent`, `opaque`, `auto` | `transparent` requires `output_format` of `png` or `webp`. |
| `output_format` | GPT Image | `png`, `jpeg`, `webp` | Default `png`. |
| `output_compression` | GPT Image | 0-100 | `jpeg`/`webp` only. |
| `moderation` | GPT Image | `auto`, `low` | `low` relaxes filtering; it does not disable it. |
| `style` | `dall-e-3` | `vivid`, `natural` | `vivid` is the default and is heavily stylised; `natural` is more literal. |
| `response_format` | DALL·E only | `url`, `b64_json` | GPT Image **always** returns base64; URLs expire after 60 minutes. |
| `stream` / `partial_images` | GPT Image | bool / 0-3 | Streams progressively rendered partial images. |
| `user` | all | string | End-user identifier for abuse monitoring. |

### /images/edits

Everything above, plus:

| Parameter | Values | Notes |
|---|---|---|
| `image` | file, or `image[]` array | GPT Image accepts multiple inputs and composes across them. `dall-e-2` takes exactly one square PNG under 4 MB. |
| `mask` | PNG with alpha | Same dimensions as the input. **Transparent pixels are what gets regenerated**; opaque pixels are preserved. |
| `input_fidelity` | `low`, `high` | `high` makes the model work harder to preserve faces, logos and fine detail from the inputs. Costs more. |

Default model for edits is `gpt-image-1.5` when unspecified.

## Request examples

```bash
curl https://api.openai.com/v1/images/generations \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "A brass sextant on a navigator'\''s chart, morning window light",
    "size": "1536x1024",
    "quality": "high",
    "background": "opaque"
  }'
```

```bash
curl https://api.openai.com/v1/images/edits \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F model="gpt-image-2" \
  -F image[]="@product.png" \
  -F image[]="@desk.png" \
  -F mask="@region.png" \
  -F input_fidelity="high" \
  -F prompt="Place the product on the desk, matching the desk photo's lighting"
```

## Response

```json
{
  "created": 1770000000,
  "data": [
    { "b64_json": "iVBORw0KGgo...", "revised_prompt": "..." }
  ],
  "usage": {
    "total_tokens": 1500,
    "input_tokens": 50,
    "output_tokens": 1450,
    "input_tokens_details": { "text_tokens": 50, "image_tokens": 0 }
  }
}
```

- GPT Image: always `b64_json`. `usage` reports token counts, which is how you audit cost.
- DALL·E: `url` by default (expires in 60 minutes) or `b64_json` on request.
- `revised_prompt` appears on `dall-e-3` - it is what the model actually generated from,
  after rewriting your prompt.

## Errors

| Code | Cause | Fix |
|---|---|---|
| 400 | Parameter not supported by the chosen model | `style`/`response_format` are DALL·E only; `background`/`output_format`/`moderation`/`input_fidelity` are GPT Image only. |
| 400 | `size` invalid for the model | Check the size table; arbitrary sizes are `gpt-image-2` only. |
| 401 | Bad key | - |
| 403 | Org not verified, or model not enabled | Complete organisation verification for GPT Image models. |
| 429 | Rate limit or no quota | Check billing; back off exponentially. |
| `content_policy_violation` | Prompt refused | Rephrase. Retrying verbatim will not help. |

## SDK equivalents

```python
from openai import OpenAI
import base64

client = OpenAI()

result = client.images.generate(
    model="gpt-image-2",
    prompt="A brass sextant on a navigator's chart, morning window light",
    size="1536x1024",
    quality="high",
)
open("out.png", "wb").write(base64.b64decode(result.data[0].b64_json))

edited = client.images.edit(
    model="gpt-image-2",
    image=[open("product.png", "rb"), open("desk.png", "rb")],
    mask=open("region.png", "rb"),
    prompt="Place the product on the desk, matching the lighting",
    input_fidelity="high",
)
```

```js
import OpenAI from "openai";
const client = new OpenAI();

const result = await client.images.generate({
  model: "gpt-image-2",
  prompt: "A brass sextant on a navigator's chart",
  size: "1536x1024",
});
fs.writeFileSync("out.png", Buffer.from(result.data[0].b64_json, "base64"));
```

The bundled `scripts/openai_image.py` uses raw HTTP so it runs with no install, including
hand-rolled multipart encoding for the edits endpoint.

## Pricing (indicative - confirm before quoting)

Billed per image, scaling with model, quality and resolution. Order of magnitude:

- `gpt-image-1-mini`, low quality: about a cent per image
- GPT Image, medium quality, 1024×1024: a few cents
- GPT Image, high quality, large or 4K: 15-25 cents
- `dall-e-3` standard 1024×1024: about 4 cents; `hd`: about 8 cents

`input_fidelity=high` and large input images add input-token cost on top. The `usage`
block in each response is the reliable number.

## Provenance

GPT Image outputs carry **C2PA content credentials** in the file metadata, identifying
them as AI-generated. There is no opt-out, though metadata can be stripped downstream by
re-encoding. Raise this whenever authenticity, licensing or disclosure comes up.
