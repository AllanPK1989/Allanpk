"""All ten GT2107 screens. Each function returns a Screen and registers its
object schedule as it draws, so the schedule can never drift from the design."""
from hmilib import (Screen, W, H, BODY_Y, PANEL, PANEL_2, LINE, LINE_2, TXT,
                    TXT_DIM, RUN, HEAT, ALARM, WARN, INFO, OFF)


# ===================================================================== B-1000
def b1000():
    s = Screen("B-1000", "OVERVIEW", role="-", alarm=True)
    s.header()
    y = s.banner("DOOR OPEN LONGER THAN 10 MIN", ALARM,
                 sub="press ACCEPT on the ALARMS screen to silence the hooter")

    s.lamp(12, y, "BLOWER 1", True, w=186, h=58)
    s.lamp(206, y, "BLOWER 2", True, w=186, h=58)
    s.obj("Lamp", "Blower 1 running", "M32", "bit lamp", "-", "gBl1Out")
    s.obj("Lamp", "Blower 2 running", "M33", "bit lamp", "-", "gBl2Out")

    s.lamp(400, y, "HEATER", True, HEAT, "ON", "OFF", w=186, h=58)
    s.obj("Lamp", "Heater on", "M35", "bit lamp", "-", "gHtrOut")
    s.lamp(594, y, "OVEN DOOR", False, RUN, "CLOSED", "OPEN", w=194, h=58)
    s.obj("Lamp", "Door closed", "M10", "bit lamp", "-", "gDoorClosed, raw X5")

    y2 = y + 68
    s.button(12, y2, 92, 54, "START", "go")
    s.button(108, y2, 90, 54, "STOP", "stop")
    s.button(206, y2, 92, 54, "START", "go")
    s.button(302, y2, 90, 54, "STOP", "stop")
    s.obj("Switch", "Blower 1 start", "M820", "momentary set", "-", "gHmiBl1Start")
    s.obj("Switch", "Blower 1 stop", "M821", "momentary set", "-", "gHmiBl1Stop")
    s.obj("Switch", "Blower 2 start", "M822", "momentary set", "-", "gHmiBl2Start")
    s.obj("Switch", "Blower 2 stop", "M823", "momentary set", "-", "gHmiBl2Stop")

    s.rect(400, y2, 186, 54, PANEL_2, LINE_2)
    s.txt(410, y2 + 20, "PID DEMAND", 11, TXT_DIM, weight="bold")
    s.txt(410, y2 + 42, "CALLING FOR HEAT", 13, HEAT, weight="bold")
    s.obj("Lamp", "PID heat demand", "M11", "bit lamp", "-", "gHeatDemand, X6")

    s.rect(594, y2, 194, 54, PANEL_2, LINE_2)
    s.txt(604, y2 + 20, "DOOR OPEN FOR", 11, TXT_DIM, weight="bold")
    s.txt(604, y2 + 44, "12", 24, ALARM, weight="bold", mono=True)
    s.txt(784, y2 + 44, "min", 12, TXT_DIM, "end")
    s.obj("Numeric", "Door open elapsed", "D18", "display, min", "-", "gDoorOpenMin")

    y3 = y2 + 64
    s.rect(12, y3, 776, 118, PANEL, LINE_2)
    s.txt(24, y3 + 21, "CURE SLOTS", 12, TXT_DIM, weight="bold")
    states = [("1", 62, "01:14:22", "46 min left", RUN),
              ("2", 0, "00:00:00", "not loaded", None),
              ("3", 88, "01:45:10", "15 min left", RUN),
              ("4", 100, "02:00:00", "ready to unload", INFO),
              ("5", 0, "00:00:00", "not loaded", None),
              ("6", 34, "00:41:05", "79 min left", RUN)]
    for i, (n, pct, el, rem, col) in enumerate(states):
        x = 24 + i * 127
        ty = y3 + 28
        s.rect(x, ty, 116, 76, PANEL_2, LINE_2)
        s.txt(x + 8, ty + 16, f"SLOT {n}", 10, TXT_DIM, weight="bold")
        if col is not None:
            s.txt(x + 108, ty + 16, "DONE" if pct == 100 else f"{pct}%", 10,
                  col, "end", weight="bold")
        s.txt(x + 8, ty + 38, el, 14, TXT if col else TXT_DIM, mono=True,
              weight="bold")
        s.bar(x + 8, ty + 46, 100, 6, pct, col or OFF)
        s.txt(x + 8, ty + 66, rem, 10, TXT_DIM)
    s.obj("Numeric", "Slot 1-6 elapsed", "D40-D57", "display h:m:s", "-",
          "gSlotH / gSlotM / gSlotS")
    s.obj("Parts/bar", "Slot 1-6 progress", "D64-D69", "bar graph 0-100", "-",
          "gSlotPct[1..6]")
    s.obj("Lamp", "Slot 1-6 running", "M4000-M4005", "bit lamp", "-", "gSlotRunning")

    y4 = y3 + 126
    cells = [("ACTIVE ALARMS", "3", ALARM, "M700-M713"),
             ("UNACCOUNTED LOTS", "3", WARN, "D24"),
             ("SLOTS CURING", "3 of 6", TXT, "D11")]
    for i, (lab, val, col, dev) in enumerate(cells):
        cx = 12 + i * 260
        s.rect(cx, y4, 252, 40, PANEL_2, col if col != TXT else LINE_2,
               sw=2 if col != TXT else 1)
        s.txt(cx + 12, y4 + 17, lab, 10, TXT_DIM, weight="bold")
        s.txt(cx + 12, y4 + 34, val, 15, col, weight="bold", mono=True)
        s.obj("Numeric", lab.title(), dev, "display", "-", "")

    s.footer("HOME")
    return s


# ===================================================================== B-1100
def b1100():
    s = Screen("B-1100", "CURE SLOT TIMERS", role="MAINT")
    s.header()
    y = s.banner("CURE TIMERS PAUSED  -  OVEN NOT FIT TO CURE", WARN,
                 sub="high-limit thermostat tripped; timers resume when it is reset")

    data = [("1", "CURING", "01:14:22", 62, "46"), ("2", "EMPTY", "00:00:00", 0, "-"),
            ("3", "CURING", "01:45:10", 88, "15"), ("4", "COMPLETE", "02:00:00", 100, "0"),
            ("5", "EMPTY", "00:00:00", 0, "-"), ("6", "CURING", "00:41:05", 34, "79")]
    for i, (n, st, el, pct, rem) in enumerate(data):
        x = 12 + (i % 3) * 259
        yy = y + (i // 3) * 116
        s.rect(x, yy, 251, 108, PANEL, LINE_2)
        col = {"CURING": RUN, "COMPLETE": INFO, "EMPTY": TXT_DIM}[st]
        s.txt(x + 12, yy + 22, f"SLOT {n}", 15, TXT, weight="bold")
        s.rect(x + 150, yy + 8, 92, 20, "#FFFFFF", col, r=10)
        s.txt(x + 196, yy + 22, st, 11, col, "middle", weight="bold")
        s.txt(x + 12, yy + 52, el, 26, TXT if st != "EMPTY" else TXT_DIM,
              weight="bold", mono=True)
        s.bar(x + 12, yy + 60, 227, 8, pct, col if st != "EMPTY" else OFF)
        s.txt(x + 12, yy + 84, f"remaining {rem} min" if st == "CURING" else
              ("ready to unload" if st == "COMPLETE" else "not loaded"),
              11, TXT_DIM)
        if st == "EMPTY":
            s.button(x + 150, yy + 72, 89, 28, "START", "go", size=12)
        elif st == "COMPLETE":
            s.button(x + 150, yy + 72, 89, 28, "RESET", "info", size=12)
        else:
            s.button(x + 150, yy + 72, 89, 28, "RESET", "neutral", size=12,
                     enabled=False)
    s.obj("Numeric", "Slot 1-6 elapsed h/m/s", "D40-D57", "display", "-",
          "gSlotH / gSlotM / gSlotS")
    s.obj("Numeric", "Slot 1-6 remaining", "D58-D63", "display, min", "-",
          "gSlotRemainMin")
    s.obj("Switch", "Slot 1-6 START", "M800-M805", "momentary set", "-",
          "gHmiSlotStart, hidden when running")
    s.obj("Switch", "Slot 1-6 RESET", "M810-M815", "momentary set", "-",
          "gHmiSlotReset, disabled unless complete")
    s.obj("Lamp", "Cure timers paused", "M62", "bit lamp + banner", "-",
          "gSlotTimersPaused")

    s.rect(12, 348, 540, 46, PANEL_2, LINE_2)
    s.txt(26, 368, "WHILE THE TIMERS ARE PAUSED", 10, TXT_DIM, weight="bold")
    s.txt(26, 385, "Elapsed time is held, not lost. Each cure still needs its full "
                   "remaining time once the oven recovers.", 11, TXT)
    s.button(560, 348, 228, 46, "EARLY RESET", "warn", size=13,
             sub="maintenance only")
    s.obj("Switch", "Go to early reset", "M58", "screen -> B-1700", "MAINT",
          "visible only while gMaintLoggedIn")
    s.footer("SLOTS")
    return s


# ===================================================================== B-1200
def b1200():
    s = Screen("B-1200", "COUNTERS", role="QUALITY")
    s.header()
    y = BODY_Y + 10

    s.txt(20, y + 14, "DOOR", 12, TXT_DIM, weight="bold")
    s.value(12, y + 22, 190, "OPENED", "1 284", "", 30)
    s.value(210, y + 22, 190, "CLOSED", "1 283", "", 30)
    s.obj("Numeric", "Door opened count", "D4020", "display", "-", "gCntDoorOpen")
    s.obj("Numeric", "Door closed count", "D4022", "display", "-", "gCntDoorClose")

    s.txt(420, y + 14, "PRODUCTION", 12, TXT_DIM, weight="bold")
    s.value(412, y + 22, 122, "LOADED", "412", "", 28)
    s.value(542, y + 22, 122, "UNLOADED", "409", "", 28)
    s.value(672, y + 22, 116, "EARLY", "3", "", 28, WARN)
    s.obj("Numeric", "Lots loaded", "D4024", "display", "-", "gCntLotsLoaded")
    s.obj("Numeric", "Lots unloaded", "D4026", "display", "-", "gCntLotsUnloaded")
    s.obj("Numeric", "Early resets", "D4028", "display", "-", "gCntEarlyReset")

    y2 = y + 98
    s.rect(12, y2, 776, 92, "#F6E9E7", ALARM, sw=2)
    s.txt(26, y2 + 24, "UNACCOUNTED LOTS", 13, ALARM, weight="bold")
    s.txt(26, y2 + 60, "3", 38, ALARM, weight="bold", mono=True)
    s.txt(70, y2 + 46, "loaded  -  unloaded  -  still curing", 12, TXT_DIM)
    s.txt(70, y2 + 62, "Every unit is a cure cut short with the maintenance passcode.",
          11, TXT)
    s.txt(70, y2 + 76, "Each one is in the PLC event log with the slot and how many "
                       "minutes it was short.", 11, TXT)
    s.obj("Numeric", "Unaccounted lots", "D24", "display, 32-bit", "-",
          "gLotsUnaccounted")
    s.obj("Lamp", "Mismatch", "M712", "bit lamp, background red", "-",
          "gAlmLotMismatch")

    y3 = y2 + 102
    s.txt(20, y3 + 14, "RUNNING HOURS", 12, TXT_DIM, weight="bold")
    for i, (lab, dev, val) in enumerate([("HEATER", "D19", "2 841"),
                                         ("BLOWER 1", "D20", "3 902"),
                                         ("BLOWER 2", "D21", "3 877")]):
        s.value(12 + i * 190, y3 + 22, 182, lab, val, "h", 24)
        s.obj("Numeric", f"{lab.title()} run hours", dev, "display, h", "-", "")

    s.button(586, y3 + 22, 202, 52, "RESET COUNTERS", "info",
             sub="quality team only")
    s.obj("Switch", "Go to counter reset", "M60", "screen -> B-1800", "QUALITY",
          "visible only while gQualityLoggedIn")

    y4 = y3 + 92
    s.rect(12, y4, 776, 44, PANEL, LINE_2)
    s.txt(24, y4 + 18, "MOST RECENT EARLY RESETS", 10, TXT_DIM, weight="bold")
    recents = [("06-09  11:47", "slot 3", "45 min short"),
               ("04-09  16:02", "slot 1", "22 min short"),
               ("02-09  09:35", "slot 5", "61 min short")]
    for i, (when, slot, short) in enumerate(recents):
        rx = 24 + i * 254
        s.txt(rx, y4 + 35, when, 11, TXT, mono=True)
        s.txt(rx + 96, y4 + 35, slot, 11, TXT, weight="bold")
        s.txt(rx + 146, y4 + 35, short, 11, WARN, weight="bold")
    s.obj("Alarm history", "Recent early resets", "GOT alarm history",
          "filtered on the early-reset events", "-",
          "full record is on the PLC SD card")
    s.footer("COUNTERS")
    return s


# ===================================================================== B-1300
def b1300():
    s = Screen("B-1300", "ALARMS", role="-")
    s.header()
    y = BODY_Y + 8
    s.rect(12, y, 776, 268, PANEL, LINE_2)
    hdr = ["", "TIME", "ALARM", "STATUS"]
    xs = [24, 60, 180, 690]
    for x, h in zip(xs, hdr):
        s.txt(x, y + 22, h, 11, TXT_DIM, weight="bold")
    s.line(20, y + 30, 780, y + 30, LINE_2)
    rows = [("14:21", "DOOR OPEN LONGER THAN 10 MIN", "ACTIVE", ALARM),
            ("14:19", "CURE TIMERS PAUSED - OVEN NOT FIT", "ACTIVE", WARN),
            ("13:58", "HIGH-LIMIT THERMOSTAT TRIPPED", "ACTIVE", ALARM),
            ("11:04", "LOTS LOADED / UNLOADED MISMATCH", "ACCEPTED", WARN),
            ("09:12", "BLOWER 2 OVERLOAD TRIPPED", "CLEARED", TXT_DIM),
            ("08:47", "FAILURE TO REACH SETPOINT", "CLEARED", TXT_DIM)]
    for i, (t, name, st, col) in enumerate(rows):
        ry = y + 40 + i * 36
        if i % 2 == 0:
            s.rect(20, ry - 4, 760, 32, PANEL_2, None, r=2)
        s.circle(30, ry + 12, 6, col)
        s.txt(60, ry + 17, t, 14, TXT, mono=True)
        s.txt(180, ry + 17, name, 14, TXT if st != "CLEARED" else TXT_DIM,
              weight="bold" if st == "ACTIVE" else "normal")
        s.txt(690, ry + 17, st, 11, col, weight="bold")
    s.obj("Alarm display", "Advanced user alarm", "M700-M713",
          "alarm observation, 14 points", "-", "see docs/alarm-list.csv")

    s.button(12, y + 282, 250, 54, "ACCEPT", "warn",
             sub="silences the hooter, the lamp stays until the cause clears")
    s.obj("Switch", "Alarm accept", "M824", "momentary set", "-", "gHmiAlarmAccept")
    s.button(270, y + 282, 250, 54, "HISTORY", "neutral", sub="7 day log")
    s.rect(528, y + 282, 260, 54, PANEL_2, LINE_2)
    s.txt(540, y + 302, "ACTIVE / UNACCEPTED", 11, TXT_DIM, weight="bold")
    s.txt(540, y + 326, "3", 22, ALARM, weight="bold", mono=True)
    s.txt(566, y + 326, "of 14 configured alarms", 11, TXT_DIM)
    s.footer("ALARMS")
    return s


# ===================================================================== B-1400
def b1400():
    s = Screen("B-1400", "MANUAL TEST", role="MAINT")
    s.header()
    y = s.banner("MANUAL TEST ACTIVE  -  NORMAL INTERLOCKS BYPASSED", WARN,
                 sub="exits by itself in 04:12, or when the door opens")
    s.obj("Numeric", "Manual timeout remaining", "D9", "display, s", "MAINT",
          "gManualTmoAcc counts up to gSetManualTmoS")

    for i, (lab, dev, fb, kind) in enumerate(
            [("BLOWER 1", "M832", "M15", "go"), ("BLOWER 2", "M833", "M16", "go"),
             ("HEATER", "M834", "M17", "warn")]):
        x = 12 + i * 259
        s.rect(x, y, 251, 150, PANEL, LINE_2)
        s.txt(x + 12, y + 24, lab, 15, TXT, weight="bold")
        s.button(x + 12, y + 36, 227, 62, "PRESS AND HOLD", kind, size=14,
                 sub="runs only while touched")
        s.circle(x + 26, y + 122, 9, OFF, "#9AA2AC", 2)
        s.txt(x + 44, y + 118, "contactor feedback", 10, TXT_DIM)
        s.txt(x + 44, y + 132, "not confirmed", 12, TXT_DIM, weight="bold")
        s.obj("Switch", f"Manual {lab.title()}", dev, "momentary while touched",
              "MAINT", "cleared automatically when manual mode drops")
        s.obj("Lamp", f"{lab.title()} contactor feedback", fb, "bit lamp", "MAINT",
              "proves the contactor actually moved")

    y2 = y + 160
    s.rect(12, y2, 520, 76, PANEL_2, LINE_2)
    s.txt(24, y2 + 22, "CONDITIONS REQUIRED", 11, TXT_DIM, weight="bold")
    conds = [("E-stop released", True), ("door closed", True),
             ("no overload tripped", True), ("high-limit healthy", True),
             ("no cure running", False)]
    for i, (c, ok) in enumerate(conds):
        cx = 24 + (i % 3) * 168
        cy = y2 + 44 + (i // 3) * 20
        s.circle(cx + 5, cy - 4, 5, RUN if ok else ALARM)
        s.txt(cx + 16, cy, c, 11, TXT if ok else ALARM)
    s.obj("Lamp", "Manual permit", "M54", "bit lamp", "MAINT", "gManualPermit")

    s.button(540, y2, 248, 76, "EXIT MANUAL TEST", "stop")
    s.obj("Switch", "Exit manual test", "M828", "momentary set", "MAINT",
          "gHmiManualExit")
    s.footer("HOME")
    return s


# ===================================================================== B-1500
def b1500():
    s = Screen("B-1500", "SETTINGS", role="MAINT")
    s.header()
    y = BODY_Y + 8
    rows = [("Heat-up watchdog", "D4100", "60", "min", "10 - 240"),
            ("Door watchdog", "D4101", "600", "s", "60 - 1800"),
            ("Chatter transitions", "D4102", "8", "", "4 - 50"),
            ("Chatter window", "D4103", "10", "s", "5 - 60"),
            ("Heater minimum ON", "D4104", "20", "s", "5 - 120"),
            ("Heater minimum OFF", "D4105", "20", "s", "5 - 120"),
            ("Manual test timeout", "D4106", "300", "s", "60 - 900"),
            ("Auto-logout", "D4107", "300", "s", "60 - 900"),
            ("Cure time", "D4108", "7200", "s", "fixed at 2 h")]
    s.rect(12, y, 470, 300, PANEL, LINE_2)
    s.txt(24, y + 22, "TIMINGS", 12, TXT_DIM, weight="bold")
    for i, (lab, dev, val, unit, rng) in enumerate(rows):
        ry = y + 36 + i * 29
        if i % 2 == 0:
            s.rect(20, ry - 4, 454, 27, PANEL_2, None, r=2)
        s.txt(28, ry + 14, lab, 13, TXT)
        s.rect(300, ry - 2, 74, 24, "#FFFFFF", INFO, sw=2, r=3)
        s.txt(337, ry + 14, val, 14, TXT, "middle", weight="bold", mono=True)
        s.txt(380, ry + 14, unit, 11, TXT_DIM)
        s.txt(468, ry + 14, rng, 10, TXT_DIM, "end")
        s.obj("Numeric input", lab, dev, "write, range checked", "MAINT", rng)

    s.rect(490, y, 298, 142, PANEL, LINE_2)
    s.txt(502, y + 22, "OPTIONS", 12, TXT_DIM, weight="bold")
    opts = [("Cure timers pause on a fault", "M4021", True),
            ("Heater requires airflow", "M4020", False)]
    for i, (lab, dev, on) in enumerate(opts):
        oy = y + 40 + i * 46
        s.rect(502, oy, 274, 38, PANEL_2, LINE_2)
        s.rect(508, oy + 6, 52, 26, RUN if on else "#CFD4DA", None, r=13)
        s.circle(547 if on else 521, oy + 19, 10, "#FFFFFF")
        s.txt(572, oy + 24, lab, 12, TXT, weight="bold" if on else "normal")
        s.obj("Switch", lab, dev, "alternate", "MAINT", "latched option bit")

    s.rect(490, y + 152, 298, 148, PANEL, LINE_2)
    s.txt(502, y + 174, "PASSCODES", 12, TXT_DIM, weight="bold")
    s.txt(502, y + 196, "Change both from the shipped defaults", 11, TXT_DIM)
    s.txt(502, y + 210, "before handover.", 11, TXT_DIM)
    s.button(502, y + 220, 130, 40, "MAINTENANCE", "warn", size=11)
    s.button(644, y + 220, 132, 40, "QUALITY", "info", size=11)
    s.txt(502, y + 288, "Quality's code is changed by quality, on their own login.",
          10, TXT_DIM, style="italic")
    s.obj("Numeric input", "Maintenance passcode", "D4110", "write, masked", "MAINT", "")
    s.obj("Numeric input", "Quality passcode", "D4111", "write, masked", "QUALITY",
          "changed under the quality login only")
    s.footer("LOGIN")
    return s


# ===================================================================== B-1600
def b1600():
    s = Screen("B-1600", "LOGIN", role="-")
    s.header()
    y = BODY_Y + 12

    s.rect(12, y, 330, 300, PANEL, LINE_2)
    s.txt(28, y + 26, "PASSCODE", 12, TXT_DIM, weight="bold")
    s.rect(28, y + 36, 286, 44, "#FFFFFF", INFO, sw=2)
    s.txt(171, y + 68, "* * * *", 26, TXT, "middle", weight="bold", mono=True)
    s.obj("Numeric input", "Passcode entry", "D27", "write, masked, 4 digits", "-",
          "gHmiPasscodeEntry, cleared by the PLC after every attempt")
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "CLR", "0", "DEL"]
    for i, k in enumerate(keys):
        kx = 28 + (i % 3) * 98
        ky = y + 92 + (i // 3) * 50
        s.button(kx, ky, 90, 44, k, "neutral" if k.isdigit() else "info", size=17)
    s.obj("Switch", "Keypad 0-9 / CLR / DEL", "D27", "GOT keypad", "-", "")

    s.rect(354, y, 434, 142, PANEL, LINE_2)
    s.txt(370, y + 26, "LOG IN AS", 12, TXT_DIM, weight="bold")
    s.button(370, y + 40, 200, 84, "MAINTENANCE", "warn", size=15,
             sub="early reset  -  manual test  -  settings")
    s.button(582, y + 40, 190, 84, "QUALITY", "info", size=15,
             sub="resetting the counters")
    s.obj("Switch", "Login maintenance", "M829",
          "write D27 then set M829, ONE touch action", "-", "gHmiMaintLoginReq")
    s.obj("Switch", "Login quality", "M835",
          "write D27 then set M835, ONE touch action", "-", "gHmiQualityLoginReq")

    s.rect(354, y + 152, 434, 76, "#F6E9E7", ALARM, sw=2)
    s.txt(370, y + 178, "LOCKED OUT", 13, ALARM, weight="bold")
    s.txt(370, y + 204, "247", 24, ALARM, weight="bold", mono=True)
    s.txt(436, y + 204, "seconds remaining  -  3 wrong entries", 12, TXT)
    s.obj("Numeric", "Lockout remaining", "D26", "display, s", "-", "gLockoutAcc")
    s.obj("Lamp", "Locked out", "M61", "bit lamp, shows this panel", "-",
          "gLockoutActive")

    s.button(354, y + 240, 210, 60, "LOG OUT", "neutral")
    s.obj("Switch", "Log out", "M830", "momentary set", "-", "gHmiLogout")
    s.rect(576, y + 240, 212, 60, PANEL_2, LINE_2)
    s.txt(588, y + 262, "AUTO-LOGOUT", 11, TXT_DIM, weight="bold")
    s.txt(588, y + 286, "after 5 minutes idle", 12, TXT)

    s.rect(12, y + 312, 776, 44, PANEL_2, LINE_2)
    s.txt(28, y + 332, "TWO SEPARATE PASSCODES  -  NEITHER ROLE CAN DO THE OTHER'S JOB",
          11, TXT_DIM, weight="bold")
    s.txt(28, y + 348, "Maintenance cuts a cure short; quality, and only quality, "
                       "clears the counters that record it.", 11, TXT)
    s.footer("LOGIN")
    return s


# ===================================================================== B-1700
def b1700():
    s = Screen("B-1700", "EARLY RESET  -  MAINTENANCE", role="MAINT")
    s.header()
    y = s.banner("THIS ENDS A CURE BEFORE ITS 2 HOURS ARE UP", WARN,
                 sub="it is recorded against your login with the slot and the minutes remaining, "
                     "and it does NOT count as a lot unloaded")

    data = [("1", "01:14:22", "46", True), ("2", "-", "-", False),
            ("3", "01:45:10", "15", True), ("4", "02:00:00", "0", False),
            ("5", "-", "-", False), ("6", "00:41:05", "79", True)]
    for i, (n, el, rem, active) in enumerate(data):
        ry = y + i * 42
        s.rect(12, ry, 776, 38, PANEL if active else PANEL_2, LINE_2)
        s.txt(28, ry + 25, f"SLOT {n}", 14, TXT if active else TXT_DIM, weight="bold")
        s.txt(120, ry + 25, el, 16, TXT if active else TXT_DIM, mono=True)
        s.txt(250, ry + 25, f"{rem} min remaining" if active else
              ("complete - use the normal reset" if n == "4" else "not loaded"),
              12, TXT_DIM)
        if active:
            s.button(600, ry + 4, 176, 30, "EARLY RESET", "stop", size=12)
    s.obj("Switch", "Slot 1-6 early reset", "M810-M815",
          "momentary set, confirm dialogue first", "MAINT",
          "same bit as the normal reset; the PLC decides which rule applies")
    s.obj("Numeric", "Slot elapsed / remaining", "D40-D63", "display", "MAINT", "")
    s.footer("SLOTS")
    return s


# ===================================================================== B-1800
def b1800():
    s = Screen("B-1800", "COUNTER RESET  -  QUALITY", role="QUALITY")
    s.header()
    y = s.banner("RESETTING A COUNTER CLEARS THE PRODUCTION RECORD", INFO,
                 sub="take the readings first; the reset itself is written to the 7 day log")

    s.rect(12, y, 380, 130, PANEL, LINE_2)
    s.txt(28, y + 26, "DOOR COUNTERS", 13, TXT, weight="bold")
    s.txt(28, y + 50, "opened", 12, TXT_DIM)
    s.txt(200, y + 50, "1 284", 16, TXT, "end", mono=True, weight="bold")
    s.txt(28, y + 72, "closed", 12, TXT_DIM)
    s.txt(200, y + 72, "1 283", 16, TXT, "end", mono=True, weight="bold")
    s.button(220, y + 40, 152, 74, "RESET", "info")
    s.obj("Switch", "Reset door counters", "M825",
          "momentary set, confirm dialogue first", "QUALITY", "gHmiResetDoorCnt")

    s.rect(408, y, 380, 130, PANEL, LINE_2)
    s.txt(424, y + 26, "LOT COUNTERS", 13, TXT, weight="bold")
    for i, (lab, val, col) in enumerate([("loaded", "412", TXT),
                                         ("unloaded", "409", TXT),
                                         ("early resets", "3", WARN)]):
        s.txt(424, y + 50 + i * 22, lab, 12, TXT_DIM)
        s.txt(596, y + 50 + i * 22, val, 16, col, "end", mono=True, weight="bold")
    s.button(616, y + 40, 152, 74, "RESET", "info")
    s.obj("Switch", "Reset lot counters", "M826",
          "momentary set, confirm dialogue first", "QUALITY", "gHmiResetLotCnt")

    y2 = y + 142
    s.rect(12, y2, 776, 96, "#EEF3F7", INFO, sw=2)
    s.txt(28, y2 + 26, "WHY ONLY QUALITY CAN DO THIS", 13, INFO, weight="bold")
    for i, t in enumerate([
        "Maintenance is who cuts a cure short with an early reset. If the maintenance passcode could also",
        "clear these counters, the person who ended a cure early could erase the record of having done it.",
        "The two passcodes are held in the PLC, not in this panel, so replacing the HMI does not change the rule."]):
        s.txt(28, y2 + 48 + i * 16, t, 11, TXT)
    s.footer("COUNTERS")
    return s


# ===================================================================== B-1900
def b1900():
    s = Screen("B-1900", "EVENT HISTORY", role="-")
    s.header()
    y = BODY_Y + 8
    s.rect(12, y, 776, 250, PANEL, LINE_2)
    for x, h in zip([24, 130, 250, 690], ["DATE", "TIME", "EVENT", "DETAIL"]):
        s.txt(x, y + 22, h, 11, TXT_DIM, weight="bold")
    s.line(20, y + 30, 780, y + 30, LINE_2)
    rows = [("06-09", "14:21", "Door open longer than 10 min", "600 s", ALARM),
            ("06-09", "13:58", "Cure timers paused", "3 slots", WARN),
            ("06-09", "11:47", "Slot 3  EARLY RESET", "45 min short", ALARM),
            ("06-09", "11:46", "MAINTENANCE logged in", "", TXT_DIM),
            ("06-09", "10:12", "Slot 1 reached 2 h", "", TXT_DIM),
            ("06-09", "08:12", "Slot 1 started", "", TXT_DIM),
            ("05-09", "17:44", "Failed login attempt", "attempt 2", WARN)]
    for i, (d, t, e, det, col) in enumerate(rows):
        ry = y + 40 + i * 30
        if i % 2 == 0:
            s.rect(20, ry - 4, 760, 26, PANEL_2, None, r=2)
        s.txt(24, ry + 14, d, 12, TXT_DIM, mono=True)
        s.txt(130, ry + 14, t, 12, TXT, mono=True)
        s.txt(250, ry + 14, e, 13, col if col != TXT_DIM else TXT,
              weight="bold" if col != TXT_DIM else "normal")
        s.txt(690, ry + 14, det, 11, TXT_DIM)
    s.obj("Alarm history", "Event log view", "SD card",
          "GOT alarm history + FX5U logging CSV", "-", "see docs/event-codes.md")

    s.button(12, y + 264, 250, 54, "EXPORT TO USB", "info",
             sub="this panel's alarm history, as CSV")
    s.obj("Switch", "USB export", "GOT alarm history",
          "GT Designer3 alarm history CSV output to USB", "-",
          "exports the GOT's own history; the 7 day event log lives on the PLC SD card")
    s.rect(270, y + 264, 518, 54, PANEL_2, LINE_2)
    s.txt(284, y + 286, "RETENTION", 11, TXT_DIM, weight="bold")
    s.txt(284, y + 304, "This panel keeps the alarm history. The full 7 day event log "
                        "- every slot start, early", 11, TXT)
    s.txt(284, y + 318, "reset, login and counter reset - is written to the SD card in "
                        "the PLC, not here.", 11, TXT)
    s.footer("HISTORY")
    return s


ALL = [b1000, b1100, b1200, b1300, b1400, b1500, b1600, b1700, b1800, b1900]
