"""Build Supervisor_Shift_Schedule_Sep-Oct_2026.xlsx from the solver output."""
import datetime as dt

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from solver import END, NDAYS, PEOPLE, START, date, solve, verify

OUT = "Supervisor_Shift_Schedule_Sep-Oct_2026.xlsx"
NAMES = {
    "M": "Main Supervisor (M)",
    "T1": "Tooling Supervisor 1 (T1)",
    "T2": "Tooling Supervisor 2 (T2)",
    "E": "Electrical Supervisor (E)",
}
FILL = {
    "1st": PatternFill("solid", fgColor="DDEBF7"),
    "2nd": PatternFill("solid", fgColor="FCE4D6"),
    "G": PatternFill("solid", fgColor="E2EFDA"),
    "OFF": PatternFill("solid", fgColor="D9D9D9"),
    "cur": PatternFill("solid", fgColor="F2F2F2"),
    "head": PatternFill("solid", fgColor="1F4E78"),
    "sun": PatternFill("solid", fgColor="FFF2CC"),
}
THIN = Side(style="thin", color="A6A6A6")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LABEL = {1: "1st", 2: "2nd", "OFF": "OFF"}


def roster_sheet(wb, title, heading, r):
    ws = wb.create_sheet(title)
    ws["A1"] = heading
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = ("1st / 2nd = shift, G = general shift, OFF = weekly off. "
                "24-27 Sep: keep the current roster; the new pattern starts Mon 28 Sep.")
    ws["A2"].font = Font(italic=True, size=9)
    cols = ["Date", "Day", NAMES["M"], NAMES["T1"], NAMES["T2"], NAMES["E"],
            "On 1st shift", "On 2nd shift", "Rules check"]
    for c, h in enumerate(cols, 1):
        cell = ws.cell(row=4, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = FILL["head"]
        cell.alignment = CENTER
        cell.border = BOX
    row = 5
    # 24-27 Sep: current roster
    d0 = dt.date(2026, 9, 24)
    while d0 < START:
        vals = [d0, d0.strftime("%a"), "Current roster", "", "", "", "", "", ""]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.fill = FILL["cur"]
            cell.border = BOX
            cell.alignment = CENTER
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=9)
        ws.cell(row=row, column=1).number_format = "DD-MMM-YY"
        row += 1
        d0 += dt.timedelta(days=1)

    for d in range(NDAYS):
        day = date(d)
        wd = day.weekday()
        m = "G" if wd < 5 else "OFF"
        cells = {p: LABEL[r[p][d]] for p in PEOPLE}
        first = (["M"] if m == "G" else []) + [p for p in PEOPLE if cells[p] == "1st"]
        second = [p for p in PEOPLE if cells[p] == "2nd"]
        if wd == 6:
            ok = "OK - Sunday cover" if first or second else "GAP"
        else:
            ok = "OK" if first and second else "GAP"
        if cells["T1"] != "OFF" and cells["T1"] == cells["T2"]:
            ok = "TOOLING CLASH"
        vals = [day, day.strftime("%a"), m, cells["T1"], cells["T2"], cells["E"],
                ", ".join(first) or "-", ", ".join(second) or "-", ok]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = BOX
            cell.alignment = CENTER
            if 3 <= c <= 6:
                cell.fill = FILL[v]
                if v == "OFF":
                    cell.font = Font(bold=True, color="7F7F7F")
            elif wd == 6:
                cell.fill = FILL["sun"]
        ws.cell(row=row, column=1).number_format = "DD-MMM-YY"
        row += 1

    # per-person summary
    row += 1
    ws.cell(row=row, column=1, value="Summary 28 Sep - 31 Oct").font = Font(bold=True)
    row += 1
    for c, h in enumerate(["Supervisor", "", "Days on 1st", "Days on 2nd", "Days off",
                           "Sundays worked", "Sundays off", "Weekend (Sat+Sun) off"], 1):
        cell = ws.cell(row=row, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = FILL["head"]
        cell.alignment = CENTER
        cell.border = BOX
    row += 1
    sundays = [d for d in range(NDAYS) if date(d).weekday() == 6]
    for p in PEOPLE:
        x = r[p]
        wk = sum(1 for d in sundays if x[d] == "OFF" and x[d - 1] == "OFF")
        vals = [NAMES[p], "", x.count(1), x.count(2), x.count("OFF"),
                sum(x[d] != "OFF" for d in sundays),
                sum(x[d] == "OFF" for d in sundays), wk]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = BOX
            cell.alignment = CENTER
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        row += 1

    widths = [12, 6, 16, 16, 16, 16, 14, 14, 18]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[4].height = 32
    ws.freeze_panes = "C5"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0
    return ws


def readme(wb, fixed_offs):
    ws = wb.active
    ws.title = "Read me"
    lines = [
        ("Supervisor Shift Schedule, 28 Sep - 31 Oct 2026", True),
        ("", False),
        ("Team", True),
        ("M  - Main Supervisor: general shift Mon-Fri, weekly off Sat + Sun. Counts as 1st-shift cover Mon-Fri.", False),
        ("T1, T2 - Tooling Supervisors: 1st / 2nd shift, never on the same shift as each other.", False),
        ("E  - Electrical Supervisor: 1st / 2nd shift, may share a shift with either tooling supervisor.", False),
        ("Replace the codes with names in the column headings of each sheet.", False),
        ("", False),
        ("Rules built in (and checked for every day in the 'Rules check' column)", True),
        ("1. T1, T2 and E each get 2 consecutive days off every week (Mon-Sun).", False),
        ("2. After the days off, the shift switches: 1st -> 2nd, 2nd -> 1st.", False),
        ("3. T1 and T2 are never on the same shift.", False),
        ("4. Mon-Sat: at least 1 supervisor on 1st and 1 on 2nd (M covers 1st Mon-Fri).", False),
        ("5. Sunday: maintenance only, at least 1 supervisor.", False),
        ("6. Nobody works more than 7 days in a row; at least 3 working days between offs.", False),
        ("", False),
        ("Option A - Fixed weekly offs", True),
        (f"Offs are the same every week: {fixed_offs}. M: Sat + Sun.", False),
        ("Because offs never move, the same person covers every Sunday. That is what fixed offs mean.", False),
        ("", False),
        ("Option B - Rotating weekly offs", True),
        ("Off days move week to week. Everyone gets at least one Sunday off and one full Sat + Sun weekend off.", False),
        ("Tradeoff: with the rules above, only one person can cover every Sunday if that person never gets a", False),
        ("Sunday off (as in Option A). Sharing Sunday offs means some Sundays have 2-3 supervisors on duty.", False),
        ("", False),
        ("Why the tooling offs sit together", True),
        ("T1 and T2 switch shift after their offs, so to stay on opposite shifts their offs must be on the", False),
        ("same days or directly one after the other.", False),
        ("", False),
        ("Not considered", True),
        ("Public holidays, leave, and the 24-27 Sep roster (keep the current one). Tell us to adjust.", False),
    ]
    for i, (t, bold) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=t)
        c.font = Font(bold=bold, size=14 if i == 1 else 11)
    ws.column_dimensions["A"].width = 110


def fixed_desc(r):
    out = []
    for p in PEOPLE:
        x = r[p]
        for d in range(NDAYS - 1):
            if x[d] == "OFF" and x[d + 1] == "OFF":
                out.append(f"{p}: {date(d).strftime('%a')} + {date(d + 1).strftime('%a')}")
                break
    return ", ".join(out)


if __name__ == "__main__":
    fixed, _ = solve(True)
    rot, _ = solve(False)
    assert not verify(fixed), verify(fixed)
    assert not verify(rot), verify(rot)
    wb = Workbook()
    readme(wb, fixed_desc(fixed))
    roster_sheet(wb, "Option A - Fixed offs",
                 f"Option A - Fixed weekly offs ({fixed_desc(fixed)})", fixed)
    roster_sheet(wb, "Option B - Rotating offs",
                 "Option B - Rotating weekly offs (Sunday offs shared)", rot)
    wb.save(OUT)
    print("saved", OUT, "|", fixed_desc(fixed))
