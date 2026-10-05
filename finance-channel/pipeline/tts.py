"""Text-to-speech for narration segments.

Each sentence is synthesised separately and decoded to 48 kHz mono WAV, so its
duration is known to the sample and the picture can't drift from the voice.
Clips are cached by (voice, rate, pitch, text).
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import subprocess
import wave
from pathlib import Path

from .config import CACHE, config

RATE = 48000


def clean_markup(text: str) -> str:
    """Strip the **bold** / __hl__ / ++good++ / --bad-- markers used on screen."""
    for m in ("**", "__", "++"):
        text = text.replace(m, "")
    return re.sub(r"--(.+?)--", r"\1", text)


_RUPEE = re.compile(r"₹\s?([\d][\d,]*(?:\.\d+)?)\s*(லட்சம்|கோடி|ஆயிரம்)?")


def for_voice(text: str) -> str:
    """Rewrite a caption sentence into what the Tamil voice should actually say."""
    t = clean_markup(text)
    t = _RUPEE.sub(lambda m: f"{m.group(1)} {m.group(2) or ''} ரூபாய்".replace("  ", " "), t)
    t = re.sub(r"(?<=\d),(?=\d)", "", t)          # 1,00,000 -> 100000
    lex = config().get("pronounce", {}) or {}
    for key in sorted(lex, key=len, reverse=True):
        val = lex[key]
        if re.search(r"[A-Za-z]", key):
            t = re.sub(rf"(?<![A-Za-z]){re.escape(key)}(?![A-Za-z])", val, t)
        else:
            t = t.replace(key, val)
    t = t.replace("×", " பெருக்கல் ").replace("÷", " வகுத்தல் ").replace("→", ", ")
    t = t.replace("=", " சமம் ").replace("&", " மற்றும் ")
    return re.sub(r"\s{2,}", " ", t).strip()


def _key(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).encode()).hexdigest()[:16]


def wav_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def _to_wav(src: Path, dst: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-ar", str(RATE), "-ac", "1", "-sample_fmt", "s16", str(dst)], check=True)


def _silent_wav(dst: Path, seconds: float) -> None:
    n = int(seconds * RATE)
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"\x00\x00" * n)


async def _edge(text: str, voice: str, rate: str, pitch: str, mp3: Path) -> None:
    import edge_tts
    last = None
    for attempt in range(5):
        try:
            await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(mp3))
            if mp3.exists() and mp3.stat().st_size > 0:
                return
        except Exception as e:  # network hiccups / throttling
            last = e
        await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"edge-tts failed for {text[:40]!r}: {last}")


def clip_key(text: str) -> str:
    """Stable id for one narrated sentence; names the clip you record for it."""
    return hashlib.sha1(clean_markup(text).strip().encode("utf-8")).hexdigest()[:12]


class MissingRecording(RuntimeError):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"{len(missing)} sentence(s) have no recorded clip, e.g. {missing[0][:60]!r}")


def synthesize(texts: list[str], fmt: str, engine: str | None = None, voice_dir: Path | None = None) -> list[Path]:
    """Return one WAV per text (same order).

    With voice_dir, use your own recorded clips (voice_dir/<clip_key>.wav,
    prepared by `pipeline voice-import`) instead of a synthetic voice.
    """
    if voice_dir is not None:
        paths = [Path(voice_dir) / f"{clip_key(t)}.wav" for t in texts]
        missing = [t for t, p in zip(texts, paths) if not p.exists()]
        if missing:
            raise MissingRecording(missing)
        return paths
    v = config()["voice"]
    engine = engine or v["engine"]
    voice, pitch = v["name"], v.get("pitch", "+0Hz")
    rate = v["rate_short"] if fmt == "short" else v["rate_long"]
    out_dir = CACHE / "tts"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[str, Path]] = []
    paths: list[Path] = []
    for t in texts:
        spoken = for_voice(t)
        k = _key(engine, voice, rate, pitch, spoken)
        wav = out_dir / f"{k}.wav"
        paths.append(wav)
        if not wav.exists():
            jobs.append((spoken, wav))

    if engine == "silent":
        # ~13 Tamil characters per second: close enough to test timing/layout
        for spoken, wav in jobs:
            _silent_wav(wav, max(1.2, len(spoken) / 13.0))
        return paths
    if engine != "edge":
        raise ValueError(f"unknown TTS engine {engine}")

    async def run_all():
        sem = asyncio.Semaphore(4)

        async def one(spoken: str, wav: Path):
            async with sem:
                mp3 = wav.with_suffix(".mp3")
                await _edge(spoken, voice, rate, pitch, mp3)
                _to_wav(mp3, wav)
                mp3.unlink(missing_ok=True)
        await asyncio.gather(*(one(s, w) for s, w in jobs))

    if jobs:
        asyncio.run(run_all())
    return paths


def concat_wavs(parts: list[tuple[Path | None, float]], dst: Path) -> float:
    """Concatenate (wav or None, seconds_of_silence_after) pairs into one WAV."""
    total = 0
    with wave.open(str(dst), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(RATE)
        for wav, pad in parts:
            if wav is not None:
                with wave.open(str(wav)) as w:
                    if w.getframerate() != RATE or w.getnchannels() != 1:
                        raise ValueError(f"{wav} is not {RATE} Hz mono")
                    frames = w.readframes(w.getnframes())
                    out.writeframes(frames)
                    total += w.getnframes()
            n = int(round(pad * RATE))
            out.writeframes(b"\x00\x00" * n)
            total += n
    return total / RATE
