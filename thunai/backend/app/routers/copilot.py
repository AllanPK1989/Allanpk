"""Tool API for the Microsoft Copilot agent (SPEC 13.2).

Every route has an operationId and a description written for the Copilot orchestrator; the
connector's OpenAPI 2.0 file is generated from these routes (app/copilot_spec.py). Callers sign in
with Microsoft Entra ID (app/entra.py). The PWA keeps using its own routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import alarm_feed, audit, copilot, jobs, logs_service, machines_service, parts, retrieval, safety, troubleshoot
from .. import copilot_schemas as S
from ..db import get_db
from ..entra import copilot_roles, copilot_user
from ..models import AISession, BreakdownLog, FaultCard, LogText, Machine, User, utcnow
from ..schemas import LogIn, SessionStart, TextIn

router = APIRouter(prefix="/api/copilot", tags=["copilot"])
supervisor_or_admin = copilot_roles("supervisor", "admin")
OUT = {"response_model_exclude_none": True}


def _session(db: Session, session_id: int, user: User, *, own: bool = True) -> AISession:
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
    if (own or user.role == "technician") and session.technician_id != user.id:
        raise HTTPException(403, "This is another technician's session")
    return session


def _open(session: AISession) -> None:
    if session.outcome != "in_progress":
        raise HTTPException(409, f"The session is {session.outcome}. Start a new one with startTroubleshooting.")


# ---- people and machines -------------------------------------------------------------------------
@router.get("/me", operation_id="whoAmI", response_model=S.Me, summary="Who is signed in")
def me(user: User = Depends(copilot_user)):
    """The signed-in technician's name, role, zone and preferred language. Call it at the start of a
    conversation to greet them and to answer in their language."""
    return {"employee_id": user.employee_id, "name": user.name, "role": user.role, "zone": user.zone,
            "language": copilot.lang_of(user.preferred_language)}


@router.get("/machines", operation_id="findMachines", response_model=S.MachineList, summary="Find machines")
def find_machines(
    q: str = Query("", max_length=60, description="Part of a machine number, name or line. Empty: machines in the technician's zone."),
    user: User = Depends(copilot_user),
    db: Session = Depends(get_db),
):
    """Find machines by number, name or line. Use it when the technician names a machine loosely
    ("the shrink oven on line 2") and ask them to pick when more than one matches."""
    query = select(Machine).where(Machine.active.is_(True)).options(selectinload(Machine.machine_type)).order_by(Machine.machine_no)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.where(or_(func.lower(Machine.machine_no).like(like), func.lower(Machine.name).like(like), func.lower(Machine.line).like(like)))
    elif user.zone:
        query = query.where(Machine.zone == user.zone)
    return {"machines": [copilot.machine_out(db, m) for m in db.scalars(query.limit(10))]}


@router.get("/machines/{machine_no}", operation_id="getMachine", response_model=S.MachineDetail, summary="Machine status and history", **OUT)
def get_machine(machine_no: str, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """Status of one machine: active PLC/SCADA alarm with its alarm-list meaning, alarms in the last
    24 hours, open breakdowns, the last fixes, approved fault cards and parts low in stock. Use it for
    questions about a machine. For repair help use startTroubleshooting instead."""
    machine = machines_service.get_machine(db, machine_no)
    alarm = alarm_feed.active(db, machine)
    cards = db.scalars(
        select(FaultCard).where(
            FaultCard.status == "approved",
            (FaultCard.machine_id == machine.id)
            | ((FaultCard.machine_type_id == machine.machine_type_id) & FaultCard.machine_id.is_(None)),
        ).order_by(FaultCard.id)
    )
    return {
        "machine": copilot.machine_out(db, machine),
        "active_alarm": copilot.alarm_out(db, machine, alarm.code) if alarm else None,
        "alarms_24h": alarm_feed.counts(alarm_feed.recent(db, machine))[:10],
        "open_logs": [copilot.log_summary(l) for l in copilot.logs_for(db, machine, statuses=("open", "draft"), user=user)],
        "recent_fixes": [copilot.log_summary(l) for l in copilot.logs_for(db, machine, statuses=("closed", "verified"))],
        "fault_cards": [f"{retrieval.card_ref(c)}: {c.symptom}" for c in cards][:10],
        "low_stock_parts": [copilot.part_out(p, user.preferred_language) for p in parts.for_machine(db, machine) if p.low][:10],
    }


@router.get("/machines/{machine_no}/alarms/{code}", operation_id="lookupAlarm", response_model=S.AlarmOut, summary="What an alarm code means")
def lookup_alarm(machine_no: str, code: str, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """The meaning, likely cause and remedy of an alarm code from this machine's alarm list, with
    past fixes for the same code. Say so plainly when found is false; never guess a meaning."""
    machine = machines_service.get_machine(db, machine_no)
    return copilot.alarm_out(db, machine, code.strip()[:60])


# ---- troubleshooting -----------------------------------------------------------------------------
@router.post("/sessions", operation_id="startTroubleshooting", response_model=S.SessionOut, summary="Start troubleshooting", **OUT)
def start(body: S.NewSession, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """Start step-by-step repair help for a breakdown. Thunai refuses unsafe requests, may return a few
    tap questions, and otherwise returns the first step (always the safety step). Pass what you read
    from any photos the technician sent. Follow status and agent_note in the answer."""
    machine = machines_service.get_machine(db, body.machine_no)
    data = SessionStart(machine_no=machine.machine_no, problem_text=body.problem, alarm_code=body.alarm_code, language=body.language)
    session = troubleshoot.start(db, user, machine, data, channel="copilot", observations=[p.model_dump() for p in body.photos])
    db.commit()
    return copilot.session_out(db, _session(db, session.id, user))


@router.post("/sessions/{session_id}/answers", operation_id="answerQuestions", response_model=S.SessionOut, summary="Answer the tap questions", **OUT)
def answer(session_id: int, body: S.Answers, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """Send the technician's answers to the questions from startTroubleshooting. Returns the first step."""
    session = _session(db, session_id, user)
    _open(session)
    troubleshoot.answer(db, session, {a.question_id: a.value for a in body.answers})
    db.commit()
    return copilot.session_out(db, session)


@router.get("/sessions/{session_id}", operation_id="getSession", response_model=S.SessionOut, summary="Where a session is", **OUT)
def get_session(session_id: int, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """The current state of a troubleshooting session and the step to show now. Use it to pick up
    after a pause."""
    return copilot.session_out(db, _session(db, session_id, user, own=False))


@router.post("/sessions/{session_id}/steps", operation_id="reportStep", response_model=S.SessionOut, summary="Report a step result", **OUT)
def report_step(session_id: int, body: S.StepResult, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """Record OK, NOT OK or CAN'T DO for the current step. Returns the next step, 'finished', or 'stop'
    (stop and call the supervisor). Only the current step can be answered."""
    session = _session(db, session_id, user)
    _open(session)
    if copilot.position(session) != body.step_no:
        raise HTTPException(409, "That is not the current step. Call getSession and show its current_step.")
    step = next(s for s in session.steps if s["step_no"] == body.step_no)
    troubleshoot.record_step(db, session, body.step_no, body.result)
    db.commit()
    lang = copilot.lang_of(session.language)
    skipped = body.result == "cant_do" and copilot.next_after(step, "cant_do") != -1
    message = copilot.LABELS[lang]["skipped"].format(n=body.step_no) if skipped else ""
    return copilot.session_out(db, session, message)


@router.post("/sessions/{session_id}/call-supervisor", operation_id="callSupervisor", response_model=S.SupervisorHelp, summary="Call the supervisor")
def call_supervisor(session_id: int, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """Mark that the supervisor is needed and get a ready summary of the session plus the zone
    supervisors' names and phone numbers. Use it whenever the technician is stuck or unsafe."""
    session = _session(db, session_id, user)
    result = troubleshoot.call_supervisor(db, session)
    db.commit()
    names = ", ".join(f"{s['name']} ({s['phone']})" if s["phone"] else s["name"] for s in result["supervisors"])
    return {**result, "message": f"Supervisor: {names}" if names else "No supervisor is listed. Call your shift in-charge."}


@router.post("/sessions/{session_id}/close", operation_id="closeSession", response_model=S.ClosedSession, summary="Close the session and save the log")
def close(session_id: int, body: S.CloseSession, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """End the session and save the breakdown log. Before calling with running=true, ask what fixed it
    and the cause in the technician's own words, read the log back, and set confirmed=true only when
    they agree. With running=false the log stays open and the supervisor gets the summary."""
    session = _session(db, session_id, user)
    if body.running and body.confirmed and not (body.what_fixed_it or body.what_fixed_it_en):
        raise HTTPException(422, "Ask the technician what fixed it before saving the log.")
    result = troubleshoot.close(
        db,
        user,
        session,
        body.running,
        fixed=copilot.text_in(body.what_fixed_it, body.what_fixed_it_en),
        cause=copilot.text_in(body.root_cause, body.root_cause_en),
        parts_used=[p.model_dump() for p in body.parts_used] if body.parts_used else None,
        confirmed=body.confirmed,
    )
    db.commit()
    log = db.get(BreakdownLog, result["log_id"])
    L = copilot.LABELS[copilot.lang_of(session.language)]
    key = "escalated" if not body.running else ("saved" if log.status == "closed" else "draft")
    return {
        "log_no": log.log_no,
        "log_status": log.status,
        "outcome": result["outcome"],
        "supervisors": result["supervisors"],
        "summary": result["summary"],
        "message": L[key].format(log_no=log.log_no),
    }


# ---- logs, parts and safety ----------------------------------------------------------------------
@router.post("/logs", operation_id="createLog", response_model=S.SavedLog, summary="Log a breakdown fix")
def create_log(body: S.NewLog, user: User = Depends(copilot_user), db: Session = Depends(get_db)):
    """Save a breakdown log the technician tells you about, without a troubleshooting session. Keep
    their own words in issue, corrective_action and root_cause, and add English versions when they
    spoke Tamil. Read the log back and set confirmed=true only when they agree."""
    if not body.confirmed:
        raise HTTPException(422, "Read the log back to the technician and ask them to confirm first.")
    machine = machines_service.get_machine(db, body.machine_no)
    data = LogIn(
        machine_no=machine.machine_no,
        issue=copilot.text_in(body.issue, body.issue_en),
        corrective_action=copilot.text_in(body.corrective_action, body.corrective_action_en),
        root_cause=copilot.text_in(body.root_cause, body.root_cause_en) or TextIn(),
        start_at=body.start_at,
        end_at=body.end_at,
        downtime_min=body.downtime_min,
        alarm_code=body.alarm_code,
        parts=[p.model_dump() for p in body.parts_used],
        still_down=body.still_down,
        submit=True,
    )
    log = logs_service.create_log(db, user, machine, data, source="copilot")
    db.commit()
    return {"log_no": log.log_no, "log_status": log.status, "machine_no": machine.machine_no,
            "message": copilot.LABELS[copilot.lang_of(user.preferred_language)]["saved"].format(log_no=log.log_no)}


@router.get("/parts", operation_id="searchParts", response_model=S.PartList, summary="Spare parts and stock")
def search_parts(
    q: str = Query("", max_length=80, description="Part number or words from the description."),
    machine_no: str = Query("", max_length=60, description="Optional: list this machine's parts first."),
    user: User = Depends(copilot_user),
    db: Session = Depends(get_db),
):
    """Spare parts from the stores catalogue with stock on hand and store location. Quote part numbers
    only from this answer, never from memory."""
    machine = machines_service.get_machine(db, machine_no) if machine_no.strip() else None
    return {"parts": [copilot.part_out(p, user.preferred_language) for p in parts.search(db, q, machine, limit=10)]}


@router.post("/safety-check", operation_id="checkSafety", response_model=S.SafetyAnswer, summary="Check an instruction is safe")
def check_safety(body: S.SafetyQuestion, user: User = Depends(copilot_user)):
    """Check any instruction or advice that did not come from a Thunai step BEFORE you say it. If
    allowed is false, do not give the instruction: show message instead."""
    verdict = safety.check_request(body.text)  # also catches "bypass it" when the device is named elsewhere
    phrase = safety.unsafe_instruction(body.text) or verdict.reason
    if phrase:
        return {"allowed": False, "phrase": phrase, "message": safety.REFUSAL[copilot.lang_of(body.language)]}
    return {"allowed": True}


# ---- translations (supervisors) ------------------------------------------------------------------
TRANSLATABLE = ("open", "closed", "verified")


def _texts_to_translate(db: Session, user: User):
    q = (
        select(LogText, BreakdownLog)
        .join(BreakdownLog, LogText.log_id == BreakdownLog.id)
        .where(
            BreakdownLog.status.in_(TRANSLATABLE),
            LogText.original != "",
            (LogText.english == "") | (LogText.tamil == ""),
        )
        .order_by(BreakdownLog.reported_at.desc(), LogText.id)
    )
    if user.role == "supervisor" and user.zone:
        q = q.where(BreakdownLog.zone == user.zone)
    return q


def _may_translate(user: User, log: BreakdownLog) -> bool:
    """Same rules as listLogsToTranslate: submitted logs, and a supervisor's own zone."""
    return log.status in TRANSLATABLE and not (user.role == "supervisor" and user.zone and log.zone != user.zone)


@router.get("/translations", operation_id="listLogsToTranslate", response_model=S.TranslationList, summary="Log texts that need translating")
def list_translations(
    limit: int = Query(10, ge=1, le=20, description="How many texts to return."),
    user: User = Depends(supervisor_or_admin),
    db: Session = Depends(get_db),
):
    """For supervisors and admins: log texts that have no English or no Tamil version yet, newest
    first. Translate each one, then send them with saveTranslations."""
    q = _texts_to_translate(db, user)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    machines = {m.id: m.machine_no for m in db.scalars(select(Machine))}
    items = []
    for text, log in db.execute(q.limit(limit)).all():
        needs = [lang for lang, value in (("en", text.english), ("ta", text.tamil)) if not value]
        items.append({"text_id": text.id, "log_no": log.log_no, "machine_no": machines.get(log.machine_id, ""),
                      "field": text.field, "original": text.original, "original_lang": text.original_lang or "", "needs": needs})
    return {"items": items, "remaining": max(total - len(items), 0)}


@router.post("/translations", operation_id="saveTranslations", response_model=S.TranslationsSaved, summary="Save translations")
def save_translations(body: S.Translations, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    """For supervisors and admins: store translations of texts from listLogsToTranslate. Only empty
    versions are filled; the technician's words and existing versions are never changed."""
    saved = skipped = 0
    touched: dict[int, BreakdownLog] = {}
    for item in body.items:
        text = db.get(LogText, item.text_id)
        if text is None or not text.original or not _may_translate(user, text.log):
            skipped += 1
            continue
        changed = False
        for attr, value in (("english", item.en), ("tamil", item.ta)):
            if value and not getattr(text, attr):
                setattr(text, attr, value[:2000])
                changed = True
        if changed:
            text.translated_at = utcnow()
            touched[text.log_id] = text.log
            saved += 1
        else:
            skipped += 1
    for log in touched.values():
        audit.record(db, user, "breakdown_log", log.id, "translated_by_copilot", None, logs_service.snapshot(logs_service.load_log(db, log.id)))
        jobs.enqueue(db, "enrich_log", log_id=log.id)  # classify again with the English text
    db.commit()
    return {"saved": saved, "skipped": skipped, "message": f"Saved {saved} translation(s)." + (f" Skipped {skipped}." if skipped else "")}
