"""JSON shapes returned by the API."""
from .models import AISession, BreakdownLog, Component, FaultCard, Glossary, LogMedia, Machine, User


def user(u: User) -> dict:
    return {
        "id": u.id,
        "employee_id": u.employee_id,
        "name": u.name,
        "role": u.role,
        "zone": u.zone,
        "preferred_language": u.preferred_language,
        "skill_level": u.skill_level,
        "phone": u.phone,
        "active": u.active,
        "locked": bool(u.locked_until),
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
    }


def component(c: Component) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "category": c.category,
        "part_no": c.part_no,
        "make": c.make,
        "location": c.location,
        "active": c.active,
    }


def machine(m: Machine, with_components: bool = False) -> dict:
    out = {
        "id": m.id,
        "machine_no": m.machine_no,
        "name": m.name,
        "machine_type": m.machine_type.name if m.machine_type else "",
        "zone": m.zone,
        "line": m.line,
        "make": m.make,
        "model": m.model,
        "plc_model": m.plc_model,
        "key_components": m.key_components,
        "criticality": m.criticality,
        "status": m.status,
        "qr_code": m.qr_code,
        "notes": m.notes,
        "active": m.active,
    }
    if with_components:
        out["components"] = [component(c) for c in m.components if c.active]
    return out


def media(md: LogMedia) -> dict:
    return {
        "id": md.id,
        "kind": md.kind,
        "mime": md.mime,
        "transcript": md.transcript,
        "stt_provider": md.stt_provider,
        "status": md.status,
        "available": md.purged_at is None,
        "created_at": md.created_at.isoformat(),
    }


def log(lg: BreakdownLog, full: bool = True) -> dict:
    texts = {
        t.field: {
            "original": t.original,
            "original_lang": t.original_lang,
            "en": t.english,
            "ta": t.tamil,
            "ai_filled": t.ai_filled,
            "unsure": t.ai_unsure,
        }
        for t in lg.texts
    }
    empty = {"original": "", "original_lang": "", "en": "", "ta": "", "ai_filled": False, "unsure": False}
    out = {
        "id": lg.id,
        "log_no": lg.log_no,
        "machine_no": lg.machine.machine_no,
        "machine_name": lg.machine.name,
        "zone": lg.zone,
        "shift": lg.shift,
        "shift_date": lg.shift_date.isoformat() if lg.shift_date else None,
        "reported_at": lg.reported_at.isoformat(),
        "start_at": lg.start_at.isoformat() if lg.start_at else None,
        "end_at": lg.end_at.isoformat() if lg.end_at else None,
        "downtime_min": lg.downtime_min,
        "alarm_code": lg.alarm_code,
        "status": lg.status,
        "source": lg.source,
        "escalated": lg.escalated,
        "needs_confirmation": lg.needs_confirmation,
        "technician_id": lg.technician_id,
        "technician_name": lg.technician.name if lg.technician else lg.technician_name,
        "verified_by": lg.verifier.name if lg.verifier else None,
        "verified_at": lg.verified_at.isoformat() if lg.verified_at else None,
        "reject_reason": lg.reject_reason,
        "ai_session_id": lg.ai_session_id,
        "texts": {f: texts.get(f, dict(empty)) for f in ("issue", "root_cause", "corrective_action")},
    }
    if full:
        out["parts"] = [{"part_no": p.part_no, "description": p.description, "qty": p.qty} for p in lg.parts]
        out["media"] = [media(m) for m in lg.media]
        c = lg.classification
        out["classification"] = (
            {
                "symptom_category": c.symptom_category,
                "component_name": c.component_name,
                "failure_mode": c.failure_mode,
                "confidence": c.confidence,
            }
            if c
            else None
        )
    return out


def fault_card(c: FaultCard) -> dict:
    return {
        "id": c.id,
        "ref": f"FC-{c.id}",
        "symptom": c.symptom,
        "symptom_ta": c.symptom_ta,
        "causes": c.causes,
        "steps_en": c.steps_en,
        "steps_ta": c.steps_ta,
        "parts": c.parts,
        "tools": c.tools,
        "avg_fix_min": c.avg_fix_min,
        "status": c.status,
        "version": c.version,
        "approved_at": c.approved_at.isoformat() if c.approved_at else None,
        "machine_id": c.machine_id,
        "machine_type_id": c.machine_type_id,
        "source_log_ids": c.source_log_ids,
        "flagged_log_ids": c.flagged_log_ids,
        "review_note": c.review_note,
        "history": c.history,
        "replaces_id": c.replaces_id,
        "drafted_at": c.drafted_at.isoformat() if c.drafted_at else None,
    }


def glossary(g: Glossary) -> dict:
    return {
        "id": g.id,
        "term_en": g.term_en,
        "term_ta": g.term_ta,
        "spoken_variants": g.spoken_variants,
        "category": g.category,
        "active": g.active,
    }


def session(s: AISession) -> dict:
    return {
        "id": s.id,
        "machine_no": s.machine.machine_no,
        "machine_name": s.machine.name,
        "technician_name": s.technician.name,
        "language": s.language,
        "problem_text": s.problem_text,
        "alarm_code": s.alarm_code,
        "questions": s.questions_and_answers,
        "steps": s.steps,
        "step_responses": s.step_responses,
        "procedure": s.procedure_meta,
        "sources": s.sources_used,
        "outcome": s.outcome,
        "feedback": s.feedback,
        "feedback_note": s.feedback_note,
        "resulting_log_id": s.resulting_log_id,
        "supervisor_called": s.supervisor_called,
        "model": s.model,
        "cost_usd": s.cost_usd,
        "created_at": s.created_at.isoformat(),
        "closed_at": s.closed_at.isoformat() if s.closed_at else None,
    }
