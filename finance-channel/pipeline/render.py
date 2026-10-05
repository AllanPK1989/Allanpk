"""Render a script to MP4: narrate, capture animated frames in Chromium, encode.

Frames are only captured while something is animating (an item sliding in, a
caption fading). Once the picture is still, the last frame is simply held for
the rest of the sentence, which keeps renders fast.
"""
from __future__ import annotations

import json
import math
import os
import random
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import MUSIC, TEMPLATES, accent_soft, config
from .script import Script, Timeline, build_timeline
from .tts import clean_markup, concat_wavs, synthesize, wav_duration

LEAD_IN = 0.30     # picture shows briefly before the first word
TAIL = 0.80        # hold on the last frame after the voice ends
CAP_MAX = {"short": 64, "long": 84}


@dataclass
class Shot:
    scene: int
    state: dict
    caption: str
    cap_new: bool
    start: float
    duration: float


def caption_chunks(text: str, maxlen: int) -> list[str]:
    text = text.strip()
    if len(text) <= maxlen:
        return [text]
    mid = len(text) // 2
    cuts = [m.end() for m in re.finditer(r"[,;:]\s+", text)] or [m.end() for m in re.finditer(r"\s+", text)]
    if not cuts:
        return [text]
    cut = min(cuts, key=lambda c: abs(c - mid))
    return caption_chunks(text[:cut], maxlen) + caption_chunks(text[cut:], maxlen)


def plan(script: Script, fmt: str, engine: str | None, workdir: Path,
         voice_dir: Path | None = None) -> tuple[Timeline, list[Shot], Path, float]:
    """Synthesise narration and lay out every shot on the clock."""
    tl = build_timeline(script, fmt)
    v = config()["voice"]
    wavs = synthesize([s.text for s in tl.segments], fmt, engine, voice_dir)
    parts: list[tuple[Path | None, float]] = [(None, LEAD_IN)]
    for seg, wav in zip(tl.segments, wavs):
        pad = v["gap_seconds"] + (v["scene_gap_seconds"] if seg.last_in_scene else 0)
        seg.audio = wav
        seg.duration = wav_duration(wav) + pad
        parts.append((wav, pad))
    parts.append((None, TAIL))
    narration = workdir / "narration.wav"
    total = concat_wavs(parts, narration)

    shots: list[Shot] = []
    t = 0.0
    for n, seg in enumerate(tl.segments):
        dur = seg.duration + (LEAD_IN if n == 0 else 0) + (TAIL if n == len(tl.segments) - 1 else 0)
        chunks = caption_chunks(clean_markup(seg.text), CAP_MAX[fmt])
        weight = sum(len(c) for c in chunks)
        for ci, ch in enumerate(chunks):
            d = dur * len(ch) / weight
            first_chunk = ci == 0
            st = {
                "revealed": seg.revealed,
                "newFrom": seg.new_from if first_chunk else -1,
                "newTo": seg.new_to if first_chunk else -1,
                "sentence": seg.sentence,
                "sentenceNew": first_chunk,
                "first": seg.first and first_chunk,
            }
            shots.append(Shot(seg.scene, st, ch, True, t, d))
            t += d
    return tl, shots, narration, total


def _launch(p, **kw):
    """Chromium for frame capture; CHROMIUM_PATH overrides the bundled build."""
    exe = os.environ.get("CHROMIUM_PATH") or None
    return p.chromium.launch(executable_path=exe, args=["--font-render-hinting=none", "--disable-lcd-text"], **kw)


def _stage_setup(script: Script, fmt: str, thumb: bool = False) -> dict:
    cfg = config()
    cat = script.cat
    return {
        "format": fmt, "thumb": thumb,
        "accent": cat["accent"], "accentSoft": accent_soft(cat["accent"]),
        "brand": cfg["channel"]["brand_ta"], "category": cat["ta"],
        "episode": f"#{int(script.id)}",
        "note": cfg["disclaimer"]["screen_ta"],
        "captions": cfg["video"][fmt].get("captions", True),
    }


FONT_WARMUP = """async () => {
  await Promise.all([
    document.fonts.load('800 60px Catamaran', 'தமிழ் Aa'),
    document.fonts.load('700 60px Catamaran', 'தமிழ் Aa'),
    document.fonts.load('400 40px "Noto Sans Tamil"', 'தமிழ் Aa'),
    document.fonts.load('600 40px "Noto Sans Tamil"', 'தமிழ் Aa'),
    document.fonts.load('800 40px Inter', '₹ 0123456789 →×'),
    document.fonts.load('600 40px Inter', '₹ 0123456789'),
  ]);
  await document.fonts.ready;
  return document.fonts.size;
}"""

ANIM_END = """() => Math.max(0, ...document.getAnimations().map(a => {
  const t = a.effect.getComputedTiming(); return (t.endTime || 0);
}))"""


def capture(script: Script, fmt: str, tl: Timeline, shots: list[Shot], frames_dir: Path) -> Path:
    """Screenshot animated frames for every shot and write an ffmpeg concat list."""
    from playwright.sync_api import sync_playwright

    vc = config()["video"]
    W, H, fps = vc[fmt]["width"], vc[fmt]["height"], vc["fps"]
    frame_dt = 1.0 / fps
    lines: list[str] = []
    idx = 0
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto((TEMPLATES / "stage.html").as_uri())
        page.evaluate("o => stage.setup(o)", _stage_setup(script, fmt))
        page.evaluate(FONT_WARMUP)
        for shot in shots:
            scene = tl.scenes[shot.scene]
            page.evaluate("([sc, st, cap, cn]) => stage.show(sc, st, cap, cn)",
                          [scene, shot.state, shot.caption, shot.cap_new])
            end_ms = page.evaluate(ANIM_END)
            n_anim = 0 if end_ms <= 0 else min(math.ceil(end_ms / 1000 / frame_dt), int(shot.duration / frame_dt) - 1)
            used = 0.0
            for f in range(max(n_anim, 0)):
                page.evaluate("ms => stage.seek(ms)", f * frame_dt * 1000)
                fp = frames_dir / f"f{idx:06d}.jpg"
                page.screenshot(path=str(fp), type="jpeg", quality=93)
                lines += [f"file '{fp.name}'", f"duration {frame_dt:.6f}"]
                used += frame_dt
                idx += 1
            page.evaluate("ms => stage.seek(ms)", max(end_ms, 0) + 50)
            fp = frames_dir / f"f{idx:06d}.jpg"
            page.screenshot(path=str(fp), type="jpeg", quality=93)
            lines += [f"file '{fp.name}'", f"duration {max(shot.duration - used, frame_dt):.6f}"]
            idx += 1
        browser.close()
    lines.append(lines[-2])  # concat demuxer needs the last file repeated
    lst = frames_dir / "frames.txt"
    lst.write_text("\n".join(lines) + "\n")
    return lst


def encode(fmt: str, script: Script, frames_list: Path, narration: Path, total: float, out_mp4: Path) -> None:
    vc = config()["video"]
    W, H, fps = vc[fmt]["width"], vc[fmt]["height"], vc["fps"]
    accent = script.cat["accent"].lstrip("#")
    bar_h = 10
    bar_y = 0 if fmt == "short" else H - bar_h
    music = sorted(MUSIC.glob("*.mp3")) + sorted(MUSIC.glob("*.m4a"))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(frames_list),
           "-i", str(narration)]
    vf = (f"[0:v]fps={fps},scale={W}:{H},format=yuv420p[v0];"
          f"color=c=0x{accent}:s={W}x{bar_h}:r={fps}[bar];"
          f"[v0][bar]overlay=x='-w+w*t/{total:.3f}':y={bar_y}:shortest=1[v]")
    af = "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=-15:TP=-1.5:LRA=11[voice]"
    if music:
        track = random.Random(script.id).choice(music)
        cmd += ["-stream_loop", "-1", "-i", str(track)]
        vol = config()["video"].get("music_volume", 0.07)
        af += (f";[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={vol},"
               f"afade=t=in:d=1,afade=t=out:st={max(total - 2.5, 0):.2f}:d=2.5[bg];"
               f"[voice][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    else:
        af += ";[voice]anull[a]"
    cmd += ["-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-tune", "stillimage", "-r", str(fps),
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", f"{total:.3f}", "-movflags", "+faststart", str(out_mp4)]
    subprocess.run(cmd, check=True)


def srt(shots: list[Shot]) -> str:
    def ts(x: float) -> str:
        ms = int(round(x * 1000))
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    out = []
    for i, s in enumerate(shots, 1):
        out.append(f"{i}\n{ts(s.start)} --> {ts(s.start + s.duration)}\n{s.caption}\n")
    return "\n".join(out)


def chapters(tl: Timeline, shots: list[Shot]) -> list[tuple[float, str]]:
    """YouTube chapters from scenes that carry a `chapter:` label."""
    marks: list[tuple[float, str]] = []
    seen = set()
    for s in shots:
        sc = tl.scenes[s.scene]
        if s.scene in seen:
            continue
        seen.add(s.scene)
        if sc.get("chapter"):
            marks.append((s.start, sc["chapter"]))
    if not marks or marks[0][0] > 0.01:
        marks.insert(0, (0.0, "அறிமுகம்"))
    else:
        marks[0] = (0.0, marks[0][1])
    # YouTube needs each chapter to be at least 10 s long; merge short ones forward
    end = shots[-1].start + shots[-1].duration
    merged: list[tuple[float, str]] = []
    for i, (t, name) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else end
        if merged and nxt - t < 10.5 and i + 1 < len(marks):
            continue
        if merged and t - merged[-1][0] < 10.5:
            continue
        merged.append((t, name))
    return merged if len(merged) >= 3 else []


def render_video(script: Script, fmt: str, out_dir: Path, engine: str | None = None,
                 voice_dir: Path | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"render-{script.id}-{fmt}-") as tmp:
        work = Path(tmp)
        tl, shots, narration, total = plan(script, fmt, engine, work, voice_dir)
        frames = work / "frames"
        frames.mkdir()
        lst = capture(script, fmt, tl, shots, frames)
        mp4 = out_dir / f"{script.id}-{fmt}.mp4"
        encode(fmt, script, lst, narration, total, mp4)
    (out_dir / f"{script.id}-{fmt}.srt").write_text(srt(shots), encoding="utf-8")
    info = {
        "format": fmt, "file": mp4.name, "duration": round(total, 2),
        "chapters": [[round(t, 1), n] for t, n in chapters(tl, shots)] if fmt == "long" else [],
        "shots": len(shots),
        "voice": "recorded" if voice_dir is not None else "ai",
    }
    (out_dir / f"{script.id}-{fmt}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return info


def render_thumbnail(script: Script, out_png: Path) -> Path:
    from playwright.sync_api import sync_playwright
    cfg = config()
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto((TEMPLATES / "stage.html").as_uri())
        page.evaluate("o => stage.setup(o)", _stage_setup(script, "long", thumb=True))
        page.evaluate(FONT_WARMUP)
        page.evaluate("t => stage.thumb(t)", {
            "title": script.get("thumb_ta") or script["title_ta"],
            "sub": script.get("thumb_en") or script.get("title_en"),
            "category": script.cat["ta"], "icon": script.get("icon") or script.cat.get("icon"),
            "brand": cfg["channel"]["brand_ta"],
        })
        page.screenshot(path=str(out_png), type="png")
        browser.close()
    return out_png


def contact_sheet(script: Script, fmt: str, out_png: Path, engine: str = "silent") -> Path:
    """Quick visual check: the final frame of every scene, tiled into one image."""
    from playwright.sync_api import sync_playwright
    tl = build_timeline(script, fmt)
    vc = config()["video"]
    W, H = vc[fmt]["width"], vc[fmt]["height"]
    last_seg = {}
    for seg in tl.segments:
        last_seg[seg.scene] = seg
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": W, "height": H})
        page.goto((TEMPLATES / "stage.html").as_uri())
        page.evaluate("o => stage.setup(o)", _stage_setup(script, fmt))
        page.evaluate(FONT_WARMUP)
        tiles = []
        for si, seg in sorted(last_seg.items()):
            st = {"revealed": seg.revealed, "newFrom": -1, "newTo": -1, "sentence": seg.sentence,
                  "sentenceNew": False, "first": False}
            page.evaluate("([sc, st, cap]) => stage.show(sc, st, cap, false)",
                          [tl.scenes[si], st, clean_markup(seg.text)[:CAP_MAX[fmt]]])
            page.evaluate("ms => stage.seek(ms)", 5000)
            fp = Path(tmp) / f"s{si:02d}.png"
            page.screenshot(path=str(fp))
            tiles.append(fp)
        browser.close()
        cols = 4 if fmt == "short" else 3
        scale = 360 if fmt == "short" else 640
        inputs = []
        for fp in tiles:
            inputs += ["-i", str(fp)]
        n = len(tiles)
        rows = math.ceil(n / cols)
        filt = "".join(f"[{i}:v]scale={scale}:-1[t{i}];" for i in range(n))
        th = int(scale * H / W)
        layout = "|".join(f"{(i % cols) * scale}_{(i // cols) * th}" for i in range(n))
        filt += "".join(f"[t{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={layout}:fill=black[o]"
        if n == 1:
            filt = f"[0:v]scale={scale}:-1[o]"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", filt,
                        "-map", "[o]", "-frames:v", "1", str(out_png)], check=True)
    return out_png
