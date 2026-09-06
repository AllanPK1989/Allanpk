"""Sheets 11-13: panel general arrangement, terminal schedule, I/O list and BOM."""
from eplan import Sheet, LW_THIN, LW_MED, LW_THICK
from data import INPUTS, OUTPUTS, TERMINALS_X1, TERMINALS_X2, BOM
from sheets_a import new


# ===================================================================== 11
def sheet11():
    s = new("11 / 13", "PANEL GENERAL ARRANGEMENT & GLAND PLATE",
            "Wall-mounted enclosure 800 H x 600 W x 250 D mm, IP54, RAL 7035")

    # ---------- internal layout (mounting plate) ----------
    PX, PY = 30, 40
    SC = 0.30                      # 1 mm real = 0.30 mm on paper
    W, H = 560 * SC, 760 * SC      # mounting plate 560 x 760
    s.text(PX, PY - 5, "MOUNTING PLATE - INTERNAL LAYOUT   (scale approx. 1:3.3)",
           2.6, weight="bold")
    s.rect(PX, PY, W, H, lw=LW_THICK)
    s.text(PX + W / 2, PY + H + 6, "mounting plate 560 x 760 mm", 2.1, "middle")

    rails = [
        (70,  "-Q1  MCCB 4P 63 A   |   -Q4  MCB 3P 40 A   |   -Q5   -Q6   -Q7"),
        (160, "-K3  40 A  + -F3    |   -K1 + -F1          |   -K2 + -F2"),
        (250, "-T1  control transformer 500 VA            |   -G1  SMPS 24 V DC 5 A"),
        (350, "-A1  PLC  MELSEC iQ-F  FX5U-32MT/ES        |   -KA1  -KA2  -KA3"),
        (440, "-F5 ... -F15  fuse holders                 |   spare DIN rail (20 %)"),
        (540, "-X1  control terminals  (45 way, 2.5 mm2)"),
        (650, "-X2  power terminals (10 mm2)              |   -PE1  earth bar 25 x 3"),
    ]
    for ry, label in rails:
        y = PY + ry * SC
        s.line(PX + 6, y, PX + W - 6, y, w=LW_MED)
        s.line(PX + 6, y + 3.2, PX + W - 6, y + 3.2, w=LW_MED)
        s.text(PX + 8, y + 2.4, label, 1.85)
    # trunking
    for tx in (0.5, ):
        pass
    s.rect(PX + 6, PY + 4, W - 12, 6, lw=LW_THIN, dash="1.5,1.5")
    s.text(PX + 8, PY + 8.4, "wiring trunking 40 x 60 mm (top)", 1.8)
    s.rect(PX + 6, PY + H - 12, W - 12, 6, lw=LW_THIN, dash="1.5,1.5")
    s.text(PX + 8, PY + H - 7.6, "wiring trunking 40 x 60 mm (bottom)", 1.8)

    # ---------- gland plate ----------
    GX, GY = 220, 40
    GW, GH = 560 * SC, 150 * SC
    s.text(GX, GY - 5, "GLAND PLATE - BOTTOM OF ENCLOSURE", 2.6, weight="bold")
    s.rect(GX, GY, GW, GH, lw=LW_THICK)
    glands = [
        (0.10, "M25", "-W1", "incomer", "4C x 16 mm2"),
        (0.26, "M20", "-W2", "blower 1", "4C x 2.5 mm2"),
        (0.42, "M20", "-W3", "blower 2", "4C x 2.5 mm2"),
        (0.58, "M25", "-W4", "heater bank", "4C x 10 mm2"),
        (0.74, "M16", "-W6", "door switch -B1", "3C x 1.0 mm2"),
        (0.90, "M16", "-W7", "-B2 / -B3", "screened, 2 pr"),
    ]
    for f, sz, tag, d1, d2 in glands:
        cx = GX + GW * f
        s.circle(cx, GY + GH / 2, 3.4, lw=LW_MED)
        s.text(cx, GY + GH / 2 + 1.0, sz, 1.7, "middle")
        s.text(cx, GY - 1.4, tag, 1.9, "middle", weight="bold")
        s.text(cx, GY + GH + 4.0, d1, 1.75, "middle")
        s.text(cx, GY + GH + 7.2, d2, 1.75, "middle")

    # ---------- construction schedule ----------
    CX, CY = 220, 100
    s.text(CX, CY - 3, "ENCLOSURE & CONSTRUCTION", 2.6, weight="bold")
    s.table(CX, CY, [(44, "ITEM"), (124, "SPECIFICATION")], [
        ["Enclosure", "800 H x 600 W x 250 D mm, mild steel 1.5 mm, IP54"],
        ["Finish", "powder coated RAL 7035, plate RAL 9003"],
        ["Mounting", "wall mounted, 4 x M8 bolts, bottom of panel 1000 mm AFFL"],
        ["Door", "single door, 3-point lock, earthed with 4 mm2 braid"],
        ["Ventilation", "filter fan 100 m3/h + exhaust filter, thermostat set 35 C"],
        ["Cable entry", "bottom gland plate, removable, glands per the detail above"],
        ["Internal wiring", "in slotted trunking, minimum 60 % spare capacity"],
        ["Segregation", "415 V power and 24 V DC control in separate trunking runs"],
        ["Earthing", "copper earth bar -PE1 25 x 3 mm, all doors and plates bonded"],
        ["Labelling", "engraved traffolyte for devices, printed ferrules for cores"],
        ["Spare capacity", "20 % free DIN rail and 4 spare terminals per strip"],
        ["Tests", "IR 500 V DC, flash 1.5 kV 1 min, functional test to sheet 13"],
    ], rh=5.4, zebra="#f4f4f4")

    # ---------- clearances ----------
    s.dashbox(220, 182, 168, 44, "INSTALLATION REQUIREMENTS")
    for i, t in enumerate([
        "1.  Keep 800 mm clear working space in front of the panel (IEC 60204-1).",
        "2.  The panel must not be mounted on the oven skin or within 1 m of it -",
        "     radiated heat will drive the internal temperature above the PLC rating",
        "     (55 C).  Mount on the adjacent wall or on a free-standing frame.",
        "3.  Thermocouple and 4-20 mA cables to be run at least 300 mm away from",
        "     the motor and heater power cables, crossing at right angles only.",
        "4.  The oven body, the element housing and the blower frames must all be",
        "     bonded to -PE1.  Measure the bond resistance: < 0.1 ohm.",
    ]):
        s.text(223, 189 + i * 4.4, t, 2.0)

    s.notes(220, 236, [
        "1.  Layout shown is indicative; the panel builder may rearrange within the same",
        "     enclosure provided the segregation and clearance requirements are kept.",
        "2.  Fit an internal panel light and a 6 A socket outlet fed from -Q7 (RCBO).",
        "3.  Fit a door-mounted pocket for this drawing set and the O&M manual.",
    ])
    return s


# ===================================================================== 12
def sheet12():
    s = new("12 / 13", "TERMINAL STRIP SCHEDULE  -X1 / -X2",
            "All field and door-loom wiring terminates here; panel-plate devices are wired direct")

    half = (len(TERMINALS_X1) + 1) // 2
    cols = [(13, "TERM"), (15, "WIRE"), (24, "DEVICE"), (108, "DESCRIPTION"), (12, "SH.")]
    s.text(20, 30, "-X1   CONTROL TERMINALS  (2.5 mm2)", 2.8, weight="bold")
    s.table(20, 33, cols, [list(r) for r in TERMINALS_X1[:half]],
            rh=5.0, zebra="#f4f4f4", align=["middle", "middle", "start", "start", "middle"])
    s.text(212, 30, "-X1   CONTROL TERMINALS  (continued)", 2.8, weight="bold")
    s.table(212, 33, cols, [list(r) for r in TERMINALS_X1[half:]],
            rh=5.0, zebra="#f4f4f4", align=["middle", "middle", "start", "start", "middle"])

    y2 = 33 + 5.0 * (half + 1) + 12
    s.text(20, y2 - 3, "-X2   POWER TERMINALS  (10 mm2 + PE)", 2.8, weight="bold")
    s.table(20, y2, [(13, "TERM"), (15, "WIRE"), (26, "DEVICE"), (106, "DESCRIPTION")],
            [list(r) for r in TERMINALS_X2],
            rh=5.0, zebra="#f4f4f4", align=["middle", "middle", "start", "start"])

    s.dashbox(212, y2 - 6, 176, 62, "TERMINAL STRIP CONVENTIONS")
    for i, t in enumerate([
        "1.  -X1 is a single strip in terminal-number order with a marked end plate at each end.",
        "2.  Terminals 01-10 are the OVEN field devices, 20-35 the panel DOOR loom, 40-48 the door",
        "     indication loom, 60-61 the door-interlock provision and 70-73 spare.",
        "3.  Every core carries a printed ferrule with the wire number shown, at BOTH ends.",
        "4.  A grey terminal is used for all signals, light blue for 0 V and green/yellow for PE.",
        "5.  No more than TWO conductors in any one terminal; use a jumper comb for commons.",
        "6.  -X1:60 / -X1:61 carry the link -LK1.  Do not remove the link unless a hard-wired door",
        "     interlock is being fitted - the blowers will not run with the link removed.",
        "7.  Spare terminals 70-73 are pre-wired to PLC outputs Y12-Y15 for future use.",
    ]):
        s.text(215, y2 + 2 + i * 5.2, t, 2.0)

    s.notes(212, y2 + 66, [
        "1.  Wire numbers follow the scheme:  1xx = 230 V AC control,  2xx = 24 V DC inputs,",
        "     3xx = 24 V DC outputs,  and power cores are numbered by feeder (1L1, 2L1, 31 ...).",
        "2.  Check every ferrule against this schedule at pre-delivery inspection and again after",
        "     installation; a mis-numbered core is the single most common cause of a failed FAT.",
    ])
    return s


# ===================================================================== 13
def sheet13():
    s = new("13 / 13", "I/O SCHEDULE & BILL OF MATERIALS",
            "MELSEC iQ-F FX5U-32MT/ES  -  16 digital inputs, 16 digital outputs")

    # ---------- inputs ----------
    s.text(20, 30, "DIGITAL INPUTS", 2.8, weight="bold")
    rows = [[a, w, t.strip(), tag, cr, d] for a, w, t, tag, sym, cr, d, loc in INPUTS]
    s.table(20, 33, [(13, "ADDR"), (14, "WIRE"), (13, "-X1"), (17, "DEVICE"),
                     (18, "CONTACT"), (110, "DESCRIPTION")], rows,
            rh=5.0, zebra="#f4f4f4",
            align=["middle", "middle", "middle", "start", "middle", "start"])

    # ---------- outputs ----------
    s.text(20, 124, "DIGITAL OUTPUTS", 2.8, weight="bold")
    rows = [[a, w, t, tag, (c if c else "-"), d] for a, w, t, tag, k, c, d in OUTPUTS]
    s.table(20, 127, [(13, "ADDR"), (14, "WIRE"), (13, "-X1"), (17, "DEVICE"),
                      (18, "COLOUR"), (110, "DESCRIPTION")], rows,
            rh=5.0, zebra="#f4f4f4",
            align=["middle", "middle", "middle", "start", "middle", "start"])

    # ---------- bill of materials ----------
    s.text(216, 30, "BILL OF MATERIALS", 2.8, weight="bold")
    rows = [[n, tag, desc, mfr, str(qty)] for n, tag, desc, mfr, qty, note in BOM]
    s.table(216, 33, [(8, "#"), (22, "TAG"), (86, "DESCRIPTION"), (48, "TYPE / MAKE"),
                      (10, "QTY")], rows,
            rh=5.4, zebra="#f4f4f4", cell_size=1.95,
            align=["middle", "start", "start", "start", "middle"])

    s.notes(20, 222, [
        "1.  I/O count used:  16 of 16 digital inputs (0 spare),  10 of 16 digital outputs (6 spare).",
        "     The input card is full.  If any further input is needed - for example a second door switch, a per-slot",
        "     load sensor or an airflow proving switch - add an FX5-16EX/ES input extension block on the right of the",
        "     CPU; no rewiring of the existing inputs is needed.",
        "2.  Quantities in the bill of materials exclude consumables (ferrules, cable ties, glands, labels, wire).",
        "3.  Equivalent devices from another manufacturer may be substituted provided the ratings, the utilisation",
        "     category and the terminal arrangement are the same, and the substitution is recorded on the as-built.",
        "4.  All settings marked 'set to ...' on sheets 03, 04 and 09 must be recorded on the commissioning sheet.",
    ])
    return s
