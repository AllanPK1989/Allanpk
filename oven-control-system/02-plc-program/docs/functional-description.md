# Functional description — OVN-2026-01 PLC program

Reference: schematic OVN-2026-01 Rev 2, sheets 06, 07 and 08 for the I/O.

---

## 1. Blowers and the door interlock

Each blower holds a **run request** (`gBl1RunReq` / `gBl2RunReq`). The request
is set by the panel START push-button or the HMI, and the output is that
request gated by the permissives and the door.

The distinction that makes the specified behaviour work:

| Event | Run request | Output | Restart behaviour |
|-------|-------------|--------|-------------------|
| Door opens | **kept** | drops instantly | restarts by itself when the door closes |
| STOP pressed | cleared | drops | operator must press START |
| Overload trips | cleared | drops | operator must press START after resetting |
| E-stop | cleared | drops (also in hardware) | operator must press START |
| Supply lost | cleared (not latched) | drops | operator must press START |

The heater is deliberately absent from that table — the door does not touch it.

### Three views of one door input

X5 is used three different ways, and the difference matters:

| Signal | Filtering | Used for |
|--------|-----------|----------|
| `gDoorClosed` | raw | chatter detection, instant blower drop |
| `gDoorOK` | drops instantly, needs 1 s stable to return, and clears only when no chatter alarm stands | the blower run permissive |
| `gDoorDeb` | 1 s debounce **both** ways | the door open/close counters |

Without this split, a bouncing door switch would hammer the blower contactors
and inflate the production counters by hundreds of counts. The tests cover
both cases.

---

## 2. Heater

`-A2` keeps the temperature loop. The PLC repeats its demand contact (X6) to
`-K3` through `Y2`, adds the permissives, and limits the switching rate.

**Permissive** = E-stop released **AND** heater overload healthy **AND**
high-limit healthy **AND** PID healthy. Losing any of them drops `Y2` in the
same scan — and the hardware drops `-K3` anyway through the overload and
high-limit contacts in the coil circuit on sheet 08.

**Anti-chatter.** `-K3` is an AC-1 contactor switching 18 kW. A 20 s PID cycle
would give ~180 operations an hour. The program imposes a minimum ON and a
minimum OFF of 20 s each, capping it at 90/hour. The minimum-ON hold never
overrides a permissive.

**Heat-up watchdog.** X6 closes when the controller calls for heat and opens
when the oven reaches set point. A timer counts while X6 is closed and **resets
to zero every time X6 opens**. If it ever reaches the setting (default 60 min)
the oven has never reached set point: failed element, stuck-open contactor,
sensor reading low, door left open, lost insulation.

It raises `FAILURE TO REACH SETPOINT` and sounds the hooter. It does **not**
trip the heater — the fault is too cold, not too hot, and `-B3` handles too hot.

---

## 3. Door-signal watchdogs

Two independent detectors, one shared output `Y12 → -KA4 → -X1:50/51`.

| Alarm | Condition | Default |
|-------|-----------|---------|
| Door signal pulsating | ≥ N transitions of X5 inside a window anchored on the first transition | 8 in 10 s |
| No 'door closed' signal | X5 continuously off | 10 min |

The chatter alarm **latches** — it clears only when the alarm is accepted *and*
the door has been stably closed. Otherwise it would flicker with the fault and
the blowers would chatter with it. While it stands, `gDoorOK` is held false, so
the blowers stay off.

The second detector catches a door genuinely left open **and** a broken door
switch wire, because a broken wire reads as 'not closed'. That is why X5 uses
the NO contact held closed by the closed door — see the schematic walkthrough.

`-H4 DOOR OPEN` is **steady** for a door that is simply open and **flashing**
for either watchdog alarm, so the panel distinguishes the two without the HMI.

---

## 4. Slot timers

Six independent retentive timers, one per oven slot.

1. Started from that slot's HMI button. Runs to **02:00:00**.
2. A running slot cannot be re-started and cannot be reset.
3. At 02:00:00 the slot is COMPLETE and the reset button works. A normal reset
   counts **one lot unloaded**.
4. Before 02:00:00 the reset works **only** for a logged-in maintenance
   technician. That is an EARLY RESET: it clears the slot, counts as an early
   reset, is written to the event log with the minutes it was cut short, and is
   **not** counted as an unload.
5. `gSlotElapsed` is in the latched device area. A power failure **pauses** the
   cure; it resumes from the accumulated value and never restarts.

### The malpractice figure

```
gLotsUnaccounted = gCntLotsLoaded − gCntLotsUnloaded − (slots running now)
```

Zero in an honest shift. It is computed from the counters and the live slot
states rather than read back from the early-reset counter, so it also exposes
tampering with either counter. Non-zero raises the mismatch indication and
every unit of it has a matching 41–46 event in the SD log.

**Worth knowing:** point 5 means an oven switched off for three hours mid-cure
resumes and completes, even though the product was not at temperature for that
time. That is what "resume from accumulated time" was specified to mean. If you
would rather the timer only advanced while the oven is healthy, set
`gSetSlotGated` (M4021) — the option is built and tested, just disabled.

---

## 5. Manual test

Password protected (level 2) and guarded. Entry requires: logged in, E-stop
released, **door closed**, no overload tripped, high-limit healthy, and **no
slot timer running** — you should not be cycling the heater by hand mid-cure.

Entering manual test clears both automatic run requests, so nothing restarts
unexpectedly on exit. It exits on the HMI button, on any guard condition being
lost, or automatically after 5 minutes.

---

## 6. Alarms

Thirteen alarms in `M700–M712`, readable by the GOT as one bit-device block.

Hooter sounds on any **new** alarm — including a new one arriving while an
earlier alarm still stands. `-S5` or the HMI accept button silences the hooter;
`-H5` keeps showing (steady once accepted, flashing while unacknowledged) until
the cause actually clears.

**Contactor feedback.** Each of `-K1/-K2/-K3` is compared against its own
command with a 1 s filter. This catches a **welded** contactor (commanded off,
feedback still on — the load is live when you think it is dead) and one that
**failed to pull in**.

---

## 7. Two options built but switched off

Both default OFF so the delivered behaviour is exactly as specified. Both are
tested. Turn either on by setting its latched bit.

| Bit | Option | Why you might want it |
|-----|--------|-----------------------|
| M4020 `gSetHtrNeedsAir` | Heater requires a blower running, or the door open | Running 18 kW of elements with no airflow and the door shut risks element burnout and local overheating. Left off because the specified door behaviour deliberately runs the heater with both blowers stopped. |
| M4021 `gSetSlotGated` | Slot timers only advance while the oven is healthy | Stops a cure timer completing across a long outage when the product was not at temperature. |

Raise either with the panel builder before FAT if you want it enabled — it is a
one-bit change, not a program change.
