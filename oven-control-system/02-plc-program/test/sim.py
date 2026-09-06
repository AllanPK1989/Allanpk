"""Behavioural model of the OVN-2026-01 PLC program.

This is a faithful Python transcription of the ST in ../st, used to test the
control logic before commissioning. It is a TEST HARNESS, not the deliverable:
the ST files are the program. If you change the ST, change this too and re-run.

Scan time modelled at 10 ms.
"""

SCAN_MS = 10


class Oven:
    def __init__(self):
        # ---- inputs (schematic sheet 06) ----
        self.X0 = True    # E-stop released      (NC, fail-safe)
        self.X1 = False   # blower 1 START
        self.X2 = True    # blower 1 STOP        (NC, fail-safe)
        self.X3 = False   # blower 2 START
        self.X4 = True    # blower 2 STOP        (NC, fail-safe)
        self.X5 = True    # door closed
        self.X6 = False   # heat demand from PID
        self.X7 = True    # PID healthy          (NC, fail-safe)
        self.X10 = False  # blower 1 OL tripped
        self.X11 = False  # blower 2 OL tripped
        self.X12 = False  # heater OL tripped
        self.X13 = True   # high limit healthy   (NC, fail-safe)
        self.X14 = False  # K1 feedback
        self.X15 = False  # K2 feedback
        self.X16 = False  # K3 feedback
        self.X17 = False  # lamp test / accept

        # ---- outputs ----
        self.Y0 = self.Y1 = self.Y2 = False
        self.Y3 = self.Y4 = self.Y5 = self.Y6 = self.Y7 = False
        self.Y10 = self.Y11 = self.Y12 = False

        self.scan = 0
        self._sm402 = True
        self.events = []
        self.autofeedback = True     # model contactors that follow their command

        self._init_latched()
        self._init_volatile()

    # ------------------------------------------------------------------ latch
    def _init_latched(self):
        self.gSlotRunning = [False] * 7      # index 1..6
        self.gSlotComplete = [False] * 7
        self.gSlotElapsed = [0] * 7
        self.gCntDoorOpen = 0
        self.gCntDoorClose = 0
        self.gCntLotsLoaded = 0
        self.gCntLotsUnloaded = 0
        self.gCntEarlyReset = 0
        self.gTotHtrRunS = self.gTotBl1RunS = self.gTotBl2RunS = 0
        self.gDefaultsWritten = False
        self.gSetHtrNeedsAir = False
        self.gSetSlotGated = True

    def _init_volatile(self):
        self.gTick100msMem = self.gTick1sMem = False
        self.gTick100ms = self.gTick1s = False
        self.gBl1RunReq = self.gBl2RunReq = False
        self.gHtrCmd = False
        self.gManualMode = False
        self.gMaintLoggedIn = False
        self.gQualityLoggedIn = False
        self.gFailedAttempts = 0
        self.gLockoutAcc = 0
        self.gHmiPasscodeEntry = 0
        self.gActiveRole = 0
        self.gSlotTimersPaused = False
        self.gSlotPausedMem = False
        self.gHtrMinOnAcc = self.gHtrMinOffAcc = 0
        self.gHeatUpAcc = 0
        self.gDoorOpenAcc = 0
        self.gChatterCount = self.gChatterWinAcc = 0
        self.gDoorStableAcc = self.gDoorDebAcc = 0
        self.gDoorDeb = self.X5
        self.gDoorDebMem = self.X5
        self.gDoorMem = self.X5
        self.gAcceptMem = False
        self.gBl1StartMem = self.gBl2StartMem = False
        self.gK1FbAcc = self.gK2FbAcc = self.gK3FbAcc = 0
        self.gManualTmoAcc = self.gMaintTmoAcc = self.gQualityTmoAcc = 0
        self.gAlmDoorChatter = False
        self.gAlmDoorNotClosedMem = self.gAlmHeatUpMem = False
        self.gAlarmUnack = False
        self.gAlmMem = [False] * 16
        self.gBl1Out = self.gBl2Out = self.gHtrOut = False
        self.gEventPulse = False
        self.gAnySlotRunning = False
        # HMI command bits
        for n in ("gHmiBl1Start", "gHmiBl1Stop", "gHmiBl2Start", "gHmiBl2Stop",
                  "gHmiAlarmAccept", "gHmiResetDoorCnt", "gHmiResetLotCnt",
                  "gHmiManualReq", "gHmiManualExit", "gHmiMaintLoginReq",
                  "gHmiQualityLoginReq", "gHmiLogout",
                  "gHmiActivity", "gHmiManBl1", "gHmiManBl2", "gHmiManHtr"):
            setattr(self, n, False)
        self.gHmiSlotStart = [False] * 7
        self.gHmiSlotReset = [False] * 7

    def power_cycle(self):
        """Supply lost and restored: volatile state clears, latched survives."""
        self._init_volatile()
        self._sm402 = True

    # ------------------------------------------------------------------- scan
    def step(self):
        self.scan += 1
        sm402 = self._sm402
        self._sm402 = False
        ms = self.scan * SCAN_MS
        self.gTick100ms = (ms % 100 == 0)
        self.gTick1s = (ms % 1000 == 0)
        sm413 = ((ms // 1000) % 2 == 0)

        self._p00(sm402)
        self._p01()
        self._p02()
        self._p03()
        self._p04()
        self._p05()
        self._p06()
        self._p07(sm413)

        if self.autofeedback:
            self.X14, self.X15, self.X16 = self.Y0, self.Y1, self.Y2

    def run(self, seconds):
        for _ in range(int(seconds * 1000 / SCAN_MS)):
            self.step()

    def _ev(self, code, param=0, value=0):
        self.gEventCode, self.gEventParam, self.gEventValue = code, param, value
        self.gEventPulse = True
        self.events.append((self.scan * SCAN_MS, code, param, value))

    # ----------------------------------------------------------------- blocks
    def _p00(self, sm402):
        self.gEventPulse = False
        if not self.gDefaultsWritten:
            self.gSetHeatUpWdMin = 60
            self.gSetDoorWdSec = 600
            self.gSetChatterCnt = 8
            self.gSetChatterWinS = 10
            self.gSetHtrMinOnS = 20
            self.gSetHtrMinOffS = 20
            self.gSetManualTmoS = 300
            self.gSetLoginTmoS = 300
            self.gSetSlotTargetS = 7200
            self.gSetMaintCode = 2468
            self.gSetQualityCode = 1357
            self.gSetMaxAttempts = 3
            self.gSetLockoutS = 300
            self.gDefaultsWritten = True
        if sm402:
            self._ev(1)

        self.gEStopOK, self.gBl1StopOK, self.gBl2StopOK = self.X0, self.X2, self.X4
        self.gPidOK, self.gHighLimitOK = self.X7, self.X13
        self.gDoorClosed, self.gHeatDemand = self.X5, self.X6
        self.gBl1OlTrip, self.gBl2OlTrip, self.gHtrOlTrip = self.X10, self.X11, self.X12
        self.gK1Closed, self.gK2Closed, self.gK3Closed = self.X14, self.X15, self.X16
        self.gLampTest = self.X17

        self.gAcceptEdge = self.X17 and not self.gAcceptMem
        self.gAcceptMem = self.X17
        self.gAlarmAcceptPulse = self.gAcceptEdge or self.gHmiAlarmAccept
        self.gHmiAlarmAccept = False

        self.gBl1Permit = self.gEStopOK and not self.gBl1OlTrip
        self.gBl2Permit = self.gEStopOK and not self.gBl2OlTrip
        self.gHtrPermit = (self.gEStopOK and not self.gHtrOlTrip
                           and self.gHighLimitOK and self.gPidOK)
        if self.gSetHtrNeedsAir:
            self.gHtrPermit = self.gHtrPermit and (
                self.gK1Closed or self.gK2Closed or not self.gDoorClosed)

    def _p01(self):
        if self.gLockoutAcc > 0 and self.gTick1s:
            self.gLockoutAcc -= 1
        self.gLockoutActive = self.gLockoutAcc > 0

        if self.gHmiMaintLoginReq or self.gHmiQualityLoginReq:
            if self.gLockoutActive:
                self._ev(76, 0, self.gLockoutAcc)
            elif self.gHmiMaintLoginReq and self.gHmiPasscodeEntry == self.gSetMaintCode:
                self.gMaintLoggedIn = True
                self.gQualityLoggedIn = False
                self.gMaintTmoAcc = 0
                self.gFailedAttempts = 0
                self._ev(73)
            elif self.gHmiQualityLoginReq and self.gHmiPasscodeEntry == self.gSetQualityCode:
                self.gQualityLoggedIn = True
                self.gMaintLoggedIn = False
                self.gQualityTmoAcc = 0
                self.gFailedAttempts = 0
                self._ev(74)
            else:
                self.gFailedAttempts += 1
                self._ev(75, 0, self.gFailedAttempts)
                if self.gFailedAttempts >= self.gSetMaxAttempts:
                    self.gLockoutAcc = self.gSetLockoutS
                    self.gFailedAttempts = 0
            self.gHmiMaintLoginReq = False
            self.gHmiQualityLoginReq = False
            self.gHmiPasscodeEntry = 0

        if self.gHmiLogout:
            self.gHmiLogout = False
            self.gMaintLoggedIn = False
            self.gQualityLoggedIn = False
            self.gHmiPasscodeEntry = 0
            self._ev(77)

        for flag, acc in (("gMaintLoggedIn", "gMaintTmoAcc"),
                          ("gQualityLoggedIn", "gQualityTmoAcc")):
            if getattr(self, flag):
                if self.gHmiActivity:
                    setattr(self, acc, 0)
                if self.gTick1s:
                    setattr(self, acc, getattr(self, acc) + 1)
                if getattr(self, acc) >= self.gSetLoginTmoS:
                    setattr(self, flag, False)
                    setattr(self, acc, 0)
                    self.gHmiPasscodeEntry = 0
            else:
                setattr(self, acc, 0)
        self.gHmiActivity = False

        self.gActiveRole = 1 if self.gMaintLoggedIn else (2 if self.gQualityLoggedIn else 0)

        self.gManualPermit = (self.gMaintLoggedIn and self.gEStopOK and self.gDoorOK
                              and not self.gBl1OlTrip and not self.gBl2OlTrip
                              and not self.gHtrOlTrip and self.gHighLimitOK
                              and not self.gAnySlotRunning)

        if self.gHmiManualReq:
            self.gHmiManualReq = False
            if self.gManualPermit and not self.gManualMode:
                self.gManualMode = True
                self.gManualTmoAcc = 0
                self.gBl1RunReq = self.gBl2RunReq = False
                self._ev(71)

        if self.gManualMode:
            if self.gTick1s:
                self.gManualTmoAcc += 1
            if (self.gManualTmoAcc >= self.gSetManualTmoS
                    or not self.gManualPermit or self.gHmiManualExit):
                self.gManualMode = False
                self.gHmiManualExit = False
                self._ev(72)
        else:
            self.gManualTmoAcc = 0
            self.gHmiManualExit = False

        self.gManBl1 = self.gHmiManBl1 and self.gManualMode
        self.gManBl2 = self.gHmiManBl2 and self.gManualMode
        self.gManHtr = self.gHmiManHtr and self.gManualMode

    def _p02(self):
        self.gDoorCloseEdge = self.gDoorClosed and not self.gDoorMem
        self.gDoorOpenEdge = (not self.gDoorClosed) and self.gDoorMem
        self.gDoorMem = self.gDoorClosed

        if self.gDoorClosed:
            if self.gTick100ms and self.gDoorStableAcc < 10:
                self.gDoorStableAcc += 1
        else:
            self.gDoorStableAcc = 0
        self.gDoorClosedStable = self.gDoorStableAcc >= 10
        self.gDoorOK = self.gDoorClosedStable and not self.gAlmDoorChatter

        if self.gDoorClosed != self.gDoorDeb:
            if self.gTick100ms:
                self.gDoorDebAcc += 1
            if self.gDoorDebAcc >= 10:
                self.gDoorDeb = self.gDoorClosed
                self.gDoorDebAcc = 0
        else:
            self.gDoorDebAcc = 0

        self.gDoorDebCloseEdge = self.gDoorDeb and not self.gDoorDebMem
        self.gDoorDebOpenEdge = (not self.gDoorDeb) and self.gDoorDebMem
        self.gDoorDebMem = self.gDoorDeb

        if self.gDoorDebOpenEdge:
            self.gCntDoorOpen += 1
            self._ev(51)
        if self.gDoorDebCloseEdge:
            self.gCntDoorClose += 1
            self._ev(52)

        if not self.gDoorClosed:
            if self.gTick1s and self.gDoorOpenAcc < self.gSetDoorWdSec:
                self.gDoorOpenAcc += 1
        else:
            self.gDoorOpenAcc = 0
        self.gAlmDoorNotClosed = self.gDoorOpenAcc >= self.gSetDoorWdSec
        if self.gAlmDoorNotClosed and not self.gAlmDoorNotClosedMem:
            self._ev(54, 0, self.gDoorOpenAcc)
        self.gAlmDoorNotClosedMem = self.gAlmDoorNotClosed

        if self.gDoorOpenEdge or self.gDoorCloseEdge:
            if self.gChatterCount == 0:
                self.gChatterWinAcc = 0
            self.gChatterCount += 1
        if self.gChatterCount > 0 and self.gTick1s:
            self.gChatterWinAcc += 1
            if self.gChatterWinAcc >= self.gSetChatterWinS:
                self.gChatterWinAcc = 0
                self.gChatterCount = 0
        if self.gChatterCount >= self.gSetChatterCnt and not self.gAlmDoorChatter:
            self.gAlmDoorChatter = True
            self._ev(53, 0, self.gChatterCount)
        if self.gAlarmAcceptPulse and self.gDoorClosedStable and self.gChatterCount == 0:
            self.gAlmDoorChatter = False

        self.gDoorAlarm = self.gAlmDoorChatter or self.gAlmDoorNotClosed
        self.Y12 = self.gDoorAlarm

    def _p03(self):
        self.gBl1StartEdge = self.X1 and not self.gBl1StartMem
        self.gBl1StartMem = self.X1
        self.gBl2StartEdge = self.X3 and not self.gBl2StartMem
        self.gBl2StartMem = self.X3

        if ((self.gBl1StartEdge or self.gHmiBl1Start)
                and self.gBl1Permit and not self.gManualMode):
            self.gBl1RunReq = True
        self.gHmiBl1Start = False
        if (not self.gBl1StopOK or self.gHmiBl1Stop
                or not self.gBl1Permit or self.gManualMode):
            self.gBl1RunReq = False
        self.gHmiBl1Stop = False

        if ((self.gBl2StartEdge or self.gHmiBl2Start)
                and self.gBl2Permit and not self.gManualMode):
            self.gBl2RunReq = True
        self.gHmiBl2Start = False
        if (not self.gBl2StopOK or self.gHmiBl2Stop
                or not self.gBl2Permit or self.gManualMode):
            self.gBl2RunReq = False
        self.gHmiBl2Stop = False

        if self.gManualMode:
            self.gBl1Out = self.gManBl1 and self.gBl1Permit and self.gDoorOK
            self.gBl2Out = self.gManBl2 and self.gBl2Permit and self.gDoorOK
        else:
            self.gBl1Out = self.gBl1RunReq and self.gBl1Permit and self.gDoorOK
            self.gBl2Out = self.gBl2RunReq and self.gBl2Permit and self.gDoorOK
        self.Y0, self.Y1 = self.gBl1Out, self.gBl2Out

    def _p04(self):
        if self.gHtrCmd:
            if self.gTick1s and self.gHtrMinOnAcc < self.gSetHtrMinOnS:
                self.gHtrMinOnAcc += 1
            if self.gHtrMinOnAcc >= self.gSetHtrMinOnS and not self.gHeatDemand:
                self.gHtrCmd = False
                self.gHtrMinOffAcc = 0
        else:
            if self.gTick1s and self.gHtrMinOffAcc < self.gSetHtrMinOffS:
                self.gHtrMinOffAcc += 1
            if self.gHtrMinOffAcc >= self.gSetHtrMinOffS and self.gHeatDemand:
                self.gHtrCmd = True
                self.gHtrMinOnAcc = 0

        if self.gManualMode:
            self.gHtrOut = self.gManHtr and self.gHtrPermit
        else:
            self.gHtrOut = self.gHtrCmd and self.gHtrPermit
        self.Y2 = self.gHtrOut

        if self.gHeatDemand:
            if self.gTick1s and self.gHeatUpAcc < self.gSetHeatUpWdMin * 60:
                self.gHeatUpAcc += 1
        else:
            self.gHeatUpAcc = 0
        self.gAlmHeatUp = self.gHeatUpAcc >= self.gSetHeatUpWdMin * 60
        if self.gAlmHeatUp and not self.gAlmHeatUpMem:
            self._ev(81, 0, self.gSetHeatUpWdMin)
        self.gAlmHeatUpMem = self.gAlmHeatUp
        self.gHeatUpMin = self.gHeatUpAcc // 60

    def _p05(self):
        self.gSlotRunPermit = (self.gEStopOK and self.gHighLimitOK and self.gPidOK
                               and not self.gHtrOlTrip and not self.gAlmHeatUp)
        self.gSlotsActive = 0
        for i in range(1, 7):
            if self.gHmiSlotStart[i]:
                self.gHmiSlotStart[i] = False
                if not self.gSlotRunning[i] and not self.gSlotComplete[i]:
                    self.gSlotRunning[i] = True
                    self.gSlotElapsed[i] = 0
                    self.gCntLotsLoaded += 1
                    self._ev(10 + i, i)

            if self.gSlotRunning[i] and not self.gSlotComplete[i]:
                if self.gTick1s and (not self.gSetSlotGated or self.gSlotRunPermit):
                    self.gSlotElapsed[i] += 1
                if self.gSlotElapsed[i] >= self.gSetSlotTargetS:
                    self.gSlotComplete[i] = True
                    self._ev(20 + i, i)

            if self.gHmiSlotReset[i]:
                self.gHmiSlotReset[i] = False
                if self.gSlotComplete[i]:
                    self.gSlotRunning[i] = False
                    self.gSlotComplete[i] = False
                    self.gSlotElapsed[i] = 0
                    self.gCntLotsUnloaded += 1
                    self._ev(30 + i, i)
                elif self.gSlotRunning[i] and self.gMaintLoggedIn:
                    mins = self.gSlotElapsed[i] // 60
                    self.gSlotRunning[i] = False
                    self.gSlotComplete[i] = False
                    self.gSlotElapsed[i] = 0
                    self.gCntEarlyReset += 1
                    self._ev(40 + i, i, mins)

            if self.gSlotRunning[i]:
                self.gSlotsActive += 1

        self.gAnySlotRunning = self.gSlotsActive > 0
        self.gSlotTimersPaused = (self.gSetSlotGated and not self.gSlotRunPermit
                                  and self.gAnySlotRunning)
        if self.gSlotTimersPaused and not self.gSlotPausedMem:
            self._ev(55, self.gSlotsActive)
        if not self.gSlotTimersPaused and self.gSlotPausedMem:
            self._ev(56, self.gSlotsActive)
        self.gSlotPausedMem = self.gSlotTimersPaused
        self.gLotsUnaccounted = (self.gCntLotsLoaded - self.gCntLotsUnloaded
                                 - self.gSlotsActive)
        self.gAlmLotMismatch = self.gLotsUnaccounted != 0

        if self.gHmiResetDoorCnt:
            self.gHmiResetDoorCnt = False
            if self.gQualityLoggedIn:
                self.gCntDoorOpen = self.gCntDoorClose = 0
                self._ev(61)
        if self.gHmiResetLotCnt:
            self.gHmiResetLotCnt = False
            if self.gQualityLoggedIn:
                self.gCntLotsLoaded = self.gCntLotsUnloaded = self.gCntEarlyReset = 0
                self._ev(62)

    def _p06(self):
        for cmd, fb, acc in (("gBl1Out", "gK1Closed", "gK1FbAcc"),
                             ("gBl2Out", "gK2Closed", "gK2FbAcc"),
                             ("gHtrOut", "gK3Closed", "gK3FbAcc")):
            if getattr(self, cmd) != getattr(self, fb):
                if self.gTick100ms and getattr(self, acc) < 10:
                    setattr(self, acc, getattr(self, acc) + 1)
            else:
                setattr(self, acc, 0)
        self.gAlmK1Fault = self.gK1FbAcc >= 10
        self.gAlmK2Fault = self.gK2FbAcc >= 10
        self.gAlmK3Fault = self.gK3FbAcc >= 10

        self.gAlmEStop = not self.gEStopOK
        self.gAlmBl1Ol = self.gBl1OlTrip
        self.gAlmBl2Ol = self.gBl2OlTrip
        self.gAlmHtrOl = self.gHtrOlTrip
        self.gAlmHighLimit = not self.gHighLimitOK
        self.gAlmPidFault = not self.gPidOK
        self.gAlmCurePaused = self.gSlotTimersPaused

        bits = [self.gAlmEStop, self.gAlmBl1Ol, self.gAlmBl2Ol, self.gAlmHtrOl,
                self.gAlmHighLimit, self.gAlmPidFault, self.gAlmHeatUp,
                self.gAlmDoorChatter, self.gAlmDoorNotClosed, self.gAlmK1Fault,
                self.gAlmK2Fault, self.gAlmK3Fault, self.gAlmLotMismatch,
                self.gAlmCurePaused, False, False]
        self.gAnyAlarm = False
        self.gAlarmNew = False
        for i, b in enumerate(bits):
            if b:
                self.gAnyAlarm = True
                if not self.gAlmMem[i]:
                    self.gAlarmNew = True
            self.gAlmMem[i] = b
        self.gAlmBits = bits

        if self.gAlarmNew:
            self.gAlarmUnack = True
        if self.gAlarmAcceptPulse or not self.gAnyAlarm:
            self.gAlarmUnack = False
        self.gHooter = self.gAlarmUnack
        self.Y11 = self.gHooter

    def _p07(self, sm413):
        self.gSlotState = [0] * 7
        for k in range(1, 7):
            self.gSlotState[k] = (2 if self.gSlotComplete[k]
                                  else (1 if self.gSlotRunning[k] else 0))
        self.Y3 = self.gLampTest or self.gBl1Out
        self.Y4 = self.gLampTest or self.gBl2Out
        self.Y5 = self.gLampTest or self.gHtrOut
        self.Y6 = (self.gLampTest
                   or ((not self.gDoorClosed) and not self.gDoorAlarm)
                   or (self.gDoorAlarm and sm413))
        self.Y7 = (self.gLampTest
                   or (self.gAlarmUnack and sm413)
                   or (self.gAnyAlarm and not self.gAlarmUnack))
        self.Y10 = self.gLampTest or self.gAnySlotRunning

        if self.gTick1s:
            if self.gHtrOut:
                self.gTotHtrRunS += 1
            if self.gBl1Out:
                self.gTotBl1RunS += 1
            if self.gBl2Out:
                self.gTotBl2RunS += 1

    # ------------------------------------------------------------- test helpers
    def press(self, name, scans=3):
        setattr(self, name, True)
        for _ in range(scans):
            self.step()
        setattr(self, name, False)
        self.step()

    def hmi(self, name):
        setattr(self, name, True)
        self.step()

    def login(self, role, code=None):
        """role: 'maint' or 'quality'. Passcode and request in one touch."""
        self.gHmiPasscodeEntry = code if code is not None else (
            self.gSetMaintCode if role == "maint" else self.gSetQualityCode)
        if role == "maint":
            self.gHmiMaintLoginReq = True
        else:
            self.gHmiQualityLoginReq = True
        self.step()
