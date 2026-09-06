"""Behavioural tests for the OVN-2026-01 PLC program.

Every test maps to a line of the specification. Run:  python3 test/test_logic.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import Oven

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  -> ' + detail if detail and not cond else ''}")


def t(title):
    print(f"\n{title}")


# =============================================================== blowers + door
def test_blowers_and_door():
    t("1. Blower start/stop and the door interlock")
    o = Oven(); o.run(2)

    o.press("X1"); o.run(1)
    check("blower 1 starts from the panel push-button", o.Y0)

    o.press("X3"); o.run(1)
    check("blower 2 starts from the panel push-button", o.Y1)

    o.X6 = True; o.run(25)
    check("heater is ON before the door opens", o.Y2)

    o.X5 = False; o.step(); o.step()
    check("both blowers stop the instant the door opens", not o.Y0 and not o.Y1)
    check("heater STAYS ON with the door open", o.Y2)

    o.run(5)
    o.X5 = True; o.run(2)
    check("both blowers restart by themselves when the door closes", o.Y0 and o.Y1)
    check("heater never dropped", o.Y2)

    t("2. A stop press during a door-open must not auto-restart")
    o.X5 = False; o.run(1)
    o.X2 = False; o.run(1); o.X2 = True      # blower 1 STOP pressed while open
    o.X5 = True;  o.run(2)
    check("blower 1 stays off after a stop press", not o.Y0)
    check("blower 2 still restarts", o.Y1)

    t("3. Overload and emergency stop cancel the run request")
    o = Oven(); o.run(2); o.press("X1"); o.run(1)
    o.X10 = True; o.run(1)
    check("blower 1 drops on its overload", not o.Y0)
    o.X10 = False; o.run(2)
    check("blower 1 does NOT restart when the overload is cleared", not o.Y0)

    o.press("X1"); o.run(1)
    o.X0 = False; o.run(1)
    check("emergency stop drops the blower", not o.Y0)
    check("emergency stop drops the heater", not o.Y2)
    o.X0 = True; o.run(2)
    check("nothing restarts when the E-stop is released", not o.Y0 and not o.Y1)


# ======================================================================= heater
def test_heater():
    t("4. Heater anti-chatter (minimum ON / minimum OFF = 20 s)")
    o = Oven(); o.run(2)
    o.X6 = True
    o.run(5)
    check("heater waits out the min-OFF delay after power-up", not o.Y2)
    o.run(16)
    check("heater comes on after 20 s", o.Y2)

    o.X6 = False; o.run(2)
    check("heater holds ON through the minimum ON time", o.Y2)
    o.run(20)
    check("heater drops once the minimum ON time has run", not o.Y2)

    t("5. A permissive overrides the minimum-ON hold")
    o = Oven(); o.run(2); o.X6 = True; o.run(22)
    check("heater is on", o.Y2)
    o.X13 = False; o.step()
    check("high-limit trip drops the heater in the same scan", not o.Y2)
    o.X13 = True

    t("6. Heat-up watchdog")
    o = Oven(); o.run(2)
    o.X6 = True
    o.run(59 * 60)
    check("no watchdog alarm at 59 minutes of continuous demand", not o.gAlmHeatUp)
    o.run(61)
    check("watchdog alarm at 60 minutes", o.gAlmHeatUp)
    check("watchdog does NOT trip the heater", o.Y2)
    o.X6 = False; o.run(2)
    check("watchdog clears when the controller finally drops out", not o.gAlmHeatUp)

    o = Oven(); o.run(2)
    for _ in range(20):                      # normal cycling: 30 min on, 1 min off
        o.X6 = True;  o.run(30 * 60)
        o.X6 = False; o.run(60)
    check("normal PID cycling never raises the watchdog", not o.gAlmHeatUp)


# ========================================================================= door
def test_door_watchdogs():
    t("7. Door counters")
    o = Oven(); o.run(2)
    for _ in range(3):
        o.X5 = False; o.run(3)
        o.X5 = True;  o.run(3)
    check("3 opens counted", o.gCntDoorOpen == 3, f"got {o.gCntDoorOpen}")
    check("3 closes counted", o.gCntDoorClose == 3, f"got {o.gCntDoorClose}")

    t("8. Watchdog A - no 'door closed' signal for 10 minutes")
    o = Oven(); o.run(2)
    o.X5 = False
    o.run(9 * 60)
    check("no alarm at 9 minutes", not o.gAlmDoorNotClosed)
    check("Y12 door alarm output still off", not o.Y12)
    o.run(61)
    check("alarm at 10 minutes", o.gAlmDoorNotClosed)
    check("Y12 door alarm output energised", o.Y12)
    o.X5 = True; o.run(2)
    check("alarm clears when the door closes", not o.gAlmDoorNotClosed and not o.Y12)

    t("9. Watchdog B - pulsating (chattering) door signal")
    o = Oven(); o.run(2)
    o.press("X1"); o.run(1)
    check("blower running before the chatter", o.Y0)
    before_open, before_close = o.gCntDoorOpen, o.gCntDoorClose
    for _ in range(6):                       # 12 transitions inside 10 s
        o.X5 = False; o.run(0.2)
        o.X5 = True;  o.run(0.2)
    check("chatter alarm raised", o.gAlmDoorChatter)
    check("Y12 door alarm output energised", o.Y12)
    check("chatter did NOT inflate the door-open counter",
          o.gCntDoorOpen == before_open, f"got {o.gCntDoorOpen}")
    check("chatter did NOT inflate the door-close counter",
          o.gCntDoorClose == before_close, f"got {o.gCntDoorClose}")
    o.run(3)
    check("blower held off while the chatter alarm stands", not o.Y0)

    o.X5 = True; o.run(12)
    o.press("X17"); o.run(2)                 # accept, signal now settled
    check("chatter alarm clears on accept once settled", not o.gAlmDoorChatter)
    check("Y12 releases", not o.Y12)
    o.run(2)
    check("blower comes back after the alarm is accepted", o.Y0)

    t("10. A normal door cycle must not look like chatter")
    o = Oven(); o.run(2)
    for _ in range(3):
        o.X5 = False; o.run(20)
        o.X5 = True;  o.run(20)
    check("three slow door cycles raise no chatter alarm", not o.gAlmDoorChatter)


# ================================================================= slot timers
def test_slot_timers():
    t("11. Slot timer runs 2 h and only then resets")
    o = Oven(); o.run(2)
    o.gHmiSlotStart[1] = True; o.run(1)
    check("slot 1 running", o.gSlotRunning[1])
    check("lots loaded = 1", o.gCntLotsLoaded == 1)
    check("cycle lamp on", o.Y10)

    o.gHmiSlotStart[1] = True; o.run(1)
    check("a running slot cannot be started again", o.gCntLotsLoaded == 1)

    o.run(60 * 60)
    o.gHmiSlotReset[1] = True; o.run(1)
    check("reset refused at 1 h with no login", o.gSlotRunning[1])
    check("no unload counted", o.gCntLotsUnloaded == 0)

    o.run(60 * 60 + 5)
    check("slot complete at 2 h", o.gSlotComplete[1])
    check("elapsed held at 7200 s", o.gSlotElapsed[1] == 7200, f"got {o.gSlotElapsed[1]}")

    o.gHmiSlotReset[1] = True; o.run(1)
    check("reset accepted once complete", not o.gSlotRunning[1])
    check("lots unloaded = 1", o.gCntLotsUnloaded == 1)
    check("nothing unaccounted", o.gLotsUnaccounted == 0)
    check("no mismatch alarm", not o.gAlmLotMismatch)

    t("12. Early reset needs the maintenance password and is NOT an unload")
    o = Oven(); o.run(2)
    o.gHmiSlotStart[2] = True; o.run(1)
    o.run(45 * 60)
    o.gHmiSlotReset[2] = True; o.run(1)
    check("early reset refused without login", o.gSlotRunning[2])

    o.login('maint'); o.run(1)
    o.gHmiSlotReset[2] = True; o.run(1)
    check("early reset accepted with the maintenance code", not o.gSlotRunning[2])
    check("early reset counted", o.gCntEarlyReset == 1)
    check("early reset NOT counted as an unload", o.gCntLotsUnloaded == 0)
    check("one lot unaccounted", o.gLotsUnaccounted == 1, f"got {o.gLotsUnaccounted}")
    check("mismatch alarm raised", o.gAlmLotMismatch)
    ev = [e for e in o.events if e[1] == 42]
    check("early reset written to the event log with the minutes elapsed",
          len(ev) == 1 and ev[0][3] == 45, f"got {ev}")

    t("12b. The HMI slot state word tracks the two state bits")
    o = Oven(); o.run(2)
    check("all slots read EMPTY at rest", all(o.gSlotState[k] == 0 for k in range(1, 7)))
    o.gHmiSlotStart[3] = True; o.run(2)
    check("started slot reads CURING", o.gSlotState[3] == 1)
    check("its neighbours still EMPTY", o.gSlotState[2] == 0 and o.gSlotState[4] == 0)
    o.run(2 * 60 * 60 + 5)
    check("finished slot reads COMPLETE", o.gSlotState[3] == 2)
    o.gHmiSlotReset[3] = True; o.run(2)
    check("reset slot returns to EMPTY", o.gSlotState[3] == 0)

    t("13. Six slots are independent")
    o = Oven(); o.run(2)
    for s in (1, 3, 5):                      # started in the SAME scan
        o.gHmiSlotStart[s] = True
    o.run(1)
    o.run(30 * 60)
    check("3 slots running", o.gSlotsActive == 3)
    check("slots 2, 4, 6 untouched",
          o.gSlotElapsed[2] == 0 and o.gSlotElapsed[4] == 0 and o.gSlotElapsed[6] == 0)
    check("running slots track together at 30 min",
          o.gSlotElapsed[1] == o.gSlotElapsed[3] == o.gSlotElapsed[5]
          and abs(o.gSlotElapsed[1] - 1800) <= 2,
          f"got {[o.gSlotElapsed[i] for i in (1, 3, 5)]}")
    check("loaded 3, unloaded 0, none unaccounted (all still running)",
          o.gCntLotsLoaded == 3 and o.gCntLotsUnloaded == 0 and o.gLotsUnaccounted == 0)

    t("14. Power failure pauses a cure and it resumes from the accumulated value")
    o = Oven(); o.run(2)
    o.gHmiSlotStart[1] = True; o.run(1)
    o.press("X1"); o.run(1)
    check("blower running before the outage", o.Y0)
    o.run(40 * 60)
    elapsed = o.gSlotElapsed[1]
    o.power_cycle()
    o.step(); o.step()                       # supply restored, 2 scans
    check("slot timer resumed, not restarted", o.gSlotElapsed[1] == elapsed,
          f"{o.gSlotElapsed[1]} vs {elapsed}")
    check("slot still running", o.gSlotRunning[1])
    check("counters survived", o.gCntLotsLoaded == 1)
    check("blower did NOT restart by itself after the outage", not o.Y0)
    resumed = o.gSlotElapsed[1]
    o.run(60)
    check("slot timer advances again", o.gSlotElapsed[1] == resumed + 60,
          f"{o.gSlotElapsed[1]} vs {resumed + 60}")


# ====================================================================== manual
def test_manual_and_counters():
    t("15. Manual test is password protected and guarded")
    o = Oven(); o.run(2)
    o.gHmiManualReq = True; o.run(1)
    check("manual test refused without login", not o.gManualMode)

    o.login('maint'); o.run(1)
    o.gHmiManualReq = True; o.run(1)
    check("manual test entered with the maintenance code", o.gManualMode)

    o.gHmiManBl1 = True; o.run(1)
    check("manual blower 1 runs", o.Y0)
    o.gHmiManHtr = True; o.run(1)
    check("manual heater runs", o.Y2)

    o.X5 = False; o.run(1)
    check("opening the door exits manual test", not o.gManualMode)
    check("manual outputs drop", not o.Y0 and not o.Y2)
    o.X5 = True; o.run(2)

    o.gHmiManualReq = True; o.run(1)
    check("manual test re-entered", o.gManualMode)
    o.run(301)
    check("manual test times out after 5 minutes", not o.gManualMode)

    t("16. Manual test is blocked during a cure")
    o = Oven(); o.run(2)
    o.login('maint'); o.run(1)
    o.gHmiSlotStart[1] = True; o.run(1)
    o.gHmiManualReq = True; o.run(1)
    check("manual test refused while a slot timer is running", not o.gManualMode)

    t("17. Counter resets are password protected")
    o = Oven(); o.run(2)
    for _ in range(2):
        o.X5 = False; o.run(3); o.X5 = True; o.run(3)
    o.gHmiResetDoorCnt = True; o.run(1)
    check("door counter reset refused with nobody logged in", o.gCntDoorOpen == 2)
    o.login('maint'); o.run(1)
    o.gHmiResetDoorCnt = True; o.run(1)
    check("door counter reset REFUSED for maintenance", o.gCntDoorOpen == 2)
    o.login('quality'); o.run(1)
    o.gHmiResetDoorCnt = True; o.run(1)
    check("door counter reset accepted for quality", o.gCntDoorOpen == 0)

    t("18. Separation of duties on the lot counters")
    o = Oven(); o.run(2)
    o.gHmiSlotStart[1] = True; o.run(1)
    o.login('maint'); o.run(1)
    o.gHmiSlotReset[1] = True; o.run(1)
    check("maintenance can cut a cure short", o.gCntEarlyReset == 1)
    check("it shows as unaccounted", o.gLotsUnaccounted == 1)
    o.gHmiResetLotCnt = True; o.run(1)
    check("maintenance CANNOT erase the record of its own early reset",
          o.gCntEarlyReset == 1 and o.gLotsUnaccounted == 1)
    o.login('quality'); o.run(1)
    o.gHmiResetLotCnt = True; o.run(1)
    check("quality can clear the lot counters", o.gCntEarlyReset == 0)

    t("19. Passcodes, wrong entries and lockout")
    o = Oven(); o.run(2)
    o.login('maint', 9999); o.run(1)
    check("wrong code refused", not o.gMaintLoggedIn)
    check("failed attempt counted", o.gFailedAttempts == 1)
    o.login('maint', 1111); o.run(1)
    o.login('maint', 2222); o.run(1)
    check("locked out after 3 failures", o.gLockoutActive)
    o.login('maint'); o.run(1)
    check("the CORRECT code is refused while locked out", not o.gMaintLoggedIn)
    o.run(301)
    check("lockout expires after 5 minutes", not o.gLockoutActive)
    o.login('maint'); o.run(1)
    check("correct code works again", o.gMaintLoggedIn)
    check("failed attempts logged", len([e for e in o.events if e[1] == 75]) == 3)

    t("20. The two roles are mutually exclusive")
    o = Oven(); o.run(2)
    o.login('maint'); o.run(1)
    check("maintenance in", o.gMaintLoggedIn and not o.gQualityLoggedIn)
    o.login('quality'); o.run(1)
    check("quality in, maintenance automatically out",
          o.gQualityLoggedIn and not o.gMaintLoggedIn)
    check("quality cannot enter manual test", not o.gManualPermit)
    o.gHmiLogout = True; o.run(1)
    check("logout clears both", not o.gMaintLoggedIn and not o.gQualityLoggedIn)

    t("21. Each role logs out on its own after 5 minutes idle")
    o = Oven(); o.run(2)
    o.login('quality'); o.run(1)
    check("logged in", o.gQualityLoggedIn)
    o.run(301)
    check("auto-logout after 5 minutes idle", not o.gQualityLoggedIn)


# ====================================================================== alarms
def test_alarms():
    t("19. Alarm handling, hooter and contactor feedback")
    o = Oven(); o.run(2)
    check("no alarm at rest", not o.gAnyAlarm)
    check("hooter silent", not o.Y11)

    o.X11 = True; o.run(1)
    check("blower 2 overload raises an alarm", o.gAlmBl2Ol and o.gAnyAlarm)
    check("hooter sounds", o.Y11)
    o.press("X17"); o.run(1)
    check("hooter silences on accept", not o.Y11)
    check("alarm still present", o.gAnyAlarm)

    o.X12 = True; o.run(1)
    check("a NEW alarm re-sounds the hooter while the first still stands", o.Y11)
    o.X11 = False; o.X12 = False; o.press("X17"); o.run(2)
    check("all clear", not o.gAnyAlarm and not o.Y11)

    t("20. Welded contactor detection")
    o = Oven(); o.run(2)
    o.press("X1"); o.run(1)
    check("blower 1 commanded on", o.Y0)
    o.autofeedback = False
    o.X14 = True                              # contact welded closed
    o.X2 = False; o.run(1); o.X2 = True       # stop it
    check("command removed", not o.Y0)
    o.run(2)
    check("welded -K1 detected within 1 s", o.gAlmK1Fault)

    t("21. Lamp test")
    o = Oven(); o.run(2)
    o.X17 = True; o.run(1)
    check("all lamps light", o.Y3 and o.Y4 and o.Y5 and o.Y6 and o.Y7 and o.Y10)
    check("hooter does not sound on a lamp test", not o.Y11)


def test_cure_gating():
    t("22. A cure timer stops on a fault and does NOT run on to completion")
    o = Oven(); o.run(2)
    o.gHmiSlotStart[1] = True; o.run(1)
    o.run(60 * 60)
    at_fault = o.gSlotElapsed[1]
    check("1 hour elapsed", abs(at_fault - 3600) <= 2, f"got {at_fault}")

    o.X13 = False                                  # high-limit trips
    o.run(2 * 60 * 60)                             # two hours of fault
    check("cure timer frozen through the fault", o.gSlotElapsed[1] == at_fault,
          f"{o.gSlotElapsed[1]} vs {at_fault}")
    check("slot did NOT complete during the fault", not o.gSlotComplete[1])
    check("paused indication shown", o.gSlotTimersPaused)
    check("cure-paused alarm raised", o.gAlmCurePaused)
    check("pause written to the event log", any(e[1] == 55 for e in o.events))

    o.X13 = True; o.run(2)
    check("paused indication clears", not o.gSlotTimersPaused)
    check("resume written to the event log", any(e[1] == 56 for e in o.events))
    o.run(60 * 60)
    check("cure completes only after a further hour of healthy running",
          o.gSlotComplete[1])

    t("23. A heat-up failure also holds the cure")
    o = Oven(); o.run(2)
    o.gHmiSlotStart[1] = True; o.run(1)
    o.X6 = True                                    # demand, oven never satisfied
    o.run(59 * 60)
    running = o.gSlotElapsed[1]
    check("cure advancing while the oven is still heating", running > 3000)
    o.run(120)
    check("heat-up watchdog fired", o.gAlmHeatUp)
    frozen = o.gSlotElapsed[1]
    o.run(30 * 60)
    check("cure timer held once the oven proves it cannot reach setpoint",
          o.gSlotElapsed[1] == frozen, f"{o.gSlotElapsed[1]} vs {frozen}")

    t("24. Normal running is unaffected by the gating")
    o = Oven(); o.run(2)
    o.gHmiSlotStart[1] = True; o.run(1)
    for _ in range(10):                            # normal PID cycling
        o.X6 = True;  o.run(60)
        o.X6 = False; o.run(30)
    check("cure advanced by the full wall time", abs(o.gSlotElapsed[1] - 900) <= 3,
          f"got {o.gSlotElapsed[1]}")
    check("no pause", not o.gSlotTimersPaused)


for fn in (test_blowers_and_door, test_heater, test_door_watchdogs,
           test_slot_timers, test_manual_and_counters, test_alarms,
           test_cure_gating):
    fn()

print(f"\n{'=' * 62}\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
sys.exit(1 if FAIL else 0)
