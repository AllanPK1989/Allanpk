(* =============================================================================
   P01_SECURITY   -   level 2 login, manual test mode
   Order : SECOND program block. Runs before the drive logic so that the
           manual-mode flags are current when the outputs are resolved.

   Security model
   --------------
   The password itself lives in the GOT operator-authentication database, not
   in the PLC. When the operator reaches authentication level 2 the GOT sets
   gHmiL2Login; the PLC latches gL2LoggedIn and starts an inactivity timer.
   Nothing password-protected can happen unless gL2LoggedIn is TRUE, so a
   disconnected or swapped HMI simply removes the ability - it never grants it.

   Local labels required in this POU:  (none)
   ============================================================================= *)

(* -- 1. level 2 login ------------------------------------------------------- *)
IF gHmiL2Login THEN
    gHmiL2Login  := FALSE;
    gL2LoggedIn  := TRUE;
    gLoginTmoAcc := 0;
END_IF;

IF gHmiL2Logout THEN
    gHmiL2Logout := FALSE;
    gL2LoggedIn  := FALSE;
END_IF;

(* -- 2. inactivity auto-logout ---------------------------------------------- *)
IF gL2LoggedIn THEN
    IF gHmiActivity THEN                (* GOT pulses this on every screen touch *)
        gHmiActivity := FALSE;
        gLoginTmoAcc := 0;
    END_IF;
    IF gTick1s THEN
        gLoginTmoAcc := gLoginTmoAcc + 1;
    END_IF;
    IF gLoginTmoAcc >= gSetLoginTmoS THEN
        gL2LoggedIn  := FALSE;
        gLoginTmoAcc := 0;
    END_IF;
ELSE
    gLoginTmoAcc := 0;
END_IF;

(* -- 3. conditions under which manual test may be entered or stay active ---- *)
(*      Deliberately strict: manual test drives contactors directly and         *)
(*      bypasses the normal start logic.                                        *)
gManualPermit := gL2LoggedIn
                 AND gEStopOK
                 AND gDoorOK                    (* door closed and settled      *)
                 AND NOT gBl1OlTrip
                 AND NOT gBl2OlTrip
                 AND NOT gHtrOlTrip
                 AND gHighLimitOK
                 AND NOT gAnySlotRunning;       (* never during a cure cycle    *)

(* -- 4. entering manual test ------------------------------------------------ *)
IF gHmiManualReq THEN
    gHmiManualReq := FALSE;
    IF gManualPermit AND NOT gManualMode THEN
        gManualMode   := TRUE;
        gManualTmoAcc := 0;
        gBl1RunReq    := FALSE;         (* drop the automatic requests so that  *)
        gBl2RunReq    := FALSE;         (* nothing restarts when manual exits   *)
        gEventCode  := 71;
        gEventParam := 0;
        gEventValue := 0;
        gEventPulse := TRUE;
    END_IF;
END_IF;

(* -- 5. staying in manual test ---------------------------------------------- *)
IF gManualMode THEN
    IF gTick1s THEN
        gManualTmoAcc := gManualTmoAcc + 1;
    END_IF;

    IF (gManualTmoAcc >= gSetManualTmoS)        (* timed out                    *)
       OR NOT gManualPermit                     (* a condition was lost         *)
       OR gHmiManualExit THEN                   (* operator exited              *)
        gManualMode    := FALSE;
        gHmiManualExit := FALSE;
        gEventCode  := 72;
        gEventParam := 0;
        gEventValue := 0;
        gEventPulse := TRUE;
    END_IF;
ELSE
    gManualTmoAcc  := 0;
    gHmiManualExit := FALSE;
END_IF;

(* -- 6. manual output requests ---------------------------------------------- *)
(*      The HMI buttons are momentary: the bit is TRUE only while touched.      *)
gManBl1 := gHmiManBl1 AND gManualMode;
gManBl2 := gHmiManBl2 AND gManualMode;
gManHtr := gHmiManHtr AND gManualMode;
