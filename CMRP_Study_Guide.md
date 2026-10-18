# CMRP Free Study Guide

**Certified Maintenance & Reliability Professional**, awarded by SMRP (Society for Maintenance & Reliability Professionals).

This is an original study guide organized around the five pillars of the SMRP Body of Knowledge, the same structure most paid CMRP courses follow. It covers key concepts, the formulas you need to know, practice questions with answers, and a list of legitimately free resources.

> **Check exam details on smrp.org.** Third-party sources disagree on the exam format. The most commonly cited figures are about 110 multiple-choice questions (roughly 10 of them unscored pretest items), 4 options each, closed book, about 2.5 hours, delivered by computer-based testing. Confirm the current numbers in SMRP's official candidate handbook before you book.

---

## Contents

1. [Exam strategy](#1-exam-strategy)
2. [Pillar 1: Business & Management](#pillar-1--business--management)
3. [Pillar 2: Manufacturing Process Reliability](#pillar-2--manufacturing-process-reliability)
4. [Pillar 3: Equipment Reliability](#pillar-3--equipment-reliability)
5. [Pillar 4: Organization & Leadership](#pillar-4--organization--leadership)
6. [Pillar 5: Work Management](#pillar-5--work-management)
7. [Formula cheat sheet](#formula-cheat-sheet)
8. [Practice questions (40)](#practice-questions)
9. [Answer key with explanations](#answer-key)
10. [Free resources](#free-resources)
11. [4-week study plan](#4-week-study-plan)

---

## 1. Exam strategy

- **This is an experience exam, not a memorization exam.** Most questions describe a scenario and ask for the *best* answer from SMRP's point of view. When two answers look right, choose the one that is proactive, data-driven, root-cause-focused, and aligned with business goals.
- **Know the SMRP metric definitions exactly.** For example, SMRP's "schedule compliance" and "wrench time" have specific numerators and denominators. Questions often test which variant is correct.
- **Typical SMRP view on common traps:**
  - Reactive work is never "best practice", but run-to-failure *is* a valid strategy when chosen deliberately for low-consequence assets.
  - More PM is not automatically better. PMs that don't address a real failure mode add cost and can introduce defects (infant mortality after intrusive work).
  - Planners plan *future* work. They shouldn't be pulled into today's breakdowns.
  - Fix the system, not the person. RCA looks for latent, organizational causes as well as physical ones.
- **Time management:** about 80 seconds per question. Flag hard ones and come back.

---

## Pillar 1 — Business & Management

**Goal:** Connect maintenance and reliability to business results: cost, risk, compliance, and strategy.

### Key concepts

| Topic | What to know |
|---|---|
| **Strategic alignment** | M&R goals are derived from business goals (throughput, cost, safety, compliance). Use a cascade: corporate goals → site goals → M&R KPIs → team targets. |
| **Leading vs. lagging indicators** | *Leading* indicators predict results (PM compliance, schedule compliance, % planned work, backlog). *Lagging* indicators report outcomes (availability, maintenance cost, MTBF, OEE). Manage leading ones to move lagging ones. |
| **Benchmarking** | Compare against best-in-class using *standardized* metric definitions (SMRP metrics) so the comparison is valid. |
| **Life Cycle Cost (LCC)** | Total cost of ownership = acquisition + installation + operation + maintenance + downtime + disposal. Purchase price is often only 10–20% of LCC. Most LCC is locked in at the design and specification stage. |
| **Asset management (ISO 55000)** | A coordinated activity to realize value from assets, balancing cost, risk, and performance across the asset lifecycle. Key documents: Asset Management Policy, Strategic Asset Management Plan (SAMP), and Asset Management Plans. |
| **Risk** | Risk = Probability (likelihood) × Consequence. Use a risk matrix to rank assets for criticality analysis. |
| **Financial tools** | Net present value (NPV), return on investment (ROI), payback period, internal rate of return (IRR). These are used to justify reliability projects. |
| **Maintenance cost as % of RAV** | Total maintenance cost ÷ Replacement Asset Value. World-class is often quoted as about 2–3%. Higher values usually mean reactive maintenance or an aging asset base. |
| **Regulatory and compliance** | OSHA (lockout/tagout, PSM), EPA, ISO 9001/14001/45001. Compliance work is non-negotiable and is scheduled first. |
| **Business case** | State the problem, cost of inaction, options, costs/benefits, risk, and recommendation. Speak the language of finance. |

### Must-know points
- The reliability program's value is shown by **reduced total cost and risk**, not by maintenance spend alone. Cutting the maintenance budget can increase total cost.
- **Capital vs. expense:** replacing or extending an asset's life is typically capital (CapEx). Restoring it to its original condition is maintenance expense (OpEx).
- **Sustainability** links to M&R through energy efficiency (for example, compressed air leaks, steam traps, and motor efficiency) and avoiding environmental releases.

---

## Pillar 2 — Manufacturing Process Reliability

**Goal:** Make the *process* (not just individual machines) deliver consistent quality and throughput.

### Key concepts

| Topic | What to know |
|---|---|
| **OEE (Overall Equipment Effectiveness)** | OEE = Availability × Performance × Quality. World-class is often quoted as about 85%. |
| **Six Big Losses** | Availability: (1) breakdowns, (2) setup/changeover. Performance: (3) minor stops/idling, (4) reduced speed. Quality: (5) process defects/scrap, (6) startup/yield losses. |
| **TEEP** | Total Effective Equipment Performance = OEE × Utilization (uses calendar time, not scheduled time). |
| **Bottleneck / constraint** | Theory of Constraints: the system's throughput equals its constraint's throughput. An hour lost at the bottleneck is an hour lost for the whole plant. Prioritize reliability effort there. |
| **Process capability** | Cp and Cpk compare process spread with specification limits. Cpk ≥ 1.33 is a common target. |
| **Statistical Process Control (SPC)** | Control charts separate common-cause (inherent) variation from special-cause (assignable) variation. Only special causes call for an immediate investigation. |
| **Lean / Six Sigma** | Lean removes waste (8 wastes: DOWNTIME — Defects, Overproduction, Waiting, Non-utilized talent, Transportation, Inventory, Motion, Extra-processing). Six Sigma reduces variation (DMAIC: Define, Measure, Analyze, Improve, Control). |
| **Management of Change (MOC)** | Any change to process, equipment, or procedures is reviewed for hazards before it's made. Required under OSHA PSM for covered processes. |
| **Operator-driven reliability (ODR)** | Operators do basic care: Clean, Inspect, Lubricate, Tighten (CILT), and report abnormalities early. This is the "autonomous maintenance" pillar of TPM. |
| **TPM (Total Productive Maintenance)** | Commonly described with 8 pillars: Autonomous Maintenance, Planned Maintenance, Focused Improvement, Quality Maintenance, Early Equipment Management, Training & Education, Safety/Health/Environment, Office TPM. Foundation: 5S. |
| **5S** | Sort, Set in order, Shine, Standardize, Sustain. |

### Must-know points
- Process reliability problems often come from **operating outside the design window** (overloading, wrong speeds, poor startups). Equipment fixes alone won't solve them.
- **Startup and shutdown** are the highest-risk periods for both safety and equipment damage.
- Use **standard operating procedures** and operator training to reduce variation.

---

## Pillar 3 — Equipment Reliability

**Goal:** Choose the right maintenance strategy for each failure mode so equipment performs its function reliably at the lowest total cost.

### Reliability fundamentals

| Term | Meaning |
|---|---|
| **Reliability R(t)** | Probability that an item performs its function for a stated period under stated conditions. For constant failure rate: R(t) = e^(−λt). |
| **Failure rate (λ)** | Failures per unit time. λ = 1 / MTBF when the rate is constant. |
| **MTBF** | Mean Time Between Failures (repairable items) = total operating time ÷ number of failures. |
| **MTTF** | Mean Time To Failure (non-repairable items). |
| **MTTR** | Mean Time To Repair = total repair time ÷ number of repairs. A measure of *maintainability*. |
| **Inherent availability** | Ai = MTBF ÷ (MTBF + MTTR). Only counts corrective repair time. |
| **Operational availability** | Ao = Uptime ÷ (Uptime + Downtime). Includes all downtime: logistics, waiting for parts, PM, and so on. |
| **Series system** | R_system = R1 × R2 × … × Rn. The system is weaker than its weakest component. |
| **Parallel (redundant) system** | R_system = 1 − (1 − R1)(1 − R2)…(1 − Rn). |

### The six failure patterns (Nowlan & Heap, 1978)

| Pattern | Shape | Share of components (airline study) |
|---|---|---|
| A | Bathtub: infant mortality, then constant, then wear-out | ~4% |
| B | Constant, then wear-out | ~2% |
| C | Slowly increasing (fatigue) | ~5% |
| D | Low at first, then rises to constant | ~7% |
| E | Random (constant) throughout | ~14% |
| F | Infant mortality, then constant | ~68% |

**Exam takeaway:** only about 11% of items (A, B, C) show age-related wear-out. For the other ~89%, **time-based overhaul doesn't help** and can even make things worse by causing infant mortality. That's why condition monitoring is so important.

### Weibull analysis
- Shape parameter **β (beta)** tells you the failure pattern:
  - β < 1 → infant mortality (decreasing failure rate). Look at installation, startup, quality, or burn-in. Time-based replacement makes this *worse*.
  - β ≈ 1 → random failures (constant rate). Use condition monitoring or run-to-failure. Time-based PM doesn't help.
  - β > 1 → wear-out (increasing rate). Time-based replacement or restoration can work. β > 3–4 suggests rapid wear-out.
- Scale parameter **η (eta)** is the characteristic life: the time by which 63.2% of the population has failed.

### The P-F curve
- **P** = point where a potential failure becomes *detectable*. **F** = functional failure.
- **P-F interval** = warning time between P and F.
- **Rule:** inspect at an interval *shorter* than the P-F interval. Common guidance is P-F ÷ 2 so you get at least one detection opportunity with time to plan.
- Detection order along the curve (earliest → latest): ultrasound/oil analysis (very early) → vibration → thermography → audible noise → hot to touch → smoke → failure.

### Maintenance strategies

| Strategy | When it fits |
|---|---|
| **Reactive / run-to-failure (RTF)** | Low-consequence, cheap, non-critical items, chosen *deliberately*. |
| **Preventive (time- or usage-based, PM)** | Clear age-related wear-out (β > 1) and the restoration task actually resets condition. |
| **Predictive / condition-based (PdM/CBM)** | A detectable P-F interval exists and is long enough to act on. Most common best-fit for random failures. |
| **Proactive / precision maintenance** | Eliminate the root causes of failure: precision alignment, balancing, lubrication contamination control, correct installation. |
| **Redesign** | No effective task exists and the consequence is unacceptable (especially for safety or environmental risk). |

### Condition monitoring technologies

| Technology | Detects |
|---|---|
| **Vibration analysis** | Imbalance (1× running speed, radial), misalignment (1× and 2×, high axial), looseness (many harmonics), bearing defects (non-synchronous frequencies BPFO, BPFI, BSF, FTF), gear mesh problems. |
| **Infrared thermography** | Hot electrical connections, overloaded circuits, insulation breakdown, bearing heat, refractory loss, steam traps. |
| **Oil analysis** | Wear metals (ferrography, spectroscopy), contamination (particle count, ISO 4406 code, water by Karl Fischer), oil degradation (viscosity, acid number). |
| **Ultrasound (airborne/structure-borne)** | Compressed air and gas leaks, early bearing lubrication problems, electrical arcing/corona, valve and steam trap leakage. |
| **Motor circuit analysis / current signature** | Rotor bar faults, winding faults, insulation issues. |
| **Non-destructive testing (NDT)** | Ultrasonic thickness (corrosion), radiography, dye penetrant, magnetic particle, eddy current (cracks). |

### RCM (Reliability-Centered Maintenance) — the 7 questions (SAE JA1011)
1. What are the **functions** and associated performance standards of the asset in its present operating context?
2. In what ways can it fail to fulfill its functions (**functional failures**)?
3. What causes each functional failure (**failure modes**)?
4. What happens when each failure occurs (**failure effects**)?
5. In what way does each failure matter (**failure consequences**: hidden, safety/environmental, operational, non-operational)?
6. What should be done to predict or prevent each failure (**proactive tasks** and intervals)?
7. What should be done if a suitable proactive task can't be found (**default actions**: failure-finding, redesign, run-to-failure)?

**Hidden failures** (for example, a standby pump or a safety relief valve) aren't evident during normal operation. They need **failure-finding tasks** (functional tests).

### FMEA / FMECA
- For each failure mode, rate **Severity (S)**, **Occurrence (O)**, and **Detection (D)**, typically on 1–10 scales.
- **RPN = S × O × D.** Higher RPN gets priority. Always address high-severity modes even if their RPN is modest.
- FMECA adds **criticality** analysis.

### Root Cause Analysis (RCA)
- **Three levels of cause:** physical (what broke), human (what someone did or didn't do), latent/organizational (the system flaw that allowed it).
- Tools: **5 Whys**, **fishbone/Ishikawa** (6 Ms: Man, Machine, Method, Material, Measurement, Mother Nature/Environment), **fault tree analysis** (top-down, logic gates), **cause-and-effect/logic trees**, **Pareto analysis** (80/20 rule to choose what to analyze).
- **Preserve the evidence** (the 4 Ps: Parts, Position, People, Paper).
- RCA isn't finished until corrective actions are implemented and verified to work.

### Precision maintenance
- **Shaft alignment:** laser alignment is preferred over straight-edge. Correct soft foot first.
- **Balancing:** reduces 1× vibration and bearing loads.
- **Lubrication:** the right lubricant, right amount, right time, right place, right method (the 5 Rs). **Over-greasing** is a common cause of bearing failure. Keep lubricants clean and dry (contamination control, breathers, filtered transfer).
- **Bearing life** (L10, basic rating life) is inversely proportional to load³ for ball bearings. A small load increase from misalignment drastically shortens life.

---

## Pillar 4 — Organization & Leadership

**Goal:** Build the people, roles, skills, and culture that sustain reliability.

### Key concepts

| Topic | What to know |
|---|---|
| **Leadership vs. management** | Leaders set vision, build commitment, and drive change. Managers plan, organize, and control resources. A reliability program needs both. |
| **Change management** | Commonly cited models: Kotter's 8 steps (create urgency, build a coalition, form a vision, communicate, empower, short-term wins, consolidate, anchor in culture) and ADKAR (Awareness, Desire, Knowledge, Ability, Reinforcement). Culture change is slow and needs visible, sustained leadership commitment. |
| **Organizational structure** | Centralized (economies of scale, specialization) vs. decentralized/area-based (ownership, responsiveness) vs. hybrid. Planning and reliability engineering usually work best as separate roles from day-to-day supervision. |
| **Key roles** | *Reliability engineer*: eliminates failures long-term (RCA, FMEA, strategy). *Maintenance engineer*: solves today's equipment problems. *Planner*: prepares future work packages. *Scheduler*: assigns planned work to time slots. *Supervisor*: manages the crew and execution. |
| **Planner ratio** | Commonly quoted as roughly 1 planner per 15–25 craftspeople (about 1:20). |
| **Supervisor span of control** | Commonly about 1 supervisor per 8–15 craftspeople. |
| **Skills and training** | Do a skills gap analysis: required skills vs. current skills. Use a training matrix, qualification and certification, and measure training effectiveness (for example, Kirkpatrick's 4 levels: Reaction, Learning, Behavior, Results). |
| **Communication** | Tailor messages to the audience. Executives want cost, risk, and ROI. Crews want what, why, and how it affects them. |
| **Teamwork and motivation** | Maslow (hierarchy of needs), Herzberg (hygiene factors vs. motivators), McGregor (Theory X vs. Y). Empowerment and recognition sustain change. |
| **Operations–maintenance partnership** | Shared goals and KPIs, joint scheduling meetings, operator care (ODR), and agreed priority definitions. |
| **Contractors** | Use them for peaks, specialist skills, or outages. Manage their safety, quality, and knowledge transfer. |

### Must-know points
- The **#1 success factor** for a reliability program is usually cited as visible, sustained **management commitment**.
- **Workforce succession / knowledge retention:** document procedures, mentor, and capture tribal knowledge before experienced staff retire.

---

## Pillar 5 — Work Management

**Goal:** Do the right work, at the right time, efficiently and safely.

### The work management cycle
1. **Identify** — work requests from operators, inspections, PM/PdM, and condition monitoring.
2. **Prioritize** — use a priority system based on risk (asset criticality × urgency). Avoid "everything is priority 1".
3. **Plan** — scope, steps, craft and hours, parts, tools, permits, safety, and drawings. Build a **job plan** or **work package**.
4. **Schedule** — weekly schedule from ready-to-work backlog, loaded to about 100% of available craft hours. Then a daily schedule.
5. **Execute** — perform the work, following procedures and safety requirements.
6. **Close out and feedback** — record failure codes, actual hours, parts used, and findings. Feed lessons back into the plan library and the CMMS history.
7. **Analyze** — use history to improve strategies, PMs, and plans.

### Planning & scheduling principles (commonly taught; widely associated with Doc Palmer's work)
- Planners work on **future** work, not today's emergencies.
- Organize the planning group **separately** from crews.
- Use a **component-level file/library** so plans improve over time.
- Planners plan; craftspeople and supervisors execute. Estimates are based on a skilled tech's time; plans give the "what", the tech supplies the "how".
- **Schedule from forecasted craft hours** and assign work to fill about 100% of available hours.
- **Schedule compliance** measures how much of the weekly schedule was completed. Track it, but use it to improve, not to blame.

### Key work management metrics

| Metric | Definition / benchmark |
|---|---|
| **Schedule compliance** | Scheduled work hours completed ÷ total scheduled work hours. Targets of ≥ 90% are commonly cited. |
| **Planned work %** | Planned work hours ÷ total maintenance work hours. Best practice is often > 85–90%. |
| **Reactive work %** | Reactive (unplanned) hours ÷ total maintenance hours. Best practice is often < 10–20%. |
| **PM compliance** | PMs completed on time ÷ PMs due. Targets above 90–95% are commonly cited. |
| **Wrench time** | Time spent actually working on equipment ÷ total time available. Typical plants are around 25–35%. Good is about 50–55%. |
| **Backlog** | Total hours of ready and not-ready work ÷ weekly crew capacity. Healthy *ready* backlog is about 2–4 weeks of crew capacity. Too low means the crew is overstaffed or work isn't being identified. Too high means the crew is understaffed or the work doesn't get done. |
| **Emergency work %** | Work that interrupts the schedule. Lower is better. |

### MRO stores and inventory
- **ABC analysis:** classifies parts by annual usage value. A items (~10–20% of items, ~70–80% of value) get tight control. C items get loose control.
- **Critical spares:** stocked based on risk of downtime, not usage frequency. They can be slow-moving or have no usage history at all.
- **EOQ (Economic Order Quantity)** = √(2DS / H). D = annual demand, S = ordering cost per order, H = annual holding cost per unit.
- **Reorder point** = (average daily usage × lead time in days) + safety stock.
- **Stockout rate** — percentage of requests not filled from stock. Target is low (commonly 1–3%).
- **Inventory turns** = annual issues value ÷ average inventory value. MRO turns are naturally low because of critical spares.
- **Kitting:** parts staged per work order by stores. Improves wrench time.
- **Storage best practice:** rotate motor shafts periodically, store bearings flat in original packaging, control humidity, and use FIFO for shelf-life items.

### CMMS / EAM
- The CMMS/EAM is the system of record for asset hierarchy, work orders, PM schedules, history, and inventory.
- **Data quality matters:** a clear asset hierarchy (ISO 14224 is a common reference) and consistent failure codes (problem, cause, remedy) make analysis possible.

### Turnarounds / shutdowns / outages
- Phases: initiation, scope definition, planning, scheduling, execution, close-out.
- **Freeze the scope** at a set date. Late scope additions drive cost and schedule overruns.
- Use **critical path** methods (CPM) for scheduling.

---

## Formula cheat sheet

| Formula | Expression |
|---|---|
| MTBF | Total operating time ÷ number of failures |
| MTTR | Total repair time ÷ number of repairs |
| Failure rate | λ = 1 ÷ MTBF |
| Reliability (constant rate) | R(t) = e^(−t ÷ MTBF) = e^(−λt) |
| Inherent availability | Ai = MTBF ÷ (MTBF + MTTR) |
| Operational availability | Ao = Uptime ÷ (Uptime + Downtime) |
| Series reliability | R = R1 × R2 × … × Rn |
| Parallel reliability | R = 1 − (1 − R1)(1 − R2)…(1 − Rn) |
| OEE | Availability × Performance × Quality |
| OEE Availability | Run time ÷ Planned production time |
| OEE Performance | (Ideal cycle time × Total count) ÷ Run time |
| OEE Quality | Good count ÷ Total count |
| RPN | Severity × Occurrence × Detection |
| Maintenance cost % RAV | Total annual maintenance cost ÷ Replacement asset value × 100 |
| Schedule compliance | Scheduled hours completed ÷ Scheduled hours |
| Wrench time | Hands-on tool time ÷ Total available time |
| Backlog (weeks) | Backlog hours ÷ Weekly available craft hours |
| EOQ | √(2DS ÷ H) |
| Reorder point | Daily usage × Lead time + Safety stock |
| Inventory turns | Annual issues value ÷ Average inventory value |
| Simple payback | Investment ÷ Annual savings |
| ROI | (Gain − Cost) ÷ Cost × 100 |
| NPV | Σ [Cash flow_t ÷ (1 + r)^t] − Initial investment |

**Useful values:** e^(−1) ≈ 0.368, so when t = MTBF, the reliability R ≈ 36.8% (only about 37% of units survive to their MTBF under constant failure rate). Weibull η is the 63.2% failure point.

---

## Practice questions

These are original practice questions written in the scenario style of the exam. Answers and explanations follow.

### Business & Management

**1.** A plant's annual maintenance cost is $4.5M and its replacement asset value is $150M. What is maintenance cost as a percentage of RAV?
A) 1.5%  B) 3.0%  C) 4.5%  D) 33%

**2.** Which of the following is a *leading* indicator?
A) Maintenance cost per unit produced  B) MTBF  C) PM compliance  D) Plant availability

**3.** Most of an asset's life cycle cost is determined during which phase?
A) Operation  B) Maintenance  C) Design and specification  D) Disposal

**4.** A reliability project costs $200,000 and saves $80,000 per year. What is the simple payback period?
A) 0.4 years  B) 2.5 years  C) 4 years  D) 8 years

**5.** When benchmarking against other plants, the most important prerequisite is:
A) Using the same CMMS  B) Using standardized metric definitions  C) Being in the same country  D) Having the same headcount

**6.** ISO 55000 is primarily a standard for:
A) Quality management  B) Asset management  C) Environmental management  D) Vibration analysis

**7.** Risk is best defined as:
A) Probability + Consequence  B) Probability × Consequence  C) Severity × Detection  D) MTBF ÷ MTTR

**8.** Executive leadership asks why the maintenance budget should not be cut by 20%. The best response is to:
A) Explain that technicians are working hard  B) Show the expected impact on total cost, risk, and production output  C) Request more headcount  D) Cite world-class wrench time

### Manufacturing Process Reliability

**9.** A line has availability 90%, performance 95%, and quality 98%. What is OEE (nearest whole %)?
A) 84%  B) 90%  C) 94%  D) 98%

**10.** Reduced speed losses affect which OEE factor?
A) Availability  B) Performance  C) Quality  D) Utilization

**11.** In a process with five sequential steps, the best place to focus reliability improvement for throughput is:
A) The newest machine  B) The step with the highest maintenance cost  C) The constraint (bottleneck)  D) The first step

**12.** A control chart shows a single point well outside the control limits. This most likely indicates:
A) Common-cause variation  B) Special-cause variation  C) A capable process  D) Normal operation

**13.** Which TPM pillar involves operators cleaning, inspecting, and lubricating their equipment?
A) Planned maintenance  B) Focused improvement  C) Autonomous maintenance  D) Early equipment management

**14.** Before a process change is implemented, the hazard review process is called:
A) RCA  B) Management of Change  C) FMEA  D) Kaizen

**15.** Changeover/setup time is which of the Six Big Losses category?
A) Availability loss  B) Performance loss  C) Quality loss  D) Not an OEE loss

**16.** The 5S step in which cleaning the equipment also serves as an inspection is:
A) Sort  B) Set in order  C) Shine  D) Sustain

### Equipment Reliability

**17.** A pump runs 8,000 hours and fails 4 times. Total repair time was 40 hours. What is MTBF?
A) 10 hours  B) 200 hours  C) 2,000 hours  D) 8,000 hours

**18.** Using the data in question 17, what is inherent availability (nearest 0.1%)?
A) 98.0%  B) 99.0%  C) 99.5%  D) 99.9%

**19.** Two components, each with reliability 0.90, are in series. System reliability is:
A) 0.99  B) 0.90  C) 0.81  D) 0.45

**20.** Two components, each with reliability 0.90, are in parallel (either can do the job). System reliability is:
A) 0.81  B) 0.90  C) 0.95  D) 0.99

**21.** A Weibull analysis gives β = 0.6. The best response is to:
A) Shorten the PM replacement interval  B) Investigate installation, startup, and quality issues  C) Do nothing—failures are random  D) Extend the overhaul interval and add more overhauls

**22.** The P-F interval of a bearing defect using vibration is 8 weeks. A reasonable inspection interval is:
A) 16 weeks  B) 8 weeks  C) 4 weeks  D) 1 year

**23.** According to the Nowlan & Heap study, the most common failure pattern was:
A) Bathtub curve  B) Wear-out  C) Infant mortality followed by random  D) Steadily increasing

**24.** A standby fire pump that is never run cannot reveal its failure during normal operation. RCM classifies this as a:
A) Operational consequence  B) Hidden failure  C) Non-operational consequence  D) Evident failure

**25.** A failure mode has Severity 9, Occurrence 3, Detection 4. Its RPN is:
A) 16  B) 36  C) 108  D) 9

**26.** High vibration at 1× running speed predominantly in the axial direction most strongly suggests:
A) Imbalance  B) Misalignment  C) Bearing outer race defect  D) Electrical fault

**27.** The best technology for finding a compressed air leak in a noisy plant is:
A) Thermography  B) Oil analysis  C) Airborne ultrasound  D) Motor current analysis

**28.** In RCA, a "latent" root cause is:
A) The physical part that broke  B) The person who made an error  C) A system or organizational weakness that allowed the error  D) The first "why"

**29.** Which of the following is the most common cause of rolling-element bearing failure cited in industry?
A) Manufacturing defects  B) Lubrication problems (wrong amount, type, or contamination)  C) Shaft material  D) Ambient temperature

**30.** No effective proactive task exists for a failure mode with a safety consequence. RCM's default action is:
A) Run to failure  B) Redesign is mandatory  C) Double the PM frequency  D) Accept the risk

### Organization & Leadership

**31.** The single most important factor for a successful reliability transformation is generally considered to be:
A) A new CMMS  B) Sustained management commitment  C) Hiring consultants  D) Buying PdM tools

**32.** A planner is frequently pulled into expediting parts for breakdowns. The main consequence is:
A) Better breakdown response  B) Less future work gets planned, so reactive work increases  C) Higher schedule compliance  D) Lower inventory

**33.** In ADKAR, which comes immediately after Awareness?
A) Ability  B) Knowledge  C) Desire  D) Reinforcement

**34.** The role primarily responsible for eliminating chronic failures through analysis is the:
A) Scheduler  B) Maintenance supervisor  C) Reliability engineer  D) Storeroom attendant

### Work Management

**35.** A crew has 400 available hours per week and a ready backlog of 1,400 hours. Ready backlog is:
A) 2.5 weeks  B) 3.5 weeks  C) 4.5 weeks  D) 14 weeks

**36.** The weekly schedule should be loaded to approximately:
A) 50% of available hours  B) 75%  C) 100%  D) 150%

**37.** 270 of 300 scheduled hours were completed this week. Schedule compliance is:
A) 81%  B) 90%  C) 111%  D) 30%

**38.** A critical spare with no usage in five years should normally be:
A) Scrapped to reduce inventory  B) Kept, because stocking is based on risk of downtime  C) Sold to another plant  D) Moved to an A-class item

**39.** Annual demand is 1,000 units, order cost is $50 per order, and holding cost is $4 per unit per year. EOQ is approximately:
A) 50  B) 112  C) 158  D) 250

**40.** The step in the work management process that most improves future plans is:
A) Prioritization  B) Scheduling  C) Close-out with feedback and history  D) Kitting

---

## Answer key

| # | Ans | Explanation |
|---|---|---|
| 1 | B | 4.5 ÷ 150 = 0.03 = 3.0%. |
| 2 | C | PM compliance predicts future results. The others are outcome (lagging) measures. |
| 3 | C | Most LCC is locked in by design and specification choices. |
| 4 | B | 200,000 ÷ 80,000 = 2.5 years. |
| 5 | B | Comparisons are only valid when metrics are defined the same way (for example, SMRP metrics). |
| 6 | B | ISO 55000/55001/55002 cover asset management. |
| 7 | B | Risk = probability × consequence. |
| 8 | B | Speak in business terms: total cost, risk, and output. |
| 9 | A | 0.90 × 0.95 × 0.98 = 0.8379 ≈ 84%. |
| 10 | B | Speed loss reduces the performance factor. |
| 11 | C | Plant throughput is limited by the constraint. |
| 12 | B | Points outside the control limits signal an assignable (special) cause. |
| 13 | C | Autonomous maintenance = operator basic care. |
| 14 | B | Management of Change (MOC). |
| 15 | A | Setup/changeover is downtime → availability loss. |
| 16 | C | Shine = cleaning, which doubles as inspection. |
| 17 | C | 8,000 ÷ 4 = 2,000 hours. |
| 18 | C | MTTR = 40 ÷ 4 = 10 h. Ai = 2,000 ÷ 2,010 = 99.5%. |
| 19 | C | 0.9 × 0.9 = 0.81. |
| 20 | D | 1 − (0.1 × 0.1) = 0.99. |
| 21 | B | β < 1 = infant mortality. Time-based replacement would introduce more early failures. |
| 22 | C | Inspect at about half the P-F interval: 8 ÷ 2 = 4 weeks. |
| 23 | C | Pattern F (infant mortality, then random) was about 68%. |
| 24 | B | Failures not evident during normal operation are hidden failures. They need failure-finding tasks. |
| 25 | C | 9 × 3 × 4 = 108. |
| 26 | B | High axial vibration at 1× (often with 2×) is the classic sign of misalignment. |
| 27 | C | Ultrasound detects the high-frequency turbulence of leaks even in noisy areas. |
| 28 | C | Latent causes are organizational/system weaknesses. |
| 29 | B | Lubrication issues are widely cited as the leading cause of bearing failures. |
| 30 | B | For safety/environmental consequences with no effective task, redesign is compulsory. |
| 31 | B | Visible, sustained leadership commitment. |
| 32 | B | Planners doing reactive work means future work goes unplanned, which feeds the reactive cycle. |
| 33 | C | ADKAR: Awareness → Desire → Knowledge → Ability → Reinforcement. |
| 34 | C | Reliability engineers focus on long-term failure elimination. |
| 35 | B | 1,400 ÷ 400 = 3.5 weeks (in the healthy 2–4 week range). |
| 36 | C | Load to about 100% of forecast available hours. |
| 37 | B | 270 ÷ 300 = 90%. |
| 38 | B | Critical spares are justified by downtime risk, not usage. |
| 39 | C | √(2 × 1,000 × 50 ÷ 4) = √25,000 ≈ 158. |
| 40 | C | Feedback at close-out improves the job plan library and history. |

---

## Free resources

These are legitimate, free sources. I checked that the official links resolve to the publishing organization. Some third-party pages are vendor blogs, so read them with that in mind.

### Official / primary
- **SMRP (Society for Maintenance & Reliability Professionals)** — [smrp.org](https://smrp.org). The official source for the CMRP candidate handbook, exam content outline, and eligibility. The SMRP Body of Knowledge, Best Practices metrics, and other documents are available to members. Membership is paid, but the **metric definitions are the most exam-relevant document you can get**, so it's often worth joining.
- **SMRP Member Exchange — CMRP exam preparation thread** — [exchange.smrp.org](https://exchange.smrp.org/discussion/cmrp-exam-preparation). Members share what helped them pass.

### Free government/public-domain reference documents
- **NASA Reliability-Centered Maintenance Guide for Facilities and Collateral Equipment (2008)** — [nasa.gov PDF](https://www.nasa.gov/wp-content/uploads/2023/06/nasa-rcmguide.pdf) (mirror: [wbdg.org](https://www.wbdg.org/FFC/NASA/NASACRIT/NASA_RCMGuide.pdf)). Excellent free coverage of RCM, failure patterns, PT&I (predictive testing and inspection) technologies, and maintenance strategy. Very relevant to Pillar 3.
- **DOE/FEMP O&M Best Practices Guide, Release 3.0 (PNNL, 2010)** — [energy.gov page](https://www.energy.gov/eere/femp/articles/operations-and-maintenance-best-practices-guide-achieving-operational-efficiency), [OSTI record](https://www.osti.gov/biblio/1220381), [PNNL O&M Best Practices](https://www.pnnl.gov/projects/om-best-practices). Covers O&M program management, metrics, PdM technologies, and equipment-specific best practices.
- **Whole Building Design Guide — O&M and NASA/DOE criteria library** — [wbdg.org](https://www.wbdg.org). Many more free federal O&M references.

### Free articles and overviews
- **UpKeep — How to prepare for the CMRP exam** — [upkeep.com](https://upkeep.com/blog/how-to-prepare-for-the-cmrp-exam/)
- **MaintainX Learning Center — What is CMRP** — [getmaintainx.com](https://webflow.getmaintainx.com/learning-center/what-is-cmrp)
- **Reliability Magazine — CMRP exam advice backed by experts and the SMRP framework** — [reliamag.com](https://reliamag.com/articles/cmrp-exam-advice-backed-by-experts-and-the-smrp-framework/)
- **Spartakus Technologies — How to prepare for the CMRP certification** — [spartakustech.com](https://spartakustech.com/reliability-blog/how-to-prepare-yourself-for-the-cmrp-certification/)
- **Velosi — Quick guide to the CMRP certification process** — [velosiaims.com](https://velosiaims.com/a-quick-guide-to-certified-maintenance-reliability-professional-cmrp-certification-process/)
- **Mometrix — Free CMRP practice test** — [mometrix.com](https://www.mometrix.com/academy/cmrp-practice-test/). Practice questions are free, but the same page describes the credential inaccurately, so verify anything it says about the exam itself.

### Free video
- **YouTube:** search for "CMRP", "SMRP Body of Knowledge", "P-F curve", "Weibull analysis", "RCM 7 questions", and "OEE explained". Many reliability consultancies and CMMS vendors post free explainer videos and webinar recordings.
- **Udemy free previews:** most Udemy courses, including the one you linked, let you watch several lectures free with the **Preview** button on the course page. Udemy also runs frequent sales (often around $10–15) if you decide the full course is worth buying.

### Avoid
- "Free CMRP PDF download" pages on unrelated domains (random university, government, or file-mirror sites). In my search, these were keyword-stuffed spam, sometimes describing the wrong certification entirely, and they're a malware risk.
- Pirated copies of paid courses. Besides the legal and ethical issues, they're often outdated and malware-laden.

---

## 4-week study plan

| Week | Focus | Tasks |
|---|---|---|
| 1 | Pillars 1 & 4 | Read the sections above. Learn the financial formulas and change models. Read SMRP metric definitions for cost and organization metrics. Do questions 1–8 and 31–34. |
| 2 | Pillar 3 (largest technical pillar) | Read the NASA RCM Guide chapters on RCM, failure patterns, and PT&I. Memorize the P-F curve, Weibull β meanings, RCM 7 questions, and condition monitoring technologies. Do questions 17–30. |
| 3 | Pillars 2 & 5 | Practice OEE, inventory, and backlog calculations. Read the DOE O&M guide chapters on O&M management and metrics. Do questions 9–16 and 35–40. |
| 4 | Review & timed practice | Re-do all 40 questions timed (≈80 seconds each). Take a free online practice test. Review every wrong answer and the related SMRP metric definitions. Rest the day before the exam. |

---

*This guide is original study material prepared from general maintenance and reliability engineering knowledge. It isn't affiliated with or endorsed by SMRP or Udemy. Benchmark values ("world-class" figures) are commonly cited industry rules of thumb, not official SMRP thresholds. Always confirm exam details and metric definitions with SMRP's official documents.*
