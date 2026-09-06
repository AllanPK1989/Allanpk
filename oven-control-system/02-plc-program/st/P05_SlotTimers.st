(* =============================================================================
   P05_SLOTTIMERS   -   six retentive 2 hour slot timers, lot counters
   Order : SIXTH program block.

   Slot rules
   ----------
   1. A slot is started from its own HMI button. It then runs to 02:00:00.
   2. A running slot cannot be started again and cannot be reset.
   3. When it reaches 02:00:00 the slot is COMPLETE and the reset button works.
      A normal reset counts one lot UNLOADED.
   4. Before 02:00:00 the reset button works only for a logged-in maintenance
      technician (level 2). That is an EARLY RESET: it clears the slot but is
      NOT counted as an unload, and it is written to the event log with the
      slot number and the minutes it was cut short.
   5. gSlotElapsed lives in the latched device area, so a power failure pauses
      a cure and it resumes from the accumulated value - it never restarts.

   The malpractice figure
   ----------------------
   gLotsUnaccounted = loaded - unloaded - slots currently running.
   It is computed from the counters and the live slot states, not read back
   from the early-reset counter, so it also exposes tampering with either
   counter. Any non-zero value raises the mismatch indication.

   LOCAL LABEL REQUIRED IN THIS POU - declare it before converting:
       Label Name  i      Class  VAR      Data Type  Word [Signed]
   Without it the build reports "Undefined label is used" on all 30
   lines that reference the loop counter.
   ============================================================================= *)

(* -- 0. may the cure timers advance? ---------------------------------------- *)
(*      gSetSlotGated is ON by default: a cure timer must not run on towards    *)
(*      completion while the oven cannot actually hold the product at           *)
(*      temperature. gAlmHeatUp is fresh here because P04 has already run.      *)
gSlotRunPermit := gEStopOK
                  AND gHighLimitOK
                  AND gPidOK
                  AND NOT gHtrOlTrip
                  AND NOT gAlmHeatUp;

gSlotsActive := 0;

FOR i := 1 TO 6 DO

    (* -- 1. start ----------------------------------------------------------- *)
    IF gHmiSlotStart[i] THEN
        gHmiSlotStart[i] := FALSE;
        IF NOT gSlotRunning[i] AND NOT gSlotComplete[i] THEN
            gSlotRunning[i] := TRUE;
            gSlotElapsed[i] := DINT#0;
            gCntLotsLoaded  := gCntLotsLoaded + DINT#1;
            gEventCode  := 10 + i;                  (* 11..16 slot started *)
            gEventParam := i;
            gEventValue := 0;
            gEventPulse := TRUE;
        END_IF;
    END_IF;

    (* -- 2. run ------------------------------------------------------------- *)
    IF gSlotRunning[i] AND NOT gSlotComplete[i] THEN
        IF gTick1s AND (NOT gSetSlotGated OR gSlotRunPermit) THEN
            gSlotElapsed[i] := gSlotElapsed[i] + DINT#1;
        END_IF;
        IF gSlotElapsed[i] >= gSetSlotTargetS THEN
            gSlotComplete[i] := TRUE;
            gEventCode  := 20 + i;                  (* 21..26 slot complete *)
            gEventParam := i;
            gEventValue := 0;
            gEventPulse := TRUE;
        END_IF;
    END_IF;

    (* -- 3. reset ----------------------------------------------------------- *)
    IF gHmiSlotReset[i] THEN
        gHmiSlotReset[i] := FALSE;

        IF gSlotComplete[i] THEN
            (* normal reset at the end of the cure - counts as an unload *)
            gSlotRunning[i]  := FALSE;
            gSlotComplete[i] := FALSE;
            gSlotElapsed[i]  := 0;
            gCntLotsUnloaded := gCntLotsUnloaded + DINT#1;
            gEventCode  := 30 + i;                  (* 31..36 normal reset *)
            gEventParam := i;
            gEventValue := 0;
            gEventPulse := TRUE;

        ELSIF gSlotRunning[i] AND gMaintLoggedIn THEN
            (* EARLY RESET - MAINTENANCE passcode only, NOT an unload *)
            gEventValue      := DINT_TO_INT(gSlotElapsed[i] / DINT#60);
            gSlotRunning[i]  := FALSE;
            gSlotComplete[i] := FALSE;
            gSlotElapsed[i]  := 0;
            gCntEarlyReset   := gCntEarlyReset + DINT#1;
            gEventCode  := 40 + i;                  (* 41..46 EARLY reset *)
            gEventParam := i;
            gEventPulse := TRUE;
        END_IF;
    END_IF;

    (* -- 4. running-slot tally ---------------------------------------------- *)
    IF gSlotRunning[i] THEN
        gSlotsActive := gSlotsActive + 1;
    END_IF;

END_FOR;

gAnySlotRunning := gSlotsActive > 0;

(* -- 4a. paused indication --------------------------------------------------- *)
(*      Operators must be able to see WHY a cure timer is not advancing.        *)
gSlotTimersPaused := gSetSlotGated AND NOT gSlotRunPermit AND gAnySlotRunning;

IF gSlotTimersPaused AND NOT gSlotPausedMem THEN
    gEventCode  := 55;
    gEventParam := gSlotsActive;
    gEventValue := 0;
    gEventPulse := TRUE;
END_IF;
IF NOT gSlotTimersPaused AND gSlotPausedMem THEN
    gEventCode  := 56;
    gEventParam := gSlotsActive;
    gEventValue := 0;
    gEventPulse := TRUE;
END_IF;
gSlotPausedMem := gSlotTimersPaused;

(* -- 5. lot reconciliation -------------------------------------------------- *)
gLotsUnaccounted := gCntLotsLoaded - gCntLotsUnloaded - INT_TO_DINT(gSlotsActive);
gAlmLotMismatch  := gLotsUnaccounted <> DINT#0;

(* -- 6. counter resets - QUALITY passcode only ------------------------------- *)
(*      NOT maintenance. Maintenance performs the early resets; they must not   *)
(*      be able to clear the counters that record them. See P01_Security.       *)
IF gHmiResetDoorCnt THEN
    gHmiResetDoorCnt := FALSE;
    IF gQualityLoggedIn THEN
        gCntDoorOpen  := DINT#0;
        gCntDoorClose := DINT#0;
        gEventCode  := 61;
        gEventParam := 0;
        gEventValue := 0;
        gEventPulse := TRUE;
    END_IF;
END_IF;

IF gHmiResetLotCnt THEN
    gHmiResetLotCnt := FALSE;
    IF gQualityLoggedIn THEN
        gCntLotsLoaded   := DINT#0;
        gCntLotsUnloaded := DINT#0;
        gCntEarlyReset   := DINT#0;
        gEventCode  := 62;
        gEventParam := 0;
        gEventValue := 0;
        gEventPulse := TRUE;
    END_IF;
END_IF;
