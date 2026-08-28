"""
pm_core.py - Shared domain model + the PM scheduling engine.

This is the single source of truth for the 4000-standard-hour scheduling rule.
The same logic is re-implemented in Power Query / DAX (see docs/03-pm-scheduling-engine.md)
and in Power Automate (see docs/05-power-automate-flows.md). If you change the rule,
change it in all three places.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

SEED = 42

# ---------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------

def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def add_months(d: date, n: int) -> date:
    total = (d.year * 12 + (d.month - 1)) + n
    return date(total // 12, total % 12 + 1, 1)


def month_range(start: date, end: date) -> list[date]:
    out, cur = [], month_start(start.year, start.month)
    last = month_start(end.year, end.month)
    while cur <= last:
        out.append(cur)
        cur = add_months(cur, 1)
    return out


def months_between(a: date, b: date) -> int:
    """Whole months from a to b (b later => positive)."""
    return (b.year * 12 + b.month) - (a.year * 12 + a.month)


def working_days(y: int, m: int, holidays: set[date]) -> list[date]:
    d, out = month_start(y, m), []
    end = month_end(y, m)
    while d <= end:
        if d.weekday() < 5 and d not in holidays:
            out.append(d)
        d += timedelta(days=1)
    return out


# ---------------------------------------------------------------------------
# Domain records
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    cell_id: str
    cell_name: str
    area: str
    plant: str
    criticality: str
    pm_interval_std_hrs: int
    calendar_backstop_months: int
    baseline_monthly_std_hrs: int
    cost_center: str
    active: str = "Yes"


@dataclass
class Machine:
    machine_id: str
    machine_name: str
    cell_id: str
    machine_type: str
    make: str
    model: str
    serial_no: str
    install_date: date
    criticality: str
    location: str
    checklist_id: str
    pm_std_minutes: int
    active: str = "Yes"


@dataclass
class Technician:
    tech_id: str
    tech_name: str
    email: str
    shift: str
    skill_group: str
    primary_area: str
    daily_capacity_min: int
    active: str = "Yes"


@dataclass
class WorkOrder:
    wo_id: str
    cycle_id: str
    cell_id: str
    machine_id: str
    pm_type: str
    trigger_type: str
    trigger_std_hrs: float
    plan_month: str
    planned_date: date
    due_date: date
    assigned_tech_id: str
    status: str
    actual_start: date | None = None
    actual_end: date | None = None
    duration_min: int | None = None
    checklist_total: int = 0
    checklist_done: int = 0
    checklist_fail: int = 0
    machine_qr_scanned: str = "No"
    result: str = ""
    remarks: str = ""


# ---------------------------------------------------------------------------
# THE SCHEDULING ENGINE
# ---------------------------------------------------------------------------
#
# Rule (as agreed):
#   * Standard hours accrue at CELL level from the monthly Excel upload.
#   * A cell's counter starts at the carry-over left after its previous PM.
#   * When the running counter reaches PM_Interval_Std_Hrs (default 4000), the
#     WHOLE cell is scheduled: one work order per active machine in the cell.
#   * Carry-over after the PM = counter - interval (never negative).
#   * Calendar backstop: if a cell has gone Calendar_Backstop_Months without a
#     PM it is scheduled anyway, whatever the counter says. Counter resets to
#     max(0, counter - interval), which is 0 for a calendar-triggered PM.
#
# Forecasting for future months uses the trailing 3-month average of uploaded
# standard hours as the run-rate.
# ---------------------------------------------------------------------------

@dataclass
class CycleTrigger:
    cell_id: str
    cycle_no: int
    plan_month: str
    trigger_type: str          # "Std Hours" | "Calendar Backstop"
    counter_at_trigger: float
    carry_over_after: float
    is_forecast: bool


def run_pm_engine(
    cell: Cell,
    std_hours_by_month: dict[str, float],
    horizon_months: list[date],
    last_pm_before_horizon: date | None = None,
    opening_carry_over: float = 0.0,
) -> list[CycleTrigger]:
    """Walk month by month and emit a trigger every time the cell falls due."""
    counter = float(opening_carry_over)
    last_pm_month = (
        month_start(last_pm_before_horizon.year, last_pm_before_horizon.month)
        if last_pm_before_horizon
        else month_start(horizon_months[0].year, horizon_months[0].month)
    )
    triggers: list[CycleTrigger] = []
    cycle_no = 0

    for m in horizon_months:
        mk = month_key(m)
        counter += float(std_hours_by_month.get(mk, 0.0))

        hours_due = counter >= cell.pm_interval_std_hrs
        calendar_due = months_between(last_pm_month, m) >= cell.calendar_backstop_months

        if hours_due or calendar_due:
            cycle_no += 1
            carry = max(0.0, counter - cell.pm_interval_std_hrs)
            triggers.append(
                CycleTrigger(
                    cell_id=cell.cell_id,
                    cycle_no=cycle_no,
                    plan_month=mk,
                    # Hours wins the label when both fire on the same month.
                    trigger_type="Std Hours" if hours_due else "Calendar Backstop",
                    counter_at_trigger=round(counter, 1),
                    carry_over_after=round(carry, 1),
                    is_forecast=False,
                )
            )
            counter = carry
            last_pm_month = m

    return triggers


def forecast_run_rate(std_hours_by_month: dict[str, float], upto: date, window: int = 3) -> float:
    """Trailing-N-month average standard hours, used to project future PM months."""
    keys = []
    cur = month_start(upto.year, upto.month)
    for _ in range(window):
        keys.append(month_key(cur))
        cur = add_months(cur, -1)
    vals = [std_hours_by_month.get(k, 0.0) for k in keys]
    vals = [v for v in vals if v > 0]
    return sum(vals) / len(vals) if vals else 0.0
