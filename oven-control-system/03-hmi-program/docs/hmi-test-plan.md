# HMI verification — GT2107-WTBD

Run after the PLC commissioning plan passes. Sign each line.

## 1. Communications and chrome

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 1.1 | Power up both | GOT connects, no comms error banner | |
| 1.2 | Pull the Ethernet lead | GOT shows a communication error within a few seconds | |
| 1.3 | Reconnect | recovers by itself, no re-login needed for the operator | |
| 1.4 | Check the clock | matches the PLC clock | |
| 1.5 | Navigate every footer tab | all six reach the right screen | |

## 2. Overview (B-1000)

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 2.1 | Start each blower from the HMI | motor runs, lamp follows | |
| 2.2 | Stop each blower from the HMI | motor stops | |
| 2.3 | Open the oven door | DOOR reads OPEN, blowers stop, door timer counts | |
| 2.4 | Heat demand from `-A2` | PID DEMAND shows CALLING FOR HEAT | |
| 2.5 | Compare the six slot tiles with B-1100 | identical values | |

## 3. Cure timers (B-1100)

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 3.1 | Start a slot | tile goes CURING, timer counts, START disappears | |
| 3.2 | Press RESET on a curing slot | **disabled — cannot be pressed** | |
| 3.3 | Let a slot complete (use the shortened cure time) | tile goes COMPLETE, RESET enabled | |
| 3.4 | Press RESET | confirm dialogue, then the slot clears | |
| 3.5 | Trip the high-limit with a slot running | PAUSED banner, timer frozen, alarm 13 | |
| 3.6 | Reset the high-limit | banner clears, the timer resumes from where it stopped | |
| 3.7 | EARLY RESET button with no login | **not visible** | |

## 4. Login and roles (B-1600)

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 4.1 | Type the maintenance code, press MAINTENANCE | header chip goes MAINTENANCE | |
| 4.2 | Check `D27` in GX Works3 straight afterwards | **zero — the code is not left in a register** | |
| 4.3 | Press QUALITY with the quality code | chip goes QUALITY, maintenance rights gone | |
| 4.4 | As QUALITY, try to reach B-1400 or B-1500 | refused | |
| 4.5 | As MAINTENANCE, try to reach B-1800 | refused | |
| 4.6 | Three wrong codes | LOCKED OUT panel, countdown runs | |
| 4.7 | Correct code during lockout | still refused | |
| 4.8 | Wait out the lockout | login works again | |
| 4.9 | Log in, leave it 5 min | auto-logout, chip returns to OPERATOR | |

## 5. Separation of duties — the one that matters

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 5.1 | As MAINTENANCE, early-reset a running slot | accepted, confirm dialogue shown | |
| 5.2 | Read B-1200 | early resets +1, **unloaded unchanged**, UNACCOUNTED +1 | |
| 5.3 | As MAINTENANCE, try to reset the lot counters | **refused — B-1800 not reachable** | |
| 5.4 | As QUALITY, reset the lot counters | accepted after the confirm dialogue | |
| 5.5 | Read the PLC SD card log | events 41–46 and 62 present with times | |

## 6. Alarms (B-1300)

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 6.1 | Force each of the 14 alarms in turn | correct text, level and detail | |
| 6.2 | ACCEPT with an alarm standing | hooter silences, lamp stays | |
| 6.3 | Clear the cause | alarm leaves the active list, stays in history | |
| 6.4 | Power the panel off and on | history survives (battery fitted) | |

## 7. Manual test (B-1400)

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 7.1 | Enter as MAINTENANCE | banner shown, countdown runs | |
| 7.2 | Hold each of the three buttons | output runs only while touched | |
| 7.3 | Watch the feedback lamps | each confirms its contactor actually moved | |
| 7.4 | Open the door | exits immediately, all outputs drop | |
| 7.5 | Enter with a cure running | refused | |
| 7.6 | Leave it 5 min | auto-exit | |

## 8. Settings (B-1500) and history (B-1900)

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 8.1 | Enter an out-of-range value in each field | rejected by the GOT | |
| 8.2 | Change a setting, power cycle | value survives (latched in the PLC) | |
| 8.3 | Change both passcodes from the defaults | new codes work, old ones do not | |
| 8.4 | Export to USB from B-1900 | CSV written, opens and is readable | |
| 8.5 | Confirm what the export contains | GOT alarm history — **not** the PLC event log | |

## 9. Handover

| # | Item | ✓ |
|---|------|---|
| 9.1 | Both passcodes changed and issued separately, in writing | |
| 9.2 | GT11-50BAT battery fitted, clock set | |
| 9.3 | Backlight timeout and screen-return set | |
| 9.4 | Project backed up, GT Designer3 project password set | |
| 9.5 | Operators shown: start/stop, slot start, reading UNACCOUNTED LOTS | |
| 9.6 | Quality shown: how to read the counters before clearing them | |
