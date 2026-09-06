(* =============================================================================
   P07_INDICATION   -   pilot lamps, HMI display registers, run-hour totals
   Order : EIGHTH and last program block.

   Holding -S5 lights every lamp (lamp test). The rising edge of the same
   button accepts alarms - see P00. The hooter is deliberately excluded from
   the lamp test.

   LOCAL LABEL REQUIRED IN THIS POU - declare it before converting:
       Label Name  idx    Class  VAR      Data Type  Word [Signed]
   Without it the build reports "Undefined label is used" on all 15
   lines that reference the loop counter.
   The name must NOT be 'i' - GX Works3 rejects it as a reserved word.
   ============================================================================= *)

(* -- 1. pilot lamps ---------------------------------------------------------- *)
Y3  := gLampTest OR gBl1Out;                                    (* -H1 green  *)
Y4  := gLampTest OR gBl2Out;                                    (* -H2 green  *)
Y5  := gLampTest OR gHtrOut;                                    (* -H3 red    *)

(*      Steady = door simply open.  Flashing = door-signal fault.              *)
Y6  := gLampTest
       OR (NOT gDoorClosed AND NOT gDoorAlarm)
       OR (gDoorAlarm AND SM413);                               (* -H4 amber  *)

(*      Flashing = unacknowledged.  Steady = accepted, cause still present.    *)
Y7  := gLampTest
       OR (gAlarmUnack AND SM413)
       OR (gAnyAlarm AND NOT gAlarmUnack);                      (* -H5 red    *)

Y10 := gLampTest OR gAnySlotRunning;                            (* -H6 white  *)

(* -- 2. slot display registers ----------------------------------------------- *)
FOR idx := 1 TO 6 DO
    gSlotH[idx] := DINT_TO_INT(gSlotElapsed[idx] / DINT#3600);
    gSlotM[idx] := DINT_TO_INT((gSlotElapsed[idx] MOD DINT#3600) / DINT#60);
    gSlotS[idx] := DINT_TO_INT(gSlotElapsed[idx] MOD DINT#60);

    (* state word for the HMI: 0 = empty, 1 = curing, 2 = complete.
       One Word Lamp per slot tile instead of three overlaid bit lamps. *)
    IF gSlotComplete[idx] THEN
        gSlotState[idx] := 2;
    ELSIF gSlotRunning[idx] THEN
        gSlotState[idx] := 1;
    ELSE
        gSlotState[idx] := 0;
    END_IF;

    IF gSlotElapsed[idx] >= gSetSlotTargetS THEN
        gSlotRemainMin[idx] := 0;
        gSlotPct[idx]       := 100;
    ELSE
        gSlotRemainMin[idx] :=
            DINT_TO_INT((gSetSlotTargetS - gSlotElapsed[idx] + DINT#59) / DINT#60);
        gSlotPct[idx] :=
            DINT_TO_INT(gSlotElapsed[idx] * DINT#100 / gSetSlotTargetS);
    END_IF;
END_FOR;

(* -- 3. run-hour totals ------------------------------------------------------ *)
IF gTick1s THEN
    IF gHtrOut THEN gTotHtrRunS := gTotHtrRunS + DINT#1; END_IF;
    IF gBl1Out THEN gTotBl1RunS := gTotBl1RunS + DINT#1; END_IF;
    IF gBl2Out THEN gTotBl2RunS := gTotBl2RunS + DINT#1; END_IF;
END_IF;

gTotHtrRunH := DINT_TO_INT(gTotHtrRunS / DINT#3600);
gTotBl1RunH := DINT_TO_INT(gTotBl1RunS / DINT#3600);
gTotBl2RunH := DINT_TO_INT(gTotBl2RunS / DINT#3600);

(* -- 4. door watchdog elapsed, for the HMI ----------------------------------- *)
gDoorOpenMin := gDoorOpenAcc / 60;
