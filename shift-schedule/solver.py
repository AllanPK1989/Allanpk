"""Supervisor shift roster solver, Mon 28 Sep - Sat 31 Oct 2026 (CP-SAT).

People
  M   main supervisor: general shift Mon-Fri, off Sat+Sun; counts as 1st-shift cover.
  T1  tooling supervisor  } never on the same shift as each other
  T2  tooling supervisor  }
  E   electrical supervisor (may share a shift with either tooling supervisor)

Rules for T1/T2/E
  * two consecutive days off a week (5 off blocks in 28 Sep - 31 Oct);
  * 3-6 working days between two off blocks (never more than 6 in a row);
  * shift switches (1st <-> 2nd) on the first day back after the days off.

Cover
  * Mon-Fri: at least one on 2nd shift (M covers 1st);
  * Sat: at least one on 1st and one on 2nd;
  * Sun: at least one supervisor (maintenance only).

Two variants are solved: FIXED (same off days every week) and ROTATING (off
days move; each off block falls after 3-6 working days, not on a fixed weekday,
which is what lets Sunday duty rotate with one supervisor per Sunday).
"""
import datetime as dt

from ortools.sat.python import cp_model

START = dt.date(2026, 9, 28)          # Monday; 24-27 Sep stay as current roster
END = dt.date(2026, 10, 31)           # Saturday
NDAYS = (END - START).days + 1        # 34 days that must be covered
HORIZON = NDAYS + 2                   # model runs to Mon 2 Nov so offs can spill over
WEEKS = (NDAYS + 6) // 7
PEOPLE = ["T1", "T2", "E"]
MIN_RUN, MAX_RUN = 3, 6


def date(d):
    return START + dt.timedelta(days=d)


def solve(fixed, time_limit=60):
    m = cp_model.CpModel()
    D = range(HORIZON)
    start = {(p, d): m.NewBoolVar(f"start_{p}_{d}") for p in PEOPLE for d in D}
    off = {(p, d): m.NewBoolVar(f"off_{p}_{d}") for p in PEOPLE for d in D}
    sec = {(p, d): m.NewBoolVar(f"second_{p}_{d}") for p in PEOPLE for d in D}
    w1 = {(p, d): m.NewBoolVar(f"on1_{p}_{d}") for p in PEOPLE for d in D}
    w2 = {(p, d): m.NewBoolVar(f"on2_{p}_{d}") for p in PEOPLE for d in D}

    for p in PEOPLE:
        for d in D:
            prev = start[p, d - 1] if d > 0 else 0
            # off today <=> a block starts today or started yesterday
            m.Add(off[p, d] == start[p, d] + prev)
            # working split by shift
            m.AddBoolAnd([off[p, d].Not(), sec[p, d].Not()]).OnlyEnforceIf(w1[p, d])
            m.AddBoolAnd([off[p, d].Not(), sec[p, d]]).OnlyEnforceIf(w2[p, d])
            m.Add(w1[p, d] + w2[p, d] + off[p, d] == 1)
            # shift flips exactly on the day back from a 2-day off
            if d >= 1:
                back = start[p, d - 2] if d >= 2 else None
                if back is None:
                    m.Add(sec[p, d] == sec[p, d - 1])
                else:
                    m.Add(sec[p, d] != sec[p, d - 1]).OnlyEnforceIf(back)
                    m.Add(sec[p, d] == sec[p, d - 1]).OnlyEnforceIf(back.Not())
            # MIN_RUN..MAX_RUN working days between off blocks
            for g in range(d + 1, min(d + 2 + MIN_RUN, HORIZON)):
                m.AddImplication(start[p, d], start[p, g].Not())
            nxt = [start[p, g] for g in range(d + 2 + MIN_RUN, d + 3 + MAX_RUN)
                   if g < HORIZON]
            # enforced up to Sun 1 Nov so nobody runs past 6 days at month end
            if d + 2 + MAX_RUN < HORIZON - 1:
                m.AddBoolOr(nxt).OnlyEnforceIf(start[p, d])
        # the week before 28 Sep is unknown: first off block by Sun 4 Oct so
        # nobody works more than 6 days from the new start
        m.AddBoolOr([start[p, d] for d in range(MAX_RUN + 1)])
        m.Add(sum(start[p, d] for d in range(7 * WEEKS, HORIZON)) == 0)
        if fixed:
            # one off block in each calendar week, same weekday every week
            for k in range(WEEKS):
                m.Add(sum(start[p, d] for d in range(7 * k, min(7 * k + 7, HORIZON))) == 1)
            for d in range(HORIZON - 7):
                m.Add(start[p, d] == start[p, d + 7])
        else:
            # 2 days off a week: exactly 5 off blocks starting 28 Sep - 31 Oct
            m.Add(sum(start[p, d] for d in range(NDAYS)) == WEEKS)

    for d in range(NDAYS):
        wd = date(d).weekday()
        # tooling supervisors never on the same shift
        m.Add(w1["T1", d] + w1["T2", d] <= 1)
        m.Add(w2["T1", d] + w2["T2", d] <= 1)
        if wd < 5:
            m.AddBoolOr([w2[p, d] for p in PEOPLE])
        elif wd == 5:
            m.AddBoolOr([w1[p, d] for p in PEOPLE])
            m.AddBoolOr([w2[p, d] for p in PEOPLE])
        else:
            m.AddBoolOr([off[p, d].Not() for p in PEOPLE])

    sundays = [d for d in range(NDAYS) if date(d).weekday() == 6]
    saturdays = [d for d in range(NDAYS) if date(d).weekday() == 5]
    sun_off = {p: sum(off[p, d] for d in sundays) for p in PEOPLE}
    # fewest people tied up on Sundays, then Sunday offs spread evenly
    lo = m.NewIntVar(0, len(sundays), "min_sunday_offs")
    for p in PEOPLE:
        m.Add(lo <= sun_off[p])
    total_sun_off = sum(sun_off.values())
    obj = 1000 * lo + 100 * total_sun_off
    if not fixed:
        # everyone gets at least one full Sat+Sun weekend off inside the period
        for p in PEOPLE:
            m.AddBoolOr([start[p, d] for d in saturdays if d + 1 < NDAYS])
        # prefer shorter stretches: penalise each full MAX_RUN-day run
        for p in PEOPLE:
            for d in range(NDAYS - MAX_RUN + 1):
                full = m.NewBoolVar("")
                m.AddBoolOr([off[p, g] for g in range(d, d + MAX_RUN)] + [full])
                obj -= 5 * full
        # off days should actually move: penalise same weekday as last week
        same = []
        for p in PEOPLE:
            for d in range(HORIZON - 7):
                s = m.NewBoolVar("")
                m.AddBoolAnd([start[p, d], start[p, d + 7]]).OnlyEnforceIf(s)
                m.AddBoolOr([start[p, d].Not(), start[p, d + 7].Not()]).OnlyEnforceIf(s.Not())
                same.append(s)
        obj -= 10 * sum(same)
    m.Maximize(obj)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 1  # deterministic: same roster every rebuild
    st = solver.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    roster = {}
    for p in PEOPLE:
        row = []
        for d in range(NDAYS):
            if solver.Value(off[p, d]):
                row.append("OFF")
            else:
                row.append(2 if solver.Value(sec[p, d]) else 1)
        roster[p] = row
    return roster, solver.StatusName(st)


def verify(r):
    """Independent re-check of every rule on a finished roster."""
    errs = []
    for d in range(NDAYS):
        wd = date(d).weekday()
        t1, t2 = r["T1"][d], r["T2"][d]
        on = [r[p][d] for p in PEOPLE if r[p][d] != "OFF"]
        if t1 != "OFF" and t1 == t2:
            errs.append(f"{date(d)} tooling overlap")
        if wd < 5 and 2 not in on:
            errs.append(f"{date(d)} no 2nd shift")
        if wd == 5 and not (1 in on and 2 in on):
            errs.append(f"{date(d)} Saturday gap")
        if wd == 6 and not on:
            errs.append(f"{date(d)} Sunday empty")
    for p in PEOPLE:
        row, prev, back = r[p], None, False
        for d, v in enumerate(row):
            if v == "OFF":
                back = True
                continue
            if prev is not None and back and v == prev:
                errs.append(f"{p} {date(d)} no switch after off")
            if prev is not None and not back and v != prev:
                errs.append(f"{p} {date(d)} switch without off")
            prev, back = v, False
        pattern = "".join("o" if v == "OFF" else "w" for v in row)
        offs = pattern.replace("w", " ").split()
        # a single OFF on the last day is a block running into 1 Nov
        if any(len(x) != 2 for x in offs[:-1]) or (offs and len(offs[-1]) != 2
                                                    and not pattern.endswith("wo")):
            errs.append(f"{p} off block not 2 days")
        if any(len(x) > MAX_RUN for x in pattern.split("o")):
            errs.append(f"{p} more than {MAX_RUN} days in a row")
    return errs


if __name__ == "__main__":
    for fixed in (True, False):
        res = solve(fixed)
        name = "FIXED" if fixed else "ROTATING"
        if res is None:
            print(name, "infeasible")
            continue
        r, status = res
        print(name, status, "errors:", verify(r))
        for d in range(NDAYS):
            print(date(d).strftime("%a %d %b"), *(f"{r[p][d]!s:>3}" for p in PEOPLE))
