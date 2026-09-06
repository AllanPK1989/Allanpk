(* =============================================================================
   P00_COMMON   -   clock ticks, input conditioning, permissives
   Project : OVN-2026-01  Oven control panel
   CPU     : MELSEC iQ-F  FX5U-32MT/ES
   Language: Structured Text
   Order   : FIRST program block in the scan program.

   Local labels required in this POU:  (none)
   ============================================================================= *)

(* -- 1. clear the event pulse raised in the previous scan ------------------- *)
(*      Any block may set gEventPulse; it is therefore ON for exactly one scan, *)
(*      which is what the CPU data-logging trigger samples.                     *)
gEventPulse := FALSE;

(* -- 2. single-scan tick pulses -------------------------------------------- *)
(*      SM409 = 0.1 s clock, SM412 = 1 s clock, SM413 = 2 s clock (1 s on/off) *)
gTick100ms    := SM409 AND NOT gTick100msMem;
gTick100msMem := SM409;

gTick1s    := SM412 AND NOT gTick1sMem;
gTick1sMem := SM412;

gHeartbeat := SM412;                    (* HMI communication watchdog *)

(* -- 3. one-time initialisation of the latched settings -------------------- *)
(*      Runs only on a virgin CPU or after the latched area has been cleared.  *)
IF NOT gDefaultsWritten THEN
    gSetHeatUpWdMin := 60;              (* heat-up watchdog, minutes           *)
    gSetDoorWdSec   := 600;             (* door-not-closed watchdog, seconds   *)
    gSetChatterCnt  := 8;               (* transitions that count as chatter   *)
    gSetChatterWinS := 10;              (* chatter observation window, seconds *)
    gSetHtrMinOnS   := 20;              (* heater minimum ON time, seconds     *)
    gSetHtrMinOffS  := 20;              (* heater minimum OFF time, seconds    *)
    gSetManualTmoS  := 300;             (* manual test auto-exit, seconds      *)
    gSetLoginTmoS   := 300;             (* level 2 auto-logout, seconds        *)
    gSetSlotTargetS := 7200;            (* slot cure time = 2 hours            *)
    gSetHtrNeedsAir := FALSE;           (* optional airflow interlock - OFF    *)
    gSetSlotGated   := FALSE;           (* optional slot-timer gating - OFF    *)
    gDefaultsWritten := TRUE;
END_IF;

(* -- 4. volatile state cleared on every transition to RUN ------------------- *)
(*      Latched production data (slot timers, counters) is NOT touched here.   *)
(*      Run requests are deliberately volatile: IEC 60204-1 forbids an         *)
(*      unexpected restart after the supply is restored.                       *)
IF SM402 THEN
    gBl1RunReq    := FALSE;
    gBl2RunReq    := FALSE;
    gHtrCmd       := FALSE;
    gManualMode   := FALSE;
    gL2LoggedIn   := FALSE;
    gHtrMinOnAcc  := 0;
    gHtrMinOffAcc := 0;                 (* forces the min-OFF delay before the *)
                                        (* first heater ON after power-up      *)
    gHeatUpAcc    := 0;
    gDoorOpenAcc  := 0;
    gChatterCount := 0;
    gChatterWinAcc := 0;
    gEventCode  := 1;                   (* event 1 = PLC entered RUN *)
    gEventParam := 0;
    gEventValue := 0;
    gEventPulse := TRUE;
END_IF;

(* -- 5. input conditioning -------------------------------------------------- *)
(*      Fail-safe NC inputs. TRUE = healthy / not pressed.                      *)
(*      A broken wire makes these FALSE, which is the safe state.               *)
gEStopOK     := X0;                     (* -S0  21-22   emergency stop released *)
gBl1StopOK   := X2;                     (* -S2  11-12   stop PB not pressed     *)
gBl2StopOK   := X4;                     (* -S4  11-12   stop PB not pressed     *)
gPidOK       := X7;                     (* -A2  AL1     controller healthy      *)
gHighLimitOK := X13;                    (* -B3  C2      high limit healthy      *)

(*      Active-high inputs. TRUE = the stated condition is present.             *)
gDoorClosed  := X5;                     (* -B1  13-14   door closed             *)
gHeatDemand  := X6;                     (* -A2  OUT1    calling for heat        *)
gBl1OlTrip   := X10;                    (* -F1  97-98   overload TRIPPED        *)
gBl2OlTrip   := X11;                    (* -F2  97-98   overload TRIPPED        *)
gHtrOlTrip   := X12;                    (* -F3  97-98   overload TRIPPED        *)
gK1Closed    := X14;                    (* -K1  13-14   contactor closed        *)
gK2Closed    := X15;                    (* -K2  13-14   contactor closed        *)
gK3Closed    := X16;                    (* -K3  13-14   contactor closed        *)
gLampTest    := X17;                    (* -S5  held    lamp test               *)

(* -- 6. alarm-accept pulse -------------------------------------------------- *)
(*      Rising edge of -S5, or the HMI accept button. Generated here so that    *)
(*      every later block sees the same pulse in the same scan.                 *)
gAcceptEdge := X17 AND NOT gAcceptMem;
gAcceptMem  := X17;
gAlarmAcceptPulse := gAcceptEdge OR gHmiAlarmAccept;
gHmiAlarmAccept   := FALSE;             (* handshake: PLC clears the HMI bit *)

(* -- 7. permissives --------------------------------------------------------- *)
gBl1Permit := gEStopOK AND NOT gBl1OlTrip;
gBl2Permit := gEStopOK AND NOT gBl2OlTrip;

gHtrPermit := gEStopOK
              AND NOT gHtrOlTrip
              AND gHighLimitOK
              AND gPidOK;

(*      OPTIONAL airflow interlock - see docs/functional-description.md.        *)
(*      Default OFF, because the specified door behaviour deliberately runs     *)
(*      the heater with both blowers stopped while the door is open.            *)
IF gSetHtrNeedsAir THEN
    gHtrPermit := gHtrPermit AND (gK1Closed OR gK2Closed OR NOT gDoorClosed);
END_IF;

(*      Permissive for the slot timers to advance, used only when the optional  *)
(*      gating is enabled.                                                       *)
gSlotRunPermit := gEStopOK AND gHighLimitOK AND NOT gHtrOlTrip;
