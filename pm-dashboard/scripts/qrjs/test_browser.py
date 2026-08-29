#!/usr/bin/env python3
"""
test_browser.py - drives qr/QR_Generator.html in a real browser and checks that
the page a technician's manager will actually open produces the right codes.

Verifies: the web-link paste extracts the three IDs; Generate renders one card
per machine and per technician; and the SVG rendered on a label encodes exactly
the same modules as the reference implementation for that machine's payload.
"""
import os, re, sys
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from qrcode.util import QRData, MODE_8BIT_BYTE
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE = "file://" + os.path.join(ROOT, "qr", "QR_Generator.html")

ENV = "3f2a8c11-4d5e-4a7b-9c0d-1e2f3a4b5c6d"
APP = "b7e91d20-6f3a-48c9-8d1e-2a5b7c9d0e3f"
TEN = "9c8b7a6d-5e4f-3210-9876-543210fedcba"
WEBLINK = f"https://apps.powerapps.com/play/e/{ENV}/a/{APP}?tenantId={TEN}"

def ref_paths(text, border=2):
    q = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=0)
    q.add_data(QRData(text.encode("utf-8"), mode=MODE_8BIT_BYTE))
    q.make(fit=True)
    out = []
    for r, row in enumerate(q.modules):
        for c, v in enumerate(row):
            if v:
                out.append(f"M{c+border},{r+border}h1v1h-1z")
    return "".join(out), len(q.modules)

fails = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(PAGE)

    pg.fill("#weblink", WEBLINK)
    got = {k: pg.input_value("#" + k) for k in ("env", "app", "ten")}
    want = {"env": ENV, "app": APP, "ten": TEN}
    print(f"  web-link parsing      {'OK' if got == want else 'FAIL ' + str(got)}")
    if got != want:
        fails.append("web-link parsing")

    pg.click("#gen")
    pg.wait_for_selector(".card", timeout=15000)
    pg.wait_for_function("document.getElementById('status').className.includes('ok')", timeout=20000)

    cards = pg.locator(".card").count()
    badges = pg.locator(".card.badge").count()
    labels = cards - badges
    status = pg.inner_text("#status")
    print(f"  machine labels        {labels}   (expect 33)")
    print(f"  technician badges     {badges}   (expect 10)")
    print(f"  status line           {status}")
    if labels != 33 or badges != 10:
        fails.append("card counts")

    # the first label must be MC-001, and its SVG must match the reference exactly
    first_id = pg.locator(".card .id").first.inner_text()
    svg_path = pg.locator(".card .qr svg path").first.get_attribute("d")
    view_box = pg.locator(".card .qr svg").first.get_attribute("viewBox")
    expect_path, n = ref_paths(
        f"https://apps.powerapps.com/play/e/{ENV}/a/{APP}"
        f"?tenantId={TEN}&source=qr&type=machine&id={first_id}")
    ok_path = svg_path == expect_path
    ok_box = view_box == f"0 0 {n+4} {n+4}"
    print(f"  first label id        {first_id}")
    print(f"  rendered svg modules  {'match the reference' if ok_path else 'DIFFER'}"
          f"   ({len(svg_path.split('z')) - 1} dark modules)")
    print(f"  viewBox               {view_box}  {'OK' if ok_box else 'FAIL'}")
    if not ok_path: fails.append("svg path")
    if not ok_box: fails.append("viewBox")

    # a technician badge, checked the same way
    t_svg = pg.locator(".card.badge .qr svg path").first.get_attribute("d")
    t_expect, _ = ref_paths(
        f"https://apps.powerapps.com/play/e/{ENV}/a/{APP}"
        f"?tenantId={TEN}&source=qr&type=tech&id=TECH-01")
    print(f"  technician badge svg  {'matches the reference' if t_svg == t_expect else 'DIFFERS'}")
    if t_svg != t_expect: fails.append("tech svg")

    print(f"  javascript errors     {len(errs)}" + (f"  {errs[:2]}" if errs else ""))
    if errs: fails.append("js errors")
    b.close()

print()
print("  " + ("PASS - the browser tool produces reference-identical codes"
             if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
