# Thunai runbook

For the in-house team that installs and runs Thunai. All commands run in the `thunai/` folder on
the server unless noted.

## 1. Install on a plant server

Needs: Linux server (pilot: 2 vCPU, 4 GB RAM, 50 GB disk), Docker Engine with Compose v2.24+,
a DNS name on the plant network (for example `thunai.plant.local`), and approval from Eaton IT
(SPEC.md, open questions 4 and 6).

```bash
git clone <repository> && cd <repository>/thunai
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # paste into POSTGRES_PASSWORD
nano .env        # SITE_ADDRESS, PUBLIC_BASE_URL, AI and speech settings, SEED_SAMPLE_DATA=false
docker compose up -d --build
docker compose ps                                   # all services "Up", api "healthy"
docker compose exec api python -m app.cli create-admin --employee-id E1001 --name "Your Name" --pin 4821
```

Open `https://<SITE_ADDRESS>` on a phone, log in as the admin, then add machines and users
(sections 3 and 4).

`POSTGRES_PASSWORD` is used when the database volume is first created. To change it later,
change it inside PostgreSQL as well (`ALTER USER thunai PASSWORD '...'`).

## 2. HTTPS for phones

Phones only allow the microphone and camera on HTTPS. Pick one option in `.env`:

| `CADDY_TLS` | When | What to do |
|---|---|---|
| `internal` (default) | No certificate from IT | Caddy creates its own certificate authority. Install its root certificate on every phone and tablet once (below). |
| `/certs/cert.pem /certs/key.pem` | IT issues a certificate for `SITE_ADDRESS` | Put the files in `thunai/certs/` and restart `web`. |
| an e-mail address | Server reachable from the internet with a public DNS name | Caddy gets a Let's Encrypt certificate automatically. |

Install Caddy's root certificate on Android:

```bash
docker compose cp web:/data/caddy/pki/authorities/local/root.crt ./thunai-root.crt
```

Copy `thunai-root.crt` to the phone, then Settings → Security → Encryption & credentials → Install a
certificate → CA certificate. (Menu names vary by brand.) Then open the site in Chrome and choose
"Add to Home screen" / "Install app".

## 3. Adding machines

- **Many at once:** Admin → Import → Machine master → download the template, fill one row per
  machine, upload. Existing machine numbers are updated; new ones are created with a QR code.
  The upload result lists rows with errors (row number and reason).
- **One machine:** Admin → Machines → Add machine.
- **Machine type** groups identical machines: logs and fault cards from one machine help the others.
- **Components** (with part numbers) can be added through the API
  (`POST /api/machines/{no}/components`, see `/api/docs`). The AI uses their exact names.
- **QR stickers:** Admin → Machines → Print QR stickers → pick a zone → Print. Each code opens
  `PUBLIC_BASE_URL/m/<machine number>`, so set `PUBLIC_BASE_URL` correctly before printing.
- Machines are never deleted. Set them inactive (Admin → Machines → Active/Inactive).

## 4. Adding users

Admin → Users → Add user: employee ID, name, role, zone, language, 4-digit PIN, and their Microsoft
account if they will use Thunai in Teams (section 13.1). Supervisors need a phone number for the
"Call" button. Reset a PIN with the **PIN** button. Five wrong PINs lock an
account for 15 minutes; a PIN reset unlocks it. Users are never deleted: use **Deactivate**.

Shared tablets: tick "Shared phone or tablet" at login. The app logs out after each finished
session or log and after 10 idle minutes.

## 5. Importing historical breakdowns

Admin → Import → Historical breakdowns → template → upload. Columns are matched by name (for example
"Machine No", "Date", "Start Time", "End Time", "Problem", "Root Cause", "Action Taken",
"Spares Used"). Dates may be `2026-10-12`, `12-10-2026` or Excel dates. Overnight times
(22:30 → 00:10) are handled. Tick "Mark as verified" for the official register. Imported logs are
translated and classified by the worker in the background; check progress with
`docker compose logs -f worker`.

## 6. Backups and restore

The `backup` service writes `backups/thunai-YYYYMMDD-HHMM.dump` once at start and then every night
at `BACKUP_HOUR` (plant time). Dumps older than `BACKUP_KEEP_DAYS` (14) are deleted. **Copy the
`backups/` folder to another machine or network share every day**; a backup on the same disk does
not survive a disk failure.

Check: `docker compose logs backup | tail` shows "backup written" with a size.

Restore (tested on this build):

```bash
docker compose stop api worker
docker compose exec -T db dropdb -U thunai thunai
docker compose exec -T db createdb -U thunai thunai
docker compose exec -T db pg_restore -U thunai -d thunai --no-owner < backups/thunai-YYYYMMDD-HHMM.dump
docker compose start api worker
```

To test a backup without touching live data, restore into a scratch database
(`createdb -U thunai thunai_restore_test`, restore, count rows, `dropdb`).

Audio and photos live in the `thunai_media` volume (audio is deleted after the retention period;
the database row stays). Back it up with:

```bash
docker run --rm -v thunai_media:/media -v "$PWD/backups":/out alpine tar czf /out/media-$(date +%F).tgz -C /media .
```

## 7. Updating

```bash
git pull
docker compose up -d --build
```

The API applies database migrations at start (`alembic upgrade head`). Take a backup first
(`docker compose restart backup` writes one immediately).

## 8. Rules engine, Copilot and speech settings

- **No model API.** The Thunai server runs its rules engine only (`AI_PROVIDER=rules`). It builds
  steps from fault cards, logs, alarm lists, the alarm feed, tips and manuals. The Claude adapter
  was removed on 25 Oct 2026 (SPEC.md section 13). An old `.env` with `AI_PROVIDER=anthropic` stops
  the API at start with a message saying so; set `AI_PROVIDER=rules` and delete the `ANTHROPIC_*`,
  `AI_MODEL_*`, `AI_EFFORT_*`, `AI_PRICES` and `AI_PHOTOS` lines.
- **Microsoft Copilot:** set up with [copilot/SETUP.md](copilot/SETUP.md); operations in section 13.
- **Prompts** (`backend/prompts/`) are kept for a model adapter Eaton may approve later; the rules
  engine does not read them. After changing the rules, run the evaluation
  (`docker compose exec api python -m eval.run_eval`).
- **Safety rules** are in `backend/app/safety.py` and cannot be switched off by settings. Any change
  there must keep `tests/test_safety.py` and the safety evaluation at 100%.
- **Speech:** `STT_PROVIDER=openai_compat` with `STT_BASE_URL` pointing at any server that offers the
  OpenAI-style `/audio/transcriptions` endpoint, for example a self-hosted Whisper server on the
  plant network (audio never leaves the site). `STT_PROVIDER=sarvam` with `SARVAM_API_KEY` uses
  Sarvam AI. Benchmark on 20 real recordings before choosing (SPEC.md, question 8).

## 9. Going live checklist

- [ ] Eaton IT approval: hosting, network path for Copilot, data location (SPEC.md question 5 and 13.5).
- [ ] `.env` filled: `ENVIRONMENT=production`, new `SECRET_KEY` and `POSTGRES_PASSWORD`,
      `SEED_SAMPLE_DATA=false`, real `SITE_ADDRESS` and `PUBLIC_BASE_URL`.
- [ ] Started on an **empty** database (if you ran the demo, `docker compose down -v` first:
      this deletes the demo data and volumes).
- [ ] First admin created; real machines imported; QR stickers printed and fixed.
- [ ] Users created with their zone and language; supervisors have phone numbers.
- [ ] Shift calendar and planned hours checked in Admin → Settings (SPEC.md questions 1 and 2).
- [ ] Glossary extended with plant terms and spoken forms.
- [ ] Root certificate installed on phones (if `CADDY_TLS=internal`).
- [ ] Evaluation run with real cases (`eval.run_eval`); results in EVAL.md.
- [ ] Copilot set up (copilot/SETUP.md); pilot people have their Microsoft account in Admin → Users.
- [ ] copilot/TEST-SCRIPT.md run in Teams: safety 13/13; safety officer signed off (SPEC 13.4).
- [ ] Backups copied off the server daily.
- [ ] Alarm lists and key manuals uploaded for the pilot machines (section 11.2).
- [ ] Supervisors know the review queue: logs, fault-card drafts, flagged cards, tips (section 11.1).
- [ ] Spare-parts stock imported, or its sync running (section 12.3); `machine_type` filled so
      parts show for the right machines.
- [ ] One integration key per connected system, with only the scopes it needs (section 12.1).
- [ ] HR has agreed how the Skills page is used (SPEC.md 12.5).

## 10. Troubleshooting

| Symptom | Check |
|---|---|
| Site does not open | `docker compose ps`; `docker compose logs web api` |
| "Network" errors on phones | Phone on plant Wi-Fi? `SITE_ADDRESS` resolves to the server? Certificate trusted? |
| Mic or camera button does nothing | Page must be HTTPS with a trusted certificate; allow the permission in Chrome site settings |
| Logs stay "Waiting to send" | Phone offline or logged out; open the app online and tap "Send now" |
| No English/Tamil versions on new PWA logs | Expected: Thunai does not translate. A supervisor asks the Teams agent to translate them (section 13.3) |
| "Thunai could not make a safe procedure" | The rules engine produced no usable steps. See `docker compose logs api` |
| Locked user | Admin → Users → PIN (reset unlocks) |
| Disk filling up | `docker system df`; old backups in `backups/`; audio retention setting |
| No fault cards appear | Cards are drafted after logs are translated and classified; check `docker compose logs worker` and the similar-logs threshold in Admin → Settings |
| A document shows "stored (no text)" | It is a scan or image without a text layer; it is listed for technicians but cannot be searched |
| Machine alarm does not pre-fill | Admin → Integrations: key active and "last used" recent? Alarm older than `alarm_prefill_hours` or already cleared? Machine number in the alarm must match Thunai's exactly |
| The Teams agent says Thunai cannot be reached | See the troubleshooting table in copilot/SETUP.md, and Admin → Integrations → Microsoft Copilot → Recent errors |
| A part on a step shows no stock | The step's part number is not in the catalogue, or the part is inactive. Import the stock list (section 12.3) |

API errors are logged by `docker compose logs api`. Every data change is in Admin → Audit.

## 11. Knowledge base (Phase 2)

### 11.1 Fault cards
- The worker drafts a card when `similar_logs_threshold` (default 3) closed or verified logs describe
  the same symptom on one machine, or on machines of the same type. Similarity uses the AI's symptom
  category or keyword similarity above `similarity_cutoff` (Admin → Settings).
- Supervisors open **Review → Fault cards to review**. Check every cause and step against the source
  logs listed under the card, edit if needed, then **Approve**. **Reject** a draft that is wrong
  (it is not drafted again until enough new similar logs arrive). **Retire** a card that no longer
  applies. Nothing is deleted; every action is in Admin → Audit.
- **Needs review:** a new log whose root cause is not among an approved card's causes flags the card.
  It stays in use, marked, until a supervisor approves it again, edits it, or uses **Re-draft from
  logs** (the old card stays live until the new draft is approved; the version number goes up and the
  old content is kept under "Earlier versions").
- The AI never adds LOTO steps to cards; the app adds safety steps in front of every procedure.

### 11.2 Documents and alarm lists
- **Admin → Documents** (admins and supervisors through the API): upload PDF manuals, SOPs, drawings,
  text files or alarm lists for one machine or for a machine type (shared by all machines of that
  type). Max 50 MB per file (`MAX_DOCUMENT_MB`).
- PDF text is read page by page. A scanned PDF or an image is kept and listed on the machine page but
  marked "stored (no text)": the AI cannot read it.
- **Alarm lists:** Excel or CSV with an `alarm_code` column and optional `message`, `cause`,
  `remedy`, `machine_no`, `machine_type` columns (download the template on the Documents tab). A
  newer list replaces the same codes from an older one. When a technician types an alarm code in
  Ask Thunai, its meaning shows at once and the AI uses it as evidence (`ALM-<code>`).
- Deactivate a document to stop its use; its alarm codes are deactivated with it.

### 11.3 Expert tips
Technicians add tips on the machine page (voice or text). Supervisors approve or reject them (with a
reason) in the review queue. Approved tips show on the machine page and the AI uses them like verified
logs.

### 11.4 Dashboard
Supervisors and admins open **Dashboard** from the home screen: period 7 / 30 / 90 days and a zone
filter. **Excel** downloads the same tables for the monthly MIS.

### 11.5 Optional embeddings
Keyword similarity is the default. To add vector similarity, run an embeddings server with an
OpenAI-style `/embeddings` endpoint on the plant network, set `EMBEDDINGS_PROVIDER=openai_compat`,
`EMBEDDINGS_BASE_URL` and `EMBEDDINGS_MODEL` in `.env`, restart, then fill the vectors once:

```bash
docker compose exec api python -m app.cli reindex
```

New logs, cards, tips and documents are embedded by the worker from then on. If the server is down,
search falls back to keywords. Changing the model needs another `reindex`.

## 12. Integration, photos and skills (Phase 3)

PM system links and SAP integration are out of scope (owner decision, SPEC.md section 12). The API
reference for what follows is at `https://<SITE_ADDRESS>/api/docs` (section "integrations").

### 12.1 Integration keys
Admin → Integrations. Make one key per connected system (SCADA or PLC gateway, stores system) and tick
only what it needs:
- **alarms:** post PLC or SCADA alarms;
- **parts:** update spare-parts stock.

The key is shown once; Thunai stores only its hash. Lost key: deactivate it and make a new one.
"Last used" shows whether the system is still sending.

### 12.2 PLC / SCADA alarm feed
Whatever the SCADA, historian or gateway (OPC UA, Modbus bridge, Node-RED…), it sends HTTPS POSTs
like this. The machine number must match Thunai's exactly.

```bash
curl -X POST https://thunai.plant.local/api/integrations/alarms \
  -H "X-Thunai-Key: thn_..." -H "Content-Type: application/json" \
  -d '{"events": [{"machine_no": "SF-01", "code": "A101", "message": "CYL NOT HOME",
                   "raised_at": "2026-10-24T09:42:10+05:30", "event_id": "scada-778812"}]}'
```

- Send the same event again with `cleared_at` when it clears.
- Repeats are ignored, so it is safe to resend.
- The newest alarm that is not cleared and is younger than `alarm_prefill_hours` (Admin → Settings,
  default 8) fills the alarm code in Ask Thunai and New log; a new log also gets it as the downtime
  start.
- No alarm opens a log by itself.

### 12.3 Spare parts and stock
- **File:** Admin → Import → *Spare parts and stock*: Excel or CSV (comma or semicolon), template on the
  same card.
  - Columns: part number, description, stock, minimum, storage bin, and `machine_type` or
    `machine_no` so the part shows for those machines.
  - Common export headings ("Material", "Unrestricted", "Storage bin") are recognised.
- **API:** `PUT /api/integrations/parts` takes the same fields as JSON, up to 1,000 rows per call. A
  nightly job from the stores system keeps it current.
- **Matching:** rows are matched by part number. Parts missing from a file are left as they are;
  deactivate a part in the API (`PATCH /api/admin/parts/{id}`) if it is no longer stocked.
- **Read-only:** Thunai never changes stock. Each part shows its stock with the "as of" time of the
  last update.
- **On steps:** a step shows stock only when its text contains the exact catalogue part number, so
  part numbers on fault cards should be written exactly.

### 12.4 Photos
- **In Teams:** the agent reads photos and sends Thunai the readings, never the photo (SPEC 13.1).
  They show in the session's evidence as `PHOTO-1`, `PHOTO-2`.
- **In the PWA:** photos are attachments to the session and log; nothing reads them.
- **Training:** tell technicians not to photograph people.

### 12.5 Skills page
Supervisors (their zone) and admins open **Skills** from the home screen.
- **What it shows:** who has fixed what by machine type, machine types only one person can fix,
  pairing suggestions, and authorised-only steps that could not be done.
- **Minimum events:** figures with fewer than `skill_min_events` events (Admin → Settings, default 3)
  show "–".
- **Purpose:** training and shift planning; agree its use with HR before the pilot.

## 13. Microsoft Copilot

Set-up for Eaton IT is in [copilot/SETUP.md](copilot/SETUP.md). The design and its limits are in
SPEC.md section 13. Day to day:

### 13.1 People
- **New person.** In Admin → Users, enter their Microsoft account (for example `name@eaton.com`). It
  shows "not used yet" until their first sign-in in Teams binds it ("linked").
- **Someone leaves, or changes account.** Deactivate the user, or change the Microsoft account:
  changing it unbinds the old one.
- **Roles** (technician, supervisor, admin) are Thunai's own, as in the PWA.

### 13.2 Monitoring
**Admin → Integrations → Microsoft Copilot** shows, for the last 30 days:
- the set-up state;
- accounts entered and used;
- tool calls per tool;
- sessions started in Teams;
- recent errors.

What the errors mean:
- **401:** the token was refused. The API log line `Copilot token refused:` gives the reason.
- **403:** the account is not linked, the user is inactive, or the role is not allowed.
- **404:** an unknown machine.

Conversation transcripts are in Copilot Studio → Analytics. Supervisors should read a sample every
week during the pilot.

### 13.3 Translations
Thunai does not translate. Logs typed or spoken in the PWA keep only their original language until
a supervisor asks the Teams agent, for example "translate the logs that need English".

The agent then:
1. lists the texts (`listLogsToTranslate`, own zone only);
2. translates them;
3. saves them (`saveTranslations`).

Only empty versions are filled. The technician's words are never changed, and every save is in the
audit trail.

### 13.4 Changes
- **A tool changes in the code.** Regenerate the connector file:
  `docker compose exec api python -m app.cli copilot-spec --host … --tenant … --scope …`.
  Then update the custom connector (Power Apps → Custom connectors → Update from OpenAPI file), and
  refresh the tools in the agent.
- **The agent's instructions or tools change.** Run copilot/TEST-SCRIPT.md again before
  publishing.
- **The connector's client secret expires.** The Teams agent stops working. Renew the secret in
  Entra, then update it in the custom connector.

### 13.5 Switching Copilot off
Set `COPILOT_ENABLED=false` and run `docker compose up -d`. The agent's tools then answer "not set
up". The PWA keeps working.
