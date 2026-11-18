"""Voice and text capture: understand a note, then apply what the user confirmed."""
from datetime import date, time

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from .. import stt
from .. import tasks_service as ts
from ..ai import service as ai
from ..config import get_config
from ..dashboard import known_people
from ..db import get_db
from ..deps import get_task, prefs
from ..models import Basket
from ..schemas import ApplyIn, InterpretIn
from ..security import require_auth
from ..serialize import task_dict
from ..settings_store import Prefs

router = APIRouter(prefix="/api/assistant", tags=["assistant"], dependencies=[Depends(require_auth)])

ALLOWED_AUDIO = ("audio/", "video/webm", "video/mp4", "application/octet-stream")


@router.post("/interpret")
def interpret(body: InterpretIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    out = ai.interpret(db, p, body.text)
    db.commit()
    return out


def _vocabulary(db: Session) -> str:
    """Names and basket words help Whisper spell them right."""
    names = known_people(db, limit=40)
    baskets = [b.name for b in db.query(Basket).filter(Basket.archived.is_(False)).all()]
    return "Task note. People: " + ", ".join(names) + ". Baskets: " + ", ".join(baskets) + "." if names else ""


@router.post("/voice")
async def voice(
    audio: UploadFile = File(...),
    auto: bool = Query(False, description="Save straight to the inbox (offline recordings nobody is reviewing)"),
    db: Session = Depends(get_db),
    p: Prefs = Depends(prefs),
):
    if not (audio.content_type or "").startswith(ALLOWED_AUDIO):
        raise HTTPException(415, "That doesn't look like a recording")
    data = await audio.read()
    if len(data) > get_config().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Recording too long")
    try:
        result = stt.get_stt().transcribe(data, audio.filename or "voice.webm", audio.content_type or "",
                                          prompt=_vocabulary(db))
    except stt.STTUnavailable as e:
        raise HTTPException(503, f"Voice isn't available right now ({e}). Please type instead.")
    del data  # recordings are never stored
    text = result.text.strip()
    if not text:
        raise HTTPException(422, "I couldn't hear anything. Try again a little closer to the mic?")
    out = ai.interpret(db, p, text)
    if auto:
        out["saved"] = _save_offline(db, p, out)
    db.commit()
    return out


def _save_offline(db: Session, p: Prefs, out: dict) -> list[dict]:
    """Offline recordings land in the inbox with the AI's guesses still highlighted."""
    c = ts.clock(p)
    saved = []
    drafts = out["drafts"] if out["intent"] == "create" else [{"title": out["transcript"][:200], "guessed": []}]
    for d in drafts:
        t = ts.create_task(db, p, {
            "title": d["title"], "notes": d.get("notes", ""), "basket_id": d.get("basket_id"),
            "due_date": date.fromisoformat(d["due_date"]) if d.get("due_date") else None,
            "due_time": time.fromisoformat(d["due_time"]) if d.get("due_time") else None,
            "priority": d.get("priority", "normal"), "person": d.get("person", ""),
            "status": "waiting" if d.get("waiting") else "open", "repeat_rule": d.get("repeat_rule", ""),
            "checklist": d.get("checklist", []), "transcript": out["transcript"],
            "ai_fields": d.get("guessed", []) + ["title"], "inbox": True,
        }, source="offline_voice")
        saved.append(task_dict(t, c))
    return saved


@router.post("/apply")
def apply(body: ApplyIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    c = ts.clock(p)
    source = body.source if body.source in ("voice", "text") else "voice"
    created, closed, moved = [], [], []
    try:
        if body.intent == "create":
            for d in body.drafts[:15]:
                t = ts.create_task(db, p, {
                    "title": d.title, "notes": d.notes, "basket_id": d.basket_id, "due_date": d.due_date,
                    "due_time": d.due_time, "priority": d.priority, "person": d.person,
                    "status": "waiting" if d.waiting and d.person else "open", "repeat_rule": d.repeat_rule,
                    "checklist": d.checklist, "transcript": body.transcript,
                    "ai_fields": d.guessed if body.keep_guesses else [],
                }, source=source)
                created.append(t)
        elif body.intent == "complete":
            for tg in body.targets:
                t, _ = ts.close_task(db, p, get_task(db, tg.task_id))
                closed.append(t)
        elif body.intent == "reschedule":
            for tg in body.targets:
                t = get_task(db, tg.task_id)
                patch = {}
                if tg.due_date:
                    patch["due_date"] = tg.due_date
                if tg.due_time:
                    patch["due_time"] = tg.due_time
                ts.update_task(db, p, t, patch)
                moved.append(t)
        else:
            raise HTTPException(400, "Nothing to apply")
    except ts.TaskError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {
        "created": [task_dict(t, c) for t in created],
        "closed": [task_dict(t, c) for t in closed],
        "moved": [task_dict(t, c) for t in moved],
    }


@router.get("/status")
def status():
    return {"ai": "claude" if ai.ai_enabled() else "rules", "voice": stt.status()}
