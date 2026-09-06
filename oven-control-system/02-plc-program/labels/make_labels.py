"""Global label list for OVN-2026-01 and a consistency checker.

Run:  python3 make_labels.py
Emits global_labels.csv and reports:
  - labels used in the ST but not declared
  - labels declared but never used
  - overlapping device assignments
"""
import csv, os, re, sys

BIT, INT, DINT = "Bit", "Word [Signed]", "Double Word [Signed]"

# (label, type, device, array_len_or_None, comment)
L = [
    # ---------------- non-latched working bits ----------------
    ("gTick100ms",        BIT, "M0",  None, "1 scan pulse every 100 ms"),
    ("gTick100msMem",     BIT, "M1",  None, "edge memory for SM409"),
    ("gTick1s",           BIT, "M2",  None, "1 scan pulse every 1 s"),
    ("gTick1sMem",        BIT, "M3",  None, "edge memory for SM412"),
    ("gHeartbeat",        BIT, "M4",  None, "1 s heartbeat for the HMI watchdog"),
    ("gEStopOK",          BIT, "M5",  None, "X0  -S0 emergency stop released"),
    ("gBl1StopOK",        BIT, "M6",  None, "X2  -S2 stop PB not pressed"),
    ("gBl2StopOK",        BIT, "M7",  None, "X4  -S4 stop PB not pressed"),
    ("gPidOK",            BIT, "M8",  None, "X7  -A2 AL1 controller healthy"),
    ("gHighLimitOK",      BIT, "M9",  None, "X13 -B3 high-limit thermostat healthy"),
    ("gDoorClosed",       BIT, "M10", None, "X5  -B1 door closed, raw"),
    ("gHeatDemand",       BIT, "M11", None, "X6  -A2 OUT1 calling for heat"),
    ("gBl1OlTrip",        BIT, "M12", None, "X10 -F1 overload tripped"),
    ("gBl2OlTrip",        BIT, "M13", None, "X11 -F2 overload tripped"),
    ("gHtrOlTrip",        BIT, "M14", None, "X12 -F3 overload tripped"),
    ("gK1Closed",         BIT, "M15", None, "X14 -K1 contactor closed"),
    ("gK2Closed",         BIT, "M16", None, "X15 -K2 contactor closed"),
    ("gK3Closed",         BIT, "M17", None, "X16 -K3 contactor closed"),
    ("gLampTest",         BIT, "M18", None, "X17 -S5 held = lamp test"),
    ("gAcceptMem",        BIT, "M19", None, "edge memory for -S5"),
    ("gAcceptEdge",       BIT, "M20", None, "rising edge of -S5"),
    ("gAlarmAcceptPulse", BIT, "M21", None, "alarm accept, panel or HMI"),
    ("gBl1Permit",        BIT, "M22", None, "blower 1 permissive"),
    ("gBl2Permit",        BIT, "M23", None, "blower 2 permissive"),
    ("gHtrPermit",        BIT, "M24", None, "heater permissive"),
    ("gSlotRunPermit",    BIT, "M25", None, "slot timers may advance (optional gating)"),
    ("gBl1StartMem",      BIT, "M26", None, "edge memory for -S1"),
    ("gBl2StartMem",      BIT, "M27", None, "edge memory for -S3"),
    ("gBl1StartEdge",     BIT, "M28", None, "rising edge of -S1"),
    ("gBl2StartEdge",     BIT, "M29", None, "rising edge of -S3"),
    ("gBl1RunReq",        BIT, "M30", None, "blower 1 run request, held over a door open"),
    ("gBl2RunReq",        BIT, "M31", None, "blower 2 run request, held over a door open"),
    ("gBl1Out",           BIT, "M32", None, "blower 1 output state"),
    ("gBl2Out",           BIT, "M33", None, "blower 2 output state"),
    ("gHtrCmd",           BIT, "M34", None, "heater command after anti-chatter"),
    ("gHtrOut",           BIT, "M35", None, "heater output state"),
    ("gDoorMem",          BIT, "M36", None, "edge memory, raw door"),
    ("gDoorCloseEdge",    BIT, "M37", None, "raw door closing edge"),
    ("gDoorOpenEdge",     BIT, "M38", None, "raw door opening edge"),
    ("gDoorClosedStable", BIT, "M39", None, "door closed continuously for 1 s"),
    ("gDoorOK",           BIT, "M40", None, "blower interlock permissive"),
    ("gDoorDeb",          BIT, "M41", None, "door state, 1 s debounce both ways"),
    ("gDoorDebMem",       BIT, "M42", None, "edge memory, debounced door"),
    ("gDoorDebCloseEdge", BIT, "M43", None, "debounced door closing edge"),
    ("gDoorDebOpenEdge",  BIT, "M44", None, "debounced door opening edge"),
    ("gDoorAlarm",        BIT, "M45", None, "any door-signal watchdog alarm"),
    ("gAlmDoorNotClosedMem", BIT, "M46", None, "edge memory for event logging"),
    ("gAlmHeatUpMem",     BIT, "M47", None, "edge memory for event logging"),
    ("gAnySlotRunning",   BIT, "M48", None, "one or more slot timers running"),
    ("gAnyAlarm",         BIT, "M49", None, "any alarm present"),
    ("gAlarmNew",         BIT, "M50", None, "a new alarm appeared this scan"),
    ("gAlarmUnack",       BIT, "M51", None, "alarm not yet accepted"),
    ("gHooter",           BIT, "M52", None, "hooter demand"),
    ("gManualMode",       BIT, "M53", None, "manual test mode active"),
    ("gManualPermit",     BIT, "M54", None, "manual test conditions satisfied"),
    ("gManBl1",           BIT, "M55", None, "manual blower 1 demand"),
    ("gManBl2",           BIT, "M56", None, "manual blower 2 demand"),
    ("gManHtr",           BIT, "M57", None, "manual heater demand"),
    ("gMaintLoggedIn",    BIT, "M58", None, "MAINTENANCE role logged in"),
    ("gEventPulse",       BIT, "M59", None, "1 scan event trigger for SD logging"),
    ("gQualityLoggedIn",  BIT, "M60", None, "QUALITY role logged in"),
    ("gLockoutActive",    BIT, "M61", None, "login locked out after failed attempts"),
    ("gSlotTimersPaused", BIT, "M62", None, "cure timers held - oven not fit to cure"),
    ("gSlotPausedMem",    BIT, "M63", None, "edge memory for the pause event"),

    # ---------------- alarm bits (GOT watches M700-M715) ----------------
    ("gAlmBits",          BIT, "M700", 16, "alarm block, overlays the named alarms"),
    ("gAlmEStop",         BIT, "M700", None, "ALM 0  emergency stop operated"),
    ("gAlmBl1Ol",         BIT, "M701", None, "ALM 1  blower 1 overload tripped"),
    ("gAlmBl2Ol",         BIT, "M702", None, "ALM 2  blower 2 overload tripped"),
    ("gAlmHtrOl",         BIT, "M703", None, "ALM 3  heater overload tripped"),
    ("gAlmHighLimit",     BIT, "M704", None, "ALM 4  high-limit thermostat tripped"),
    ("gAlmPidFault",      BIT, "M705", None, "ALM 5  PID alarm or sensor break"),
    ("gAlmHeatUp",        BIT, "M706", None, "ALM 6  failure to reach setpoint"),
    ("gAlmDoorChatter",   BIT, "M707", None, "ALM 7  door signal pulsating"),
    ("gAlmDoorNotClosed", BIT, "M708", None, "ALM 8  no door closed signal"),
    ("gAlmK1Fault",       BIT, "M709", None, "ALM 9  -K1 feedback disagrees"),
    ("gAlmK2Fault",       BIT, "M710", None, "ALM 10 -K2 feedback disagrees"),
    ("gAlmK3Fault",       BIT, "M711", None, "ALM 11 -K3 feedback disagrees"),
    ("gAlmLotMismatch",   BIT, "M712", None, "ALM 12 lots loaded / unloaded mismatch"),
    ("gAlmCurePaused",    BIT, "M713", None, "ALM 13 cure timers paused, oven not fit"),
    ("gAlmMem",           BIT, "M720", 16, "previous scan alarm block"),

    # ---------------- HMI command bits ----------------
    ("gHmiSlotStart",     BIT, "M800", 6, "HMI start, slot 1-6"),
    ("gHmiSlotReset",     BIT, "M810", 6, "HMI reset, slot 1-6"),
    ("gHmiBl1Start",      BIT, "M820", None, "HMI blower 1 start"),
    ("gHmiBl1Stop",       BIT, "M821", None, "HMI blower 1 stop"),
    ("gHmiBl2Start",      BIT, "M822", None, "HMI blower 2 start"),
    ("gHmiBl2Stop",       BIT, "M823", None, "HMI blower 2 stop"),
    ("gHmiAlarmAccept",   BIT, "M824", None, "HMI alarm accept"),
    ("gHmiResetDoorCnt",  BIT, "M825", None, "HMI reset door counters"),
    ("gHmiResetLotCnt",   BIT, "M826", None, "HMI reset lot counters"),
    ("gHmiManualReq",     BIT, "M827", None, "HMI enter manual test"),
    ("gHmiManualExit",    BIT, "M828", None, "HMI exit manual test"),
    ("gHmiMaintLoginReq", BIT, "M829", None, "HMI login attempt, MAINTENANCE"),
    ("gHmiLogout",        BIT, "M830", None, "HMI log out"),
    ("gHmiActivity",      BIT, "M831", None, "GOT screen touch, resets the logout timer"),
    ("gHmiManBl1",        BIT, "M832", None, "HMI manual blower 1, momentary"),
    ("gHmiManBl2",        BIT, "M833", None, "HMI manual blower 2, momentary"),
    ("gHmiManHtr",        BIT, "M834", None, "HMI manual heater, momentary"),
    ("gHmiQualityLoginReq", BIT, "M835", None, "HMI login attempt, QUALITY"),

    # ---------------- latched bits ----------------
    ("gSlotRunning",      BIT, "M4000", 6, "LATCH slot 1-6 occupied / timing"),
    ("gSlotComplete",     BIT, "M4008", 6, "LATCH slot 1-6 reached 2 hours"),
    ("gSetHtrNeedsAir",   BIT, "M4020", None, "LATCH option: heater needs a blower running"),
    ("gSetSlotGated",     BIT, "M4021", None, "LATCH option: slot timers pause on a fault"),
    ("gDefaultsWritten",  BIT, "M4022", None, "LATCH settings have been initialised"),

    # ---------------- non-latched words ----------------
    ("gHtrMinOnAcc",      INT, "D0",  None, "heater minimum ON elapsed, s"),
    ("gHtrMinOffAcc",     INT, "D1",  None, "heater minimum OFF elapsed, s"),
    ("gDoorStableAcc",    INT, "D2",  None, "door stable-closed filter, 100 ms units"),
    ("gDoorDebAcc",       INT, "D3",  None, "door debounce filter, 100 ms units"),
    ("gChatterCount",     INT, "D4",  None, "door transitions in the current window"),
    ("gChatterWinAcc",    INT, "D5",  None, "chatter window elapsed, s"),
    ("gK1FbAcc",          INT, "D6",  None, "-K1 feedback disagreement, 100 ms units"),
    ("gK2FbAcc",          INT, "D7",  None, "-K2 feedback disagreement, 100 ms units"),
    ("gK3FbAcc",          INT, "D8",  None, "-K3 feedback disagreement, 100 ms units"),
    ("gManualTmoAcc",     INT, "D9",  None, "manual test elapsed, s"),
    ("gMaintTmoAcc",      INT, "D10", None, "maintenance login idle time, s"),
    ("gSlotsActive",      INT, "D11", None, "number of slots currently running"),
    ("gEventCode",        INT, "D12", None, "event code for the SD log"),
    ("gEventParam",       INT, "D13", None, "event parameter, usually the slot number"),
    ("gEventValue",       INT, "D14", None, "event value, e.g. minutes cut short"),
    ("gHeatUpAcc",        INT, "D15", None, "heat demand held, s"),
    ("gHeatUpMin",        INT, "D16", None, "heat demand held, min, for the HMI"),
    ("gDoorOpenAcc",      INT, "D17", None, "no door closed signal, s"),
    ("gDoorOpenMin",      INT, "D18", None, "no door closed signal, min, for the HMI"),
    ("gTotHtrRunH",       INT, "D19", None, "heater running hours, for the HMI"),
    ("gTotBl1RunH",       INT, "D20", None, "blower 1 running hours, for the HMI"),
    ("gTotBl2RunH",       INT, "D21", None, "blower 2 running hours, for the HMI"),
    ("gQualityTmoAcc",    INT, "D22", None, "quality login idle time, s"),
    ("gFailedAttempts",   INT, "D23", None, "consecutive failed login attempts"),
    ("gLockoutAcc",       INT, "D26", None, "login lockout remaining, s"),
    ("gHmiPasscodeEntry", INT, "D27", None, "passcode typed on the HMI, cleared after use"),
    ("gActiveRole",       INT, "D28", None, "0 none, 1 maintenance, 2 quality"),
    ("gLotsUnaccounted",  DINT,"D24", None, "loaded - unloaded - running = the discrepancy"),
    ("gSlotH",            INT, "D40", 6, "slot 1-6 elapsed hours"),
    ("gSlotM",            INT, "D46", 6, "slot 1-6 elapsed minutes"),
    ("gSlotS",            INT, "D52", 6, "slot 1-6 elapsed seconds"),
    ("gSlotRemainMin",    INT, "D58", 6, "slot 1-6 remaining minutes"),
    ("gSlotPct",          INT, "D64", 6, "slot 1-6 progress percent"),

    # ---------------- latched words ----------------
    ("gSlotElapsed",      DINT,"D4000", 6, "LATCH slot 1-6 elapsed seconds"),
    ("gCntDoorOpen",      DINT,"D4020", None, "LATCH door opened count"),
    ("gCntDoorClose",     DINT,"D4022", None, "LATCH door closed count"),
    ("gCntLotsLoaded",    DINT,"D4024", None, "LATCH lots loaded (slot starts)"),
    ("gCntLotsUnloaded",  DINT,"D4026", None, "LATCH lots unloaded (normal resets)"),
    ("gCntEarlyReset",    DINT,"D4028", None, "LATCH early resets by maintenance"),
    ("gTotHtrRunS",       DINT,"D4030", None, "LATCH heater running seconds"),
    ("gTotBl1RunS",       DINT,"D4032", None, "LATCH blower 1 running seconds"),
    ("gTotBl2RunS",       DINT,"D4034", None, "LATCH blower 2 running seconds"),
    ("gSetHeatUpWdMin",   INT, "D4100", None, "SET heat-up watchdog, min (10-240)"),
    ("gSetDoorWdSec",     INT, "D4101", None, "SET door watchdog, s (60-1800)"),
    ("gSetChatterCnt",    INT, "D4102", None, "SET chatter transition count (4-50)"),
    ("gSetChatterWinS",   INT, "D4103", None, "SET chatter window, s (5-60)"),
    ("gSetHtrMinOnS",     INT, "D4104", None, "SET heater minimum ON, s (5-120)"),
    ("gSetHtrMinOffS",    INT, "D4105", None, "SET heater minimum OFF, s (5-120)"),
    ("gSetManualTmoS",    INT, "D4106", None, "SET manual test auto-exit, s"),
    ("gSetLoginTmoS",     INT, "D4107", None, "SET level 2 auto-logout, s"),
    ("gSetSlotTargetS",   DINT,"D4108", None, "SET slot cure time, s (default 7200)"),
    ("gSetMaintCode",     INT, "D4110", None, "SET MAINTENANCE passcode - change at commissioning"),
    ("gSetQualityCode",   INT, "D4111", None, "SET QUALITY passcode - change at commissioning"),
    ("gSetMaxAttempts",   INT, "D4112", None, "SET failed logins before lockout (default 3)"),
    ("gSetLockoutS",      INT, "D4113", None, "SET lockout duration, s (default 300)"),
]

SIZE = {BIT: 1, INT: 1, DINT: 2}


def typename(t, n):
    return t if n is None else f"{t}(1..{n})" if t != BIT or True else t


def rows():
    out = []
    for name, t, dev, n, cmt in L:
        lo = 0 if name in ("gAlmBits", "gAlmMem") else 1
        dt = t if n is None else f"{t}({lo}..{lo + n - 1})"
        out.append([name, dt, "VAR_GLOBAL", dev, "", cmt])
    return out


def span(dev, t, n):
    """Return (prefix, first, last) device numbers occupied."""
    m = re.match(r"([A-Z]+)(\d+)$", dev)
    pfx, start = m.group(1), int(m.group(2))
    count = (n or 1) * SIZE[t]
    return pfx, start, start + count - 1


def check():
    ok = True
    declared = {r[0] for r in L}

    # 1. every gXxx used in the ST must be declared
    used = set()
    stdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "st")
    for f in sorted(os.listdir(stdir)):
        if not f.endswith(".st"):
            continue
        src = re.sub(r"\(\*.*?\*\)", "", open(os.path.join(stdir, f)).read(), flags=re.S)
        used |= set(re.findall(r"\bg[A-Z]\w*", src))
    missing = sorted(used - declared)
    unused = sorted(declared - used)
    if missing:
        ok = False
        print("UNDECLARED labels used in the ST:", ", ".join(missing))
    if unused:
        print("declared but not referenced:", ", ".join(unused))

    # 2. no unintended device overlap
    occupied = {}
    OVERLAY_OK = {("gAlmBits", "gAlmEStop"), ("gAlmBits", "gAlmBl1Ol"), ("gAlmBits", "gAlmBl2Ol"),
                  ("gAlmBits", "gAlmHtrOl"), ("gAlmBits", "gAlmHighLimit"), ("gAlmBits", "gAlmPidFault"),
                  ("gAlmBits", "gAlmHeatUp"), ("gAlmBits", "gAlmDoorChatter"),
                  ("gAlmBits", "gAlmDoorNotClosed"), ("gAlmBits", "gAlmK1Fault"),
                  ("gAlmBits", "gAlmK2Fault"), ("gAlmBits", "gAlmK3Fault"),
                  ("gAlmBits", "gAlmLotMismatch"), ("gAlmBits", "gAlmCurePaused")}
    for name, t, dev, n, _ in L:
        pfx, a, b = span(dev, t, n)
        for d in range(a, b + 1):
            key = (pfx, d)
            if key in occupied:
                other = occupied[key]
                if (other, name) in OVERLAY_OK or (name, other) in OVERLAY_OK:
                    continue
                ok = False
                print(f"DEVICE CLASH {pfx}{d}: {other} and {name}")
            else:
                occupied[key] = name

    # 3. latch-range sanity
    for name, t, dev, n, cmt in L:
        pfx, a, b = span(dev, t, n)
        latched = cmt.startswith("LATCH") or cmt.startswith("SET")
        in_range = (pfx == "M" and 4000 <= a and b <= 4095) or \
                   (pfx == "D" and 4000 <= a and b <= 4499)
        if latched and not in_range:
            ok = False
            print(f"LATCH ERROR {name} at {dev} is outside the latch range")
        if in_range and not latched:
            ok = False
            print(f"LATCH ERROR {name} at {dev} sits in the latch range but is not latched data")
    return ok


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "global_labels.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Label Name", "Data Type", "Class", "Assign (Device/Label)",
                    "Constant", "Comment"])
        w.writerows(rows())
    print(f"global_labels.csv written: {len(L)} labels")
    sys.exit(0 if check() else 1)
