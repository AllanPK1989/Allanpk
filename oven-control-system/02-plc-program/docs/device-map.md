# Device map — FX5U-32MT/ES

Generated from `labels/make_labels.py`, which is also the checker: it fails
if a label used in the ST is undeclared, if two labels collide on a device,
or if latched data strays outside the latch ranges.

Run `python3 labels/make_labels.py` after any change.

## Latch ranges (set these in CPU Parameter — see cpu-parameters.md)

| Device | Latch (1) | Contents |
|---|---|---|
| M | M4000–M4095 | slot state, config options |
| D | D4000–D4499 | slot elapsed, counters, settings |

## Summary

| Area | Range | Count |
|---|---|---|
| Working bits | M0–M59 | 60 |
| Alarm bits (GOT block) | M700–M715 | 16 |
| Alarm memory | M720–M735 | 16 |
| HMI command bits | M800–M834 | 35 |
| Latched bits | M4000–M4022 | 23 |
| Working words | D0–D69 | 70 |
| Latched words | D4000–D4109 | 110 |
| **Total labels** | | **143** |

## Latched data — survives a power failure

| Label | Device | Type | Purpose |
|---|---|---|---|
| `gSlotRunning` | M4000 | Bit(1..6) | LATCH slot 1-6 occupied / timing |
| `gSlotComplete` | M4008 | Bit(1..6) | LATCH slot 1-6 reached 2 hours |
| `gSetHtrNeedsAir` | M4020 | Bit | LATCH option: heater needs a blower running |
| `gSetSlotGated` | M4021 | Bit | LATCH option: slot timers pause on a fault |
| `gDefaultsWritten` | M4022 | Bit | LATCH settings have been initialised |
| `gSlotElapsed` | D4000 | Double Word [Signed](1..6) | LATCH slot 1-6 elapsed seconds |
| `gCntDoorOpen` | D4020 | Double Word [Signed] | LATCH door opened count |
| `gCntDoorClose` | D4022 | Double Word [Signed] | LATCH door closed count |
| `gCntLotsLoaded` | D4024 | Double Word [Signed] | LATCH lots loaded (slot starts) |
| `gCntLotsUnloaded` | D4026 | Double Word [Signed] | LATCH lots unloaded (normal resets) |
| `gCntEarlyReset` | D4028 | Double Word [Signed] | LATCH early resets by maintenance |
| `gTotHtrRunS` | D4030 | Double Word [Signed] | LATCH heater running seconds |
| `gTotBl1RunS` | D4032 | Double Word [Signed] | LATCH blower 1 running seconds |
| `gTotBl2RunS` | D4034 | Double Word [Signed] | LATCH blower 2 running seconds |
| `gSetHeatUpWdMin` | D4100 | Word [Signed] | SET heat-up watchdog, min (10-240) |
| `gSetDoorWdSec` | D4101 | Word [Signed] | SET door watchdog, s (60-1800) |
| `gSetChatterCnt` | D4102 | Word [Signed] | SET chatter transition count (4-50) |
| `gSetChatterWinS` | D4103 | Word [Signed] | SET chatter window, s (5-60) |
| `gSetHtrMinOnS` | D4104 | Word [Signed] | SET heater minimum ON, s (5-120) |
| `gSetHtrMinOffS` | D4105 | Word [Signed] | SET heater minimum OFF, s (5-120) |
| `gSetManualTmoS` | D4106 | Word [Signed] | SET manual test auto-exit, s |
| `gSetLoginTmoS` | D4107 | Word [Signed] | SET level 2 auto-logout, s |
| `gSetSlotTargetS` | D4108 | Double Word [Signed] | SET slot cure time, s (default 7200) |

## Full label list

| Label | Device | Type | Comment |
|---|---|---|---|
| `gTick100ms` | M0 | Bit | 1 scan pulse every 100 ms |
| `gTick100msMem` | M1 | Bit | edge memory for SM409 |
| `gTick1s` | M2 | Bit | 1 scan pulse every 1 s |
| `gTick1sMem` | M3 | Bit | edge memory for SM412 |
| `gHeartbeat` | M4 | Bit | 1 s heartbeat for the HMI watchdog |
| `gEStopOK` | M5 | Bit | X0  -S0 emergency stop released |
| `gBl1StopOK` | M6 | Bit | X2  -S2 stop PB not pressed |
| `gBl2StopOK` | M7 | Bit | X4  -S4 stop PB not pressed |
| `gPidOK` | M8 | Bit | X7  -A2 AL1 controller healthy |
| `gHighLimitOK` | M9 | Bit | X13 -B3 high-limit thermostat healthy |
| `gDoorClosed` | M10 | Bit | X5  -B1 door closed, raw |
| `gHeatDemand` | M11 | Bit | X6  -A2 OUT1 calling for heat |
| `gBl1OlTrip` | M12 | Bit | X10 -F1 overload tripped |
| `gBl2OlTrip` | M13 | Bit | X11 -F2 overload tripped |
| `gHtrOlTrip` | M14 | Bit | X12 -F3 overload tripped |
| `gK1Closed` | M15 | Bit | X14 -K1 contactor closed |
| `gK2Closed` | M16 | Bit | X15 -K2 contactor closed |
| `gK3Closed` | M17 | Bit | X16 -K3 contactor closed |
| `gLampTest` | M18 | Bit | X17 -S5 held = lamp test |
| `gAcceptMem` | M19 | Bit | edge memory for -S5 |
| `gAcceptEdge` | M20 | Bit | rising edge of -S5 |
| `gAlarmAcceptPulse` | M21 | Bit | alarm accept, panel or HMI |
| `gBl1Permit` | M22 | Bit | blower 1 permissive |
| `gBl2Permit` | M23 | Bit | blower 2 permissive |
| `gHtrPermit` | M24 | Bit | heater permissive |
| `gSlotRunPermit` | M25 | Bit | slot timers may advance (optional gating) |
| `gBl1StartMem` | M26 | Bit | edge memory for -S1 |
| `gBl2StartMem` | M27 | Bit | edge memory for -S3 |
| `gBl1StartEdge` | M28 | Bit | rising edge of -S1 |
| `gBl2StartEdge` | M29 | Bit | rising edge of -S3 |
| `gBl1RunReq` | M30 | Bit | blower 1 run request, held over a door open |
| `gBl2RunReq` | M31 | Bit | blower 2 run request, held over a door open |
| `gBl1Out` | M32 | Bit | blower 1 output state |
| `gBl2Out` | M33 | Bit | blower 2 output state |
| `gHtrCmd` | M34 | Bit | heater command after anti-chatter |
| `gHtrOut` | M35 | Bit | heater output state |
| `gDoorMem` | M36 | Bit | edge memory, raw door |
| `gDoorCloseEdge` | M37 | Bit | raw door closing edge |
| `gDoorOpenEdge` | M38 | Bit | raw door opening edge |
| `gDoorClosedStable` | M39 | Bit | door closed continuously for 1 s |
| `gDoorOK` | M40 | Bit | blower interlock permissive |
| `gDoorDeb` | M41 | Bit | door state, 1 s debounce both ways |
| `gDoorDebMem` | M42 | Bit | edge memory, debounced door |
| `gDoorDebCloseEdge` | M43 | Bit | debounced door closing edge |
| `gDoorDebOpenEdge` | M44 | Bit | debounced door opening edge |
| `gDoorAlarm` | M45 | Bit | any door-signal watchdog alarm |
| `gAlmDoorNotClosedMem` | M46 | Bit | edge memory for event logging |
| `gAlmHeatUpMem` | M47 | Bit | edge memory for event logging |
| `gAnySlotRunning` | M48 | Bit | one or more slot timers running |
| `gAnyAlarm` | M49 | Bit | any alarm present |
| `gAlarmNew` | M50 | Bit | a new alarm appeared this scan |
| `gAlarmUnack` | M51 | Bit | alarm not yet accepted |
| `gHooter` | M52 | Bit | hooter demand |
| `gManualMode` | M53 | Bit | manual test mode active |
| `gManualPermit` | M54 | Bit | manual test conditions satisfied |
| `gManBl1` | M55 | Bit | manual blower 1 demand |
| `gManBl2` | M56 | Bit | manual blower 2 demand |
| `gManHtr` | M57 | Bit | manual heater demand |
| `gL2LoggedIn` | M58 | Bit | maintenance level 2 logged in |
| `gEventPulse` | M59 | Bit | 1 scan event trigger for SD logging |
| `gAlmBits` | M700 | Bit(0..15) | alarm block, overlays the named alarms |
| `gAlmEStop` | M700 | Bit | ALM 0  emergency stop operated |
| `gAlmBl1Ol` | M701 | Bit | ALM 1  blower 1 overload tripped |
| `gAlmBl2Ol` | M702 | Bit | ALM 2  blower 2 overload tripped |
| `gAlmHtrOl` | M703 | Bit | ALM 3  heater overload tripped |
| `gAlmHighLimit` | M704 | Bit | ALM 4  high-limit thermostat tripped |
| `gAlmPidFault` | M705 | Bit | ALM 5  PID alarm or sensor break |
| `gAlmHeatUp` | M706 | Bit | ALM 6  failure to reach setpoint |
| `gAlmDoorChatter` | M707 | Bit | ALM 7  door signal pulsating |
| `gAlmDoorNotClosed` | M708 | Bit | ALM 8  no door closed signal |
| `gAlmK1Fault` | M709 | Bit | ALM 9  -K1 feedback disagrees |
| `gAlmK2Fault` | M710 | Bit | ALM 10 -K2 feedback disagrees |
| `gAlmK3Fault` | M711 | Bit | ALM 11 -K3 feedback disagrees |
| `gAlmLotMismatch` | M712 | Bit | ALM 12 lots loaded / unloaded mismatch |
| `gAlmMem` | M720 | Bit(0..15) | previous scan alarm block |
| `gHmiSlotStart` | M800 | Bit(1..6) | HMI start, slot 1-6 |
| `gHmiSlotReset` | M810 | Bit(1..6) | HMI reset, slot 1-6 |
| `gHmiBl1Start` | M820 | Bit | HMI blower 1 start |
| `gHmiBl1Stop` | M821 | Bit | HMI blower 1 stop |
| `gHmiBl2Start` | M822 | Bit | HMI blower 2 start |
| `gHmiBl2Stop` | M823 | Bit | HMI blower 2 stop |
| `gHmiAlarmAccept` | M824 | Bit | HMI alarm accept |
| `gHmiResetDoorCnt` | M825 | Bit | HMI reset door counters |
| `gHmiResetLotCnt` | M826 | Bit | HMI reset lot counters |
| `gHmiManualReq` | M827 | Bit | HMI enter manual test |
| `gHmiManualExit` | M828 | Bit | HMI exit manual test |
| `gHmiL2Login` | M829 | Bit | GOT reports auth level 2 reached |
| `gHmiL2Logout` | M830 | Bit | GOT reports logout |
| `gHmiActivity` | M831 | Bit | GOT screen touch, resets the logout timer |
| `gHmiManBl1` | M832 | Bit | HMI manual blower 1, momentary |
| `gHmiManBl2` | M833 | Bit | HMI manual blower 2, momentary |
| `gHmiManHtr` | M834 | Bit | HMI manual heater, momentary |
| `gSlotRunning` | M4000 | Bit(1..6) | LATCH slot 1-6 occupied / timing |
| `gSlotComplete` | M4008 | Bit(1..6) | LATCH slot 1-6 reached 2 hours |
| `gSetHtrNeedsAir` | M4020 | Bit | LATCH option: heater needs a blower running |
| `gSetSlotGated` | M4021 | Bit | LATCH option: slot timers pause on a fault |
| `gDefaultsWritten` | M4022 | Bit | LATCH settings have been initialised |
| `gHtrMinOnAcc` | D0 | Word [Signed] | heater minimum ON elapsed, s |
| `gHtrMinOffAcc` | D1 | Word [Signed] | heater minimum OFF elapsed, s |
| `gDoorStableAcc` | D2 | Word [Signed] | door stable-closed filter, 100 ms units |
| `gDoorDebAcc` | D3 | Word [Signed] | door debounce filter, 100 ms units |
| `gChatterCount` | D4 | Word [Signed] | door transitions in the current window |
| `gChatterWinAcc` | D5 | Word [Signed] | chatter window elapsed, s |
| `gK1FbAcc` | D6 | Word [Signed] | -K1 feedback disagreement, 100 ms units |
| `gK2FbAcc` | D7 | Word [Signed] | -K2 feedback disagreement, 100 ms units |
| `gK3FbAcc` | D8 | Word [Signed] | -K3 feedback disagreement, 100 ms units |
| `gManualTmoAcc` | D9 | Word [Signed] | manual test elapsed, s |
| `gLoginTmoAcc` | D10 | Word [Signed] | level 2 login idle time, s |
| `gSlotsActive` | D11 | Word [Signed] | number of slots currently running |
| `gEventCode` | D12 | Word [Signed] | event code for the SD log |
| `gEventParam` | D13 | Word [Signed] | event parameter, usually the slot number |
| `gEventValue` | D14 | Word [Signed] | event value, e.g. minutes cut short |
| `gHeatUpAcc` | D15 | Word [Signed] | heat demand held, s |
| `gHeatUpMin` | D16 | Word [Signed] | heat demand held, min, for the HMI |
| `gDoorOpenAcc` | D17 | Word [Signed] | no door closed signal, s |
| `gDoorOpenMin` | D18 | Word [Signed] | no door closed signal, min, for the HMI |
| `gTotHtrRunH` | D19 | Word [Signed] | heater running hours, for the HMI |
| `gTotBl1RunH` | D20 | Word [Signed] | blower 1 running hours, for the HMI |
| `gTotBl2RunH` | D21 | Word [Signed] | blower 2 running hours, for the HMI |
| `gLotsUnaccounted` | D24 | Double Word [Signed] | loaded - unloaded - running = the discrepancy |
| `gSlotH` | D40 | Word [Signed](1..6) | slot 1-6 elapsed hours |
| `gSlotM` | D46 | Word [Signed](1..6) | slot 1-6 elapsed minutes |
| `gSlotS` | D52 | Word [Signed](1..6) | slot 1-6 elapsed seconds |
| `gSlotRemainMin` | D58 | Word [Signed](1..6) | slot 1-6 remaining minutes |
| `gSlotPct` | D64 | Word [Signed](1..6) | slot 1-6 progress percent |
| `gSlotElapsed` | D4000 | Double Word [Signed](1..6) | LATCH slot 1-6 elapsed seconds |
| `gCntDoorOpen` | D4020 | Double Word [Signed] | LATCH door opened count |
| `gCntDoorClose` | D4022 | Double Word [Signed] | LATCH door closed count |
| `gCntLotsLoaded` | D4024 | Double Word [Signed] | LATCH lots loaded (slot starts) |
| `gCntLotsUnloaded` | D4026 | Double Word [Signed] | LATCH lots unloaded (normal resets) |
| `gCntEarlyReset` | D4028 | Double Word [Signed] | LATCH early resets by maintenance |
| `gTotHtrRunS` | D4030 | Double Word [Signed] | LATCH heater running seconds |
| `gTotBl1RunS` | D4032 | Double Word [Signed] | LATCH blower 1 running seconds |
| `gTotBl2RunS` | D4034 | Double Word [Signed] | LATCH blower 2 running seconds |
| `gSetHeatUpWdMin` | D4100 | Word [Signed] | SET heat-up watchdog, min (10-240) |
| `gSetDoorWdSec` | D4101 | Word [Signed] | SET door watchdog, s (60-1800) |
| `gSetChatterCnt` | D4102 | Word [Signed] | SET chatter transition count (4-50) |
| `gSetChatterWinS` | D4103 | Word [Signed] | SET chatter window, s (5-60) |
| `gSetHtrMinOnS` | D4104 | Word [Signed] | SET heater minimum ON, s (5-120) |
| `gSetHtrMinOffS` | D4105 | Word [Signed] | SET heater minimum OFF, s (5-120) |
| `gSetManualTmoS` | D4106 | Word [Signed] | SET manual test auto-exit, s |
| `gSetLoginTmoS` | D4107 | Word [Signed] | SET level 2 auto-logout, s |
| `gSetSlotTargetS` | D4108 | Double Word [Signed] | SET slot cure time, s (default 7200) |
