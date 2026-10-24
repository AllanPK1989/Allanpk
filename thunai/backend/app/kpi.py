"""MTTR and MTBF. Formulas are SAMPLE until the plant confirms them (SPEC.md open question 1).

MTTR (minutes) = total downtime / number of breakdowns that have a recorded downtime
MTBF (hours)   = (planned hours in period - downtime hours) / number of breakdowns
planned hours  = period days x planned_hours_per_day
"""
from dataclasses import asdict, dataclass

COUNTED_STATUSES = ("closed", "verified")


@dataclass
class KPI:
    breakdowns: int
    downtime_min: int
    mttr_min: float | None
    mtbf_h: float | None
    period_days: int
    planned_hours: float

    def as_dict(self) -> dict:
        return asdict(self)


def compute(downtimes: list[int | None], period_days: int, planned_hours_per_day: float) -> KPI:
    """downtimes: one entry per counted breakdown (None when no downtime was recorded)."""
    breakdowns = len(downtimes)
    recorded = [d for d in downtimes if d is not None and d >= 0]
    total_min = sum(recorded)
    planned_hours = period_days * planned_hours_per_day
    mttr = round(total_min / len(recorded), 1) if recorded else None
    mtbf = None
    if breakdowns:
        mtbf = round(max(planned_hours - total_min / 60, 0) / breakdowns, 1)
    return KPI(breakdowns, total_min, mttr, mtbf, period_days, planned_hours)
