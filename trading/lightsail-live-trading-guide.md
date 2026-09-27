# Nifty Shop on Amazon Lightsail: from zero to live trading

A step-by-step procedure to set up the Nifty Shop bot (`jev-shop/` on this branch) on an Amazon Lightsail server
in Mumbai, run it on paper, and then switch it to live trading on Firstock.

**What you end up with:** a small server in Mumbai that, every trading day at 15:18 IST, ranks the Nifty 50,
sells a holding that's 5% up, buys ₹5,000 of the most beaten-down stock you don't own (or averages one that has
fallen 3% more), skips stocks with serious bad news, and reports to your phone on Telegram. You log in once a
day by sending your 2FA code to your Telegram bot.

**Time:** about 2 hours of setup (Phases 1–6), then **4 to 8 weeks of paper trading** (Phase 7) before any real
money (Phase 8).

> Not financial advice. The strategy has **no stop-loss**: falling stocks get averaged, not sold, so money can
> sit in losers for months. Only commit money you can leave invested for a year or more.

---

## Costs

| Item | Per month |
|---|---|
| Lightsail **$5 plan with IPv4**, Mumbai (512 MB RAM, 2 vCPU, 20 GB SSD) | **Free for the first 3 months** (new accounts), then about ₹500 including 18% GST |
| Lightsail static IP | ₹0 while attached to the server (charged only if left unattached) |
| Automatic snapshots (backup, recommended) | about ₹80–100 |
| Firstock API, Telegram, Jev on Vercel's free tier | ₹0 (check Firstock's API page for any API charges) |
| **Trading costs** (separate) | No delivery brokerage on Firstock, but about ₹29 per ₹5,000 round trip (STT, stamp duty, exchange, DP charge, GST) |

Indian AWS accounts are billed in rupees by AWS India (AISPL), and you can pay by UPI AutoPay, RuPay, cards or
net banking.

---

## Phase 0 · Accounts to prepare (do these first, some take a day)

| # | What | Why | Notes |
|---|---|---|---|
| 0.1 | **Firstock trading account**, equity segment active | The broker | PAN, Aadhaar, bank account |
| 0.2 | **Authenticator-app 2FA (TOTP)** on Firstock | The API login needs the 6-digit code | In the Firstock app or website, switch on TOTP and scan the QR code with Google Authenticator or Microsoft Authenticator. Keep the QR/secret to yourself; never give it to anyone or any bot. |
| 0.3 | **DDPI** on your Firstock account | Without it, the bot's **sell** orders are rejected | Apply in Firstock's back office (online, usually with Aadhaar e-sign). Can take a few days; there may be a small fee. |
| 0.4 | **AWS account** with an Indian billing address | For Lightsail | aws.amazon.com → Create account. Then **switch on MFA** for the root user (IAM → Security credentials). |
| 0.5 | **Telegram** on your phone | Daily login, report, alerts | You'll create the bot in Phase 4 |
| 0.6 | **Vercel account** (free) | Lets Jev read headlines for the news check | vercel.com, sign up with GitHub or email |

---

## Phase 1 · Create the Lightsail server (Mumbai)

1. Open the **Lightsail console**: lightsail.aws.amazon.com → **Create instance**.
2. **Region:** click *Change AWS Region and Availability Zone* → **Mumbai (ap-south-1)**, zone A.
   (SEBI's rules want the trading server in India.)
3. **Image:** Platform **Linux/Unix** → **Operating system (OS) only** → **Ubuntu 24.04 LTS**.
4. **SSH key:** keep the **default key** for Mumbai (you'll download it in step 12 for laptop access).
5. **Plan:** under **Dual-stack** (not *IPv6-only*), choose the **$5 USD/month** plan (512 MB, 2 vCPU, 20 GB).
   The IPv6-only plans can't get the IPv4 static address Firstock needs.
6. **Name:** `jev-shop`. Click **Create instance**. Wait until it shows **Running** (1–2 minutes).
7. **Static IP (essential):** open the instance → **Networking** tab → **Attach static IP** → create one named
   `jev-shop-ip` → attach it. **Write this IP down.** It's the address you'll register with Firstock.
   (The default IP changes whenever the server stops and starts; the static IP never does, as long as you don't
   delete it.)
8. **Firewall:** still on **Networking**, under **IPv4 Firewall**, **delete the HTTP (80) rule**. Keep only **SSH (22)**.
   The bot needs no incoming connections at all.
9. **Switch IPv6 off:** on the same tab, turn **IPv6 networking** off for this instance, so every connection to
   Firstock comes from your static IPv4 address.
10. **Backups:** **Snapshots** tab → switch on **Automatic snapshots** (keeps the last 7 days). This protects the
    bot's trade record (`results/ledger-live.json`), which the strategy needs to know your buy prices.
11. Open a terminal on the server: **Connect** tab → **Connect using SSH**. A browser window opens, logged in as
    `ubuntu`. Phases 2–6 happen in this window. (To paste into it, use the clipboard icon at the bottom right.)
12. *(Optional, for the dashboard later)* Download the key: Lightsail → **Account** → **SSH keys** → download the
    default key for **Mumbai**. On your laptop (Mac/Linux): `mv ~/Downloads/LightsailDefaultKey-ap-south-1.pem ~/.ssh/ && chmod 400 ~/.ssh/LightsailDefaultKey-ap-south-1.pem`.

---

## Phase 2 · Prepare the server and install the bot

Paste these into the browser SSH window, one block at a time.

**2.1 Updates, git, India time, and a little swap (insurance for the 512 MB plan):**

```bash
sudo apt update && sudo apt -y upgrade && sudo apt -y install git
sudo timedatectl set-timezone Asia/Kolkata
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

If `apt upgrade` asks about restarting services or a config file, press Enter to accept the defaults.

**2.2 Install uv (it brings its own Python):**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
uv --version
```

**2.3 Download just the bot from GitHub, and install its libraries:**

```bash
cd ~
git clone --depth 1 --filter=blob:none --sparse -b claude/firstock-indian-trades-mntq9v https://github.com/AllanPK1989/Allanpk.git
cd Allanpk && git sparse-checkout set jev-shop && cd jev-shop
uv sync
```

**2.4 Create your settings file (only readable by you):**

```bash
cp .env.example .env && chmod 600 .env
```

**2.5 First check (no keys yet):**

```bash
uv run python -m jevlab check
```

Expect: *Firstock: not set up yet* (fine for now), *50 stocks from NSE*, headlines from the news feeds, and
*this machine's public IP is …*. **That IP must be the static IP from step 1.7.** Also run:

```bash
curl -s https://api64.ipify.org; echo
```

It must print the **same static IPv4**. If it prints an IPv6 address (with colons), go back to step 1.9.

> From here on, every command runs inside `~/Allanpk/jev-shop`. If you open a new SSH window, first run
> `cd ~/Allanpk/jev-shop`.

---

## Phase 3 · Firstock API key, registered to your static IP

1. On your laptop, open **firstock.in/api/docs** and sign in to generate an **API key**. Note your **vendor code**
   on the same page. (Labels on Firstock's site change; look for "API key" / "key generation".)
2. On the same developer page, register your **static IP from step 1.7** as the IP for this API key (SEBI's rule:
   API orders only from a registered static IP). Double-check it: changes are limited to about once a week.
   Activation can take a while.
3. Put your Firstock details in `.env` on the server:

   ```bash
   nano .env
   ```

   Fill in, after the `=` signs (no spaces, no quotes):

   ```
   FIRSTOCK_USER_ID=your client ID
   FIRSTOCK_PASSWORD=your Firstock login password
   FIRSTOCK_API_KEY=the API key
   FIRSTOCK_VENDOR_CODE=the vendor code
   ```

   Leave `FIRSTOCK_MODE=paper`, `BUY_AMOUNT_INR=5000`, `AVERAGE_AMOUNT_INR=5000`, `MAX_CAPITAL_INR=200000` as they
   are. Save with **Ctrl+O, Enter**, exit with **Ctrl+X**.

4. **First login** (this is the daily 2FA login; later you'll do it from Telegram):

   ```bash
   uv run python -m jevlab login
   ```

   Type the 6-digit code from your authenticator app. "Invalid TOTP" means the code expired: wait for the next one.
   A message about the IP means the static IP isn't active on your key yet: check step 3.2 and try later.

5. `uv run python -m jevlab check` again. The Firstock section should show your name, prices, and your cash.

---

## Phase 4 · Telegram bot (daily login, report, alerts)

1. In Telegram, open **@BotFather** → send `/newbot` → pick a name and a username ending in `bot` → copy the
   **token** it gives you. Treat it like a password.
2. `nano .env` → paste it after `TELEGRAM_BOT_TOKEN=` → save and exit.
3. In Telegram, open your new bot and send it any message ("hi").
4. On the server:

   ```bash
   uv run python -m jevlab telegram-id
   ```

   It prints your chat ID. `nano .env` → put that number after `TELEGRAM_CHAT_ID=` → save and exit.
5. `uv run python -m jevlab check`: section 4 should say *test message sent*, and the message arrives on your phone.

---

## Phase 5 · The news check with Jev

The news check is already on: red-flag words (fraud, SEBI ban, ED raid, insolvency, auditor quits…) work without
a key. Adding Jev makes it read each headline properly.

1. vercel.com/dashboard → **AI Gateway** → **API Keys** → **Create key** → copy it.
2. `nano .env` → paste after `AI_GATEWAY_API_KEY=` → save and exit.
3. `uv run python -m jevlab check`: section 3 should say *Jev reads each headline too*.
4. `uv run python -m jevlab news`: reads the feeds now and shows the watch-list (stocks the bot won't buy for 10
   days because of serious news).

It makes a few calls a day, so Vercel's free tier is enough.

---

## Phase 6 · Backtest, today's picks, and switch on the daily timers

1. **Backtest** (1–3 minutes the first time):

   ```bash
   uv run python -m jevlab backtest
   ```

   Read: buys, averages and sells; profit after charges; **the most money invested at once**; the worst drawdown;
   stocks still stuck at the end; and NIFTY's own return for comparison. It uses today's Nifty 50 for the whole
   period, so treat it as a **best case**.
2. **Today's picks** (any time, no orders): `uv run python -m jevlab scan`
3. **Switch on the timers:**

   ```bash
   sudo bash deploy/install.sh
   systemctl list-timers 'jev-*' --no-pager
   ```

   This installs:

   | Timer / service | When | What |
   |---|---|---|
   | `jev-news` | every hour, 07:05–23:05, every day | reads the news, keeps the watch-list, warns you if a stock you hold gets serious news |
   | `jev-remind` | 14:30, Mon–Fri | Telegram nudge if you haven't logged in yet |
   | `jev-shop` | **15:18, Mon–Fri** | the daily run: at most one sell and one buy |
   | `jev-telegram` | always | answers `/login`, `/status`, `/stop`, `/resume` |

4. Send `/status` to your bot. It should answer with the mode (**paper**) and your login state.

---

## Phase 7 · Paper trading, 4 to 8 weeks (don't skip this)

**Every trading day** (the only chore): before **15:15**, open your authenticator app and send your bot
`/login 123456` (your current code). The message with the code is deleted automatically. At about **15:20**
you get the day's report. If you forget to log in, the bot simply skips that day and tells you.

**Each week:**
- `/status`, or on the server: `uv run python -m jevlab report` (holdings, open P&L, profit booked)
- The dashboard, from your laptop (needs the key from step 1.12):

  ```bash
  ssh -i ~/.ssh/LightsailDefaultKey-ap-south-1.pem -L 8765:127.0.0.1:8765 ubuntu@YOUR_STATIC_IP "cd ~/Allanpk/jev-shop && ~/.local/bin/uv run python -m jevlab dashboard --no-open"
  ```

  then open http://127.0.0.1:8765 on your laptop. It closes when you stop the command (Ctrl+C). The dashboard is
  never open to the internet.

**Before going live, all of these should be true:**
- [ ] It ran every trading day you logged in, with no errors in the Telegram reports
- [ ] Its paper buys and sells make sense to you, and look like the backtest's behaviour
- [ ] You've seen at least a few paper sells at +5%
- [ ] You're comfortable with the worst case: up to `MAX_CAPITAL_INR` sitting in falling stocks for months
- [ ] **DDPI is active** on your Firstock account
- [ ] **The static IP is active** on your Firstock API key

---

## Phase 8 · Go live

1. **Fund** your Firstock account. The bot checks your cash before every buy and skips if there isn't enough.
2. **Start smaller than the full plan** for the first month, e.g. a ₹50,000 cap (10 lots). In `nano .env`:

   ```
   MAX_CAPITAL_INR=50000
   FIRSTOCK_MODE=live
   JEV_LIVE_CONFIRM=I accept the risk of trading real money
   ```

   The confirmation phrase must be **exactly** that sentence, or the bot refuses to trade real money.
3. Restart the Telegram listener so it sees the change, and check:

   ```bash
   sudo systemctl restart jev-telegram
   uv run python -m jevlab check
   ```

   Section 5 must say **mode LIVE · REAL MONEY**.
4. **First live day:**
   - Log in before 15:15 (`/login 123456`).
   - At 15:18, watch the **Firstock app → Orders**. You should see one delivery (CNC) limit order from the bot,
     filled within seconds. Its remark is `jev-shop`.
   - At about 15:20, the Telegram report confirms it.
   - The next trading day, the shares show in your **Holdings**.
5. **First live sell** (whenever a holding reaches +5%): check it went through. A rejection mentioning
   authorisation or eDIS means DDPI isn't active yet: the bot keeps the stock and tries again at the next run.
6. **Scale up slowly:** after a month or two that matches your paper results, raise `MAX_CAPITAL_INR` (for
   example to 1,00,000, then 2,00,000). No restart is needed; the next 15:18 run reads it.

Good to know:
- The live bot keeps its own record (`results/ledger-live.json`), separate from paper: it starts with no holdings
  and builds them from real fills. Shares you already owned before aren't touched.
- The bot never places more than one order action a second (SEBI treats 10+ a second as a registered algo), and
  only one buy and one sell a day.

**To stop live trading:** `/stop` on Telegram (no new orders; holdings stay) or set `FIRSTOCK_MODE=paper` in `.env`.

---

## Daily and routine operations

| Task | How |
|---|---|
| Daily login | `/login 123456` to your bot before 15:15 |
| See status, holdings, watch-list | `/status` |
| Pause all orders (kill switch) | `/stop`; resume with `/resume` |
| Holdings and profit in detail | `uv run python -m jevlab report` |
| What happened today | `journalctl -u jev-shop -n 40 --no-pager` |
| News watch-list | `uv run python -m jevlab news`; to let a stock back in early: `uv run python -m jevlab news --clear SYMBOL` |
| Change the amounts or cap | `nano .env` (`BUY_AMOUNT_INR`, `AVERAGE_AMOUNT_INR`, `MAX_CAPITAL_INR`) |
| Change the strategy numbers | `nano jevlab/strategy.py` (`SETTINGS`), then `uv run python -m jevlab backtest` |
| Get an updated version of the bot | `cd ~/Allanpk && git pull && cd jev-shop && uv sync && sudo bash deploy/install.sh` (re-installs the timers and restarts the Telegram listener; your `.env` and `results/` are untouched) |
| Back up the trade record to your laptop | `scp -i ~/.ssh/LightsailDefaultKey-ap-south-1.pem ubuntu@YOUR_STATIC_IP:Allanpk/jev-shop/results/ledger-live.json .` |
| Stop everything for good | `sudo systemctl disable --now jev-shop.timer jev-remind.timer jev-news.timer jev-telegram` |

**Monthly:** compare the bot's record with Firstock's **contract notes** (the source of truth for fills and
charges). Keep them for tax: gains on shares held under a year are short-term capital gains. Ask a CA.

---

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Invalid TOTP` at login | The code expired (they change every 30 seconds). Send a fresh one. |
| Orders rejected with an IP / whitelist message | The static IP isn't registered or active on your Firstock API key (Phase 3.2), or the server isn't using it: re-check steps 1.7, 1.9 and 2.5. |
| Sell rejected (authorisation, eDIS, TPIN) | DDPI isn't active (Phase 0.3). The bot keeps the stock and retries at the next run. |
| "not logged in to Firstock today" | You didn't send `/login` before 15:15. The day is skipped; nothing to fix. |
| "the shop trades between 15:15 and 15:29" | You ran `run` by hand outside the window. Use `scan` to look any time. |
| "NSE didn't trade today (a holiday)" | Exchange holiday: normal. |
| "the feeds couldn't be read" | A news site is down. The bot uses headlines collected earlier. If one feed stays broken, swap its address in `jevlab/news.py` (`FEEDS`). |
| Nifty 50 list "built-in list (NSE unreachable)" | NSE blocked the download; it retries next time. The built-in list is from late 2025. |
| Telegram silent | `sudo systemctl status jev-telegram --no-pager`; check the token and chat ID in `.env`, then `sudo systemctl restart jev-telegram`. |
| Server unreachable | Lightsail console → instance → **Reboot**. Rebooting keeps the static IP; never delete the static IP. |
| Out of disk | `df -h`; the bot uses very little. Check `journalctl --disk-usage` and `sudo journalctl --vacuum-size=200M`. |

---

## Security checklist

- [ ] MFA on your AWS root user
- [ ] Only SSH (22) open in the Lightsail firewall; HTTP removed; the dashboard only through the SSH tunnel
- [ ] `.env` is `chmod 600`, never copied into chat, email or GitHub (it's in `.gitignore`)
- [ ] Your authenticator QR/secret is never shared or stored on the server; you type the 6-digit code daily
- [ ] The static IP stays attached; don't delete or recreate the instance (the IP registered with Firstock would change)
- [ ] Automatic snapshots on

---

*The bot and this guide were tested against a simulated Firstock, not a real account. On your first real day,
watch the first `check`, `login` and 15:18 run closely, and compare everything with the Firstock app.*
