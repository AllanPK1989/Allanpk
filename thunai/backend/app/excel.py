"""Excel import (machine master, historical breakdowns, spare parts, PM plan) and export."""
import csv
import io
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import audit, jobs, machines_service, parts, pm, settings_store
from .config import get_config
from .kpi import COUNTED_STATUSES, compute
from .logs_service import set_text
from .models import BreakdownLog, LogPart, Machine, User, utcnow
from .schemas import MachineIn, MachineUpdate
from .shifts import downtime_minutes, shift_for
from .textutil import detect_lang

MACHINE_COLUMNS = {
    "machine_no": ("machine_no", "machine no", "machine number", "m/c no", "mc no", "asset no", "machine"),
    "name": ("name", "machine name", "description"),
    "machine_type": ("machine_type", "type", "machine type"),
    "zone": ("zone",),
    "line": ("line",),
    "make": ("make", "manufacturer"),
    "model": ("model",),
    "plc_model": ("plc_model", "plc", "plc model"),
    "key_components": ("key_components", "key components", "components"),
    "criticality": ("criticality", "class"),
    "status": ("status",),
}
LOG_COLUMNS = {
    "machine_no": MACHINE_COLUMNS["machine_no"],
    "date": ("date", "breakdown date", "shift date"),
    "start_time": ("start_time", "start time", "start", "from"),
    "end_time": ("end_time", "end time", "end", "to"),
    "downtime_min": ("downtime_min", "downtime", "downtime (min)", "duration", "bd time"),
    "shift": ("shift",),
    "technician": ("technician", "attended by", "technician name", "employee_id", "done by"),
    "alarm_code": ("alarm_code", "alarm", "alarm code", "error code"),
    "issue": ("issue", "problem", "breakdown", "fault", "complaint"),
    "root_cause": ("root_cause", "root cause", "cause", "reason"),
    "corrective_action": ("corrective_action", "corrective action", "action", "action taken", "remedy"),
    "parts_replaced": ("parts_replaced", "parts replaced", "spares", "spares used", "parts"),
}
SAMPLE_MACHINE = {
    "machine_no": "DEMO-XX-01",
    "name": "[SAMPLE] Delete this row",
    "machine_type": "Sand filling machine",
    "zone": "Bussmann Zone 1",
    "line": "Line 1",
    "make": "",
    "model": "",
    "plc_model": "Mitsubishi FX5U",
    "key_components": "Cylinder, solenoid valve, proximity sensor",
    "criticality": "A",
    "status": "running",
}
SAMPLE_LOG = {
    "machine_no": "DEMO-XX-01",
    "date": "2026-01-15",
    "start_time": "10:05",
    "end_time": "10:40",
    "downtime_min": "",
    "shift": "",
    "technician": "",
    "alarm_code": "",
    "issue": "[SAMPLE] Delete this row",
    "root_cause": "",
    "corrective_action": "",
    "parts_replaced": "",
}


def _norm(header) -> str:
    return re.sub(r"\s+", " ", str(header or "").strip().lower().replace("_", " ")).replace(" ", "_")


def _sheet_rows(content: bytes):
    """Rows of the first sheet of an .xlsx file, or of a CSV file (comma or semicolon)."""
    if content[:2] == b"PK":  # .xlsx files are zip archives
        try:
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as e:  # openpyxl raises several types for bad files
            raise HTTPException(400, f"Not a readable .xlsx file: {e}")
        return wb.worksheets[0].iter_rows(values_only=True)
    text = content.decode("utf-8-sig", errors="replace")
    first = text.split("\n", 1)[0]
    delimiter = ";" if first.count(";") > first.count(",") else ","
    return iter(list(csv.reader(io.StringIO(text), delimiter=delimiter)))


def _read_rows(content: bytes, columns: dict, required: str = "machine_no") -> list[tuple[int, dict]]:
    rows = _sheet_rows(content)
    try:
        headers = [_norm(h) for h in next(rows)]
    except StopIteration:
        return []
    lookup = {}
    for key, aliases in columns.items():
        for alias in aliases:
            n = _norm(alias)
            if n in headers:
                lookup[key] = headers.index(n)
                break
    if required not in lookup:
        raise HTTPException(400, f"The first row must have a '{required}' column")
    out = []
    for i, row in enumerate(rows, start=2):
        if row is None or all(v in (None, "") for v in row):
            continue
        out.append((i, {k: row[idx] if idx < len(row) else None for k, idx in lookup.items()}))
    return out


def _s(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def import_machines(db: Session, user: User, content: bytes) -> dict:
    created = updated = 0
    errors = []
    for row_no, row in _read_rows(content, MACHINE_COLUMNS):
        values = {k: _s(v) for k, v in row.items()}
        if values.get("name", "").startswith("[SAMPLE] Delete"):
            continue
        values["criticality"] = (values.get("criticality") or "B").upper()[:1]
        values["status"] = (values.get("status") or "running").lower()
        try:
            data = MachineIn(**{k: v for k, v in values.items() if v != "" or k in ("machine_no", "name")})
        except ValidationError as e:
            errors.append({"row": row_no, "error": "; ".join(f"{x['loc'][0]}: {x['msg']}" for x in e.errors())})
            continue
        existing = db.scalar(select(Machine).where(func.upper(Machine.machine_no) == data.machine_no))
        if existing:
            update = MachineUpdate(**data.model_dump(exclude={"machine_no"}, exclude_unset=True))
            machines_service.update_machine(db, user, existing, update)
            updated += 1
        else:
            machines_service.create_machine(db, user, data)
            created += 1
    audit.record(db, user, "import", "machines", "import", None, {"created": created, "updated": updated, "errors": len(errors)})
    return {"created": created, "updated": updated, "errors": errors}


def _parse_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _s(value)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(value) -> time | None:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, float) and 0 <= value < 1:  # Excel time as a day fraction
        minutes = round(value * 24 * 60)
        return time(minutes // 60 % 24, minutes % 60)
    m = re.match(r"^\s*(\d{1,2})[:.](\d{2})", _s(value))
    return time(int(m.group(1)), int(m.group(2))) if m else None


def import_logs(db: Session, user: User, content: bytes, mark_verified: bool) -> dict:
    tz = ZoneInfo(get_config().plant_tz)
    shifts = settings_store.get(db, "shifts")
    machines = {m.machine_no.upper(): m for m in db.scalars(select(Machine))}
    users_by_emp = {u.employee_id.upper(): u for u in db.scalars(select(User))}
    created = 0
    errors = []
    new_ids = []
    for row_no, row in _read_rows(content, LOG_COLUMNS):
        issue = _s(row.get("issue"))
        if issue.startswith("[SAMPLE] Delete"):
            continue
        machine = machines.get(_s(row.get("machine_no")).upper())
        if machine is None:
            errors.append({"row": row_no, "error": f"Unknown machine {row.get('machine_no')}"})
            continue
        day = _parse_date(row.get("date"))
        if day is None:
            errors.append({"row": row_no, "error": "Missing or unreadable date"})
            continue
        if not issue:
            errors.append({"row": row_no, "error": "Missing issue"})
            continue
        start_t, end_t = _parse_time(row.get("start_time")), _parse_time(row.get("end_time"))
        start = datetime.combine(day, start_t or time(0, 0), tz).astimezone(timezone.utc)
        end = None
        if end_t:
            end = datetime.combine(day, end_t, tz).astimezone(timezone.utc)
            if end < start:
                end += timedelta(days=1)  # ran past midnight
        downtime = downtime_minutes(start, end) if start_t and end else None
        if downtime is None and _s(row.get("downtime_min")):
            try:
                downtime = int(float(_s(row.get("downtime_min"))))
            except ValueError:
                pass
        tech_text = _s(row.get("technician"))
        tech = users_by_emp.get(tech_text.upper())
        shift, shift_date = shift_for(start, shifts, get_config().plant_tz) if start_t else ("", day)
        log = BreakdownLog(
            machine=machine,
            technician_id=tech.id if tech else None,
            technician_name=tech.name if tech else tech_text,
            zone=machine.zone,
            shift=_s(row.get("shift")) or shift,
            shift_date=shift_date,
            reported_at=start,
            start_at=start if start_t else None,
            end_at=end,
            downtime_min=downtime,
            alarm_code=_s(row.get("alarm_code")),
            status="verified" if mark_verified else "closed",
            verified_by=user.id if mark_verified else None,
            verified_at=utcnow() if mark_verified else None,
            source="import",
        )
        db.add(log)
        for field in ("issue", "root_cause", "corrective_action"):
            set_text(db, log, field, _s(row.get(field)))
        log.original_language = detect_lang(" ".join(t.original for t in log.texts))
        for part in [p.strip() for p in re.split(r"[;\n]", _s(row.get("parts_replaced"))) if p.strip()]:
            log.parts.append(LogPart(description=part, qty=1))
        db.flush()
        log.log_no = f"BL-{start.astimezone(tz).year}-{log.id:06d}"
        new_ids.append(log.id)
        created += 1
    for log_id in new_ids:
        jobs.enqueue(db, "enrich_log", log_id=log_id)
    audit.record(db, user, "import", "breakdown_logs", "import", None, {"created": created, "errors": len(errors), "verified": mark_verified})
    return {"created": created, "errors": errors}


def _styled(ws, headers: list[str]) -> None:
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
    ws.freeze_panes = "A2"


SAMPLE_ALARM = {
    "alarm_code": "A101",
    "message": "[SAMPLE] Delete this row",
    "cause": "",
    "remedy": "",
    "machine_no": "",
    "machine_type": "",
}


PART_COLUMNS = {
    "part_no": ("part_no", "part no", "part number", "material", "material no", "material number", "item code", "sap code"),
    "description": ("description", "material description", "part description", "part name"),
    "unit": ("unit", "uom", "base unit"),
    "stock_qty": ("stock_qty", "stock", "stock on hand", "on hand", "unrestricted", "qty", "quantity"),
    "min_qty": ("min_qty", "min stock", "minimum", "min", "reorder level", "safety stock"),
    "location": ("location", "storage bin", "bin", "store", "storage location"),
    "alt_part_nos": ("alt_part_nos", "manufacturer part no", "mfr part no", "oem part no", "make part no"),
    "machine_type": ("machine_type", "machine type", "fits type"),
    "machine_no": ("machine_no", "machine no", "fits machine"),
    "stock_at": ("stock_at", "stock date", "as of"),
}
SAMPLE_PART = {
    "part_no": "DEMO-PART-1",
    "description": "[SAMPLE] Delete this row",
    "unit": "EA",
    "stock_qty": 2,
    "min_qty": 1,
    "location": "Store A-12",
    "alt_part_nos": "",
    "machine_type": "Sand filling machine",
    "machine_no": "",
    "stock_at": "",
}
PM_COLUMNS = {
    "machine_no": MACHINE_COLUMNS["machine_no"],
    "task_code": ("task_code", "task code", "pm code", "maintenance plan", "plan no", "task no", "item"),
    "title": ("title", "task", "task description", "description", "activity"),
    "frequency_days": ("frequency_days", "frequency (days)", "frequency", "interval (days)", "interval", "cycle"),
    "last_done_on": ("last_done_on", "last done", "last date", "completed on", "last completed"),
    "next_due_on": ("next_due_on", "next due", "due date", "planned date", "next date"),
}
SAMPLE_PM = {
    "machine_no": "DEMO-XX-01",
    "task_code": "PM-001",
    "title": "[SAMPLE] Delete this row",
    "frequency_days": 30,
    "last_done_on": "2026-09-01",
    "next_due_on": "",
}


def _list(value) -> list[str]:
    return [x.strip() for x in re.split(r"[;,\n]", _s(value)) if x.strip()]


def _stamp(value) -> datetime | None:
    day = _parse_date(value)
    if day is None:
        return None
    tz = ZoneInfo(get_config().plant_tz)
    return datetime.combine(day, time(0, 0), tz).astimezone(timezone.utc)


def import_parts(db: Session, user: User, content: bytes) -> dict:
    rows = []
    for row_no, row in _read_rows(content, PART_COLUMNS, required="part_no"):
        values = {k: _s(v) for k, v in row.items()}
        values["alt_part_nos"] = _list(row.get("alt_part_nos"))
        values["machine_nos"] = _list(row.get("machine_no"))
        values["machine_types"] = _list(row.get("machine_type"))
        values["stock_at"] = _stamp(row.get("stock_at"))
        rows.append((row_no, values))
    return parts.upsert(db, user, rows, "import")


def import_pm(db: Session, user: User, content: bytes) -> dict:
    rows = [
        (row_no, {k: (v if k.endswith("_on") else _s(v)) for k, v in row.items()})  # dates may be Excel dates
        for row_no, row in _read_rows(content, PM_COLUMNS)
    ]
    return pm.upsert(db, user, rows, "import")


def template(kind: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    sample = {
        "machines": SAMPLE_MACHINE,
        "logs": SAMPLE_LOG,
        "alarms": SAMPLE_ALARM,
        "parts": SAMPLE_PART,
        "pm": SAMPLE_PM,
    }[kind]
    ws.title = kind
    _styled(ws, list(sample))
    ws.append(list(sample.values()))
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 22
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_logs(db: Session, *, since: date | None, until: date | None, zone: str = "", machine_no: str = "") -> bytes:
    tz = ZoneInfo(get_config().plant_tz)
    q = (
        select(BreakdownLog)
        .options(
            selectinload(BreakdownLog.texts),
            selectinload(BreakdownLog.parts),
            selectinload(BreakdownLog.machine),
            selectinload(BreakdownLog.technician),
            selectinload(BreakdownLog.verifier),
            selectinload(BreakdownLog.classification),
        )
        .order_by(BreakdownLog.reported_at)
    )
    if since:
        q = q.where(BreakdownLog.reported_at >= datetime.combine(since, time(0), tz))
    if until:
        q = q.where(BreakdownLog.reported_at < datetime.combine(until + timedelta(days=1), time(0), tz))
    if zone:
        q = q.where(BreakdownLog.zone == zone)
    if machine_no:
        q = q.join(Machine).where(func.upper(Machine.machine_no) == machine_no.upper())
    logs = db.scalars(q).all()

    def local(dt):
        return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M") if dt else ""

    wb = Workbook()
    ws = wb.active
    ws.title = "Logs"
    _styled(
        ws,
        [
            "Log no", "Machine no", "Machine", "Zone", "Line", "Shift", "Shift date", "Reported", "Start", "End",
            "Downtime (min)", "Alarm", "Issue (EN)", "Root cause (EN)", "Corrective action (EN)", "Issue (TA)",
            "Root cause (TA)", "Corrective action (TA)", "Issue (original)", "Root cause (original)",
            "Corrective action (original)", "Parts", "Symptom category", "Failure mode", "Technician",
            "Status", "Verified by", "Source", "Escalated",
        ],
    )
    for l in logs:
        c = l.classification
        ws.append(
            [
                l.log_no, l.machine.machine_no, l.machine.name, l.zone, l.machine.line, l.shift,
                l.shift_date.isoformat() if l.shift_date else "", local(l.reported_at), local(l.start_at),
                local(l.end_at), l.downtime_min, l.alarm_code,
                l.text("issue", "en"), l.text("root_cause", "en"), l.text("corrective_action", "en"),
                l.text("issue", "ta"), l.text("root_cause", "ta"), l.text("corrective_action", "ta"),
                l.original("issue"), l.original("root_cause"), l.original("corrective_action"),
                "; ".join(f"{p.description} {p.part_no} x{p.qty:g}".strip() for p in l.parts),
                c.symptom_category if c else "", c.failure_mode if c else "",
                l.technician.name if l.technician else l.technician_name, l.status,
                l.verifier.name if l.verifier else "", l.source, "yes" if l.escalated else "",
            ]
        )
    # KPI sheet: one row per machine that appears in the export (or all machines in the zone).
    ks = wb.create_sheet("KPIs by machine")
    # KPIs use a fixed window: the export dates, or the KPI period from settings.
    kpi_until = until or datetime.now(tz).date()
    kpi_since = since or kpi_until - timedelta(days=int(settings_store.get(db, "kpi_period_days")) - 1)
    period_days = (kpi_until - kpi_since).days + 1
    _styled(ks, ["Machine no", "Machine", "Zone", "Breakdowns", "Downtime (min)", "MTTR (min)", "MTBF (h)", "Period (days)"])
    mq = select(Machine).where(Machine.active.is_(True)).order_by(Machine.machine_no)
    if zone:
        mq = mq.where(Machine.zone == zone)
    if machine_no:
        mq = mq.where(func.upper(Machine.machine_no) == machine_no.upper())
    machines = db.scalars(mq).all()
    hours = float(settings_store.get(db, "planned_hours_per_day"))
    for m in machines:
        downs = [
            l.downtime_min
            for l in logs
            if l.machine_id == m.id
            and l.status in COUNTED_STATUSES
            and kpi_since <= l.reported_at.astimezone(tz).date() <= kpi_until
        ]
        k = compute(downs, max(period_days, 1), hours)
        ks.append([m.machine_no, m.name, m.zone, k.breakdowns, k.downtime_min, k.mttr_min, k.mtbf_h, k.period_days])
    for sheet in (ws, ks):
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = 18
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()



def export_dashboard(data: dict) -> bytes:
    """The dashboard's tables as an Excel workbook for the monthly MIS."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    _styled(ws, ["Measure", "Value"])
    t = data["totals"]
    k = data["knowledge"]
    a = data["ask_thunai"]
    for row in [
        ("Period (days)", data["days"]),
        ("Zone", data["zone"] or "All"),
        ("Machines", data["machines"]),
        ("Open breakdowns now", t["open_breakdowns"]),
        ("Breakdowns in period", t["breakdowns"]),
        ("Downtime (min)", t["downtime_min"]),
        ("MTTR (min)", t["mttr_min"]),
        ("Logs verified (%)", t["logs_verified_pct"]),
        ("Machines with a fault card", k["machines_covered"]),
        ("Machines without a fault card", len(k["machines_uncovered"])),
        ("Fault cards in use", k["cards_live"]),
        ("Draft cards waiting", k["cards_draft"]),
        ("Cards needing review", k["cards_needs_review"]),
        ("Approved expert tips", k["tips_approved"]),
        ("Ask Thunai sessions", a["sessions"]),
        ("Resolved", a["resolved"]),
        ("Escalated", a["escalated"]),
        ("Helpful / not helpful", f"{a['helpful']} / {a['not_helpful']}"),
        ("AI cost (USD)", a["cost_usd"]),
    ]:
        ws.append(list(row))
    for title, key in (("Downtime by zone", "downtime_by_zone"), ("Downtime by shift", "downtime_by_shift")):
        sheet = wb.create_sheet(title)
        _styled(sheet, ["Name", "Downtime (min)", "Breakdowns"])
        for r in data[key]:
            sheet.append([r["name"], r["downtime_min"], r["breakdowns"]])
    sheet = wb.create_sheet("Machines")
    _styled(sheet, ["Machine no", "Machine", "Zone", "Criticality", "Breakdowns", "Downtime (min)", "MTTR (min)", "MTBF (h)"])
    for r in data["machines_table"]:
        sheet.append([r["machine_no"], r["name"], r["zone"], r["criticality"], r["breakdowns"], r["downtime_min"], r["mttr_min"], r["mtbf_h"]])
    sheet = wb.create_sheet("Top faults")
    _styled(sheet, ["Symptom", "Times", "Machines", "Average downtime (min)", "Last seen"])
    for f in data["top_faults"]:
        sheet.append([f["symptom"], f["count"], ", ".join(f["machines"]), f["avg_downtime_min"], f["last"]])
    sheet = wb.create_sheet("Spare parts")
    _styled(sheet, ["Part no", "Description", "Times used", "Qty used", "Stock now", "Min stock", "Location", "Low"])
    for r in data["parts"]["used"]:
        st = r["stock"] or {}
        sheet.append([r["part_no"], r["description"], r["times"], r["qty"], st.get("stock_qty"), st.get("min_qty"), st.get("location", ""), "yes" if st.get("low") else ""])
    for p in data["parts"]["low_stock"]:
        if not any((r["part_no"] or "").upper() == p["part_no"].upper() for r in data["parts"]["used"]):
            sheet.append([p["part_no"], p["description"], 0, 0, p["stock_qty"], p["min_qty"], p["location"], "yes"])
    sheet = wb.create_sheet("PM overdue")
    _styled(sheet, ["Machine no", "Zone", "Task code", "Task", "Days overdue"])
    for r in data["pm"]["overdue"]:
        sheet.append([r["machine_no"], r["zone"], r["task_code"], r["title"], r["days_overdue"]])
    for s in wb.worksheets:
        for col in s.columns:
            s.column_dimensions[col[0].column_letter].width = 22
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_skills(data: dict) -> bytes:
    """Skill-gap tables (SPEC 12.7). Blank cells: fewer events than the minimum."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Technicians"
    _styled(ws, ["Technician", "Employee ID", "Zone", "Fixes", "Verified", "Median downtime (min)", "vs team median",
                 "Ask Thunai sessions", "Supervisor called", "Called (%)", "Can't do steps", "Authorised-only can't do",
                 "Approved tips", "Machine types fixed"])
    for t in data["technicians"]:
        ws.append([t["name"], t["employee_id"], t["zone"], t["fixes"], t["verified"], t["median_downtime_min"], t["vs_team"],
                   t["sessions"], t["escalated"], t["escalation_pct"], t["cant_do"], t["cant_do_authorised"], t["tips"],
                   ", ".join(t["machine_types"])])
    cov = wb.create_sheet("Coverage")
    _styled(cov, ["Technician", *data["types"]])
    for row in data["matrix"]:
        cov.append([row["name"], *[row["cells"].get(t, 0) or None for t in data["types"]]])
    mt = wb.create_sheet("Machine types")
    _styled(mt, ["Machine type", "Breakdowns", "People who fixed it", "Names", "Median downtime (min)", "Ask Thunai sessions", "Called (%)"])
    for r in data["machine_types"]:
        mt.append([r["name"], r["breakdowns"], r["fixers"], ", ".join(r["fixer_names"]), r["median_downtime_min"], r["sessions"], r["escalation_pct"]])
    sg = wb.create_sheet("Suggestions")
    _styled(sg, ["Kind", "Machine type", "Technician", "Partner", "Suggestion"])
    for g in data["suggestions"]:
        sg.append([g["kind"], g["machine_type"] or "", g["technician"] or "", g["partner"] or "", g["text_en"]])
    for s in wb.worksheets:
        for col in s.columns:
            s.column_dimensions[col[0].column_letter].width = 20
    sg.column_dimensions["E"].width = 90
    info = wb.create_sheet("About")
    info.append([f"Period: last {data['days']} days. Zone: {data['zone'] or 'All'}. Figures need at least {data['min_events']} events."])
    info.append(["For training and shift planning, not appraisal."])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
