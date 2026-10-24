# Thunai: Phase 1 build plan

Order from the brief: scaffold → schema, migrations and sample data → auth → machine registry →
text logging → voice and extraction → AI troubleshooting → history page → export.
Each step ends with a demo (API call or screen) before the next starts.

| # | Step | Done when |
|---|---|---|
| 1 | Scaffold: `backend/` (FastAPI), `frontend/` (Vite React TS PWA), `docker-compose.yml`, `.env.example` | `/api/health` answers; web shell loads |
| 2 | Schema: SQLAlchemy models, Alembic migration `0001`, settings defaults, sample data (`DEMO-` machines, `[SAMPLE]` names, demo users) | `alembic upgrade head` + `python -m app.cli seed` on Postgres |
| 3 | Auth: employee ID + PIN, lockout, JWT, roles, shared-device logout | Login screen works; wrong PIN ×5 locks |
| 4 | Machine registry: CRUD, Excel template + import (upsert), QR PNG/SVG, QR print sheet, audit | Import sample sheet; scan sticker opens machine page |
| 5 | Text logging: create / edit / submit, shift + downtime auto-fill, open-log merge offer, log_texts, enrichment job (translate + classify) | Log appears in EN and TA |
| 6 | Voice + extraction: audio upload, ffmpeg → STT adapter, `extract_log` prompt, unsure-field highlighting, offline queue + sync | Spoken Tanglish sample fills the form |
| 7 | AI troubleshooting: retrieval, `clarify` + `troubleshoot` prompts, safety guard, step screen, evidence, explain, call supervisor, session → draft log | Full flow on a demo machine; safety prompts refused |
| 8 | Machine page: open issues, timeline, top 5 repeat faults, fault cards, MTTR / MTBF | Numbers match unit tests |
| 9 | Historical import + Excel export; supervisor review queue; admin users / glossary / settings | Import → export round trip |
| 10 | Tests, eval harness, README, RUNBOOK, demo script with screenshots | All tests pass; `EVAL.md` written |
