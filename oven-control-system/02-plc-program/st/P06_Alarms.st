(* =============================================================================
   P06_ALARMS   -   alarm collection, contactor feedback, hooter and accept
   Order : SEVENTH program block. Runs after the outputs are resolved so that
           the contactor feedback comparison uses this scan's commands.

   gAlmBits is an ARRAY [0..15] OF Bit assigned to M700. The named alarm
   labels gAlmEStop .. gAlmLotMismatch are assigned to M700 .. M712 and
   therefore OVERLAY the array - one alarm, two names. The array exists so the
   summary loop below stays short, and so the GOT can watch M700-M715 as a
   single bit-device alarm block.

   LOCAL LABEL REQUIRED IN THIS POU - declare it before converting:
       Label Name  idx    Class  VAR      Data Type  Word [Signed]
   Without it the build reports "Undefined label is used" on all 6
   lines that reference the loop counter.
   The name must NOT be 'i' - GX Works3 rejects it as a reserved word.
   ============================================================================= *)

(* -- 1. contactor feedback, 1 s disagreement filter ------------------------- *)
(*      Catches a welded contactor (commanded OFF, feedback still ON) and one   *)
(*      that failed to pull in (commanded ON, no feedback).                     *)
IF gBl1Out <> gK1Closed THEN
    IF gTick100ms AND (gK1FbAcc < 10) THEN gK1FbAcc := gK1FbAcc + 1; END_IF;
ELSE
    gK1FbAcc := 0;
END_IF;
gAlmK1Fault := gK1FbAcc >= 10;

IF gBl2Out <> gK2Closed THEN
    IF gTick100ms AND (gK2FbAcc < 10) THEN gK2FbAcc := gK2FbAcc + 1; END_IF;
ELSE
    gK2FbAcc := 0;
END_IF;
gAlmK2Fault := gK2FbAcc >= 10;

IF gHtrOut <> gK3Closed THEN
    IF gTick100ms AND (gK3FbAcc < 10) THEN gK3FbAcc := gK3FbAcc + 1; END_IF;
ELSE
    gK3FbAcc := 0;
END_IF;
gAlmK3Fault := gK3FbAcc >= 10;

(* -- 2. direct alarm conditions --------------------------------------------- *)
gAlmEStop     := NOT gEStopOK;
gAlmBl1Ol     := gBl1OlTrip;
gAlmBl2Ol     := gBl2OlTrip;
gAlmHtrOl     := gHtrOlTrip;
gAlmHighLimit := NOT gHighLimitOK;
gAlmPidFault  := NOT gPidOK;
(*  gAlmHeatUp          set in P04                                             *)
(*  gAlmDoorChatter     set in P02 (latched)                                   *)
(*  gAlmDoorNotClosed   set in P02                                             *)
(*  gAlmLotMismatch     set in P05                                             *)
gAlmCurePaused := gSlotTimersPaused;

(* -- 3. summary and new-alarm detection ------------------------------------- *)
gAnyAlarm  := FALSE;
gAlarmNew  := FALSE;

FOR idx := 0 TO 15 DO
    IF gAlmBits[idx] THEN
        gAnyAlarm := TRUE;
        IF NOT gAlmMem[idx] THEN
            gAlarmNew := TRUE;          (* a NEW alarm, even if others stand *)
        END_IF;
    END_IF;
    gAlmMem[idx] := gAlmBits[idx];
END_FOR;

(* -- 4. unacknowledged latch ------------------------------------------------ *)
IF gAlarmNew THEN
    gAlarmUnack := TRUE;
END_IF;
IF gAlarmAcceptPulse OR NOT gAnyAlarm THEN
    gAlarmUnack := FALSE;
END_IF;

(* -- 5. hooter --------------------------------------------------------------- *)
(*      Silences on accept; the lamp keeps showing until the cause clears.      *)
gHooter := gAlarmUnack;
Y11 := gHooter;                         (* -B4 *)
