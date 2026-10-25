from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import machines_service, parts, retrieval, serialize, troubleshoot
from ..db import get_db
from ..models import AISession, LogMedia, Machine, SparePart, User
from ..schemas import AnswersIn, CloseIn, ExplainIn, FeedbackIn, SessionStart, StepResponseIn
from ..security import current_user

router = APIRouter(prefix="/api/ai", tags=["ask-thunai"])


def _load(db: Session, session_id: int, user: User) -> AISession:
    session = db.scalar(
        select(AISession)
        .where(AISession.id == session_id)
        .options(
            selectinload(AISession.machine).selectinload(Machine.components),
            selectinload(AISession.machine).selectinload(Machine.machine_type),
            selectinload(AISession.technician),
        )
    )
    if session is None:
        raise HTTPException(404, "Session not found")
    if user.role == "technician" and session.technician_id != user.id:
        raise HTTPException(403, "Not your session")
    return session


def _out(db: Session, session: AISession) -> dict:
    data = serialize.session(session)
    wanted = {n for step in data["steps"] for n in step.get("part_nos", [])}
    stock = {p.part_no: parts.info(p) for p in db.scalars(select(SparePart).where(SparePart.part_no.in_(wanted)))} if wanted else {}
    for step in data["steps"]:
        step["evidence"] = retrieval.evidence(session.sources_used, step.get("source_refs", []), session.machine.machine_no)
        step["parts"] = [stock[n] for n in step.get("part_nos", []) if n in stock]  # live stock, not a copy
    data["photos"] = [
        {"media_id": m.id}
        for m in db.scalars(select(LogMedia).where(LogMedia.ai_session_id == session.id, LogMedia.kind == "photo"))
    ]
    data["observations"] = session.observations or []  # photo readings from the Copilot agent
    return data


@router.post("/sessions")
def start(body: SessionStart, user: User = Depends(current_user), db: Session = Depends(get_db)):
    machine = machines_service.get_machine(db, body.machine_no)
    session = troubleshoot.start(db, user, machine, body)
    db.commit()
    return _out(db, _load(db, session.id, user))


@router.get("/sessions/{session_id}")
def get_session(session_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _out(db, _load(db, session_id, user))


@router.post("/sessions/{session_id}/answers")
def answers(session_id: int, body: AnswersIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = troubleshoot.answer(db, _load(db, session_id, user), body.answers)
    db.commit()
    return _out(db, session)


@router.post("/sessions/{session_id}/steps")
def step(session_id: int, body: StepResponseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    result = troubleshoot.record_step(db, _load(db, session_id, user), body.step_no, body.response)
    db.commit()
    return result


@router.post("/sessions/{session_id}/explain")
def explain(session_id: int, body: ExplainIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    result = troubleshoot.explain(db, _load(db, session_id, user), body.step_no)
    db.commit()
    return result


@router.post("/sessions/{session_id}/call-supervisor")
def call_supervisor(session_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    result = troubleshoot.call_supervisor(db, _load(db, session_id, user))
    db.commit()
    return result


@router.post("/sessions/{session_id}/close")
def close(session_id: int, body: CloseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    result = troubleshoot.close(db, user, _load(db, session_id, user), body.running)
    db.commit()
    return result


@router.post("/sessions/{session_id}/feedback")
def feedback(session_id: int, body: FeedbackIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _load(db, session_id, user)
    session.feedback = body.feedback
    session.feedback_note = body.note[:1000]
    db.commit()
    return {"ok": True}
