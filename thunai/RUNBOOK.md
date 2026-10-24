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

Admin → Users → Add user: employee ID, name, role, zone, language, 4-digit PIN. Supervisors need a
phone number for the "Call" button. Reset a PIN with the **PIN** button. Five wrong PINs lock an
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

## 8. AI and speech settings

- **Models:** `AI_MODEL_DIAGNOSIS` (procedures, questions) and `AI_MODEL_EXTRACTION` (voice-log
  extraction, translation, classification, explanations). Change in `.env`, then
  `docker compose up -d`.
- **Prompts:** in `backend/prompts/<name>.v<N>.md`. To try a change, copy to the next version
  (`troubleshoot.v2.md`), set `PROMPT_VERSIONS=troubleshoot=v2`, rebuild, and run the evaluation
  (`docker compose exec api python -m eval.run_eval`). Each AI call records its prompt version.
- **Cost:** Admin → AI usage shows calls, tokens and cost by purpose for the last 30 days, and the
  cost per 100 sessions. Prices per model are in `AI_PRICES` (USD per million tokens).
- **Safety rules** are in `backend/app/safety.py` and cannot be switched off by settings. Any change
  there must keep `tests/test_safety.py` and the safety evaluation at 100%.
- **Speech:** `STT_PROVIDER=openai_compat` with `STT_BASE_URL` pointing at any server that offers the
  OpenAI-style `/audio/transcriptions` endpoint, for example a self-hosted Whisper server on the
  plant network (audio never leaves the site). `STT_PROVIDER=sarvam` with `SARVAM_API_KEY` uses
  Sarvam AI. Benchmark on 20 real recordings before choosing (SPEC.md, question 8).

## 9. Going live checklist

- [ ] Eaton IT approval: hosting, data location (SPEC.md questions 5 and 6).
- [ ] `.env` filled: `ENVIRONMENT=production`, new `SECRET_KEY` and `POSTGRES_PASSWORD`,
      `SEED_SAMPLE_DATA=false`, real `SITE_ADDRESS` and `PUBLIC_BASE_URL`.
- [ ] Started on an **empty** database (if you ran the demo, `docker compose down -v` first:
      this deletes the demo data and volumes).
- [ ] First admin created; real machines imported; QR stickers printed and fixed.
- [ ] Users created with their zone and language; supervisors have phone numbers.
- [ ] Shift calendar and planned hours checked in Admin → Settings (SPEC.md questions 1 and 2).
- [ ] Glossary extended with plant terms and spoken forms.
- [ ] Root certificate installed on phones (if `CADDY_TLS=internal`).
- [ ] Evaluation run with the real model and real cases; results in EVAL.md.
- [ ] Backups copied off the server daily.
- [ ] Alarm lists and key manuals uploaded for the pilot machines (section 11.2).
- [ ] Supervisors know the review queue: logs, fault-card drafts, flagged cards, tips (section 11.1).

## 10. Troubleshooting

| Symptom | Check |
|---|---|
| Site does not open | `docker compose ps`; `docker compose logs web api` |
| "Network" errors on phones | Phone on plant Wi-Fi? `SITE_ADDRESS` resolves to the server? Certificate trusted? |
| Mic or camera button does nothing | Page must be HTTPS with a trusted certificate; allow the permission in Chrome site settings |
| Logs stay "Waiting to send" | Phone offline or logged out; open the app online and tap "Send now" |
| No English/Tamil versions on new logs | `docker compose logs worker`; AI key valid? Admin → AI usage shows failed calls |
| "Thunai could not make a safe procedure" | The AI failed twice or produced unsafe text. See Admin → AI usage and `docker compose logs api` |
| Locked user | Admin → Users → PIN (reset unlocks) |
| Disk filling up | `docker system df`; old backups in `backups/`; audio retention setting |
| No fault cards appear | Cards are drafted after logs are translated and classified; check `docker compose logs worker` and the similar-logs threshold in Admin → Settings |
| A document shows "stored (no text)" | It is a scan or image without a text layer; it is listed for technicians but not read by the AI |

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
