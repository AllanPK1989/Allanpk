(* =============================================================================
   P01_SECURITY   -   two independent roles, passcode entry, manual test mode
   Order : SECOND program block. Runs before the drive logic so that the
           manual-mode flags are current when the outputs are resolved.

   Two SEPARATE roles, not two levels of one hierarchy
   ---------------------------------------------------
     MAINTENANCE  gMaintLoggedIn    early slot-timer reset
                                    manual test of blowers and heater
                                    changing the settings
     QUALITY      gQualityLoggedIn  resetting the door counters
                                    resetting the lot counters

   They are mutually exclusive: logging in as one logs the other out. Neither
   inherits the other's rights.

   Separation of duties - read this before changing it
   ---------------------------------------------------
   MAINTENANCE performs early slot resets. QUALITY, and only QUALITY, can
   clear the counters that record them. If maintenance could zero the lot
   counters they could erase the evidence of their own early resets, and the
   whole traceability requirement would be decorative.

   Where the passcodes live
   ------------------------
   In the PLC (latched D4110 / D4111), not in the GOT. Two roles that do not
   inherit from each other cannot be expressed by GOT security levels, which
   are hierarchical. Holding the check here also means the rules survive an
   HMI swap. Protect the GX Works3 project with a password as well - see
   docs/cpu-parameters.md.

   Local labels required in this POU:  (none)
   ============================================================================= *)

(* -- 1. lockout after repeated failed attempts ----------------------------- *)
IF gLockoutAcc > 0 THEN
    IF gTick1s THEN
        gLockoutAcc := gLockoutAcc - 1;
    END_IF;
END_IF;
gLockoutActive := gLockoutAcc > 0;

(* -- 2. login attempt ------------------------------------------------------- *)
(*      The HMI writes the passcode to gHmiPasscodeEntry and sets the request  *)
(*      bit in the SAME touch action, so the typed code exists for one scan.   *)
IF gHmiMaintLoginReq OR gHmiQualityLoginReq THEN

    IF gLockoutActive THEN
        (* locked out - the attempt is discarded and logged *)
        gEventCode  := 76;
        gEventParam := 0;
        gEventValue := gLockoutAcc;
        gEventPulse := TRUE;

    ELSIF gHmiMaintLoginReq AND (gHmiPasscodeEntry = gSetMaintCode) THEN
        gMaintLoggedIn   := TRUE;
        gQualityLoggedIn := FALSE;
        gMaintTmoAcc     := 0;
        gFailedAttempts  := 0;
        gEventCode  := 73;
        gEventParam := 0;
        gEventValue := 0;
        gEventPulse := TRUE;

    ELSIF gHmiQualityLoginReq AND (gHmiPasscodeEntry = gSetQualityCode) THEN
        gQualityLoggedIn := TRUE;
        gMaintLoggedIn   := FALSE;
        gQualityTmoAcc   := 0;
        gFailedAttempts  := 0;
        gEventCode  := 74;
        gEventParam := 0;
        gEventValue := 0;
        gEventPulse := TRUE;

    ELSE
        (* wrong code *)
        gFailedAttempts := gFailedAttempts + 1;
        gEventCode  := 75;
        gEventParam := 0;
        gEventValue := gFailedAttempts;
        gEventPulse := TRUE;
        IF gFailedAttempts >= gSetMaxAttempts THEN
            gLockoutAcc     := gSetLockoutS;
            gFailedAttempts := 0;
        END_IF;
    END_IF;

    gHmiMaintLoginReq   := FALSE;
    gHmiQualityLoginReq := FALSE;
    gHmiPasscodeEntry   := 0;       (* never leave a typed code in a register *)
END_IF;

(* -- 3. logout -------------------------------------------------------------- *)
IF gHmiLogout THEN
    gHmiLogout        := FALSE;
    gMaintLoggedIn    := FALSE;
    gQualityLoggedIn  := FALSE;
    gHmiPasscodeEntry := 0;
    gEventCode  := 77;
    gEventParam := 0;
    gEventValue := 0;
    gEventPulse := TRUE;
END_IF;

(* -- 4. inactivity auto-logout, one timer per role -------------------------- *)
IF gMaintLoggedIn THEN
    IF gHmiActivity THEN
        gMaintTmoAcc := 0;
    END_IF;
    IF gTick1s THEN
        gMaintTmoAcc := gMaintTmoAcc + 1;
    END_IF;
    IF gMaintTmoAcc >= gSetLoginTmoS THEN
        gMaintLoggedIn    := FALSE;
        gMaintTmoAcc      := 0;
        gHmiPasscodeEntry := 0;
    END_IF;
ELSE
    gMaintTmoAcc := 0;
END_IF;

IF gQualityLoggedIn THEN
    IF gHmiActivity THEN
        gQualityTmoAcc := 0;
    END_IF;
    IF gTick1s THEN
        gQualityTmoAcc := gQualityTmoAcc + 1;
    END_IF;
    IF gQualityTmoAcc >= gSetLoginTmoS THEN
        gQualityLoggedIn  := FALSE;
        gQualityTmoAcc    := 0;
        gHmiPasscodeEntry := 0;
    END_IF;
ELSE
    gQualityTmoAcc := 0;
END_IF;

gHmiActivity := FALSE;

(*      Role indication for the HMI header: 0 = none, 1 = maintenance,        *)
(*      2 = quality.                                                           *)
IF gMaintLoggedIn THEN
    gActiveRole := 1;
ELSIF gQualityLoggedIn THEN
    gActiveRole := 2;
ELSE
    gActiveRole := 0;
END_IF;

(* -- 5. conditions under which manual test may be entered or stay active ---- *)
(*      Maintenance only. Deliberately strict: manual test drives contactors    *)
(*      directly and bypasses the normal start logic.                           *)
gManualPermit := gMaintLoggedIn
                 AND gEStopOK
                 AND gDoorOK                    (* door closed and settled      *)
                 AND NOT gBl1OlTrip
                 AND NOT gBl2OlTrip
                 AND NOT gHtrOlTrip
                 AND gHighLimitOK
                 AND NOT gAnySlotRunning;       (* never during a cure cycle    *)

(* -- 6. entering manual test ------------------------------------------------ *)
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

(* -- 7. staying in manual test ---------------------------------------------- *)
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

(* -- 8. manual output requests ---------------------------------------------- *)
(*      The HMI buttons are momentary: the bit is TRUE only while touched.      *)
gManBl1 := gHmiManBl1 AND gManualMode;
gManBl2 := gHmiManBl2 AND gManualMode;
gManHtr := gHmiManHtr AND gManualMode;
