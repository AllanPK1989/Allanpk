# Forms build script — every question, ready to copy

**Generated from the master data. Copy the text; do not retype it.**

Microsoft Forms has no import, so somebody types these five forms by hand. This is that typing reduced to copy-and-paste, and it is generated from `Checklist_Master`, `Technician_Master` and `Spare_Master` so the wording on the phone matches the wording in the lists exactly.

> **Why that matters most for the acceptance standards.** The standard is the limit the technician judges the machine against. Retyped by hand, "≤ 0.05 mm" becomes "< 0.5 mm" on one line out of fifty-one, and a machine passes against a number ten times too loose. Nothing catches it.

**Total: 140 questions across five forms** — 102 of them on the checklist.

## Before you start

Read `FLOW_SPECS.md` §"The five forms" first — it explains *why* the first questions are ordered the way they are. The short version, and the rule that will catch you out:

> **A pre-filled link fills answers by POSITION, not by name.** `Machine ID` is always question 1, `Cell ID` always question 2, and on the checklist `Checklist ID` is always question 3. Insert anything above them and every sticker on the shop floor starts filling the wrong boxes, silently. New questions go at the bottom, always.

Settings, identical on all five: **Anyone can respond** on, **Record name** off.

---

# Form 1 — PM Start

**Two questions, both pre-filled from the sticker.** The technician taps Submit and nothing else.

**Q1 · Text · Required**

```
Machine ID
```

**Q2 · Text · Required**

```
Cell ID
```

> No technician question. Nothing stores who *started* a job — `Completed_By` on the checklist is the record that matters — so a dropdown here would be a tap that throws its answer away.

---

# Form 2 — PM Checklist

**4 questions, then one branched section per checklist — 9 sections, 51 check points, 102 questions.** This is the long one.

**Q1 · Text · Required**

```
Machine ID
```

**Q2 · Text · Required**

```
Cell ID
```

**Q3 · Choice · Required**

```
Checklist ID
```

*Choices*, one per line:

```
CL-FEED
CL-FILL
CL-GEN
CL-OVEN
CL-PRESS
CL-TEST
CL-UTIL
CL-VISION
CL-WELD
```

**Q4 · Choice · Required**

```
Technician Name
```

*Choices*, one per line:

```
Murugan S
Karthik R
Dinesh V
Prakash A
Sathish B
Manoj K
```

### Now set the branching on Q3

**… (on Q3) → Add branching.** Point each answer at its own section:

| If Checklist ID is | Go to |
|---|---|
| `CL-FEED` | Section 1 |
| `CL-FILL` | Section 2 |
| `CL-GEN` | Section 3 |
| `CL-OVEN` | Section 4 |
| `CL-PRESS` | Section 5 |
| `CL-TEST` | Section 6 |
| `CL-UTIL` | Section 7 |
| `CL-VISION` | Section 8 |
| `CL-WELD` | Section 9 |

> Build **one form with nine sections**, not nine forms. Pre-fill Q3 from the machine's `Checklist_ID` and the technician never touches it.

Every check point below is **two questions**: the four-option choice, then one optional text box. The four options carry two facts in one tap —

| Answer | `Result` | `Follow_Up_Required` |
|---|---|---|
| OK | `OK` | No |
| NOT OK — fixed on the spot | `NOT OK` | No |
| NOT OK — needs follow-up | `NOT OK` | **Yes** |
| N/A | `NA` | No |

## Section 1 — `CL-FEED`  ·  4 check points  ·  8 questions

*2 need a **measured number**.*

**Item 1**

**Q1a · Choice · Required**

```
Feed roller wear
```

*Subtitle* (paste into the question's description box):

```
Accept: No slip, no groove
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Observation — Feed roller wear
```

**Item 2**

**Q2a · Choice · Required**

```
Servo backlash check
```

*Subtitle* (paste into the question's description box):

```
Accept: < 0.05 mm
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Reading — Servo backlash check
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 3**

**Q3a · Choice · Required**

```
Strip guide alignment
```

*Subtitle* (paste into the question's description box):

```
Accept: Strip centered within 0.5 mm
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Reading — Strip guide alignment
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 4**

**Q4a · Choice · Required**

```
Lubrication unit level
```

*Subtitle* (paste into the question's description box):

```
Accept: Above min mark
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Observation — Lubrication unit level
```


## Section 2 — `CL-FILL`  ·  7 check points  ·  14 questions

*3 need a **measured number**.*

**Item 1**

**Q1a · Choice · Required**

```
Vibrator motor mounting bolts
```

*Subtitle* (paste into the question's description box):

```
Accept: All bolts tight, no crack
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Observation — Vibrator motor mounting bolts
```

**Item 2**

**Q2a · Choice · Required**

```
Sand hopper level sensor
```

*Subtitle* (paste into the question's description box):

```
Accept: Triggers at set level
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Observation — Sand hopper level sensor
```

**Item 3**

**Q3a · Choice · Required**

```
Filling nozzle wear
```

*Subtitle* (paste into the question's description box):

```
Accept: Bore within 0.2 mm of nominal
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Reading — Filling nozzle wear
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 4**

**Q4a · Choice · Required**

```
Compaction cycle time
```

*Subtitle* (paste into the question's description box):

```
Accept: Within +/- 5% of standard
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Reading — Compaction cycle time
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 5**

**Q5a · Choice · Required**

```
Dust extraction suction
```

*Subtitle* (paste into the question's description box):

```
Accept: > 15 m/s at hood
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q5b · Text**

```
Reading — Dust extraction suction
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 6**

**Q6a · Choice · Required**

```
Conveyor belt tracking
```

*Subtitle* (paste into the question's description box):

```
Accept: Centered, no edge rub
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q6b · Text**

```
Observation — Conveyor belt tracking
```

**Item 7**

**Q7a · Choice · Required**

```
PLC battery status
```

*Subtitle* (paste into the question's description box):

```
Accept: No low-battery alarm
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q7b · Text**

```
Observation — PLC battery status
```


## Section 3 — `CL-GEN`  ·  6 check points  ·  12 questions

*1 are **safety-critical** and block the cell from closing.*

**Item 1**

**Q1a · Choice · Required**

```
General cleanliness and 5S
```

*Subtitle* (paste into the question's description box):

```
Accept: No dust, tools in place
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Observation — General cleanliness and 5S
```

**Item 2**

**Q2a · Choice · Required**

```
Fastener tightness check
```

*Subtitle* (paste into the question's description box):

```
Accept: All fasteners tight
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Observation — Fastener tightness check
```

**Item 3  ⚠ SAFETY-CRITICAL**

**Q3a · Choice · Required**

```
Guard and interlock function
```

*Subtitle* (paste into the question's description box):

```
Accept: Machine stops on guard open
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Observation — Guard and interlock function
```

**Item 4**

**Q4a · Choice · Required**

```
Lubrication as per chart
```

*Subtitle* (paste into the question's description box):

```
Accept: All points greased
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Observation — Lubrication as per chart
```

**Item 5**

**Q5a · Choice · Required**

```
Electrical panel inspection
```

*Subtitle* (paste into the question's description box):

```
Accept: No loose wire or heating
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q5b · Text**

```
Observation — Electrical panel inspection
```

**Item 6**

**Q6a · Choice · Required**

```
Abnormal noise / vibration
```

*Subtitle* (paste into the question's description box):

```
Accept: No abnormal sound
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q6b · Text**

```
Observation — Abnormal noise / vibration
```


## Section 4 — `CL-OVEN`  ·  6 check points  ·  12 questions

*2 need a **measured number**; 1 are **safety-critical** and block the cell from closing.*

**Item 1**

**Q1a · Choice · Required**

```
Door gasket condition
```

*Subtitle* (paste into the question's description box):

```
Accept: No cut, seals fully
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Observation — Door gasket condition
```

**Item 2**

**Q2a · Choice · Required**

```
Steam trap operation
```

*Subtitle* (paste into the question's description box):

```
Accept: Discharging, no live steam
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Observation — Steam trap operation
```

**Item 3**

**Q3a · Choice · Required**

```
Temperature sensor calibration
```

*Subtitle* (paste into the question's description box):

```
Accept: Within +/- 2 deg C of master
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Reading — Temperature sensor calibration
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 4  ⚠ SAFETY-CRITICAL**

**Q4a · Choice · Required**

```
Safety relief valve test
```

*Subtitle* (paste into the question's description box):

```
Accept: Lifts at set pressure
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Observation — Safety relief valve test
```

**Item 5**

**Q5a · Choice · Required**

```
Insulation surface temperature
```

*Subtitle* (paste into the question's description box):

```
Accept: < 55 deg C
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q5b · Text**

```
Reading — Insulation surface temperature
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 6**

**Q6a · Choice · Required**

```
Condensate drain line
```

*Subtitle* (paste into the question's description box):

```
Accept: Free flow, no blockage
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q6b · Text**

```
Observation — Condensate drain line
```


## Section 5 — `CL-PRESS`  ·  8 check points  ·  16 questions

*3 need a **measured number**; 2 are **safety-critical** and block the cell from closing.*

**Item 1**

**Q1a · Choice · Required**

```
Slide / ram guideway lubrication
```

*Subtitle* (paste into the question's description box):

```
Accept: Grease film present, no dry patch
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Observation — Slide / ram guideway lubrication
```

**Item 2**

**Q2a · Choice · Required**

```
Clutch & brake air pressure
```

*Subtitle* (paste into the question's description box):

```
Accept: 5.0 - 6.0 bar
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Reading — Clutch & brake air pressure
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 3**

**Q3a · Choice · Required**

```
Die clamping bolt torque
```

*Subtitle* (paste into the question's description box):

```
Accept: As per torque chart
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Reading — Die clamping bolt torque
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 4  ⚠ SAFETY-CRITICAL**

**Q4a · Choice · Required**

```
Safety light curtain function
```

*Subtitle* (paste into the question's description box):

```
Accept: Stops ram within 200 ms
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Observation — Safety light curtain function
```

**Item 5**

**Q5a · Choice · Required**

```
Flywheel bearing temperature
```

*Subtitle* (paste into the question's description box):

```
Accept: < 60 deg C
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q5b · Text**

```
Reading — Flywheel bearing temperature
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 6**

**Q6a · Choice · Required**

```
Oil level in gearbox
```

*Subtitle* (paste into the question's description box):

```
Accept: Between min and max mark
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q6b · Text**

```
Observation — Oil level in gearbox
```

**Item 7**

**Q7a · Choice · Required**

```
Air line FRL water drain
```

*Subtitle* (paste into the question's description box):

```
Accept: Bowl empty, drain free
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q7b · Text**

```
Observation — Air line FRL water drain
```

**Item 8  ⚠ SAFETY-CRITICAL**

**Q8a · Choice · Required**

```
Emergency stop function
```

*Subtitle* (paste into the question's description box):

```
Accept: Machine stops in all modes
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q8b · Text**

```
Observation — Emergency stop function
```


## Section 6 — `CL-TEST`  ·  5 check points  ·  10 questions

*2 need a **measured number**; 1 are **safety-critical** and block the cell from closing.*

**Item 1**

**Q1a · Choice · Required**

```
Calibration validity
```

*Subtitle* (paste into the question's description box):

```
Accept: Within due date
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Observation — Calibration validity
```

**Item 2**

**Q2a · Choice · Required**

```
Test lead / probe condition
```

*Subtitle* (paste into the question's description box):

```
Accept: No fray, firm contact
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Observation — Test lead / probe condition
```

**Item 3**

**Q3a · Choice · Required**

```
Reference standard verification
```

*Subtitle* (paste into the question's description box):

```
Accept: Within stated accuracy
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Reading — Reference standard verification
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 4**

**Q4a · Choice · Required**

```
Earthing of test bench
```

*Subtitle* (paste into the question's description box):

```
Accept: < 1 ohm
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Reading — Earthing of test bench
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 5  ⚠ SAFETY-CRITICAL**

**Q5a · Choice · Required**

```
Interlock and guard function
```

*Subtitle* (paste into the question's description box):

```
Accept: Test inhibited when open
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q5b · Text**

```
Observation — Interlock and guard function
```


## Section 7 — `CL-UTIL`  ·  5 check points  ·  10 questions

*2 need a **measured number**.*

**Item 1**

**Q1a · Choice · Required**

```
Motor current draw
```

*Subtitle* (paste into the question's description box):

```
Accept: Within nameplate FLC
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Reading — Motor current draw
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 2**

**Q2a · Choice · Required**

```
Vibration level at bearing
```

*Subtitle* (paste into the question's description box):

```
Accept: < 4.5 mm/s RMS
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Reading — Vibration level at bearing
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 3**

**Q3a · Choice · Required**

```
Coupling / belt condition
```

*Subtitle* (paste into the question's description box):

```
Accept: No crack, correct tension
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Observation — Coupling / belt condition
```

**Item 4**

**Q4a · Choice · Required**

```
Panel cleanliness and glands
```

*Subtitle* (paste into the question's description box):

```
Accept: No dust ingress, glands sealed
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Observation — Panel cleanliness and glands
```

**Item 5**

**Q5a · Choice · Required**

```
Leak check on all joints
```

*Subtitle* (paste into the question's description box):

```
Accept: No leak
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q5b · Text**

```
Observation — Leak check on all joints
```


## Section 8 — `CL-VISION`  ·  4 check points  ·  8 questions

*1 need a **measured number**.*

**Item 1**

**Q1a · Choice · Required**

```
Camera lens cleanliness
```

*Subtitle* (paste into the question's description box):

```
Accept: No smear or dust
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Observation — Camera lens cleanliness
```

**Item 2**

**Q2a · Choice · Required**

```
Lighting intensity
```

*Subtitle* (paste into the question's description box):

```
Accept: Within recipe tolerance
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Reading — Lighting intensity
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 3**

**Q3a · Choice · Required**

```
Reject gate actuation
```

*Subtitle* (paste into the question's description box):

```
Accept: Rejects within 2 stations
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Observation — Reject gate actuation
```

**Item 4**

**Q4a · Choice · Required**

```
Master sample pass/fail check
```

*Subtitle* (paste into the question's description box):

```
Accept: 100% correct classification
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Observation — Master sample pass/fail check
```


## Section 9 — `CL-WELD`  ·  6 check points  ·  12 questions

*3 need a **measured number**.*

**Item 1**

**Q1a · Choice · Required**

```
Electrode tip dressing condition
```

*Subtitle* (paste into the question's description box):

```
Accept: Flat, no mushrooming
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q1b · Text**

```
Observation — Electrode tip dressing condition
```

**Item 2**

**Q2a · Choice · Required**

```
Weld current calibration
```

*Subtitle* (paste into the question's description box):

```
Accept: Within +/- 3% of set value
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q2b · Text**

```
Reading — Weld current calibration
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 3**

**Q3a · Choice · Required**

```
Cooling water flow rate
```

*Subtitle* (paste into the question's description box):

```
Accept: > 4 LPM
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q3b · Text**

```
Reading — Cooling water flow rate
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```

**Item 4**

**Q4a · Choice · Required**

```
Transformer terminal tightness
```

*Subtitle* (paste into the question's description box):

```
Accept: No discoloration, torque OK
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q4b · Text**

```
Observation — Transformer terminal tightness
```

**Item 5**

**Q5a · Choice · Required**

```
Pneumatic cylinder leak check
```

*Subtitle* (paste into the question's description box):

```
Accept: No audible leak
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q5b · Text**

```
Observation — Pneumatic cylinder leak check
```

**Item 6**

**Q6a · Choice · Required**

```
Earth continuity
```

*Subtitle* (paste into the question's description box):

```
Accept: < 1 ohm
```

*Choices*, one per line:

```
OK
NOT OK — fixed on the spot
NOT OK — needs follow-up
N/A
```

**Q6b · Text**

```
Reading — Earth continuity
```

*Subtitle* (paste into the question's description box):

```
Type the number you measured. Not "ok".
```


### Last question on the form, after every section

**File upload · 1 file · not required**

```
Photo
```

Flow 4 attaches it to the rows marked NOT OK — which is what a photo on a PM checklist is ever of.

---

# Form 3 — Spare Replaced

**9 questions.** Records what was *fitted* — there is no requisition or approval here; the stores process already runs that.

**Q1 · Text · Required**

```
Machine ID
```

**Q2 · Text · Required**

```
Cell ID
```

**Q3 · Choice · Required**

```
Replaced by
```

*Choices*, one per line:

```
Murugan S
Karthik R
Dinesh V
Prakash A
Sathish B
Manoj K
```

**Q4 · Choice · Required**

```
Replaced during
```

*Choices*, one per line:

```
PM
Breakdown
```

**Q5 · Text · Required**

```
Work order or breakdown reference
```

**Q6 · Choice · Required**

```
Spare code
```

*Choices*, one per line:

```
SP-1001 — Proximity Sensor M12 PNP NO
SP-1002 — Pneumatic Cylinder 32x100 DA
SP-1003 — Solenoid Valve 5/2 24VDC
SP-1004 — Deep Groove Ball Bearing 6205
SP-1005 — V-Belt A-42
SP-1006 — Contactor 25A 3P 240V Coil
SP-1007 — PLC Battery CR2032 FX Series
SP-1008 — FRL Unit 1/2 inch
SP-1009 — Thermocouple Type K 3mm
SP-1010 — Steam Trap 1/2 inch Thermodynamic
SP-1011 — Door Gasket Silicone 10m Roll
SP-1012 — Vibration Motor 0.25 kW
SP-1013 — Welding Electrode Tip Cu-Cr
SP-1014 — SMPS 24VDC 5A
SP-1015 — Servo Drive Cooling Fan 24V
```

**Q7 · Number · Required**

```
Quantity used
```

**Q8 · Choice · Required**

```
Failure mode
```

*Choices*, one per line:

```
Wear
Contamination
Fatigue
Overload
Corrosion
Electrical
End of life
Other
```

**Q9 · Choice · Required**

```
Warranty claim
```

*Choices*, one per line:

```
Yes
No
```

> **Question 8 is the one that pays for this form.** Repeated "Contamination" on the same part is a filtration problem, not a spares problem, and no amount of buying more parts will fix it. Keep it mandatory.

---

# Form 4 — Breakdown Report

**14 questions.**

**Q1 · Text · Required**

```
Machine ID
```

**Q2 · Text · Required**

```
Cell ID
```

**Q3 · Choice · Required**

```
Reported by
```

*Choices*, one per line:

```
Murugan S
Karthik R
Dinesh V
Prakash A
Sathish B
Manoj K
```

**Q4 · Choice · Required**

```
Shift
```

*Choices*, one per line:

```
A
B
C
```

**Q5 · Choice · Required**

```
Breakdown type
```

*Choices*, one per line:

```
Electrical
Mechanical
Pneumatic
Hydraulic
Tooling
Other
```

**Q6 · Text · long answer · Required**

```
Symptom — what did it do?
```

**Q7 · Text · long answer**

```
Root cause — what was actually wrong?
```

**Q8 · Text · long answer**

```
Action taken
```

**Q9 · Date**

```
When was it responded to?
```

**Q10 · Date**

```
Repair started
```

**Q11 · Date**

```
Repair finished
```

**Q12 · Number**

```
Production lost, minutes
```

*Subtitle* (paste into the question's description box):

```
The WHOLE time the machine could not run — including waiting for a technician and waiting for a part. Not just the repair.
```

**Q13 · Choice · Required**

```
Status
```

*Choices*, one per line:

```
Open
Under Repair
Closed
```

**Q14 · Choice · Required**

```
Has this happened before on this machine?
```

*Choices*, one per line:

```
Yes
No
```

> Questions 9, 10 and 11 must be **Date and time**, not date only. Response time and MTTR are the gaps between them, worked out by the report — and a gap between two dates with no clock on them is measured in days.

---

# Form 5 — Abnormality Log

**9 questions.**

**Q1 · Text · Required**

```
Machine ID
```

**Q2 · Text · Required**

```
Cell ID
```

**Q3 · Choice · Required**

```
Logged by
```

*Choices*, one per line:

```
Murugan S
Karthik R
Dinesh V
Prakash A
Sathish B
Manoj K
```

**Q4 · Choice · Required**

```
Category
```

*Choices*, one per line:

```
Safety
Quality
Leak
Noise
Vibration
5S / Housekeeping
Other
```

**Q5 · Text · long answer · Required**

```
What did you see?
```

**Q6 · Choice · Required**

```
Severity
```

*Choices*, one per line:

```
High
Medium
Low
```

**Q7 · File upload · 1 file**

```
Photo
```

**Q8 · Choice · Required**

```
Who should fix it?
```

*Choices*, one per line:

```
Maintenance
Production
Quality
Safety
```

**Q9 · Date · Required**

```
Fix by
```

---

# When all five exist

Make a pre-filled link for each (**Collect responses → Get a link to prefill answers**), cut each into its parts, and paste them into the 11 placeholders in `sharepoint/formatting/Machine_Master.MachineHub.view.json`. Then re-run `apply_views.ps1`.

**Test one on a real phone before going further.** There are 8 cells and 30 machines depending on these links being right.
