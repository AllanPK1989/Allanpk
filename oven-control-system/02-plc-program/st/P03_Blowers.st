(* =============================================================================
   P03_BLOWERS   -   blower 1 and blower 2, start / stop and door interlock
   Order : FOURTH program block.

   Door interlock behaviour, as specified:
     - the door opening does NOT cancel the run request, it only inhibits the
       output, so the blower restarts by itself when the door is closed again;
     - a stop push-button, an overload trip or an emergency stop DOES cancel
       the run request, so nothing restarts by itself after those.

   Local labels required in this POU:  (none)
   ============================================================================= *)

(* -- 1. push-button edges --------------------------------------------------- *)
gBl1StartEdge := X1 AND NOT gBl1StartMem;
gBl1StartMem  := X1;
gBl2StartEdge := X3 AND NOT gBl2StartMem;
gBl2StartMem  := X3;

(* -- 2. blower 1 run request ------------------------------------------------ *)
IF (gBl1StartEdge OR gHmiBl1Start) AND gBl1Permit AND NOT gManualMode THEN
    gBl1RunReq := TRUE;
END_IF;
gHmiBl1Start := FALSE;

IF NOT gBl1StopOK                       (* stop pressed, or a broken wire *)
   OR gHmiBl1Stop
   OR NOT gBl1Permit                    (* E-stop or overload *)
   OR gManualMode THEN
    gBl1RunReq := FALSE;
END_IF;
gHmiBl1Stop := FALSE;

(* -- 3. blower 2 run request ------------------------------------------------ *)
IF (gBl2StartEdge OR gHmiBl2Start) AND gBl2Permit AND NOT gManualMode THEN
    gBl2RunReq := TRUE;
END_IF;
gHmiBl2Start := FALSE;

IF NOT gBl2StopOK
   OR gHmiBl2Stop
   OR NOT gBl2Permit
   OR gManualMode THEN
    gBl2RunReq := FALSE;
END_IF;
gHmiBl2Stop := FALSE;

(* -- 4. outputs ------------------------------------------------------------- *)
(*      gDoorOK is the interlock: it goes FALSE the instant the door opens and  *)
(*      only returns after the door has been proved closed for 1 s with no      *)
(*      chatter alarm standing.                                                 *)
IF gManualMode THEN
    gBl1Out := gManBl1 AND gBl1Permit AND gDoorOK;
    gBl2Out := gManBl2 AND gBl2Permit AND gDoorOK;
ELSE
    gBl1Out := gBl1RunReq AND gBl1Permit AND gDoorOK;
    gBl2Out := gBl2RunReq AND gBl2Permit AND gDoorOK;
END_IF;

Y0 := gBl1Out;                          (* -KA1 -> -K1 *)
Y1 := gBl2Out;                          (* -KA2 -> -K2 *)
