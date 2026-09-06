"""Sheets 01-04: cover/legend, single line diagram, blower power, heater power."""
from eplan import Sheet, LW_THIN, LW_MED, LW_THICK, LW_POWER

DWG = "OVN-2026-01"


def new(num, title, sub=None):
    s = Sheet(num, title, DWG, rev="2")
    s.frame()
    s.header(sub)
    return s


# ===================================================================== 01
def sheet01():
    s = new("01 / 13", "COVER SHEET, DRAWING INDEX & LEGEND",
            "Electric batch oven - 18 kW heater bank, 2 x recirculation blowers, "
            "PLC / HMI control retrofit")

    # ---------------- design basis ----------------
    x, y = 16, 27
    s.text(x, y, "1.  DESIGN BASIS", 3.0, weight="bold")
    s.line(x, y + 1.6, x + 128, y + 1.6, w=LW_THIN)
    basis = [
        ("Incoming supply", "415 V AC, 3-phase + N + PE, 50 Hz, TN-S"),
        ("Prospective Isc", "10 kA rms sym. at panel incomer"),
        ("Control supply", "230 V AC ex 500 VA control transformer -T1"),
        ("DC supply", "24 V DC, 5 A regulated SMPS -G1"),
        ("Heater load", "18 kW total - 3 x 6 kW elements, star, 25 A/ph"),
        ("Blower load", "2 x 1.5 kW, 415 V, 3-ph, 3.5 A FLC, DOL start"),
        ("Heater switching", "Contactor -K3, driven from PLC output Y2"),
        ("Temp. control", "Panel PID controller -A2, relay output OUT1"),
        ("", "wired as a volt-free signal to PLC input X6"),
        ("Over-temperature", "Independent high-limit thermostat -B3 wired"),
        ("", "directly in the -K3 coil circuit (hard-wired trip)"),
        ("Door interlock", "Position switch -B1 to PLC input X5 only"),
        ("", "(software stop of blowers - see NOTE 4)"),
        ("PLC", "MELSEC iQ-F  FX5U-32MT/ES  (16 DI / 16 DO, sink)"),
        ("HMI", "GOT2000  GT2107-WTBD  7\" TFT, 24 V DC, Ethernet"),
        ("PLC <-> HMI link", "Ethernet 100BASE-TX, MELSOFT connection"),
        ("Door watchdog", "Chatter or no 'door closed' signal for 10 min"),
        ("", "-> alarm + volt-free output Y12 / -KA4"),
        ("Data logging", "FX5U SD card, 7-day rolling history, CSV"),
        ("Enclosure", "Wall-mounted 800 x 600 x 250 mm, IP54, RAL 7035"),
        ("Standards", "IEC 60204-1, IEC 61439-1/-2, IS 8623"),
    ]
    yy = y + 6.4
    for k, v in basis:
        if k:
            s.text(x + 1, yy, k, 2.1, weight="bold")
        s.text(x + 34, yy, v, 2.1)
        yy += 3.9

    # ---------------- functional summary ----------------
    yy += 3.0
    s.text(x, yy, "2.  CONTROL FUNCTIONS IMPLEMENTED IN THE PLC", 3.0, weight="bold")
    s.line(x, yy + 1.6, x + 128, yy + 1.6, w=LW_THIN)
    yy += 6.4
    funcs = [
        "a)  Blower 1 / Blower 2 start-stop from panel push-buttons and from the HMI.",
        "b)  Door interlock: blowers stop while the door is open, heater stays ON;",
        "     blowers restart automatically when the door is closed again.",
        "c)  Heater contactor -K3 follows the PID controller demand signal (X6),",
        "     gated by PLC permissives (E-stop, overloads, high-limit, no fault).",
        "d)  Heat-up watchdog alarm: the demand contact X6 stays closed continuously",
        "     for longer than the preset time, i.e. the oven never reaches set point",
        "     and the controller never drops out  =>  'FAILURE TO REACH SETPOINT'.",
        "e)  Door-signal watchdog: a chattering door switch, or no 'door closed'",
        "     signal for 10 minutes, raises an alarm and energises the volt-free",
        "     remote alarm output Y12 / -KA4 on terminals -X1:50 / -X1:51.",
        "f)  Six independent retentive 2-hour slot timers (slot 1...6). Once started",
        "     a timer runs to 02:00:00 and can only then be reset. An earlier reset",
        "     needs the maintenance password (HMI security level 2).",
        "g)  Door open / door close event counters, separate and resettable.",
        "h)  Lots loaded / lots unloaded counters derived from slot-timer start and",
        "     reset events, with a mismatch indication.",
        "i)  Password-protected manual test of the blowers and the heater (level 2).",
        "j)  Alarm and event history logged to the FX5U SD card, 7 days rolling,",
        "     exportable to a USB stick from the HMI.",
    ]
    for f in funcs:
        ind = (len(f) - len(f.lstrip())) * 0.85
        s.text(x + 1 + ind, yy, f.strip(), 2.1)
        yy += 3.7

    # ---------------- drawing index ----------------
    ix, iy = 152, 27
    s.text(ix, iy, "3.  DRAWING INDEX", 3.0, weight="bold")
    s.line(ix, iy + 1.6, ix + 116, iy + 1.6, w=LW_THIN)
    rows = [
        ["01", DWG + "-01", "Cover sheet, drawing index & legend"],
        ["02", DWG + "-02", "Single line diagram - power distribution"],
        ["03", DWG + "-03", "Power circuit - blower motors -M1 / -M2"],
        ["04", DWG + "-04", "Power circuit - heater bank -E1/-E2/-E3"],
        ["05", DWG + "-05", "Control supply, E-stop & 24 V DC distribution"],
        ["06", DWG + "-06", "PLC -A1 : CPU supply & digital inputs X0-X17"],
        ["07", DWG + "-07", "PLC -A1 : digital outputs Y0-Y17"],
        ["08", DWG + "-08", "Contactor coil circuits & interlock provision"],
        ["09", DWG + "-09", "Temperature controller & over-temp protection"],
        ["10", DWG + "-10", "HMI -A3, Ethernet network & door layout"],
        ["11", DWG + "-11", "Panel general arrangement & gland plate"],
        ["12", DWG + "-12", "Terminal strip schedule -X1 / -X2"],
        ["13", DWG + "-13", "I/O schedule & bill of materials"],
    ]
    s.table(ix, iy + 4.0, [(13, "SH."), (33, "DRAWING No."), (70, "TITLE")], rows,
            rh=5.2, zebra="#f4f4f4")

    # ---------------- legend ----------------
    lx, ly = 280, 27
    s.text(lx, ly, "4.  LEGEND (IEC 60617)", 3.0, weight="bold")
    s.line(lx, ly + 1.6, lx + 122, ly + 1.6, w=LW_THIN)

    col = [(lx + 5, lx + 15), (lx + 63, lx + 85)]
    row_y = ly + 8

    def item(c, r, drawfn, label):
        sx, tx = col[c]
        yv = row_y + r * 14.0
        drawfn(sx, yv)
        s.text(tx, yv + 5.2, label, 2.0)

    item(0, 0, lambda a, b: s.c_no(a, b), "Contact, normally open")
    item(0, 1, lambda a, b: s.c_nc(a, b), "Contact, normally closed")
    item(0, 2, lambda a, b: s.pb_no(a, b), "Push-button, NO, spring return")
    item(0, 3, lambda a, b: s.pb_nc(a, b), "Push-button, NC, spring return")
    item(0, 4, lambda a, b: s.estop(a, b), "Emergency stop, latching, NC")
    item(0, 5, lambda a, b: s.limit_switch(a, b), "Position (door) switch, roller")
    item(0, 6, lambda a, b: s.coil(a, b - 2), "Contactor / relay coil")
    item(0, 7, lambda a, b: s.lamp(a, b - 2), "Indicator lamp, 24 V DC")
    item(0, 8, lambda a, b: s.buzzer(a, b - 2), "Audible alarm (hooter)")
    item(0, 9, lambda a, b: s.fuse(a, b), "Fuse")

    item(1, 0, lambda a, b: s.breaker([a], b - 2), "Circuit breaker, thermal-magnetic")
    item(1, 1, lambda a, b: s.isolator([a], b - 2), "Switch-disconnector / isolator")
    item(1, 2, lambda a, b: s.contactor_poles([a], b - 1), "Contactor, main pole")
    item(1, 3, lambda a, b: s.overload([a], b - 1), "Thermal overload relay")
    item(1, 4, lambda a, b: s.motor(a, b - 1, r=5.0), "Motor, 3-phase asynchronous")
    item(1, 5, lambda a, b: s.heater(a, b - 3, h=11.0), "Resistive heating element")
    item(1, 6, lambda a, b: s.transformer(a, b - 3, h=15.0), "Control transformer")
    item(1, 7, lambda a, b: s.psu(a - 5, b - 2, w=16, h=12), "AC/DC power supply unit")
    item(1, 8, lambda a, b: s.thermocouple(a, b - 2), "Thermocouple, type K")
    item(1, 9, lambda a, b: (s.terminal(a, b + 4, "1"), s.earth(a + 11, b)),
         "Terminal / protective earth")

    # ---------------- notes ----------------
    nx, ny = 152, 175
    s.text(nx, ny, "5.  NOTES", 3.0, weight="bold")
    s.line(nx, ny + 1.6, nx + 250, ny + 1.6, w=LW_THIN)
    notes = [
        "1.  All wiring to IEC 60204-1.  Power conductors 1100 V grade PVC copper, control conductors 1.5 mm2 black,",
        "     24 V DC control conductors 1.0 mm2 dark blue, protective conductor green/yellow, neutral light blue.",
        "2.  All field wiring terminates on terminal strip -X1 / -X2.  No field cable is landed directly on a device.",
        "3.  Heater over-temperature protection is HARD-WIRED: high-limit thermostat -B3 (manual reset) is in series with",
        "     the -K3 coil, so the heater drops out on over-temperature regardless of the state of the PLC.",
        "4.  DOOR INTERLOCK - the door position switch -B1 is wired to PLC input X5 only, as instructed.  The blowers are",
        "     therefore stopped by the PLC program (software), not by hardware.  A wire link -LK1 is fitted in the blower",
        "     coil circuit on sheet 08; if a hard-wired interlock is required later, remove -LK1 and land the NC contact of a",
        "     second (safety) door switch on terminals -X1:60 / -X1:61.  No panel rework is needed.",
        "5.  The door interlock deliberately does NOT break the heater circuit: the heater stays energised while the door is",
        "     open, per the process requirement.  Warning label to be fitted at the door: 'HOT SURFACES - HEATER LIVE'.",
        "6.  PLC digital inputs are wired SINK type: terminal S/S is connected to +24 V and the field contact switches 0 V",
        "     into the X terminal.  PLC digital outputs are transistor SINK type: the load sits between +24 V and the Y",
        "     terminal, COM0 / COM1 are connected to 0 V.  Contactor coils (230 V AC) are driven via interposing relays.",
        "7.  All fail-safe field contacts (E-stop, high-limit, stop push-buttons) are wired normally CLOSED so that a broken",
        "     wire produces the safe state.  Overload trip contacts are wired NO (input ON = tripped) for diagnostics.",
        "8.  0 V of the 24 V DC system is bonded to PE at one point only, at terminal -X2:0V/PE in the panel.",
        "9.  Cable screens of the thermocouple extension lead are earthed at the panel end only.",
        "10. Ratings shown are for the assumed loads listed in section 1.  Confirm motor nameplate FLC and heater element",
        "     rating on site and adjust -Q2/-Q3 settings, -F1/-F2/-F3 overload settings and cable sizes accordingly.",
    ]
    s.text(x, 212, "6.  REVISION HISTORY", 3.0, weight="bold")
    s.line(x, 213.6, x + 128, 213.6, w=LW_THIN)
    s.table(x, 216, [(12, "REV"), (22, "DATE"), (74, "DESCRIPTION"), (20, "BY")], [
        ["0", "2026-09-06", "First issue - schematic for review", "CLAUDE"],
        ["1", "2026-09-06", "Door-signal watchdog alarm output", "CLAUDE"],
        ["", "", "Y12 / -KA4 added; single maintenance", ""],
        ["", "", "password level; 7-day data logging to", ""],
        ["", "", "the SD card in the FX5U", ""],
        ["2", "2026-09-06", "-S0 contact to PLC X0 corrected from", "CLAUDE"],
        ["", "", "11-12 to 21-22 (11-12 is used in the", ""],
        ["", "", "coil bus on sheet 05)", ""],
    ], rh=5.0, align=["middle", "middle", "start", "middle"])

    yy = ny + 6.0
    for n in notes:
        ind = (len(n) - len(n.lstrip())) * 0.85
        s.text(nx + ind, yy, n.strip(), 2.05)
        yy += 3.5
    return s


# ===================================================================== 02
def sheet02():
    s = new("02 / 13", "SINGLE LINE DIAGRAM - POWER DISTRIBUTION",
            "415 V AC, 3-ph + N + PE, 50 Hz, TN-S, 10 kA")

    ytop = 30
    # ---- incoming ----
    xin = 40
    s.text(xin - 22, ytop - 2, "INCOMING SUPPLY", 2.6, weight="bold")
    s.text(xin - 22, ytop + 2, "415 V AC 3-ph + N + PE, 50 Hz", 2.1)
    s.line(xin, ytop + 5, xin, ytop + 16, w=LW_POWER)
    s.text(xin + 3, ytop + 10, "3P + N", 2.1)
    s.isolator([xin], ytop + 16, tag="-Q1", sub="MCCB 4P 63 A, Icu 25 kA, Ir = 50 A")
    s.line(xin, ytop + 28, xin, ytop + 45, w=LW_POWER)
    s.earth(xin - 22, ytop + 24, size=6, label="PE bar -PE1")
    s.line(xin - 22, ytop + 24, xin - 22, ytop + 12, w=LW_MED)
    s.line(xin - 22, ytop + 12, xin, ytop + 12, w=LW_MED)

    # ---- busbar ----
    by = ytop + 45
    s.line(xin, by, 388, by, w=LW_POWER)
    s.line(xin, by + 3.2, 388, by + 3.2, w=LW_POWER)
    s.text(xin - 22, by + 1.4, "L1 L2 L3", 2.2, weight="bold")
    s.text(xin - 22, by + 5.6, "N", 2.2, weight="bold")
    s.text(200, by - 2.0, "PANEL BUSBAR  -W1   415 V / 63 A", 2.4, "middle", weight="bold")

    feeds = [
        (72,  "-Q2", ["MPCB 3P", "2.5 - 4 A", "GV2ME08"], "-K1", ["9 A AC-3", "230 V coil"],
         "-F1", ["OLR 2.5-4 A", "set 3.5 A"], "M", "-M1", ["BLOWER 1", "1.5 kW / 2 HP", "415 V 3-ph 3.5 A"]),
        (140, "-Q3", ["MPCB 3P", "2.5 - 4 A", "GV2ME08"], "-K2", ["9 A AC-3", "230 V coil"],
         "-F2", ["OLR 2.5-4 A", "set 3.5 A"], "M", "-M2", ["BLOWER 2", "1.5 kW / 2 HP", "415 V 3-ph 3.5 A"]),
        (212, "-Q4", ["MCB 3P 40 A", "C-curve", "10 kA"], "-K3", ["40 A AC-1", "230 V coil"],
         "-F3", ["OLR 23-32 A", "set 25 A"], "H", "-E1..-E3", ["HEATER BANK", "3 x 6 kW = 18 kW", "STAR, 25 A/ph"]),
    ]
    for fx, qt, qs, kt, ks, ft, fs, kind, mt, ms in feeds:
        s.line(fx, by + 3.2, fx, by + 18, w=LW_POWER)
        s.text(fx + 3, by + 11, "3P", 2.0)
        s.breaker([fx], by + 18, tag=qt, sub=qs)
        s.line(fx, by + 30, fx, by + 48, w=LW_POWER)
        s.contactor_poles([fx], by + 48, tag=kt, sub=ks)
        s.line(fx, by + 58, fx, by + 76, w=LW_POWER)
        s.overload([fx], by + 76, tag=ft, sub=fs)
        s.line(fx, by + 86, fx, by + 104, w=LW_POWER)
        if kind == "M":
            s.motor(fx, by + 104, tag=mt, sub=ms)
            s.earth(fx, by + 122, size=5)
        else:
            s.line(fx - 22, by + 104, fx + 22, by + 104, w=LW_MED)
            for i, dx in enumerate([-22, 0, 22]):
                s.line(fx + dx, by + 104, fx + dx, by + 108, w=LW_MED)
                s.heater(fx + dx, by + 108, h=14, tag=f"-E{i+1}")
                s.line(fx + dx, by + 126, fx + dx, by + 132, w=LW_MED)
            s.dot(fx, by + 104)
            s.line(fx - 22, by + 132, fx + 22, by + 132, w=LW_MED)
            s.text(fx, by + 138.0, "STAR POINT - not earthed and not", 2.0, "middle")
            s.text(fx, by + 141.0, "connected to the system neutral", 2.0, "middle")
            s.text(fx + 30, by + 80, mt, 2.4, weight="bold")
            for i, m in enumerate(ms):
                s.text(fx + 30, by + 84 + i * 3.2, m, 2.0)
            s.line(fx - 48, by + 116, fx - 32, by + 116, w=LW_MED, dash="1.5,1.5")
            s.text(fx - 48, by + 112, "oven body / element housing", 2.0, "end")
            s.earth(fx - 48, by + 116, size=5)

    # ---- control transformer feeder ----
    cx = 300
    s.line(cx, by + 3.2, cx, by + 18, w=LW_MED)
    s.text(cx + 3, by + 11, "L1-L2", 2.0)
    s.breaker([cx], by + 18, tag="-Q5", sub=["MCB 2P 6 A", "C-curve"])
    s.line(cx, by + 30, cx, by + 42, w=LW_MED)
    s.transformer(cx, by + 42, tag="-T1", sub=["415 / 230 V, 500 VA", "single phase, 50 Hz",
                                               "screened, IEC 61558-2-6"])
    s.line(cx, by + 62, cx, by + 72, w=LW_MED)
    s.breaker([cx], by + 72, tag="-Q6", sub=["MCB 1P 4 A", "C-curve"])
    s.line(cx, by + 84, cx, by + 94, w=LW_MED)
    s.line(cx - 30, by + 94, cx + 46, by + 94, w=LW_MED)
    s.text(cx + 48, by + 95, "230 V AC CONTROL BUS  (wire 100 / 190)  -> SHEET 05", 2.1)
    s.earth(cx + 14, by + 62, size=5, label="secondary N earthed")
    s.line(cx, by + 62, cx + 14, by + 62, w=LW_MED)
    s.dot(cx, by + 62)

    # ---- 24 V DC ----
    s.line(cx - 30, by + 94, cx - 30, by + 106, w=LW_MED)
    s.psu(cx - 43, by + 106, w=26, h=18, tag="-G1",
          sub=["SMPS 230 V AC / 24 V DC", "5 A, 120 W, DIN rail", "MELSEC FX5-PSU or equiv."])
    s.line(cx - 30, by + 124, cx - 30, by + 134, w=LW_MED)
    s.line(cx - 52, by + 134, cx + 20, by + 134, w=LW_MED)
    s.text(cx + 22, by + 135, "24 V DC BUS (wire 200 / 201)  -> SHEET 05", 2.1)

    # ---- panel auxiliaries ----
    ax = 356
    s.line(ax, by + 3.2, ax, by + 18, w=LW_MED)
    s.text(ax + 3, by + 11, "L3-N", 2.0)
    s.breaker([ax], by + 18, tag="-Q7", sub=["MCB 2P 6 A", "30 mA RCBO"])
    s.line(ax, by + 30, ax, by + 44, w=LW_MED)
    s.block(ax - 16, by + 44, 32, 16, title="PANEL AUX",
            sub=["light + 6 A socket", "+ filter fan"], tsize=2.4)

    # ---- notes ----
    s.notes(18, 248, [
        "1.  Diagram is single-line; all switching devices are 3-pole unless noted.  See sheets 03 and 04 for the 3-line detail.",
        "2.  Heater elements are connected in STAR; the star point is not connected to the system neutral.",
        "3.  Cable schedule:  -M1/-M2  4C x 2.5 mm2 Cu;  heater bank  4C x 10 mm2 Cu;  incomer  4C x 16 mm2 Cu.",
        "4.  -Q4 is a C-curve MCB sized for the resistive load; -F3 gives the overload/asymmetry protection for the elements.",
        "5.  -K3 is rated for AC-1 utilisation.  Expect contact wear proportional to the PID cycle time - see NOTE 6 on sheet 04.",
    ])
    return s


def _rails(s, y0=30, x0=18, x1=402, names=("L1", "L2", "L3", "N", "PE"), pitch=4.6):
    ys = {}
    for i, n in enumerate(names):
        y = y0 + i * pitch
        ys[n] = y
        w = LW_POWER if n in ("L1", "L2", "L3") else LW_MED
        s.line(x0, y, x1, y, w=w)
        s.text(x0 - 1.5, y + 0.9, n, 2.3, "end", weight="bold")
        s.text(x1 + 1.5, y + 0.9, n, 2.3, "start", weight="bold")
    s.text(x0, y0 - 4.2,
           "FROM PANEL BUSBAR -W1  (SHEET 02)   415 V AC, 3-ph + N + PE, 50 Hz", 2.4,
           "start", weight="bold")
    return ys


def _feeder(s, xc, ys, qtag, qsub, ktag, ksub, ftag, fsub, term, wirepfx, dx=9.0):
    """Draw a 3-phase feeder column; returns y of the bottom of the OLR."""
    px = [xc - dx, xc, xc + dx]
    # tap from rails
    for i, ph in enumerate(("L1", "L2", "L3")):
        s.line(px[i], ys[ph], px[i], 56, w=LW_POWER)
        s.dot(px[i], ys[ph])
        s.text(px[i] + 1.4, ys[ph] - 1.4, ph, 1.9)
    s.breaker(px, 56, tag=qtag, sub=qsub, h=13)
    for i in range(3):
        s.line(px[i], 69, px[i], 86, w=LW_POWER)
        s.text(px[i] + 1.2, 76, f"{wirepfx}L{i+1}", 1.9)
    s.contactor_poles(px, 86, tag=ktag, sub=ksub, h=11)
    for i in range(3):
        s.line(px[i], 97, px[i], 112, w=LW_POWER)
        s.text(px[i] + 1.2, 104, f"{wirepfx}{i+1}", 1.9)
    s.overload(px, 112, tag=ftag, sub=fsub, h=11)
    for i in range(3):
        s.line(px[i], 123, px[i], 134, w=LW_POWER)
    # terminals
    for i in range(3):
        s.terminal(px[i], 134, term[i], lp="left" if i == 0 else "right", tsize=1.9)
        s.line(px[i], 135.3, px[i], 146, w=LW_POWER)
    s.text(px[0] - dx * 0.6, 136.0, "-X2", 2.2, "end", weight="bold")
    return px


# ===================================================================== 03
def sheet03():
    s = new("03 / 13", "POWER CIRCUIT - BLOWER MOTORS -M1 / -M2",
            "Direct-on-line starters, 415 V 3-ph, 1.5 kW each")
    ys = _rails(s, x1=286)

    for xc, q, k, f, term, wp, mt, ms, cbl in [
        (66, "-Q2", "-K1", "-F1", ("1", "2", "3"), "1", "-M1",
         ["BLOWER 1 (RECIRCULATION)", "1.5 kW / 2 HP, 415 V, 3-ph", "FLC 3.5 A, 2870 rpm, IP55"],
         "cable -W2  4C x 2.5 mm2 Cu XLPE, 12 m"),
        (196, "-Q3", "-K2", "-F2", ("4", "5", "6"), "2", "-M2",
         ["BLOWER 2 (RECIRCULATION)", "1.5 kW / 2 HP, 415 V, 3-ph", "FLC 3.5 A, 2870 rpm, IP55"],
         "cable -W3  4C x 2.5 mm2 Cu XLPE, 14 m"),
    ]:
        px = _feeder(s, xc, ys,
                     q, ["MPCB 3P, 2.5-4 A", "set to 3.5 A", "Icu 50 kA"],
                     k, ["9 A AC-3, 4 kW", "230 V AC coil", "1 NO + 1 NC aux"],
                     f, ["OLR 2.5-4 A", "set to 3.5 A", "class 10A, manual reset"],
                     term, wp)
        s.motor(xc, 146, tag=mt, sub=ms)
        s.line(xc, 158, xc - 22, 158, w=LW_MED, dash="1.5,1.5")
        s.earth(xc - 22, 158, size=5)
        s.line(xc - 22, 158, xc - 22, ys["PE"], w=LW_MED)
        s.dot(xc - 22, ys["PE"])
        s.text(xc, 178, cbl, 2.0, "middle")
        s.text(xc, 182, "motor frame bonded to PE via cable core 4", 1.9, "middle")

    # ---- auxiliary contact detail ----
    ax = 300
    s.dashbox(ax - 6, 46, 104, 116, "AUXILIARY CONTACT ALLOCATION  (for reference only)")
    s.text(ax, 54, "DEVICE", 2.2, weight="bold")
    s.text(ax + 26, 54, "CONTACT", 2.2, weight="bold")
    s.text(ax + 54, 54, "USED FOR", 2.2, weight="bold")
    aux = [
        ("-K1", "13-14 (NO)", "PLC input X14 - run feedback", "sheet 06"),
        ("-K1", "21-22 (NC)", "spare", "-"),
        ("-K2", "13-14 (NO)", "PLC input X15 - run feedback", "sheet 06"),
        ("-K2", "21-22 (NC)", "spare", "-"),
        ("-F1", "95-96 (NC)", "in series with -K1 coil", "sheet 08"),
        ("-F1", "97-98 (NO)", "PLC input X10 - OL tripped", "sheet 06"),
        ("-F2", "95-96 (NC)", "in series with -K2 coil", "sheet 08"),
        ("-F2", "97-98 (NO)", "PLC input X11 - OL tripped", "sheet 06"),
        ("-Q2", "aux 1 NO", "spare (future MCB trip alarm)", "-"),
        ("-Q3", "aux 1 NO", "spare (future MCB trip alarm)", "-"),
    ]
    yy = 60
    for d, c, u, x in aux:
        s.text(ax, yy, d, 2.0, weight="bold")
        s.text(ax + 26, yy, c, 2.0)
        s.text(ax + 54, yy, u, 2.0)
        s.text(ax + 54, yy + 2.9, x, 1.8, style="italic")
        yy += 6.6

    s.notes(18, 196, [
        "1.  -Q2 / -Q3 are motor-protection circuit breakers providing short-circuit and isolation duty; the thermal overload",
        "     relays -F1 / -F2 provide the running overload and phase-loss protection and give the trip signal to the PLC.",
        "2.  Set both MPCB and OLR to the motor nameplate FLC after commissioning - the values shown assume 3.5 A.",
        "3.  Overload relays are set to MANUAL RESET. A tripped overload must be reset at the panel; the PLC will not",
        "     restart the blower until the trip input clears and the corresponding fault is acknowledged on the HMI.",
        "4.  Both starters are direct-on-line. Motor direction to be checked at commissioning - airflow must be towards the",
        "     oven plenum. Swap two phases at -X2 if rotation is incorrect.",
        "5.  Blower contactors -K1 / -K2 are energised only when the PLC output Y0 / Y1 is ON - see sheets 07 and 08.",
    ])
    return s


# ===================================================================== 04
def sheet04():
    s = new("04 / 13", "POWER CIRCUIT - HEATER BANK -E1 / -E2 / -E3",
            "3 x 6 kW resistive elements, star connected, 18 kW total, 25 A per phase")
    ys = _rails(s, x1=186)

    xc = 96
    px = _feeder(s, xc, ys,
                 "-Q4", ["MCB 3P 40 A", "C-curve, 10 kA", "isolation duty"],
                 "-K3", ["40 A AC-1", "230 V AC coil", "1 NO + 1 NC aux"],
                 "-F3", ["OLR 23-32 A", "set to 25 A", "class 10A, manual reset"],
                 ("10", "11", "12"), "3", dx=16)

    # heater elements
    for i in range(3):
        s.line(px[i], 146, px[i], 152, w=LW_POWER)
        s.heater(px[i], 152, h=16, tag=f"-E{i+1}",
                 sub=["6 kW", "240 V", "8.7 A"])
        s.line(px[i], 170, px[i], 182, w=LW_MED)
    s.line(px[0], 182, px[2], 182, w=LW_MED)
    s.dot(px[1], 182)
    s.text(xc, 188, "STAR POINT", 2.3, "middle", weight="bold")
    s.text(xc, 192, "floating - not connected to N or PE", 2.0, "middle")
    s.line(px[0] - 26, 162, px[0] - 4, 162, w=LW_MED, dash="1.5,1.5")
    s.earth(px[0] - 26, 162, size=5)
    s.line(px[0] - 26, 162, px[0] - 26, ys["PE"], w=LW_MED)
    s.dot(px[0] - 26, ys["PE"])
    s.text(px[0] - 28, 158, "oven body / element", 1.9, "end")
    s.text(px[0] - 28, 161, "housing bonded to PE", 1.9, "end")
    s.text(xc, 200, "cable -W4  4C x 10 mm2 Cu XLPE, 10 m, in metal conduit", 2.0, "middle")

    # ---- calculation block ----
    bx = 196
    s.dashbox(bx, 46, 96, 78, "HEATER CIRCUIT CALCULATION")
    calc = [
        ("Total connected load", "P = 3 x 6 kW = 18 kW"),
        ("Line current (star, 415 V)", "I = 18000 / (1.732 x 415) = 25.0 A"),
        ("Element voltage (star)", "U = 415 / 1.732 = 240 V"),
        ("Element current", "I = 6000 / 240 = 25.0 A per element"),
        ("Element resistance (cold)", "R = 240 / 25 = 9.6 ohm nominal"),
        ("Cable sizing (25 A, 40 C)", "10 mm2 Cu -> 57 A capacity, derated 0.87"),
        ("", "= 49 A > 25 A   OK"),
        ("MCB -Q4", "40 A C-curve  >  1.45 x 25 A = 36 A   OK"),
        ("Overload -F3", "set 25 A, class 10A"),
        ("Volt drop at 10 m", "approx. 0.7 V (0.17 %)   OK"),
    ]
    yy = 54
    for k, v in calc:
        if k:
            s.text(bx + 3, yy, k, 2.0, weight="bold")
        s.text(bx + 44, yy, v, 2.0)
        yy += 6.8

    # ---- contactor duty block ----
    s.dashbox(bx, 132, 96, 62, "CONTACTOR -K3  DUTY  (see NOTE 6)")
    duty = [
        "-K3 is switched by PLC output Y2, which follows the",
        "PID controller demand contact on input X6.",
        "",
        "With a PID cycle time of 20 s the contactor would make",
        "and break up to 180 operations per hour, i.e. about",
        "1.5 million operations per year on a 2-shift pattern.",
        "",
        "The PLC program therefore imposes a minimum ON time",
        "and a minimum OFF time of 20 s each on Y2 (anti-chatter",
        "timers T_HTR_MIN_ON / T_HTR_MIN_OFF), which caps the",
        "switching rate at 90 operations per hour.",
        "",
        "Set the controller cycle time to 20 s or longer to suit.",
    ]
    yy = 140
    for d in duty:
        s.text(bx + 3, yy, d, 2.0)
        yy += 4.0

    # ---- protection philosophy ----
    px2 = 300
    s.dashbox(px2, 56, 100, 138, "HEATER PROTECTION - LAYERS")
    layers = [
        ("1", "-Q4  MCB 3P 40 A",
         ["short-circuit protection and", "isolation of the heater feeder"]),
        ("2", "-F3  thermal overload relay",
         ["overload, element failure and", "phase asymmetry; manual reset"]),
        ("3", "-B3  high-limit thermostat",
         ["independent over-temperature trip,", "HARD-WIRED in the -K3 coil circuit",
          "(sheet 08) - it drops the heater even", "if the PLC or the PID controller fails.",
          "Manual reset at the panel."]),
        ("4", "-A2  PID controller",
         ["closed-loop process temperature", "control; sensor-break alarm to X7"]),
        ("5", "PLC -A1",
         ["start permissives, heat-up watchdog", "alarm and manual-test interlocks"]),
    ]
    yy = 64
    for n, d, lines in layers:
        s.circle(px2 + 7, yy - 1.0, 3.2, lw=LW_MED)
        s.text(px2 + 7, yy + 0.0, n, 2.2, "middle", weight="bold")
        s.text(px2 + 13, yy, d, 2.1, weight="bold")
        for i, t in enumerate(lines):
            s.text(px2 + 13, yy + 3.6 + i * 3.4, t, 2.0)
        yy += 8.0 + len(lines) * 3.4

    s.text(px2 + 4, 168, "IMPORTANT:", 2.2, weight="bold")
    for i, t in enumerate([
        "The door interlock does NOT break the heater circuit.",
        "The heater stays energised while the oven door is open,",
        "as required by the process.  Layer 3 is then the only",
        "protection limiting the oven temperature, so -B3 must be",
        "function-tested at every planned maintenance.",
    ]):
        s.text(px2 + 4, 172.4 + i * 3.6, t, 2.0)

    s.notes(18, 214, [
        "1.  Elements are connected in STAR with the star point floating. Do not connect the star point to the system neutral -",
        "     a single element failure would then unbalance the neutral current.",
        "2.  -Q4 is C-curve. The heater is a purely resistive load with a cold-start inrush of about 1.3 x In for a few seconds.",
        "3.  Element terminal box on the oven is to be wired with high-temperature silicone/glass-fibre insulated cable, rated",
        "     180 C minimum, from the gland plate to the element studs.",
        "4.  Insulation resistance of the element bank to be measured before energising: > 1 Mohm at 500 V DC when cold.",
        "5.  -F3 also protects against the loss of one element (current asymmetry) - set it to the measured balanced current.",
        "6.  Contactor -K3 is an AC-1 rated device switching a resistive load. See the duty block above: the PLC limits the",
        "     switching frequency so that the mechanical and electrical life of -K3 is not consumed prematurely.",
    ])
    return s
