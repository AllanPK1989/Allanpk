"""Tool answers for the Copilot agent (SPEC 13): steps, sessions and logs in a form the agent can show.

The agent is told to show `display` texts exactly as written and to follow `agent_note`. Thunai's
stored session stays the record; the chat is only how it is shown.
"""
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import alarm_feed, parts, retrieval, safety
from .config import get_config
from .models import AISession, BreakdownLog, Machine, SparePart, User
from .schemas import TextIn

LABELS = {
    "en": {
        "step": "Step {n} of {total}",
        "kind": {"safety": "Safety", "check": "Check", "action": "Action"},
        "do": "Do",
        "check": "Check",
        "expected": "Should be",
        "authorised": "Authorised electrician only.",
        "general": "General suggestion: not seen on this machine before.",
        "tools": "Tools",
        "parts": "Parts",
        "from": "From",
        "reply": "Reply OK, NOT OK or CAN'T DO.",
        "low_confidence": "Thunai is not sure: no matching history. Call the supervisor if you are unsure.",
        "failed": "Thunai could not prepare steps for this. Call the supervisor.",
        "closed": "This troubleshooting session is already closed.",
        "skipped": "Step {n} skipped. If it matters, call the supervisor.",
        "stop": "Stop here. Keep the machine isolated and call the supervisor or an authorised person.",
        "finished": "All steps done. Is the machine running now?",
        "saved": "Saved as {log_no}. Thank you.",
        "draft": "Saved as draft {log_no}. Confirm it in the Thunai app.",
        "escalated": "Log {log_no} is open: the machine is still down. The supervisor has the summary.",
        "stock_unknown": "Stock not known",
        "out_of_stock": "Out of stock",
        "in": "in",
        "low": "low stock",
    },
    "ta": {
        "step": "Step {n} / {total}",
        "kind": {"safety": "Safety", "check": "Check", "action": "Action"},
        "do": "செய்யுங்க",
        "check": "பாருங்க",
        "expected": "இப்படி இருக்கணும்",
        "authorised": "Authorised electrician மட்டும்.",
        "general": "பொதுவான யோசனை: இந்த machine-ல இதுக்கு முன் பார்த்ததில்லை.",
        "tools": "Tools",
        "parts": "Parts",
        "from": "ஆதாரம்",
        "reply": "OK, NOT OK, அல்லது CAN'T DO-ன்னு சொல்லுங்க.",
        "low_confidence": "Thunai-க்கு உறுதியா தெரியல: இதுக்கு முன் history இல்லை. சந்தேகம்னா supervisor-ஐ கூப்பிடுங்க.",
        "failed": "இதுக்கு Thunai-ஆல steps தயார் பண்ண முடியல. Supervisor-ஐ கூப்பிடுங்க.",
        "closed": "இந்த session ஏற்கனவே முடிஞ்சிடுச்சு.",
        "skipped": "Step {n} விட்டாச்சு. முக்கியம்னா supervisor-ஐ கூப்பிடுங்க.",
        "stop": "இங்கேயே நிறுத்துங்க. Machine-ஐ isolate பண்ணியே வைங்க, supervisor அல்லது authorised ஆளை கூப்பிடுங்க.",
        "finished": "எல்லா steps-உம் முடிஞ்சது. Machine இப்போ ஓடுதா?",
        "saved": "{log_no}-ஆ save ஆயிடுச்சு. நன்றி.",
        "draft": "{log_no} draft-ஆ save ஆயிடுச்சு. Thunai app-ல confirm பண்ணுங்க.",
        "escalated": "Log {log_no} open-ல இருக்கு: machine இன்னும் down. Supervisor-க்கு summary போயிடுச்சு.",
        "stock_unknown": "Stock தெரியல",
        "out_of_stock": "Stock இல்லை",
        "in": "இருக்கு:",
        "low": "stock குறைவு",
    },
}

NOTES = {
    "questions": "Ask these questions one at a time with their options. Then call answerQuestions with all the answers.",
    "step": "Show current_step.display exactly as written, alone. Wait for OK, NOT OK or CAN'T DO, then call reportStep. "
    "Never skip, merge, reorder or add steps.",
    "translate": " The session is in Tamil but this step has no Tamil version: translate display faithfully into simple "
    "spoken Tamil, keep technical terms in English, change nothing else.",
    "finished": "Ask whether the machine runs now. If yes, ask what fixed it and the cause in the technician's own words, "
    "read the log back, and call closeSession with confirmed=true once they agree.",
    "stop": "Tell the technician to stop and keep the machine isolated. Call callSupervisor and share its summary. "
    "When they are done, call closeSession with running=false.",
    "refused": "Show message exactly. Do not suggest any workaround or partial steps. Offer to call the supervisor.",
    "failed": "Show message. Offer callSupervisor.",
    "closed": "This session is over. Start a new one with startTroubleshooting if the technician needs help again.",
}


def lang_of(value: str) -> str:
    return "ta" if value == "ta" else "en"


def plant_date(log: BreakdownLog) -> str:
    if log.shift_date:
        return log.shift_date.isoformat()
    return log.reported_at.astimezone(ZoneInfo(get_config().plant_tz)).date().isoformat()


def stock_text(info: dict, lang: str = "en") -> str:
    L = LABELS[lang_of(lang)]
    qty = info.get("stock_qty")
    if qty is None:
        text = L["stock_unknown"]
    elif qty <= 0:
        text = L["out_of_stock"]
    else:
        where = f" {L['in']} {info['location']}" if info.get("location") else ""
        text = f"{qty:g} {info.get('unit') or ''}".rstrip() + where
    if info.get("low") and qty:
        text += f" ({L['low']})"
    return text


def part_out(p: SparePart, lang: str = "en") -> dict:
    info = parts.info(p)
    return {
        "part_no": info["part_no"],
        "description": info["description"],
        "unit": info["unit"],
        "stock_qty": info["stock_qty"],
        "location": info["location"],
        "low": info["low"],
        "stock_text": stock_text(info, lang),
    }


def machine_out(db: Session, m: Machine) -> dict:
    alarm = alarm_feed.active(db, m)
    return {
        "machine_no": m.machine_no,
        "name": m.name,
        "machine_type": m.machine_type.name if m.machine_type else "",
        "zone": m.zone,
        "line": m.line,
        "status": m.status,
        "active_alarm_code": alarm.code if alarm else "",
    }


def _text(log: BreakdownLog, field: str) -> str:
    row = next((t for t in log.texts if t.field == field), None)
    return (row.english or row.original or row.tamil) if row else ""


def log_summary(log: BreakdownLog) -> dict:
    return {
        "log_no": log.log_no,
        "date": plant_date(log),
        "status": log.status,
        "verified": log.status == "verified",
        "technician": log.technician_name,
        "alarm_code": log.alarm_code,
        "issue": _text(log, "issue"),
        "root_cause": _text(log, "root_cause"),
        "fix": _text(log, "corrective_action"),
        "downtime_min": log.downtime_min,
    }


def logs_for(db: Session, machine: Machine, *, statuses: tuple[str, ...], alarm_code: str = "", user: User | None = None, limit: int = 5):
    q = (
        select(BreakdownLog)
        .where(BreakdownLog.machine_id == machine.id, BreakdownLog.status.in_(statuses))
        .options(selectinload(BreakdownLog.texts))
        .order_by(BreakdownLog.reported_at.desc())
        .limit(limit)
    )
    if alarm_code:
        q = q.where(func.upper(BreakdownLog.alarm_code) == alarm_code.strip().upper())
    if user is not None:  # drafts are personal
        q = q.where((BreakdownLog.status != "draft") | (BreakdownLog.technician_id == user.id))
    return list(db.scalars(q))


def alarm_out(db: Session, machine: Machine, code: str) -> dict:
    a = retrieval.lookup_alarm(db, machine, code)
    return {
        "code": a.code if a else code,
        "found": a is not None,
        "message": a.message if a else "",
        "cause": a.cause if a else "",
        "remedy": a.remedy if a else "",
        "past_fixes": [log_summary(l) for l in logs_for(db, machine, statuses=("closed", "verified"), alarm_code=code)],
    }


# ---- sessions ------------------------------------------------------------------------------------
def next_after(step: dict, response: str) -> int:
    """Where a response leads: a step number, 0 (finished) or -1 (stop and call the supervisor)."""
    if response == "ok":
        return step["if_ok_next"]
    if response == "not_ok":
        return step["if_not_ok_next"]
    if step["kind"] == "safety" or step["authorised_only"]:
        return -1
    return step["if_ok_next"]  # can't do an ordinary step: skip it, as the PWA's "Skip" does


def position(session: AISession) -> int:
    """The step to show now (step number), 0 when finished, -1 when stopped."""
    if not session.steps:
        return 0
    if not session.step_responses:
        return session.steps[0]["step_no"]
    last = session.step_responses[-1]
    step = next((s for s in session.steps if s["step_no"] == last["step_no"]), None)
    return next_after(step, last["response"]) if step else 0


def _pick(step: dict, name: str, lang: str) -> str:
    return (step.get(f"{name}_ta") if lang == "ta" else "") or step.get(f"{name}_en", "")


def _step_lang(step: dict, session_lang: str) -> str:
    """'ta' only when every English text of the step has a Tamil version; never mix languages in one step."""
    if session_lang != "ta":
        return "en"
    for name in ("action", "check", "expected_result", "safety_note"):
        if step.get(f"{name}_en") and not step.get(f"{name}_ta"):
            return "en"
    return "ta"


def step_out(db: Session, session: AISession, step: dict) -> dict:
    lang = _step_lang(step, session.language)
    L = LABELS[lang]
    total = len(session.steps)
    n = next((i for i, s in enumerate(session.steps, start=1) if s["step_no"] == step["step_no"]), step["step_no"])
    by_ref = {s["ref"]: s for s in session.sources_used or []}
    evidence = [
        {"ref": r, "label": by_ref[r].get("label", by_ref[r]["kind"]), "text": by_ref[r]["text_en"][:300]}
        for r in step.get("source_refs", [])
        if r in by_ref
    ]
    wanted = step.get("part_nos", [])
    rows = {p.part_no: p for p in db.scalars(select(SparePart).where(SparePart.part_no.in_(wanted)))} if wanted else {}
    step_parts = [part_out(rows[no], lang) for no in wanted if no in rows]
    texts = {name: _pick(step, name, lang) for name in ("action", "check", "expected_result", "safety_note")}

    lines = [f"**{L['step'].format(n=n, total=total)} · {L['kind'].get(step['kind'], step['kind'])}**"]
    lines.append(f"{L['do']}: {texts['action']}")
    if texts["check"]:
        lines.append(f"{L['check']}: {texts['check']}")
    if texts["expected_result"]:
        lines.append(f"{L['expected']}: {texts['expected_result']}")
    if texts["safety_note"]:
        lines.append(f"⚠️ {texts['safety_note']}")
    if step.get("authorised_only"):
        lines.append(f"🔒 {L['authorised']}")
    if step.get("tools"):
        lines.append(f"{L['tools']}: {', '.join(step['tools'])}")
    if step_parts:
        lines.append(f"{L['parts']}: " + "; ".join(f"{p['part_no']} {p['description']} ({p['stock_text']})" for p in step_parts))
    if evidence:
        lines.append(f"{L['from']}: " + ", ".join(e["ref"] for e in evidence))
    elif step.get("general"):
        lines.append(L["general"])
    lines.append(L["reply"])
    return {
        "step_no": step["step_no"],
        "total_steps": total,
        "kind": step["kind"],
        "language": lang,
        "action": texts["action"],
        "check": texts["check"],
        "expected_result": texts["expected_result"],
        "safety_note": texts["safety_note"],
        "tools": list(step.get("tools", [])),
        "authorised_only": bool(step.get("authorised_only")),
        "general": bool(step.get("general")),
        "evidence": evidence,
        "parts": step_parts,
        "display": "\n".join(lines),
    }


def session_out(db: Session, session: AISession, message: str = "") -> dict:
    lang = lang_of(session.language)
    L = LABELS[lang]
    meta = session.procedure_meta or {}
    out = {
        "session_id": session.id,
        "machine_no": session.machine.machine_no,
        "problem": session.problem_text,
        "alarm_code": session.alarm_code,
        "language": lang,
        "message": message,
        "summary": meta.get(f"summary_{lang}") or meta.get("summary_en", ""),
        "likely_causes": [
            {"cause": c.get(f"cause_{lang}") or c.get("cause_en", ""), "refs": c.get("source_refs", [])}
            for c in meta.get("likely_causes", [])
        ],
        "low_confidence": bool(meta.get("low_confidence")),
        "questions": [],
        "steps_done": len(session.step_responses or []),
    }
    if session.outcome == "refused":
        out.update(status="refused", message=meta.get(f"refuse_reason_{lang}") or safety.REFUSAL[lang], agent_note=NOTES["refused"])
        return out
    if session.outcome == "failed" or (session.outcome == "in_progress" and not session.steps and not _open_questions(session)):
        out.update(status="failed", message=message or L["failed"], agent_note=NOTES["failed"])
        return out
    if session.outcome != "in_progress":
        out.update(status="closed", message=message or L["closed"], agent_note=NOTES["closed"])
        return out
    questions = _open_questions(session)
    if questions:
        out["questions"] = [
            {
                "id": q["id"],
                "text": q.get(f"text_{lang}") or q["text_en"],
                "options": [{"value": o["value"], "label": o.get(f"label_{lang}") or o["label_en"]} for o in q["options"]],
            }
            for q in questions
        ]
        out.update(status="questions", agent_note=NOTES["questions"])
        return out
    if out["low_confidence"] and not session.step_responses:
        out["message"] = " ".join(x for x in (message, L["low_confidence"]) if x)
    at = position(session)
    if at == 0:
        out.update(status="finished", message=message or L["finished"], agent_note=NOTES["finished"])
    elif at == -1:
        out.update(status="stop", message=message or L["stop"], agent_note=NOTES["stop"])
    else:
        step = next(s for s in session.steps if s["step_no"] == at)
        current = step_out(db, session, step)
        note = NOTES["step"] + (NOTES["translate"] if lang == "ta" and current["language"] == "en" else "")
        out.update(status="step", current_step=current, agent_note=note)
    return out


def _open_questions(session: AISession) -> list[dict]:
    return [q for q in session.questions_and_answers or [] if q.get("answer") is None]


def text_in(words: str, english: str) -> TextIn | None:
    """The technician's words as the original, the agent's English version as `en`."""
    words, english = (words or "").strip(), (english or "").strip()
    if not words and not english:
        return None
    return TextIn(original=words or english, en=english or None)
