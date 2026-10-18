"""Markdown for the GitHub approval issue and the manual posting kit."""
from __future__ import annotations

from datetime import datetime

from .compliance import Report
from .config import ROOT, channel_id, config, loc
from .metadata import _fmt_ts, description, tags, titles
from .script import Script, build_timeline
from .tts import clean_markup

COMMANDS = """### ✅ Approve or reject
Reply to this issue (or to the notification email) with one command:

| Command | What happens |
|---|---|
| `/approve` | publish both videos at the next free daily slot |
| `/approve now` | publish immediately |
| `/approve short` · `/approve long` | publish only one format |
| `/reject <reason>` | skip this topic; the next topic renders tomorrow |
| `/rerender` | render again after you edit the script file (link above) |
| `/voice` + attached zip | re-render both videos in **your recorded voice** (see 🎙️ above) |
"""


def recorder_url(repo_url: str, topic_id: str) -> str | None:
    """GitHub Pages address of the recorder for this repo (see .github/workflows/finance-pages.yml)."""
    rec = config().get("recording") or {}
    if not rec.get("enabled", True):
        return None
    base = rec.get("page_url")
    if not base:
        owner, repo = repo_url.rstrip("/").split("/")[-2:]
        base = f"https://{owner.lower()}.github.io/{repo}/"
    return f"{base.rstrip('/')}/?t={topic_id}"


def _slot_text(dt: datetime) -> str:
    return dt.strftime("%a %d %b %Y, %I:%M %p IST").replace(" 0", " ")


def _unique_sentences(s: Script) -> list:
    from .voice import voice_script
    return voice_script(s)["sentences"]


def issue_body(s: Script, infos: dict, rep: Report, assets_url: str, repo_url: str, slot: datetime) -> str:
    t = titles(s)
    lines = [f"<!-- video-id: {s.id} -->", f"<!-- channel: {channel_id()} -->",
             f"## 🎬 #{int(s.id)} · {s.title}",
             (f"**{s.subtitle}** · {s.cat_label} ({s.cat['en']})" if s.subtitle else
              f"**{loc(config()['channel'], 'brand')}** · {s.cat_label}"),
             "",
             "### 👀 Preview",
             "Tap a link to download and watch on your phone or computer."]
    if "short" in infos:
        lines.append(f"- 📱 **Short** ({_fmt_ts(infos['short']['duration'])}): [{s.id}-short.mp4]({assets_url}{s.id}-short.mp4)")
    if "long" in infos:
        lines.append(f"- 🖥️ **Long video** ({_fmt_ts(infos['long']['duration'])}): [{s.id}-long.mp4]({assets_url}{s.id}-long.mp4)")
        lines += ["", f"![thumbnail]({assets_url}{s.id}-thumb.png)"]
    rec = recorder_url(repo_url, s.id)
    voice = next(iter(infos.values()), {}).get("voice", "ai")
    if voice == "recorded":
        lines += ["", "🎙️ **Narrated in your recorded voice.**"]
    elif rec:
        lines += ["", f"🎙️ **Want it in your own voice?** [Open the recorder]({rec}): read the "
                      f"{len(_unique_sentences(s))} sentences, save the zip, then comment `/voice` here and attach it."]
    lines += ["", f"📅 If approved, goes live at the next free slot: **{_slot_text(slot)}**",
              f"📝 Script: [{s.path.name}]({repo_url}/blob/HEAD/finance-channel/{s.path.relative_to(ROOT).as_posix()})"
              + (" · ⚠️ *written by Claude, please read it*" if "by Claude" in s.path.read_text(encoding='utf-8')[:200] else ""),
              "", "### 🛡️ Compliance check"]
    lines.append("✅ No named stocks/funds/brokers · ✅ No buy/sell calls or targets · ✅ No return promises · "
                 "✅ Disclaimer spoken, on screen and in the description"
                 + (" · ✅ SEBI F&O risk statement" if s.category == "fno" else ""))
    if rep.warnings:
        lines += ["", "**Please double-check:**"] + [f"- ⚠️ {w}" for w in rep.warnings]
    lines += ["", "### 🏷️ Titles"]
    for f in infos:
        lines.append(f"- {f}: `{t[f]}`")
    for f in infos:
        tl = build_timeline(s, f)
        said = "\n".join(f"{i}. {clean_markup(seg.text)}" for i, seg in enumerate(tl.segments, 1))
        lines += ["", f"<details><summary>🗣️ What the voice says ({f})</summary>\n\n{said}\n\n</details>"]
    lines += ["", f"<details><summary>📄 Description (long)</summary>\n\n```\n{description(s, 'long', infos.get('long', {}))}\n```\n</details>",
              "", COMMANDS]
    return "\n".join(lines)


def manual_kit(s: Script, infos: dict, assets_url: str, slot: datetime | None) -> str:
    """Posting instructions for when automatic YouTube upload isn't enabled yet."""
    t = titles(s)
    when = _slot_text(slot) if slot else "now"
    out = [f"### 📤 Ready to post: #{int(s.id)} {s.title}",
           "Automatic upload is off (`publish.mode: manual` in config.yaml), so here is everything you need. "
           f"In the YouTube app, on the **{loc(config()['channel'], 'brand')}** channel: **+ → Upload a video**, pick the file, paste the title and description, set "
           f"**Audience → No, it's not made for kids**, and **Visibility → Schedule → {when}**.", ""]
    for f in infos:
        out += [f"#### {'📱 Short' if f == 'short' else '🖥️ Long video'}",
                f"1. Download: [{s.id}-{f}.mp4]({assets_url}{s.id}-{f}.mp4)"
                + (f" · thumbnail: [{s.id}-thumb.png]({assets_url}{s.id}-thumb.png)" if f == "long" else ""),
                "2. Title:", f"```\n{t[f]}\n```",
                "3. Description:", f"```\n{description(s, f, infos[f])}\n```",
                "4. Tags:", f"```\n{', '.join(tags(s))}\n```", ""]
    out.append("Close this issue once both are posted.")
    return "\n".join(out)


def published_comment(s: Script, uploaded: dict, slot: datetime | None) -> str:
    when = f"scheduled for **{_slot_text(slot)}**" if slot else "**live now**"
    lines = [f"### 🚀 Uploaded to YouTube, {when}"]
    for f, vid in uploaded.items():
        url = f"https://youtu.be/{vid}"
        lines.append(f"- {'📱 Short' if f == 'short' else '🖥️ Long'}: {url} · [YouTube Studio](https://studio.youtube.com/video/{vid}/edit)")
    if not config()["publish"].get("audited", False):
        lines.append("\n> If YouTube Studio shows the video as **Private (locked)**, your Google Cloud project hasn't "
                     "passed YouTube's API audit yet. See docs/SETUP.md, step 5.")
    return "\n".join(lines)
