"""Command line: python -m pipeline [--channel ta|en] <command> ...  (run from finance-channel/).

--channel picks the YouTube channel (default ta; see channels/). Each channel
has its own scripts, queue and approval issues.

  lint [ids]           validate scripts (structure + compliance)
  sheet ID             contact sheet of every scene (fast visual check)
  render ID            render MP4s (+ thumbnail) into out/ID/
  daily                pick the next topic, generate a script if needed, lint, render, write issue.md
  publish ID           upload an approved topic (or write the manual posting kit)
  reserve ID           claim the next free publish slot (before uploading)
  mark ID --status ..  update state/items/ID.json
  generate [ID]        write a Tamil script with Claude for the next topic without one
  translate [IDs]      write this channel's script from the Tamil one with Claude (e.g. --channel en)
  status               show the queue
  voice-script ID      sentence list for the recorder page (voice-scripts/ID.json)
  voice-import ID ZIP  clean the recorder's zip into WAVs for --voice-dir
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


def _outdir(base: str, topic_id: str) -> Path:
    """out/ID for the Tamil channel, out/<channel>/ID for the others."""
    from .config import DEFAULT_CHANNEL, channel_id
    ch = channel_id()
    return Path(base) / topic_id if ch == DEFAULT_CHANNEL else Path(base) / ch / topic_id


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


def _render(s, fmts, out: Path, tts=None, voice_dir: Path | None = None) -> dict:
    from .render import render_thumbnail, render_video
    infos = {}
    for f in fmts:
        t0 = time.time()
        infos[f] = render_video(s, f, out, engine=tts, voice_dir=voice_dir)
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
    _render(s, _formats(a.format), _outdir(a.out, s.id), a.tts, Path(a.voice_dir) if a.voice_dir else None)


def _write_script(tid: str):
    """Write the missing script for this channel: the Tamil one with Claude, then (other channels) translate it."""
    from . import generate, translate
    from .config import lang
    if not generate.available():
        print(f"error: topic {tid} has no script and ANTHROPIC_API_KEY is not set, "
              "so it can't be written automatically. Add the script or the secret.")
        return None
    if translate.source_script(tid) is None:
        print(f"generated {generate.generate(tid)}")
    if lang() == "ta":
        return translate.source_script(tid)
    return translate.translate(tid)


def cmd_daily(a):
    from . import state
    from .compliance import lint
    from .config import config, lang, release_tag
    from .review import issue_body
    from .script import find_script, load_script

    if a.topic:
        tid = str(a.topic).zfill(3)
    else:
        if not config()["channel"].get("daily", True):
            _out(skip="true", reason="the daily video is switched off for this channel (channel.daily)")
            return 0
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
            path = _write_script(tid)
            if path is None:
                return 1
            print(f"generated {path}")
            _out(generated=str(path))
    if a.topic and lang() != "ta" and not find_script(tid):  # e.g. the English version of a rendered Tamil topic
        path = _write_script(tid)
        if path is None:
            return 1
        _out(generated=str(path))

    s = load_script(tid)
    rep = lint(s)
    if rep.errors:
        print("\n".join(f"error: {e}" for e in rep.errors))
        return 1
    out = _outdir(a.out, s.id)
    voice_dir = Path(a.voice_dir) if a.voice_dir else None
    if voice_dir and not a.topic:
        print("error: --voice-dir needs --topic")
        return 1
    infos = _render(s, _formats(None), out, a.tts, voice_dir)
    from .voice import write_voice_script
    write_voice_script(s)
    repo_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', 'OWNER/REPO')}"
    tag = release_tag(s.id)
    assets = f"{repo_url}/releases/download/{tag}/"
    body = issue_body(s, infos, rep, assets, repo_url, state.next_slot())
    (out / "issue.md").write_text(body, encoding="utf-8")
    title = f"🎬 {config()['channel'].get('issue_tag', '')}Approve #{int(s.id)}: {s.title}" + (f" ({s.subtitle})" if s.subtitle else "")
    _out(skip="false", topic=s.id, tag=tag, title=title, dir=str(out))


def cmd_publish(a):
    from . import state, youtube
    from .config import config, release_tag
    from .metadata import video_body
    from .review import manual_kit, published_comment
    from .script import load_script

    s = load_script(a.topic)
    d = Path(a.dir) if a.dir else _outdir("out", s.id)
    fmts = _formats(a.only)
    infos = {f: json.loads((d / f"{s.id}-{f}.json").read_text(encoding="utf-8")) for f in fmts
             if (d / f"{s.id}-{f}.json").exists()}
    if not infos:
        print(f"error: no rendered videos in {d}")
        return 1
    item = state.get(s.id)
    if a.now:
        slot = None
    elif item.get("status") == "publishing" and item.get("publish_at"):
        slot = datetime.fromisoformat(item["publish_at"]).astimezone(state.tz())  # reserved by `reserve`
    else:
        slot = state.next_slot(ignore=s.id)
    publish_at = slot.astimezone().isoformat() if slot else datetime.now().astimezone().isoformat()
    repo_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', 'OWNER/REPO')}"
    assets = f"{repo_url}/releases/download/{release_tag(s.id)}/"

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


def cmd_reserve(a):
    """Claim the next free publish slot for a topic (committed before uploading)."""
    from . import state
    slot = None if a.now else state.next_slot(ignore=a.topic)
    when = (slot or datetime.now(state.tz())).isoformat()
    state.update(a.topic, status="publishing", publish_at=when)
    print(f"reserved {a.topic} for {when}")


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


def cmd_translate(a):
    from . import state, translate
    from .config import curriculum
    from .script import find_script
    tids = [str(t).zfill(3) for t in a.topics]
    if not tids:  # the next topic in this channel's queue that has a Tamil script but no translation
        rendered = state.load()["items"]
        tids = [next((str(t["id"]).zfill(3) for t in curriculum()
                      if str(t["id"]).zfill(3) not in rendered and not find_script(str(t["id"]))
                      and translate.source_script(str(t["id"]))), None)]
        if tids == [None]:
            print("every topic with a Tamil script already has a translation")
            return 0
    bad = 0
    for tid in tids:
        if find_script(tid):
            print(f"{tid}: already translated")
            continue
        try:
            print(translate.translate(tid))
        except Exception as e:  # noqa: BLE001 - report and carry on with the rest
            print(f"{tid}: {e}")
            bad += 1
    return 1 if bad else 0


def cmd_voice_script(a):
    from .script import load_script
    from .voice import write_voice_script
    for t in a.topics:
        print(write_voice_script(load_script(t)))


def cmd_voice_import(a):
    from .config import CACHE
    from .script import load_script
    from .voice import import_zip, report_markdown
    s = load_script(a.topic)
    out = Path(a.dir) if a.dir else CACHE / "voice" / s.id
    rep = import_zip(s, Path(a.zip), out)
    text = report_markdown(rep)
    Path(a.report).write_text(text, encoding="utf-8")
    print(text)
    _out(voice_dir=str(out), complete="false" if rep["missing"] or rep["too_short"] else "true")
    return 1 if rep["missing"] or rep["too_short"] else 0


def cmd_status(a):
    from . import state
    from .config import curriculum, lang
    from .script import find_script
    items = state.load()["items"]
    for t in curriculum():
        tid = str(t["id"]).zfill(3)
        st = items.get(tid, {}).get("status", "-")
        script = "script" if find_script(tid) else "      "
        print(f"{tid}  {script}  {st:18s} {t['category']:12s} {t.get('title_' + lang()) or t['title_en']}")
    print(f"\nnext publish slot: {state.next_slot():%a %d %b %H:%M %Z}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--channel", help="which YouTube channel (default: $FINANCE_CHANNEL or ta)")
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
    p.add_argument("--voice-dir", help="use your recorded clips (from voice-import) instead of TTS")
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("daily"); p.add_argument("--topic")
    p.add_argument("--voice-dir", help="use your recorded clips (from voice-import) instead of TTS")
    p.add_argument("--tts", choices=["edge", "silent"], default=None)
    p.add_argument("--out", default="out"); p.set_defaults(fn=cmd_daily)

    p = sub.add_parser("publish"); p.add_argument("topic")
    p.add_argument("--dir"); p.add_argument("--now", action="store_true")
    p.add_argument("--only", choices=["short", "long"])
    p.add_argument("--comment-file", default="comment.md"); p.set_defaults(fn=cmd_publish)

    p = sub.add_parser("reserve"); p.add_argument("topic"); p.add_argument("--now", action="store_true")
    p.set_defaults(fn=cmd_reserve)

    p = sub.add_parser("mark"); p.add_argument("topic")
    p.add_argument("--status", required=True,
                   choices=["awaiting_approval", "rejected", "scheduled", "published", "approved_manual"])
    p.add_argument("--issue"); p.add_argument("--release"); p.add_argument("--reason")
    p.set_defaults(fn=cmd_mark)

    p = sub.add_parser("generate"); p.add_argument("topic", nargs="?"); p.set_defaults(fn=cmd_generate)
    p = sub.add_parser("translate"); p.add_argument("topics", nargs="*"); p.set_defaults(fn=cmd_translate)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)

    p = sub.add_parser("voice-script"); p.add_argument("topics", nargs="+")
    p.set_defaults(fn=cmd_voice_script)

    p = sub.add_parser("voice-import"); p.add_argument("topic"); p.add_argument("zip")
    p.add_argument("--dir", help="where to put the cleaned WAVs (default .cache/voice/ID)")
    p.add_argument("--report", default="voice-report.md", help="markdown summary for the approval issue")
    p.set_defaults(fn=cmd_voice_import)

    a = ap.parse_args(argv)
    if a.channel:
        from .config import channel_ids
        if a.channel not in channel_ids():
            ap.error(f"unknown channel {a.channel!r} (have: {', '.join(channel_ids())})")
        os.environ["FINANCE_CHANNEL"] = a.channel
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
