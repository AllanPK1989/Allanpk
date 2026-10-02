"""Command line: python -m pipeline <command> ...  (run from finance-channel/).

  lint [ids]           validate scripts (structure + compliance)
  sheet ID             contact sheet of every scene (fast visual check)
  render ID            render MP4s (+ thumbnail) into out/ID/
  daily                pick the next topic, generate a script if needed, lint, render, write issue.md
  publish ID           upload an approved topic (or write the manual posting kit)
  mark ID --status ..  update state/state.json
  generate [ID]        write a script with Claude for the next topic without one
  status               show the queue
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _out(**kv):
    """Write step outputs for GitHub Actions (and echo them)."""
    path = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"{k}={v}")
        if path:
            with open(path, "a", encoding="utf-8") as f:
                if "\n" in str(v):
                    f.write(f"{k}<<__EOF__\n{v}\n__EOF__\n")
                else:
                    f.write(f"{k}={v}\n")


def _formats(a_format: str | None) -> list[str]:
    from .config import config
    if a_format in ("short", "long"):
        return [a_format]
    return list(config()["publish"].get("formats", ["short", "long"]))


def cmd_lint(a):
    from .compliance import lint
    from .script import all_scripts, load_script
    scripts = [load_script(t) for t in a.topics] if a.topics else all_scripts()
    bad = 0
    for s in scripts:
        rep = lint(s)
        mark = "✗" if rep.errors else ("!" if rep.warnings else "✓")
        print(f"{mark} {s.path.name}")
        for e in rep.errors:
            print(f"    error: {e}")
        for w in rep.warnings:
            print(f"    warn:  {w}")
        bad += bool(rep.errors)
    print(f"\n{len(scripts)} scripts, {bad} with errors")
    return 1 if bad else 0


def cmd_sheet(a):
    from .render import contact_sheet
    from .script import load_script
    s = load_script(a.topic)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in _formats(a.format):
        print(contact_sheet(s, f, out / f"{s.id}-{f}-sheet.png"))


def _render(s, fmts, out: Path, tts=None) -> dict:
    from .render import render_thumbnail, render_video
    infos = {}
    for f in fmts:
        t0 = time.time()
        infos[f] = render_video(s, f, out, engine=tts)
        print(f"[{s.id}] {f}: {infos[f]['duration']:.1f}s video, {infos[f]['shots']} shots, {time.time() - t0:.0f}s to render")
    if "long" in fmts:
        render_thumbnail(s, out / f"{s.id}-thumb.png")
    return infos


def cmd_render(a):
    from .compliance import lint
    from .script import load_script
    s = load_script(a.topic)
    rep = lint(s)
    if rep.errors and not a.force:
        print("\n".join(f"error: {e}" for e in rep.errors))
        return 1
    _render(s, _formats(a.format), Path(a.out) / s.id, a.tts)


def cmd_daily(a):
    from . import generate, state
    from .compliance import lint
    from .config import config
    from .review import issue_body
    from .script import load_script

    if a.topic:
        tid = str(a.topic).zfill(3)
    else:
        waiting = state.pending()
        limit = int(config()["publish"].get("max_pending_approvals", 3))
        if len(waiting) >= limit:
            _out(skip="true", reason=f"{len(waiting)} videos already waiting for approval ({', '.join(waiting)})")
            return 0
        nxt = state.next_topic()
        if not nxt:
            _out(skip="true", reason="every curriculum topic has been rendered; add topics to curriculum.yaml")
            return 0
        tid, has_script = nxt
        if not has_script:
            if not generate.available():
                print(f"error: topic {tid} has no script in content/ and ANTHROPIC_API_KEY is not set, "
                      "so it can't be written automatically. Add the script or the secret.")
                return 1
            path = generate.generate(tid)
            print(f"generated {path}")
            _out(generated=str(path))

    s = load_script(tid)
    rep = lint(s)
    if rep.errors:
        print("\n".join(f"error: {e}" for e in rep.errors))
        return 1
    out = Path(a.out) / s.id
    infos = _render(s, _formats(None), out, a.tts)
    repo_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', 'OWNER/REPO')}"
    tag = f"video-{s.id}"
    assets = f"{repo_url}/releases/download/{tag}/"
    body = issue_body(s, infos, rep, assets, repo_url, state.next_slot())
    (out / "issue.md").write_text(body, encoding="utf-8")
    title = f"🎬 Approve #{int(s.id)}: {s['title_ta']} ({s.get('title_en', '')})"
    _out(skip="false", topic=s.id, tag=tag, title=title, dir=str(out))


def cmd_publish(a):
    from . import state, youtube
    from .config import config
    from .metadata import video_body
    from .review import manual_kit, published_comment
    from .script import load_script

    s = load_script(a.topic)
    d = Path(a.dir or f"out/{s.id}")
    fmts = _formats(a.only)
    infos = {f: json.loads((d / f"{s.id}-{f}.json").read_text(encoding="utf-8")) for f in fmts
             if (d / f"{s.id}-{f}.json").exists()}
    if not infos:
        print(f"error: no rendered videos in {d}")
        return 1
    slot = None if a.now else state.next_slot()
    publish_at = slot.astimezone().isoformat() if slot else datetime.now().astimezone().isoformat()
    repo_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', 'OWNER/REPO')}"
    assets = f"{repo_url}/releases/download/video-{s.id}/"

    if config()["publish"].get("mode", "manual") != "youtube" or not youtube.configured():
        text = manual_kit(s, infos, assets, slot)
        state.update(s.id, status="approved_manual", publish_at=publish_at, formats=list(infos))
    else:
        uploaded: dict[str, str] = {}
        when = slot.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if slot else None
        if "long" in infos:
            body = video_body(s, "long", infos["long"], when, None)
            uploaded["long"] = youtube.upload(d / infos["long"]["file"], body, d / f"{s.id}-thumb.png")
        if "short" in infos:
            other = f"https://youtu.be/{uploaded['long']}" if "long" in uploaded else None
            body = video_body(s, "short", infos["short"], when, other)
            uploaded["short"] = youtube.upload(d / infos["short"]["file"], body)
        state.update(s.id, status="scheduled" if slot else "published", publish_at=publish_at,
                     youtube={f: {"id": v, "url": f"https://youtu.be/{v}"} for f, v in uploaded.items()})
        text = published_comment(s, uploaded, slot)
    Path(a.comment_file).write_text(text, encoding="utf-8")
    print(text)


def cmd_mark(a):
    from . import state
    fields = {"status": a.status}
    if a.issue:
        fields["issue"] = int(a.issue)
    if a.release:
        fields["release"] = a.release
    if a.reason:
        fields["reason"] = a.reason
    print(json.dumps(state.update(a.topic, **fields), ensure_ascii=False, indent=1))


def cmd_generate(a):
    from . import generate, state
    tid = a.topic
    if not tid:
        nxt = state.next_topic()
        if not nxt or nxt[1]:
            from .config import curriculum
            from .script import find_script
            tid = next((str(t["id"]).zfill(3) for t in curriculum() if not find_script(str(t["id"]))), None)
        else:
            tid = nxt[0]
    if not tid:
        print("every curriculum topic already has a script")
        return 0
    print(generate.generate(tid))


def cmd_status(a):
    from . import state
    from .config import curriculum
    from .script import find_script
    items = state.load()["items"]
    for t in curriculum():
        tid = str(t["id"]).zfill(3)
        st = items.get(tid, {}).get("status", "-")
        script = "script" if find_script(tid) else "      "
        print(f"{tid}  {script}  {st:18s} {t['category']:12s} {t['title_en']}")
    print(f"\nnext publish slot: {state.next_slot():%a %d %b %H:%M %Z}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lint"); p.add_argument("topics", nargs="*"); p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("sheet"); p.add_argument("topic")
    p.add_argument("--format", choices=["short", "long", "both"], default="both")
    p.add_argument("--out", default="out/sheets"); p.set_defaults(fn=cmd_sheet)

    p = sub.add_parser("render"); p.add_argument("topic")
    p.add_argument("--format", choices=["short", "long", "both"], default="both")
    p.add_argument("--tts", choices=["edge", "silent"], default=None, help="override config voice.engine")
    p.add_argument("--out", default="out")
    p.add_argument("--force", action="store_true", help="render even if lint finds errors")
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("daily"); p.add_argument("--topic")
    p.add_argument("--tts", choices=["edge", "silent"], default=None)
    p.add_argument("--out", default="out"); p.set_defaults(fn=cmd_daily)

    p = sub.add_parser("publish"); p.add_argument("topic")
    p.add_argument("--dir"); p.add_argument("--now", action="store_true")
    p.add_argument("--only", choices=["short", "long"])
    p.add_argument("--comment-file", default="comment.md"); p.set_defaults(fn=cmd_publish)

    p = sub.add_parser("mark"); p.add_argument("topic")
    p.add_argument("--status", required=True,
                   choices=["awaiting_approval", "rejected", "scheduled", "published", "approved_manual"])
    p.add_argument("--issue"); p.add_argument("--release"); p.add_argument("--reason")
    p.set_defaults(fn=cmd_mark)

    p = sub.add_parser("generate"); p.add_argument("topic", nargs="?"); p.set_defaults(fn=cmd_generate)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)

    a = ap.parse_args(argv)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
