(* =============================================================================
   P07_INDICATION   -   pilot lamps, HMI display registers, run-hour totals
   Order : EIGHTH and last program block.

   Holding -S5 lights every lamp (lamp test). The rising edge of the same
   button accepts alarms - see P00. The hooter is deliberately excluded from
   the lamp test.

   Local labels required in this POU:   i : INT
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
FOR i := 1 TO 6 DO
    gSlotH[i] := DINT_TO_INT(gSlotElapsed[i] / DINT#3600);
    gSlotM[i] := DINT_TO_INT((gSlotElapsed[i] MOD DINT#3600) / DINT#60);
    gSlotS[i] := DINT_TO_INT(gSlotElapsed[i] MOD DINT#60);

    IF gSlotElapsed[i] >= gSetSlotTargetS THEN
        gSlotRemainMin[i] := 0;
        gSlotPct[i]       := 100;
    ELSE
        gSlotRemainMin[i] :=
            DINT_TO_INT((gSetSlotTargetS - gSlotElapsed[i] + DINT#59) / DINT#60);
        gSlotPct[i] :=
            DINT_TO_INT(gSlotElapsed[i] * DINT#100 / gSetSlotTargetS);
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
