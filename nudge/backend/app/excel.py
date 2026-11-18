"""Excel export of everything: open work, follow-ups, closed history and a basket summary."""
import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from . import recurrence
from .lanes import is_overdue, lane, waiting_days
from .models import Basket, Task
from .settings_store import Prefs
from .tasks_service import clock
from .timeutil import to_local, utcnow

HEADER_FILL = PatternFill("solid", fgColor="1D5FBF")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def _safe(value):
    """Text that starts like a formula is stored as text, so a task title can't run in Excel."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _sheet(wb: Workbook, title: str, headers: list[str], rows: list[list], first: bool = False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.append(headers)
    for cell in ws[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(vertical="center")
    for r in rows:
        ws.append([_safe(v) for v in r])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for i, h in enumerate(headers, start=1):
        width = max([len(str(h))] + [len(str(r[i - 1] or "")) for r in rows[:300]]) + 2
        ws.column_dimensions[get_column_letter(i)].width = min(60, max(10, width))
    return ws


def export(db: Session, prefs: Prefs, now: datetime | None = None) -> bytes:
    now = now or utcnow()
    c = clock(prefs, now)
    tasks = db.query(Task).order_by(Task.created_at).all()

    def local(dt):
        return to_local(dt, prefs.zone).strftime("%Y-%m-%d %H:%M") if dt else ""

    lane_names = {"inbox": "Inbox", "today": "Today", "upcoming": "Upcoming", "waiting": "Waiting",
                  "overdue": "Overdue", "done": "Done"}
    open_rows = [[
        t.title, t.basket.name if t.basket else "", lane_names[lane(t, c)], t.priority.title(),
        t.due_date.isoformat() if t.due_date else "", t.due_time.strftime("%H:%M") if t.due_time else "",
        t.person, recurrence.label(t.repeat_rule), "Yes" if is_overdue(t, c) else "",
        (now - t.created_at).days, local(t.created_at), t.notes,
    ] for t in tasks if t.status == "open"]
    waiting_rows = [[
        t.title, t.person, t.basket.name if t.basket else "", waiting_days(t, now), t.nudge_count,
        local(t.next_nudge_at), t.due_date.isoformat() if t.due_date else "", t.notes,
    ] for t in tasks if t.status == "waiting"]
    closed_rows = [[
        t.title, t.basket.name if t.basket else "", "Done" if t.status == "done" else "Dropped", t.person,
        local(t.created_at), local(t.closed_at), (t.closed_at - t.created_at).days if t.closed_at else "",
        t.closing_note,
    ] for t in sorted([t for t in tasks if t.status in ("done", "dropped")],
                      key=lambda t: t.closed_at or t.created_at, reverse=True)]

    summary = []
    for b in db.query(Basket).order_by(Basket.position).all():
        mine = [t for t in tasks if t.basket_id == b.id]
        summary.append([
            b.name, sum(1 for t in mine if t.status == "open"), sum(1 for t in mine if t.status == "waiting"),
            sum(1 for t in mine if is_overdue(t, c)), sum(1 for t in mine if t.status == "done"),
        ])

    wb = Workbook()
    _sheet(wb, "Open tasks", ["Title", "Basket", "List", "Priority", "Due date", "Due time", "Person", "Repeats",
                              "Overdue", "Days open", "Created", "Notes"], open_rows, first=True)
    _sheet(wb, "Waiting on others", ["Title", "Person", "Basket", "Days waiting", "Times nudged", "Next nudge",
                                     "Due date", "Notes"], waiting_rows)
    _sheet(wb, "Closed", ["Title", "Basket", "Outcome", "Person", "Created", "Closed", "Days to close",
                          "Closing note"], closed_rows)
    _sheet(wb, "Baskets", ["Basket", "Open", "Waiting", "Overdue", "Done (all time)"], summary)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
