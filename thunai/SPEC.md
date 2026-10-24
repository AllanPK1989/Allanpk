# Thunai: specification (Phase 0 output)

Status: **Phase 1 built on the defaults below; open for correction.** Written 24 Oct 2026 from
`Claude Code Prompt – AI Troubleshooting App for Technicians`. The owner asked to build the
application directly, so every Phase 0 question was answered with the **proposed default from the
brief**. Items marked **CONFIRM** need a decision from the plant before the pilot. None of them
blocked the Phase 1 build; changing any of them is a configuration or small code change.

## 1. Understanding (10 lines)

1. Thunai is an installable web app (PWA) for maintenance technicians at EPQPL Pondicherry.
2. A technician picks or scans a machine, describes the fault by voice or text in English, Tamil or a mix.
3. The AI asks at most 3 tap questions, then gives a safe, one-action-per-step procedure, safety first.
4. Each step has OK / Not OK / Can't do, read-aloud, "Why this step?" evidence and a Call supervisor button.
5. When the machine runs again, the session becomes a draft breakdown log for the technician to confirm.
6. Technicians can also log a fix directly by speaking; the AI fills the form and never overwrites their words.
7. Every log is stored in original, English and Tamil, classified, and feeds the machine's history and KPIs.
8. Supervisors verify logs; verified logs and approved fault cards are the AI's first sources.
9. Admins manage machines (Excel import, QR stickers), users, glossary and settings; everything is audited.
10. Phase 1 is an MVP for one pilot zone; knowledge automation and integrations follow in Phases 2 and 3.

## 2. Phase 0 answers (defaults taken)

| # | Question | Answer used |
|---|---|---|
| 1 | Devices | Both personal phones and shared zone tablets. PWA, no Play Store. |
| 2 | Scale | Designed for 200 users, 500 machines. |
| 3 | Login | Employee ID + 4-digit PIN. "Shared device" switch at login logs out after each session and after 10 min idle. 5 wrong PINs lock the account for 15 min. |
| 4 | Network | Patchy. Logging works offline and syncs later. AI guidance needs a connection. |
| 5 | Hosting | Docker Compose; same build on a plant server or cloud. **CONFIRM with Eaton IT before pilot.** |
| 6 | Data location | Database, audio and photos stay on the plant server. **CONFIRM:** problem text and log text are sent to the Claude API for processing (not stored for training under Anthropic's commercial terms), and that processing happens outside India. If text must not leave India, the AI adapter can point at an in-country deployment; that needs IT approval. |
| 7 | AI provider | Anthropic Claude API behind a provider-agnostic interface. Models set by environment variable. |
| 8 | Speech | Pluggable adapter. Shipped: OpenAI-compatible transcription endpoint (works with a self-hosted Whisper server, so audio stays on-premise) and Sarvam AI (Indian provider). Benchmark on 20 real recordings before choosing. |
| 9 | Budget | Cost per 100 queries and per 100 voice logs shown in section 9. The app logs real tokens and cost per call. |
| 10 | Tamil style | Simple spoken Tamil in Tamil script; technical terms stay in English. |
| 11 | Language setting | Profile default plus one-tap toggle on every screen. |
| 12 | Read aloud | Yes, in the chosen language, with replay. Phase 1 uses the phone's own text-to-speech (free, works offline). |
| 13 | Stored versions | Original, English and Tamil text for each field; audio kept 90 days (setting). |
| 14 | Machine master | Excel import with template; QR sticker per machine. |
| 15 | History | Excel import through the same pipeline as live logs. |
| 16 | Manuals | Phase 2. |
| 17 | Mandatory fields | Machine, technician, date, time, shift (auto); issue and corrective action (required); downtime start and end, root cause, parts, alarm code, photos (optional). |
| 18 | Verification | Zone supervisor. Unverified logs inform the AI but are labelled "not yet verified". |
| 19 | Glossary | Seeded with common technical terms; admin edits; used in prompts for speech, translation and Tamil output. |
| 20 | Integration | Phase 3. Phase 1 has Excel export and a REST API (OpenAPI docs at `/api/docs`). |
| 21 | Reports | MTTR, MTBF, top repeat faults per machine in Phase 1; zone/shift dashboards in Phase 2; Excel export now. |
| 22 | Pilot | One zone, 10 to 15 machines. MVP in 4 to 6 weeks. |
| 23 | Maintainers | In-house team. README, RUNBOOK and code comments. |
| 24 | Name | "Thunai" (Tamil: companion/helper), neutral branding. |

### Open questions (CONFIRM before pilot)

1. **KPI formulas.** Implemented (editable in `backend/app/kpi.py`):
   - MTTR (min) = total breakdown downtime ÷ number of breakdowns with a recorded downtime.
   - MTBF (h) = (planned hours in period − downtime hours) ÷ number of breakdowns.
   - Planned hours = days in period × `planned_hours_per_day` setting (default 24 for 3 shifts).
   - Breakdowns counted: status closed or verified. Rejected and draft logs are excluded.
2. **Shift timings.** Sample calendar A 06:00–14:00, B 14:00–22:00, C 22:00–06:00 (Asia/Kolkata). A C-shift event after midnight belongs to the previous day's C shift. Editable in Admin → Settings.
3. **Machine number format, zone and line names.** Sample data uses `DEMO-…` machine numbers and `[SAMPLE]` names. Zone names are from the brief.
4. **Data location** (question 6 above).
5. **Speech provider** after the benchmark.
6. **HTTPS certificate.** Microphone and camera need HTTPS. Plant DNS name + certificate from IT, or Caddy's internal CA installed on phones.

## 3. Scope by phase

**Phase 1 – MVP (built, merged in PR #11)**
- Machine registry: Excel import (upsert by machine number), QR code per machine, printable QR sheet.
- Login with employee ID + PIN; roles technician / supervisor / admin.
- Text and voice logging in English and Tamil with AI field extraction; offline queue with later sync.
- Ask Thunai: clarifying questions, step-by-step procedure, safety rules enforced in code, evidence, Call supervisor, session-to-log.
- Machine page: open issues, history timeline, top 5 repeat faults, approved fault cards, MTTR, MTBF.
- Background enrichment of each log: translation to English and Tamil, classification.
- Historical breakdown import; Excel export of logs and KPIs.
- Supervisor review queue: verify / reject logs; AI answers marked "not helpful".
- Admin: users, glossary, settings, audit trail (all edits recorded, no hard deletes).

**Phase 2 – Knowledge and reports (this build, see section 11)**: automatic fault-card drafting when
≥3 similar logs exist, approval and versioning; contradiction flags; dashboards (zone, shift,
knowledge coverage); expert tips; manual, drawing and alarm-list ingestion; optional embeddings.

**Phase 3 – Integration**: PM system, SAP and spare-parts links, PLC/SCADA alarm pre-fill,
photo-based diagnosis, skill-gap analytics.

Pulled forward from Phase 2: offline log queue (question 4 needs it) and device read-aloud (free).

## 4. User flows

**Ask Thunai** (≤3 taps): Home → Ask Thunai → pick/scan machine → speak or type the problem (alarm
code, photo optional) → answer up to 3 tap questions → steps one at a time (safety step first) →
OK / Not OK / Can't do drives the next step → "Is the machine running now?" → Yes: draft log opens
pre-filled for confirmation. No: session escalates, an open log is kept.

**Voice log** (≤3 taps): Home → New log → machine → hold mic and speak → AI fills issue, root cause,
corrective action, parts, downtime → fields the AI is unsure about are highlighted → technician taps
to correct or re-records → Submit. If an open log exists for the machine, the app offers to add to it.
Offline: the recording and form are saved on the phone and synced later; transcription runs after sync
and the log appears under "Needs your check".

**Supervisor**: Review → verify or reject (with reason) each closed log; edits are audited.
**Admin**: Machines (import, QR print), Users, Glossary, Settings, History import, Export.

## 5. Screens

Login · Home · Machine picker (search, recent first, zone filter) · QR scanner · Machine page ·
Ask Thunai (describe → questions → steps → finish) · Log form (new / confirm / view) · My logs ·
Review queue · Admin: Machines, QR sheet, Users, Glossary, Settings, Imports, Export, Audit.

## 6. Data model

All records link to a machine. Integer primary keys; `machine_no` is unique and is what users see.
Timestamps are stored in UTC and shown in plant time (Asia/Kolkata).

| Table | Key fields |
|---|---|
| machine_types | name, description |
| machines | machine_no (unique), name, machine_type_id, zone, line, make, model, plc_model, key_components, criticality A/B/C, status, qr_code, active |
| components | machine_id, name, category (pneumatic / electrical / sensor / plc / mechanical), part_no, make, location |
| users | employee_id (unique), name, role, zone, preferred_language, skill_level, phone, pin_hash, active, failed_attempts, locked_until |
| breakdown_logs | log_no, machine_id, technician_id, zone, shift, shift_date, reported_at, start_at, end_at, downtime_min, alarm_code, status (draft / open / closed / verified / rejected), verified_by, source (voice / text / ai_session / import), ai_session_id, needs_confirmation, client_uuid (offline idempotency) |
| log_texts | log_id, field (issue / root_cause / corrective_action), original, original_lang, english, tamil, ai_filled, ai_unsure |
| log_media | log_id or ai_session_id, kind (audio / photo), file_path, transcript, stt_provider, confidence, expires_at, purged_at |
| log_parts | log_id, part_no, description, qty |
| log_classification | log_id, symptom_category, component_id, component_name, failure_mode, confidence, edited_by |
| ai_sessions | machine_id, technician_id, language, problem_text, alarm_code, questions_and_answers, steps, step_responses, sources_used, model, prompt_version, tokens, cost_usd, outcome, feedback, resulting_log_id |
| ai_calls | purpose, model, tokens in/out/cache, cost_usd, ok, error, session_id, log_id |
| fault_cards | machine_id or machine_type_id, symptom (en/ta), ranked causes with counts, steps_en, steps_ta, parts, tools, avg_fix_min, source_log_ids, status, version, approved_by |
| glossary | term_en, term_ta, spoken_variants, category |
| translation_cache | key (hash of text + target + glossary version), translated |
| settings | key, value (JSON) |
| audit_log | user_id, entity, entity_id, action, before, after, at |

Phase 2 adds `expert_tips`, `documents` and `embeddings` (pgvector) through a new migration.

**Auto-population**: machine, zone, technician, date, time and shift fill automatically; downtime_min
is computed from start and end; a "machine running" session creates a draft log linked to the
session; each submit queues translate + classify; importing a machine creates its QR code.

**Data rules**: the technician's words are never overwritten (`original`); AI-filled fields stay marked
until confirmed; no hard deletes (deactivate / reject / retire); every change writes `audit_log`.

## 7. AI design

- Prompts live in `backend/prompts/<name>.v<N>.md`, never in code. Active version per prompt is an
  environment setting; each AI call records the prompt version.
- Calls: `clarify` (≤3 tap questions), `troubleshoot` (procedure JSON), `explain` (on tap),
  `extract_log` (voice/text → fields), `enrich_log` (translate + classify), `session_to_log`.
- Models: diagnosis `AI_MODEL_DIAGNOSIS` (default `claude-opus-5-5`); extraction and translation
  `AI_MODEL_EXTRACTION` (default `claude-haiku-5-5`). JSON is constrained with structured outputs
  and then validated on the server with Pydantic. Invalid output is retried once, then the app shows
  "Call supervisor".
- Retrieval order: approved fault cards (machine) → verified logs (machine) → logs and cards of the
  same machine type → unverified logs (labelled) → general knowledge (labelled "General suggestion:
  not seen on this machine before"). Phase 1 ranks with keyword similarity on English text with
  glossary normalisation. That is enough because results are filtered to one machine or type first.
  Embeddings come in Phase 2.
- Every step carries `source_refs`. The server drops refs that were not in the context, and labels
  steps without refs as general suggestions.
- **Safety rules enforced in code** (`backend/app/safety.py`, no setting can switch them off):
  - Requests to bypass, jumper or disable interlocks, guards, light curtains or e-stops, or to force
    PLC outputs or edit PLC programs, are refused before any AI call.
  - The first step is always energy isolation / LOTO. For pneumatics it also says to release stored air.
  - AI output containing a bypass instruction is rejected.
  - Steps with live electrical measurement get the "Authorised electrician only" badge.
  - Autoclave, steam and pressure-vessel machines get a "never open under pressure, escalate" step.
  - Low confidence or no matching history → a plain warning and a suggestion to call the supervisor.
- Cost control: small model for extraction and translation; translation cache; prompt caching on the
  fixed system prompt; tokens and cost logged per call and per session.
- Without an API key the app runs with `AI_PROVIDER=mock`, a rule-based stand-in for demos and tests.
  The UI shows a "Demo AI" badge in that mode.

## 8. Tech stack and hosting

| Layer | Choice |
|---|---|
| Frontend | React 19 + TypeScript + Vite PWA, EN/TA strings, IndexedDB offline queue, MediaRecorder audio, Noto Sans Tamil bundled |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 (pgvector image, extension used from Phase 2) |
| Jobs | Redis + RQ worker; inline fallback for development |
| Files | Local volume `/data/media` (S3-compatible later) |
| AI | Anthropic Python SDK behind `AIProvider` interface |
| Speech | `STTProvider` interface: OpenAI-compatible (self-hosted Whisper), Sarvam AI, mock |
| Auth | Employee ID + PIN (scrypt hash), JWT, role checks |
| Deploy | Docker Compose: db, redis, api, worker, web (Caddy: HTTPS + static files + `/api` proxy), nightly `pg_dump` backup |

Server sizing for the pilot: 2 vCPU, 4 GB RAM, 50 GB disk. A self-hosted Whisper server needs its own
GPU or a larger CPU machine. Size it after the benchmark.

## 9. Cost estimate (Claude API list prices, USD, Oct 2026)

| Item | Assumption | Per 100 |
|---|---|---|
| Troubleshooting sessions | clarify (~3k in / 1k out) + procedure (~6k in / 4k out incl. thinking) on Opus 5.5 at $4 / $20 per M tokens | ≈ $13 |
| Same on Sonnet 5.5 (`AI_MODEL_DIAGNOSIS=claude-sonnet-5-5`, $2 / $10) | | ≈ $7 |
| Voice/text logs: extraction + translate/classify | ~5k in / 2k out on Haiku 5.5 at $0.10 / $0.50 | ≈ $0.15 |
| Speech-to-text | depends on provider; measure in the benchmark | TBD |

Example: 15 machines, 20 sessions and 40 logs a day ≈ $80/month on Opus 5.5 or $40 on Sonnet 5.5,
plus speech. These are estimates. The app records real cost per session; check after week 1.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Unsafe advice | Code-level safety guard, safety-first step, refusal test set (must be 100%), supervisor escalation always visible |
| Wrong or invented steps | Evidence-first retrieval, source refs validated, "general suggestion" label, supervisor verification |
| Tamil quality | Glossary, spoken-style prompt, native review of 30 outputs before pilot, two-technician readability rating |
| Speech accuracy in noise | Provider benchmark with WER per provider; technician always confirms the form |
| Data leaving the plant | Question 6; on-prem storage; provider choice; no training on data |
| Low adoption | ≤3 taps, voice first, big buttons, works with gloves, offline logging |
| Weak 4-digit PINs | Lockout after 5 tries, shared-device auto logout, HTTPS only, PIN reset by admin |
| Unverifiable evaluation now | Eval harness ships; real 20-case set needs plant data (see `EVAL.md`) |

## 11. Phase 2 design (defaults taken)

The owner asked to start Phase 2 directly, so these choices follow the brief and the Phase 0 defaults.
Items marked **CONFIRM** can be changed later without rework.

### 11.1 Automatic fault cards
- **When:** after each log is translated and classified, and after historical imports, the worker
  looks for groups of similar logs. A group is logs with the same symptom category, or keyword
  similarity of at least `similarity_cutoff` (setting, default 0.35) on the English issue text.
  Only closed or verified logs count; rejected ones never do.
- **Scope:** if a group has at least `similar_logs_threshold` (setting, default 3) logs on one machine,
  the card belongs to that machine. Otherwise, if the machines of one type together reach the
  threshold, the card belongs to the machine type and helps every machine of that type.
- **Drafting:** the diagnosis model writes the card from the group's logs only: symptom (EN/TA), causes
  ranked by how often they occurred (counts computed in code, not by the AI), verified fix steps in
  English and Tamil, parts, tools, and average fix time (computed in code). Draft cards cite their
  source logs. The same safety guard used for procedures rejects unsafe steps.
- **Approval:** supervisors see drafts under Review → Fault cards. They can edit the text, approve,
  reject (with a reason) or later retire a card. Only approved cards are used as the first AI source.
- **Versions:** approving an edit, or approving a re-draft after new logs, increases the version and
  keeps the previous content in the card's history. Nothing is deleted.
- **Contradiction flag:** when a new closed or verified log matches an approved card's symptom but its
  root cause matches none of the card's causes, the card is marked "needs review" with that log
  attached. It stays in use (with the flag shown) until a supervisor approves or re-drafts it.
  **CONFIRM:** whether a flagged card should stop being used until it is reviewed.

### 11.2 Dashboards
Supervisors and admins get a dashboard with period (7 / 30 / 90 days) and zone filters: open
breakdowns, downtime by zone and by shift, MTTR and MTBF by machine (worst first), top repeat faults
across the plant, knowledge coverage (machines with and without approved fault cards, share of logs
verified, drafts and flags waiting), and Ask Thunai use (sessions, resolved, escalated, helpful /
not helpful). The Excel export gains the same tables.

### 11.3 Expert tips
Any technician can record a short tip for a machine by voice or text (stored in original, English and
Tamil, like logs). Supervisors approve or reject tips in the review queue. Approved tips show on the
machine page and are an AI source with the same weight as verified logs, labelled "expert tip".

### 11.4 Documents and alarm lists
- **Upload** per machine or per machine type: PDF manuals, SOPs, electrical drawings (PDF or image),
  plain text, and alarm lists (Excel or CSV).
- **Text extraction** on the server: the PDF text layer (no OCR); images are stored and listed but not
  read. **CONFIRM:** reading scanned drawings would mean sending them to an AI model (Phase 3,
  photo-based diagnosis), which needs the data-location decision in question 6.
- **Chunks** of about 1,200 characters with page numbers are indexed and become the 4th AI source
  ("manuals, drawings and alarm lists"), cited as `DOC-<id>-p<page>`.
- **Alarm lists** become an alarm-code table (code, message, cause, remedy). When a technician enters an
  alarm code in Ask Thunai, the matching entry is shown at once and given to the AI as evidence
  (`ALM-<code>`). Template: `alarm_code, message, cause, remedy, machine_type or machine_no`.

### 11.5 Similarity search and embeddings
Anthropic does not offer an embeddings API. Adding an embeddings vendor would send log text to another
company, which question 6 has not cleared. Phase 2 therefore keeps keyword similarity as the default
and adds an optional embeddings adapter for any OpenAI-compatible `/embeddings` endpoint, for example
a multilingual model served on the plant network. When it is configured, retrieval and fault-card
grouping use a mix of keyword and vector similarity, and `python -m app.cli reindex` fills the
vectors. Vectors are stored as JSON next to the record. At this plant's size (thousands of logs per
machine type) an exact search in Python is fast enough; a pgvector index can be added later without
changing the API. **CONFIRM:** embeddings provider, if any.

### 11.6 Read-aloud
Phase 1 already reads steps aloud with the phone's own text-to-speech, which works offline and costs
nothing. Server-side text-to-speech is not added: it would need a provider decision like speech-to-text
and gives little benefit if phones have a Tamil voice installed (RUNBOOK covers installing one).

### 11.7 Data model additions (migration 0002)
| Table | Key fields |
|---|---|
| fault_cards (extended) | scope (machine / type), title_key, review_note, flagged_log_ids, history, drafted_at, rejected_reason |
| expert_tips | machine_id, author_id, original, original_lang, english, tamil, media_id, status (pending / approved / rejected), reviewed_by |
| documents | machine_id or machine_type_id, title, kind (manual / sop / drawing / alarm_list / other), file_path, mime, pages, status, indexed_at, uploaded_by, active |
| document_chunks | document_id, page, seq, text |
| alarm_codes | machine_id or machine_type_id, code, message, cause, remedy, document_id |
| embeddings | source_type, source_id, model, vector (JSON), text_hash |
