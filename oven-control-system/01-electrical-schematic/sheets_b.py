"""Sheets 05-10: control supply, PLC I/O, coil circuits, instruments, HMI."""
from eplan import Sheet, LW_THIN, LW_MED, LW_THICK, LW_POWER
from data import INPUTS, OUTPUTS
from sheets_a import new


def xref(s, x, y, text, d="right", size=2.0):
    """Off-sheet cross-reference pennant."""
    if d == "right":
        s.poly([(x, y - 2.4), (x + 6, y - 2.4), (x + 9, y), (x + 6, y + 2.4), (x, y + 2.4)],
               w=LW_MED, close=True)
        s.text(x + 10.5, y + 0.8, text, size)
    else:
        s.poly([(x, y - 2.4), (x - 6, y - 2.4), (x - 9, y), (x - 6, y + 2.4), (x, y + 2.4)],
               w=LW_MED, close=True)
        s.text(x - 10.5, y + 0.8, text, size, "end")


# ===================================================================== 05
def sheet05():
    s = new("05 / 13", "CONTROL SUPPLY, EMERGENCY STOP & 24 V DC DISTRIBUTION",
            "230 V AC control circuit ex -T1  /  24 V DC ex -G1")

    LY, NY, RX = 44, 140, 300
    s.line(18, LY, RX, LY, w=LW_MED)
    s.text(16, LY - 2.2, "100", 2.2, "end", weight="bold")
    xref(s, 18, LY, "", "left")
    s.text(21, LY - 5.2, "230 V AC CONTROL SUPPLY   ex -T1 / -Q6   (SHEET 02)", 2.4, weight="bold")

    blocks = [
        (46,  "-F5", "2 A", "PLC -A1", ["MELSEC iQ-F", "FX5U-32MT/ES", "100-240 V AC"], True),
        (112, "-F6", "2 A", "-G1  SMPS", ["230 V AC in", "24 V DC 5 A out"], False),
        (176, "-F7", "1 A", "-A2  PID", ["TEMPERATURE", "CONTROLLER, 230 V AC"], False),
    ]
    for bx, ft, fr, title, lines, earthed in blocks:
        s.line(bx, LY, bx, LY + 8, w=LW_MED)
        s.dot(bx, LY)
        s.fuse(bx, LY + 8, tag=ft, sub=fr)
        s.line(bx, LY + 16, bx, 70, w=LW_MED)
        s.text(bx + 2, 68, "L", 2.0)
        s.block(bx - 22, 70, 44, 34, title=title, sub=lines, tsize=2.6)
        s.line(bx, 104, bx, NY, w=LW_MED)
        s.dot(bx, NY)
        s.text(bx + 2, 110, "N", 2.0)
        if earthed:
            s.line(bx, 112, bx + 16, 112, w=LW_MED)
            s.dot(bx, 112)
            s.earth(bx + 16, 112, size=4.5, label="PE")

    # -- SMPS DC output --
    s.line(134, 84, 142, 84, w=LW_MED)
    s.line(134, 94, 150, 94, w=LW_MED)
    s.text(136, 81, "+V", 1.9)
    s.text(136, 91, "-V", 1.9)
    s.line(142, 84, 142, 180, w=LW_MED)
    s.line(150, 94, 150, 244, w=LW_MED)
    s.hop(150, 180, vertical=True)

    s.hline_hops(NY, 18, RX, hops=(142, 150))
    s.text(16, NY - 2.2, "190", 2.2, "end", weight="bold")
    xref(s, 18, NY, "", "left")
    s.text(21, NY + 5.0, "230 V AC NEUTRAL   (secondary of -T1, earthed at the transformer)", 2.2)

    # -- control healthy lamp --
    hx = 215
    s.line(hx, LY, hx, LY + 10, w=LW_MED)
    s.dot(hx, LY)
    s.lamp(hx, LY + 10, tag="-H0")
    s.text(hx + 5, LY + 21, "CONTROL ON", 1.9)
    s.text(hx + 5, LY + 24.4, "white, 230 V", 1.9)
    s.line(hx, LY + 22, hx, NY, w=LW_MED)
    s.dot(hx, NY)

    # -- emergency stop / switched coil bus --
    ex = 255
    s.line(ex, LY, ex, LY + 8, w=LW_MED)
    s.dot(ex, LY)
    s.fuse(ex, LY + 8, tag="-F8", sub="2 A")
    s.line(ex, LY + 16, ex, LY + 24, w=LW_MED)
    s.text(ex + 2.0, LY + 22, "101", 2.0)
    s.estop(ex, LY + 24, tag="11-12")
    s.text(ex + 10, LY + 30, "-S0  EMERGENCY STOP", 2.2, weight="bold")
    s.text(ex + 10, LY + 33.6, "40 mm mushroom, twist release", 1.9)
    s.text(ex + 10, LY + 37.0, "2 x NC:  11-12 here,", 1.9)
    s.text(ex + 10, LY + 40.4, "21-22 -> PLC X0 (sheet 06)", 1.9)
    s.line(ex, LY + 32, ex, 110, w=LW_MED)
    s.text(ex + 2.0, 106, "102", 2.4, weight="bold")
    s.line(ex, 110, 300, 110, w=LW_MED)
    xref(s, 300, 110, "", "right")
    s.text(302, 107, "COIL BUS 102  ->  SHEET 08", 2.0)

    # ================= 24 V DC =================
    PY, MY = 180, 244
    s.hline_hops(PY, 18, 300, hops=(150,))
    s.line(18, MY, 300, MY, w=LW_MED)
    s.text(16, PY - 2.2, "200", 2.2, "end", weight="bold")
    s.text(16, MY - 2.2, "201", 2.2, "end", weight="bold")
    s.text(21, PY - 5.2, "+24 V DC BUS   (wire 200)", 2.4, weight="bold")
    s.text(21, MY + 5.0,
           "0 V BUS   (wire 201)  -  bonded to PE at one point only, at -X2:0V/PE", 2.2)
    s.dot(142, PY)
    s.dot(150, MY)
    s.earth(268, MY, size=5)
    s.dot(268, MY)
    s.text(274, MY + 4.6, "single-point 0 V / PE bond", 2.0)

    dcb = [
        (40,  "-F10", "1 A", "PLC -A1", "S/S and digital inputs", "SHEET 06"),
        (92,  "-F11", "2 A", "PLC -A1", "output loads -KA1..-KA3", "SHEET 07"),
        (144, "-F12", "1 A", "HMI -A3", "GT2107-WTBD", "SHEET 10"),
        (196, "-F13", "2 A", "DOOR", "lamps -H1..-H6, hooter -B4", "SHEET 07"),
        (248, "-F14", "1 A", "FIELD", "devices -B1 / -B3", "SHEET 06"),
        (290, "-F15", "2 A", "SPARE", "reserved", "-"),
    ]
    for bx, ft, fr, hd, desc, sh in dcb:
        s.line(bx, PY, bx, PY + 8, w=LW_MED)
        s.dot(bx, PY)
        s.fuse(bx, PY + 8, tag=ft, sub=fr)
        s.line(bx, PY + 16, bx, PY + 24, w=LW_MED)
        xref(s, bx - 4.5, PY + 26, "", "right")
        s.text(bx, PY + 34, hd, 2.1, "middle", weight="bold")
        s.text(bx, PY + 37.8, desc, 1.85, "middle")
        s.text(bx, PY + 41.6, sh, 1.85, "middle", style="italic")

    # ---- information blocks ----
    ix = 310
    s.dashbox(ix, 42, 90, 58, "EMERGENCY STOP - FUNCTION")
    for i, t in enumerate([
        "Operating -S0 removes 230 V from the",
        "contactor coil bus (wire 102), so -K1,",
        "-K2 and -K3 all drop out in HARDWARE,",
        "independently of the PLC.",
        "",
        "The second NC contact tells the PLC",
        "(input X0) that -S0 is operated, so the",
        "HMI can display it and the program can",
        "inhibit restart.",
        "",
        "Releasing -S0 does NOT restart anything;",
        "the blowers must be started again from",
        "the push-buttons or the HMI.",
    ]):
        s.text(ix + 3, 48 + i * 4.0, t, 2.0)

    s.dashbox(ix, 114, 90, 58, "24 V DC LOAD BUDGET")
    rows = [
        ("PLC input circuit (16 x 5 mA)", "0.08 A"),
        ("Relays -KA1..-KA3 (3 x 25 mA)", "0.08 A"),
        ("HMI -A3  GT2107-WTBD", "0.40 A"),
        ("Lamps -H1..-H6 (6 x 20 mA)", "0.12 A"),
        ("Hooter -B4", "0.05 A"),
        ("Field devices / spare", "0.30 A"),
        ("TOTAL", "1.03 A"),
        ("-G1 rated 5 A  ->  21 % loaded", "OK"),
    ]
    yy = 121
    for a, b in rows:
        bold = "bold" if a.startswith(("TOTAL", "-G1")) else "normal"
        s.text(ix + 3, yy, a, 2.0, weight=bold)
        s.text(ix + 86, yy, b, 2.0, "end", weight=bold)
        if a.startswith("TOTAL"):
            s.line(ix + 3, yy - 4.4, ix + 86, yy - 4.4, w=LW_THIN)
        yy += 6.2

    s.dashbox(ix, 186, 90, 60, "WIRE IDENTIFICATION")
    wc = [
        ("415 V AC power", "black, 2.5 / 10 mm2"),
        ("Neutral", "light blue"),
        ("Protective earth", "green / yellow"),
        ("230 V AC control", "black (red if fed from"),
        ("", "outside the main isolator)"),
        ("+24 V DC", "dark blue"),
        ("0 V DC", "dark blue with white"),
        ("", "0 V ferrule"),
        ("Interlock / signal", "orange"),
        ("All cores", "numbered ferrules both ends"),
    ]
    yy = 193
    for a_, b_ in wc:
        if a_:
            s.text(ix + 3, yy, a_, 2.0, weight="bold")
        s.text(ix + 40, yy, b_, 2.0)
        yy += 5.2

    s.notes(18, 258, [
        "1.  -F5 to -F15 are DIN-rail fuse holders with 5 x 20 mm cartridge fuses; the rating is marked beside each holder.",
        "2.  The PLC, the SMPS and the PID controller are fed UPSTREAM of the emergency stop so that they stay alive during",
        "     an E-stop; only the contactor coil bus (wire 102) is interrupted, and that is what removes power from the loads.",
        "3.  Wire crossings drawn with a semicircular hop are NOT connected.  A junction is shown by a solid dot.",
    ])
    return s


# ===================================================================== 06
def sheet06():
    s = new("06 / 13", "PLC -A1 : CPU SUPPLY & DIGITAL INPUTS X0 - X17",
            "MELSEC iQ-F  FX5U-32MT/ES  -  sink input wiring (S/S = +24 V)")

    BX, BY, BW = 24, 28, 66
    n = len(INPUTS)
    pitch = 10.0
    y0 = 52.0
    BH = y0 + (n - 1) * pitch + 8 - BY
    s.plcblock(BX, BY, BW, BH, "-A1", ["MELSEC iQ-F", "FX5U-32MT/ES",
                                       "16 DI / 16 DO", "transistor sink"])

    XT = BX + BW           # right edge of the block
    WIRE_X = XT + 22       # wire label column
    TERM_X = XT + 46       # -X1 terminal column
    DEV_X = XT + 66        # device symbol column
    RAIL_X = XT + 128      # 0 V rail
    TXT_X = RAIL_X + 12

    # S/S terminal fed from +24 V
    ss_y = 34.0
    px, _ = s.stub(XT, ss_y, "S/S")
    s.line(px, ss_y, RAIL_X + 0, ss_y, w=LW_MED)
    s.line(RAIL_X, ss_y, RAIL_X, ss_y - 6, w=LW_MED)
    xref(s, RAIL_X, ss_y - 6, "+24 V bus, wire 200, ex -F10   (SHEET 05)", "right")
    s.text(px + 3, ss_y - 1.8, "wire 200", 2.0)

    # 0 V rail
    s.line(RAIL_X, ss_y + 8, RAIL_X, y0 + (n - 1) * pitch + 8, w=LW_MED)
    s.line(RAIL_X, y0 + (n - 1) * pitch + 8, RAIL_X, y0 + (n - 1) * pitch + 14, w=LW_MED)
    xref(s, RAIL_X - 4.5, y0 + (n - 1) * pitch + 16, "", "right")
    s.text(RAIL_X + 8, y0 + (n - 1) * pitch + 17, "0 V bus, wire 201   (SHEET 05)", 2.0)

    s.text(TERM_X, 42.0, "-X1", 2.4, "middle", weight="bold")
    s.text(DEV_X - 2, 42.0, "DEVICE / CONTACT", 2.2, "end", weight="bold")
    s.text(TXT_X, 42.0, "FUNCTION", 2.2, weight="bold")
    s.text(WIRE_X, 42.0, "WIRE", 2.2, "middle", weight="bold")

    for i, (addr, wire, term, tag, sym, cref, desc, loc) in enumerate(INPUTS):
        y = y0 + i * pitch
        px, _ = s.stub(XT, y, addr)
        s.line(px, y, DEV_X, y, w=LW_MED)
        s.text(WIRE_X, y - 1.6, wire, 2.0, "middle")
        if term.strip() != "-":
            s.terminal(TERM_X, y, term, lp="above", tsize=1.9)
        else:
            s.text(TERM_X, y - 2.4, "direct", 1.8, "middle", style="italic")
        s.hsym(sym, DEV_X, y)
        s.text(DEV_X - 2, y - 1.8, tag, 2.1, "end", weight="bold")
        s.text(DEV_X - 2, y + 3.2, cref, 1.85, "end")
        s.line(DEV_X + 8, y, RAIL_X, y, w=LW_MED)
        s.dot(RAIL_X, y)
        s.text(TXT_X, y + 0.9, desc, 2.05)
        s.text(TXT_X, y + 4.0, loc, 1.8, style="italic")

    # AC supply of the CPU
    ax, ay = 296, 222
    s.text(ax, ay - 4, "-A1  CPU POWER SUPPLY", 2.4, weight="bold")
    for i, (t, w) in enumerate([("L", "100"), ("N", "190"), ("PE", "PE")]):
        yy = ay + i * 8
        s.stub(ax + 28, yy, t, side="left")
        s.line(ax + 24, yy, ax + 6, yy, w=LW_MED)
        s.text(ax + 30, yy - 2.4, w, 2.0)
        xref(s, ax + 6, yy, "", "left")
    s.text(ax + 38, ay + 2, "230 V AC ex -F5  (SHEET 05)", 2.1)
    s.text(ax + 38, ay + 6, "PE to panel earth bar -PE1", 2.1)

    s.notes(BX, 220, [
        "1.  SINK input wiring: terminal S/S is tied to +24 V.  The internal input circuit sources current out of each X",
        "     terminal; the field contact completes the circuit to 0 V.  A closed field contact = input ON.",
        "2.  Fail-safe contacts:  -S0 (E-stop), -S2 / -S4 (stop push-buttons) and -B3 (high-limit) are wired normally",
        "     CLOSED, so the PLC sees the input go OFF on a broken wire, a loose terminal or a device failure, and the",
        "     program then takes the safe action.  The PLC program must therefore treat X0, X2, X4 and X13 as ACTIVE-LOW.",
        "3.  Overload trip contacts -F1 / -F2 / -F3 (97-98) are wired normally OPEN so that the input is ON only when",
        "     that overload has actually tripped - this gives an unambiguous alarm on the HMI.",
        "4.  Contactor feedback inputs X14 / X15 / X16 let the program detect a welded or a failed-to-close contactor:",
        "     if the feedback does not agree with the commanded output within 1 s, a contactor fault alarm is raised.",
    ], w=0)
    return s


# ===================================================================== 07
def sheet07():
    s = new("07 / 13", "PLC -A1 : DIGITAL OUTPUTS Y0 - Y17",
            "MELSEC iQ-F  FX5U-32MT/ES  -  transistor SINK outputs, 24 V DC, 0.5 A per point")

    used = [o for o in OUTPUTS if o[4] != "spare"]
    BX, BY, BW = 24, 28, 66
    pitch = 11.0
    y0 = 52.0
    n = len(used)
    BH = y0 + (n - 1) * pitch + 4 + 2 * 9 + 6 - BY
    s.plcblock(BX, BY, BW, BH, "-A1", ["MELSEC iQ-F", "FX5U-32MT/ES",
                                       "16 DI / 16 DO", "transistor sink"])

    XT = BX + BW
    WIRE_X = XT + 20
    TERM_X = XT + 42
    LOAD_X = XT + 62
    RAIL_X = XT + 130
    TXT_X = RAIL_X + 12

    # +24 V rail on the right
    s.line(RAIL_X, 46, RAIL_X, y0 + (n - 1) * pitch + 4, w=LW_MED)
    s.line(RAIL_X, 46, RAIL_X, 36, w=LW_MED)
    xref(s, RAIL_X, 36, "+24 V bus, wire 200, ex -F11 / -F13   (SHEET 05)", "right")

    s.text(TERM_X, 42.0, "-X1", 2.4, "middle", weight="bold")
    s.text(LOAD_X - 2, 42.0, "DEVICE", 2.2, "end", weight="bold")
    s.text(LOAD_X + 6, 42.0, "LOAD", 2.2, "middle", weight="bold")
    s.text(WIRE_X, 42.0, "WIRE", 2.2, "middle", weight="bold")
    s.text(TXT_X, 42.0, "FUNCTION", 2.2, weight="bold")

    for i, (addr, wire, term, tag, kind, colr, desc) in enumerate(used):
        y = y0 + i * pitch
        px, _ = s.stub(XT, y, addr)
        s.line(px, y, LOAD_X, y, w=LW_MED)
        s.text(WIRE_X, y - 1.6, wire, 2.0, "middle")
        if term != "-":
            s.terminal(TERM_X, y, term, lp="above", tsize=1.9)
        else:
            s.text(TERM_X, y - 2.4, "direct", 1.8, "middle", style="italic")
        s.hload(kind, LOAD_X, y)
        s.text(LOAD_X - 2, y - 1.8, tag, 2.1, "end", weight="bold")
        if colr:
            s.text(LOAD_X + 15, y - 1.8, colr, 1.85, "start")
        s.line(LOAD_X + 12, y, RAIL_X, y, w=LW_MED)
        s.dot(RAIL_X, y)
        s.text(TXT_X, y + 0.9, desc, 2.05)

    # commons
    for i, t in enumerate(["COM0", "COM1"]):
        yy = y0 + n * pitch + 4 + i * 9
        px, _ = s.stub(XT, yy, t)
        s.line(px, yy, RAIL_X - 14, yy, w=LW_MED)
        s.line(RAIL_X - 14, yy, RAIL_X - 14, y0 + n * pitch + 22, w=LW_MED)
        s.text(px + 3, yy - 1.8, "wire 201", 2.0)
    s.line(RAIL_X - 14, y0 + n * pitch + 22, RAIL_X - 14, y0 + n * pitch + 28, w=LW_MED)
    xref(s, RAIL_X - 18.5, y0 + n * pitch + 30, "", "right")
    s.text(RAIL_X - 6, y0 + n * pitch + 31, "0 V bus, wire 201  (SHEET 05)", 2.0)

    # spare outputs note
    sx = 300
    s.dashbox(sx, 186, 100, 30, "SPARE OUTPUTS")
    s.text(sx + 3, 194, "Y12, Y13, Y14, Y15, Y16, Y17 are not used.", 2.0)
    s.text(sx + 3, 198, "Terminals are wired out to -X1:70...-X1:73 so", 2.0)
    s.text(sx + 3, 202, "that four of them can be commissioned later", 2.0)
    s.text(sx + 3, 206, "without opening the PLC wiring - e.g. per-slot", 2.0)
    s.text(sx + 3, 210, "indication lamps for the six oven slots.", 2.0)

    s.notes(BX, 226, [
        "1.  Outputs are transistor SINK type.  The load is connected between +24 V (wire 200) and the Y terminal; the",
        "     output transistor completes the circuit to 0 V through COM0 / COM1.  Never connect a load between a Y",
        "     terminal and 0 V - it will be permanently energised.",
        "2.  Each output point is rated 0.5 A; each common group is rated 0.8 A total.  The loads used here (relay coils",
        "     25 mA, LED lamps 20 mA, hooter 50 mA) are well inside both limits.",
        "3.  Interposing relays -KA1 / -KA2 / -KA3 have an integral free-wheel diode fitted across the coil.  Where a",
        "     socket-mounted relay without a diode is used, fit a 1N4007 across A1 (+) / A2 (-) to protect the output.",
        "4.  Contactor coils are 230 V AC and are NOT driven directly from the PLC - see sheet 08.",
        "5.  -H5 COMMON ALARM is flashed by the program (1 s on / 1 s off) while an alarm is unacknowledged and is",
        "     steady once accepted with -S5.  The hooter -B4 silences on -S5 but the lamp stays on until the cause clears.",
    ], w=0)
    return s


# ===================================================================== 08
def sheet08():
    s = new("08 / 13", "CONTACTOR COIL CIRCUITS & DOOR-INTERLOCK PROVISION",
            "230 V AC coil circuits fed from the switched coil bus, wire 102")

    LY, NY, RX = 46, 178, 300
    s.line(18, LY, RX, LY, w=LW_MED)
    s.line(18, NY, RX, NY, w=LW_MED)
    s.text(16, LY - 2.2, "102", 2.4, "end", weight="bold")
    s.text(16, NY - 2.2, "190", 2.4, "end", weight="bold")
    xref(s, 18, LY, "", "left")
    xref(s, 18, NY, "", "left")
    s.text(21, LY - 5.2, "SWITCHED COIL BUS, wire 102   (downstream of -S0 EMERGENCY STOP, SHEET 05)",
           2.4, weight="bold")
    s.text(21, NY + 5.0, "230 V AC NEUTRAL, wire 190   (SHEET 05)", 2.2)

    # ---------- door-interlock provision ----------
    lx = 60
    s.line(lx, LY, lx, LY + 8, w=LW_MED)
    s.dot(lx, LY)
    s.terminal(lx, LY + 8, "60", lp="left", tsize=2.0)
    s.line(lx, LY + 9.3, lx, LY + 14, w=LW_MED)
    # the link itself
    s.line(lx - 3.2, LY + 14, lx + 3.2, LY + 14, w=LW_THICK)
    s.line(lx - 3.2, LY + 14, lx - 3.2, LY + 17, w=LW_THICK)
    s.line(lx + 3.2, LY + 14, lx + 3.2, LY + 17, w=LW_THICK)
    s.line(lx, LY + 17, lx, LY + 20, w=LW_MED)
    s.line(lx - 3.2, LY + 17, lx + 3.2, LY + 17, w=LW_THICK)
    s.text(lx + 6, LY + 16, "-LK1  LINK FITTED", 2.2, weight="bold")
    s.terminal(lx, LY + 21.3, "61", lp="left", tsize=2.0)
    s.line(lx, LY + 22.6, lx, LY + 30, w=LW_MED)
    s.text(lx + 3, LY + 28, "103", 2.2, weight="bold")
    s.text(lx + 6, LY + 20, "-X1:60 / -X1:61", 2.0)

    # 103 bus
    s.line(lx, LY + 30, 200, LY + 30, w=LW_MED)
    s.text(205, LY + 31, "BLOWER COIL BUS, wire 103", 2.2, weight="bold")

    rungs = [
        (100, "-KA1", "13-14", "110", "-F1", "95-96", "111", None, None, None,
         "-K1", "BLOWER 1 CONTACTOR", "9 A AC-3, 230 V coil"),
        (160, "-KA2", "13-14", "120", "-F2", "95-96", "121", None, None, None,
         "-K2", "BLOWER 2 CONTACTOR", "9 A AC-3, 230 V coil"),
    ]
    for rx, ka, kac, w1, ol, olc, w2, _a, _b, _c, kt, kd, ks in rungs:
        s.line(rx, LY + 30, rx, LY + 38, w=LW_MED)
        s.dot(rx, LY + 30)
        s.c_no(rx, LY + 38, tag=kac)
        s.text(rx - 2, LY + 42.6, ka, 2.2, "end", weight="bold")
        s.line(rx, LY + 46, rx, LY + 56, w=LW_MED)
        s.text(rx + 2, LY + 53, w1, 2.0)
        s.c_nc(rx, LY + 56, tag=olc)
        s.text(rx - 2, LY + 60.6, ol, 2.2, "end", weight="bold")
        s.line(rx, LY + 64, rx, LY + 74, w=LW_MED)
        s.text(rx + 2, LY + 71, w2, 2.0)
        s.coil(rx, LY + 74, tag=kt, sub=[kd, ks])
        s.line(rx, LY + 86, rx, NY, w=LW_MED)
        s.dot(rx, NY)

    # ---------- heater rung ----------
    hx = 250
    s.line(hx, LY, hx, LY + 8, w=LW_MED)
    s.dot(hx, LY)
    s.c_no(hx, LY + 8, tag="13-14")
    s.text(hx - 2, LY + 12.6, "-KA3", 2.2, "end", weight="bold")
    s.line(hx, LY + 16, hx, LY + 24, w=LW_MED)
    s.text(hx + 2, LY + 22, "130", 2.0)
    s.c_nc(hx, LY + 24, tag="95-96")
    s.text(hx - 2, LY + 28.6, "-F3", 2.2, "end", weight="bold")
    s.line(hx, LY + 32, hx, LY + 40, w=LW_MED)
    s.text(hx + 2, LY + 38, "131", 2.0)
    s.terminal(hx, LY + 40, "03", lp="left", tsize=2.0)
    s.line(hx, LY + 41.3, hx, LY + 46, w=LW_MED)
    s.c_nc(hx, LY + 46, tag="C1", tag_dx=-2.0)
    s.text(hx + 8, LY + 47, "-B3  HIGH-LIMIT THERMOSTAT", 2.1, weight="bold")
    s.text(hx + 8, LY + 50.4, "manual reset, contact C1 of 2", 1.9)
    s.text(hx + 8, LY + 53.8, "contact C2 -> PLC X13 (sheet 09)", 1.9)
    s.line(hx, LY + 54, hx, LY + 60, w=LW_MED)
    s.terminal(hx, LY + 60, "04", lp="left", tsize=2.0)
    s.line(hx, LY + 61.3, hx, LY + 70, w=LW_MED)
    s.text(hx + 2, LY + 68, "132", 2.0)
    s.coil(hx, LY + 70, tag="-K3", sub=["HEATER CONTACTOR", "40 A AC-1, 230 V coil"])
    s.line(hx, LY + 82, hx, NY, w=LW_MED)
    s.dot(hx, NY)

    # ---------- explanation blocks ----------
    ix = 312
    s.dashbox(ix, 42, 88, 92, "HOW EACH COIL IS ENERGISED")
    txt = [
        ("-K1 / -K2  (blowers)", True),
        ("102 present (E-stop released)", False),
        ("AND -LK1 fitted (or the future door", False),
        ("      switch closed)", False),
        ("AND PLC output Y0 / Y1 ON", False),
        ("AND that overload not tripped", False),
        ("", False),
        ("-K3  (heater)", True),
        ("102 present (E-stop released)", False),
        ("AND PLC output Y2 ON", False),
        ("AND -F3 not tripped", False),
        ("AND -B3 high-limit not tripped", False),
        ("", False),
        ("The door interlock acts on Y0 / Y1", False),
        ("in the PLC program only - it is NOT", False),
        ("in the -K3 chain, so the heater stays", False),
        ("ON while the door is open.", False),
    ]
    yy = 49
    for t, b in txt:
        s.text(ix + 3, yy, t, 2.05, weight="bold" if b else "normal")
        yy += 4.0 if t else 2.4

    s.dashbox(ix, 144, 88, 76, "-LK1  UPGRADE TO A HARD-WIRED INTERLOCK")
    up = [
        "As instructed, the door switch -B1 goes to",
        "PLC input X5 only and the blowers are",
        "stopped by the program.  The wire link",
        "-LK1 between -X1:60 and -X1:61 keeps the",
        "blower coil bus permanently made.",
        "",
        "To convert to a hard-wired interlock later:",
        "",
        "1.  Remove the link -LK1.",
        "2.  Land the NC contact of a second",
        "     (safety-rated) door switch -B1.2 on",
        "     -X1:60 and -X1:61.",
        "3.  No other panel change is needed;",
        "     X5 keeps working for the counters",
        "     and the HMI status.",
    ]
    yy = 151
    for t in up:
        s.text(ix + 3, yy, t, 2.05)
        yy += 4.4 if t else 2.2

    s.notes(18, 200, [
        "1.  Interposing relays -KA1 / -KA2 / -KA3 have 24 V DC coils driven from PLC outputs Y0 / Y1 / Y2 (sheet 07).",
        "     Their volt-free 13-14 contacts switch the 230 V AC contactor coils shown here, so the PLC never carries",
        "     230 V and the coil circuit stays independent of the PLC output stage.",
        "2.  Overload contacts -F1 / -F2 / -F3 (95-96) are in the coil circuits, so an overload trip drops its contactor in",
        "     HARDWARE.  The 97-98 contact of the same relay tells the PLC which overload tripped (sheet 06).",
        "3.  -B3 contact C1 is in the -K3 coil circuit only.  An over-temperature therefore removes the heater without",
        "     any involvement of the PLC or the PID controller.  Contact C2 reports the same event to PLC input X13.",
        "4.  Contactor auxiliary contacts 13-14 of -K1 / -K2 / -K3 report back to PLC inputs X14 / X15 / X16 so the",
        "     program can detect a welded contactor or one that failed to pull in.",
        "5.  Fit an RC suppressor across the coil of -K3 to limit the switching transient seen by -KA3.",
    ])
    return s


# ===================================================================== 09
def sheet09():
    s = new("09 / 13", "TEMPERATURE CONTROLLER, THERMOCOUPLE & OVER-TEMPERATURE PROTECTION",
            "-A2 PID controller, -B2 type K thermocouple, -B3 independent high-limit thermostat")

    # ---------- PID controller ----------
    BX, BY, BW, BH = 96, 44, 66, 104
    s.plcblock(BX, BY, BW, BH, "-A2", ["PID TEMPERATURE", "CONTROLLER", "96 x 96 DIN",
                                       "universal input", "relay OUT1 + AL1"])
    # supply
    s.stub(BX, BY + 84, "1  L", side="left")
    s.stub(BX, BY + 94, "2  N", side="left")
    for i, (t, w) in enumerate([("L", "100"), ("N", "190")]):
        yy = BY + 84 + i * 10
        s.line(BX - 4, yy, BX - 34, yy, w=LW_MED)
        xref(s, BX - 34, yy, "", "left")
        s.text(BX - 32, yy - 2.2, w, 2.0)
    s.text(BX - 66, BY + 78, "230 V AC ex -F7", 2.1, weight="bold")
    s.text(BX - 66, BY + 100, "(SHEET 05)", 2.0)

    # thermocouple input
    s.stub(BX, BY + 20, "11 +", side="left")
    s.stub(BX, BY + 30, "12 -", side="left")
    s.line(BX - 4, BY + 20, BX - 30, BY + 20, w=LW_MED)
    s.line(BX - 4, BY + 30, BX - 30, BY + 30, w=LW_MED)
    s.terminal(BX - 30, BY + 20, "07", lp="above", tsize=1.9)
    s.terminal(BX - 30, BY + 30, "08", lp="below", tsize=1.9)
    s.text(BX - 30, BY + 10, "-X1", 2.4, "middle", weight="bold")
    tcx, tcy = BX - 62, BY + 46
    s.line(BX - 30, BY + 20, tcx - 3, BY + 20, w=LW_MED)
    s.line(tcx - 3, BY + 20, tcx - 3, tcy, w=LW_MED)
    s.line(BX - 30, BY + 30, tcx + 3, BY + 30, w=LW_MED)
    s.line(tcx + 3, BY + 30, tcx + 3, tcy, w=LW_MED)
    s.thermocouple(tcx, tcy)
    s.text(tcx + 6, tcy + 10, "-B2", 2.4, "start", weight="bold")
    s.text(tcx + 6, tcy + 14, "thermocouple type K", 2.0)
    s.text(tcx + 6, tcy + 17.4, "6 x 300 mm, Inconel sheath", 2.0)
    s.text(tcx + 6, tcy + 20.8, "in the oven chamber", 2.0)
    # screen
    s.line(BX - 46, BY + 30, BX - 46, BY + 40, w=LW_MED, dash="1.2,1.2")
    s.terminal(BX - 46, BY + 40, "09", lp="right", tsize=1.9)
    s.earth(BX - 46, BY + 42, size=4.5)
    s.text(BX - 40, BY + 48, "screen earthed at the panel end only", 2.0)
    s.text(BX - 52, BY + 12, "compensating cable", 2.0, "middle")
    s.text(BX - 52, BY + 15.4, "type KX, screened", 2.0, "middle")

    # outputs
    RX = BX + BW
    s.stub(RX, BY + 20, "13", side="right")
    s.stub(RX, BY + 26, "14", side="right")
    s.text(RX + 8, BY + 16, "OUT1  relay, heat demand", 2.1, weight="bold")
    s.line(RX + 4, BY + 20, RX + 30, BY + 20, w=LW_MED)
    s.line(RX + 4, BY + 26, RX + 30, BY + 26, w=LW_MED)
    s.line(RX + 30, BY + 20, RX + 30, BY + 26, w=LW_MED)
    s.line(RX + 30, BY + 23, RX + 46, BY + 23, w=LW_MED)
    s.terminal(RX + 46, BY + 23, "30", lp="above", tsize=1.9)
    s.line(RX + 46, BY + 23, RX + 70, BY + 23, w=LW_MED)
    xref(s, RX + 70, BY + 23, "PLC INPUT X6   (SHEET 06)", "right")
    s.text(RX + 32, BY + 30, "wire 226", 2.0)

    s.stub(RX, BY + 44, "15", side="right")
    s.stub(RX, BY + 50, "16", side="right")
    s.text(RX + 8, BY + 40, "AL1  relay, alarm / sensor break", 2.1, weight="bold")
    s.line(RX + 4, BY + 44, RX + 30, BY + 44, w=LW_MED)
    s.line(RX + 4, BY + 50, RX + 30, BY + 50, w=LW_MED)
    s.line(RX + 30, BY + 44, RX + 30, BY + 50, w=LW_MED)
    s.line(RX + 30, BY + 47, RX + 46, BY + 47, w=LW_MED)
    s.terminal(RX + 46, BY + 47, "31", lp="above", tsize=1.9)
    s.line(RX + 46, BY + 47, RX + 70, BY + 47, w=LW_MED)
    xref(s, RX + 70, BY + 47, "PLC INPUT X7   (SHEET 06)", "right")
    s.text(RX + 32, BY + 54, "wire 227", 2.0)

    # optional analogue retransmission
    s.dashbox(RX + 6, BY + 66, 130, 34, "OPTIONAL - PROCESS VALUE TO THE HMI TREND")
    s.text(RX + 9, BY + 74, "Fit -A2 with a 4-20 mA retransmission output (terminals 17 / 18)", 2.0)
    s.text(RX + 9, BY + 78, "and an FX5-4AD-ADP analogue adapter on the left of the CPU.", 2.0)
    s.text(RX + 9, BY + 82, "Wire 17 (+) -> CH1 V+/I+, 18 (-) -> CH1 COM, screened twisted pair.", 2.0)
    s.text(RX + 9, BY + 86, "This gives a live temperature trend and a numeric PV on the HMI;", 2.0)
    s.text(RX + 9, BY + 90, "it is NOT required for any of the control or alarm functions, which", 2.0)
    s.text(RX + 9, BY + 94, "all work from the volt-free demand contact on X6.", 2.0)

    # ---------- high-limit thermostat ----------
    HY = 170
    s.plcblock(96, HY, 66, 52, "-B3", ["SAFETY HIGH-LIMIT", "THERMOSTAT", "2 x NC, manual reset",
                                       "independent sensor"])
    s.stub(96, HY + 24, "C1", side="left")
    s.stub(96, HY + 34, "C2", side="left")
    s.line(92, HY + 24, 66, HY + 24, w=LW_MED)
    xref(s, 66, HY + 24, "", "left")
    s.text(64, HY + 21, "-K3 COIL CIRCUIT, wires 131 / 132   (SHEET 08)", 2.05, "end")
    s.line(92, HY + 34, 66, HY + 34, w=LW_MED)
    xref(s, 66, HY + 34, "", "left")
    s.text(64, HY + 31, "PLC INPUT X13, wire 231   (SHEET 06)", 2.05, "end")
    s.thermocouple(180, HY + 8, tag="-B3 sensor", sub=["capillary / RTD, mounted in the", "oven chamber, separate from -B2"])
    s.line(162, HY + 16, 180, HY + 16, w=LW_MED)
    s.line(180, HY + 8, 180, HY + 16, w=LW_MED)

    # ---------- settings table ----------
    tx, ty = 250, 156
    s.text(tx, ty - 3, "COMMISSIONING SETTINGS", 2.6, weight="bold")
    rows = [
        ["-A2  input type", "K thermocouple, 0 - 400 C"],
        ["-A2  SV (set point)", "as per product recipe (e.g. 180 C)"],
        ["-A2  control action", "reverse (heating), PID"],
        ["-A2  OUT1 cycle time", "20 s minimum  (see sheet 04, NOTE 6)"],
        ["-A2  AL1 type", "process high + sensor break, contact NC"],
        ["-A2  AL1 setting", "SV + 15 C"],
        ["-B3  trip setting", "SV + 30 C, or 250 C, whichever is lower"],
        ["-B3  reset", "manual, at the panel, after investigation"],
        ["PLC  heat-up watchdog", "60 min, adjustable 10 - 240 min on the HMI"],
    ]
    s.table(tx, ty, [(44, "PARAMETER"), (104, "SETTING")], rows, rh=5.6, zebra="#f4f4f4")

    s.notes(18, 236, [
        "1.  -A2 keeps full local control of the process temperature.  The PLC does not compute the temperature loop; it",
        "     simply repeats the controller's demand contact to the heater contactor and adds the permissives and alarms.",
        "2.  The demand contact on X6 is volt-free.  If the controller supplied is an SSR-drive (12 V DC pulse) type instead",
        "     of a relay type, fit an interposing relay -KA5 (12 V DC coil) and take its NO contact to X6 - the PLC program",
        "     is unchanged.",
        "3.  -B2 and the -B3 sensor must be separate sensing elements in separate pockets.  A single shared sensor would",
        "     defeat the whole purpose of the independent over-temperature layer.",
        "4.  Heat-up watchdog: the PLC starts a timer when the demand contact X6 closes.  If X6 stays closed continuously",
        "     for longer than the watchdog time - i.e. the controller never gets to set point and drops out - the alarm",
        "     'FAILURE TO REACH SETPOINT' is raised on the HMI and the hooter sounds.  The heater is not tripped by this",
        "     alarm; it is an operator warning, since the real protection against over-temperature is -B3.",
    ])
    return s


# ===================================================================== 10
def sheet10():
    s = new("10 / 13", "HMI -A3, ETHERNET NETWORK & PANEL DOOR ARRANGEMENT",
            "GOT2000 GT2107-WTBD  <->  MELSEC iQ-F FX5U-32MT/ES, 100BASE-TX")

    # ---------- network ----------
    s.plcblock(30, 44, 62, 46, "-A1", ["FX5U-32MT/ES", "built-in Ethernet"])
    s.plcblock(180, 44, 62, 46, "-A3", ["GT2107-WTBD", "7\" TFT 800 x 480"])
    s.stub(92, 62, "ETH", side="right")
    s.stub(180, 62, "ETH", side="left")
    s.line(96, 62, 176, 62, w=LW_THICK)
    s.text(136, 58, "-W5  CAT5e SF/UTP patch cord, 1 m, RJ45", 2.1, "middle")
    s.text(136, 66, "MELSOFT connection, 100BASE-TX", 2.0, "middle")

    # power
    for bx, tag in [(30, "-A1"), (180, "-A3")]:
        s.stub(bx + 31, 90, "24 V" if bx == 180 else "L / N", side="bottom")
        s.line(bx + 31, 94, bx + 31, 106, w=LW_MED)
        xref(s, bx + 26.5, 106, "", "right")
    s.text(61, 114, "230 V AC ex -F5", 2.0, "middle")
    s.text(61, 117.6, "(SHEET 05)", 2.0, "middle")
    s.text(211, 114, "24 V DC ex -F12, wires 200 / 201", 2.0, "middle")
    s.text(211, 117.6, "(SHEET 05)", 2.0, "middle")

    # USB note
    s.stub(222, 90, "USB", side="bottom")
    s.line(222, 94, 222, 104, w=LW_MED, dash="1.5,1.5")
    s.line(222, 104, 250, 104, w=LW_MED, dash="1.5,1.5")
    s.text(252, 105, "USB device port - project transfer and", 2.0)
    s.text(252, 108.4, "operation-log export to a USB stick", 2.0)

    # ---------- addressing ----------
    s.text(268, 46, "NETWORK ADDRESSING", 2.6, weight="bold")
    s.table(268, 50, [(34, "DEVICE"), (44, "IP ADDRESS"), (54, "NOTES")], [
        ["-A1  FX5U", "192.168.3.250", "built-in port, default"],
        ["-A3  GT2107", "192.168.3.18", "GOT default"],
        ["Engineering PC", "192.168.3.10", "GX Works3 / GT Designer3"],
        ["Subnet mask", "255.255.255.0", "-"],
        ["Gateway", "not used", "isolated machine network"],
    ], rh=5.4, zebra="#f4f4f4")

    # ---------- door arrangement ----------
    DX, DY, DW, DH = 30, 140, 210, 132
    s.text(DX, DY - 4, "PANEL DOOR - EXTERNAL ARRANGEMENT  (view on front, 800 x 600 mm door)",
           2.6, weight="bold")
    s.rect(DX, DY, DW, DH, lw=LW_THICK)
    s.rect(DX + 3, DY + 3, DW - 6, DH - 6, lw=LW_THIN, dash="2,2")

    # HMI
    s.rect(DX + 12, DY + 12, 78, 52, lw=LW_MED)
    s.rect(DX + 16, DY + 16, 70, 40, lw=LW_THIN)
    s.text(DX + 51, DY + 34, "HMI -A3", 3.0, "middle", weight="bold")
    s.text(DX + 51, DY + 39, "GT2107-WTBD  7\"", 2.1, "middle")
    s.text(DX + 51, DY + 43.4, "cut-out 152 x 117 mm", 1.9, "middle")

    # PID controller
    s.rect(DX + 104, DY + 12, 34, 34, lw=LW_MED)
    s.text(DX + 121, DY + 26, "-A2", 2.6, "middle", weight="bold")
    s.text(DX + 121, DY + 31, "PID", 2.2, "middle")
    s.text(DX + 121, DY + 36, "96 x 96", 1.9, "middle")
    s.text(DX + 121, DY + 42, "cut-out 92 x 92", 1.8, "middle")

    # E-stop
    s.circle(DX + 168, DY + 28, 12, lw=LW_THICK)
    s.circle(DX + 168, DY + 28, 8, lw=LW_MED)
    s.text(DX + 168, DY + 29, "-S0", 2.4, "middle", weight="bold")
    s.text(DX + 168, DY + 46, "EMERGENCY", 2.0, "middle", weight="bold")
    s.text(DX + 168, DY + 49.6, "STOP", 2.0, "middle", weight="bold")

    # lamps row
    lamps = [("-H1", "BLOWER 1", "RUNNING", "GN"), ("-H2", "BLOWER 2", "RUNNING", "GN"),
             ("-H3", "HEATER", "ON", "RD"), ("-H4", "DOOR", "OPEN", "AM"),
             ("-H5", "COMMON", "ALARM", "RD"), ("-H6", "CYCLE", "RUNNING", "WH")]
    for i, (t, l1, l2, c) in enumerate(lamps):
        cx = DX + 22 + i * 30
        s.circle(cx, DY + 78, 5.0, lw=LW_MED)
        s.text(cx, DY + 79, c, 2.0, "middle", weight="bold")
        s.text(cx, DY + 87, t, 2.0, "middle", weight="bold")
        s.text(cx, DY + 90.6, l1, 1.8, "middle")
        s.text(cx, DY + 93.6, l2, 1.8, "middle")

    # push-buttons row
    pbs = [("-S1", "BL 1", "START", "GN"), ("-S2", "BL 1", "STOP", "RD"),
           ("-S3", "BL 2", "START", "GN"), ("-S4", "BL 2", "STOP", "RD"),
           ("-S5", "LAMP TEST", "ALARM ACC.", "BL")]
    for i, (t, l1, l2, c) in enumerate(pbs):
        cx = DX + 22 + i * 30
        s.circle(cx, DY + 108, 5.5, lw=LW_MED)
        s.text(cx, DY + 109, c, 2.0, "middle", weight="bold")
        s.text(cx, DY + 117, t, 2.0, "middle", weight="bold")
        s.text(cx, DY + 120.6, l1, 1.8, "middle")
        s.text(cx, DY + 123.6, l2, 1.8, "middle")
    # hooter
    s.circle(DX + 178, DY + 108, 7.0, lw=LW_MED)
    s.text(DX + 178, DY + 109, "-B4", 2.0, "middle", weight="bold")
    s.text(DX + 178, DY + 119, "HOOTER", 1.9, "middle")

    # ---------- HMI screen list ----------
    sx = 268
    s.text(sx, 96, "HMI SCREEN STRUCTURE  (see the HMI project for detail)", 2.6, weight="bold")
    scr = [
        ["B-1000", "HOME / OVERVIEW", "0"],
        ["B-1100", "SLOT TIMERS 1-6", "0"],
        ["B-1200", "COUNTERS - door, lots", "0"],
        ["B-1300", "ALARMS - live & history", "0"],
        ["B-1400", "MANUAL TEST - blowers, heater", "2"],
        ["B-1500", "SETTINGS - watchdog, presets", "1"],
        ["B-1600", "PASSWORD / LOGIN", "0"],
        ["B-1700", "TIMER EARLY RESET", "2"],
        ["B-1800", "COUNTER RESET", "1"],
    ]
    s.table(sx, 100, [(24, "SCREEN"), (76, "TITLE"), (32, "SEC. LEVEL")], scr,
            rh=5.2, zebra="#f4f4f4", align=["start", "start", "middle"])
    s.text(sx, 162, "Security level 0 = operator (no login),  1 = supervisor,", 2.0)
    s.text(sx, 165.6, "2 = maintenance technician (password protected).", 2.0)

    s.notes(268, 178, [
        "1.  The HMI is powered from -F12 and is NOT",
        "     interrupted by the emergency stop, so",
        "     alarms and the timer values stay visible.",
        "2.  Slot timer values, counters and the alarm",
        "     history are held in PLC latched memory",
        "     (see the PLC program device list), not in",
        "     the HMI, so they survive a power failure",
        "     and an HMI replacement.",
        "3.  The GOT battery (GT11-50BAT) is fitted for",
        "     the real-time clock used by the alarm and",
        "     the operation-log time stamps.",
        "4.  Door cut-outs to be made before painting;",
        "     use the gaskets supplied to keep IP54.",
    ], title="NOTES:")
    return s
