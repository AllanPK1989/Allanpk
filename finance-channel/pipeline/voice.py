"""Narrate videos in your own recorded voice.

1. `voice-script ID` lists every sentence of both videos (the disclaimer is
   shared, so it appears once), each with a clip key. The daily job commits it
   to voice-scripts/ID.json, which the recorder page reads.
2. The recorder page records one clip per sentence and saves them as a zip:
   voice/<key>.<webm|m4a|...> plus manifest.json.
3. `voice-import ID ZIP` cleans each clip (rumble filter, light denoise, trim
   leading/trailing silence, even out loudness) into 48 kHz mono WAVs that the
   renderer uses instead of the synthetic voice.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from .config import ROOT, config
from .script import Script, build_timeline
from .tts import RATE, clean_markup, clip_key, wav_duration

VOICE_SCRIPTS = ROOT / "voice-scripts"


def voice_scripts_dir() -> Path:
    """voice-scripts/ for the Tamil channel, voice-scripts/<channel>/ for the others."""
    return ROOT / config()["channel"].get("voice_scripts_dir", "voice-scripts")
MAX_ZIP_BYTES = 60 * 1024 * 1024
MIN_CLIP_SECONDS = 0.35
AUDIO_EXT = {".webm", ".weba", ".ogg", ".opus", ".m4a", ".mp4", ".aac", ".mp3", ".wav", ".caf", ".3gp", ".amr"}

# rumble filter, gentle denoise, trim silence at both ends, then even out loudness
CLEANUP = ("highpass=f=75,afftdn=nf=-28,"
           "silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.08:detection=peak,"
           "areverse,"
           "silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.15:detection=peak,"
           "areverse,"
           "loudnorm=I=-18:TP=-2:LRA=9")


def voice_script(s: Script, formats=("short", "long")) -> dict:
    """Unique sentences in reading order (short first, then long)."""
    items: dict[str, dict] = {}
    for fmt in formats:
        for seg in build_timeline(s, fmt).segments:
            k = clip_key(seg.text)
            if k not in items:
                items[k] = {"key": k, "text": clean_markup(seg.text).strip(), "formats": []}
            if fmt not in items[k]["formats"]:
                items[k]["formats"].append(fmt)
    return {"id": s.id, "title_ta": s.get("title_ta", ""), "title_en": s.get("title_en", ""),
            "sentences": list(items.values())}


def write_voice_script(s: Script, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or voice_scripts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{s.id}.json"
    p.write_text(json.dumps(voice_script(s), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p


def _clean(src: Path, dst: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", "-af", CLEANUP,
                    "-ar", str(RATE), "-ac", "1", "-sample_fmt", "s16", str(dst)], check=True)


def import_zip(s: Script, zip_path: Path, out_dir: Path) -> dict:
    """Turn the recorder's zip into cleaned WAVs. Returns a report dict."""
    zip_path = Path(zip_path)
    if zip_path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError(f"the zip is {zip_path.stat().st_size // 1_000_000} MB; the limit is {MAX_ZIP_BYTES // 1_000_000} MB")
    expected = {it["key"]: it["text"] for it in voice_script(s)["sentences"]}
    out_dir.mkdir(parents=True, exist_ok=True)
    imported, too_short, unknown = [], [], []
    with zipfile.ZipFile(zip_path) as z, tempfile.TemporaryDirectory() as tmp:
        for info in z.infolist():
            name = Path(info.filename).name
            stem, ext = Path(name).stem, Path(name).suffix.lower()
            if info.is_dir() or ext not in AUDIO_EXT or not re.fullmatch(r"[0-9a-f]{12}", stem):
                continue
            if stem not in expected:
                unknown.append(stem)  # recorded for an older version of the script
                continue
            raw = Path(tmp) / f"{stem}{ext}"
            raw.write_bytes(z.read(info))
            wav = out_dir / f"{stem}.wav"
            _clean(raw, wav)
            if wav_duration(wav) < MIN_CLIP_SECONDS:
                too_short.append(expected[stem])
                wav.unlink()
                continue
            imported.append(stem)
    missing = [text for k, text in expected.items() if k not in imported and text not in too_short]
    return {"topic": s.id, "expected": len(expected), "imported": len(imported),
            "missing": missing, "too_short": too_short, "unknown": len(unknown)}


def report_markdown(rep: dict) -> str:
    lines = [f"🎙️ Recording for #{int(rep['topic'])}: {rep['imported']} of {rep['expected']} sentences usable."]
    if rep["too_short"]:
        lines.append("\nThese clips were silent or too short (re-record them):")
        lines += [f"- {t}" for t in rep["too_short"]]
    if rep["missing"]:
        lines.append("\nThese sentences have no clip yet:")
        lines += [f"- {t}" for t in rep["missing"]]
    if rep["unknown"]:
        lines.append(f"\n{rep['unknown']} clip(s) belong to an older version of the script and were ignored.")
    if rep["missing"] or rep["too_short"]:
        lines.append("\nOpen the recorder again (it remembers what you already recorded), add these, save the zip and send `/voice` again.")
    return "\n".join(lines)
