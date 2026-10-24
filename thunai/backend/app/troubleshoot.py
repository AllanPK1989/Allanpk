"""Ask Thunai: clarifying questions → safe step-by-step procedure → outcome and draft log."""
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import logs_service, retrieval, safety, settings_store
from .ai import schemas as ai_schemas
from .ai.service import AIOutputError, call_json
from .config import get_config
from .models import AISession, LogMedia, Machine, User, utcnow
from .schemas import LogIn, SessionStart, TextIn


def _machine_texts(machine: Machine) -> list[str]:
    return [
        machine.name,
        machine.machine_type.name if machine.machine_type else "",
        machine.key_components,
        " ".join(c.name for c in machine.components if c.active),
        " ".join(c.category for c in machine.components if c.active),
    ]


def _answers_text(session: AISession, lang: str = "en") -> str:
    rows = []
    for q in session.questions_and_answers:
        if q.get("answer") is None:
            continue
        label = next(
            (o[f"label_{lang}"] for o in q.get("options", []) if o["value"] == q["answer"]), q["answer"]
        )
        rows.append(f"- {q[f'text_{lang}']} → {label}")
    return "\n".join(rows) or "(no questions asked)"


def _variables(db: Session, session: AISession, ctx: retrieval.Context) -> dict:
    machine = session.machine
    return {
        "machine": retrieval.format_machine(machine),
        "components": retrieval.format_components(ctx.components),
        "glossary": retrieval.format_glossary(ctx.glossary),
        "context": retrieval.format_context(ctx),
        "language": {"en": "English", "ta": "Tamil"}.get(session.language, "English"),
        "problem": session.problem_text,
        "alarm_code": session.alarm_code or "none",
        "answers": _answers_text(session),
        "max_questions": settings_store.get(db, "max_clarifying_questions"),
    }


def _refuse(session: AISession, reason_en: str = "", reason_ta: str = "") -> None:
    session.outcome = "refused"
    session.steps = []
    session.closed_at = utcnow()
    session.procedure_meta = {
        "refused": True,
        "refuse_reason_en": reason_en or safety.REFUSAL["en"],
        "refuse_reason_ta": reason_ta or safety.REFUSAL["ta"],
        "call_supervisor": True,
    }


def start(db: Session, user: User, machine: Machine, data: SessionStart) -> AISession:
    session = AISession(
        machine=machine,
        technician=user,
        language=data.language,
        problem_text=data.problem_text.strip(),
        alarm_code=data.alarm_code.strip(),
    )
    db.add(session)
    db.flush()
    for media_id in data.media_ids:
        media = db.get(LogMedia, media_id)
        if media and media.created_by == user.id:
            media.ai_session_id = session.id

    if safety.check_request(session.problem_text).refused:
        _refuse(session)
        return session

    ctx = retrieval.build_context(db, machine, session.problem_text, session.alarm_code)
    session.sources_used = [i.as_dict() for i in ctx.items]
    hints = {
        "problem": session.problem_text,
        "alarm_code": session.alarm_code,
        "pneumatic": safety.is_pneumatic(session.problem_text, *_machine_texts(machine)),
        "items": session.sources_used,
    }
    out, _ = call_json(
        db,
        purpose="clarify",
        prompt_name="clarify",
        tier="diagnosis",
        variables=_variables(db, session, ctx),
        out_model=ai_schemas.ClarifyOut,
        max_tokens=4000,
        hints=hints,
        session=session,
    )
    limit = int(settings_store.get(db, "max_clarifying_questions"))
    questions = []
    for q in (out.questions if out else [])[:limit]:
        if 2 <= len(q.options) <= 4:
            questions.append({**q.model_dump(), "answer": None})
    session.questions_and_answers = questions
    if not questions:
        generate(db, session)
    return session


def answer(db: Session, session: AISession, answers: dict[str, str]) -> AISession:
    _require_open(session)
    updated = []
    for q in session.questions_and_answers:
        valid = {o["value"] for o in q["options"]}
        value = answers.get(q["id"])
        updated.append({**q, "answer": value if value in valid else "skipped"})
    session.questions_and_answers = updated  # new list so the JSON column is saved
    generate(db, session)
    return session


def _validator(proc: ai_schemas.TroubleshootOut) -> ai_schemas.TroubleshootOut:
    if proc.refuse:
        return proc
    if not proc.steps:
        raise AIOutputError("No steps returned. Give 3 to 10 steps.")
    unsafe = safety.find_unsafe_output(proc)
    if unsafe:
        raise AIOutputError(f"Unsafe instruction in {unsafe}. Never suggest bypassing or disabling safety devices.")
    return proc


def generate(db: Session, session: AISession) -> None:
    machine = session.machine
    # Search on the technician's words only; the answers go to the AI but would drown the query.
    ctx = retrieval.build_context(db, machine, session.problem_text, session.alarm_code)
    session.sources_used = [i.as_dict() for i in ctx.items]
    texts = _machine_texts(machine)
    hints = {
        "problem": session.problem_text,
        "items": session.sources_used,
        "answers": session.questions_and_answers,
    }
    out, error = call_json(
        db,
        purpose="troubleshoot",
        prompt_name="troubleshoot",
        tier="diagnosis",
        variables=_variables(db, session, ctx),
        out_model=ai_schemas.TroubleshootOut,
        max_tokens=16000,
        hints=hints,
        session=session,
        validate=_validator,
    )
    if out is None:
        session.outcome = "failed"
        session.steps = []
        session.procedure_meta = {"error": error[:300], "call_supervisor": True}
        return
    if out.refuse:
        _refuse(session, out.refuse_reason_en, out.refuse_reason_ta)
        return
    steps = safety.enforce_procedure(
        out,
        known_refs=ctx.refs,
        pneumatic=safety.is_pneumatic(session.problem_text, *texts),
        pressure_machine=safety.is_pressure_machine(*texts),
    )
    threshold = float(settings_store.get(db, "low_confidence_threshold"))
    causes = []
    for c in out.likely_causes[:3]:
        d = c.model_dump()
        d["source_refs"] = [r for r in c.source_refs if r in ctx.refs]
        causes.append(d)
    session.steps = steps
    session.procedure_meta = {
        "summary_en": out.summary_en,
        "summary_ta": out.summary_ta,
        "likely_causes": causes,
        "confidence": min(max(out.confidence, 0.0), 1.0),
        "no_history": not ctx.items,
        "low_confidence": out.confidence < threshold or not ctx.items,
        "explanations": {},
    }


def _require_open(session: AISession) -> None:
    if session.outcome != "in_progress":
        raise HTTPException(409, f"Session is {session.outcome}")


def _step(session: AISession, step_no: int) -> dict:
    step = next((s for s in session.steps if s["step_no"] == step_no), None)
    if step is None:
        raise HTTPException(404, "Step not found")
    return step


def record_step(db: Session, session: AISession, step_no: int, response: str) -> dict:
    _require_open(session)
    step = _step(session, step_no)
    session.step_responses = [
        *session.step_responses,
        {"step_no": step_no, "response": response, "at": utcnow().isoformat()},
    ]
    if response == "ok":
        nxt = step["if_ok_next"]
    elif response == "not_ok":
        nxt = step["if_not_ok_next"]
    else:  # can't do: safety and authorised steps stop here; others may be skipped
        nxt = -1 if (step["kind"] == "safety" or step["authorised_only"]) else None
    return {"next": nxt}


def explain(db: Session, session: AISession, step_no: int) -> dict:
    step = _step(session, step_no)
    cached = (session.procedure_meta or {}).get("explanations", {}).get(str(step_no))
    if cached:
        return cached
    out, error = call_json(
        db,
        purpose="explain",
        prompt_name="explain",
        tier="extraction",
        variables={
            "machine": retrieval.format_machine(session.machine),
            "problem": session.problem_text,
            "step": f"Do: {step['action_en']}\nCheck: {step['check_en']}\nExpected: {step['expected_result_en']}",
        },
        out_model=ai_schemas.ExplainOut,
        max_tokens=2000,
        hints={"step": step},
        session=session,
    )
    if out is None:
        raise HTTPException(503, "Explanation not available right now")
    result = out.model_dump()
    meta = dict(session.procedure_meta or {})
    meta["explanations"] = {**meta.get("explanations", {}), str(step_no): result}
    session.procedure_meta = meta
    return result


def summary_text(session: AISession) -> str:
    when = session.created_at.astimezone(ZoneInfo(get_config().plant_tz)).strftime("%d %b %Y %H:%M")
    machine = session.machine
    lines = [
        "Thunai: help needed",
        f"Machine: {machine.machine_no} {machine.name} ({machine.zone})",
        f"Technician: {session.technician.name}",
        f"Problem: {session.problem_text}",
    ]
    if session.alarm_code:
        lines.append(f"Alarm: {session.alarm_code}")
    answered = [q for q in session.questions_and_answers if q.get("answer")]
    for q in answered:
        lines.append(f"Q: {q['text_en']} A: {q['answer']}")
    labels = {"ok": "OK", "not_ok": "NOT OK", "cant_do": "CAN'T DO"}
    by_no = {s["step_no"]: s for s in session.steps}
    if session.step_responses:
        lines.append("Steps done:")
        for r in session.step_responses:
            s = by_no.get(r["step_no"], {})
            lines.append(f"  {r['step_no']}. {s.get('action_en', '')} → {labels.get(r['response'], r['response'])}")
    causes = (session.procedure_meta or {}).get("likely_causes", [])
    if causes:
        lines.append("Likely causes: " + "; ".join(c["cause_en"] for c in causes))
    if (session.procedure_meta or {}).get("refused"):
        lines.append("Request refused by safety rules.")
    lines.append(f"Session #{session.id}, started {when}")
    return "\n".join(lines)


def supervisors_for(db: Session, zone: str) -> list[dict]:
    rows = db.scalars(
        select(User).where(User.role == "supervisor", User.active.is_(True)).order_by(User.name)
    ).all()
    in_zone = [u for u in rows if u.zone == zone] or rows
    return [{"name": u.name, "phone": u.phone, "zone": u.zone} for u in in_zone]


def call_supervisor(db: Session, session: AISession) -> dict:
    session.supervisor_called = True
    return {"summary": summary_text(session), "supervisors": supervisors_for(db, session.machine.zone)}


def close(db: Session, user: User, session: AISession, running: bool) -> dict:
    if session.outcome not in ("in_progress", "failed", "refused"):
        raise HTTPException(409, f"Session is already {session.outcome}")
    machine = session.machine
    session.closed_at = utcnow()
    done = []
    for r in session.step_responses:
        s = next((x for x in session.steps if x["step_no"] == r["step_no"]), None)
        if s:
            done.append({**s, "response": r["response"]})

    if running:
        session.outcome = "resolved"
        draft, _ = call_json(
            db,
            purpose="session_to_log",
            prompt_name="session_to_log",
            tier="extraction",
            variables={"machine": retrieval.format_machine(machine), "session": summary_text(session)},
            out_model=ai_schemas.ExtractOut,
            max_tokens=3000,
            hints={
                "problem": session.problem_text,
                "language": session.language,
                "alarm_code": session.alarm_code,
                "steps_done": [d for d in done if d["response"] == "ok"],
                "likely_causes": (session.procedure_meta or {}).get("likely_causes", []),
            },
            session=session,
        )

        def text(name: str) -> TextIn:
            if draft is None:
                return TextIn()
            v = getattr(draft, name)
            return TextIn(original="", en=v.en, ta=v.ta, ai_filled=True, unsure=v.unsure)

        body = LogIn(
            machine_no=machine.machine_no,
            issue=TextIn(original=session.problem_text),  # the technician's own words
            root_cause=text("root_cause"),
            corrective_action=text("corrective_action"),
            start_at=session.created_at,
            end_at=utcnow(),
            alarm_code=session.alarm_code,
            parts=[{"description": p.description, "part_no": p.part_no, "qty": p.qty} for p in (draft.parts_replaced if draft else [])],
            source="ai_session",
            ai_session_id=session.id,
            submit=False,
        )
        log = logs_service.create_log(db, user, machine, body, source="ai_session")
        log.needs_confirmation = True
    else:
        session.outcome = "escalated"
        session.supervisor_called = True
        tried = "; ".join(
            f"{d['action_en']} ({d['response'].replace('_', ' ')})" for d in done if d["kind"] != "safety"
        )
        body = LogIn(
            machine_no=machine.machine_no,
            issue=TextIn(original=session.problem_text),
            corrective_action=TextIn(
                original="", en=f"Tried with Thunai: {tried}. Machine still down." if tried else "", ai_filled=True
            ),
            start_at=session.created_at,
            alarm_code=session.alarm_code,
            source="ai_session",
            ai_session_id=session.id,
            submit=False,
            still_down=True,
        )
        log = logs_service.create_log(db, user, machine, body, source="ai_session")
        log.escalated = True
        machine.status = "down"
    session.resulting_log_id = log.id
    return {
        "log_id": log.id,
        "outcome": session.outcome,
        "supervisors": [] if running else supervisors_for(db, machine.zone),
        "summary": "" if running else summary_text(session),
    }

