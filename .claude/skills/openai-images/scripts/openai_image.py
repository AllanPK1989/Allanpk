#!/usr/bin/env python3
"""
OpenAI Images CLI - GPT Image and DALL-E.

Generates, edits and varies images through the OpenAI Images API.
Standard library only - no pip install required.

Auth:
    export OPENAI_API_KEY=sk-...
    export OPENAI_BASE_URL=...   # optional, for proxies/gateways

Usage:
    # text -> image
    ./openai_image.py generate "a brass sextant on a navigator's chart" -o out/sextant.png

    # transparent-background asset at an exact size
    ./openai_image.py generate "a flat vector maple leaf icon" \
        --background transparent --size 1024x1024 -o out/leaf.png

    # edit, with an optional mask (transparent pixels = the area to change)
    ./openai_image.py edit "replace the sky with storm clouds" -i photo.png -o out/storm.png
    ./openai_image.py edit "add a brass lamp here" -i room.png --mask lamp_mask.png -o out/room.png

    # combine several inputs into one composition
    ./openai_image.py edit "put the product from image 1 on the desk in image 2" \
        -i product.png -i desk.png --input-fidelity high -o out/staged.png

    ./openai_image.py models
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
import uuid

DEFAULT_BASE = "https://api.openai.com/v1"

MODEL_ALIASES = {
    "best": "gpt-image-2",             # current flagship, arbitrary sizes up to 3840x2160
    "pinned": "gpt-image-2-2026-04-21",  # dated snapshot - use when output must not drift
    "mid": "gpt-image-1.5",
    "mini": "gpt-image-1-mini",        # cheapest GPT Image tier
    "legacy": "gpt-image-1",
    "chatgpt": "chatgpt-image-latest", # the model behind ChatGPT's image tool
    "dalle3": "dall-e-3",
    "dalle2": "dall-e-2",              # only model supporting /variations
}
DEFAULT_MODEL = "best"

GPT_IMAGE_PREFIXES = ("gpt-image", "chatgpt-image")
DALLE3_SIZES = {"1024x1024", "1792x1024", "1024x1792"}
DALLE2_SIZES = {"256x256", "512x512", "1024x1024"}
STANDARD_SIZES = {"1024x1024", "1536x1024", "1024x1536", "auto"}


def is_gpt_image(model):
    return model.startswith(GPT_IMAGE_PREFIXES)


def api_key():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("No API key. Set OPENAI_API_KEY.\nCreate one at https://platform.openai.com/api-keys")
    return key


def base_url():
    return os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE).rstrip("/")


def ssl_context():
    bundle = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if bundle and os.path.exists(bundle):
        return ssl.create_default_context(cafile=bundle)
    return ssl.create_default_context()


def headers(extra=None):
    h = {"Authorization": f"Bearer {api_key()}"}
    if os.environ.get("OPENAI_ORG_ID"):
        h["OpenAI-Organization"] = os.environ["OPENAI_ORG_ID"]
    h.update(extra or {})
    return h


def send(url, data=None, content_type=None, method="GET", retries=4):
    extra = {"Content-Type": content_type} if content_type else {}
    delay = 2.0
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers(extra), method=method)
        try:
            with urllib.request.urlopen(req, context=ssl_context(), timeout=600) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                sys.stderr.write(f"  HTTP {e.code}, retrying in {delay:.0f}s...\n")
                time.sleep(delay)
                delay *= 2
                continue
            sys.exit(explain(e.code, body))
        except urllib.error.URLError as e:
            if attempt < retries:
                sys.stderr.write(f"  network error ({e.reason}), retrying in {delay:.0f}s...\n")
                time.sleep(delay)
                delay *= 2
                continue
            sys.exit(f"Network error reaching the OpenAI API: {e.reason}")


def explain(code, body):
    try:
        msg = json.loads(body)["error"]["message"]
    except Exception:
        msg = body[:800]
    hints = {
        400: "Usually an unsupported parameter for this model - `style` and `response_format` "
             "are DALL-E only; `background` and `output_format` are GPT Image only.",
        401: "Invalid API key.",
        403: "Model not available to this account, or the org is not verified. "
             "GPT Image models require organisation verification.",
        404: "Unknown model ID. Run `openai_image.py models`.",
        429: "Rate limit or insufficient quota. Check billing at platform.openai.com/usage.",
    }
    return f"OpenAI API error {code}: {msg}\n\n{hints.get(code, '')}"


def multipart(fields, files):
    """Build a multipart/form-data body. files: list of (field_name, path)."""
    boundary = f"----openai{uuid.uuid4().hex}"
    out = bytearray()
    for name, value in fields.items():
        if value is None:
            continue
        out += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
    for name, path in files:
        if not os.path.isfile(path):
            sys.exit(f"File not found: {path}")
        mime = mimetypes.guess_type(path)[0] or "image/png"
        with open(path, "rb") as f:
            blob = f.read()
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; "
                f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: {mime}\r\n\r\n").encode()
        out += blob + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def save(response, out_path, fmt="png"):
    items = response.get("data") or []
    if not items:
        sys.exit(f"No images returned:\n{json.dumps(response)[:1200]}")

    root, ext = os.path.splitext(out_path)
    ext = ext or f".{fmt}"
    written = []
    for i, item in enumerate(items, start=1):
        seq = f"_{i}" if len(items) > 1 else ""
        path = f"{root}{seq}{ext}"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if item.get("b64_json"):
            blob = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            with urllib.request.urlopen(item["url"], context=ssl_context(), timeout=300) as r:
                blob = r.read()
        else:
            sys.exit(f"Response item had neither b64_json nor url: {json.dumps(item)[:400]}")
        with open(path, "wb") as f:
            f.write(blob)
        written.append(path)
        if item.get("revised_prompt"):
            sys.stderr.write(f"  revised prompt: {item['revised_prompt'][:500]}\n")

    usage = response.get("usage") or {}
    if usage:
        sys.stderr.write(f"  tokens: {usage.get('total_tokens', '?')}\n")
    return written


def check_size(model, size):
    if not size or size == "auto":
        return
    if model == "dall-e-3" and size not in DALLE3_SIZES:
        sys.stderr.write(f"  warning: dall-e-3 supports only {', '.join(sorted(DALLE3_SIZES))}\n")
    elif model == "dall-e-2" and size not in DALLE2_SIZES:
        sys.stderr.write(f"  warning: dall-e-2 supports only {', '.join(sorted(DALLE2_SIZES))}\n")
    elif is_gpt_image(model) and size not in STANDARD_SIZES:
        try:
            w, h = (int(x) for x in size.lower().split("x"))
        except ValueError:
            sys.exit(f"--size {size!r} must be WIDTHxHEIGHT, or one of {', '.join(sorted(STANDARD_SIZES))}")
        problems = []
        if w % 16 or h % 16:
            problems.append("both dimensions must be divisible by 16")
        if not (1 / 3) <= w / h <= 3:
            problems.append("aspect ratio must be between 1:3 and 3:1")
        if w > 3840 or h > 2160:
            problems.append("maximum is 3840x2160")
        if problems:
            sys.stderr.write("  warning: arbitrary sizes are a gpt-image-2 feature and this one is "
                             f"invalid - {'; '.join(problems)}\n")


def common_fields(args, model):
    """Parameters shared by generate and edit, filtered to what the model accepts."""
    fields = {"model": model, "prompt": args.prompt, "n": str(args.n)}
    if args.size:
        fields["size"] = args.size
    if args.quality:
        fields["quality"] = args.quality
    if args.user:
        fields["user"] = args.user

    if is_gpt_image(model):
        if args.background:
            fields["background"] = args.background
        if args.output_format:
            fields["output_format"] = args.output_format
        if args.output_compression is not None:
            fields["output_compression"] = str(args.output_compression)
        if args.moderation:
            fields["moderation"] = args.moderation
        for unsupported, name in ((args.style, "--style"), (args.response_format, "--response-format")):
            if unsupported:
                sys.stderr.write(f"  warning: {name} is DALL-E only; ignoring it for {model}\n")
    else:
        if args.style:
            fields["style"] = args.style
        if args.response_format:
            fields["response_format"] = args.response_format
        for unsupported, name in ((args.background, "--background"),
                                  (args.output_format, "--output-format"),
                                  (args.moderation, "--moderation")):
            if unsupported:
                sys.stderr.write(f"  warning: {name} is GPT Image only; ignoring it for {model}\n")
    return fields


def cmd_generate(args):
    model = MODEL_ALIASES.get(args.model, args.model)
    check_size(model, args.size)
    if model == "dall-e-3" and args.n > 1:
        sys.exit("dall-e-3 supports only n=1. Run the command repeatedly, or use a GPT Image model.")

    fields = common_fields(args, model)
    payload = {k: (int(v) if k in ("n", "output_compression") else v) for k, v in fields.items()}

    if args.dry_run:
        print(f"POST {base_url()}/images/generations\n{json.dumps(payload, indent=2)}")
        return

    response = send(f"{base_url()}/images/generations", json.dumps(payload).encode(),
                    "application/json", method="POST")
    for path in save(response, args.output, args.output_format or "png"):
        print(f"{path} ({os.path.getsize(path) / 1024:.0f} KB)")


def cmd_edit(args):
    model = MODEL_ALIASES.get(args.model, args.model)
    check_size(model, args.size)
    if not args.image:
        sys.exit("edit needs at least one -i/--image.")
    if model == "dall-e-2" and len(args.image) > 1:
        sys.exit("dall-e-2 edits accept a single image. Use a GPT Image model for multi-image input.")

    fields = common_fields(args, model)
    if args.input_fidelity and is_gpt_image(model):
        fields["input_fidelity"] = args.input_fidelity

    files = [("image[]" if len(args.image) > 1 else "image", p) for p in args.image]
    if args.mask:
        files.append(("mask", args.mask))

    if args.dry_run:
        print(f"POST {base_url()}/images/edits\nfields: {json.dumps(fields, indent=2)}\n"
              f"files: {files}")
        return

    body, ctype = multipart(fields, files)
    response = send(f"{base_url()}/images/edits", body, ctype, method="POST")
    for path in save(response, args.output, args.output_format or "png"):
        print(f"{path} ({os.path.getsize(path) / 1024:.0f} KB)")


def cmd_variation(args):
    fields = {"model": "dall-e-2", "n": str(args.n)}
    if args.size:
        fields["size"] = args.size
    if args.dry_run:
        print(f"POST {base_url()}/images/variations\n{json.dumps(fields, indent=2)}")
        return
    body, ctype = multipart(fields, [("image", args.image)])
    response = send(f"{base_url()}/images/variations", body, ctype, method="POST")
    for path in save(response, args.output):
        print(f"{path} ({os.path.getsize(path) / 1024:.0f} KB)")


def cmd_models(args):
    data = send(f"{base_url()}/models")
    ids = sorted(m["id"] for m in data.get("data", [])
                 if "image" in m["id"] or m["id"].startswith("dall-e"))
    if not ids:
        print("No image models visible to this key.")
        return
    for mid in ids:
        alias = next((a for a, m in MODEL_ALIASES.items() if m == mid), "")
        print(f"{mid:<32}{'  [--model ' + alias + ']' if alias else ''}")


def add_shared(p, with_prompt=True):
    if with_prompt:
        p.add_argument("prompt")
    p.add_argument("-o", "--output", default="output.png", help="output path (default: output.png)")
    p.add_argument("-m", "--model", default=DEFAULT_MODEL,
                   help=f"alias or model ID. Aliases: {', '.join(MODEL_ALIASES)} (default: {DEFAULT_MODEL})")
    p.add_argument("-n", type=int, default=1, help="number of images, 1-10 (dall-e-3: 1 only)")
    p.add_argument("-s", "--size", help="1024x1024 | 1536x1024 | 1024x1536 | auto, or WxH on gpt-image-2")
    p.add_argument("-q", "--quality", choices=["auto", "low", "medium", "high", "standard", "hd"],
                   help="GPT Image: auto/low/medium/high. DALL-E 3: standard/hd")
    p.add_argument("--background", choices=["transparent", "opaque", "auto"],
                   help="GPT Image only. transparent needs --output-format png or webp")
    p.add_argument("--output-format", choices=["png", "jpeg", "webp"], help="GPT Image only")
    p.add_argument("--output-compression", type=int, help="0-100, jpeg/webp only")
    p.add_argument("--moderation", choices=["auto", "low"], help="GPT Image only")
    p.add_argument("--style", choices=["vivid", "natural"], help="dall-e-3 only")
    p.add_argument("--response-format", choices=["url", "b64_json"], help="DALL-E only")
    p.add_argument("--user", help="end-user identifier for abuse monitoring")
    p.add_argument("--dry-run", action="store_true", help="print the request instead of sending it")


def main():
    parser = argparse.ArgumentParser(
        description="Generate and edit images with OpenAI GPT Image / DALL-E.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="text -> image", aliases=["gen"])
    add_shared(g)
    g.set_defaults(func=cmd_generate)

    e = sub.add_parser("edit", help="edit or compose from input images")
    add_shared(e)
    e.add_argument("-i", "--image", action="append", required=True,
                   help="input image (repeatable - GPT Image composes across several)")
    e.add_argument("--mask", help="PNG whose transparent pixels mark the region to change")
    e.add_argument("--input-fidelity", choices=["low", "high"],
                   help="high preserves faces, logos and fine detail from the inputs")
    e.set_defaults(func=cmd_edit)

    v = sub.add_parser("variation", help="variations of an image (dall-e-2 only)")
    v.add_argument("image")
    v.add_argument("-o", "--output", default="variation.png")
    v.add_argument("-n", type=int, default=1)
    v.add_argument("-s", "--size", choices=sorted(DALLE2_SIZES))
    v.add_argument("--dry-run", action="store_true")
    v.set_defaults(func=cmd_variation)

    m = sub.add_parser("models", help="list image models available to this key")
    m.set_defaults(func=cmd_models)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
