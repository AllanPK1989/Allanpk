# Nudge runbook: free, private setup

This gets Nudge running on a computer you own and onto your phone, at no cost, with no accounts,
API keys or subscriptions, and without your tasks leaving your machine. Allow about an hour the
first time.

## 1. What you need

- **A computer that stays on**, with Docker installed: a desktop, an old laptop, a mini PC, or a
  Raspberry Pi 4/5 with 4 GB RAM. On a small machine, use `WHISPER_MODEL=base.en`.
- **Your home Wi-Fi.** Your phone talks to Nudge over your own network.

That's it. Push reminders reach your phone anywhere, including away from home (section 4 explains
how).

## 2. Install

```bash
git clone <this repo> && cd <repo>/nudge
cp .env.example .env
nano .env        # at least: SEED_SAMPLE_DATA=false and SITE_ADDRESS (step 3)
docker compose up -d
docker compose logs -f whisper   # first start downloads the speech model (~500 MB), then "Whisper model ready"
```

Once you see "Whisper model ready", you can set `WHISPER_OFFLINE=1` in `.env` and run
`docker compose up -d` again. From then on the speech server never contacts the internet.

**Already ran the demo?** Remove the demo tasks with
`docker compose exec api python -m app.cli clear-sample`, and change the demo PIN in
Settings → Security (or `docker compose exec api python -m app.cli set-pin 4321`).

## 3. HTTPS on your home network

Phones only allow notifications, the microphone and offline mode over HTTPS. Nudge's built-in web
server (Caddy) makes its own certificate. You install it on your phone once, with no account and no
outside service.

1. Find the computer's address on your network: `hostname -I` on Linux (e.g. `192.168.1.20`), or
   look in your router's device list. Giving the computer a fixed address in your router settings
   stops it changing.
2. In `.env` set `SITE_ADDRESS=192.168.1.20` (your address) and keep `TLS_MODE=internal`, then run
   `docker compose up -d`.
3. Copy Caddy's root certificate out:
   ```bash
   docker compose cp web:/data/caddy/pki/authorities/local/root.crt ./nudge-root.crt
   ```
4. Install it on your phone:
   - **Android:** copy the file to the phone, then Settings → Security → Encryption & credentials →
     Install a certificate → CA certificate.
   - **iPhone:** AirDrop the file to the phone and open it. Then go to Settings → General → VPN &
     Device Management to install it, and Settings → General → About → Certificate Trust Settings
     to turn it on.
5. Open `https://192.168.1.20` on the phone. There should be no warning.

**Other options**, if you already have them:
- **A domain name pointing at the machine** (ports 80 and 443 open to the internet): set
  `SITE_ADDRESS=nudge.yourdomain.in` and `TLS_MODE=public`. Caddy gets a free Let's Encrypt
  certificate without asking for an e-mail. Note that registering a domain means giving your details
  to a registrar, and opening ports makes the login page reachable from the internet (the PIN lockout
  protects it).
- **Your own certificate:** put `cert.pem` and `key.pem` in `nudge/certs/` and set `TLS_MODE=files`.

## 4. Set up your phone

1. Open your Nudge address in **Chrome (Android)** or **Safari (iPhone)** and enter your PIN.
2. Install it:
   - **Android:** menu → **Install app**.
   - **iPhone:** Share → **Add to Home Screen**, then open Nudge from the new icon. iPhone only
     allows notifications for apps opened from the Home Screen (iOS 16.4 or newer).
3. Go to **Settings → Notifications on this device → Turn on**, allow notifications, and tap **Test**.
4. Allow the microphone the first time you tap the mic.

**Away from home:**
- Reminders and nudges still arrive. Your computer at home sends them through the phone's own push
  service, so the phone doesn't need to reach the computer.
- Tapping **Done / Snooze / Tomorrow** on a notification is saved on the phone and synced the next
  time it's on your Wi-Fi. (iPhone doesn't show these buttons on web notifications; tapping opens
  the app.)
- The app opens from its saved copy. Anything you add, close or record is kept on the phone and
  synced when you're home.
- To use Nudge fully from anywhere, you'd need a way to reach your home network: a VPN on your
  router, a domain (step 3), or a service such as Tailscale. Those involve setting up or signing up
  with a third party, so they're left to you.

## 5. E-mail digest (optional)

The digest is off unless you set it up, and push reminders cover the same ground. If you want it,
add your mail account's SMTP details to `.env`. Bear in mind the e-mail lists your tasks and passes
through that mail provider.

- **Gmail:** turn on 2-Step Verification, create an **App password** (Google Account → Security),
  then:
  ```
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=you@gmail.com
  SMTP_PASSWORD=<the 16-character app password>
  SMTP_FROM=you@gmail.com
  DIGEST_TO=you@gmail.com
  ```
- **Other providers:** use their SMTP host and port (`SMTP_SECURITY=ssl` for port 465).

These values stay in `.env` on your computer. `.env` is listed in `.gitignore`, so it isn't
committed to git. Test it with **Settings → E-mail digest → Send now**.

## 6. Daily rhythm (defaults, all changeable in Settings)

| Time | What happens |
|---|---|
| 07:30 | Morning briefing push (what's due, overdue, Top 3, who to follow up with, what's gone quiet) |
| 10:00 | Follow-up nudges for "waiting on" items that are due |
| 12:30 | Overdue check (only if something is overdue) |
| due time | A reminder for each task with a time |
| 18:30 | Evening wrap-up (Sundays: "your weekly review is ready") |
| 21:30–07:00 | Quiet hours: reminders and nudges wait |
| 02:00 | Database backup |

## 7. Backups and restore

Nudge backs up its database every night and keeps the last 14. In **Settings → Your data** you can
**Back up now**, download any backup, or **Export everything to Excel**. Copy the backups to a USB
drive now and then:

```bash
docker compose cp api:/data/backups ./backups
```

To restore a backup:

```bash
docker compose stop api
docker compose cp ./backups/nudge-2026-11-18-020000.sqlite api:/data/nudge.db
docker compose start api
```

## 8. Updating

```bash
git pull
docker compose up -d --build
```

Your data, the speech model and the certificate live in Docker volumes and are kept.

## 9. Troubleshooting

| Problem | Check |
|---|---|
| Voice says "isn't available" | `docker compose logs whisper`. On first start, wait for "Whisper model ready" (it needs internet once to download the model, so keep `WHISPER_OFFLINE=0` until then). On a small computer use `WHISPER_MODEL=base.en`. |
| A note was understood wrongly | Fix it on the review card before saving. Saying the date and person plainly helps ("on Friday", "with Ravi"). |
| Certificate warning on the phone | Install the root certificate (step 3), and open the same address you put in `SITE_ADDRESS`. |
| No notifications | Must be HTTPS your phone trusts (step 3). On iPhone, open Nudge from the Home Screen icon. Check that notifications are allowed, look at Settings → **Recent notifications** (it shows "no devices" or the error), and check quiet hours. |
| Read aloud does nothing | Nudge uses only voices built into your device. Install an offline English voice in the phone's text-to-speech settings. |
| Forgot the PIN | `docker compose exec api python -m app.cli set-pin 4321` (logs out all devices). |

Logs: `docker compose logs -f api` (reminders show as `scheduler: {...}`).

## 10. Privacy: what leaves your computer

| What | Where it goes |
|---|---|
| Your tasks, notes, people, history | **Nowhere.** They live in the `data` volume on your computer. |
| Voice recordings | **Nowhere.** They're turned into text on your computer and deleted straight away. |
| Understanding notes, follow-up messages | **Nowhere.** Both are built in, with no outside AI. |
| Read-aloud | **Nowhere.** Only voices built into your device are used; online voices are skipped. |
| Push reminders | Delivered through your phone's push service (Google for Android/Chrome, Apple for iPhone). The content is **encrypted end to end**, so they can't read it. |
| E-mail digest | Only if you set it up (section 5), through your own mail provider. |
| Speech model | Downloaded once from huggingface.co (no personal data is sent), with usage reporting switched off. Set `WHISPER_OFFLINE=1` afterwards. |
| Installing and updating | Docker, Python and Node packages are downloaded from their public registries. |

The app itself loads nothing from outside (no fonts, analytics or trackers), and the browser is told
to block any outside requests (Content-Security-Policy). The interactive API page is off by
default, because it loads scripts from a public CDN (turn it on with `API_DOCS=true` if you need it).

Other safeguards:
- The PIN locks for 5 minutes after five wrong tries, and for 30 after ten.
- Sessions can be ended with Log out.
- Notification buttons carry a signed token that is valid for 7 days and only for that task.
