#!/usr/bin/env python3
"""
Midjourney prompt builder, linter and permutation expander.

Midjourney has no public API - prompts are pasted into the web app
(midjourney.com/imagine) or the Discord bot. This script builds well-formed
prompts, catches parameter mistakes before you spend GPU minutes, and expands
permutation syntax so you can queue a batch.

Usage:
    # build a prompt
    ./mj_prompt.py build "a brass sextant on a navigator's chart" \
        --ar 3:2 --style raw --s 150 --no text

    # style reference + character lock
    ./mj_prompt.py build "the same explorer at a campfire" \
        --sref https://cdn.example/style.jpg --sw 400 --cref https://cdn.example/face.jpg

    # lint a prompt someone else wrote
    ./mj_prompt.py check "a cat --ar 3:2 --s 2000 --oref http://x.jpg --v 8.2"

    # expand {a,b,c} permutations into the full job list
    ./mj_prompt.py permute "a {red,blue} car in {rain,fog} --ar 16:9"
"""

import argparse
import itertools
import re
import sys

DEFAULT_VERSION = "8.2"

# (regex over the raw value, human range) - validation is advisory, not a gate.
RANGES = {
    "ar": (r"^\d{1,3}:\d{1,3}$", "W:H, e.g. 16:9 (max 1:2 to 2:1 on most versions)"),
    "s": (None, "0-1000, default 100"),
    "c": (None, "0-100, default 0"),
    "w": (None, "0-3000, default 0"),
    "q": (None, "1, 2 or 4 (higher = more GPU minutes)"),
    "seed": (None, "0-4294967295"),
    "sw": (None, "0-1000, default 100"),
    "cw": (None, "0-100, default 100 (0 = face only, 100 = face+hair+clothes)"),
    "ow": (None, "0-1000, default 100"),
    "exp": (None, "0-100"),
    "repeat": (None, "1-40, Pro/Mega plans only"),
    "stop": (None, "10-100"),
}
NUMERIC_BOUNDS = {
    "s": (0, 1000), "c": (0, 100), "w": (0, 3000), "seed": (0, 4294967295),
    "sw": (0, 1000), "cw": (0, 100), "ow": (0, 1000), "exp": (0, 100),
    "repeat": (1, 40), "stop": (10, 100),
}
NIJI_STYLES = {"cute", "expressive", "original", "scenic", "default"}


def lint(text):
    """Return a list of (level, message) for a raw Midjourney prompt string."""
    issues = []
    params = dict(re.findall(r"--(\w+)(?:\s+([^\-\s][^\s]*(?:\s+[^\-\s][^\s]*)*?))?(?=\s+--|$)", text))
    params = {k: (v or "").strip() for k, v in params.items()}

    version = params.get("v") or params.get("version") or DEFAULT_VERSION
    is_niji = "niji" in params

    for key, (pattern, human) in RANGES.items():
        if key not in params:
            continue
        val = params[key]
        if pattern and not re.match(pattern, val):
            issues.append(("error", f"--{key} {val!r} is malformed ({human})"))
            continue
        if key in NUMERIC_BOUNDS:
            try:
                num = float(val)
            except ValueError:
                issues.append(("error", f"--{key} {val!r} is not a number ({human})"))
                continue
            lo, hi = NUMERIC_BOUNDS[key]
            if not lo <= num <= hi:
                issues.append(("error", f"--{key} {val} is out of range ({human})"))

    if "q" in params and params["q"] not in {"1", "2", "4", ".25", ".5", "0.25", "0.5"}:
        issues.append(("error", f"--q {params['q']} invalid (use 1, 2 or 4)"))

    # Omni Reference is a v7 feature; the v8 series had not picked it up as of mid-2026.
    if "oref" in params and version.startswith("8"):
        issues.append(("error", "--oref (Omni Reference) is not supported on the V8 series. "
                                "Add --v 7, or use --sref/--cref instead."))
    if "ow" in params and "oref" not in params:
        issues.append(("warn", "--ow has no effect without --oref"))
    if "sw" in params and "sref" not in params:
        issues.append(("warn", "--sw has no effect without --sref"))
    if "cw" in params and "cref" not in params:
        issues.append(("warn", "--cw has no effect without --cref"))

    if is_niji and ("v" in params or "version" in params):
        issues.append(("error", "--niji and --v are mutually exclusive - pick one model"))
    if is_niji and params.get("style") and params["style"] not in NIJI_STYLES:
        issues.append(("warn", f"--style {params['style']} is not a niji style "
                               f"({', '.join(sorted(NIJI_STYLES))})"))
    if not is_niji and params.get("style") and params["style"] != "raw":
        issues.append(("warn", f"--style {params['style']} is unusual outside niji (expected 'raw')"))

    if "ar" in params:
        try:
            w, h = (int(x) for x in params["ar"].split(":"))
            if max(w / h, h / w) > 2.05:
                issues.append(("warn", f"--ar {params['ar']} is more extreme than 2:1 - "
                                       "expect stretched or repeated content"))
        except (ValueError, ZeroDivisionError):
            pass

    # Image prompts must lead.
    urls = re.findall(r"https?://\S+", text)
    for url in urls:
        before = text[:text.index(url)]
        if re.search(r"--(sref|cref|oref|p)\s*$", before.strip()):
            continue
        if before.strip() and not re.match(r"^(https?://\S+\s*)*$", before.strip()):
            issues.append(("warn", f"image prompt {url[:48]}... should come before the text, "
                                   "not after it"))

    if text.count("::") and re.search(r"::\s*-?\d*\.?\d*", text) is None:
        issues.append(("warn", "'::' used without a weight - that is valid but usually a typo"))

    if len(text) > 6000:
        issues.append(("warn", f"prompt is {len(text)} chars - very long prompts dilute each concept"))

    return issues


def build(args):
    parts = []
    for url in args.image or []:
        parts.append(url)
    parts.append(args.prompt.strip())

    def add(flag, value):
        if value is not None:
            parts.append(f"--{flag}" if value is True else f"--{flag} {value}")

    add("no", args.no)
    add("ar", args.ar)
    add("style", args.style)
    add("s", args.s)
    add("c", args.c)
    add("w", args.w)
    add("q", args.q)
    add("exp", args.exp)
    add("seed", args.seed)
    add("stop", args.stop)
    add("repeat", args.repeat)
    add("tile", args.tile or None)
    add("draft", args.draft or None)
    add("preview", args.preview or None)
    add("video", args.video or None)
    add("sref", args.sref)
    add("sw", args.sw)
    add("cref", args.cref)
    add("cw", args.cw)
    add("oref", args.oref)
    add("ow", args.ow)
    add("p", args.p if args.p != "" else True)
    if args.niji:
        add("niji", args.niji if args.niji is not True else None)
    elif args.v:
        add("v", args.v)

    prompt = " ".join(p for p in parts if p)
    report(prompt)


def report(prompt):
    print(prompt)
    issues = lint(prompt)
    if issues:
        print(file=sys.stderr)
        for level, msg in issues:
            marker = "ERROR" if level == "error" else "warn "
            print(f"  {marker} {msg}", file=sys.stderr)
    if any(level == "error" for level, _ in issues):
        sys.exit(1)


def permute(args):
    text = args.prompt
    groups = re.findall(r"\{([^{}]*)\}", text)
    if not groups:
        print(text)
        return
    options = [[o.strip() for o in g.split(",")] for g in groups]
    combos = list(itertools.product(*options))
    if len(combos) > args.max:
        sys.exit(f"{len(combos)} combinations exceeds --max {args.max}. "
                 "Midjourney charges per job - narrow the permutation or raise --max.")
    for combo in combos:
        out = text
        for choice in combo:
            out = re.sub(r"\{[^{}]*\}", choice, out, count=1)
        print(out)
    print(f"\n{len(combos)} jobs", file=sys.stderr)


def check(args):
    issues = lint(args.prompt)
    if not issues:
        print("No issues found.")
        return
    for level, msg in issues:
        print(f"{'ERROR' if level == 'error' else 'warn '} {msg}")
    if any(level == "error" for level, _ in issues):
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(
        description="Build, lint and expand Midjourney prompts (no API - output is paste-ready).",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="assemble a prompt from parts")
    b.add_argument("prompt", help="the descriptive text")
    b.add_argument("-i", "--image", action="append", help="image prompt URL (repeatable, goes first)")
    b.add_argument("--ar", help="aspect ratio, e.g. 3:2")
    b.add_argument("--v", default=None,
                   help=f"model version; omitted by default so your account setting applies "
                        f"(currently {DEFAULT_VERSION})")
    b.add_argument("--niji", nargs="?", const=True, help="use the niji anime model, optional version")
    b.add_argument("--style", help="'raw' for less opinionated output; niji styles: cute/expressive/original/scenic")
    b.add_argument("--s", help="stylize 0-1000 (default 100)")
    b.add_argument("--c", help="chaos 0-100")
    b.add_argument("--w", help="weird 0-3000")
    b.add_argument("--q", help="quality 1, 2 or 4")
    b.add_argument("--exp", help="experimental aesthetics 0-100")
    b.add_argument("--seed", help="seed for reproducibility")
    b.add_argument("--stop", help="stop early 10-100")
    b.add_argument("--repeat", help="run the job N times (Pro/Mega)")
    b.add_argument("--no", help="things to exclude, comma separated")
    b.add_argument("--sref", help="style reference URL, or 'random'")
    b.add_argument("--sw", help="style weight 0-1000 (default 100)")
    b.add_argument("--cref", help="character reference URL")
    b.add_argument("--cw", help="character weight 0-100")
    b.add_argument("--oref", help="omni reference URL (V7 only)")
    b.add_argument("--ow", help="omni weight 0-1000")
    b.add_argument("--p", nargs="?", const="", help="personalization, optional profile code")
    b.add_argument("--tile", action="store_true", help="seamless tiling texture")
    b.add_argument("--draft", action="store_true", help="draft mode - 24 fast low-res images")
    b.add_argument("--preview", action="store_true", help="preview mode (V8.2 early-access aesthetics)")
    b.add_argument("--video", action="store_true", help="animate the result")
    b.set_defaults(func=build)

    c = sub.add_parser("check", help="lint an existing prompt string")
    c.add_argument("prompt")
    c.set_defaults(func=check)

    m = sub.add_parser("permute", help="expand {a,b} permutation syntax into one prompt per line")
    m.add_argument("prompt")
    m.add_argument("--max", type=int, default=40, help="refuse to expand beyond N jobs (default 40)")
    m.set_defaults(func=permute)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
