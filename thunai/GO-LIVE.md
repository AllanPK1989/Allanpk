# Thunai: steps to finish the build and go live

The application is built and tested with SAMPLE data (README, Definition of done). What is left:
- decisions and approvals at Eaton;
- real plant data;
- the Microsoft Copilot set-up in Eaton's tenant;
- tests with real people and machines;
- a pilot, then the roll-out.

Work through the stages in order. Each one ends with a check before you move on.

| Who | Role |
|---|---|
| **Owner** | Maintenance lead who owns Thunai |
| **Dev** | Developer maintaining the code (in-house team) |
| **IT** | Eaton IT: servers, network, Microsoft 365 / Entra / Power Platform |
| **Safety** | Plant safety officer |
| **HR** | Human resources |
| **Sup** | Zone supervisors |

## Stage 0. Decisions and approvals (weeks 1–2)

| # | Decision | Who | Details |
|---|---|---|---|
| 0.1 | Hosting: plant server or Eaton cloud VM; server name and HTTPS certificate | Owner, IT | SPEC question 5, RUNBOOK 1–2 |
| 0.2 | How Microsoft's cloud reaches Thunai: on-premises data gateway (recommended) or a public HTTPS path for `/api/copilot` only | IT | SPEC 13.5 |
| 0.3 | Data location: chat and Teams photos in Microsoft 365, everything else on the plant server | IT | SPEC 13.5 |
| 0.4 | Licences: Microsoft 365 Copilot licences or Copilot Credits for technicians, and the monthly estimate | IT, Microsoft account team | SPEC 13.6 |
| 0.5 | Tamil in Copilot Studio: supported, or Tamil users stay on the PWA | IT | SPEC 13.7 |
| 0.6 | Speech-to-text for PWA voice logs: self-hosted Whisper (audio stays on site) or Sarvam AI (needs approval as an outside service) | Owner, IT | SPEC question 8 |
| 0.7 | KPI formulas and shift timings | Owner | SPEC open questions 1–2 |
| 0.8 | The safety split: what Thunai enforces in code and what the agent is only instructed to do | Safety | SPEC 13.4 |
| 0.9 | How the Skills page may be used | HR | SPEC 12.5 |
| 0.10 | Which SCADA/PLC gateway and stores system to connect, and who owns them on the IT side | Owner, IT | SPEC 12 |
| 0.11 | Pilot zone (10–15 machines), pilot technicians and supervisors, pilot dates | Owner | SPEC question 22 |

**Check:** every item has a written answer. Update the **CONFIRM** items in SPEC.md with the answers.

## Stage 1. Finish the build (weeks 2–4, Dev)

1. **Protect the code.**
   - Make `main` a protected branch: changes only through pull requests with one review.
   - Add a CI workflow (GitHub Actions) that runs on every pull request:
     - `cd backend && pip install -r requirements-dev.txt && pytest -q` on SQLite, and again with a
       PostgreSQL 16 service and `TEST_DATABASE_URL`;
     - `cd frontend && npm ci && npm run build`;
     - the connector check is part of `pytest` (`tests/test_copilot_spec.py`).
2. **Apply the Stage 0 answers.**
   - KPI formulas: `backend/app/kpi.py`.
   - Shift calendar: Admin → Settings.
   - Speech provider: `.env`.
3. **Bulk user import** (recommended; not built yet). The pilot can add users one by one in
   Admin → Users. For the whole plant, add an Excel import for users, like the machine import:
   - employee ID, name, role, zone, language, phone;
   - Microsoft account;
   - a first PIN.
4. **Plant words.**
   - Extend the glossary with plant terms and the way people say them (Admin → Glossary).
   - Add unsafe phrasings heard on the floor, in Tamil and Tanglish, to
     `backend/eval/safety_prompts.json`.
5. **Real evaluation cases.** Write 20 real past breakdowns into `backend/eval/breakdown_cases.json`.
   Use the machine, the technician's words and the cause that was found.
6. **Speech benchmark.** Record 20 real voice logs on the floor. Compare the providers' word error
   rate, and keep the best one that IT approves.
7. **Integrations** (if chosen in 0.10):
   - SCADA gateway posts alarms with an integration key (RUNBOOK 12.1–12.2);
   - stores stock comes as a daily file or through the API (RUNBOOK 12.3).
8. **Tamil review.** A native speaker reviews the app's Tamil strings (`frontend/src/i18n.ts`) and
   Thunai's own Tamil step texts (`backend/app/safety.py`, `backend/app/ai/rules_provider.py`,
   `backend/app/copilot.py`).
9. **Monitoring.** Add an uptime check on `https://<server>/api/health`, and alert IT if it fails.

**Check:**
- CI is green.
- The evaluation (`python -m eval.run_eval --write`) shows safety refusals at 100% and the correct
  cause in the top 3 for at least 16 of 20 real cases.

## Stage 2. Install the server (IT, 1–2 days)

Follow RUNBOOK sections 1, 2 and 6.
1. Docker host: 2 vCPU, 4 GB RAM, 50 GB disk, plus the Whisper server if used.
2. `.env` from `.env.example`:
   - `ENVIRONMENT=production`;
   - a new `SECRET_KEY` and `POSTGRES_PASSWORD`;
   - `SEED_SAMPLE_DATA=false`;
   - the real `SITE_ADDRESS` and `PUBLIC_BASE_URL`;
   - the certificate from IT (`CADDY_TLS`).
3. Run `docker compose up -d`. Then create the first admin:
   `docker compose exec api python -m app.cli create-admin ...`
4. Backups:
   - copy the nightly backups off the server;
   - **run a restore test once** (RUNBOOK 6).

**Check:**
- Phones on plant Wi-Fi open the site without a certificate warning.
- The restore test works.

## Stage 3. Load the real data (Owner, Sup; 1 week)

Follow RUNBOOK sections 3–5, 11 and 12.
1. **Machine master** (Excel template) for the pilot zone. Print and fix the QR stickers.
2. **Users**, with zone, language, supervisor phone numbers and Microsoft accounts.
3. **Historical breakdowns** (Excel template). Supervisors verify the most useful ones.
4. **Documents:** alarm lists and key manuals per machine type.
5. **Spare-parts stock list.**
6. **First fault cards.** Supervisors review the drafted cards and approve the good ones.

**Check:** for each pilot machine, the machine page shows history, the alarm list and spare parts.

## Stage 4. Connect Microsoft Copilot (IT; about 1 day)

Follow [copilot/SETUP.md](copilot/SETUP.md) step by step:
1. Register the Thunai API and the connector in Entra ID.
2. Set `COPILOT_ENABLED`, `ENTRA_TENANT_ID` and `ENTRA_AUDIENCE`.
3. Generate the connector file for the tenant.
4. Create the custom connector.
5. Create the agent with the instructions in `copilot/agent-instructions.md`. Turn off general
   knowledge and web search.
6. Add all 15 tools with end-user sign-in.
7. Publish to the pilot security group.
8. Set `COPILOT_TEAMS_URL`.

**Check:** Admin → Integrations → Microsoft Copilot shows **Ready**, and a pilot user's `whoAmI`
works in Teams.

## Stage 5. Test before the pilot (1–2 weeks)

| Test | Pass mark | Who |
|---|---|---|
| [copilot/TEST-SCRIPT.md](copilot/TEST-SCRIPT.md) in Teams | Safety **13/13**; all other sections pass | Owner, Safety |
| Evaluation with 20 real cases (Stage 1.5) | ≥ 80% correct cause in top 3; safety 100% | Dev |
| Native Tamil review of 30 answers (Teams and PWA) | No wrong or unsafe wording | Tamil-speaking engineer |
| Two technicians rate Tamil step readability | No "hard" items | Sup |
| Field test on a low-end Android phone: gloves, noise, poor Wi-Fi, offline log that syncs later | Works | Sup |
| Voice log benchmark (Stage 1.6) | Agreed error rate | Owner |

**Sign-offs before the pilot:**
- Safety: the safety split and the test script.
- IT: security, network and data location.
- HR: the Skills page.

Record all results in EVAL.md.

## Stage 6. Pilot (4–6 weeks, one zone)

1. **Training (30 minutes each):**
   - technicians: Teams agent, PWA, voice log, offline log, Call supervisor;
   - supervisors: review queue, fault cards, tips, translations through the agent, Skills page;
   - admins: RUNBOOK sections 3–6 and 13.
2. **Daily:**
   - Sup works through the review queue;
   - Owner checks Admin → Integrations for errors.
3. **Weekly:**
   - read a sample of agent conversations (Copilot Studio → Analytics);
   - hold a 30-minute review: fixes, unsafe or wrong answers, adoption.
4. **Measure:**
   - sessions and logs per shift;
   - share of logs verified;
   - MTTR before and after;
   - "not helpful" rate and escalations;
   - Copilot Credits used.
   - **Any unsafe answer stops the pilot** until it is fixed and the test script passes again.
5. **Go / no-go at the end:**
   - no safety incidents;
   - technicians use it on most breakdowns;
   - supervisors keep up with reviews;
   - cost within the estimate.

## Stage 7. Roll out to the plant

1. Zone by zone, for each zone:
   - load the machines, QR stickers and users;
   - add the zone's people to the agent's security group;
   - train them.
2. Give each new zone two weeks of close support.
3. **Hand over:**
   - name the owners for RUNBOOK tasks, backups, user accounts and the connector secret;
   - put the secret's expiry date in the IT calendar.

## Stage 8. After go-live (routine)

| When | Task | Where |
|---|---|---|
| Daily | Review queue; Copilot errors | PWA Review; Admin → Integrations |
| Daily | Backups copied off the server | RUNBOOK 6 |
| Weekly | Sample agent conversations; flagged fault cards | Copilot Studio Analytics; Review |
| Monthly | Run copilot/TEST-SCRIPT.md; restore test; update stock and alarm lists | copilot/, RUNBOOK |
| On every change | CI green; evaluation at 100% safety; test script again if the agent or tools changed | Stage 1, RUNBOOK 13.4 |
| Before expiry | Renew the connector's client secret | copilot/SETUP.md step 2 |
