from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import db as dbmod
from ..agent import chat as chat_mod
from ..data.market import MarketData
from ..db import get_db
from ..models import ChatSession
from ..security import require_owner
from .routes import market_dep

log = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_owner)], tags=["chat"])


@router.get("/chat/sessions")
def sessions(db: Session = Depends(get_db)):
    rows = db.scalars(select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(100))
    return {"sessions": [{"id": s.id, "title": s.title, "updated_at": s.updated_at.isoformat()} for s in rows]}


@router.post("/chat/sessions")
def new_session(db: Session = Depends(get_db)):
    s = ChatSession()
    db.add(s)
    db.flush()
    return {"id": s.id, "title": s.title}


@router.get("/chat/sessions/{sid}")
def get_session(sid: int, db: Session = Depends(get_db)):
    s = db.get(ChatSession, sid)
    if s is None:
        raise HTTPException(404, "Not found")
    return {"id": s.id, "title": s.title, "messages": chat_mod.display_messages(s)}


@router.delete("/chat/sessions/{sid}")
def delete_session(sid: int, db: Session = Depends(get_db)):
    s = db.get(ChatSession, sid)
    if s is None:
        raise HTTPException(404, "Not found")
    db.delete(s)
    return {"ok": True}


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


@router.post("/chat/sessions/{sid}/messages")
def send(sid: int, body: MessageIn, market: MarketData = Depends(market_dep)):
    """Streams Server-Sent Events. The generator owns its own DB session because it outlives the request handler."""
    check = dbmod.new_session()
    try:
        if check.get(ChatSession, sid) is None:
            raise HTTPException(404, "Not found")
    finally:
        check.close()

    def events():
        db = dbmod.new_session()
        try:
            session = db.get(ChatSession, sid)
            for ev in chat_mod.run_turn(db, session, body.text, market):
                yield f"data: {json.dumps(ev, default=str)}\n\n"
            db.commit()
        except Exception as e:  # never leave the client hanging
            log.exception("chat turn failed")
            db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'message': f'Server error: {type(e).__name__}'})}\n\n"
        finally:
            db.close()

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
