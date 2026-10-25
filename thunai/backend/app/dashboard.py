"""Supervisor dashboard (SPEC.md 11.2): breakdowns, downtime, KPIs, repeat faults, knowledge coverage.

Phase 3 (SPEC 12.2): spare parts used in breakdowns with current stock, and low stock.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import kpi, machines_service, parts, settings_store
from .models import AISession, BreakdownLog, Component, ExpertTip, FaultCard, LogPart, Machine, PartFit, SparePart

LIVE = ("approved", "needs_review")


def build(db: Session, *, days: int, zone: str = "") -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    hours = float(settings_store.get(db, "planned_hours_per_day"))

    mq = select(Machine).where(Machine.active.is_(True)).options(selectinload(Machine.machine_type)).order_by(Machine.machine_no)
    if zone:
        mq = mq.where(Machine.zone == zone)
    machines = list(db.scalars(mq))
    ids = [m.id for m in machines]
    by_id = {m.id: m for m in machines}

    logs = list(
        db.scalars(
            select(BreakdownLog)
            .where(BreakdownLog.machine_id.in_(ids or [0]), BreakdownLog.reported_at >= since)
            .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.classification))
        )
    )
    counted = [l for l in logs if l.status in kpi.COUNTED_STATUSES]
    open_logs = list(
        db.scalars(
            select(BreakdownLog)
            .where(BreakdownLog.machine_id.in_(ids or [0]), BreakdownLog.status == "open")
            .options(selectinload(BreakdownLog.texts), selectinload(BreakdownLog.machine))
            .order_by(BreakdownLog.reported_at)
        )
    )

    def downtime_by(key) -> list[dict]:
        sums: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for l in counted:
            k = key(l) or "Not recorded"
            sums[k][0] += l.downtime_min or 0
            sums[k][1] += 1
        return sorted(
            ({"name": k, "downtime_min": v[0], "breakdowns": v[1]} for k, v in sums.items()),
            key=lambda r: -r["downtime_min"],
        )

    per_machine: dict[int, list] = defaultdict(list)
    for l in counted:
        per_machine[l.machine_id].append(l.downtime_min)
    machine_rows = []
    for m in machines:
        k = kpi.compute(per_machine.get(m.id, []), days, hours)
        machine_rows.append(
            {
                "machine_no": m.machine_no,
                "name": m.name,
                "zone": m.zone,
                "criticality": m.criticality,
                "breakdowns": k.breakdowns,
                "downtime_min": k.downtime_min,
                "mttr_min": k.mttr_min,
                "mtbf_h": k.mtbf_h,
            }
        )
    machine_rows.sort(key=lambda r: (-r["downtime_min"], -r["breakdowns"], r["machine_no"]))

    faults = machines_service.top_faults(counted, limit=10)
    machines_per_fault: dict[str, set] = defaultdict(set)
    for l in counted:
        key, _ = machines_service.fault_key(l)
        machines_per_fault[key].add(by_id[l.machine_id].machine_no)
    for f in faults:
        f["machines"] = sorted(machines_per_fault.get(f["symptom"].lower(), set()))

    # Knowledge coverage: a machine is covered by a live card of its own or of its type.
    live_cards = list(db.scalars(select(FaultCard).where(FaultCard.status.in_(LIVE))))
    card_machines = {c.machine_id for c in live_cards if c.machine_id}
    card_types = {c.machine_type_id for c in live_cards if c.machine_id is None and c.machine_type_id}
    covered = [m for m in machines if m.id in card_machines or (m.machine_type_id and m.machine_type_id in card_types)]
    uncovered = [m for m in machines if m not in covered]
    verified = sum(1 for l in counted if l.status == "verified")
    approved_tips = db.scalar(
        select(func.count(ExpertTip.id)).where(ExpertTip.status == "approved", ExpertTip.machine_id.in_(ids or [0]))
    )

    sessions = list(db.scalars(select(AISession).where(AISession.machine_id.in_(ids or [0]), AISession.created_at >= since)))
    outcomes: dict[str, int] = defaultdict(int)
    for s in sessions:
        outcomes[s.outcome] += 1
    all_downtimes = [l.downtime_min for l in counted]
    overall = kpi.compute(all_downtimes, days, hours * max(len(machines), 1))
    stores = _parts(db, machines, counted)

    return {
        "days": days,
        "zone": zone,
        "machines": len(machines),
        "totals": {
            "open_breakdowns": len(open_logs),
            "breakdowns": overall.breakdowns,
            "downtime_min": overall.downtime_min,
            "mttr_min": overall.mttr_min,
            "logs_verified_pct": round(100 * verified / len(counted)) if counted else None,
        },
        "open_breakdowns": [
            {
                "id": l.id,
                "log_no": l.log_no,
                "machine_no": l.machine.machine_no,
                "issue": l.text("issue", "en"),
                "issue_ta": l.text("issue", "ta"),
                "reported_at": l.reported_at.isoformat(),
                "hours_open": round((now - l.reported_at).total_seconds() / 3600, 1),
                "escalated": l.escalated,
            }
            for l in open_logs
        ],
        "downtime_by_zone": downtime_by(lambda l: l.zone),
        "downtime_by_shift": sorted(downtime_by(lambda l: l.shift), key=lambda r: r["name"]),
        "machines_table": machine_rows,
        "top_faults": faults,
        "knowledge": {
            "machines_covered": len(covered),
            "machines_uncovered": [{"machine_no": m.machine_no, "name": m.name} for m in uncovered],
            "cards_live": len(live_cards),
            "cards_draft": db.scalar(select(func.count(FaultCard.id)).where(FaultCard.status == "draft")) or 0,
            "cards_needs_review": sum(1 for c in live_cards if c.status == "needs_review"),
            "tips_approved": approved_tips or 0,
            "tips_pending": db.scalar(select(func.count(ExpertTip.id)).where(ExpertTip.status == "pending")) or 0,
        },
        "parts": stores,
        "ask_thunai": {
            "sessions": len(sessions),
            "resolved": outcomes.get("resolved", 0),
            "escalated": outcomes.get("escalated", 0),
            "refused": outcomes.get("refused", 0),
            "failed": outcomes.get("failed", 0),
            "helpful": sum(1 for s in sessions if s.feedback == "helpful"),
            "not_helpful": sum(1 for s in sessions if s.feedback == "not_helpful"),
            "in_teams": sum(1 for s in sessions if s.channel == "copilot"),
        },
    }


def _parts(db: Session, machines: list[Machine], counted: list[BreakdownLog]) -> dict:
    """Parts used in the period's breakdowns (with current stock), and low stock for these machines."""
    ids = [l.id for l in counted] or [0]
    used: dict[str, dict] = {}
    for p in db.scalars(select(LogPart).where(LogPart.log_id.in_(ids))):
        key = (p.part_no or p.description).strip().upper()
        if not key:
            continue
        row = used.setdefault(key, {"part_no": p.part_no, "description": p.description, "times": 0, "qty": 0.0})
        row["times"] += 1
        row["qty"] += p.qty or 0
    numbers = [r["part_no"] for r in used.values() if r["part_no"]]
    catalogue = {sp.part_no.upper(): sp for sp in db.scalars(select(SparePart).where(SparePart.part_no.in_(numbers or [""])))}
    for r in used.values():
        sp = catalogue.get((r["part_no"] or "").upper())
        r["stock"] = parts.info(sp) if sp else None
    # Parts that fit these machines or their types, or match a component's part number (as on the
    # machine page, without manufacturer numbers), in two queries for any number of machines.
    ids = [m.id for m in machines] or [0]
    type_ids = list({m.machine_type_id for m in machines if m.machine_type_id}) or [0]
    component_nos = {
        n.strip().upper()
        for n in db.scalars(select(Component.part_no).where(Component.machine_id.in_(ids), Component.active.is_(True)))
        if n and n.strip()
    }
    fitting = select(SparePart).where(
        SparePart.active.is_(True),
        SparePart.fits.any(PartFit.machine_id.in_(ids) | PartFit.machine_type_id.in_(type_ids))
        | func.upper(SparePart.part_no).in_(component_nos or [""]),
    )
    low = [sp for sp in db.scalars(fitting) if sp.low]
    return {
        "used": sorted(used.values(), key=lambda r: (-r["times"], r["description"]))[:15],
        "low_stock": [parts.info(sp) for sp in sorted(low, key=lambda sp: (sp.stock_qty or 0, sp.part_no))],
    }

