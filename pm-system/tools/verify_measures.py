"""
verify_measures.py
------------------
Recomputes every headline measure from the prepared CSVs, in plain Python,
independently of the DAX.

The point is not to test Python. It is to have a second, independently written
answer for each measure so that "the measure compiles" can be upgraded to "the
measure returns the right number". A measure nobody has checked against a known
answer is a number, not a fact.

Three calculations get a full hand-worked example printed, because they are the
ones the whole system's credibility rests on and the ones most likely to be
quietly wrong:

  * Breakdowns After PM (7d) - is the PM actually working
  * Projected PM Date        - when will this cell hit its trigger
  * Mid-month proration      - how many of this month's hours belong to the new
                               counter after a reset

Usage:
    python tools/verify_measures.py
    python tools/verify_measures.py --asof 2026-08-30   # pin "today"
    python tools/verify_measures.py --json out.json
"""

import argparse
import csv
import datetime as dt
import json
import os
import statistics
from collections import Counter, defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sharepoint", "data")
DATA = os.path.normpath(DATA)

RESULTS = []


def load(name):
    with open(os.path.join(DATA, f"{name}.csv"), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def num(v, default=None):
    if v is None or str(v).strip() == "":
        return default
    try:
        return float(v)
    except ValueError:
        return default


def date(v):
    if not v:
        return None
    return dt.date.fromisoformat(str(v)[:10])


def dtm(v):
    if not v:
        return None
    s = str(v)
    return dt.datetime.fromisoformat(s) if "T" in s else dt.datetime.fromisoformat(s + "T00:00:00")


def yes(v):
    return str(v).strip().lower() in ("yes", "true", "1")


def record(folder, name, value, unit="", note=""):
    RESULTS.append({"folder": folder, "measure": name, "value": value,
                    "unit": unit, "note": note})


def fmt(v):
    if v is None:
        return "(blank)"
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:,.0f}"
    return f"{v:,}" if isinstance(v, int) else str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None, help="treat this date as TODAY (yyyy-mm-dd)")
    ap.add_argument("--json", default=None, help="also write results as JSON")
    args = ap.parse_args()

    today = date(args.asof) if args.asof else dt.date.today()

    cells = load("Cell_Master")
    machines = load("Machine_Master")
    checks = load("Checklist_Master")
    techs = load("Technician_Master")
    spares = load("Spare_Master")
    std = load("StdHours_Monthly")
    wos = load("PM_WorkOrder")
    tasks = load("PM_Machine_Task")
    resp = load("Checklist_Response")
    scans = load("Scan_Log")
    bds = load("Breakdown_Log")
    sreq = load("Spare_Request")
    srep = load("Spare_Replaced")
    abns = load("Abnormality_Log")
    plan = load("PM_Plan_Calendar")

    print("=" * 78)
    print(f"  Measure verification against dummy data   (TODAY = {today})")
    print("=" * 78)

    # ---------------------------------------------------------------- 01
    due = [w for w in wos if w["WO_Status"] != "Cancelled"]
    completed = [w for w in wos if w["WO_Status"] == "Completed"]
    overdue = [w for w in wos
               if w["WO_Status"] not in ("Completed", "Cancelled")
               and date(w["Planned_End_Date"]) and date(w["Planned_End_Date"]) < today]
    inprog = [w for w in wos if w["WO_Status"] == "In Progress"]
    ontime = [w for w in completed
              if date(w["Actual_End_Date"]) and date(w["Planned_End_Date"])
              and date(w["Actual_End_Date"]) <= date(w["Planned_End_Date"])]

    record("01 PM Compliance", "PM Due Count", len(due))
    record("01 PM Compliance", "PM Completed Count", len(completed))
    record("01 PM Compliance", "PM Overdue Count", len(overdue))
    record("01 PM Compliance", "PM In Progress Count", len(inprog))
    record("01 PM Compliance", "PM Compliance %", len(completed) / len(due) if due else None, "%")
    record("01 PM Compliance", "PM On-Time Count", len(ontime))
    record("01 PM Compliance", "PM On-Time %", len(ontime) / len(completed) if completed else None, "%")

    committed = [p for p in plan
                 if "Forecast" not in (p["Plan_Version"] or "")
                 and p["Adherence_Status"] != "Forecast"]
    adh_ontime = [p for p in committed if p["Adherence_Status"] == "On Time"]
    record("01 PM Compliance", "Schedule Adherence %",
           len(adh_ontime) / len(committed) if committed else None, "%",
           f"{len(adh_ontime)} on time of {len(committed)} committed plan rows "
           f"({len(plan) - len(committed)} forecast rows excluded)")

    delays = [(date(w["Actual_End_Date"]) - date(w["Planned_End_Date"])).days
              for w in completed if date(w["Actual_End_Date"]) and date(w["Planned_End_Date"])]
    record("01 PM Compliance", "Avg PM Delay (Days)",
           statistics.fmean(delays) if delays else None, "days")
    cal_trig = [w for w in due if w["Trigger_Type"] == "Calendar Backstop"]
    record("01 PM Compliance", "Calendar-Triggered PM %",
           len(cal_trig) / len(due) if due else None, "%",
           "high share means the 4,000 h rule is set too high for actual utilisation")

    # ---------------------------------------------------------------- 02
    cum = sum(num(c["Cum_Std_Hours_Since_PM"], 0) for c in cells)
    trig = sum(num(c["PM_Trigger_Hours"], 0) for c in cells)
    record("02 Hours & Forecast", "Cum Std Hours", cum, "h")
    record("02 Hours & Forecast", "PM Trigger Hours", trig, "h")
    record("02 Hours & Forecast", "Hours to Next PM", max(trig - cum, 0), "h")
    record("02 Hours & Forecast", "Hours Utilisation %", cum / trig if trig else None, "%")

    months = sorted({s["Upload_Month"] for s in std})
    l3m = months[-3:]
    l3_rows = [s for s in std if s["Upload_Month"] in l3m]
    l3_total = sum(num(s["Actual_Std_Hours"], 0) for s in l3_rows)
    record("02 Hours & Forecast", "Avg Monthly Std Hours L3M (all cells)",
           l3_total / len(l3m), "h/month", f"window {l3m[0]} .. {l3m[-1]}")

    per_cell_l3m = {}
    for c in cells:
        rows = [s for s in l3_rows if s["Cell_ID"] == c["Cell_ID"]]
        per_cell_l3m[c["Cell_ID"]] = (sum(num(s["Actual_Std_Hours"], 0) for s in rows) / len(l3m)
                                      if rows else None)

    record("02 Hours & Forecast", "Total Std Hours", sum(num(s["Actual_Std_Hours"], 0) for s in std), "h")
    record("02 Hours & Forecast", "Production Qty", sum(num(s["Production_Qty"], 0) for s in std))

    active_cells = [c for c in cells if yes(c["Active"])]
    due_soon = [c for c in active_cells
                if num(c["PM_Trigger_Hours"], 0) > 0
                and num(c["Cum_Std_Hours_Since_PM"], 0) / num(c["PM_Trigger_Hours"]) >= 0.9]
    over = [c for c in active_cells
            if (num(c["PM_Trigger_Hours"], 0) > 0
                and num(c["Cum_Std_Hours_Since_PM"], 0) >= num(c["PM_Trigger_Hours"]))
            or (date(c["Next_PM_Due_Date_Calendar"]) and date(c["Next_PM_Due_Date_Calendar"]) <= today)]
    record("02 Hours & Forecast", "Cells Due Soon Count", len(due_soon), "cells",
           ", ".join(c["Cell_ID"] for c in due_soon) or "none")
    record("02 Hours & Forecast", "Overdue Cells Count", len(over), "cells",
           ", ".join(c["Cell_ID"] for c in over) or "none")

    # ---------------------------------------------------------------- 03
    t_completed = [t for t in tasks if t["Task_Status"] == "Completed"]
    t_pending = [t for t in tasks if t["Task_Status"] in ("Pending", "In Progress")]
    record("03 Execution", "Machine Tasks Total", len(tasks))
    record("03 Execution", "Machine Tasks Completed", len(t_completed))
    record("03 Execution", "Machine Tasks Pending", len(t_pending))
    record("03 Execution", "Cell Completion %", len(t_completed) / len(tasks) if tasks else None, "%")

    durs = [num(t["Duration_Min"]) for t in t_completed
            if num(t["Duration_Min"]) and num(t["Duration_Min"]) > 0]
    record("03 Execution", "Avg PM Duration (Hrs)",
           statistics.fmean(durs) / 60 if durs else None, "h")
    record("03 Execution", "Total PM Man-Hours",
           sum(num(t["Duration_Min"], 0) for t in tasks) / 60, "h")

    notok_by_wo = defaultdict(int)
    for t in tasks:
        notok_by_wo[t["WO_No"]] += int(num(t["NOT_OK_Count"], 0))
    clean = [w for w in completed if notok_by_wo.get(w["WO_No"], 0) == 0]
    record("03 Execution", "First-Pass PM %",
           len(clean) / len(completed) if completed else None, "%",
           f"{len(clean)} of {len(completed)} completed work orders had zero findings")

    exp_by_checklist = defaultdict(int)
    for c in checks:
        if yes(c["Active"]):
            exp_by_checklist[c["Checklist_ID"]] += int(num(c["Expected_Time_Min"], 0))
    checklist_of = {m["Machine_ID"]: m["Checklist_ID"] for m in machines}
    expected_total = sum(exp_by_checklist.get(checklist_of.get(t["Machine_ID"], ""), 0) for t in tasks)
    actual_total = sum(num(t["Duration_Min"], 0) for t in tasks)
    record("03 Execution", "Expected PM Duration (Min)", expected_total, "min")
    record("03 Execution", "PM Duration vs Expected %",
           actual_total / expected_total if expected_total else None, "%",
           "well below 1.0 across the board would mean checklists are being signed, not done")
    record("03 Execution", "Machines Not Scanned",
           len([t for t in tasks if t["Task_Status"] == "Pending" and not t["Scan_Start_Time"]]))
    open_wos = [w for w in wos if w["WO_Status"] in ("Planned", "In Progress", "Overdue")]
    ages = [(today - date(w["WO_Created_Date"])).days for w in open_wos if date(w["WO_Created_Date"])]
    record("03 Execution", "Open WO Ageing (Days)", statistics.fmean(ages) if ages else None, "days")
    record("03 Execution", "Reset Not Applied Count",
           len([w for w in completed if not yes(w["Reset_Applied"])]), "",
           "must be 0 - integrity rule 3 says the reset quartet moves together")

    # ---------------------------------------------------------------- 04
    checked = [r for r in resp if r["Result"] in ("OK", "NOT OK")]
    notok = [r for r in resp if r["Result"] == "NOT OK"]
    record("04 Quality of PM", "Checklist Items Checked", len(checked))
    record("04 Quality of PM", "NOT OK Count", len(notok))
    record("04 Quality of PM", "NOT OK %", len(notok) / len(checked) if checked else None, "%")

    safety = {(c["Checklist_ID"], c["Item_No"]) for c in checks if yes(c["Safety_Critical"])}
    sc_notok = [r for r in notok if (r["Checklist_ID"], r["Item_No"]) in safety]
    record("04 Quality of PM", "Safety-Critical NOT OK Count", len(sc_notok), "",
           "a non-zero value is an event, not a trend")
    record("04 Quality of PM", "Follow-Up Raised Count",
           len([r for r in resp if yes(r["Follow_Up_Required"])]))

    open_abn = [a for a in abns if a["Status"] != "Closed"]
    record("04 Quality of PM", "Open Abnormalities", len(open_abn))
    record("04 Quality of PM", "High Severity Open",
           len([a for a in open_abn if a["Severity"] == "High"]))
    ages_a = []
    for a in abns:
        lg = dtm(a["Logged_DateTime"])
        if not lg:
            continue
        cl = date(a["Closed_Date"])
        ages_a.append(((cl or today) - lg.date()).days)
    record("04 Quality of PM", "Abnormality Ageing (Days)",
           statistics.fmean(ages_a) if ages_a else None, "days")
    record("04 Quality of PM", "Overdue Abnormalities",
           len([a for a in abns if a["Status"] != "Closed" and date(a["Target_Date"])
                and date(a["Target_Date"]) < today]))

    # Repeat Finding Count - same check point NOT OK on the same machine in two
    # ADJACENT PM cycles. Cycle order comes from the machine task completion date.
    cycles = defaultdict(list)
    for t in tasks:
        if date(t["Completion_Date"]):
            cycles[t["Machine_ID"]].append((date(t["Completion_Date"]), t["WO_No"]))
    seq = {}
    for mid, lst in cycles.items():
        for i, (_, wo) in enumerate(sorted(lst), start=1):
            seq[(mid, wo)] = i
    notok_seq = set()
    for r in notok:
        s = seq.get((r["Machine_ID"], r["WO_No"]))
        if s:
            notok_seq.add((r["Machine_ID"], r["Check_Point"], s))
    repeats = [(m, c, s) for (m, c, s) in notok_seq if (m, c, s - 1) in notok_seq]
    record("04 Quality of PM", "Repeat Finding Count", len(repeats), "",
           "same check point NOT OK on the same machine in two consecutive PM cycles")

    # ---------------------------------------------------------------- 05
    record("05 Reliability", "Breakdown Count", len(bds))
    mttrs = [num(b["MTTR_Min"]) for b in bds if num(b["MTTR_Min"]) is not None]
    record("05 Reliability", "MTTR (Min)", statistics.fmean(mttrs) if mttrs else None, "min")
    rts = [num(b["Response_Time_Min"]) for b in bds if num(b["Response_Time_Min"]) is not None]
    record("05 Reliability", "Avg Response Time (Min)", statistics.fmean(rts) if rts else None, "min")
    loading = sum(num(s["Actual_Std_Hours"], 0) for s in std)
    downtime = sum(num(b["Production_Loss_Min"], 0) for b in bds) / 60
    record("05 Reliability", "Loading Hours", loading, "h")
    record("05 Reliability", "Downtime Hours", downtime, "h")
    record("05 Reliability", "MTBF (Hrs)", loading / len(bds) if bds else None, "h")
    record("05 Reliability", "Availability %",
           (loading - downtime) / loading if loading else None, "%")

    # Breakdowns After PM (7d)
    pm_ends = [(w["Cell_ID"], date(w["Actual_End_Date"]))
               for w in completed if date(w["Actual_End_Date"])]
    after_pm = []
    for b in bds:
        bd = dtm(b["Reported_DateTime"])
        if not bd:
            continue
        for cell, end in pm_ends:
            if cell == b["Cell_ID"] and end <= bd.date() <= end + dt.timedelta(days=7):
                after_pm.append((b["BD_ID"], b["Cell_ID"], bd.date(), end,
                                 (bd.date() - end).days))
                break
    record("05 Reliability", "Breakdowns After PM (7d)", len(after_pm), "",
           "THE measure that says whether the PM is working or cosmetic")
    record("05 Reliability", "Breakdowns After PM %",
           len(after_pm) / len(bds) if bds else None, "%")
    record("05 Reliability", "Repeat Breakdown Count",
           len([b for b in bds if yes(b["Recurrence_Flag"])]))
    record("05 Reliability", "Open Breakdowns", len([b for b in bds if b["Status"] != "Closed"]))

    # ---------------------------------------------------------------- 06
    spare_cost = sum(num(r["Total_Cost_INR"], 0) for r in srep)
    pm_cost = sum(num(r["Total_Cost_INR"], 0) for r in srep if r["Source_Type"] == "PM")
    bd_cost = sum(num(r["Total_Cost_INR"], 0) for r in srep if r["Source_Type"] == "Breakdown")
    record("06 Spares", "Spare Cost", spare_cost, "INR")
    record("06 Spares", "Planned Spare Cost", pm_cost, "INR")
    record("06 Spares", "Unplanned Spare Cost", bd_cost, "INR")
    record("06 Spares", "Spare Cost per PM",
           pm_cost / len(completed) if completed else None, "INR/PM")
    record("06 Spares", "Qty Replaced", sum(num(r["Qty_Used"], 0) for r in srep))
    record("06 Spares", "Requests Pending Approval",
           len([r for r in sreq if r["Approval_Status"] == "Pending"]))
    leads = [(date(r["Approved_Date"]) - dtm(r["Request_DateTime"]).date()).days
             for r in sreq if date(r["Approved_Date"]) and dtm(r["Request_DateTime"])]
    record("06 Spares", "Avg Approval Lead Time (Days)",
           statistics.fmean(leads) if leads else None, "days")
    record("06 Spares", "Approved Not Issued Count",
           len([r for r in sreq if r["Approval_Status"] == "Approved" and r["Issue_Status"] != "Issued"]),
           "", "the gap nobody watches - approval is done, the PM still waits")
    below = [s for s in spares if yes(s["Active"])
             and num(s["Current_Stock"]) is not None and num(s["Min_Stock"]) is not None
             and num(s["Current_Stock"]) <= num(s["Min_Stock"])]
    record("06 Spares", "Stock Below Min Count", len(below), "",
           ", ".join(s["Spare_Code"] for s in below) or "none")
    record("06 Spares", "Stock Value (INR)",
           sum(num(s["Current_Stock"], 0) * num(s["Unit_Cost_INR"], 0) for s in spares), "INR")
    record("06 Spares", "Warranty Claims Flagged",
           len([r for r in srep if yes(r["Warranty_Claim"])]))

    # ---------------------------------------------------------------- 07
    by_tech = Counter(t["Completed_By"] for t in t_completed if t["Completed_By"])
    record("07 Technician", "PMs Completed by Tech (max)",
           max(by_tech.values()) if by_tech else None, "tasks",
           ", ".join(f"{k}={v}" for k, v in sorted(by_tech.items())))
    record("07 Technician", "Avg Task Duration by Tech",
           statistics.fmean(durs) if durs else None, "min")
    total_notok_completed = sum(int(num(t["NOT_OK_Count"], 0)) for t in t_completed)
    record("07 Technician", "Findings Raised per PM",
           total_notok_completed / len(t_completed) if t_completed else None, "findings/PM",
           "higher means more thorough - label it that way on the page")
    record("07 Technician", "Active Technicians", len(by_tech))
    record("07 Technician", "Workload Imbalance",
           max(by_tech.values()) - min(by_tech.values()) if len(by_tech) > 1 else None, "tasks")

    # ------------------------------------------------------------------
    # Print
    # ------------------------------------------------------------------
    folder = None
    blanks = []
    for r in RESULTS:
        if r["folder"] != folder:
            folder = r["folder"]
            print(f"\n{folder}")
            print("-" * 78)
        line = f"  {r['measure']:<42} {fmt(r['value']):>14} {r['unit']}"
        if r["value"] is None:
            blanks.append(r["measure"])
        print(line)
        if r["note"]:
            print(f"     {r['note']}")

    # ------------------------------------------------------------------
    # Hand-worked examples for the three calculations that carry the most weight
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("  HAND-WORKED EXAMPLE 1 - Breakdowns After PM (7 days)")
    print("=" * 78)
    print(f"  {len(after_pm)} of {len(bds)} breakdowns fell within 7 days of a completed")
    print(f"  PM on the same cell  ({len(after_pm) / len(bds):.1%}).")
    print("\n  BD_ID      Cell      Breakdown    PM completed   Gap")
    print("  " + "-" * 56)
    for bid, cell, bdd, end, gap in sorted(after_pm, key=lambda x: x[2])[:8]:
        print(f"  {bid:<10} {cell:<9} {bdd}   {end}     {gap} day(s)")
    if len(after_pm) > 8:
        print(f"  ... and {len(after_pm) - 8} more")
    print("\n  Read as a SHARE, not a count. A rising count during a period of rising")
    print("  PM volume is expected; a rising share is the warning that the PM is not")
    print("  doing anything.")

    print("\n" + "=" * 78)
    print("  HAND-WORKED EXAMPLE 2 - Projected PM Date")
    print("=" * 78)
    print(f"  Formula:  Hours to Next PM  /  Avg Monthly Std Hours L3M  ->  months,")
    print(f"            rounded UP, added to today ({today}).")
    print(f"  L3M window: {l3m[0]} .. {l3m[-1]}\n")
    print("  Cell      Counter  Trigger  Remaining   L3M avg   Months   Projected     Calendar due  Which first")
    print("  " + "-" * 108)
    import math
    for c in sorted(cells, key=lambda x: x["Cell_ID"]):
        cid = c["Cell_ID"]
        counter = num(c["Cum_Std_Hours_Since_PM"], 0)
        trg = num(c["PM_Trigger_Hours"], 0)
        remaining = max(trg - counter, 0)
        avg = per_cell_l3m.get(cid)
        if avg:
            m = remaining / avg
            mo = math.ceil(m)
            y, mth = today.year, today.month + mo
            y += (mth - 1) // 12
            mth = (mth - 1) % 12 + 1
            day = min(today.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mth - 1])
            proj = dt.date(y, mth, day)
        else:
            m, proj = None, None
        cal = date(c["Next_PM_Due_Date_Calendar"])
        first = "calendar" if (proj and cal and cal < proj) else ("hours" if proj else "calendar")
        print(f"  {cid:<9} {counter:>7,.0f}  {trg:>7,.0f}  {remaining:>9,.0f}  "
              f"{(avg or 0):>8,.0f}  {(f'{m:.2f}' if m is not None else '-'):>7}   "
              f"{str(proj):<12}  {str(cal):<12}  {first}")
    print("\n  Rounded UP on purpose: a cell needing 1.2 months of running is due in the")
    print("  second month, not the first. Rounding down would schedule a PM before the")
    print("  hours exist to justify it.")

    print("\n" + "=" * 78)
    print("  HAND-WORKED EXAMPLE 3 - Mid-month proration after a PM reset")
    print("=" * 78)
    print("  Rule: if a cell's PM reset falls inside the month being uploaded, only the")
    print("  portion of that month's hours AFTER the reset date is posted to the new")
    print("  counter, prorated by calendar days.\n")
    print("      posted = Actual_Std_Hours x (days_in_month - day_of_reset) / days_in_month\n")
    ex_cell, ex_month, ex_hours, ex_reset = "CELL-05", "2026-04", 780.0, dt.date(2026, 4, 2)
    dim = 30
    posted = ex_hours * (dim - ex_reset.day) / dim
    print(f"  Worked example - {ex_cell}, month {ex_month}:")
    print(f"    Actual_Std_Hours reported for the month : {ex_hours:,.1f} h")
    print(f"    PM reset date                           : {ex_reset}  (day {ex_reset.day})")
    print(f"    Days in month                           : {dim}")
    print(f"    Days after the reset                    : {dim} - {ex_reset.day} = {dim - ex_reset.day}")
    print(f"    Posted to the NEW counter               : "
          f"{ex_hours:,.1f} x {dim - ex_reset.day}/{dim} = {posted:,.2f} h")
    print(f"    Discarded (belonged to the old cycle)   : {ex_hours - posted:,.2f} h")
    print(f"\n  Check: {posted:,.2f} + {ex_hours - posted:,.2f} = {ex_hours:,.1f} h - the month is")
    print("  fully accounted for, nothing is lost and nothing is double-counted.")
    print("\n  Without this rule the whole month's hours land on the new counter and every")
    print("  cell that resets mid-month runs its next PM early, permanently.")

    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("  Summary")
    print("=" * 78)
    print(f"  {len(RESULTS)} measures recomputed.")
    if blanks:
        print(f"  {len(blanks)} returned blank (check these are legitimately empty):")
        for b in blanks:
            print(f"     - {b}")
    else:
        print("  Every measure returned a value. None is blank, none errored.")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"asof": str(today), "results": RESULTS}, fh, indent=2, default=str)
        print(f"\n  wrote {args.json}")


if __name__ == "__main__":
    main()
