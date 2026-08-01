# Nano Banana / Gemini Image API Reference

Everything here goes through the standard Gemini `generateContent` endpoint. Image
generation is not a separate API - you ask a multimodal model to respond with an image.

(Imagen is a *different*, prompt-only image API. The older Imagen models are deprecated;
Nano Banana is the recommended path for both generation and editing.)

## Models

| Alias | Model ID | Notes |
|---|---|---|
| `flash` | `gemini-3.1-flash-image` | Nano Banana 2. Default. Balanced speed/quality. |
| `lite` | `gemini-3.1-flash-lite-image` | Nano Banana 2 Lite. Cheapest, fastest. |
| `pro` | `gemini-3-pro-image` | Nano Banana Pro. Best text rendering and fine detail; 2K/4K. |
| `legacy` | `gemini-2.5-flash-image` | Original Nano Banana (Aug 2025). |

Some IDs carry a `-preview` suffix while a model is in preview and drop it at GA, so a
`404` on a plausible ID usually means the suffix moved rather than that the model is gone.
Confirm against the live list:

```bash
scripts/nano_banana.py models
# equivalently:
curl -s "https://generativelanguage.googleapis.com/v1beta/models" \
  -H "x-goog-api-key: $GEMINI_API_KEY" | grep -i image
```

## Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent
Header: x-goog-api-key: $GEMINI_API_KEY
Header: Content-Type: application/json
```

`v1` also serves GA models. Preview models generally need `v1beta`.

## Request body

```json
{
  "contents": [
    {
      "role": "user",
      "parts": [
        { "inlineData": { "mimeType": "image/png", "data": "<base64>" } },
        { "text": "Make the background a sunlit workshop, keep the machine identical." }
      ]
    }
  ],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "imageConfig": {
      "aspectRatio": "16:9",
      "imageSize": "2K"
    }
  }
}
```

### generationConfig fields

| Field | Values | Notes |
|---|---|---|
| `responseModalities` | `["TEXT","IMAGE"]` | Must include `IMAGE`. Including `TEXT` is the safe default - the model often narrates what it did. |
| `imageConfig.aspectRatio` | `1:1 2:3 3:2 3:4 4:3 4:5 5:4 9:16 16:9 21:9` | Omit to let the model choose (it infers from input images when editing). |
| `imageConfig.imageSize` | `512 1K 2K 4K` | 2K/4K are Pro features; flash models silently return ~1K if asked for more. |
| `temperature` | `0.0-2.0` | Lower for literal reproduction, higher for variety. |

`systemInstruction` (a top-level sibling of `contents`) holds persistent style rules
across a series.

### Input images

Inline base64 in an `inlineData` part - fine up to roughly 20 MB of total request size.
Above that, upload via the Files API first and reference the returned `fileData.fileUri`.
Two or three reference images stay reliable; more than that and adherence degrades.

Accepted: `image/png`, `image/jpeg`, `image/webp`.

## Response body

```json
{
  "candidates": [{
    "content": {
      "role": "model",
      "parts": [
        { "text": "Here is the machine rendered in a factory setting." },
        { "inlineData": { "mimeType": "image/png", "data": "<base64>" } }
      ]
    },
    "finishReason": "STOP"
  }],
  "usageMetadata": { "promptTokenCount": 21, "candidatesTokenCount": 1290, "totalTokenCount": 1311 }
}
```

Walk `candidates[].content.parts[]` and take every part with `inlineData` - there can be
more than one, and text parts are interleaved. Images are billed as a flat token count
(around 1290 tokens for 1K/2K), so `usageMetadata` is how you audit spend.

## Error handling

| Code | Meaning | Action |
|---|---|---|
| 400 | Bad model ID, or an `imageConfig` value the model doesn't support | Check the model list; drop `imageSize` on flash models. |
| 403 | Key invalid, or image generation not enabled for the key/region | Regenerate the key in AI Studio. |
| 404 | Model ID not on this API version | Try `v1beta`, or the `-preview` suffix. |
| 429 | Quota / rate limit | Back off exponentially. Free-tier daily image quota is small. |
| 5xx | Transient | Retry with backoff. |

`scripts/nano_banana.py` already retries 429 and 5xx with exponential backoff and prints
an actionable hint for each of these.

### No image in a successful response

A `200` with only text means a refusal or a misread prompt. Check:

- `promptFeedback.blockReason` - the prompt itself was blocked.
- `candidates[].finishReason` - `IMAGE_SAFETY`, `PROHIBITED_CONTENT`, `RECITATION`.
- Prompt phrasing - a question ("what would this look like?") gets answered in words.
  Command it: "Generate an image of...".

## SDK equivalents

Python (`pip install google-genai`):

```python
from google import genai
from google.genai import types

client = genai.Client()  # reads GEMINI_API_KEY

response = client.models.generate_content(
    model="gemini-3.1-flash-image",
    contents=["Make the background a sunlit workshop", types.Part.from_bytes(
        data=open("machine.png", "rb").read(), mime_type="image/png")],
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K"),
    ),
)

for part in response.parts:
    if part.inline_data:
        part.as_image().save("out.png")
```

JavaScript (`npm i @google/genai`):

```js
import { GoogleGenAI } from "@google/genai";
const ai = new GoogleGenAI({});

const res = await ai.models.generateContent({
  model: "gemini-3.1-flash-image",
  contents: "A photoreal brass sextant on a navigator's chart",
  config: { responseModalities: ["TEXT", "IMAGE"], imageConfig: { aspectRatio: "3:2" } },
});

for (const part of res.candidates[0].content.parts) {
  if (part.inlineData) fs.writeFileSync("out.png", Buffer.from(part.inlineData.data, "base64"));
}
```

The SDKs use snake_case (Python) or camelCase (JS) for the same fields the REST body uses.
The bundled script deliberately avoids both so it runs with no install.

## Pricing (indicative - confirm before quoting to a user)

Billed per image as output tokens:

- Flash / Lite 1K-2K: roughly $0.03-0.04 per image
- Pro 1K-2K: roughly $0.13 per image
- Pro 4K: roughly $0.24 per image

Input images cost a small per-image token charge on top. A free tier exists with a low
daily image cap; a `429` on a fresh key is nearly always that cap, not a broken setup.

## Provenance

Every generated or edited image carries an invisible **SynthID** watermark, and Pro
outputs also carry C2PA content credentials. There is no opt-out. Google's SynthID
Detector can verify an image's origin. Mention this whenever a user asks about
authenticity, licensing, or whether output can pass as an unedited photograph.

## Related official docs

- Image generation guide: https://ai.google.dev/gemini-api/docs/image-generation
- Model list: https://ai.google.dev/gemini-api/docs/models
- Files API (for large inputs): https://ai.google.dev/gemini-api/docs/files
- API keys: https://aistudio.google.com/apikey
