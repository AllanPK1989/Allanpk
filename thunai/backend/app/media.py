"""Audio and photo files on local disk (MEDIA_DIR). Audio is kept for audio_retention_days."""
import logging
import shutil
import subprocess
import uuid
from datetime import timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import settings_store
from .config import get_config
from .models import LogMedia, User, utcnow
from .stt import STTUnavailable, get_stt

log = logging.getLogger("thunai.media")

ALLOWED = {
    "audio": ("audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac"),
    "photo": ("image/jpeg", "image/png", "image/webp"),
}
EXT = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/aac": ".aac",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _root() -> Path:
    root = get_config().media_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_upload(db: Session, user: User, upload: UploadFile, kind: str) -> LogMedia:
    mime = (upload.content_type or "").split(";")[0].strip().lower()
    if mime not in ALLOWED[kind]:
        raise HTTPException(415, f"Unsupported {kind} type: {mime or 'unknown'}")
    limit = get_config().max_upload_mb * 1024 * 1024
    now = utcnow()
    rel = Path(f"{now:%Y/%m}") / f"{uuid.uuid4().hex}{EXT[mime]}"
    dest = _root() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with dest.open("wb") as out:
        while chunk := upload.file.read(1024 * 256):
            size += len(chunk)
            if size > limit:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"File larger than {get_config().max_upload_mb} MB")
            out.write(chunk)
    media = LogMedia(kind=kind, file_path=str(rel), mime=mime, size_bytes=size, created_by=user.id)
    if kind == "audio":
        media.expires_at = now + timedelta(days=int(settings_store.get(db, "audio_retention_days")))
    db.add(media)
    db.flush()
    return media


def path_of(media: LogMedia) -> Path:
    return _root() / media.file_path


def _to_wav(src: Path) -> Path:
    """16 kHz mono WAV suits every speech provider. Falls back to the original file."""
    ffmpeg = shutil.which(get_config().ffmpeg_path)
    if src.suffix == ".wav" or not ffmpeg:
        return src
    dest = src.with_suffix(".16k.wav")
    try:
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(dest)],
            check=True,
            timeout=60,
        )
        return dest
    except (subprocess.SubprocessError, OSError):
        log.warning("ffmpeg conversion failed for %s", src)
        return src


def transcribe(db: Session, media: LogMedia, language_hint: str) -> str | None:
    """Transcribe and store the text on the media row. None when speech-to-text is unavailable."""
    src = path_of(media)
    target = src
    try:
        stt = get_stt()
        target = src if stt.name == "mock" else _to_wav(src)
        result = stt.transcribe(target, language_hint)
    except STTUnavailable as e:
        media.status = "failed"
        log.info("Speech-to-text unavailable: %s", e)
        return None
    finally:
        if target != src:
            target.unlink(missing_ok=True)
    media.transcript = result.text
    media.stt_provider = result.provider
    media.language = result.language or language_hint
    media.confidence = result.confidence
    media.status = "transcribed"
    return result.text


def purge_expired(db: Session) -> int:
    """Delete expired audio files. The database row stays (no hard deletes) with purged_at set."""
    count = 0
    for media in db.scalars(
        select(LogMedia).where(LogMedia.expires_at <= utcnow(), LogMedia.purged_at.is_(None))
    ):
        path_of(media).unlink(missing_ok=True)
        media.purged_at = utcnow()
        count += 1
    return count
