"""Skill-gap analytics by technician and machine type (SPEC 12.5).

For training and shift planning, not appraisal. Every figure comes with its count, and figures based
on fewer than `skill_min_events` events are not shown. Suggestions come from fixed rules, not the AI.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import kpi, settings_store
from .models import AISession, BreakdownLog, ExpertTip, Machine, User

NO_TYPE = "No machine type"
ESCALATION_SHARE = 0.5  # pair a technician when at least half their sessions on a type escalate
SLOW_RATIO = 1.5  # repairs this many times the team median are worth pairing on


def _tech_key(log: BreakdownLog) -> str | None:
    if log.technician_id:
        return f"u{log.technician_id}"
    name = (log.technician_name or "").strip()
    return f"n:{name.lower()}" if name else None


def _type(machine: Machine) -> str:
    return machine.machine_type.name if machine.machine_type else NO_TYPE


def build(db: Session, *, days: int, zone: str = "") -> dict:
    min_events = int(settings_store.get(db, "skill_min_events"))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    mq = select(Machine).options(selectinload(Machine.machine_type))
    if zone:
        mq = mq.where(Machine.zone == zone)
    machines = {m.id: m for m in db.scalars(mq)}
    ids = list(machines) or [0]

    logs = list(
        db.scalars(
            select(BreakdownLog).where(
                BreakdownLog.machine_id.in_(ids),
                BreakdownLog.status.in_(kpi.COUNTED_STATUSES),
                BreakdownLog.reported_at >= since,
            )
        )
    )
    sessions = list(
        db.scalars(select(AISession).where(AISession.machine_id.in_(ids), AISession.created_at >= since))
    )
    tips = list(
        db.scalars(
            select(ExpertTip).where(
                ExpertTip.machine_id.in_(ids), ExpertTip.status == "approved", ExpertTip.created_at >= since
            )
        )
    )
    users = {u.id: u for u in db.scalars(select(User))}

    people: dict[str, dict] = {}

    def person(key: str, log: BreakdownLog | None = None) -> dict:
        if key not in people:
            if key.startswith("u"):
                u = users.get(int(key[1:]))
                name, emp, home = (u.name, u.employee_id, u.zone) if u else ("Unknown", "", "")
            else:
                name, emp, home = (log.technician_name if log else key[2:]), "", ""
            people[key] = {
                "key": key, "name": name, "employee_id": emp, "zone": home, "in_thunai": key.startswith("u"),
                "fixes": 0, "verified": 0, "downtimes": [], "ratios": [], "sessions": 0, "escalated": 0,
                "cant_do": 0, "cant_do_authorised": 0, "tips": 0,
                "by_type": defaultdict(lambda: {"fixes": 0, "sessions": 0, "escalated": 0, "downtimes": []}),
            }
        return people[key]

    # Team median downtime per machine type, for the "vs team" ratio.
    type_downtimes: dict[str, list[int]] = defaultdict(list)
    type_breakdowns: dict[str, int] = defaultdict(int)
    for l in logs:
        t = _type(machines[l.machine_id])
        type_breakdowns[t] += 1
        if l.downtime_min is not None:
            type_downtimes[t].append(l.downtime_min)
    type_median = {t: median(v) for t, v in type_downtimes.items() if v}

    for l in logs:
        key = _tech_key(l)
        if key is None:
            continue
        p = person(key, l)
        t = _type(machines[l.machine_id])
        p["fixes"] += 1
        p["verified"] += l.status == "verified"
        p["by_type"][t]["fixes"] += 1
        if l.downtime_min is not None:
            p["downtimes"].append(l.downtime_min)
            p["by_type"][t]["downtimes"].append(l.downtime_min)
            if type_median.get(t):
                p["ratios"].append(l.downtime_min / type_median[t])

    for s in sessions:
        p = person(f"u{s.technician_id}")
        t = _type(machines[s.machine_id])
        p["sessions"] += 1
        p["by_type"][t]["sessions"] += 1
        if s.outcome == "escalated" or s.supervisor_called:
            p["escalated"] += 1
            p["by_type"][t]["escalated"] += 1
        by_no = {st["step_no"]: st for st in s.steps or []}
        for r in s.step_responses or []:
            if r.get("response") == "cant_do":
                p["cant_do"] += 1
                if by_no.get(r.get("step_no"), {}).get("authorised_only"):
                    p["cant_do_authorised"] += 1

    for tip in tips:
        person(f"u{tip.author_id}")["tips"] += 1

    types = sorted(set(type_breakdowns) | {t for p in people.values() for t in p["by_type"]})

    def enough(n: int) -> bool:
        return n >= min_events

    technicians = []
    for p in sorted(people.values(), key=lambda x: (-x["fixes"], x["name"])):
        technicians.append(
            {
                "key": p["key"], "name": p["name"], "employee_id": p["employee_id"], "zone": p["zone"],
                "in_thunai": p["in_thunai"], "fixes": p["fixes"], "verified": p["verified"],
                "median_downtime_min": round(median(p["downtimes"])) if enough(len(p["downtimes"])) else None,
                "vs_team": round(median(p["ratios"]), 2) if enough(len(p["ratios"])) else None,
                "sessions": p["sessions"], "escalated": p["escalated"],
                "escalation_pct": round(100 * p["escalated"] / p["sessions"]) if enough(p["sessions"]) else None,
                "cant_do": p["cant_do"], "cant_do_authorised": p["cant_do_authorised"], "tips": p["tips"],
                "machine_types": sorted(t for t, c in p["by_type"].items() if c["fixes"]),
            }
        )

    matrix = [
        {"key": p["key"], "name": p["name"], "cells": {t: p["by_type"][t]["fixes"] for t in types if p["by_type"][t]["fixes"]}}
        for p in sorted(people.values(), key=lambda x: (-x["fixes"], x["name"]))
        if p["fixes"]
    ]

    type_rows = []
    for t in types:
        fixers = [p for p in people.values() if p["by_type"][t]["fixes"]]
        sess = sum(p["by_type"][t]["sessions"] for p in people.values())
        esc = sum(p["by_type"][t]["escalated"] for p in people.values())
        type_rows.append(
            {
                "name": t, "breakdowns": type_breakdowns.get(t, 0), "fixers": len(fixers),
                "fixer_names": sorted(p["name"] for p in fixers),
                "median_downtime_min": round(type_median[t]) if t in type_median and enough(len(type_downtimes[t])) else None,
                "sessions": sess, "escalation_pct": round(100 * esc / sess) if enough(sess) else None,
            }
        )
    type_rows.sort(key=lambda r: (-r["breakdowns"], r["name"]))

    return {
        "days": days,
        "zone": zone,
        "min_events": min_events,
        "technicians": technicians,
        "types": types,
        "matrix": matrix,
        "machine_types": type_rows,
        "suggestions": suggestions(people, type_rows, type_median, min_events),
    }


def suggestions(people: dict, type_rows: list[dict], type_median: dict, min_events: int) -> list[dict]:
    out: list[dict] = []

    def best_partner(t: str, exclude: str) -> dict | None:
        candidates = [p for p in people.values() if p["key"] != exclude and p["in_thunai"] and p["by_type"][t]["fixes"] >= min_events]
        return max(candidates, key=lambda p: p["by_type"][t]["fixes"], default=None)

    # 1. Single-person knowledge: a machine type with breakdowns that only one person fixed.
    for r in type_rows:
        if r["breakdowns"] and r["fixers"] <= 1:
            who = r["fixer_names"][0] if r["fixer_names"] else None
            text = (
                f"Only {who} fixed {r['name']} breakdowns in this period ({r['breakdowns']}). Train a second person."
                if who
                else f"{r['name']}: {r['breakdowns']} breakdowns with no technician recorded. Record who fixes them."
            )
            out.append({"kind": "single_person", "machine_type": r["name"], "technician": who, "partner": None, "text_en": text})

    for p in people.values():
        if not p["in_thunai"]:
            continue
        for t, c in p["by_type"].items():
            # 2. Escalates often on a type where someone else fixes it regularly.
            if c["sessions"] >= min_events and c["escalated"] / c["sessions"] >= ESCALATION_SHARE:
                partner = best_partner(t, p["key"])
                if partner:
                    out.append({
                        "kind": "pair", "machine_type": t, "technician": p["name"], "partner": partner["name"],
                        "text_en": f"{p['name']} called the supervisor in {c['escalated']} of {c['sessions']} Ask Thunai sessions on {t}. "
                                   f"Pair with {partner['name']} ({partner['by_type'][t]['fixes']} fixes) on the next ones.",
                    })
            # 3. Repairs take much longer than the team's on this type.
            d = c["downtimes"]
            if len(d) >= min_events and type_median.get(t) and median(d) >= SLOW_RATIO * type_median[t]:
                partner = best_partner(t, p["key"])
                if partner:
                    out.append({
                        "kind": "pair", "machine_type": t, "technician": p["name"], "partner": partner["name"],
                        "text_en": f"{p['name']}'s {t} repairs take about {median(d) / type_median[t]:.1f}× the team median "
                                   f"({len(d)} repairs). Pair with {partner['name']} to share the method.",
                    })
        # 4. Authorised-only electrical steps that could not be done.
        if p["cant_do_authorised"] >= min_events:
            out.append({
                "kind": "authorisation", "machine_type": None, "technician": p["name"], "partner": None,
                "text_en": f"{p['name']} could not do {p['cant_do_authorised']} authorised-only electrical steps. "
                           "If this holds up repairs on their shift, plan an authorised electrician or authorisation training.",
            })
    seen, unique = set(), []
    for item in out:  # one suggestion per kind, person and machine type
        key = (item["kind"], item["technician"], item["machine_type"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
