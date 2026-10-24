# Thunai: build plan

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

## Phase 2 build plan

| # | Step | Done when |
|---|---|---|
| 11 | Migration `0002`: tip, document, chunk, alarm-code and embedding tables; fault-card fields | upgrade and downgrade run on PostgreSQL |
| 12 | Fault-card engine: grouping, AI draft (`draft_fault_card` prompt), approve / edit / reject / retire, versions, contradiction flag; review UI | a 4th similar sample log drafts a card; approval shows it on the machine page and in Ask |
| 13 | Dashboard API and page; dashboard sheets in the Excel export | numbers match the unit tests |
| 14 | Expert tips: record by voice or text, review, machine page, AI source | an approved tip is cited in "Why this step?" |
| 15 | Documents and alarm lists: upload, PDF text, chunks, alarm-code lookup in Ask, AI source | entering a sample alarm code shows its meaning |
| 16 | Embeddings adapter (optional), hybrid similarity, `reindex` command | tests with a fake embeddings server |
| 17 | Tests, evaluation, docs and screenshots | all tests pass on SQLite and PostgreSQL; Docker stack starts |

## Phase 3 build plan

| # | Step | Done when |
|---|---|---|
| 18 | Migration `0003`: spare parts, part fits, machine alarms, integration keys; photo observation columns | upgrade, downgrade and `alembic check` run on PostgreSQL |
| 19 | Spare parts: Excel/CSV import with template, machine page section, parts picker in the log form, stock shown on steps and fault cards, AI context | a step naming a sample part number shows its stock |
| 20 | Integration API: keys with scopes, alarm feed, parts sync; alarm pre-fill in Ask Thunai and New log | a posted sample alarm pre-fills the next log's alarm code and start time |
| 21 | ~~PM plan and outbound webhooks for the PM system and SAP~~ | out of scope (owner decision, 24 Oct 2026); removed |
| 22 | Photo diagnosis: image input in the AI adapter, `read_photo` prompt, server-side re-encoding, observations on the Ask screen, `PHOTO-` evidence, `AI_PHOTOS` switch | a sample HMI photo fills the alarm code and is cited in "Why this step?" |
| 23 | Skill-gap analytics: API, page, rules, Excel export | numbers match the unit tests |
| 24 | Tests, evaluation, docs and screenshots | all tests pass on SQLite and PostgreSQL; Docker stack starts |
