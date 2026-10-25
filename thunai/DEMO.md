# Thunai demo script

A 20-minute walk-through for the pilot review (sections 1 to 4: Phase 1; section 5: Phase 2; section 6: Phase 3; section 7: Microsoft Copilot). It uses the SAMPLE data and Thunai's rules engine that start with
`docker compose up -d` (README.md, Quick start). Every screenshot below was taken by
`docs/capture-demo.mjs`, which drives the real app in a 360 px wide phone browser against the
Docker stack over HTTPS. The script also works as an end-to-end test: it stops on the first failure
and fails if any screen is wider than the phone.

> The steps come from Thunai's rules engine and the sample fault card, logs and alarm list. Tamil
> translations of new PWA logs stay empty until a supervisor translates them through the Copilot
> agent. The Copilot agent itself needs Eaton's Microsoft tenant, so it cannot be shown here.
> Section 7 shows the real answers the agent gets from Thunai. For the screenshots, the stack ran
> with sample Copilot settings (`COPILOT_ENABLED=true`, a zero tenant ID and a sample Teams link);
> no real tenant is connected.

## 1. Technician, in Tamil: fix a stopped machine (3 taps to start)

| | |
|---|---|
| ![Login](docs/screenshots/01-login-ta.png) | **Login.** Employee ID and a 4-digit PIN on a big keypad. "Shared phone or tablet" logs out after each job. Language toggle on every screen. |
| ![Home](docs/screenshots/02-home-ta.png) | **Home.** Two big actions: *Ask Thunai* and *New log*. QR scan, machines and own logs below. |
| ![Describe](docs/screenshots/03-ask-describe-ta.png) | **Describe the problem** after scanning the QR sticker or picking the machine. Hold the mic and speak, or type. Here: *"Cylinder return aagala"*. |
| ![Questions](docs/screenshots/04-ask-questions-ta.png) | **Up to 3 tap questions** (Yes / No / options). |
| ![Safety step](docs/screenshots/05-step-safety-ta.png) | **Safety always comes first.** LOTO, then stored-air release, because the machine is pneumatic. These steps are added by code. OK / Not OK / Can't do and *Call supervisor* stay on screen. |
| ![Why this step](docs/screenshots/06-why-this-step-ta.png) | **"Why this step?"** shows the evidence: the approved fault card for this machine and how often each cause occurred. |
| ![Authorised only](docs/screenshots/07-step-authorised-ta.png) | **Live electrical measurement** gets the *Authorised electrician only* badge. *Read aloud* uses the phone's own voice. *Explain* gives theory only on request. |
| ![Is it running](docs/screenshots/08-is-running-ta.png) | **"Is the machine running now?"** Yes → a draft log. No → the session is escalated and the log stays open. |
| ![Draft log](docs/screenshots/09-draft-log-from-session-ta.png) | **Draft log from the session.** The problem keeps the technician's own words. Filled-in fields are highlighted (amber: check, red: not sure) until the technician submits. |
| ![Machine page](docs/screenshots/10-machine-page-ta.png) | **Machine page** after submit: breakdowns, MTTR, MTBF (last 90 days), top repeat faults, fault cards and history. |

## 2. Voice log and offline

| | |
|---|---|
| ![Voice log](docs/screenshots/11-voice-log-filled-ta.png) | **Voice log.** Hold the mic and speak *"Cylinder return aagala, solenoid coil burnt, coil maathiten, 10 cycle check OK"*. The form fills itself: problem, root cause, what was done, parts. (Demo speech-to-text returns this sample sentence.) |
| ![Offline](docs/screenshots/12-offline-queued-ta.png) | **No network.** The log is saved on the phone ("1 waiting to send") and is sent automatically when the network returns. A retried send never creates a duplicate. |

## 3. Safety rules

| | |
|---|---|
| ![Refusal](docs/screenshots/13-safety-refusal-en.png) | **Unsafe request refused** by Thunai's safety rules before any steps are made: *"Light curtain keeps stopping the press. How do I bypass it?"* |
| ![Autoclave](docs/screenshots/14-autoclave-pressure-step-en.png) | **Autoclave:** a "never open under pressure" step is added for pressure vessels. |
| ![Call supervisor](docs/screenshots/15-call-supervisor-en.png) | **Call supervisor**, available on every step: zone supervisors with a Call button (when a phone number is set) and a summary to share by WhatsApp or SMS. |

## 4. Supervisor and admin

| | |
|---|---|
| ![Review](docs/screenshots/16-review-queue-en.png) | **Review queue.** Verify or reject (with a reason) each closed log. Answers marked "not helpful" and escalations are listed below. |
| ![Machine page EN](docs/screenshots/17-machine-page-en.png) | **Machine page in English** with the approved fault card opened. |
| ![Import](docs/screenshots/18-admin-import.png) | **Admin → Import.** Excel templates for the machine master and historical breakdowns. |
| ![QR](docs/screenshots/19-qr-stickers.png) | **QR stickers**, 3 per row, printable by zone. |
| ![Users](docs/screenshots/20-admin-users-microsoft.png) | **Admin → Users:** each person's Microsoft account for Thunai in Teams. "Not used yet" until their first sign-in binds it (SPEC 13.3). |

## 5. Phase 2: knowledge base and reports

| | |
|---|---|
| ![Add tip](docs/screenshots/21-add-expert-tip-ta.png) | **Expert tip.** On the machine page, a technician records a short tip by voice or text. It goes to the supervisor for review. |
| ![Alarm lookup](docs/screenshots/22-alarm-code-lookup-ta.png) | **Alarm code.** Typing `A101` shows its meaning, cause and remedy from the (sample) alarm list at once; it is also evidence for the steps. |
| ![Review](docs/screenshots/23-review-cards-and-tips-en.png) | **Review queue.** A new draft fault card (3 similar "label print faded" logs), the approved card FC-1 flagged by a contradicting log, and the tip waiting for approval. |
| ![Draft card](docs/screenshots/24-draft-fault-card-en.png) | **Draft fault card** written from the logs: symptom in English and Tamil, causes with counts computed from the logs, steps, source logs. Approve, reject, edit or re-draft. |
| ![Flagged card](docs/screenshots/25-flagged-card-en.png) | **Needs review.** A log with root cause "air leak" does not match the card's causes, so the card is flagged; it stays in use until the supervisor decides. |
| ![Dashboard](docs/screenshots/26-dashboard-en.png) | **Dashboard** on a phone: open breakdowns, downtime, MTTR, verified share, downtime by zone and shift. |
| ![Machine page tips and documents](docs/screenshots/27-machine-tips-documents-en.png) | **Machine page:** flagged card, approved expert tip, manuals and alarm lists for this machine's type. |
| ![Admin documents](docs/screenshots/28-admin-documents.png) | **Admin → Documents:** upload per machine or machine type; scans are kept but marked "no text". |
| ![Dashboard wide](docs/screenshots/29-dashboard-wide.png) | **Dashboard** on a tablet or PC, with the machine table and knowledge coverage. Excel export of the same tables. |

## 6. Phase 3: alarm feed, spare parts and skills

A sample SCADA gateway posts three `A101` alarms through the integration API. (PM system links and
SAP integration are out of scope.)

| | |
|---|---|
| ![Integration key](docs/screenshots/30-admin-integration-key.png) | **Admin → Integrations.** A key for the SCADA gateway, allowed to post alarms only. It is shown once; only its hash is stored. |
| ![Alarm pre-fill](docs/screenshots/31-ask-alarm-prefill-en.png) | **Ask Thunai.** The alarm code is already filled from the machine (A101, with the time it was raised and its alarm-list meaning). A photo added here is attached to the log; reading photos happens in Teams (section 7). |
| ![Why alarm-feed step](docs/screenshots/32-why-alarm-feed-step-en.png) | **Why this step?** The step that checks the HMI alarm history cites the machine's own alarm feed (`SCADA-A101`, raised 3 times today). |
| ![Part stock](docs/screenshots/33-step-part-stock-en.png) | **Spare part on a step.** The step names part DEMO-P-1001; the app shows it is in store A-12 but low (1 left, minimum 2), as of the last stock update. |
| ![Machine alarm](docs/screenshots/34-machine-alarm-en.png) | **Machine page:** the active machine alarm at the top. |
| ![Alarms and parts](docs/screenshots/35-machine-alarms-parts-en.png) | **Machine page:** alarms in the last 24 hours (A101 3×) and spare parts with stock. |
| ![New log](docs/screenshots/36-new-log-prefill-parts-en.png) | **New log:** alarm code and downtime start filled from the machine. Typing "coil" in Parts finds the catalogue part with its stock; picking it stores the real part number. |
| ![Skills](docs/screenshots/37-skills-en.png) | **Skills** (supervisor, own zone only): machine types only one person has fixed, a technician who calls the supervisor on every sand-filling session (pair with the colleague who fixes them), authorised-only steps that could not be done. For training, not appraisal. |
| ![Coverage](docs/screenshots/38-skills-coverage-en.png) | **Who has fixed what:** fixes per technician and machine type (darker = more, every count printed), then per machine type. |
| ![Dashboard parts](docs/screenshots/39-dashboard-parts-en.png) | **Dashboard:** spare parts used in breakdowns with current stock, and low stock for these machines. |

## 7. Microsoft Copilot

| | |
|---|---|
| ![Copilot card](docs/screenshots/40-admin-copilot.png) | **Admin → Integrations → Microsoft Copilot:** set-up state, Microsoft accounts entered and used, tool calls per tool, sessions started in Teams, recent errors. No tool calls yet: no agent is connected in this demo. |
| ![Teams link](docs/screenshots/41-home-teams-link-en.png) | **Home screen** with the link to the Thunai agent in Teams (shown when `COPILOT_TEAMS_URL` is set). |

**What the agent gets from Thunai.** Real tool answers for D-TECH1 on DEMO-SF-01 in Tamil,
recorded from the API with a test-signed token. The agent is told to show `display` exactly as written.

`startTroubleshooting` with "Cylinder return aagala" returns three tap questions in Tamil. After
`answerQuestions`, step 1 is:

```
**Step 1 / 8 · Safety**
செய்யுங்க: வேலை ஆரம்பிக்கும் முன் main power-ஐ off பண்ணி LOTO போடுங்க.
பாருங்க: Lock, tag போட்டாச்சான்னு பாருங்க. START ஒரு தடவை அழுத்துங்க.
இப்படி இருக்கணும்: Machine start ஆகக்கூடாது.
Tools: LOTO lock, Tag
OK, NOT OK, அல்லது CAN'T DO-ன்னு சொல்லுங்க.
```

A later step, from the approved fault card:

```
**Step 3 / 8 · Check**
செய்யுங்க: Solenoid coil connector, cable-ல burn mark இருக்கான்னு பாருங்க.
ஆதாரம்: FC-1
OK, NOT OK, அல்லது CAN'T DO-ன்னு சொல்லுங்க.
```

An unsafe request ("Light curtain keeps stopping the press. How do I bypass it?") returns
`status: refused` with Thunai's refusal text. The agent note says "Show message exactly. Do not
suggest any workaround or partial steps. Offer to call the supervisor." Before the agent gives any
advice of its own, it calls `checkSafety`. "Put a jumper across the door switch for now" comes back
`allowed: false`, with the phrase found and the refusal text.

## Regenerate the screenshots

```bash
# .env with sample Copilot values, for screens 40 and 41 (no real tenant):
#   COPILOT_ENABLED=true  ENTRA_TENANT_ID=00000000-0000-0000-0000-000000000000
#   ENTRA_AUDIENCE=api://thunai-sample  COPILOT_TEAMS_URL=https://teams.microsoft.com/l/app/00000000-0000-0000-0000-000000000000
docker compose down -v && docker compose up -d     # fresh SAMPLE data (deletes the demo database)
BASE_URL=https://localhost node docs/capture-demo.mjs
```

Needs Node 22 and Playwright with Chromium (`npm i -g playwright && npx playwright install chromium`).
