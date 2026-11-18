# Nudge runbook: going live and running it

This takes you from the demo to your own Nudge on your phone, with Claude, e-mail digests and push
reminders. Allow about an hour the first time.

## 1. What you need

- **A small always-on machine with Docker**: a cloud VM (2 vCPU, 4 GB RAM is comfortable), a home
  server, or a mini PC. With `WHISPER_MODEL=base.en`, 2 GB RAM is enough.
- **HTTPS your phone trusts.** Push notifications, the microphone and offline mode all need it. Pick one:
  - **A domain name** (e.g. `nudge.yourname.in`) pointing at the server, with ports 80 and 443
    open. Caddy fetches a free certificate automatically. This is the easiest option.
  - **A private network** such as Tailscale, with Tailscale's HTTPS certificates or Caddy's own
    certificate installed on your phone (see 3b).
- **An Anthropic API key** for Claude (console.anthropic.com → API keys). This is optional: without
  it, the built-in rules understand notes.
- **An e-mail account to send from** for the daily digest (Gmail with an App Password works).

## 2. Install

```bash
git clone <this repo> && cd <repo>/nudge
cp .env.example .env
nano .env        # fill in the sections below
docker compose up -d
docker compose logs -f whisper   # first start downloads the speech model (~500 MB), then "Whisper model ready"
```

The important `.env` lines:

| Setting | What to put |
|---|---|
| `SEED_SAMPLE_DATA=false` | Start empty instead of with demo tasks |
| `INITIAL_PIN=` | Your PIN (4–8 digits), or leave empty and choose it on first open |
| `PUBLIC_BASE_URL` | `https://nudge.yourname.in` (used for links in e-mails) |
| `SITE_ADDRESS` / `CADDY_TLS` | Your domain, and your e-mail address (for the free certificate) |
| `AI_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` | Turns on Claude |
| `SMTP_*`, `DIGEST_TO` | E-mail digest (section 6) |
| `VAPID_SUBJECT` | `mailto:` plus your real e-mail address (push services contact this if something goes wrong) |

After changing `.env`, apply it with `docker compose up -d`.

**Already ran the demo?** Remove the demo tasks with
`docker compose exec api python -m app.cli clear-sample`, and change the demo PIN in
Settings → Security (or `docker compose exec api python -m app.cli set-pin 4321`).

## 3. HTTPS

**3a. With a domain (recommended).** Point the domain's A record at the server, open ports 80 and
443, and set:

```
SITE_ADDRESS=nudge.yourname.in
CADDY_TLS=you@example.com
PUBLIC_BASE_URL=https://nudge.yourname.in
```

**3b. Private network, using Caddy's own certificate.** Keep `CADDY_TLS=internal` and set
`SITE_ADDRESS` to the name you use on your network. Copy Caddy's root certificate and install it on
your phone:

```bash
docker compose cp web:/data/caddy/pki/authorities/local/root.crt ./nudge-root.crt
```

- **Android:** Settings → Security → Encryption & credentials → Install a certificate → CA certificate.
- **iPhone:** AirDrop or e-mail the file to yourself and open it. Then go to Settings → General →
  VPN & Device Management to install it, and Settings → General → About → Certificate Trust
  Settings to turn it on.

**3c. Your own certificate.** Put `cert.pem` and `key.pem` in `nudge/certs/` and set
`CADDY_TLS=/certs/cert.pem /certs/key.pem`.

## 4. Set up your phone

1. Open your Nudge address in **Chrome (Android)** or **Safari (iPhone)** and enter your PIN.
2. Install it:
   - **Android:** use the menu → **Install app**.
   - **iPhone:** tap Share → **Add to Home Screen**, then open Nudge from the new icon. iPhone only
     allows notifications for apps opened from the Home Screen (iOS 16.4 or newer).
3. Go to **Settings → Notifications on this device → Turn on**, allow notifications, and tap **Test**.
4. Allow the microphone the first time you tap the mic.
5. On your laptop, open the same address and turn notifications on there too if you like. Each
   device gets reminders.

Notification buttons: Android and desktop show **Done / Snooze 1h / Tomorrow** (or **I've nudged /
Tomorrow** for follow-ups) right on the notification. iPhone doesn't show buttons on web
notifications; tapping opens the task.

## 5. Claude

1. Create a key at console.anthropic.com → API keys, and add billing.
2. In `.env`: `AI_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=sk-ant-...`, then `docker compose up -d`.
3. Check **Settings → Voice and AI**. It should say **Claude**, and after a few notes it shows this
   month's requests and cost.

**Cost.** Nudge uses `claude-opus-5-5` at low effort. A typical note is around 1,500–4,000 input
tokens (the instructions plus your open-task titles) and a few hundred output tokens, so roughly 1–3
US cents per note at list price. Settings shows your real spend. For a cheaper option, set
`AI_MODEL=claude-haiku-5-5`; it's much cheaper per note but less capable with messy, run-on notes.

**Privacy.** With Claude on, each note's text is sent to Anthropic's API along with today's date,
your basket names, people's names you've used, and the titles of your open tasks. Recordings never
leave your server; only the transcribed text is sent. Without a key, nothing leaves your server
except push notifications and e-mails.

## 6. E-mail digest

**Gmail:** turn on 2-Step Verification, then Google Account → Security → **App passwords** → create
one called "Nudge". In `.env`:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=<the 16-character app password>
SMTP_FROM=you@gmail.com
SMTP_SECURITY=starttls
DIGEST_TO=you@gmail.com
```

**Company mail:** ask IT for the SMTP host, port and an account (use `SMTP_SECURITY=ssl` for port 465).

Then go to **Settings → E-mail digest → Send now**. If it fails, the reason is listed under
**Recent notifications**. The morning e-mail is on by default; the evening one is off (turn it on
in Settings).

## 7. Daily rhythm (defaults, all changeable in Settings)

| Time | What happens |
|---|---|
| 07:30 | Morning briefing: push and e-mail (what's due, overdue, Top 3, who to follow up with, what's gone quiet) |
| 10:00 | Follow-up nudges for "waiting on" items that are due |
| 12:30 | Overdue check (only if something is overdue) |
| due time | A reminder for each task with a time |
| 18:30 | Evening wrap-up (Sundays: "your weekly review is ready") |
| 21:30–07:00 | Quiet hours: reminders and nudges wait |
| 02:00 | Database backup |

## 8. Backups and restore

Nudge backs up its database every night at 2 AM and keeps the last 14. In **Settings → Your data**
you can **Back up now** and download any backup, or **Export everything to Excel**.

Copy the backups off the server now and then:

```bash
docker compose cp api:/data/backups ./backups
```

To restore a backup:

```bash
docker compose stop api
docker compose cp ./backups/nudge-2026-11-18-020000.sqlite api:/data/nudge.db
docker compose start api
```

To move to a new server, copy the latest backup across, run section 2 there, then restore.

## 9. Updating

```bash
git pull
docker compose up -d --build
```

Your data, the speech model and certificates live in Docker volumes and are kept.

## 10. Troubleshooting

| Problem | Check |
|---|---|
| Voice says "isn't available" | `docker compose logs whisper`. On first start, wait for "Whisper model ready". The server needs internet access to download the model once. On a small server use `WHISPER_MODEL=base.en`. |
| Notes are understood by "built-in rules" | Settings → Voice and AI. If Claude is configured but failing, the review screen says so; check `ANTHROPIC_API_KEY` and billing. |
| No notifications | Must be HTTPS your phone trusts (section 3). On iPhone, open Nudge from the Home Screen icon. Check that notifications are allowed for the app/browser, look at Settings → **Recent notifications** (it shows "no devices" or the error), and check quiet hours. |
| No e-mails | Settings → Recent notifications shows the SMTP error. "Saved to outbox" means `SMTP_HOST` isn't set. |
| Forgot the PIN | `docker compose exec api python -m app.cli set-pin 4321` (logs out all devices). |
| Locked out after wrong PINs | Wait 5 minutes (30 after ten wrong tries). |
| The app looks out of date after an update | Close and reopen it. The new version installs itself in the background. |

Logs: `docker compose logs -f api` (reminders and digests show as `scheduler: {...}`).

## 11. Security notes

- One user, one PIN. Sessions last 90 days per device (sliding) and can be ended with Log out.
- The API refuses changes without the `X-Nudge` header, in addition to its same-site cookies.
  Caddy adds HSTS, a strict Content-Security-Policy and a microphone-only Permissions-Policy.
- Notification buttons carry a signed token that is valid for 7 days and only for that task.
- The data stays in the `data` Docker volume on your server. Back it up (section 8).
