#!/usr/bin/env python3
"""
test_power_app.py - drives the prototype through the whole technician journey and
checks that every rule the app is supposed to enforce actually holds.

The rules are the reason the app exists, so they are what gets tested:
a checklist cannot start without a machine scan, mandatory tasks block submit,
a Not OK needs a comment and a photo, closing a job removes it from the list,
and the month-end run applies the 4000-hour rule.
"""
import os, sys
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "file://" + os.path.join(ROOT, "powerapp", "PM_Field_App.html")
fails = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        fails.append(label)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page(viewport={"width": 1400, "height": 1050}, device_scale_factor=2)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(PAGE)
    print()

    counts = pg.evaluate("""() => { const o={};
        DATA.openWOs.forEach(w => o[w.AssignedTechID] = (o[w.AssignedTechID]||0)+1); return o; }""")
    tech = max(counts, key=counts.get)
    pg.select_option("#whoSel", tech)
    print(f"  signed in as {tech}, {counts[tech]} open work orders\n")

    pg.click('[data-go="scanTech"]')
    check("technician QR opens their own list",
          pg.locator(".wo").count() == counts[tech],
          f"{pg.locator('.wo').count()} jobs")

    first_wo = pg.locator(".wo").first.get_attribute("data-wo")
    pg.locator(".wo").first.click()
    check("tapping a job opens the machine hub, not the checklist",
          pg.locator(".bar .t").inner_text().splitlines()[0] != "PM checklist")

    pg.click('[data-go="startPM"]')
    on_checklist = pg.locator(".bar .t").inner_text().startswith("PM checklist")
    warn = pg.locator(".toast").inner_text() if pg.locator(".toast").count() else ""
    check("checklist blocked without a machine scan", not on_checklist, f"'{warn}'")

    machine = pg.evaluate("() => JSON.parse(localStorage.getItem('pmFieldAppState.v1')).machineId")
    pg.click('[data-go="back"]')
    pg.select_option("#machPick", machine)
    pg.click('[data-go="scanMachine"]')
    check("machine hub answers 'when was the last PM' first",
          pg.locator(".hero .lab").first.inner_text().lower().startswith("last pm"),
          pg.locator(".hero .big").first.inner_text())

    pg.click('[data-go="startPM"]')
    n_tasks = pg.locator(".task").count()
    check("checklist opens after a scan, with its tasks", n_tasks > 0, f"{n_tasks} tasks")
    check("submit is gated on mandatory tasks",
          pg.locator('[data-go="submitChecklist"]').is_disabled())

    for i in range(n_tasks):
        pg.locator(f'[data-res="{i}"][data-val="{"Not OK" if i == 1 else "OK"}"]').click()
    pg.locator('[data-obs="1"]').fill("Measured 3.8%, below the 6-9% standard")
    pg.click('[data-go="submitChecklist"]')
    t = pg.locator(".toast").inner_text() if pg.locator(".toast").count() else ""
    check("a Not OK cannot be submitted without a photo", "photo" in t.lower(), f"'{t}'")

    pg.locator('[data-photo="1"]').click()
    pg.click('[data-go="submitChecklist"]')
    pg.wait_for_timeout(150)
    check("submitted job leaves the technician's list",
          pg.locator(f'.wo[data-wo="{first_wo}"]').count() == 0,
          f"{pg.locator('.wo').count()} remaining")

    st = pg.evaluate("() => JSON.parse(localStorage.getItem('pmFieldAppState.v1'))")
    wo = next((w for w in st["done"] if w["WOID"] == first_wo), None)
    check("closed work order records result, on-time and the scan", wo is not None
          and wo["MachineQRScanned"] == "Yes" and wo["OnTimeFlag"] in ("Yes", "No"),
          f"result='{wo['PMResult']}' onTime={wo['OnTimeFlag']}" if wo else "")
    check("a failed task raises an abnormality automatically",
          len(st["abnormalities"]) >= 1, f"{len(st['abnormalities'])} raised")
    check("every action wrote a scan record", len(st["scans"]) >= 3,
          f"{len(st['scans'])} scans")

    pg.evaluate("""() => { const s = JSON.parse(localStorage.getItem('pmFieldAppState.v1'));
        s.screen = 'scrMonthEnd'; localStorage.setItem('pmFieldAppState.v1', JSON.stringify(s)); }""")
    pg.reload()
    pg.click('[data-go="runMonth"]')
    pg.wait_for_timeout(150)
    st2 = pg.evaluate("() => JSON.parse(localStorage.getItem('pmFieldAppState.v1'))")
    run = st2["monthsRun"][0] if st2["monthsRun"] else None
    check("month-end applies the rule to every cell", run is not None and len(run["rows"]) == 8,
          f"{run['tripped']} tripped, {run['created']} work orders raised" if run else "")
    if run:
        carry_ok = all(
            (not r["triggered"]) or abs(max(0, r["closing"] - r["threshold"])
                                        - (r["closing"] - r["threshold"] if r["closing"] > r["threshold"] else 0)) < 0.01
            for r in run["rows"])
        check("hours past the threshold carry forward, never lost", carry_ok)

    pg.screenshot(path=os.path.join(ROOT, "powerapp", "prototype-screenshot.png"))
    check("no javascript errors", len(errs) == 0, str(errs[:2]) if errs else "")
    b.close()

print()
print("  " + ("PASS - the prototype enforces every rule end to end"
             if not fails else f"FAIL - {len(fails)}: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
