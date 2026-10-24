# Thunai (துணை): breakdown help for maintenance technicians

Thunai is an installable web app (PWA) for maintenance technicians at EPQPL Pondicherry. A technician
at a stopped machine gets simple, safe, step-by-step troubleshooting in English or Tamil, then logs
the fix by voice. Every log builds the machine's history and knowledge base.

Phase 1 (MVP) and Phase 2 (knowledge and reports) are built: see [SPEC.md](SPEC.md) for scope and
decisions (Phase 2 in section 11), [PLAN.md](PLAN.md) for the
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
| `D-ADMIN` | 1234 | Admin | English |

Without a `.env` file the app runs in **demo mode**: `AI_PROVIDER=mock` answers from sample rules
and the speech-to-text returns a labelled demo transcript. A "Demo" badge shows on every screen.
To use the real AI, copy `.env.example` to `.env`, set `AI_PROVIDER=anthropic` and
`ANTHROPIC_API_KEY`, then `docker compose up -d` again. Going live: follow [RUNBOOK.md](RUNBOOK.md).

## What it does

| Module | Features |
|---|---|
| Machine registry | Excel import (upsert by machine number), QR code per machine, printable sticker sheet, machine page with open issues, history, top 5 repeat faults, fault cards, MTTR and MTBF |
| Ask Thunai | Problem by voice or text (English, Tamil, mixed), up to 3 tap questions, one step at a time with OK / Not OK / Can't do, read-aloud, "Why this step?" evidence, Explain, Call supervisor always visible, "Is the machine running?" → draft log or escalation |
| Breakdown logging | Push-to-talk voice log, AI fills issue / root cause / action / parts / downtime, AI-filled fields highlighted until confirmed, one follow-up question when a required field is missing, shift and downtime auto-filled, open-log merge, offline queue that syncs later |
| Knowledge | Each log stored as original + English + Tamil, translated and classified in the background, translation cache |
| Supervisor and admin | Review queue (verify / reject, "not helpful" answers, escalations), users and PINs, glossary, settings (shift calendar, thresholds), historical import, Excel export of logs and KPIs, AI cost per purpose, audit trail |
| Fault cards (Phase 2) | Drafted by the AI when 3 or more similar logs exist for a machine or machine type; causes ranked by counts computed from the logs; supervisor edits, approves, rejects, retires or re-drafts; versions kept; a new log with an unknown root cause flags the card for review |
| Dashboard (Phase 2) | Open breakdowns, downtime by zone and shift, MTTR / MTBF by machine, top repeat faults, knowledge coverage, Ask Thunai use; 7 / 30 / 90 days and zone filters; Excel export |
| Expert tips (Phase 2) | Short tips by voice or text, reviewed by supervisors; approved tips show on the machine page and are an AI source |
| Documents and alarm lists (Phase 2) | Manuals, SOPs, drawings and alarm lists per machine or machine type; PDF text indexed for the AI; alarm-code meaning shown as soon as it is typed; optional embeddings for similarity search |

Safety rules are enforced in code (`backend/app/safety.py`) as well as in the prompts: unsafe requests
are refused before any AI call, every procedure starts with LOTO (plus stored-air release for
pneumatics and a pressure check for autoclaves), unsafe AI output is rejected, live electrical
measurements get an "Authorised electrician only" badge, and steps without evidence are labelled
"General suggestion".

## Layout

```
thunai/
├── SPEC.md  PLAN.md  EVAL.md  RUNBOOK.md  DEMO.md
├── docker-compose.yml  .env.example
├── backend/                 FastAPI + SQLAlchemy + Alembic (Python 3.12)
│   ├── app/                 API, services, safety, retrieval, KPI, jobs, knowledge (fault cards),
│   │                        dashboard, tips, documents, embeddings
│   │   ├── ai/              provider interface, Claude adapter, mock, output contracts
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
.venv/bin/pytest -q                       # 90 tests, SQLite; TEST_DATABASE_URL=... for PostgreSQL
DATABASE_URL=sqlite:///./dev.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite:///./dev.db .venv/bin/python -m app.cli init      # SAMPLE data
DATABASE_URL=sqlite:///./dev.db .venv/bin/uvicorn app.main:app --reload
.venv/bin/python -m eval.run_eval         # evaluation harness (mock AI unless configured)
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
| `AI_PROVIDER` | `mock` | `anthropic` for the Claude API |
| `AI_MODEL_DIAGNOSIS` | `claude-opus-5-5` | troubleshooting and clarifying questions |
| `AI_MODEL_EXTRACTION` | `claude-haiku-5-5` | voice-log extraction, translation, classification, explanations |
| `PROMPT_VERSIONS` | (all v1) | e.g. `troubleshoot=v2` to switch one prompt |
| `STT_PROVIDER` | `mock` | `openai_compat` (self-hosted Whisper), `sarvam`, `none` |
| `EMBEDDINGS_PROVIDER` | `none` | `openai_compat` with `EMBEDDINGS_BASE_URL` for vector similarity (optional) |
| `SEED_SAMPLE_DATA` | `true` | seed SAMPLE data into an empty database |
| `SITE_ADDRESS` / `PUBLIC_BASE_URL` | `localhost` | server name; base of every QR code |
| `CADDY_TLS` | `internal` | HTTPS certificate source |

Plant settings (shift calendar, planned hours for MTBF, similar-logs threshold and similarity cut-off
for fault cards, audio retention) are changed in **Admin → Settings** and are audited.

## Definition of done (Phases 1 and 2)

| Item | Status |
|---|---|
| Starts with one command (`docker compose up`), with `.env.example` and sample data | Done. Tested here with Docker 29: all six services up, HTTPS via Caddy, worker jobs (including fault-card drafting), nightly backup. |
| All tests pass; evaluation results in `EVAL.md` | 90/90 tests pass on SQLite and PostgreSQL 16. Real-model evaluation needs plant cases and an API key; see EVAL.md. |
| No secrets in code | Done. Keys come from `.env` (git-ignored); production refuses to start with the default `SECRET_KEY`. |
| README and RUNBOOK cover setup, backup, restore, adding machines and users | Done. Backup and restore commands were run and checked. RUNBOOK also covers fault cards, documents and alarm lists. |
| Short demo script with screenshots | [DEMO.md](DEMO.md); 29 screenshots taken by `docs/capture-demo.mjs` against the Docker stack. |
