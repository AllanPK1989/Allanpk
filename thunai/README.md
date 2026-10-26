# Thunai (துணை): breakdown help for maintenance technicians

Thunai helps maintenance technicians at EPQPL Pondicherry fix stopped machines. A technician gets
simple, safe, step-by-step troubleshooting in English or Tamil, then logs the fix. Every log builds the
machine's history and knowledge base. Technicians use Thunai in two ways:
- **Microsoft Teams / Microsoft 365 Copilot:** a Copilot Studio agent that calls Thunai's tools.
- **The Thunai web app (PWA):** for offline logging, supervisors and admins.

**AI runs in Microsoft Copilot.** The conversation runs in the Copilot agent. The Thunai server keeps
the plant data, the safety rules and a rules engine that builds the steps from fault cards, logs and
alarm lists; it calls no outside AI service. See [SPEC.md section 13](SPEC.md) and
[copilot/SETUP.md](copilot/SETUP.md).

**Going live:** follow [GO-LIVE.md](GO-LIVE.md).

Phase 1 (MVP), Phase 2 (knowledge and reports), Phase 3 (alarm feed, spare parts, skills) and the
Copilot connection are built:
see [SPEC.md](SPEC.md) for scope and decisions (Phase 2 in section 11, Phase 3 in section 12, Copilot in section 13),
[PLAN.md](PLAN.md) for the
build order, [EVAL.md](EVAL.md) for test results, [RUNBOOK.md](RUNBOOK.md) for operations and
[DEMO.md](DEMO.md) for a walk-through with screenshots.

> **Sample data only.** Machines starting with `DEMO-`, names starting with `[SAMPLE]` and users
> starting with `D-` are made up for demos. Nothing here is real plant data.

## Quick start (demo)

Needs Docker with Compose v2.24 or newer.

```bash
cd thunai
docker compose up -d
```

Open **https://localhost** (accept the local certificate warning) and log in:

| Employee ID | PIN | Role | Language |
|---|---|---|---|
| `D-TECH1` | 1234 | Technician, Bussmann Zone 1 | Tamil |
| `D-TECH2` | 1234 | Technician, Zone 2 | English |
| `D-SUP1` | 1234 | Supervisor, Bussmann Zone 1 | English |
| `D-TECH3` | 1234 | Technician, Bussmann Zone 1 (sample data for the Skills page) | Tamil |
| `D-ADMIN` | 1234 | Admin | English |

Without a `.env` file the app runs with SAMPLE data, Thunai's rules engine and a demo
speech-to-text that returns a labelled sample transcript. The Copilot connection is off until it is
set up ([copilot/SETUP.md](copilot/SETUP.md)). Going live: follow [RUNBOOK.md](RUNBOOK.md).

## What it does

| Module | Features |
|---|---|
| Machine registry | Excel import (upsert by machine number), QR code per machine, printable sticker sheet, machine page with open issues, history, top 5 repeat faults, fault cards, MTTR and MTBF |
| Thunai in Teams (Copilot) | A Copilot Studio agent in Teams and Microsoft 365 Copilot. It calls 15 Thunai tools: machine status, alarm meaning, step-by-step troubleshooting (Thunai's steps, shown as given), photo readings as evidence, logging in the technician's words with an English version, spare parts, a safety check, supervisor call, and log translation for supervisors. Sign-in with each person's own Microsoft Entra ID account. Usage and errors in Admin → Integrations |
| Ask Thunai (PWA) | Problem by voice or text (English, Tamil, mixed), up to 3 tap questions, one step at a time with OK / Not OK / Can't do, read-aloud, "Why this step?" evidence, Explain, Call supervisor always visible, "Is the machine running?" → draft log or escalation |
| Breakdown logging | Push-to-talk voice log, rules fill issue / root cause / action / parts / downtime, filled fields highlighted until confirmed, one follow-up question when a required field is missing, shift and downtime auto-filled, open-log merge, offline queue that syncs later |
| Knowledge | Each log stored as original + English + Tamil and classified in the background. Logs from Teams arrive with both versions; supervisors translate PWA logs through the agent |
| Supervisor and admin | Review queue (verify / reject, "not helpful" answers, escalations), users, PINs and Microsoft accounts, glossary, settings (shift calendar, thresholds), historical import, Excel export of logs and KPIs, Copilot usage, audit trail |
| Fault cards (Phase 2) | Drafted by the rules engine when 3 or more similar logs exist for a machine or machine type; causes ranked by counts computed from the logs; supervisor edits, approves, rejects, retires or re-drafts; versions kept; a new log with an unknown root cause flags the card for review |
| Dashboard (Phase 2) | Open breakdowns, downtime by zone and shift, MTTR / MTBF by machine, top repeat faults, knowledge coverage, Ask Thunai use; 7 / 30 / 90 days and zone filters; Excel export |
| Expert tips (Phase 2) | Short tips by voice or text, reviewed by supervisors; approved tips show on the machine page and are a source for steps |
| Documents and alarm lists (Phase 2) | Manuals, SOPs, drawings and alarm lists per machine or machine type; PDF text indexed for search; alarm-code meaning shown as soon as it is typed; optional embeddings for similarity search |
| Spare parts (Phase 3) | Stock list from the stores system (Excel, CSV or API); part numbers on steps and fault cards matched exactly to the catalogue with stock and store location; parts picker in the log form; parts tables on the dashboard |
| PLC / SCADA alarms (Phase 3) | Alarm events posted by a gateway or SCADA; the newest active alarm pre-fills the alarm code (and the downtime start in a new log); the last 24 hours of alarms are evidence for the steps |
| Integration API (Phase 3) | Scoped, hashed, revocable integration keys for the alarm feed and the stock list. PM system links and SAP integration are out of scope |
| Photos | In Teams the agent reads photos of gauges, HMI screens or damage and passes the readings to Thunai (checked: no value without legibility, real-looking alarm codes only). An alarm code on the screen fills the alarm field, and the readings are evidence for the steps. In the PWA, photos are attachments |
| Skill-gap analytics (Phase 3) | Who has fixed what by machine type, machine types only one person can fix, rule-based pairing and training suggestions, minimum-event guard; supervisors see their own zone; Excel export |

Safety rules are enforced in code (`backend/app/safety.py`), for the PWA and for the Copilot tools:
- unsafe requests are refused before any steps are made;
- every procedure starts with LOTO, plus stored-air release for pneumatics and a pressure check for
  autoclaves;
- unsafe step text is rejected;
- live electrical measurements get an "Authorised electrician only" badge;
- steps without evidence are labelled "General suggestion";
- the agent checks its own advice with `checkSafety`.

What only the agent's instructions can cover, and how that is tested, is in SPEC 13.4 and
[copilot/TEST-SCRIPT.md](copilot/TEST-SCRIPT.md).

## Layout

```
thunai/
├── SPEC.md  PLAN.md  EVAL.md  RUNBOOK.md  DEMO.md
├── docker-compose.yml  .env.example
├── copilot/                 Copilot Studio package: connector OpenAPI 2.0 file, agent instructions,
│                            setup guide for Eaton IT, test script
├── backend/                 FastAPI + SQLAlchemy + Alembic (Python 3.12)
│   ├── app/                 API, services, safety, retrieval, KPI, jobs, knowledge (fault cards),
│   │                        dashboard, tips, documents, embeddings, parts, alarm_feed,
│   │                        integrations, photos, skills, copilot (tool answers), entra (sign-in),
│   │                        copilot_spec (OpenAPI 2.0 for the connector)
│   │   ├── ai/              provider interface, rules engine, output contracts
│   │   └── stt/             speech-to-text adapters (OpenAI-compatible/Whisper, Sarvam, mock)
│   ├── prompts/             versioned prompts (name.vN.md); never hard-coded
│   ├── alembic/             database migrations
│   ├── tests/               pytest (unit + API)
│   └── eval/                evaluation harness (troubleshooting accuracy, safety refusals)
├── frontend/                React + TypeScript PWA (Vite), Caddyfile for HTTPS
├── ops/backup.sh            nightly pg_dump
└── docs/                    screenshots and the demo/e2e script
```

## Development

Backend (Python 3.12+):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q                       # 141 tests, SQLite; TEST_DATABASE_URL=... for PostgreSQL
DATABASE_URL=sqlite:///./dev.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite:///./dev.db .venv/bin/python -m app.cli init      # SAMPLE data
DATABASE_URL=sqlite:///./dev.db .venv/bin/uvicorn app.main:app --reload
.venv/bin/python -m eval.run_eval         # evaluation harness (safety refusals, rules engine)
.venv/bin/python -m app.cli copilot-spec > ../copilot/thunai-tools.swagger.json   # after changing a Copilot tool
```

API docs: http://localhost:8000/api/docs

Frontend (Node 22):

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173, proxies /api to :8000
npm run build      # type-check and production build
```

The microphone and camera need HTTPS or `localhost`.

End-to-end demo with screenshots (needs Playwright and a running instance with fresh SAMPLE data):
`BASE_URL=https://localhost node docs/capture-demo.mjs`

## Configuration

All settings are environment variables; see `.env.example` for the full list.

| Variable | Default | Purpose |
|---|---|---|
| `AI_PROVIDER` | `rules` | Thunai's rules engine (the only option; SPEC 13) |
| `COPILOT_ENABLED` | `false` | accept calls from the Copilot agent (`/api/copilot`) |
| `ENTRA_TENANT_ID` / `ENTRA_AUDIENCE` / `ENTRA_SCOPE` | – / – / `Thunai.Use` | Microsoft Entra ID token checks (copilot/SETUP.md) |
| `COPILOT_TEAMS_URL` | – | link to the agent in Teams on the PWA home screen |
| `STT_PROVIDER` | `mock` | `openai_compat` (self-hosted Whisper), `sarvam`, `none` |
| `EMBEDDINGS_PROVIDER` | `none` | `openai_compat` with `EMBEDDINGS_BASE_URL` for vector similarity (optional) |
| `SEED_SAMPLE_DATA` | `true` | seed SAMPLE data into an empty database |
| `SITE_ADDRESS` / `PUBLIC_BASE_URL` | `localhost` | server name; base of every QR code |
| `CADDY_TLS` | `internal` | HTTPS certificate source |

Plant settings (shift calendar, planned hours for MTBF, similar-logs threshold and similarity cut-off
for fault cards, audio retention, alarm pre-fill window, minimum events for skill figures) are changed
in **Admin → Settings** and are audited. Integration keys and the Copilot status are in
**Admin → Integrations**; Microsoft accounts in **Admin → Users**.

## Definition of done (Phases 1, 2, 3 and Copilot)

| Item | Status |
|---|---|
| Starts with one command (`docker compose up`), with `.env.example` and sample data | Done. Tested here with Docker 29: all six services up, HTTPS via Caddy, worker jobs (including fault-card drafting), nightly backup. |
| All tests pass; evaluation results in `EVAL.md` | 141/141 tests pass on SQLite and PostgreSQL 16; evaluation 10/10 safety refusals and 4/4 sample cases with the rules engine. Real cases are still needed; see EVAL.md. |
| Microsoft Copilot connection | Tool API, Entra ID token checks (test-signed tokens) and the OpenAPI 2.0 file are tested in code. **Not yet tried in a real tenant:** follow copilot/SETUP.md, then run copilot/TEST-SCRIPT.md in Teams. |
| No secrets in code | Done. Keys come from `.env` (git-ignored); production refuses to start with the default `SECRET_KEY`. |
| README and RUNBOOK cover setup, backup, restore, adding machines and users | Done. Backup and restore commands were run and checked. RUNBOOK also covers fault cards, documents, alarm lists, the alarm feed, spare parts, photos and skills. |
| Short demo script with screenshots | [DEMO.md](DEMO.md); 39 screenshots taken by `docs/capture-demo.mjs` against the Docker stack, plus the agent's real tool answers (section 7). |
