from datetime import datetime, timedelta, timezone

from app import kpi
from app.settings_store import DEFAULTS
from app.shifts import downtime_minutes, shift_for

IST = timezone(timedelta(hours=5, minutes=30))
SHIFTS = DEFAULTS["shifts"]


def at(day: int, hh: int, mm: int = 0) -> datetime:
    return datetime(2026, 10, day, hh, mm, tzinfo=IST)


def test_day_shifts():
    assert shift_for(at(10, 6, 0), SHIFTS, "Asia/Kolkata") == ("A", at(10, 0).date())
    assert shift_for(at(10, 13, 59), SHIFTS, "Asia/Kolkata")[0] == "A"
    assert shift_for(at(10, 14, 0), SHIFTS, "Asia/Kolkata")[0] == "B"
    assert shift_for(at(10, 21, 59), SHIFTS, "Asia/Kolkata")[0] == "B"


def test_overnight_shift_belongs_to_previous_day_after_midnight():
    assert shift_for(at(10, 22, 0), SHIFTS, "Asia/Kolkata") == ("C", at(10, 0).date())
    assert shift_for(at(11, 0, 30), SHIFTS, "Asia/Kolkata") == ("C", at(10, 0).date())
    assert shift_for(at(11, 5, 59), SHIFTS, "Asia/Kolkata") == ("C", at(10, 0).date())


def test_shift_uses_plant_time_for_utc_input():
    utc_moment = datetime(2026, 10, 10, 17, 0, tzinfo=timezone.utc)  # 22:30 IST
    assert shift_for(utc_moment, SHIFTS, "Asia/Kolkata") == ("C", at(10, 0).date())


def test_gap_in_calendar_returns_no_shift():
    two_shifts = [{"name": "A", "start": "06:00", "end": "14:00"}, {"name": "B", "start": "14:00", "end": "22:00"}]
    assert shift_for(at(10, 23), two_shifts, "Asia/Kolkata")[0] == ""


def test_downtime_minutes():
    assert downtime_minutes(at(10, 22, 30), at(11, 0, 10)) == 100
    assert downtime_minutes(at(10, 9), None) is None
    assert downtime_minutes(at(10, 9), at(10, 8)) is None  # end before start is rejected


def test_mttr_mtbf():
    k = kpi.compute([35, 40, 25, 30], period_days=90, planned_hours_per_day=24)
    assert k.breakdowns == 4
    assert k.downtime_min == 130
    assert k.mttr_min == 32.5
    # (2160 h - 130/60 h) / 4 = 539.46
    assert k.mtbf_h == 539.5


def test_kpi_ignores_missing_downtime_for_mttr_but_counts_breakdown():
    k = kpi.compute([60, None], period_days=30, planned_hours_per_day=22.5)
    assert k.breakdowns == 2
    assert k.mttr_min == 60
    assert k.mtbf_h == round((30 * 22.5 - 1) / 2, 1)


def test_kpi_with_no_breakdowns():
    k = kpi.compute([], period_days=30, planned_hours_per_day=24)
    assert k.breakdowns == 0 and k.mttr_min is None and k.mtbf_h is None
