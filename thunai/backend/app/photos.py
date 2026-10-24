"""Photo-based diagnosis (SPEC 12.4): the AI reads a photo before the questions and steps.

The technician sees what was read and can correct it. The observation becomes evidence PHOTO-<id>.
Photos are sent to the AI provider only when AI_PHOTOS=true (the mock provider never sends them),
and are re-encoded first so location and camera metadata never leave the server.
"""
import base64
import io
import json
import logging
import re

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import media as media_service
from . import retrieval
from .ai import schemas as ai_schemas
from .ai.service import call_json
from .config import get_config
from .models import AlarmCode, LogMedia, Machine, utcnow

log = logging.getLogger("thunai.photos")

MAX_EDGE = 2576  # the model's maximum long edge; larger photos only cost more
CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,19}$")
# SAMPLE photos made for demos carry the mock AI's answer in a PNG text chunk. Real photos never do,
# and the chunk is dropped by re-encoding, so it never reaches a real provider.
DEMO_KEY = "thunai_demo"


def prepare(content: bytes) -> tuple[str, str, dict | None]:
    """(media type, base64 JPEG, demo answer or None). Fixes rotation, drops all metadata, caps size."""
    with Image.open(io.BytesIO(content)) as im:
        demo = im.info.get(DEMO_KEY)
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        im.thumbnail((MAX_EDGE, MAX_EDGE))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)  # a fresh JPEG has no EXIF (no GPS, no camera details)
    try:
        demo_answer = json.loads(demo) if demo else None
    except json.JSONDecodeError:
        demo_answer = None
    return "image/jpeg", base64.standard_b64encode(buf.getvalue()).decode("ascii"), demo_answer


def _known_codes(db: Session, machine: Machine) -> str:
    rows = db.scalars(
        select(AlarmCode.code)
        .where(
            AlarmCode.active.is_(True),
            (AlarmCode.machine_id == machine.id)
            | ((AlarmCode.machine_type_id == machine.machine_type_id) & AlarmCode.machine_id.is_(None)),
        )
        .order_by(AlarmCode.code)
        .limit(200)
    ).all()
    return ", ".join(dict.fromkeys(rows)) or "(no alarm list uploaded)"


def _clean(out: ai_schemas.PhotoOut) -> ai_schemas.PhotoOut:
    """Code-side checks: no value without legibility, codes look like codes, confidence in range."""
    for r in out.readings:
        if not r.legible:
            r.value = ""
        elif not r.value.strip():
            r.legible = False
    out.alarm_codes = [c.strip() for c in out.alarm_codes if CODE.match(c.strip())][:5]
    out.confidence = min(max(out.confidence, 0.0), 1.0)
    if not out.usable:
        out.readings, out.alarm_codes = [], []
    return out


def read(db: Session, media: LogMedia, machine: Machine, note: str = "") -> dict:
    """Read the photo with the AI and store the observation on the media row."""
    cfg = get_config()
    if media.observed_at is not None:
        return media.observation or {}  # already read; reading again would cost again
    if not cfg.photos_to_ai:
        # Not marked as read, so the photo can be read later if AI_PHOTOS is switched on.
        media.observation = {"usable": False, "disabled": True}
        return media.observation
    try:
        media_type, data, demo = prepare(media_service.path_of(media).read_bytes())
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError) as e:
        log.warning("Photo %s could not be opened: %s", media.id, e)
        media.observation = {"usable": False, "error": "The photo file could not be opened."}
        media.observed_at = utcnow()
        return media.observation
    info: dict = {}
    out, error = call_json(
        db,
        purpose="read_photo",
        prompt_name="read_photo",
        tier="diagnosis",
        variables={
            "machine": retrieval.format_machine(machine),
            "components": retrieval.format_components([c for c in machine.components if c.active]),
            "alarm_codes": _known_codes(db, machine),
            "note": note.strip()[:500] or "(none)",
        },
        out_model=ai_schemas.PhotoOut,
        max_tokens=4000,
        hints={"demo": demo},
        validate=_clean,
        info=info,
        images=[(media_type, data)],
    )
    if out is None:
        # Not marked as read: the session start tries once more.
        media.observation = {"usable": False, "error": "Thunai could not read the photo right now."}
        log.info("Photo %s not read: %s", media.id, error)
    else:
        media.observation = out.model_dump()
        media.observed_at = utcnow()
        media.observation_model = info.get("model", "")[:80]
    return media.observation


def suggestion(db: Session, machine: Machine, observation: dict) -> dict | None:
    """The first alarm code seen on a screen, with its alarm-list meaning, to pre-fill the alarm field."""
    for code in observation.get("alarm_codes") or []:
        meaning = retrieval.lookup_alarm(db, machine, code)
        return {
            "code": code,
            "meaning": {"code": meaning.code, "message": meaning.message, "cause": meaning.cause, "remedy": meaning.remedy}
            if meaning
            else None,
        }
    return None
