(* =============================================================================
   P04_HEATER   -   heater command, contactor anti-chatter, heat-up watchdog
   Order : FIFTH program block.

   The PID controller -A2 keeps the temperature loop. The PLC only repeats the
   controller's demand contact (X6) to the heater contactor, adds the safety
   permissives, and limits how often the contactor is allowed to operate.

   The door interlock is deliberately NOT in this block: the heater stays
   energised while the oven door is open, as specified. The only protection
   that limits oven temperature in that condition is the hard-wired high-limit
   thermostat -B3, which is in the -K3 coil circuit on schematic sheet 08.

   Local labels required in this POU:  (none)
   ============================================================================= *)

(* -- 1. minimum ON / minimum OFF state machine ------------------------------ *)
(*      -K3 is an AC-1 contactor. Without this limiter a 20 s PID cycle would   *)
(*      give roughly 180 operations an hour; this caps it at 90.                *)
IF gHtrCmd THEN
    IF gTick1s AND (gHtrMinOnAcc < gSetHtrMinOnS) THEN
        gHtrMinOnAcc := gHtrMinOnAcc + 1;
    END_IF;
    IF (gHtrMinOnAcc >= gSetHtrMinOnS) AND NOT gHeatDemand THEN
        gHtrCmd       := FALSE;
        gHtrMinOffAcc := 0;
    END_IF;
ELSE
    IF gTick1s AND (gHtrMinOffAcc < gSetHtrMinOffS) THEN
        gHtrMinOffAcc := gHtrMinOffAcc + 1;
    END_IF;
    IF (gHtrMinOffAcc >= gSetHtrMinOffS) AND gHeatDemand THEN
        gHtrCmd      := TRUE;
        gHtrMinOnAcc := 0;
    END_IF;
END_IF;

(* -- 2. output -------------------------------------------------------------- *)
(*      The minimum-ON hold never overrides a permissive: losing gHtrPermit     *)
(*      drops Y2 in the same scan. The hardware drops -K3 anyway through the    *)
(*      overload and high-limit contacts in the coil circuit.                   *)
IF gManualMode THEN
    gHtrOut := gManHtr AND gHtrPermit;
ELSE
    gHtrOut := gHtrCmd AND gHtrPermit;
END_IF;

Y2 := gHtrOut;                          (* -KA3 -> -K3 *)

(* -- 3. heat-up watchdog ---------------------------------------------------- *)
(*      X6 closes when the controller calls for heat and opens when the oven    *)
(*      reaches set point. In normal running X6 cycles, and every drop-out      *)
(*      resets this timer. If X6 stays closed for the whole watchdog period the *)
(*      oven has never reached set point - a failed element, a stuck-open       *)
(*      contactor, a sensor reading low, or lost insulation.                    *)
(*                                                                             *)
(*      This is a WARNING only. It does not trip the heater: the condition is   *)
(*      too cold, not too hot, and -B3 handles too hot.                         *)
IF gHeatDemand THEN
    IF gTick1s AND (gHeatUpAcc < gSetHeatUpWdMin * 60) THEN
        gHeatUpAcc := gHeatUpAcc + 1;
    END_IF;
ELSE
    gHeatUpAcc := 0;                    (* controller satisfied - restart *)
END_IF;

gAlmHeatUp := gHeatUpAcc >= gSetHeatUpWdMin * 60;

IF gAlmHeatUp AND NOT gAlmHeatUpMem THEN
    gEventCode  := 81;
    gEventParam := 0;
    gEventValue := gSetHeatUpWdMin;
    gEventPulse := TRUE;
END_IF;
gAlmHeatUpMem := gAlmHeatUp;

(* -- 4. elapsed-time display for the HMI ------------------------------------ *)
gHeatUpMin := gHeatUpAcc / 60;
