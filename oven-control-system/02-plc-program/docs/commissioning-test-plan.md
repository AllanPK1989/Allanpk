# Commissioning test plan

Sign each line. Anything that fails, stop and record it — do not "adjust and
carry on". Every test below is also automated in `test/test_logic.py`, which
passes 97/97 against the behavioural model.

**Before starting:** heater feeder `-Q4` OFF and locked. Do sections 1–4 with
the heater isolated.

## 1. Power-up and I/O proving

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 1.1 | Power up, PLC to RUN | no alarms, no lamps except as commanded | |
| 1.2 | Hold `-S5` | all six lamps light, hooter silent | |
| 1.3 | Force each input in turn, watch the HMI | each reads as sheet 06 | |
| 1.4 | Open the oven door | X5 goes OFF | |
| 1.5 | Disconnect `-X1:01` with the door closed | X5 goes OFF (fail-safe proved) | |
| 1.6 | Operate `-S0` | X0 goes OFF, coil bus 102 dead at `-X1` | |

## 2. Blowers and the door interlock

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 2.1 | `-S1` START | blower 1 runs, `-H1` on, X14 follows | |
| 2.2 | `-S3` START | blower 2 runs, `-H2` on, X15 follows | |
| 2.3 | Open the door | **both blowers stop immediately**, `-H4` steady | |
| 2.4 | Close the door | **both restart by themselves** within ~1 s | |
| 2.5 | Open door, press `-S2`, close door | blower 1 stays off, blower 2 restarts | |
| 2.6 | Trip `-F1` by hand | blower 1 drops, alarm, hooter | |
| 2.7 | Reset `-F1` | blower 1 does **not** restart on its own | |
| 2.8 | Run both, press `-S0` | both drop, contactors seen to open | |
| 2.9 | Release `-S0` | nothing restarts | |

## 3. Door-signal watchdogs

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 3.1 | Leave the door open 10 min | `NO DOOR CLOSED SIGNAL` alarm, `-KA4` picks up, `-X1:50/51` closes, `-H4` flashes | |
| 3.2 | Close the door | alarm and `-KA4` release | |
| 3.3 | Flick the door switch by hand ~10 times in 10 s | `DOOR SIGNAL PULSATING` alarm, `-KA4` picks up, blowers held off | |
| 3.4 | Settle the door closed, press `-S5` | alarm clears, blowers return | |
| 3.5 | Check the door counters after 3.3 | **unchanged by the chatter** | |
| 3.6 | Open and close the door 5 times slowly | opens = 5, closes = 5, no chatter alarm | |

## 4. Counters and slot timers

Temporarily set `gSetSlotTargetS` (D4108) to **120 s** for tests 4.1–4.5, then
**put it back to 7200** and record that you did.

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 4.1 | Start slot 1 from the HMI | timer runs, `-H6` on, lots loaded +1 | |
| 4.2 | Press slot 1 START again | ignored, loaded still 1 | |
| 4.3 | Press slot 1 RESET at 60 s, not logged in | **refused** | |
| 4.4 | Wait for completion, press RESET | accepted, lots unloaded +1, unaccounted = 0 | |
| 4.5 | Start slot 2, log in as maintenance, RESET at 60 s | accepted, early reset +1, **unloaded unchanged**, unaccounted = 1, mismatch shown | |
| 4.6 | Read the SD log | event 42 present with the minutes elapsed | |
| 4.7 | Start slots 1–6 together | six independent timers, all tracking | |
| 4.8 | **Restore D4108 = 7200** | verified on the HMI | |
| 4.9 | Start a slot, run 10 min, switch the panel off for 2 min, restore | timer **resumes from ~10 min**, does not restart; blowers do **not** restart | |

## 5. Heater — heater feeder now live

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 5.1 | Set `-A2` set point above ambient | X6 closes, `-K3` picks up after ≤ 20 s | |
| 5.2 | Time `-K3` cycling at set point | never faster than one operation per 20 s | |
| 5.3 | Open the oven door while heating | **heater stays on**, blowers stop | |
| 5.4 | Trip `-B3` (lower its setting below PV) | `-K3` drops **in hardware**; pull the PLC to STOP first and repeat to prove it is not the program | |
| 5.5 | Reset `-B3` | manual reset required at the panel | |
| 5.6 | Disconnect the thermocouple | `-A2` sensor-break alarm, X7 opens, heater inhibited | |
| 5.7 | Set `gSetHeatUpWdMin` = 2 min, demand heat with the elements isolated | `FAILURE TO REACH SETPOINT` after 2 min, **heater not tripped** | |
| 5.8 | **Restore `gSetHeatUpWdMin` = 60** | verified on the HMI | |

## 6. Manual test and security

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 6.1 | Manual test screen without login | refused | |
| 6.2 | Log in level 2, enter manual test | entered | |
| 6.3 | Manual blower and heater buttons | each runs while touched | |
| 6.4 | Open the door in manual test | exits immediately, outputs drop | |
| 6.5 | Enter manual test with a slot timer running | refused | |
| 6.6 | Leave the HMI idle 5 min | auto-logout | |
| 6.7 | Leave manual test idle 5 min | auto-exit | |

## 7. Contactor feedback

| # | Test | Expected | ✓ |
|---|------|----------|---|
| 7.1 | Isolate, jumper `-K1` 13-14 closed, run and stop blower 1 | `-K1 FEEDBACK` alarm within 1 s | |
| 7.2 | Remove the jumper | alarm clears | |
| 7.3 | Repeat for `-K2` and `-K3` | same | |

## 8. Handover

| # | Item | ✓ |
|---|------|---|
| 8.1 | D4108 = 7200 and `gSetHeatUpWdMin` = 60 confirmed | |
| 8.2 | All counters zeroed, maintenance login logged out | |
| 8.3 | SD card fitted, logging proved, one day's file read back | |
| 8.4 | Maintenance password handed over in writing, not verbally | |
| 8.5 | 'HOT SURFACES — HEATER LIVE' label fitted at the oven door | |
| 8.6 | `-B3` high-limit function test recorded and diarised for every PM | |
