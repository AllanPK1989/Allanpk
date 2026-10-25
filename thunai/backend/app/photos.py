"""Photo readings sent by the Copilot agent (SPEC 13.1).

Technicians send photos of gauges, HMI screens, indicator LEDs or damage in Teams. The agent reads
them with Microsoft's model and passes what it read to startTroubleshooting. Thunai never receives
the photo itself: it checks and stores the readings, which become evidence PHOTO-1, PHOTO-2, ...
In the PWA, photos are attachments only.
"""
import re

from sqlalchemy.orm import Session

from . import retrieval
from .models import Machine

CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,19}$")
MAX_PHOTOS = 3
MAX_READINGS = 10


def clean(o: dict) -> dict:
    """Code-side checks: no value without legibility, codes look like codes, sizes capped."""
    readings = []
    for r in (o.get("readings") or [])[:MAX_READINGS]:
        label = str(r.get("label") or "").strip()[:80]
        value = str(r.get("value") or "").strip()[:40]
        legible = bool(r.get("legible")) and bool(value)
        if label:
            readings.append({"label": label, "value": value if legible else "", "unit": str(r.get("unit") or "").strip()[:20], "legible": legible})
    codes = [str(c).strip() for c in o.get("alarm_codes") or []]
    return {
        "usable": True,
        "source": "copilot",
        "shows_en": str(o.get("shows") or "").strip()[:300],
        "shows_ta": "",
        "readings": readings,
        "screen_text": str(o.get("screen_text") or "").strip()[:500],
        "alarm_codes": [c for c in codes if CODE.match(c)][:5],
        "damage_en": str(o.get("damage") or "").strip()[:300],
        "damage_ta": "",
    }


def suggestion(db: Session, machine: Machine, observations: list[dict]) -> dict | None:
    """The first alarm code seen on a screen, with its alarm-list meaning, to fill an empty alarm field."""
    for o in observations:
        for code in o.get("alarm_codes") or []:
            meaning = retrieval.lookup_alarm(db, machine, code)
            return {
                "code": code,
                "meaning": {"code": meaning.code, "message": meaning.message, "cause": meaning.cause, "remedy": meaning.remedy}
                if meaning
                else None,
            }
    return None
