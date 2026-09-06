(* =============================================================================
   P02_DOOR   -   door state, interlock signal, counters, door-signal watchdog
   Order : THIRD program block. Runs before the blower logic so that gDoorOK
           is current when the blower outputs are resolved.

   Three different views of one input are produced here, on purpose:

     gDoorClosed        raw X5. Used for the immediate blower drop and for
                        chatter detection - it must NOT be filtered.
     gDoorOK            closed continuously for 1 s AND no chatter alarm.
                        Used as the blower run permissive, so a bouncing
                        switch cannot hammer the contactors.
     gDoorDeb           1 s debounce in BOTH directions. Used for the
                        production counters, so chatter cannot inflate them.

   Local labels required in this POU:  (none)
   ============================================================================= *)

(* -- 1. raw edges (chatter detection uses these) --------------------------- *)
gDoorCloseEdge := gDoorClosed AND NOT gDoorMem;
gDoorOpenEdge  := NOT gDoorClosed AND gDoorMem;
gDoorMem       := gDoorClosed;

(* -- 2. stable-closed filter, 1 s, for the blower interlock ---------------- *)
(*      Opening is instantaneous; closing must be proved for 1 s.             *)
IF gDoorClosed THEN
    IF gTick100ms AND (gDoorStableAcc < 10) THEN
        gDoorStableAcc := gDoorStableAcc + 1;
    END_IF;
ELSE
    gDoorStableAcc := 0;
END_IF;
gDoorClosedStable := gDoorStableAcc >= 10;

gDoorOK := gDoorClosedStable AND NOT gAlmDoorChatter;

(* -- 3. symmetric 1 s debounce for the counters ---------------------------- *)
IF gDoorClosed <> gDoorDeb THEN
    IF gTick100ms THEN
        gDoorDebAcc := gDoorDebAcc + 1;
    END_IF;
    IF gDoorDebAcc >= 10 THEN
        gDoorDeb    := gDoorClosed;
        gDoorDebAcc := 0;
    END_IF;
ELSE
    gDoorDebAcc := 0;
END_IF;

gDoorDebCloseEdge := gDoorDeb AND NOT gDoorDebMem;
gDoorDebOpenEdge  := NOT gDoorDeb AND gDoorDebMem;
gDoorDebMem       := gDoorDeb;

(* -- 4. door event counters ------------------------------------------------ *)
(*      Driven from the debounced state, so a chattering switch adds nothing.  *)
IF gDoorDebOpenEdge THEN
    gCntDoorOpen := gCntDoorOpen + DINT#1;
    gEventCode  := 51;
    gEventParam := 0;
    gEventValue := 0;
    gEventPulse := TRUE;
END_IF;

IF gDoorDebCloseEdge THEN
    gCntDoorClose := gCntDoorClose + DINT#1;
    gEventCode  := 52;
    gEventParam := 0;
    gEventValue := 0;
    gEventPulse := TRUE;
END_IF;

(* -- 5. watchdog A : no 'door closed' signal for longer than the setting ---- *)
(*      Catches a door genuinely left open AND a broken door-switch wire,      *)
(*      because a broken wire reads as 'not closed'.                           *)
IF NOT gDoorClosed THEN
    IF gTick1s AND (gDoorOpenAcc < gSetDoorWdSec) THEN
        gDoorOpenAcc := gDoorOpenAcc + 1;
    END_IF;
ELSE
    gDoorOpenAcc := 0;
END_IF;

gAlmDoorNotClosed := gDoorOpenAcc >= gSetDoorWdSec;

IF gAlmDoorNotClosed AND NOT gAlmDoorNotClosedMem THEN
    gEventCode  := 54;
    gEventParam := 0;
    gEventValue := gDoorOpenAcc;
    gEventPulse := TRUE;
END_IF;
gAlmDoorNotClosedMem := gAlmDoorNotClosed;

(* -- 6. watchdog B : pulsating (chattering) door signal --------------------- *)
(*      The observation window is anchored on the first transition, so a burst *)
(*      cannot be split across two fixed windows and go undetected.            *)
IF gDoorOpenEdge OR gDoorCloseEdge THEN
    IF gChatterCount = 0 THEN
        gChatterWinAcc := 0;
    END_IF;
    gChatterCount := gChatterCount + 1;
END_IF;

IF (gChatterCount > 0) AND gTick1s THEN
    gChatterWinAcc := gChatterWinAcc + 1;
    IF gChatterWinAcc >= gSetChatterWinS THEN
        gChatterWinAcc := 0;
        gChatterCount  := 0;            (* window expired without chatter *)
    END_IF;
END_IF;

IF (gChatterCount >= gSetChatterCnt) AND NOT gAlmDoorChatter THEN
    gAlmDoorChatter := TRUE;            (* latched *)
    gEventCode  := 53;
    gEventParam := 0;
    gEventValue := gChatterCount;
    gEventPulse := TRUE;
END_IF;

(*      Cleared only by an accepted alarm with the signal settled again.       *)
IF gAlarmAcceptPulse AND gDoorClosedStable AND (gChatterCount = 0) THEN
    gAlmDoorChatter := FALSE;
END_IF;

(* -- 7. door alarm summary and the volt-free output ------------------------ *)
gDoorAlarm := gAlmDoorChatter OR gAlmDoorNotClosed;
Y12 := gDoorAlarm;                      (* -KA4 -> -X1:50 / -X1:51 *)
