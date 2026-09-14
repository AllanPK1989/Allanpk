#!/usr/bin/env python3
"""
build_forms_script.py
---------------------
Generates automate/FORMS_BUILD_SCRIPT.md - every question on all five Microsoft
Forms, in the exact order to enter them, with the wording to copy.

Building the forms is the one stage nobody can automate away: Microsoft Forms has
no import, so somebody types them. The checklist form alone is 102 questions
across nine branched sections, every one carrying a check point and an acceptance
standard that has to match Checklist_Master exactly - because the acceptance
standard IS the limit the technician judges against, and a typo in it is a
machine passed against the wrong number.

So this generates the script FROM the master data. Copy, do not transcribe.

    python3 tools/build_forms_script.py
"""
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "sharepoint" / "data"
OUT = ROOT / "automate" / "FORMS_BUILD_SCRIPT.md"


def rows(name):
    with open(DATA / f"{name}.csv", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def active(recs):
    return [r for r in recs if r.get("Active", "Yes") == "Yes"]


def q(n, kind, title, required=True, subtitle=None, options=None):
    """One question, formatted so the title can be copied on its own line."""
    out = [f"**Q{n} · {kind}{' · Required' if required else ''}**", "", "```",
           title, "```"]
    if subtitle:
        out += ["", "*Subtitle* (paste into the question's description box):", "",
                "```", subtitle, "```"]
    if options:
        out += ["", "*Choices*, one per line:", "", "```"] + list(options) + ["```"]
    return "\n".join(out) + "\n"


def main():
    techs = active(rows("Technician_Master"))
    spares = active(rows("Spare_Master"))
    checks = active(rows("Checklist_Master"))
    cells = active(rows("Cell_Master"))

    tech_names = [t["Tech_Name"] for t in techs]
    by_checklist = {}
    for c in checks:
        by_checklist.setdefault(c["Checklist_ID"], []).append(c)
    for v in by_checklist.values():
        v.sort(key=lambda r: int(r["Item_No"]))

    L = []
    w = L.append

    w("# Forms build script — every question, ready to copy\n")
    w("**Generated from the master data. Copy the text; do not retype it.**\n")
    w("Microsoft Forms has no import, so somebody types these five forms by hand. "
      "This is that typing reduced to copy-and-paste, and it is generated from "
      "`Checklist_Master`, `Technician_Master` and `Spare_Master` so the wording "
      "on the phone matches the wording in the lists exactly.\n")
    w("> **Why that matters most for the acceptance standards.** The standard is "
      "the limit the technician judges the machine against. Retyped by hand, "
      "\"≤ 0.05 mm\" becomes \"< 0.5 mm\" on one line out of fifty-one, and a "
      "machine passes against a number ten times too loose. Nothing catches it.\n")
    w(f"**Total: {4 + 2 + 9 + 14 + 9 + len(checks) * 2} questions across five forms** "
      f"— {len(checks) * 2} of them on the checklist.\n")

    w("## Before you start\n")
    w("Read `FLOW_SPECS.md` §\"The five forms\" first — it explains *why* the first "
      "questions are ordered the way they are. The short version, and the rule that "
      "will catch you out:\n")
    w("> **A pre-filled link fills answers by POSITION, not by name.** `Machine ID` "
      "is always question 1, `Cell ID` always question 2, and on the checklist "
      "`Checklist ID` is always question 3. Insert anything above them and every "
      "sticker on the shop floor starts filling the wrong boxes, silently. New "
      "questions go at the bottom, always.\n")
    w("Settings, identical on all five: **Anyone can respond** on, **Record name** "
      "off.\n")
    w("---\n")

    # ------------------------------------------------------------------ Form 1
    w("# Form 1 — PM Start\n")
    w("**Two questions, both pre-filled from the sticker.** The technician taps "
      "Submit and nothing else.\n")
    w(q(1, "Text", "Machine ID"))
    w(q(2, "Text", "Cell ID"))
    w("> No technician question. Nothing stores who *started* a job — `Completed_By` "
      "on the checklist is the record that matters — so a dropdown here would be a "
      "tap that throws its answer away.\n")
    w("---\n")

    # ------------------------------------------------------------------ Form 2
    w("# Form 2 — PM Checklist\n")
    w(f"**4 questions, then one branched section per checklist — "
      f"{len(by_checklist)} sections, {len(checks)} check points, "
      f"{len(checks) * 2} questions.** This is the long one.\n")
    w(q(1, "Text", "Machine ID"))
    w(q(2, "Text", "Cell ID"))
    w(q(3, "Choice", "Checklist ID", options=sorted(by_checklist)))
    w(q(4, "Choice", "Technician Name", options=tech_names))
    w("### Now set the branching on Q3\n")
    w("**… (on Q3) → Add branching.** Point each answer at its own section:\n")
    w("| If Checklist ID is | Go to |\n|---|---|")
    for i, cid in enumerate(sorted(by_checklist), 1):
        w(f"| `{cid}` | Section {i} |")
    w("")
    w("> Build **one form with nine sections**, not nine forms. Pre-fill Q3 from the "
      "machine's `Checklist_ID` and the technician never touches it.\n")

    OPTIONS = ["OK",
               "NOT OK — fixed on the spot",
               "NOT OK — needs follow-up",
               "N/A"]
    w("Every check point below is **two questions**: the four-option choice, then "
      "one optional text box. The four options carry two facts in one tap —\n")
    w("| Answer | `Result` | `Follow_Up_Required` |\n|---|---|---|")
    w("| OK | `OK` | No |")
    w("| NOT OK — fixed on the spot | `NOT OK` | No |")
    w("| NOT OK — needs follow-up | `NOT OK` | **Yes** |")
    w("| N/A | `NA` | No |\n")

    for i, cid in enumerate(sorted(by_checklist), 1):
        items = by_checklist[cid]
        meas = sum(1 for it in items if it["Check_Type"] == "Measurement")
        crit = sum(1 for it in items if it["Safety_Critical"] == "Yes")
        w(f"## Section {i} — `{cid}`  ·  {len(items)} check points  "
          f"·  {len(items) * 2} questions\n")
        bits = []
        if meas:
            bits.append(f"{meas} need a **measured number**")
        if crit:
            bits.append(f"{crit} are **safety-critical** and block the cell from closing")
        if bits:
            w("*" + "; ".join(bits) + ".*\n")
        for it in items:
            n = it["Item_No"]
            flag = "  ⚠ SAFETY-CRITICAL" if it["Safety_Critical"] == "Yes" else ""
            w(f"**Item {n}{flag}**\n")
            w(q(f"{n}a", "Choice", it["Check_Point"],
                subtitle=f"Accept: {it['Acceptance_Standard']}", options=OPTIONS))
            if it["Check_Type"] == "Measurement":
                w(q(f"{n}b", "Text", f"Reading — {it['Check_Point']}", required=False,
                    subtitle="Type the number you measured. Not \"ok\"."))
            else:
                w(q(f"{n}b", "Text", f"Observation — {it['Check_Point']}",
                    required=False))
        w("")

    w("### Last question on the form, after every section\n")
    w("**File upload · 1 file · not required**\n\n```\nPhoto\n```\n")
    w("Flow 4 attaches it to the rows marked NOT OK — which is what a photo on a "
      "PM checklist is ever of.\n")
    w("---\n")

    # ------------------------------------------------------------------ Form 3
    w("# Form 3 — Spare Replaced\n")
    w("**9 questions.** Records what was *fitted* — there is no requisition or "
      "approval here; the stores process already runs that.\n")
    w(q(1, "Text", "Machine ID"))
    w(q(2, "Text", "Cell ID"))
    w(q(3, "Choice", "Replaced by", options=tech_names))
    w(q(4, "Choice", "Replaced during", options=["PM", "Breakdown"]))
    w(q(5, "Text", "Work order or breakdown reference"))
    w(q(6, "Choice", "Spare code",
        options=[f"{s['Spare_Code']} — {s['Spare_Description']}" for s in spares]))
    w(q(7, "Number", "Quantity used"))
    w(q(8, "Choice", "Failure mode",
        options=["Wear", "Contamination", "Fatigue", "Overload", "Corrosion",
                 "Electrical", "End of life", "Other"]))
    w(q(9, "Choice", "Warranty claim", options=["Yes", "No"]))
    w("> **Question 8 is the one that pays for this form.** Repeated "
      "\"Contamination\" on the same part is a filtration problem, not a spares "
      "problem, and no amount of buying more parts will fix it. Keep it mandatory.\n")
    w("---\n")

    # ------------------------------------------------------------------ Form 4
    w("# Form 4 — Breakdown Report\n")
    w("**14 questions.**\n")
    w(q(1, "Text", "Machine ID"))
    w(q(2, "Text", "Cell ID"))
    w(q(3, "Choice", "Reported by", options=tech_names))
    w(q(4, "Choice", "Shift", options=["A", "B", "C"]))
    w(q(5, "Choice", "Breakdown type",
        options=["Electrical", "Mechanical", "Pneumatic", "Hydraulic", "Tooling",
                 "Other"]))
    w(q(6, "Text · long answer", "Symptom — what did it do?"))
    w(q(7, "Text · long answer", "Root cause — what was actually wrong?",
        required=False))
    w(q(8, "Text · long answer", "Action taken", required=False))
    w(q(9, "Date", "When was it responded to?", required=False))
    w(q(10, "Date", "Repair started", required=False))
    w(q(11, "Date", "Repair finished", required=False))
    w(q(12, "Number", "Production lost, minutes", required=False,
        subtitle="The WHOLE time the machine could not run — including waiting for "
                 "a technician and waiting for a part. Not just the repair."))
    w(q(13, "Choice", "Status", options=["Open", "Under Repair", "Closed"]))
    w(q(14, "Choice", "Has this happened before on this machine?",
        options=["Yes", "No"]))
    w("> Questions 9, 10 and 11 must be **Date and time**, not date only. Response "
      "time and MTTR are the gaps between them, worked out by the report — and a "
      "gap between two dates with no clock on them is measured in days.\n")
    w("---\n")

    # ------------------------------------------------------------------ Form 5
    w("# Form 5 — Abnormality Log\n")
    w("**9 questions.**\n")
    w(q(1, "Text", "Machine ID"))
    w(q(2, "Text", "Cell ID"))
    w(q(3, "Choice", "Logged by", options=tech_names))
    w(q(4, "Choice", "Category",
        options=["Safety", "Quality", "Leak", "Noise", "Vibration",
                 "5S / Housekeeping", "Other"]))
    w(q(5, "Text · long answer", "What did you see?"))
    w(q(6, "Choice", "Severity", options=["High", "Medium", "Low"]))
    w(q(7, "File upload · 1 file", "Photo", required=False))
    w(q(8, "Choice", "Who should fix it?",
        options=["Maintenance", "Production", "Quality", "Safety"]))
    w(q(9, "Date", "Fix by"))
    w("---\n")

    # ------------------------------------------------------------------ after
    w("# When all five exist\n")
    w("Make a pre-filled link for each (**Collect responses → Get a link to prefill "
      "answers**), cut each into its parts, and paste them into the 11 placeholders "
      "in `sharepoint/formatting/Machine_Master.MachineHub.view.json`. Then re-run "
      "`apply_views.ps1`.\n")
    w(f"**Test one on a real phone before going further.** There are {len(cells)} "
      "cells and 30 machines depending on these links being right.\n")

    OUT.write_text("\n".join(L), encoding="utf-8")
    total = sum(len(v) for v in by_checklist.values())
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  5 forms, {len(by_checklist)} branched sections, {total} check points")
    print(f"  {total * 2} checklist questions generated from Checklist_Master")
    print(f"  {len(tech_names)} technicians, {len(spares)} spare codes embedded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
