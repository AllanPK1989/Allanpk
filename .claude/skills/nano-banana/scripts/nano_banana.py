#!/usr/bin/env python3
"""
Nano Banana (Gemini image models) CLI.

Generates and edits images through the Gemini API `generateContent` endpoint.
Standard library only - no pip install required.

Auth:
    export GEMINI_API_KEY=...        # or GOOGLE_API_KEY

Usage:
    # text -> image
    ./nano_banana.py generate "a photoreal studio shot of a brass compass" -o out/compass.png

    # edit / re-render an existing image (repeat -i for multi-image composition)
    ./nano_banana.py generate "make the background a sunlit workshop" -i photo.jpg -o out/edit.png

    # 4K widescreen on the Pro model, 3 variants
    ./nano_banana.py generate "cutaway diagram of a jet engine, labelled" \
        --model pro --size 4K --aspect 16:9 -n 3 -o out/engine.png

    # what image models does this key actually have?
    ./nano_banana.py models
"""

import argparse
import base64
import json
import mimetypes
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

API_HOST = "https://generativelanguage.googleapis.com"

# Friendly aliases -> API model IDs. Verify against `nano_banana.py models`,
# which asks the API what this key can actually reach.
MODEL_ALIASES = {
    "flash": "gemini-3.1-flash-image",           # Nano Banana 2 - default workhorse
    "lite": "gemini-3.1-flash-lite-image",       # Nano Banana 2 Lite - cheapest/fastest
    "pro": "gemini-3-pro-image",                 # Nano Banana Pro - best text + 4K
    "legacy": "gemini-2.5-flash-image",          # original Nano Banana
}
DEFAULT_MODEL = "flash"

ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
IMAGE_SIZES = ["512", "1K", "2K", "4K"]

EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def api_key():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit(
            "No API key. Set GEMINI_API_KEY (or GOOGLE_API_KEY).\n"
            "Create one at https://aistudio.google.com/apikey"
        )
    return key


def ssl_context():
    """Honour a custom CA bundle when one is configured (corporate/agent proxies)."""
    bundle = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if bundle and os.path.exists(bundle):
        return ssl.create_default_context(cafile=bundle)
    return ssl.create_default_context()


def request_json(url, payload=None, method="GET", retries=4):
    """POST/GET JSON with exponential backoff on 429 and 5xx."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"x-goog-api-key": api_key(), "Content-Type": "application/json"}
    delay = 2.0

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=ssl_context(), timeout=300) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                sys.stderr.write(f"  HTTP {e.code}, retrying in {delay:.0f}s...\n")
                time.sleep(delay)
                delay *= 2
                continue
            sys.exit(explain_http_error(e.code, body))
        except urllib.error.URLError as e:
            if attempt < retries:
                sys.stderr.write(f"  network error ({e.reason}), retrying in {delay:.0f}s...\n")
                time.sleep(delay)
                delay *= 2
                continue
            sys.exit(f"Network error reaching the Gemini API: {e.reason}")


def explain_http_error(code, body):
    hints = {
        400: "Bad request - usually an unsupported model ID, aspectRatio, or imageSize "
             "for this model. Run `nano_banana.py models` to see valid IDs.",
        403: "Forbidden - the API key is invalid, or image generation is not enabled "
             "for this key/region.",
        404: "Model not found - the ID does not exist on this API version. "
             "Run `nano_banana.py models`, or retry with --api-version v1beta.",
        429: "Rate limit or quota exhausted. Free-tier image quotas are small; "
             "wait, or use --model lite.",
    }
    hint = hints.get(code, "")
    return f"Gemini API error {code}. {hint}\n\n{body[:2000]}"


def inline_part(path):
    """Read a local image into an inlineData part."""
    if not os.path.isfile(path):
        sys.exit(f"Input image not found: {path}")
    mime = mimetypes.guess_type(path)[0] or "image/png"
    if not mime.startswith("image/"):
        sys.exit(f"Not an image file: {path} (detected {mime})")
    with open(path, "rb") as f:
        return {"inlineData": {"mimeType": mime, "data": base64.b64encode(f.read()).decode()}}


def build_payload(args, prompt):
    parts = [inline_part(p) for p in (args.image or [])]
    parts.append({"text": prompt})

    image_config = {}
    if args.aspect:
        image_config["aspectRatio"] = args.aspect
    if args.size:
        image_config["imageSize"] = args.size

    generation_config = {"responseModalities": ["TEXT", "IMAGE"]}
    if image_config:
        generation_config["imageConfig"] = image_config
    if args.temperature is not None:
        generation_config["temperature"] = args.temperature

    payload = {"contents": [{"role": "user", "parts": parts}], "generationConfig": generation_config}
    if args.system:
        payload["systemInstruction"] = {"parts": [{"text": args.system}]}
    return payload


def save_images(response, out_path, suffix=""):
    """Write every inline image in the response; return list of written paths."""
    written, notes = [], []
    root, ext = os.path.splitext(out_path)
    candidates = response.get("candidates") or []

    if not candidates:
        block = (response.get("promptFeedback") or {}).get("blockReason")
        if block:
            sys.exit(f"Prompt blocked by safety filters (reason: {block}). Rephrase and retry.")
        sys.exit(f"No candidates returned:\n{json.dumps(response)[:1500]}")

    blobs = []
    for cand in candidates:
        finish = cand.get("finishReason")
        if finish and finish not in ("STOP", "MAX_TOKENS"):
            notes.append(f"finishReason={finish}")
        for part in (cand.get("content") or {}).get("parts") or []:
            if "inlineData" in part:
                blobs.append(part["inlineData"])
            elif part.get("text"):
                notes.append(part["text"].strip())

    for i, blob in enumerate(blobs, start=1):
        out_ext = ext or EXT_BY_MIME.get(blob.get("mimeType", "image/png"), ".png")
        seq = f"_{i}" if len(blobs) > 1 else ""
        path = f"{root}{suffix}{seq}{out_ext}"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as f:
            f.write(base64.b64decode(blob["data"]))
        written.append(path)

    if not written:
        detail = " | ".join(notes) or json.dumps(response)[:1000]
        sys.exit(
            "The model returned no image. This usually means the prompt was refused "
            f"or read as a question rather than an image request.\nModel said: {detail}"
        )

    for note in notes:
        if note:
            sys.stderr.write(f"  model: {note[:400]}\n")
    return written


def cmd_generate(args):
    prompt = args.prompt
    if prompt == "-":
        prompt = sys.stdin.read()
    if args.prompt_file:
        with open(args.prompt_file) as f:
            prompt = f.read()
    prompt = prompt.strip()
    if not prompt:
        sys.exit("Empty prompt.")

    model = MODEL_ALIASES.get(args.model, args.model)
    if args.aspect and args.aspect not in ASPECT_RATIOS:
        sys.stderr.write(f"  warning: unusual aspect ratio {args.aspect} (known: {', '.join(ASPECT_RATIOS)})\n")
    if args.size and args.size not in IMAGE_SIZES:
        sys.stderr.write(f"  warning: unusual size {args.size} (known: {', '.join(IMAGE_SIZES)})\n")

    payload = build_payload(args, prompt)
    url = f"{API_HOST}/{args.api_version}/models/{model}:generateContent"

    if args.dry_run:
        redacted = json.loads(json.dumps(payload))
        for part in redacted["contents"][0]["parts"]:
            if "inlineData" in part:
                part["inlineData"]["data"] = f"<{len(part['inlineData']['data'])} base64 chars>"
        print(f"POST {url}\n{json.dumps(redacted, indent=2)}")
        return

    all_written = []
    for i in range(args.n):
        if args.n > 1:
            sys.stderr.write(f"  variant {i + 1}/{args.n}...\n")
        response = request_json(url, payload, method="POST")
        all_written += save_images(response, args.output, suffix=f"_v{i + 1}" if args.n > 1 else "")

    for path in all_written:
        size_kb = os.path.getsize(path) / 1024
        print(f"{path} ({size_kb:.0f} KB)")


def cmd_models(args):
    data = request_json(f"{API_HOST}/{args.api_version}/models?pageSize=200")
    rows = []
    for m in data.get("models", []):
        name = m.get("name", "").replace("models/", "")
        methods = m.get("supportedGenerationMethods", []) or m.get("supportedActions", [])
        if "image" in name and ("generateContent" in methods or not methods):
            rows.append((name, m.get("displayName", ""), m.get("description", "")[:80]))
    if not rows:
        print("No image-capable models visible to this key. Check the key's project and region.")
        return
    print(f"{'MODEL ID':<38} DISPLAY NAME")
    for name, display, _ in sorted(rows):
        alias = next((a for a, mid in MODEL_ALIASES.items() if mid == name), "")
        tag = f"  [--model {alias}]" if alias else ""
        print(f"{name:<38} {display}{tag}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate and edit images with Gemini image models (Nano Banana).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate or edit an image", aliases=["gen", "edit"])
    gen.add_argument("prompt", nargs="?", default="", help="prompt text, or '-' to read stdin")
    gen.add_argument("--prompt-file", help="read the prompt from a file instead")
    gen.add_argument("-i", "--image", action="append", metavar="PATH",
                     help="input image to edit or use as reference (repeatable, up to ~3 subjects)")
    gen.add_argument("-o", "--output", default="output.png", help="output path (default: output.png)")
    gen.add_argument("-m", "--model", default=DEFAULT_MODEL,
                     help=f"alias or full model ID. Aliases: {', '.join(MODEL_ALIASES)} (default: {DEFAULT_MODEL})")
    gen.add_argument("-a", "--aspect", help=f"aspect ratio: {', '.join(ASPECT_RATIOS)}")
    gen.add_argument("-s", "--size", help=f"image size: {', '.join(IMAGE_SIZES)} (2K/4K need --model pro)")
    gen.add_argument("-n", type=int, default=1, help="number of variants to request (separate calls)")
    gen.add_argument("--temperature", type=float, help="sampling temperature")
    gen.add_argument("--system", help="system instruction (persistent style/role guidance)")
    gen.add_argument("--dry-run", action="store_true", help="print the request instead of sending it")
    gen.set_defaults(func=cmd_generate)

    models = sub.add_parser("models", help="list image models available to this API key")
    models.set_defaults(func=cmd_models)

    for p in (gen, models):
        p.add_argument("--api-version", default="v1beta", choices=["v1beta", "v1"],
                       help="API version (default: v1beta)")

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
