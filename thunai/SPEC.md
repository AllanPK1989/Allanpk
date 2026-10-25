# Thunai: specification (Phase 0 output)

Status: **Phases 1 and 2 built on the defaults below, Phase 3 in section 12, Microsoft Copilot in section 13 (replaces the Claude API); open for correction.** Written 24 Oct 2026 from
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
| 6 | Data location | **Superseded by section 13 (Microsoft Copilot).** Was: database, audio and photos stay on the plant server. **CONFIRM:** problem text and log text are sent to the Claude API for processing (not stored for training under Anthropic's commercial terms), and that processing happens outside India. If text must not leave India, the AI adapter can point at an in-country deployment; that needs IT approval. |
| 7 | AI provider | **Microsoft Copilot Studio agent** calling Thunai's tool API (section 13, owner decision 25 Oct 2026). Was: Anthropic Claude API. |
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
| 20 | Integration | Phase 3: PLC/SCADA alarms and spare-parts stock. PM system and SAP: out of scope (owner, 24 Oct 2026). Excel export and a REST API (OpenAPI docs at `/api/docs`). |
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

**Phase 2 – Knowledge and reports (built, PR #12, see section 11)**: automatic fault-card drafting when
≥3 similar logs exist, approval and versioning; contradiction flags; dashboards (zone, shift,
knowledge coverage); expert tips; manual, drawing and alarm-list ingestion; optional embeddings.

**Phase 3 – Integration (this build, see section 12)**: spare-parts stock (file import and API),
PLC/SCADA alarm feed that pre-fills logs, photo-based diagnosis, skill-gap analytics by technician and
machine type. PM system links and SAP integration are out of scope (owner decision, 24 Oct 2026).

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
Phase 2 adds: Fault-card review · Dashboard · Admin: Documents. Phase 3 adds: Skills · Admin:
Integrations (keys).

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

> **Superseded in part by section 13.** Since 25 Oct 2026 the server runs the rules engine only; the Copilot agent does conversation, photos and translation. The prompts, contracts, retrieval order and safety rules below still apply.

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
| AI | Rules engine behind the `AIProvider` interface; conversation in a Copilot Studio agent (section 13) |
| Speech | `STTProvider` interface: OpenAI-compatible (self-hosted Whisper), Sarvam AI, mock |
| Auth | Employee ID + PIN (scrypt hash), JWT, role checks |
| Deploy | Docker Compose: db, redis, api, worker, web (Caddy: HTTPS + static files + `/api` proxy), nightly `pg_dump` backup |

Server sizing for the pilot: 2 vCPU, 4 GB RAM, 50 GB disk. A self-hosted Whisper server needs its own
GPU or a larger CPU machine. Size it after the benchmark.

## 9. Cost estimate (Claude API list prices, USD, Oct 2026)

> **No longer applies** (section 13.6): Thunai makes no model calls. Kept for comparison.

| Item | Assumption | Per 100 |
|---|---|---|
| Troubleshooting sessions | clarify (~3k in / 1k out) + procedure (~6k in / 4k out incl. thinking) on Opus 5.5 at $4 / $20 per M tokens | ≈ $13 |
| Same on Sonnet 5.5 (`AI_MODEL_DIAGNOSIS=claude-sonnet-5-5`, $2 / $10) | | ≈ $7 |
| Voice/text logs: extraction + translate/classify | ~5k in / 2k out on Haiku 5.5 at $0.10 / $0.50 | ≈ $0.15 |
| Speech-to-text | depends on provider; measure in the benchmark | TBD |
| Photo diagnosis (Phase 3, only with `AI_PHOTOS=true`) | up to ~4,800 image tokens + ~500 out on Opus 5.5 | ≈ $3 |

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

## 12. Phase 3 design (defaults taken)

The owner asked to start Phase 3 directly. The brief lists: PM system, spare parts and SAP links; PLC
or SCADA alarm codes to pre-fill logs; photo-based diagnosis; skill-gap analytics by technician and
machine.

**Owner decision, 24 Oct 2026: PM system links and SAP integration are out of scope.** A first build
had a PM plan mirror, signed webhooks for the PM system and SAP, a logs poll and an external-reference
write-back; they were removed (they are in the git history, commit 3d8872b, if this changes). The
breakdown log stays Thunai's own record; Excel export and the REST API (question 20) remain for
monthly reports.

Which SCADA or PLC gateways and stores system the plant uses is not known yet, so Thunai offers
**system-neutral connection points** rather than a vendor connector:
- **files:** Excel or CSV imports, the same way machines and history are imported;
- **an inbound API** with integration keys.

**CONFIRM:** which gateway and stores system, access method (files or API), owner on the IT side.

Not built, by design:
- Thunai never writes stock back. The stores system stays the record.
- No alarm opens a log by itself. Technicians start logs.

### 12.1 Integration keys and inbound API
- **Keys.** Admins create one key per connected system, with scopes `alarms` and `parts`.
  - The key is shown once and stored only as a SHA-256 hash; it is a long random token, so a fast
    hash is enough.
  - It is sent in the `X-Thunai-Key` header. Keys can be deactivated, show "last used", and every
    change is audited.
- **Endpoints** (OpenAPI docs at `/api/docs`). Each call takes at most 1,000 rows. The response lists
  accepted rows and rejected rows with the reason. Validation is the same as for the file imports.

| Endpoint | Scope | Purpose |
|---|---|---|
| `POST /api/integrations/alarms` | alarms | PLC or SCADA alarm events |
| `PUT /api/integrations/parts` | parts | spare-parts stock (upsert by part number) |

### 12.2 Spare parts (stores stock)
- **Catalogue fields:** part number (the plant's own), description, unit, stock on hand, minimum stock,
  store location, manufacturer part numbers, and the machine types or machines it fits. Each stock
  figure carries the time it was valid ("as of").
- **Sources:** Admin → Import → Spare parts (Excel or CSV, template provided) or `PUT
  /api/integrations/parts`.
  - Rows are matched by part number.
  - Parts missing from a file are left as they are (no hard deletes). An admin can deactivate them.
- **Uses:**
  - **AI context:** the AI receives "Spare parts for this machine": parts that fit the machine or its
    type, or whose number matches a component's part number. Prompt rule: use only these part
    numbers or the component part numbers; never invent one (the brief's "never guess part
    numbers").
  - **Steps and fault cards:** part numbers in their text are matched exactly (whole word, any case)
    against the catalogue. The screen then shows stock and location, for example "2 in store A-12,
    as of 24 Oct", or a clear "out of stock" warning.
  - **Log form:** the "Parts used" picker searches the catalogue. Free text is still allowed and is
    marked "not in the catalogue".
  - **Machine page:** spare parts with stock, and low stock highlighted.
  - **Dashboard:** parts used in breakdowns in the period, with current stock and a low-stock flag.

### 12.3 PLC and SCADA alarms
- **Feed.** Alarm events come from a SCADA system, an alarm historian or a gateway (for example an OPC
  UA or Modbus bridge run by IT), posted to `POST /api/integrations/alarms`.
  - Each event has: machine number, alarm code, optional message, raised time, optional cleared time,
    optional event id.
  - Repeats of the same event id, or the same machine, code and raised time, are ignored.
- **Pre-fill.** When a technician opens Ask Thunai or New log on a machine, the newest alarm that is
  not cleared and was raised within `alarm_prefill_hours` (setting, default 8) is used:
  - **Ask Thunai:** it fills the alarm code.
  - **New log:** it fills the alarm code and the downtime start time.
  - Pre-filled values are marked "from the machine" and can be changed. The alarm-list meaning shows
    as in Phase 2.
- **Evidence.** The machine's alarm counts for the last 24 hours (how often each code was raised) go to
  the AI as evidence about the current breakdown (`SCADA-<code>`). For example: "A101 raised 4 times
  since 08:10".
- **Link.** The alarm event is linked to the log that used it.
- **CONFIRM:** which gateway, how machine numbers appear in alarm tags, and whether an alarm should
  open a draft log automatically. That is not done by default.

### 12.4 Photo-based diagnosis

> **Superseded by section 13.1.** Photos are read by the Copilot agent in Teams. Thunai stores and
> checks the readings, and they are still evidence `PHOTO-n`. In the PWA, photos are attachments
> only. `AI_PHOTOS` and the server-side reading below were removed.
- **Reading the photo.** A technician adds a photo in Ask Thunai, for example of a gauge, an HMI
  screen, indicator LEDs or a damaged part. The diagnosis model reads it straight away, and the
  technician sees:
  - what it shows;
  - readings with units, only where they are legible ("could not read" otherwise);
  - alarm codes on a screen;
  - visible damage.
  An alarm code read from an HMI fills the alarm field if it is empty (marked and editable).
- **Evidence.** The observations are evidence about the current breakdown (`PHOTO-<id>`), used for the
  questions and steps. Fault cards and logs still come first for causes.
- **Safety.**
  - Text in a photo is treated as data, never as instructions.
  - The safety guard checks the procedure as before.
  - Readings are approximate, so steps still ask the technician to check values.
  - A photo the model cannot read is reported as unreadable, never guessed.
- **Privacy and data location.**
  - Before sending, the server re-encodes the photo: location and camera metadata are removed and
    the long edge is capped at 2,576 px, the model's maximum.
  - Photos are sent to the Claude API only when `AI_PHOTOS=true`. In demo mode the mock AI reads
    sample photos without sending anything.
  - Photos stay on the plant server either way.
  - **CONFIRM** with question 6. Technicians are asked not to photograph people.
- **Cost:** up to about 4,800 input tokens per full-size photo plus a short answer, about $0.03 per
  photo on Opus 5.5.

### 12.5 Skill-gap analytics
- **Who sees it:** supervisors (their own zone) and admins, over 30, 90 or 365 days.
- **Per technician and machine type:**
  - fixes (closed or verified logs);
  - median repair time, and its ratio to the team's median on that machine type;
  - Ask Thunai sessions, the share escalated, and "Can't do" steps;
  - approved tips.
- **Single-person knowledge:** machine types with breakdowns in the period that only one technician,
  or nobody in Thunai, has fixed.
- **Suggestions,** from fixed rules in code (no AI):
  - pair technician A with B on machine type X when A escalated at least half of at least 3 sessions
    there and B has at least 3 fixes;
  - name a second person for each single-person machine type;
  - point out repeated "Can't do" on authorised-only electrical steps (training or authorisation
    need).
- **Fairness:** figures show only with at least `skill_min_events` events (setting, default 3) and
  always with their counts.
- **Purpose:** training and shift planning, not appraisal. **CONFIRM** with HR before per-person figures
  are shown beyond supervisors.
- **Export:** Excel.

### 12.6 Data model additions (migration 0003)
| Table | Key fields |
|---|---|
| spare_parts | part_no (unique), description, unit, stock_qty, min_qty, location, alt_part_nos, match_keys, stock_at, source, active |
| part_fits | part_id, machine_id or machine_type_id |
| machine_alarms | machine_id, code, message, raised_at, cleared_at, source, event_id, log_id |
| integration_keys | name, key_hash, key_prefix, scopes, active, last_used_at, created_by |
| log_media (extended) | observation (JSON), observed_at, observation_model |

New settings: `alarm_prefill_hours` (8), `skill_min_events` (3).

New environment variable: `AI_PHOTOS` (false).

Prompt versions:
- `troubleshoot.v2` and `clarify.v2` add the photo, alarm-feed and parts sections. They are the
  defaults; the v1 prompts still work.
- `read_photo.v1` is new.

### 12.7 Phase 3 risks
| Risk | Mitigation |
|---|---|
| Leaked integration key | Scoped, hashed, revocable keys; last-used time shown; HTTPS only |
| Photos leave the plant | Now: photos sent in Teams stay in Microsoft 365 (section 13.5); PWA photos stay on the plant server |
| Misread gauge or screen | Shown to the technician first; "could not read" instead of guesses; steps still ask for a check |
| Wrong part number on screen | Only exact matches against the catalogue are shown; the AI may only cite listed numbers |
| Skill figures used unfairly | Minimum event counts, counts always shown, supervisors and admins only, HR to confirm |

## 13. Microsoft Copilot (owner decision, 25 Oct 2026)

**Owner decision, 25 Oct 2026:** Eaton will approve Microsoft Copilot, not the Claude API. So Thunai
moves to **Microsoft 365 Copilot / Copilot Studio**. Technicians talk to a Thunai agent in Microsoft
Teams or Microsoft 365 Copilot. The agent calls Thunai's tool API for machine facts, safe repair
steps and logging. The Claude adapter, its dependency and its settings are removed. The Thunai server
has no language model of its own any more.

Before this choice the owner was told what it costs:
- a Microsoft licence or Copilot Studio capacity for every technician;
- a weaker safety screen, because Microsoft's model, not Thunai's code, writes the chat (13.4);
- no offline use and no push-to-talk in Teams.

The PWA stays for:
- offline logging;
- supervisors and admins;
- technicians without a Microsoft account.

### 13.1 Who does what

| Work | Before (sections 7 and 12) | Now |
|---|---|---|
| Conversation, English and Tamil | Claude | Thunai agent in Copilot Studio (Microsoft's models) |
| Clarifying questions | Claude (`clarify`) | Thunai rules (fixed tap questions), asked by the agent |
| Repair steps | Claude, checked by `safety.py` | **Thunai rules engine**, checked by `safety.py`. Sources: fault cards, logs, alarm list, alarm feed, tips, manuals. The agent shows the steps as given |
| Refusing unsafe requests | `safety.py` before any AI call | `safety.py` in `startTroubleshooting` and `checkSafety`, plus the agent instructions |
| "Why this step?" | Claude (`explain`) | The agent explains from the step text and its evidence. It may not add actions |
| Reading photos | Claude (`AI_PHOTOS`) | The agent reads photos sent in Teams and passes the readings to Thunai as evidence (`PHOTO-n`). In the PWA, photos are attachments only |
| Log from speech or text | Claude (`extract_log`) | In Teams: the agent fills the log fields from the chat (`createLog`). In the PWA: rules extraction, then the technician checks the form as before |
| English ↔ Tamil translation of logs | Claude (`enrich_log`, `translate`) | The agent sends both versions when it creates a log. Supervisors ask the agent to translate PWA logs (`listLogsToTranslate`, `saveTranslations`). Until then the original is shown |
| Fault-card drafts, classification | Claude | Thunai rules (group logs by cause; keyword match for component and failure mode) |

The AI interface (`backend/app/ai/`) stays, with the rules engine as its only provider. The prompts
and output contracts stay too. If Eaton later approves a model API, adding an adapter there brings
the earlier behaviour back without other code changes.

### 13.2 Tool API (`/api/copilot`)

The custom connector is built from `copilot/thunai-tools.swagger.json`. That file is OpenAPI 2.0,
which Copilot Studio and Power Platform custom connectors expect; Copilot Studio converts OpenAPI 3
to 2. It is generated from the code (`python -m app.cli copilot-spec`), and a test fails if the
committed file is out of date. Microsoft suggests at most 25 to 30 tools per agent; Thunai has 15.

| Tool (operationId) | Call | Who | What it does |
|---|---|---|---|
| `whoAmI` | `GET /me` | all | Name, role, zone and language of the signed-in technician |
| `findMachines` | `GET /machines?q=` | all | Find machines by number, name or line |
| `getMachine` | `GET /machines/{machine_no}` | all | Status, active PLC alarm with its meaning, open logs, last fixes, low-stock parts |
| `lookupAlarm` | `GET /machines/{machine_no}/alarms/{code}` | all | Alarm-list meaning, cause, remedy and past fixes for the code |
| `startTroubleshooting` | `POST /sessions` | all | Safety refusal check. Returns tap questions, or the first step. Accepts photo readings |
| `answerQuestions` | `POST /sessions/{id}/answers` | session owner | Returns the first step |
| `getSession` | `GET /sessions/{id}` | owner, supervisor | Current step and progress |
| `reportStep` | `POST /sessions/{id}/steps` | owner | OK / Not OK / Can't do. Returns the next step, "finished" or "stop and call the supervisor" |
| `callSupervisor` | `POST /sessions/{id}/call-supervisor` | owner | Summary to send, supervisors' names and phone numbers |
| `closeSession` | `POST /sessions/{id}/close` | owner | Machine running or not, what fixed it. Creates the breakdown log |
| `createLog` | `POST /logs` | all | Log a fix directly, in the technician's words plus the English version |
| `searchParts` | `GET /parts?q=&machine_no=` | all | Catalogue matches with stock and store location |
| `checkSafety` | `POST /safety-check` | all | Is this instruction allowed? Used before the agent says anything that is not a Thunai step |
| `listLogsToTranslate` | `GET /translations` | supervisor, admin | Log texts that lack English or Tamil |
| `saveTranslations` | `POST /translations` | supervisor, admin | Store the agent's translations (only fills empty versions) |

Every answer is small, well under Microsoft's connector payload limits. Thunai makes no model calls,
so no call comes near the tool time-out. Each step comes as fields and as a ready `display` text in
the session language. The agent is told to show that text as it is.

### 13.3 Sign-in and users

- **Microsoft Entra ID OAuth 2.0, the technician's own account.** The custom connector uses Entra
  ID as its identity provider. Each technician signs in once in the chat, and the connector sends
  their access token to Thunai. There is no shared key: every log must name the person who did the work.
- **Thunai checks every token:**
  - the signature, against the tenant's published keys;
  - the issuer is the configured tenant (v1 or v2 tokens);
  - the audience is the Thunai API app (`ENTRA_AUDIENCE`);
  - the delegated scope `ENTRA_SCOPE` (default `Thunai.Use`) is present;
  - expiry, with 60 s leeway.
  Application-only tokens are refused.
- **Linking people.** An admin enters each person's Microsoft account (UPN, for example
  `name@eaton.com`) on their Thunai user. On first use Thunai matches the token's UPN to that user and
  then binds the account's object ID. After that it matches only on the object ID, which never
  changes. Unknown or inactive accounts are refused with "ask your Thunai admin to link your account".
- **Roles** are Thunai's, not Microsoft's. The same rules apply as in the PWA: technicians see only
  their own sessions, and the translation tools are for supervisors and admins.
- Every tool call is recorded (`copilot_calls`: tool, user, result, time). Admins see the usage in
  Admin → Integrations.

### 13.4 Safety: what is enforced and what is only instructed

**Enforced in Thunai's code**, whatever the agent does:
- unsafe requests that reach `startTroubleshooting` are refused;
- every procedure starts with LOTO, plus stored-air release for pneumatics and the pressure step for
  autoclaves;
- no step contains a bypass instruction;
- steps come only from plant data, with source references;
- authorised-only badges;
- part numbers only from the catalogue;
- logs carry the signed-in person.

**Only instructed** (`copilot/agent-instructions.md`). Microsoft's model writes the chat, so Thunai
cannot guarantee that the agent:
- shows the steps unchanged and one at a time;
- adds no advice of its own;
- calls `checkSafety`;
- translates faithfully.

Mitigations:
- **Copilot Studio settings.** General knowledge and web search off; only Thunai's tools.
- **Safety and quality test** (`copilot/TEST-SCRIPT.md`). Run it in Teams before go-live, after
  every agent change and monthly. It includes the 10 refusal prompts; all 10 must pass.
- **Transcript review.** Supervisors review conversations in Copilot Studio analytics during the pilot.
- **Thunai's record is the authority.** Logs and step results are stored by Thunai, not taken from
  the chat.

**CONFIRM:** the plant safety officer accepts this split before the pilot.

### 13.5 Hosting, network and data location

Copilot Studio calls the connector from Microsoft's cloud, so it must reach Thunai over HTTPS with a
publicly trusted certificate. Two options:
- **On-premises data gateway (recommended).** Thunai stays on the plant network. Custom connectors
  can route through the gateway.
- **Public HTTPS endpoint** behind Eaton's reverse proxy or API gateway, limited to the
  `/api/copilot` path.

Either way, the Thunai server needs outbound HTTPS to `login.microsoftonline.com` to fetch the token
signing keys. **CONFIRM** both with Eaton IT.

Data location (replaces question 6):
- The database, audio and PWA photos stay on the plant server.
- Chat messages and photos sent in Teams are processed by Microsoft 365 under Eaton's tenant
  agreement.
- Tool answers (machine facts, steps, log text) pass through Microsoft's service to the agent.
- Nothing is sent to Anthropic.

### 13.6 Licensing and cost

According to Microsoft's billing FAQ:
- use by people with a Microsoft 365 Copilot licence is not billed to the agent;
- other users of an agent built in Copilot Studio consume Copilot Credits, through capacity or
  pay-as-you-go with an Azure subscription;
- an agent that only uses its instructions or public websites is not billed.

Thunai's agent calls Thunai's tools, so expect credits for unlicensed users. The Claude cost table
(section 9) no longer applies. Thunai itself has no per-call AI cost.

**CONFIRM** the licence model and monthly credit estimate with Eaton IT and Microsoft.

### 13.7 Languages

Copilot Studio says that agents using generative orchestration answer in the user's language and can
switch languages turn by turn. One of its FAQ pages still says "English only". Whether Tamil is
supported is not confirmed.

Thunai returns Tamil text for its own steps and questions wherever it has it:
- fault cards;
- safety steps;
- tap questions.

The agent is told to show that text and to translate only what has no Tamil version.

**CONFIRM** Tamil on Microsoft's language-support page and with 30 native-reviewed answers, as in
section 10. If Tamil is not good enough, technicians keep the PWA for Tamil.

### 13.8 Data model (migration 0004)

| Table | Change |
|---|---|
| users | + `entra_upn` (unique, lower case), + `entra_oid` (unique) |
| ai_sessions | + `channel` (`app` or `copilot`), + `observations` (photo readings sent by the agent) |
| copilot_calls | new: operation, user_id, status_code, ok, duration_ms, created_at |
| log_media | − `observation`, `observed_at`, `observation_model` (PWA photo reading removed) |

New environment variables:
- `COPILOT_ENABLED` (false);
- `ENTRA_TENANT_ID`;
- `ENTRA_AUDIENCE`;
- `ENTRA_SCOPE` (`Thunai.Use`);
- `COPILOT_TEAMS_URL` (optional link shown on the PWA home screen).

Removed environment variables:
- `ANTHROPIC_API_KEY`;
- `AI_MODEL_*`, `AI_EFFORT_*`;
- `AI_PRICES`;
- `AI_PHOTOS`;
- `AI_REFUSAL_FALLBACK`;
- `AI_TIMEOUT_S`.

`AI_PROVIDER` accepts only `rules`.

### 13.9 Risks

| Risk | Mitigation |
|---|---|
| The agent changes or adds to a step | Instructions; general knowledge off; `display` text to show unchanged; test script; transcript review; Thunai's stored steps are the record |
| Unsafe request phrased so that it never reaches a tool | Instructions; Copilot's own content filters; refusal prompts in the test script (must be 10/10) |
| Tamil quality or support | Thunai sends its own Tamil text; native review; PWA fallback |
| Wrong person on a log | Entra token checks; admin-controlled linking; binding to the object ID |
| Thunai exposed to the internet | Data gateway preferred; only `/api/copilot` published; HTTPS; tokens checked on every call |
| Licence cost | Measure Copilot Credits in the pilot (13.6) |
| No offline use in Teams | Technicians log in the PWA when the network is down; it syncs later |
| Photo readings wrong | The agent is told to pass only clearly legible values. Readings are evidence only, and steps still ask the technician to check |

**Not verified here:** Thunai was not tried in a real Copilot Studio tenant. The tool API, the token
checks (with test-signed tokens) and the OpenAPI file are tested in code. The agent's behaviour must
be tested in Eaton's tenant with `copilot/TEST-SCRIPT.md`.
