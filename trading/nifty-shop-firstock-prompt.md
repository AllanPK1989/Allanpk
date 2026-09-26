# Jev Starter · Nifty Shop edition: a ₹5,000-a-day Nifty 50 bot on Firstock, for ₹0–₹450 a month

> **How to use this:** open Claude Code in an empty folder, drag this file in (or paste it), and say "go".
> Claude sets everything up and talks you through it. Mac, Windows and Linux.
>
> **What it does:** once each trading day at 15:18 IST, it runs the **Nifty Shop** strategy (popularised by Mahesh
> Chander Kaushik; FabTrader's "10-minute trading strategy for busy professionals"). It ranks the Nifty 50 by how far
> each stock is below its 20-day moving average, buys one beaten-down stock for **₹5,000**, averages a holding that
> has kept falling, and sells any holding once it's 5% up. At most one buy and one sell a day.
> - **Path 1, laptop (about 25 min):** set up, backtest the rules over 5 years, see today's picks, paper trade.
> - **Path 2, server (about 45 min more):** the shop runs itself every trading day on a tiny server in India
>   (free on Oracle Cloud, or about ₹250–450 a month), with Telegram on your phone for the daily login and report.
>   It starts in **paper mode**. Real money only happens if you switch it on yourself.
>
> You need a Firstock trading account (Indian KYC, equity segment, 2FA with an authenticator app). Telegram and a
> Vercel account (for Jev's optional news check) are optional.

---

You are the setup agent for **jev-shop** (the Nifty Shop edition of jev-starter). Do the work yourself: run every
command, check every result, fix errors as they come up. The user is watching and may not be technical, so talk to
them in plain English, one or two short lines per step. Ask before anything that costs money or creates an account;
those are their decisions.

## What you're building (say this to the user first, in 4–5 lines)

A bot that runs the Nifty Shop for them once a day, near the close. Every trading day at 15:18 it ranks the Nifty 50
by how far each stock is below its 20-day average and does at most two things: **sell** a holding that's 5% or more
above its average price, and **buy** ₹5,000 of the most beaten-down stock they don't own yet. If they already own all
5 candidates, it adds ₹5,000 to the holding that has fallen furthest (once it's 3% below its last buy). It starts on
paper, with a 5-year backtest first so they can see how the rules behaved. It runs on a free or very cheap server,
with Telegram for the daily login and report.

Then ask: **"Do you want just the laptop version (Path 1), or the bot running by itself every day (Path 2)? Either way
we start on the laptop, so you can see the backtest and today's picks first."**

## The honest part (say this too, briefly, before any money is involved)

- **No stop-loss.** A falling stock is averaged, not sold (this build stops at 6 lots per stock). In a long bear market,
  money sits in losers for months. `MAX_CAPITAL_INR` (₹2,00,000 by default = 40 lots) caps the total invested, and they
  should only commit money they can leave alone for a year or more.
- **₹5,000 a day adds up:** up to about ₹1 lakh a month can go in before sells start freeing it up.
- **Costs:** no delivery brokerage on Firstock, but each ₹5,000 round trip pays about ₹29 (STT, stamp duty, exchange
  charges, the DP charge, GST), so a +5% winner of ₹250 nets about ₹220 before tax. Gains on shares held under a year
  are short-term capital gains (20% at the time of writing): ask a CA.
- **Whole shares only:** a ₹4,000 share buys 1 share (₹4,000), and stocks above ₹5,000 a share are skipped.
- The backtest uses today's Nifty 50 for the whole period, so it's a best case. Not financial advice.

## Rules (never break these)

1. Write every file exactly as given in the **Files** section. Don't rewrite, reformat or "improve" them. The only file
   you may change later is `jevlab/strategy.py`, when the user asks. Narrow exceptions, and tell the user when you use
   them:
   - If Firstock's API answers in a shape `jevlab/firstock.py` doesn't parse (a renamed field, a different date or
     interval format: their API is young and changes), you may fix the parsing in `firstock.py`. Never touch
     `live_mode`, `LIVE_PHRASE`, the one-order-a-second throttle, or the delivery product code.
   - If a news feed in `jevlab/news.py` stops working, swap its URL for another markets feed from the same site. If
     NSE's Nifty 50 list can't be downloaded, you may update `FALLBACK` in `jevlab/universe.py`.
2. Never type, paste, print or echo any key, secret or password: the Firstock password, API key and vendor code, the
   session token in `results/session.json`, the Telegram bot token, the Vercel key, or a server password. The user puts
   their own into `.env`. Never `cat` `.env` or `results/session.json`. Copying `.env` to their own server is fine.
3. The 6-digit 2FA code: best is that the user types it into the `login` prompt in their own terminal, or sends
   `/login 123456` to their Telegram bot. If they read a code out to you instead, you may run `login --totp <code>` straight
   away (it expires within a minute and is useless without the password). Never ask for, store or automate the
   authenticator's secret key or QR code: that would defeat 2FA, which SEBI's rules require.
4. Never set `FIRSTOCK_MODE=live` or `JEV_LIVE_CONFIRM` yourself, and never change `BUY_AMOUNT_INR`,
   `AVERAGE_AMOUNT_INR` or `MAX_CAPITAL_INR` unless the user asks for a specific number. Real money is the user's own
   deliberate step (Part C).
5. Stay inside SEBI's retail algo rules: orders go only from the static IP registered with Firstock. Never route around
   it with proxies, VPNs or anyone else's IP. The shop sends at most one order action a second, far under the
   10-a-second level where an algo must be registered with the exchange.
6. Never open the dashboard port (8765) to the internet. On the server it's reached only through an SSH tunnel.
7. Never promise profit. Say the honest part above whenever money comes up.

# PART A · Path 1: the laptop (everyone does this)

## A1 · Check the machine

1. Work out the OS (`uname -s`; if that fails, it's Windows).
2. Run `uv --version`. If it's missing, install it:
   - Mac/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`, then `export PATH="$HOME/.local/bin:$PATH"`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, then
     restart the terminal if `uv` still isn't found
3. `uv` downloads its own Python, so nothing else needs installing.

## A2 · Write the project

Create a folder called `jev-shop`, write every file from the **Files** section into it at the exact path shown, then
`cd jev-shop` and run `uv sync`.

## A3 · Test it before the keys

Run `uv run python -m jevlab check`. "The Nifty 50 list" should show 50 stocks from NSE, and Firstock will say
"not set up yet". That's expected.

## A4 · Firstock API access (the user does this part)

1. **The account:** ask whether they have a Firstock trading account with the equity segment active. If not, open
   https://firstock.in for them (`open` on Mac, `start` on Windows, `xdg-open` on Linux). It needs PAN, Aadhaar and a
   bank account, and takes a day or so.
2. **2FA:** logging in through the API needs the 6-digit code from an authenticator app. If they only ever get SMS
   codes, have them switch on authenticator-app (TOTP) login in the Firstock app or website first.
3. **API key:** open https://firstock.in/api/docs/ and guide them (by meaning: labels on the site change) to generate
   an **API key**, and to note their **vendor code**. Orders through the API also need a registered static IP (a SEBI
   rule), but the laptop only reads prices, so that waits for B6. If the page won't create a key without an IP, don't
   guess one: do Part B's server first (B3–B6), then run A5–A7 there.
4. Copy `.env.example` to `.env` (`cp .env.example .env`, or `copy .env.example .env` on Windows) and open it in their
   editor (`open -e .env` on Mac, `notepad .env` on Windows, `${EDITOR:-nano} .env` on Linux). Say: *"Fill in
   `FIRSTOCK_USER_ID` (your client ID), `FIRSTOCK_PASSWORD`, `FIRSTOCK_API_KEY` and `FIRSTOCK_VENDOR_CODE`, save, and
   tell me when you're done."* `BUY_AMOUNT_INR=5000` is already set. Then wait.
5. **The daily login.** Explain: SEBI's rules end every API session each day, so once each trading day they log in with
   their 2FA code. Show them the folder path (`pwd`) and ask them to open their own terminal (Terminal on Mac,
   PowerShell on Windows), `cd` there, and run `uv run python -m jevlab login`. (Or they read you a fresh code and you
   run `uv run python -m jevlab login --totp <code>` right away: see Rule 3.) "Invalid TOTP" means the code expired:
   use a fresh one. A message about the IP not being allowed means their key is IP-locked: see step 3.
6. Run `uv run python -m jevlab check` again. The Firstock section should show their name and live prices.

## A5 · The backtest (what the rules would have done)

Run `uv run python -m jevlab backtest` (the first run downloads 5 years of daily prices for 50 stocks, about 1–3
minutes; later runs use the cache). Read the result to them in plain English:
- how many buys, averages and sells, and the profit booked vs. still open, **after charges**
- **the most money ever invested at once**, the return on that, and roughly how much a year
- the worst drawdown, and any stocks still stuck well below their buy price at the end
- NIFTY's own return over the same period, for comparison
Then say it plainly: this uses today's Nifty 50 for the whole period, so companies that dropped out after falling are
missing, and real results will be worse. If Firstock's history is shorter than 5 years, say how far back it went.
If a stock shows "no history", mention it and move on.

## A6 · Today's picks, and the dashboard

1. Run `uv run python -m jevlab scan` (any time: no orders). Explain the list: the stocks furthest below their 20-day
   average, the ★ five candidates, and what the shop **would** sell and buy right now. The real run uses the 15:18 price.
2. Run `uv run python -m jevlab dashboard` in the background. It opens http://127.0.0.1:8765: the ranking, what they
   hold, what's been sold, and the backtest curve (profit after charges vs. money invested).

## A7 · Optional: Jev's news check

The Nifty Shop buys dips. This option skips a dip that's happening for a very good reason: before buying, Jev reads
the last day and a half of Indian market headlines (Economic Times, Moneycontrol, Livemint, Business Standard) that
mention the company, and vetoes the buy if one is serious bad news (fraud, a regulator's ban, collapsing results). It
makes 1–5 tiny calls a day, so Vercel's free tier is plenty. If they want it: open https://vercel.com/dashboard, and
guide them to **AI Gateway → API Keys → Create key**, then paste it after `AI_GATEWAY_API_KEY=` in `.env` themselves.
Re-run `check`: "Jev answered" should say ok. Without a key the shop simply runs without the check. The backtest can't
test this (there's no archive of old headlines).

## A8 · Their own settings

Open `jevlab/strategy.py` and show them `SETTINGS` in two lines: the 5% target, 3% averaging step, 5 candidates,
20-day average, and our 6-lot cap per stock. Common variants: Kaushik's 6.28% target, or FabTrader's 8% version.
If they want a change, edit `SETTINGS` (or `decide()`), re-run `backtest`, and compare. Before trusting any change,
ask three questions: why should it make money, does it survive costs, does it work on data it's never seen?

**If they only wanted Path 1, wrap up here.** On the laptop they can run the paper shop by hand each trading day
between 15:15 and 15:29: `uv run python -m jevlab login`, then `uv run python -m jevlab run`. Also remind them of
`scan`, `report`, `backtest` and `dashboard`, and that this is paper trading.

# PART B · Path 2: the shop runs itself every day

Tell them what's coming in 3 lines: a Telegram bot for their phone (optional but recommended), a tiny server in India
with a fixed IP (free on Oracle Cloud, or about ₹250–450 a month), and three timers on it: a 14:30 login reminder, the
15:18 run, and the Telegram listener. The one daily chore: send `/login 123456` to their bot before 15:15.

## B1 · The rules they trade under (tell them, briefly)

SEBI's framework for retail algo trading has applied since 1 April 2026:
- Firstock only accepts API orders from a **static IP registered with them** (a main IP and optionally a backup,
  changeable about once a week). The server should be **in India**.
- Every API session **ends daily**; logging in needs 2FA.
- Below **10 orders a second** you're an ordinary API user. The shop sends a couple of orders a day.
- **Selling** shares from the demat through the API needs **DDPI** (or eDIS authorisation) on the Firstock account.

## B2 · A Telegram bot (optional, recommended; the user does the clicking)

1. In Telegram, they open **@BotFather**, send `/newbot`, pick a name, and copy the **bot token** it gives them.
2. They paste it after `TELEGRAM_BOT_TOKEN=` in `.env` and save. Then they open their new bot in Telegram and send it
   any message ("hi").
3. Run `uv run python -m jevlab telegram-id`. It prints their chat ID (not a secret). Have them put it after
   `TELEGRAM_CHAT_ID=` in `.env` (you may do this edit yourself: it's just their chat number), then run `check`: they
   should get "Telegram works" on their phone.

## B3 · Pick a server (the user does the buying)

Explain the choice and what it costs each month:

| | Monthly cost | Notes |
|---|---|---|
| **Oracle Cloud Always Free**, home region **Mumbai or Hyderabad** | ₹0 | The home region is chosen at sign-up and can't be changed. Sign-up needs a card for verification. Free machines are sometimes "out of capacity" (try again later, or another availability domain). Oracle may reclaim Always Free machines that sit idle, and this bot is idle most of the day: upgrading the account to Pay As You Go avoids that and stays ₹0 within the free limits (check Oracle's current terms). |
| **Smallest paid VPS in India** with a dedicated IPv4 (DigitalOcean Bangalore, Vultr Mumbai or Delhi, AWS Lightsail Mumbai, Hostinger India…) | about ₹250–450 | Simpler and dependable. Check the plan includes an IPv4 address, not IPv6 only. |
| Firstock API · Telegram · Jev's news check (free tier) | ₹0 | Check Firstock's API page for any API charges. |

The shop only needs about 2 minutes of computing a day, so the smallest machine of any kind is plenty. Ubuntu 24.04.
What matters is a **fixed public IPv4**: on Oracle, create a **reserved public IP** (Always Free includes one) and
attach it to the machine; on paid VPSs the machine's own IPv4 stays fixed for as long as the server exists, so they
should never destroy and recreate it.

## B4 · Create the server (the user does this, you make the SSH key)

1. Make an SSH key for them. It's a key pair: the private half stays on their laptop, and the public half goes to the
   server.
   - Mac/Linux: `ssh-keygen -t ed25519 -f ~/.ssh/jev_shop -N "" -C jev-shop`, then show `cat ~/.ssh/jev_shop.pub`
   - Windows: `ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\jev_shop" -N '""' -C jev-shop`, then show
     `Get-Content "$env:USERPROFILE\.ssh\jev_shop.pub"`
   Showing the **.pub** (public) key is safe. They paste it into the provider's **SSH key** field while creating an
   **Ubuntu 24.04** machine in an Indian region (and on Oracle, attach the reserved public IP).
2. Ask for the **IP address**, and the **login user**: `ubuntu` on Oracle Cloud and AWS, `root` on most others.

## B5 · Install the shop on the server

Below, `$SSH` is shorthand for the full command `ssh -i ~/.ssh/jev_shop -o StrictHostKeyChecking=accept-new <USER>@<IP>`
(on Windows, use the `$env:USERPROFILE\.ssh\jev_shop` key path), and `~` on the server is that user's home. Each
command runs in a fresh shell, so write the full command every time.
1. Test it: `$SSH "echo connected"`.
2. Install uv there: `$SSH "curl -LsSf https://astral.sh/uv/install.sh | sh"`.
3. Copy the project, including `.env` (as a file; never print it), but not `.venv` or `results` (the laptop's paper
   ledger and session stay on the laptop):
   - Mac/Linux: `rsync -az --exclude .venv --exclude results -e "ssh -i ~/.ssh/jev_shop" ./ <USER>@<IP>:jev-shop/`
   - Windows (no rsync): `$SSH "mkdir -p jev-shop"`, then `scp -i <key> -r pyproject.toml README.md .env jevlab dashboard deploy <USER>@<IP>:jev-shop/`
4. `$SSH "cd jev-shop && ~/.local/bin/uv sync"`.
5. Log in **on the server** (it needs its own session): with Telegram set up, the easiest way is to run the listener
   once by hand, `$SSH "cd jev-shop && timeout 120 ~/.local/bin/uv run python -m jevlab telegram"`, and have them send
   `/login 123456` (a fresh code) to the bot. Without Telegram, give them this to run in their own terminal:
   `ssh -t -i ~/.ssh/jev_shop <USER>@<IP> "cd jev-shop && ~/.local/bin/uv run python -m jevlab login"`.
6. `$SSH "cd jev-shop && ~/.local/bin/uv run python -m jevlab check"`. Firstock, the Nifty 50 list, and Telegram
   should say ok **from the server**. Step 5 prints "this machine's public IP is …": that's the IP to register in B6.

## B6 · Register the IP, and switch on DDPI (the user does this part)

1. In Firstock's API page, set the IP from B5.6 as the static IP for their API key (guide by meaning). Activation can
   take a while, and it can only be changed about once a week, so check it carefully. Paper mode doesn't need it.
2. Ask them to switch on **DDPI** (Demat Debit and Pledge Instruction) in their Firstock account if it isn't already.
   Without it, the shop's sell orders are rejected (the report says so).
3. Once the key is locked to the server, Firstock may stop answering the laptop. That's expected: from then on, use
   the server (dashboard through the tunnel in B8).

## B7 · Switch on the daily timers

`$SSH "cd jev-shop && sudo bash deploy/install.sh"`. It installs the 14:30 reminder, the 15:18 run (Monday to Friday,
India time), and the Telegram listener if Telegram is set up, and prints the next run times. Then
`$SSH "systemctl list-timers 'jev-*' --no-pager"` should show both timers.
Explain the routine: **every trading day, send `/login 123456` to the bot before 15:15** (the 14:30 reminder nudges
them if they haven't). If they forget, the shop skips that day and tells them. Holidays and weekends are skipped
automatically. The report arrives on Telegram at about 15:20.

## B8 · Watch it from the laptop

- **Telegram:** `/status` any time: login state, holdings, profit booked.
- **Dashboard:** in the background, run
  `ssh -i ~/.ssh/jev_shop -L 8765:127.0.0.1:8765 <USER>@<IP> "cd jev-shop && ~/.local/bin/uv run python -m jevlab dashboard --no-open"`
  and open http://127.0.0.1:8765 (use `-L 8766:127.0.0.1:8765` and :8766 if 8765 is busy). It's never exposed to the
  internet; it closes when the SSH command ends.

## B9 · Controls (tell them, and write these into `MY-SHOP.md` in their project folder)

- **Daily login:** `/login 123456` on Telegram (or `ssh -t -i ~/.ssh/jev_shop <USER>@<IP> "cd jev-shop && ~/.local/bin/uv run python -m jevlab login"`)
- **Kill switch:** `/stop` on Telegram (or `$SSH "touch jev-shop/STOP"`): no orders until `/resume`. Existing holdings stay.
- **What it did:** `$SSH "journalctl -u jev-shop -n 40 --no-pager"`, or `$SSH "cd jev-shop && ~/.local/bin/uv run python -m jevlab report"`
- **Change the rules:** edit `jevlab/strategy.py` on the laptop, run `backtest` and `scan`, then copy it up (re-run the
  B5.3 copy). The next 15:18 run uses it.
- **Change the amounts:** `BUY_AMOUNT_INR`, `AVERAGE_AMOUNT_INR`, `MAX_CAPITAL_INR` in the server's `.env`.
- **Stop for good:** `$SSH "sudo systemctl disable --now jev-shop.timer jev-remind.timer jev-telegram"`
- **The source of truth** is the Firstock app: holdings, orders, and the contract notes with the exact charges.

## B10 · Wrap up

Tell them it now runs every trading day in **paper mode**: it picks, "buys" and "sells" at real 15:18 prices, with
charges, and reports on Telegram. Because it trades once a day, paper results take a while to mean anything: suggest
at least 1–2 months, compared against the backtest, before even thinking about real money.

# PART C · Real money (only if they explicitly ask)

Explain the steps, but they do them themselves:
1. Confirm the static IP (B6.1) is active and DDPI (B6.2) is on, and the Firstock account has enough cash for the
   buys (the shop checks the cash before each buy and skips if there isn't enough).
2. Edit the server's `.env` in their own terminal: `ssh -t -i ~/.ssh/jev_shop <USER>@<IP> "nano jev-shop/.env"`, set
   `FIRSTOCK_MODE=live` and `JEV_LIVE_CONFIRM=I accept the risk of trading real money`. They can start with a smaller
   `MAX_CAPITAL_INR` if they like.
3. The live shop keeps its own record (`results/ledger-live.json`), separate from paper, so it starts with no holdings
   and builds them from real fills. On the first live day, watch the order appear in the Firstock app at 15:18. If
   it's rejected with an IP message, the static IP isn't active yet.

Remind them: only commit money they can leave invested for a year or more, there's no stop-loss, and keep the
contract notes for tax (ask a CA). Not financial advice.

---

## Files

### `jev-shop/pyproject.toml`

````toml
[project]
name = "jev-shop"
version = "1.0.0"
description = "The Nifty Shop on Firstock: a once-a-day Nifty 50 dip-buying bot, built on jev-starter. Paper first, backtest included, Telegram alerts."
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "pandas>=2.0",
    "python-dotenv>=1.0",
    "rich>=13",
    "tzdata>=2024.1",
]
````

### `jev-shop/.gitignore`

````
.env
.venv/
results/
__pycache__/
STOP
````

### `jev-shop/.env.example`

````
# Copy this file to .env (same folder) and fill it in after the = signs.
# Never share this file.

# --- Firstock (prices, and orders once you go live) --------------------------
# Your Firstock client ID and login password, plus the API key and vendor code
# from Firstock's API key page. The 6-digit 2FA code is NOT stored here: you log
# in once each trading day (terminal: `uv run python -m jevlab login`, or send
# /login 123456 to your Telegram bot).
FIRSTOCK_USER_ID=
FIRSTOCK_PASSWORD=
FIRSTOCK_API_KEY=
FIRSTOCK_VENDOR_CODE=

# --- The shop -------------------------------------------------------------------
# paper = real prices, simulated fills, no orders ever sent. Start here.
FIRSTOCK_MODE=paper

# Rupees per new buy, and per averaging lot (one buy a day at most).
BUY_AMOUNT_INR=5000
AVERAGE_AMOUNT_INR=5000
# Hard limit on the total invested at once. The Nifty Shop can hold 20-40 lots in a
# falling market, so this is the capital it may tie up (40 lots x 5,000 = 2,00,000).
MAX_CAPITAL_INR=200000

# Firstock's depository (DP) charge per stock sold per day, before GST. Check your contract notes.
DP_CHARGE_INR=15

# --- Optional: Jev's news check (skip buying into serious bad news) --------------
# Vercel AI Gateway key: https://vercel.com/dashboard -> AI Gateway -> API Keys.
# One to five Jev calls a day: the free tier is plenty. Leave blank to skip the check.
AI_GATEWAY_API_KEY=
TYPESAFE_API_KEY=
NEWS_CHECK=on

# --- Optional: Telegram (daily report, login reminder, /login from your phone) ----
# Bot token from @BotFather, and your own chat ID.
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Real money: leave this blank. Only set FIRSTOCK_MODE=live, and this line to the exact
# phrase "I accept the risk of trading real money", after weeks of paper results.
JEV_LIVE_CONFIRM=
````

### `jev-shop/README.md`

````markdown
# jev-shop: the Nifty Shop on Firstock

A once-a-day Nifty 50 dip-buying bot, built on jev-starter. At 15:18 IST on trading days it ranks the Nifty 50 by how far each stock is below its 20-day moving average, and (with ₹5,000 by default):
- **sells** the holding furthest above its average price, if it's at least 5% up (one sell a day)
- **buys** the first of the 5 furthest-below stocks you don't hold yet (one buy a day)
- or, if it can't, **averages** the holding that has fallen furthest, once it's 3% below its last buy

This is the Nifty Shop strategy popularised by Mahesh Chander Kaushik (FabTrader's "10-minute trading strategy for busy professionals"). It starts in **paper mode**: real prices from your Firstock account, simulated fills, no orders.

## What's inside

| | |
|---|---|
| **Scan** · `uv run python -m jevlab scan` | Any time: today's ranking, and what the shop would buy or sell right now. No orders. |
| **Backtest** · `uv run python -m jevlab backtest` | What the rules would have done over the last 5 years with your amounts and caps, after charges, next to NIFTY itself. |
| **Daily run** · `uv run python -m jevlab run` | The real thing, 15:15 to 15:29 IST. The server runs it at 15:18. |
| **Your strategy** · `jevlab/strategy.py` | The one file you edit: the rules and their numbers (5% target, 3% averaging, 5 candidates, 20-DMA, 6 lots max per stock). |
| **Dashboard** · `uv run python -m jevlab dashboard` | Holdings, today's ranking and trades, sells so far, and the backtest curve. |
| **Telegram** (optional) | Daily report on your phone, a 14:30 reminder if you haven't logged in, and `/login 123456`, `/status`, `/stop`, `/resume`. |
| **News check** (optional) | Before buying, Jev reads the day's Indian market headlines about that company and skips the buy if one is serious bad news. |

## Setup

1. Install [uv](https://docs.astral.sh/uv/). `cp .env.example .env` and fill in your Firstock client ID, password, API key and vendor code.
2. `uv sync`, then `uv run python -m jevlab login` (the 6-digit code from your authenticator app), then `uv run python -m jevlab check`.
3. `uv run python -m jevlab backtest`, then `uv run python -m jevlab scan`.

SEBI's rules end every API session daily, so you log in once each trading day before 15:15 (on the server, send `/login 123456` to your Telegram bot).

## Costs

The bot itself costs ₹0 to ₹450 a month: a free Oracle Cloud server in India (or a small paid VPS with a fixed IP), Firstock's API, Telegram, and Jev's free tier. Trading costs are separate. Firstock charges no delivery brokerage, but each ₹5,000 round trip still pays about ₹29 in STT, stamp duty, exchange charges, the DP charge and GST (about 0.6%). A 5% winner on ₹5,000 is ₹250 before tax.

## Things to know

- **No stop-loss.** A falling stock gets averaged (up to 6 lots here), not sold. In a long bear market money gets stuck: `MAX_CAPITAL_INR` caps the total invested (₹2,00,000 = 40 lots by default).
- **The backtest is a best case.** It uses today's Nifty 50 for the whole period, so stocks that fell out of the index are missing.
- **Selling needs DDPI** (or eDIS) switched on in your Firstock account, or sell orders get rejected.
- **Live orders need a static IP** registered with Firstock (SEBI's rule), from a server in India.
- **Tax:** gains on shares held under a year are short-term capital gains (20% at the time of writing). Ask a CA.

Real money needs `FIRSTOCK_MODE=live` **and** the exact phrase in `JEV_LIVE_CONFIRM`. Set those yourself, after weeks of paper results. Not financial advice.
````

### `jev-shop/jevlab/__init__.py`

````python
"""jev-starter, Nifty Shop edition: a once-a-day Nifty 50 dip-buying bot on Firstock, with an optional Jev news check."""
````

### `jev-shop/jevlab/__main__.py`

````python
"""jev-starter, Nifty Shop edition: a once-a-day Nifty 50 dip-buying bot on Firstock.

  uv run python -m jevlab login             # once each trading day: the 6-digit code from your authenticator app
  uv run python -m jevlab check             # test the setup: Firstock, prices, the Nifty 50 list, news, Jev, Telegram
  uv run python -m jevlab scan              # any time: today's ranking and what the shop would do (no orders)
  uv run python -m jevlab backtest          # what the rules would have done over the last 5 years
  uv run python -m jevlab run               # the daily run, 15:15 to 15:29 IST (paper unless you chose live)
  uv run python -m jevlab report            # what you hold, and the profit so far
  uv run python -m jevlab dashboard         # the same, in the browser
  uv run python -m jevlab telegram          # listen for /login, /status, /stop, /resume on Telegram
  uv run python -m jevlab telegram-id       # find your Telegram chat ID (message your bot first)
  uv run python -m jevlab remind            # Telegram nudge if you haven't logged in today (the server runs it at 14:30)
  uv run python -m jevlab logout            # end today's Firstock session early

Flags: --paper (run: paper mode whatever .env says) · --years 10 (backtest) · --totp 123456 (login) ·
       --port 8766 · --no-open
"""

from __future__ import annotations

import argparse
import os
import sys
import threading

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def login_cmd(totp: str | None) -> None:
    from .core import console
    from .firstock import FirstockError, login
    if not totp:
        if not sys.stdin.isatty():
            raise SystemExit("  no terminal to type into: run it as  uv run python -m jevlab login --totp 123456")
        totp = input("  6-digit code from your authenticator app: ").strip()
    try:
        session = login(totp)
    except FirstockError as exc:
        msg = str(exc)
        hint = (" (the code changes every 30 seconds: use a fresh one)" if "otp" in msg.lower()
                else " (check FIRSTOCK_USER_ID, FIRSTOCK_PASSWORD, FIRSTOCK_API_KEY and FIRSTOCK_VENDOR_CODE in .env)")
        raise SystemExit(f"  Firstock said no: {msg}{hint}")
    console.print(f"  logged in to Firstock as [bold]{session.name}[/] · the session lasts until the end of today  [#3fd68a]ok[/]")


def logout_cmd() -> None:
    from .core import console
    from .firstock import FirstockError, forget_session, load_session, logout
    session = load_session()
    if not session:
        forget_session()
        console.print("  not logged in today")
        return
    try:
        logout(session)
    except FirstockError:
        pass
    console.print("  logged out of Firstock  [#3fd68a]ok[/]")


def check() -> None:
    from .core import console, inr, ist_now
    from .firstock import FirstockError, cash, credentials, live_mode, load_session, ltps, public_ip
    from .judges import JevJudge, JudgeError
    from .news import FEEDS, check_enabled, fetch_headlines
    from .shop import amounts
    from .universe import nifty50
    from . import telegram

    ok = "[#3fd68a]ok[/]"
    console.print("  [bold]1. Firstock[/]")
    session = None
    try:
        credentials()
    except FirstockError as exc:
        console.print(f"     [#f5b53d]not set up yet[/]: {exc}")
    else:
        session = load_session()
        if not session:
            console.print("     [#f5b53d]not logged in today[/]: run [bold]uv run python -m jevlab login[/] "
                          "and type the 6-digit code from your authenticator app")
    if session:
        try:
            px = ltps(session, ["RELIANCE-EQ", "NIFTY"])
            console.print(f"     logged in as {session.name} · RELIANCE {inr(px.get('RELIANCE-EQ', 0))} · "
                          f"NIFTY {px.get('NIFTY', 0):,.2f}  {ok}")
        except FirstockError as exc:
            console.print(f"     [#ff5d6c]Firstock said no[/]: {str(exc)[:140]}")
    now = ist_now()
    console.print(f"     it's {now.strftime('%a %H:%M')} IST · the shop runs on trading days at 15:18")
    console.print("  [bold]2. The Nifty 50 list[/]")
    stocks, source = nifty50()
    console.print(f"     {len(stocks)} stocks from {source}  " + (ok if source in ("NSE", "cache") else "[#f5b53d]check[/]"))
    console.print("  [bold]3. News check (optional)[/]")
    if not check_enabled():
        console.print("     switched off (NEWS_CHECK=off)")
    else:
        n = len(fetch_headlines(24))
        console.print(f"     {n} headlines in the last 24h from {len(FEEDS)} feeds  {ok}" if n
                      else "     no headlines found  [#f5b53d]check your internet[/]")
        try:
            jev = JevJudge()
            q = {"x": {"type": "choice", "instructions": "Is this news good or bad for the company?",
                       "criteria": {"good": None, "bad": None}}}
            _, meta = jev.ask({"headline": "Company wins a large new order"}, q, timeout=15, retries=2)
            console.print(f"     Jev answered in {meta['latency_ms']} ms  {ok}")
        except JudgeError as exc:
            msg = str(exc)
            console.print("     no Jev key: the shop runs without the news check (fine)" if "no AI_GATEWAY" in msg
                          else f"     [#ff5d6c]Jev failed[/]: {msg[:120]}")
    console.print("  [bold]4. Telegram (optional)[/]")
    if telegram.enabled():
        console.print(f"     test message sent  {ok}" if telegram.send("✅ jev-shop check: Telegram works.")
                      else "     [#ff5d6c]couldn't send[/]: check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    else:
        console.print("     not set up (reports go to the log only)")
    console.print("  [bold]5. Trading[/]")
    buy, avg, cap = amounts()
    try:
        mode = live_mode()
        console.print(f"     mode [bold]{mode.upper()}[/]" + (" (simulated fills: no orders are sent)" if mode == "paper"
                                                                else " · [bold #ff5d6c]REAL MONEY[/]")
                      + f" · {inr(buy)} a buy · {inr(avg)} an average · cap {inr(cap)}")
    except FirstockError as exc:
        console.print(f"     [#ff5d6c]{exc}[/]")
    if session:
        try:
            c = cash(session)
            console.print(f"     cash in Firstock {inr(c)}  {ok}" if c is not None else f"     account readable  {ok}")
        except FirstockError as exc:
            console.print(f"     [dim]couldn't read the account: {str(exc)[:100]}[/]")
    ip = public_ip()
    console.print(f"     this machine's public IP is [bold]{ip}[/]. Firstock only accepts API orders from the static IP "
                  "you registered with them" if ip else "     [dim](couldn't look up this machine's public IP)[/]")


def report_cmd() -> None:
    import json
    from .core import console, inr
    from .firstock import FirstockError, live_mode, load_session, ltps, trading_symbol
    from .ledger import Ledger
    try:
        mode = live_mode()
    except FirstockError:
        mode = "paper"
    ledger = Ledger(mode)
    held = ledger.holdings()
    prices = {}
    session = load_session()
    if session and held:
        try:
            got = ltps(session, [trading_symbol(s) for s in held])
            prices = {s: got.get(trading_symbol(s)) for s in held}
        except FirstockError:
            prices = {}
    if not prices:
        from .shop import STATUS
        try:
            prices = json.loads(STATUS.read_text()).get("prices", {})
        except (OSError, ValueError):
            prices = {}
    console.print(f"  [bold]Nifty Shop · {mode}[/] · {len(held)} holdings" + ("" if session else " · [dim]last known prices[/]"))
    open_pnl = 0.0
    for sym, h in sorted(held.items()):
        p = prices.get(sym)
        chg = f"{p / h['avg'] - 1:+6.1%}" if p else "     ?"
        if p:
            open_pnl += (p - h["avg"]) * h["qty"]
        console.print(f"   {sym:<12} {h['qty']:>5} sh · avg ₹{h['avg']:>10,.2f} · now {('₹' + format(p, ',.2f')) if p else '?':>11} "
                      f"· {chg} · {h['lots']} lot(s) since {h['first_buy']}")
    real, wins, closed = ledger.realised()
    console.print(f"  invested {inr(ledger.invested())} · open P&L {inr(open_pnl, True)} · booked {inr(real, True)} "
                  f"from {closed} sells ({wins} with a profit)")


def main() -> None:
    ap = argparse.ArgumentParser(prog="jevlab")
    ap.add_argument("command", choices=["check", "login", "logout", "scan", "run", "backtest", "report", "dashboard",
                                        "telegram", "telegram-id", "remind"])
    ap.add_argument("--paper", action="store_true", help="run: paper mode (simulated fills), whatever .env says")
    ap.add_argument("--years", type=float, default=5.0, help="backtest: how many years back")
    ap.add_argument("--totp", default=None, help="login: the 6-digit code from your authenticator app")
    ap.add_argument("--port", type=int, default=8765, help="dashboard port")
    ap.add_argument("--no-open", action="store_true", help="don't open the dashboard in a browser")
    a = ap.parse_args()
    from .core import console

    if a.command == "login":
        login_cmd(a.totp)
    elif a.command == "logout":
        logout_cmd()
    elif a.command == "check":
        console.print("[bold #8b7bff]jev-shop[/] [dim]· the Nifty Shop on Firstock[/]")
        check()
    elif a.command in ("scan", "run"):
        from .shop import run_shop
        sys.exit(run_shop(force_paper=a.paper, scan_only=(a.command == "scan")))
    elif a.command == "backtest":
        from .backtest import run_backtest
        run_backtest(a.years)
    elif a.command == "report":
        report_cmd()
    elif a.command == "remind":
        from .shop import remind
        remind()
    elif a.command == "telegram":
        from .telegram import listen
        listen()
    elif a.command == "telegram-id":
        from .telegram import whoami
        whoami()
    elif a.command == "dashboard":
        from .server import serve
        serve(a.port, not a.no_open)
        console.print("  [dim]dashboard open · Ctrl+C to stop[/]")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
````

### `jev-shop/jevlab/core.py`

````python
"""Shared bits: where results go, the terminal styling, India time, and rupees."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rich import box
from rich.console import Console
from rich.panel import Panel

RESULTS = Path(__file__).resolve().parent.parent / "results"
console = Console(highlight=False)

IST = ZoneInfo("Asia/Kolkata")


def header(title: str, subtitle: str) -> None:
    console.print()
    console.print(Panel(f"[dim]{subtitle}[/]", title=f"[bold #8b7bff]{title}[/]", title_align="left",
                        border_style="#3a3f5c", box=box.ROUNDED, padding=(0, 2)))


def ist_now() -> datetime:
    return datetime.now(IST)


def inr(v: float, sign: bool = False) -> str:
    """Rupees with Indian digit grouping: 1234567.8 -> ₹12,34,567.80"""
    neg, v = v < 0, abs(v)
    whole, paise = f"{v:.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        whole = ",".join(([head] if head else []) + groups + [tail])
    return ("-" if neg else "+" if sign else "") + f"₹{whole}.{paise}"
````

### `jev-shop/jevlab/firstock.py`

````python
"""Firstock: the daily login, prices and candles, holdings, and delivery (CNC) orders.

Everything talks to Firstock's developer API (the same endpoints the official
`firstock` Python SDK uses): https://api.firstock.in/V1/<endpoint>, JSON in and out.

The daily login: SEBI's rules end every API session each day, and a login needs
your 2FA code. So once each trading day you log in (from the terminal with
`uv run python -m jevlab login`, or by sending `/login 123456` to your Telegram
bot). The session token is saved in results/session.json (readable only by you)
and is valid until the day ends.

Orders are delivery (CNC, product "C") limit orders priced a little through the
market, so they fill at once but never at a crazy price. At most one order action
a second: far below the 10 orders a second at which SEBI treats you as a
registered algo. Selling shares from your demat needs DDPI (or eDIS) switched on
in your Firstock account.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from datetime import date, datetime, time as dtime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

from .core import IST, RESULTS, ist_now

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_URL = "https://api.firstock.in/V1"
EXCHANGE = "NSE"
DELIVERY = "C"  # Firstock's product code for delivery (CNC): the shares go into your demat account
REMARK = "jev-shop"  # tags the bot's orders
SESSION_FILE = RESULTS / "session.json"
LIVE_PHRASE = "I accept the risk of trading real money"
DONE = ("COMPLETE", "REJECTED", "CANCELED")

# NSE delivery charges. Approximate: check firstock.in/support/charges and your contract notes.
BROKERAGE = 0.0           # Firstock charges no brokerage on equity delivery
STT = 0.001               # securities transaction tax, 0.1% on buy and sell
EXCHANGE_TXN = 0.0000297  # NSE transaction charge
SEBI_FEE = 0.000001       # ₹10 per crore
STAMP_BUY = 0.00015       # stamp duty, buy side only
GST = 0.18                # on brokerage, exchange, SEBI and DP charges
DP_CHARGE = float(os.getenv("DP_CHARGE_INR", "15"))  # depository charge per stock sold per day, before GST


def charges(side: str, value: float) -> float:
    """Everything one delivery order costs, in rupees: brokerage, STT, exchange, SEBI, stamp duty, DP charge, GST."""
    fixed = BROKERAGE + EXCHANGE_TXN * value + SEBI_FEE * value + (DP_CHARGE if side == "sell" else 0.0)
    tax = STT * value + (STAMP_BUY * value if side == "buy" else 0.0)
    return fixed + tax + GST * fixed


class FirstockError(Exception):
    pass


class SessionExpired(FirstockError):
    pass


_EXPIRED = re.compile(r"session (has )?expired|invalid session|session is invalid|jkey|not logged in|please login|"
                      r"login again", re.I)
_IP = re.compile(r"\bip\b|whitelist|static", re.I)  # an IP rejection is not an expired session
_EMPTY = re.compile(r"no data|not found|no record|no position|no order|no holding", re.I)
_lock = threading.Lock()
_last_order = [0.0]


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _message(d) -> str:
    if not isinstance(d, dict):
        return str(d)[:200]
    err = d.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)[:200]
    return str(d.get("message") or err or d.get("emsg") or "")[:200]


def _post(path: str, body: dict, timeout: float = 15.0):
    try:
        r = requests.post(f"{API_URL}/{path}", json=body, timeout=timeout)
    except requests.RequestException as exc:
        raise FirstockError(f"can't reach Firstock: {str(exc)[:120]}") from exc
    try:
        data = r.json()
    except ValueError:
        raise FirstockError(f"HTTP {r.status_code}: {r.text[:160]}")
    if not isinstance(data, dict) or str(data.get("status", "")).lower() != "success":
        msg = _message(data) or f"HTTP {r.status_code}"
        if (r.status_code == 401 or _EXPIRED.search(msg)) and not _IP.search(msg) and path != "login":
            raise SessionExpired(msg)
        raise FirstockError(msg)
    return data.get("data", {})


# ---------------------------------------------------------------- login and session

def credentials() -> dict:
    names = {"userId": "FIRSTOCK_USER_ID", "password": "FIRSTOCK_PASSWORD",
             "apiKey": "FIRSTOCK_API_KEY", "vendorCode": "FIRSTOCK_VENDOR_CODE"}
    out = {k: os.getenv(v, "").strip() for k, v in names.items()}
    missing = [names[k] for k, v in out.items() if not v]
    if missing:
        raise FirstockError("missing from .env: " + ", ".join(missing))
    return out


def write_private(path, text: str) -> None:
    RESULTS.mkdir(exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


class Session:
    """A logged-in Firstock session: every API call carries the user ID and the session token (jKey)."""

    def __init__(self, user_id: str, jkey: str, name: str = ""):
        self.user_id, self.jkey, self.name = user_id, jkey, name

    def post(self, path: str, timeout: float = 15.0, **fields):
        try:
            return _post(path, {"userId": self.user_id, "jKey": self.jkey, **fields}, timeout)
        except SessionExpired:
            forget_session()  # so nothing retries a dead token; log in again
            raise

    def rows(self, path: str, **fields) -> list[dict]:
        """A list endpoint (orders, holdings). An empty book comes back as an error, which means []."""
        try:
            data = self.post(path, **fields)
        except SessionExpired:
            raise
        except FirstockError as exc:
            if _EMPTY.search(str(exc)):
                return []
            raise
        return data if isinstance(data, list) else [data] if isinstance(data, dict) and data else []


def login(totp: str) -> Session:
    c = credentials()
    code = re.sub(r"\s", "", totp or "")
    if not re.fullmatch(r"\d{6}", code):
        raise FirstockError("the 2FA code should be the 6 digits from your authenticator app")
    body = {"userId": c["userId"], "password": hashlib.sha256(c["password"].encode()).hexdigest(),
            "TOTP": code, "vendorCode": c["vendorCode"], "apiKey": c["apiKey"]}
    data = _post("login", body, timeout=20)
    token = data.get("susertoken") if isinstance(data, dict) else None
    if not token:
        raise FirstockError("Firstock accepted the login but sent no session token")
    name = str(data.get("userName") or c["userId"])
    write_private(SESSION_FILE, json.dumps({"userId": c["userId"], "jKey": token, "name": name,
                                            "date": ist_now().date().isoformat()}))
    return Session(c["userId"], token, name)


def load_session() -> Session | None:
    """Today's session, if you've logged in today. Sessions end every day, so yesterday's is useless."""
    try:
        d = json.loads(SESSION_FILE.read_text())
    except (OSError, ValueError):
        return None
    if d.get("date") != ist_now().date().isoformat() or not d.get("jKey"):
        return None
    return Session(d["userId"], d["jKey"], d.get("name", ""))


def forget_session() -> None:
    try:
        SESSION_FILE.unlink()
    except OSError:
        pass


def logout(session: Session) -> None:
    try:
        session.post("logout")
    finally:
        forget_session()


def live_mode() -> str:
    """'paper' (default) or 'live'. Live is refused unless JEV_LIVE_CONFIRM is the exact phrase."""
    mode = os.getenv("FIRSTOCK_MODE", "paper").strip().lower() or "paper"
    if mode not in ("paper", "live"):
        raise FirstockError(f"FIRSTOCK_MODE must be 'paper' or 'live', not '{mode}'")
    if mode == "live" and os.getenv("JEV_LIVE_CONFIRM", "").strip() != LIVE_PHRASE:
        raise FirstockError("FIRSTOCK_MODE=live, but JEV_LIVE_CONFIRM isn't set to the exact confirmation phrase. "
                            "Refusing to trade real money.")
    return mode


def public_ip() -> str | None:
    try:
        return requests.get("https://api.ipify.org", timeout=6).text.strip() or None
    except requests.RequestException:
        return None


# ---------------------------------------------------------------- market data

def trading_symbol(symbol: str) -> str:
    """RELIANCE -> RELIANCE-EQ (the NSE equity series). Anything with a dash (and NIFTY) is left alone."""
    s = symbol.strip().upper()
    return s if "-" in s or s == "NIFTY" else f"{s}-EQ"


def security_info(session: Session, tsym: str) -> dict:
    d = session.post("securityInfo", exchange=EXCHANGE, tradingSymbol=tsym)
    if not isinstance(d, dict) or not d.get("token"):
        raise FirstockError(f"Firstock doesn't know {EXCHANGE}:{tsym}")
    return {"token": str(d["token"]), "tick": _f(d.get("tickSize"), 0.05) or 0.05, "name": d.get("symbolName") or tsym}


def quote(session: Session, tsym: str) -> dict:
    d = session.post("getQuote", exchange=EXCHANGE, tradingSymbol=tsym)
    return {"ltp": _f(d.get("lastTradedPrice")), "bid": _f(d.get("bestBuyPrice1")), "ask": _f(d.get("bestSellPrice1")),
            "open": _f(d.get("dayOpenPrice")), "prev_close": _f(d.get("dayClosePrice")),
            "tick": _f(d.get("tickSize"), 0.0), "name": d.get("companyName") or tsym}


def ltps(session: Session, tsyms: list[str]) -> dict[str, float]:
    """Last traded prices for many stocks: one multi-quote call per 25 stocks, one-by-one for any it misses."""
    out: dict[str, float] = {}
    for i in range(0, len(tsyms), 25):
        chunk = tsyms[i:i + 25]
        try:
            rows = session.post("getMultiQuotes/ltp", data=[{"exchange": EXCHANGE, "tradingSymbol": t} for t in chunk])
            for r in rows if isinstance(rows, list) else []:
                if _f(r.get("lastTradedPrice")) > 0:
                    out[r.get("tradingSymbol")] = _f(r.get("lastTradedPrice"))
        except SessionExpired:
            raise
        except FirstockError:
            pass
    for t in tsyms:
        if t not in out:
            try:
                px = quote(session, t)["ltp"]
            except SessionExpired:
                raise
            except FirstockError:
                continue
            if px > 0:
                out[t] = px
            time.sleep(0.05)
    return out


def daily_candles(session: Session, tsym: str, start: date, end: date | None = None) -> pd.DataFrame:
    """Daily OHLCV, indexed by date (IST). Asks for a year at a time."""
    end = end or ist_now().date()
    frames, t0 = [], start
    fmt = "%H:%M:%S %d-%m-%Y"
    while t0 <= end:
        t1 = min(end, t0 + timedelta(days=364))
        rows = session.post("timePriceSeries", timeout=30, exchange=EXCHANGE, tradingSymbol=tsym, interval="1d",
                            startTime=datetime.combine(t0, dtime(9, 15)).strftime(fmt),
                            endTime=datetime.combine(t1, dtime(15, 30)).strftime(fmt))
        frames.append(_rows_to_frame(rows if isinstance(rows, list) else []))
        t0 = t1 + timedelta(days=1)
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.concat(frames)
    return df[~df.index.duplicated(keep="last")].sort_index()


def _rows_to_frame(rows: list[dict]) -> pd.DataFrame:
    out = []
    for r in rows:
        day = None
        epoch = _f(r.get("epochTime") or r.get("ssboe"))
        if epoch:
            day = pd.Timestamp(epoch / (1000 if epoch > 1e11 else 1), unit="s", tz="UTC").tz_convert(IST).date()
        elif r.get("time"):
            try:
                day = pd.to_datetime(r["time"], dayfirst=True).date()
            except (ValueError, TypeError):
                day = None
        if day is not None and _f(r.get("close")) > 0:
            out.append((day, _f(r.get("open")), _f(r.get("high")), _f(r.get("low")), _f(r.get("close")), _f(r.get("volume"))))
    return pd.DataFrame(out, columns=["day", "open", "high", "low", "close", "volume"]).set_index("day")


# ---------------------------------------------------------------- account and orders (live mode only)

def cash(session: Session) -> float | None:
    d = session.post("limit")
    return _f(d.get("cash")) if isinstance(d, dict) and d.get("cash") is not None else None


def holdings(session: Session) -> dict[str, dict]:
    """Shares in your demat you can sell today: {tradingSymbol: {"qty": int, "avg": float}}."""
    out: dict[str, dict] = {}
    for r in session.rows("holdingsDetails"):
        syms = [s.get("tradingSymbol") for s in r.get("exchangeTradingSymbol") or [] if s.get("exchange", EXCHANGE) == EXCHANGE]
        tsym = syms[0] if syms else r.get("tradingSymbol")
        if not tsym:
            continue
        qty = int(_f(r.get("holdQuantity")) + _f(r.get("BTSTQuantity")) - _f(r.get("usedQuantity")))
        out[tsym] = {"qty": max(0, qty), "avg": _f(r.get("uploadPrice"))}
    return out


def _throttle() -> None:
    with _lock:
        wait = _last_order[0] + 1.0 - time.time()  # at most one order action a second
        if wait > 0:
            time.sleep(wait)
        _last_order[0] = time.time()


def round_to_tick(px: float, tick: float, up: bool) -> float:
    steps = px / tick
    return round((math.ceil(steps - 1e-9) if up else math.floor(steps + 1e-9)) * tick, 2)


def place_limit(session: Session, tsym: str, side: str, qty: int, px: float) -> str:
    _throttle()
    d = session.post("placeOrder", exchange=EXCHANGE, tradingSymbol=tsym, quantity=str(int(qty)), price=f"{px:.2f}",
                     product=DELIVERY, transactionType="B" if side == "buy" else "S", priceType="LMT",
                     retention="DAY", triggerPrice="0", remarks=REMARK)
    oid = str(d.get("orderNumber") or "") if isinstance(d, dict) else ""
    if not oid:
        raise FirstockError(f"no order number in Firstock's reply: {str(d)[:120]}")
    return oid


def order(session: Session, oid: str) -> dict:
    """Current state of one order: status, shares filled, average fill price, reject reason."""
    rows = session.rows("singleOrderHistory", orderNumber=oid)
    if not rows:
        rows = [r for r in session.rows("orderBook") if str(r.get("orderNumber")) == oid]
    if not rows:
        return {"status": "UNKNOWN", "filled": 0, "avg_px": 0.0, "reason": ""}
    statuses = [str(r.get("status", "")).upper().replace("CANCELLED", "CANCELED") for r in rows]
    status = next((s for s in DONE if s in statuses), statuses[0])
    filled = int(max(_f(r.get("fillShares")) for r in rows))
    avg = next((_f(r.get("averagePrice")) for r in rows
                if int(_f(r.get("fillShares"))) == filled and _f(r.get("averagePrice"))), 0.0)
    reason = next((r.get("rejectReason") for r in rows if r.get("rejectReason")), "")
    return {"status": status, "filled": filled, "avg_px": avg, "reason": str(reason)[:160]}


def cancel(session: Session, oid: str) -> None:
    try:
        _throttle()
        session.post("cancelOrder", orderNumber=oid)
    except SessionExpired:
        raise
    except FirstockError:
        pass  # already filled or gone


def execute(session: Session, tsym: str, side: str, qty: int, ref_px: float) -> dict:
    """Buy or sell `qty` shares for delivery with a limit order priced 0.5% through the last price
    (then 1% once, if the first try doesn't fill in 30 seconds). Returns what actually filled."""
    try:
        tick = security_info(session, tsym)["tick"]
    except FirstockError:
        tick = 0.05
    remaining, fills, reason = qty, [], ""
    for width in (0.005, 0.01):
        if remaining <= 0:
            break
        px = round_to_tick(ref_px * (1 + width) if side == "buy" else ref_px * (1 - width), tick, up=(side == "buy"))
        oid = place_limit(session, tsym, side, remaining, px)
        o = {"status": "", "filled": 0, "avg_px": 0.0, "reason": ""}
        for _ in range(30):
            time.sleep(1)
            o = order(session, oid)
            if o["status"] in DONE:
                break
        if o["status"] not in DONE:
            cancel(session, oid)
            time.sleep(1)
            o = order(session, oid)
        if o["filled"]:
            fills.append((o["filled"], o["avg_px"] or px))
            remaining -= o["filled"]
        if o["status"] == "REJECTED":
            reason = o["reason"] or "rejected"
            break
    done = qty - remaining
    avg = sum(q * p for q, p in fills) / done if done else 0.0
    return {"qty": done, "avg_px": round(avg, 2), "missed": remaining, "reason": reason}
````

### `jev-shop/jevlab/universe.py`

````python
"""The Nifty 50: which stocks the shop looks at.

The list changes twice a year, so it's downloaded from NSE and cached for a week.
If NSE can't be reached, the last good download is used, and failing that the list
below (correct as of late 2025, and possibly out of date).
"""

from __future__ import annotations

import csv
import io
import json
import time

import requests

from .core import RESULTS

URLS = [
    "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
]
CACHE = RESULTS / "nifty50.json"
FALLBACK = {
    "ADANIENT": "Adani Enterprises", "ADANIPORTS": "Adani Ports", "APOLLOHOSP": "Apollo Hospitals",
    "ASIANPAINT": "Asian Paints", "AXISBANK": "Axis Bank", "BAJAJ-AUTO": "Bajaj Auto", "BAJAJFINSV": "Bajaj Finserv",
    "BAJFINANCE": "Bajaj Finance", "BEL": "Bharat Electronics", "BHARTIARTL": "Bharti Airtel", "CIPLA": "Cipla",
    "COALINDIA": "Coal India", "DRREDDY": "Dr. Reddy's", "EICHERMOT": "Eicher Motors", "ETERNAL": "Eternal",
    "GRASIM": "Grasim", "HCLTECH": "HCL Technologies", "HDFCBANK": "HDFC Bank", "HDFCLIFE": "HDFC Life",
    "HINDALCO": "Hindalco", "HINDUNILVR": "Hindustan Unilever", "ICICIBANK": "ICICI Bank", "INDIGO": "InterGlobe Aviation",
    "INFY": "Infosys", "ITC": "ITC", "JIOFIN": "Jio Financial", "JSWSTEEL": "JSW Steel", "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro", "M&M": "Mahindra & Mahindra", "MARUTI": "Maruti Suzuki", "MAXHEALTH": "Max Healthcare",
    "NESTLEIND": "Nestle India", "NTPC": "NTPC", "ONGC": "ONGC", "POWERGRID": "Power Grid", "RELIANCE": "Reliance Industries",
    "SBILIFE": "SBI Life", "SBIN": "State Bank of India", "SHRIRAMFIN": "Shriram Finance", "SUNPHARMA": "Sun Pharma",
    "TATACONSUM": "Tata Consumer", "TATASTEEL": "Tata Steel", "TCS": "Tata Consultancy Services", "TECHM": "Tech Mahindra",
    "TITAN": "Titan", "TMPV": "Tata Motors", "TRENT": "Trent", "ULTRACEMCO": "UltraTech Cement", "WIPRO": "Wipro",
}


def nifty50(max_age_days: float = 7) -> tuple[dict[str, str], str]:
    """{symbol: company name} and where it came from ("NSE", "cache", "built-in list")."""
    cached = None
    try:
        cached = json.loads(CACHE.read_text())
        if time.time() - cached["t"] < max_age_days * 86400 and len(cached["stocks"]) >= 45:
            return cached["stocks"], "cache"
    except (OSError, ValueError, KeyError):
        cached = None
    for url in URLS:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (jev-shop)", "Accept": "text/csv,*/*"})
            r.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
            stocks = {row["Symbol"].strip(): row.get("Company Name", "").strip() for row in rows
                      if row.get("Symbol") and row.get("Series", "EQ").strip() == "EQ"}
            if len(stocks) >= 45:
                RESULTS.mkdir(exist_ok=True)
                CACHE.write_text(json.dumps({"t": time.time(), "stocks": stocks}))
                return stocks, "NSE"
        except (requests.RequestException, KeyError, UnicodeDecodeError, csv.Error):
            continue
    if cached:
        return cached["stocks"], "cache (NSE unreachable)"
    return dict(FALLBACK), "built-in list (NSE unreachable; may be out of date)"
````

### `jev-shop/jevlab/strategy.py`

````python
"""YOUR STRATEGY: the Nifty Shop rules. This is the one file you're meant to edit.

The Nifty Shop (popularised by Mahesh Chander Kaushik, written up by FabTrader as
the "10-minute trading strategy for busy professionals") buys temporary weakness
in big, liquid Nifty 50 companies and sells when the bounce comes. Once a day,
near the close (15:18 IST):

  1. SELL (at most one a day): of the stocks you hold, the one furthest above its
     average buy price, if it's at least 5% up. The whole holding is sold.
  2. BUY (at most one a day): rank the Nifty 50 by how far each is below its
     20-day moving average. Of the 5 furthest below, buy the first one you don't
     already hold, for your daily amount (₹5,000 by default).
  3. If you can't (you hold all 5, or a share costs more than your amount),
     AVERAGE instead: of your holdings now 3% or more below their LAST buy
     price, add one lot to the one that has fallen furthest.

There is no stop-loss in the original rules: a stock that keeps falling just gets
averaged. max_lots_per_stock is our addition, so no single stock can swallow your
capital. Sells go first, so money freed up today can be reused today.

decide() gets:
  scan       every stock with enough data, most below its 20-DMA first:
               {"symbol": "INFY", "ltp": 1480.5, "dma": 1532.1, "gap": -0.0337}   (gap = ltp / dma - 1)
  holdings   what you hold: {"INFY": {"qty": 7, "avg": 1500.2, "last_buy": 1471.0, "lots": 2, "ltp": 1480.5}}
  buy_amount, average_amount   rupees per new buy / per averaging lot (BUY_AMOUNT_INR, AVERAGE_AMOUNT_INR in .env)

and returns:
  {"sell": {"symbol": ..., "reason": ...} or None,
   "buys": [{"symbol": ..., "kind": "new" | "average", "amount": ..., "reason": ...}, ...],   best first
   "notes": [...]}
The runner sells, then buys the FIRST entry in "buys" it can (it checks cash, your
limits and the optional news check), and records everything. Change the numbers in
SETTINGS, or rewrite decide(). Then run `uv run python -m jevlab backtest` to see
what your change would have done, and `scan` to see what it would do today.
"""

SETTINGS = {
    "dma_days": 20,           # the moving average the ranking uses
    "candidates": 5,          # look at the 5 stocks furthest below it
    "only_below_dma": True,   # and only if they really are below it
    "average_drop": 0.03,     # average into a holding once it's 3% below its last buy price
    "target": 0.05,           # sell a whole holding once it's 5% above its average price
    "max_lots_per_stock": 6,  # our addition: stop averaging a stock after 6 lots
}

DESCRIPTION = (f"Nifty 50 · buy the furthest below the {SETTINGS['dma_days']}-DMA · "
               f"average at -{SETTINGS['average_drop']:.0%} · sell at +{SETTINGS['target']:.0%} · one buy and one sell a day")


def decide(scan: list[dict], holdings: dict, buy_amount: float, average_amount: float) -> dict:
    s = SETTINGS
    notes: list[str] = []

    # 1. the best winner at or above target
    sell = None
    winners = [(h["ltp"] / h["avg"] - 1, sym) for sym, h in holdings.items() if h.get("ltp") and h["avg"] > 0]
    winners = [w for w in winners if w[0] >= s["target"]]
    if winners:
        gain, sym = max(winners)
        sell = {"symbol": sym, "reason": f"{gain:+.1%} above its average price (target +{s['target']:.0%})"}

    # 2. a new stock from the bottom of the ranking
    pool = [x for x in scan if x["gap"] < 0] if s["only_below_dma"] else list(scan)
    bottom = pool[:s["candidates"]]
    sold = sell["symbol"] if sell else None
    new, too_dear = [], []
    for x in bottom:
        if x["symbol"] in holdings or x["symbol"] == sold:
            continue
        (new if x["ltp"] <= buy_amount else too_dear).append(x)
    for x in too_dear:
        notes.append(f"{x['symbol']} is a candidate, but one share (₹{x['ltp']:,.0f}) costs more than ₹{buy_amount:,.0f}")
    buys = [{"symbol": x["symbol"], "kind": "new", "amount": buy_amount,
             "reason": f"{-x['gap']:.1%} below its {s['dma_days']}-DMA, not held yet"} for x in new]

    # 3. otherwise average the holding that has fallen furthest since its last buy
    if not buys:
        if not bottom:
            notes.append(f"no Nifty 50 stock is below its {s['dma_days']}-DMA today")
        drops = []
        for sym, h in holdings.items():
            if not h.get("ltp") or sym == sold or h["lots"] >= s["max_lots_per_stock"] or h["ltp"] > average_amount:
                continue
            drop = h["ltp"] / h["last_buy"] - 1
            if drop <= -s["average_drop"]:
                drops.append((drop, sym))
        maxed = [sym for sym, h in holdings.items() if h["lots"] >= s["max_lots_per_stock"]]
        if maxed:
            notes.append(f"not averaging {', '.join(sorted(maxed))} any more ({s['max_lots_per_stock']} lots each)")
        buys = [{"symbol": sym, "kind": "average", "amount": average_amount,
                 "reason": f"{drop:.1%} since its last buy (averages at -{s['average_drop']:.0%})"} for drop, sym in sorted(drops)]
        if not buys and holdings:
            notes.append("nothing to buy today: all candidates held, and no holding is far enough down to average")
    return {"sell": sell, "buys": buys, "notes": notes}
````

### `jev-shop/jevlab/ledger.py`

````python
"""The shop's own record of every lot it bought and sold.

results/ledger-paper.json (paper mode) or results/ledger-live.json (live mode).
Firstock knows what you own; the ledger adds what the strategy needs and Firstock
doesn't keep: each lot's buy price and date (the averaging rule uses the LAST buy
price), and which days the shop has already run (so it never buys twice in a day).
"""

from __future__ import annotations

import json
import os

from .core import RESULTS


def split_factor(before: float, after: float) -> int:
    """If a price fell to about 1/2, 1/3, 1/4, 1/5 or 1/10 overnight, that's a split or bonus, not a crash."""
    if not before or not after or after >= before / 1.8:
        return 1
    ratio = before / after
    for k in (2, 3, 4, 5, 10):
        if abs(ratio / k - 1) < 0.04:
            return k
    return 1


def adjust_for_splits(prices: list[float]) -> list[float]:
    """Divide every price before an apparent split or bonus by its factor, so moving averages stay honest."""
    out = [float(p) for p in prices]
    for i in range(1, len(out)):
        k = split_factor(out[i - 1], out[i])
        if k > 1:
            out[:i] = [p / k for p in out[:i]]
    return out


class Ledger:
    def __init__(self, mode: str):
        self.mode = mode
        self.path = RESULTS / f"ledger-{mode}.json"
        try:
            self.d = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.d = {}
        for key, empty in (("lots", {}), ("closed", []), ("runs", {}), ("last_price", {})):
            self.d.setdefault(key, empty)

    def save(self) -> None:
        RESULTS.mkdir(exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, indent=1))
        os.replace(tmp, self.path)

    # ---- what you hold
    def holdings(self) -> dict[str, dict]:
        out = {}
        for sym, lots in self.d["lots"].items():
            qty = sum(l["qty"] for l in lots)
            if qty <= 0:
                continue
            cost = sum(l["qty"] * l["price"] for l in lots)
            out[sym] = {"qty": qty, "avg": cost / qty, "cost": cost, "last_buy": lots[-1]["price"], "lots": len(lots),
                        "first_buy": lots[0]["date"], "fees": sum(l.get("fees", 0.0) for l in lots)}
        return out

    def invested(self) -> float:
        return sum(h["cost"] for h in self.holdings().values())

    # ---- trades
    def buy(self, sym: str, qty: int, price: float, fees: float, day: str, kind: str) -> None:
        self.d["lots"].setdefault(sym, []).append({"date": day, "qty": qty, "price": round(price, 2),
                                                   "fees": round(fees, 2), "kind": kind})
        self.save()

    def sell(self, sym: str, qty: int, price: float, fees: float, day: str) -> float:
        """Sell `qty` shares, oldest lots first. Returns the net profit (after buy and sell charges)."""
        lots, left, cost, buy_fees = self.d["lots"].get(sym, []), qty, 0.0, 0.0
        first = lots[0]["date"] if lots else day
        while left > 0 and lots:
            lot = lots[0]
            take = min(left, lot["qty"])
            share = take / lot["qty"]
            cost += take * lot["price"]
            buy_fees += lot.get("fees", 0.0) * share
            lot["fees"] = lot.get("fees", 0.0) * (1 - share)
            lot["qty"] -= take
            left -= take
            if lot["qty"] <= 0:
                lots.pop(0)
        if not lots:
            self.d["lots"].pop(sym, None)
        sold = qty - left
        pnl = sold * price - cost - buy_fees - fees
        self.d["closed"].append({"symbol": sym, "qty": sold, "avg": round(cost / sold, 2) if sold else 0.0,
                                 "price": round(price, 2), "first_buy": first, "sold": day, "pnl": round(pnl, 2),
                                 "fees": round(buy_fees + fees, 2)})
        self.save()
        return pnl

    def adjust_splits(self, prices: dict[str, float], notes: list[str]) -> None:
        """A split or bonus multiplies your shares and divides the price. Adjust the lots to match, so the
        averaging and target rules keep working (checked against the price the last run saw)."""
        for sym in list(self.d["lots"]):
            k = split_factor(self.d["last_price"].get(sym, 0.0), prices.get(sym, 0.0))
            if k > 1:
                for lot in self.d["lots"][sym]:
                    lot["qty"] *= k
                    lot["price"] = round(lot["price"] / k, 2)
                notes.append(f"{sym}: price fell to about 1/{k} overnight, so this looks like a split or bonus. "
                             f"Shares ×{k}, buy prices ÷{k} (check it against your Firstock holdings)")
        self.d["last_price"].update({s: p for s, p in prices.items() if p})
        self.save()

    # ---- one run a day
    def ran(self, day: str) -> dict | None:
        return self.d["runs"].get(day)

    def mark(self, day: str, summary: dict) -> None:
        self.d["runs"][day] = summary
        runs = self.d["runs"]
        for old in sorted(runs)[:-400]:  # keep a bit over a year and a half of daily summaries
            runs.pop(old)
        self.save()

    def realised(self) -> tuple[float, int, int]:
        closed = self.d["closed"]
        return sum(c["pnl"] for c in closed), sum(1 for c in closed if c["pnl"] > 0), len(closed)
````

### `jev-shop/jevlab/shop.py`

````python
"""The daily Nifty Shop run.

  uv run python -m jevlab scan           # any time: today's ranking and what the shop WOULD do (no orders)
  uv run python -m jevlab run            # the real thing, 15:15 to 15:29 IST (the server's timer runs it at 15:18)
  uv run python -m jevlab run --paper    # force paper mode, whatever .env says

What a run does:
  1. Checks the day: a weekday, NSE open today (not a holiday), today's Firstock login,
     no STOP file, and that it hasn't already run today.
  2. Ranks the Nifty 50 by distance below the 20-DMA (last price vs the 19 previous closes
     plus today's price), and prices everything you hold.
  3. Asks strategy.decide() for at most one sell and one buy.
  4. Sells first, then buys: delivery (CNC) limit orders priced 0.5% through the market in
     live mode, or a simulated fill at the last price in paper mode. Charges included.
  5. Records it in the ledger, writes results/shop.json for the dashboard, and sends you
     the day's report on Telegram (if set up).

Safety, always on:
  * paper mode unless FIRSTOCK_MODE=live AND JEV_LIVE_CONFIRM is the exact phrase
  * BUY_AMOUNT_INR / AVERAGE_AMOUNT_INR per buy, and MAX_CAPITAL_INR caps the total invested
  * at most one buy and one sell a day, and one run a day (a re-run does nothing)
  * a buy needs the cash in your Firstock account, and (optionally) Jev's news check
  * kill switch: a file called STOP in the project folder (or /stop on Telegram)
"""

from __future__ import annotations

import json
import os
import time
from datetime import time as dtime, timedelta
from pathlib import Path

from . import strategy, telegram
from .core import RESULTS, console, header, inr, ist_now
from .firstock import (FirstockError, SessionExpired, cash, charges, daily_candles, execute, holdings, live_mode,
                       load_session, ltps, trading_symbol)
from .ledger import Ledger, adjust_for_splits
from .universe import nifty50

RUN_FROM, RUN_UNTIL = dtime(15, 15), dtime(15, 29)
STOP_FILE = Path(__file__).resolve().parent.parent / "STOP"
STATUS = RESULTS / "shop.json"


def amounts() -> tuple[float, float, float]:
    buy = float(os.getenv("BUY_AMOUNT_INR", "5000"))
    avg = float(os.getenv("AVERAGE_AMOUNT_INR", "") or buy)
    cap = float(os.getenv("MAX_CAPITAL_INR", "200000"))
    return buy, avg, cap


def traded_today(session) -> bool | None:
    """Did NSE trade today? (No 1-minute candles today = a holiday.) None if we can't tell."""
    now = ist_now()
    fmt = "%H:%M:%S %d-%m-%Y"
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    for interval in ("1mi", "1"):
        try:
            rows = session.post("timePriceSeries", timeout=20, exchange="NSE", tradingSymbol="RELIANCE-EQ",
                                interval=interval, startTime=start.strftime(fmt), endTime=now.strftime(fmt))
            return bool(rows)
        except SessionExpired:
            raise
        except FirstockError as exc:
            if "no data" in str(exc).lower():
                return False
    return None


def scan_market(session, universe: dict[str, str], held: list[str]) -> tuple[list[dict], dict[str, float], list[str]]:
    """Rank the universe by distance below the DMA, and price everything held too."""
    n = strategy.SETTINGS["dma_days"]
    today = ist_now().date()
    names = sorted(set(universe) | set(held))
    by_tsym = {trading_symbol(s): s for s in names}
    px = {by_tsym[t]: p for t, p in ltps(session, list(by_tsym)).items() if t in by_tsym}
    scan, problems = [], []
    for sym in sorted(universe):
        if sym not in px:
            problems.append(f"{sym}: no price")
            continue
        try:
            df = daily_candles(session, trading_symbol(sym), today - timedelta(days=2 * n + 15), today)
        except SessionExpired:
            raise
        except FirstockError as exc:
            problems.append(f"{sym}: {str(exc)[:60]}")
            continue
        closes = [float(c) for d, c in df["close"].items() if d < today][-(n - 1):]
        if len(closes) < n - 1:
            problems.append(f"{sym}: only {len(closes)} days of history")
            continue
        dma = sum(adjust_for_splits(closes + [px[sym]])) / n  # a split or bonus mustn't look like a crash
        scan.append({"symbol": sym, "ltp": px[sym], "dma": round(dma, 2), "gap": round(px[sym] / dma - 1, 5)})
        time.sleep(0.05)
    return sorted(scan, key=lambda x: x["gap"]), px, problems


def run_shop(force_paper: bool = False, scan_only: bool = False) -> int:
    """One day's run. Returns a process exit code (0 = fine, including "nothing to do")."""
    try:
        configured = live_mode()
    except FirstockError as exc:
        if not (force_paper or scan_only):
            raise SystemExit(f"  {exc}")
        configured = "paper"
    mode = "paper" if force_paper else configured  # a scan reads the configured mode's holdings, and never trades
    buy_amount, avg_amount, max_capital = amounts()
    now = ist_now()
    today = now.date().isoformat()
    header("THE NIFTY SHOP", f"{'SCAN ONLY · no orders' if scan_only else mode.upper()} · {strategy.DESCRIPTION} · "
           f"{inr(buy_amount)} a buy, {inr(avg_amount)} an average · capital cap {inr(max_capital)}")
    ledger = Ledger(mode)

    def stop(why: str, tell: bool = True, mark: bool = False) -> int:
        console.print(f"  {why}")
        if tell and not scan_only:
            telegram.send(f"Nifty Shop ({mode}): {why}")
        if mark:
            ledger.mark(today, {"status": "skipped", "why": why, "mode": mode})
        return 0

    if not scan_only:
        if now.weekday() >= 5:
            return stop("NSE is closed today (weekend).", tell=False)
        if not RUN_FROM <= now.time() <= RUN_UNTIL:
            raise SystemExit("  the shop trades between 15:15 and 15:29 IST (the server runs it at 15:18). "
                             "Use `scan` to see what it would do right now.")
        if ledger.ran(today):
            return stop(f"already ran today ({ledger.ran(today).get('status')}): nothing more to do.", tell=False)
        if STOP_FILE.exists():
            return stop("kill switch is on (STOP file): no orders today.", mark=True)
    session = load_session()
    if not session:
        return stop("not logged in to Firstock today, so no trades today. Log in tomorrow before 15:15 "
                    "(`uv run python -m jevlab login`, or /login 123456 on Telegram).")
    try:
        if not scan_only and traded_today(session) is False:
            return stop("NSE didn't trade today (a holiday): nothing to do.", tell=False, mark=True)
        universe, source = nifty50()
        held = ledger.holdings()
        console.print(f"  ranking {len(universe)} Nifty 50 stocks ({source}) against their "
                      f"{strategy.SETTINGS['dma_days']}-DMA…")
        scan, px, problems = scan_market(session, universe, list(held))
    except SessionExpired:
        return stop("the Firstock session ended. Log in again, then re-run.")
    except FirstockError as exc:
        return stop(f"Firstock problem: {exc}")

    notes: list[str] = []
    if not scan_only:
        ledger.adjust_splits({s: px[s] for s in held if s in px}, notes)
        held = ledger.holdings()
    for sym, h in held.items():
        h["ltp"] = px.get(sym)
    decision = strategy.decide(scan, held, buy_amount, avg_amount)
    notes += decision["notes"]
    if problems:
        notes.append(f"skipped {len(problems)}: " + "; ".join(problems[:4]) + ("…" if len(problems) > 4 else ""))
    actions: list[dict] = []

    if scan_only:
        _print_scan(scan, held, decision, notes)
        _write_status(mode, ledger, scan, held, decision, actions, notes, scan_only=True)
        return 0

    ledger.mark(today, {"status": "running", "mode": mode})  # from here on, a re-run today does nothing
    live = mode == "live"
    try:
        # ---- 1. sell (at most one)
        if decision["sell"]:
            sym = decision["sell"]["symbol"]
            qty, ref = held[sym]["qty"], px[sym]
            if live:
                avail = holdings(session).get(trading_symbol(sym), {}).get("qty", 0)
                if avail < qty:
                    notes.append(f"{sym}: ledger says {qty} shares, Firstock shows {avail} sellable; selling {avail}")
                    qty = avail
                res = execute(session, trading_symbol(sym), "sell", qty, ref) if qty else {"qty": 0, "avg_px": 0,
                                                                                            "reason": "nothing sellable"}
            else:
                res = {"qty": qty, "avg_px": ref, "reason": ""}
            if res["qty"]:
                fee = charges("sell", res["qty"] * res["avg_px"])
                pnl = ledger.sell(sym, res["qty"], res["avg_px"], fee, today)
                actions.append({"side": "sell", "symbol": sym, "qty": res["qty"], "price": res["avg_px"], "fees": round(fee, 2),
                                "pnl": round(pnl, 2), "why": decision["sell"]["reason"]})
            else:
                notes.append(f"sell of {sym} didn't go through: {res['reason'] or 'not filled'}"
                             + (" (is DDPI/eDIS switched on in Firstock?)" if live else ""))

        # ---- 2. buy (at most one: the first candidate that passes every check)
        buys = decision["buys"]
        jev, headlines = None, []
        if buys:
            from .news import check_enabled, fetch_headlines
            if check_enabled() and os.getenv("AI_GATEWAY_API_KEY", "").strip():
                from .judges import JevJudge, JudgeError
                try:
                    jev = JevJudge()
                    headlines = fetch_headlines(36, quiet=True)
                except JudgeError:
                    jev = None
        invested = ledger.invested()
        vetoed: set[str] = set()
        queue = list(buys)
        while queue:
            b = queue.pop(0)
            sym, ref = b["symbol"], px.get(b["symbol"], 0.0)
            qty = int(b["amount"] // ref) if ref else 0
            if qty < 1:
                notes.append(f"{sym}: one share costs more than {inr(b['amount'])}")
                continue
            cost = qty * ref
            if invested + cost > max_capital:
                notes.append(f"no buy: {sym} would take the total invested past MAX_CAPITAL_INR ({inr(max_capital)})")
                break
            if jev:
                from .news import veto
                bad = veto(jev, sym, universe.get(sym, sym), headlines)
                if bad:
                    notes.append(f"skipped {sym}: Jev read serious bad news: “{bad[:90]}”")
                    vetoed.add(sym)
                    if not queue:  # every candidate vetoed: decide again as if they weren't there (so averaging can happen)
                        again = strategy.decide([x for x in scan if x["symbol"] not in vetoed],
                                                {k: v for k, v in held.items() if k not in vetoed}, buy_amount, avg_amount)
                        queue = [x for x in again["buys"] if x["symbol"] not in vetoed]
                    continue
            if live:
                free = cash(session)
                if free is not None and free < cost * 1.01 + charges("buy", cost):
                    notes.append(f"no buy: {inr(free)} cash in Firstock, {sym} needs about {inr(cost * 1.01)}")
                    break
                res = execute(session, trading_symbol(sym), "buy", qty, ref)
            else:
                res = {"qty": qty, "avg_px": ref, "reason": ""}
            if res["qty"]:
                fee = charges("buy", res["qty"] * res["avg_px"])
                ledger.buy(sym, res["qty"], res["avg_px"], fee, today, b["kind"])
                actions.append({"side": "buy", "kind": b["kind"], "symbol": sym, "qty": res["qty"], "price": res["avg_px"],
                                "fees": round(fee, 2), "why": b["reason"]})
            else:
                notes.append(f"buy of {sym} didn't go through: {res['reason'] or 'not filled'}")
            break
    except SessionExpired:
        notes.append("the Firstock session ended during the run: check the Firstock app for open orders")
    except FirstockError as exc:
        notes.append(f"Firstock problem: {str(exc)[:120]}")
    finally:
        ledger.mark(today, {"status": "done", "mode": mode, "actions": actions, "notes": notes})

    held = ledger.holdings()
    for sym, h in held.items():
        h["ltp"] = px.get(sym)
    _print_run(actions, notes, held, ledger)
    _write_status(mode, ledger, scan, held, decision, actions, notes)
    telegram.send(_report(mode, actions, notes, held, ledger))
    return 0


# ---------------------------------------------------------------- reporting

def _pnl(h: dict) -> float | None:
    return (h["ltp"] - h["avg"]) * h["qty"] if h.get("ltp") else None


def _print_scan(scan, held, decision, notes) -> None:
    console.print("\n  [bold]furthest below the DMA today[/]  [dim](★ = the 5 candidates)[/]")
    for i, x in enumerate(scan[:10]):
        star = "★" if i < strategy.SETTINGS["candidates"] and x["gap"] < 0 else " "
        own = f"  [dim]held · {held[x['symbol']]['lots']} lot(s)[/]" if x["symbol"] in held else ""
        console.print(f"   {star} {x['symbol']:<12} {x['gap']:+7.2%}  ₹{x['ltp']:>10,.2f}  (DMA ₹{x['dma']:,.2f}){own}")
    s, b = decision["sell"], decision["buys"]
    console.print(f"\n  would sell: [bold]{s['symbol']}[/] · {s['reason']}" if s else "\n  would sell: nothing")
    console.print(f"  would buy:  [bold]{b[0]['symbol']}[/] ({b[0]['kind']}) · {b[0]['reason']}" if b else "  would buy:  nothing")
    for n in notes:
        console.print(f"  [dim]· {n}[/]")


def _print_run(actions, notes, held, ledger) -> None:
    for a in actions:
        colour = "#3fd68a" if a["side"] == "buy" else "#8b7bff"
        extra = f" · profit {inr(a['pnl'], True)}" if a["side"] == "sell" else f" · {a['kind']}"
        console.print(f"  [{colour}]{a['side'].upper()}[/] {a['qty']} {a['symbol']} @ ₹{a['price']:,.2f}{extra} · {a['why']}")
    if not actions:
        console.print("  no trades today")
    for n in notes:
        console.print(f"  [dim]· {n}[/]")
    real, wins, closed = ledger.realised()
    open_pnl = sum(p for p in (_pnl(h) for h in held.values()) if p is not None)
    console.print(f"\n  holding {len(held)} stocks · invested {inr(ledger.invested())} · open P&L {inr(open_pnl, True)} · "
                  f"booked {inr(real, True)} from {closed} sells")


def _report(mode, actions, notes, held, ledger) -> str:
    lines = [f"🛒 Nifty Shop · {ist_now().strftime('%a %d %b')} · {mode}"]
    for a in actions:
        if a["side"] == "sell":
            lines.append(f"SOLD {a['qty']} {a['symbol']} @ ₹{a['price']:,.2f} · profit {inr(a['pnl'], True)}")
        else:
            lines.append(f"BOUGHT {a['qty']} {a['symbol']} @ ₹{a['price']:,.2f} ({a['kind']})")
    if not actions:
        lines.append("No trades today.")
    lines += [f"· {n}" for n in notes[:5]]
    real, _, closed = ledger.realised()
    open_pnl = sum(p for p in (_pnl(h) for h in held.values()) if p is not None)
    lines.append(f"Holding {len(held)} · invested {inr(ledger.invested())} · open {inr(open_pnl, True)} · "
                 f"booked {inr(real, True)} ({closed} sells)")
    return "\n".join(lines)


def status_text() -> str:
    """For Telegram's /status."""
    try:
        mode = live_mode()
    except FirstockError:
        mode = "paper"
    ledger = Ledger(mode)
    held = ledger.holdings()
    try:
        last = json.loads(STATUS.read_text()).get("prices", {})
    except (OSError, ValueError):
        last = {}
    for sym, h in held.items():
        h["ltp"] = last.get(sym)
    session = load_session()
    today = ist_now().date().isoformat()
    run = ledger.ran(today)
    lines = [f"Nifty Shop · {mode} · {'logged in ✅' if session else 'NOT logged in today ❌'}"
             + (" · kill switch ON 🛑" if STOP_FILE.exists() else ""),
             f"Today: {run['status'] if run else 'runs at 15:18'}"]
    for sym, h in sorted(held.items()):
        chg = f"{h['ltp'] / h['avg'] - 1:+.1%}" if h.get("ltp") else "?"
        lines.append(f"{sym}: {h['qty']} @ ₹{h['avg']:,.2f} ({h['lots']} lots) {chg}")
    real, _, closed = ledger.realised()
    lines.append(f"Invested {inr(ledger.invested())} · booked {inr(real, True)} ({closed} sells)")
    return "\n".join(lines)


def _write_status(mode, ledger, scan, held, decision, actions, notes, scan_only: bool = False) -> None:
    real, wins, closed = ledger.realised()
    buy_amount, avg_amount, cap = amounts()
    payload = {
        "updated": time.time(), "mode": mode, "scan_only": scan_only, "strategy": strategy.DESCRIPTION,
        "settings": strategy.SETTINGS, "buy_amount": buy_amount, "average_amount": avg_amount, "max_capital": cap,
        "scan": scan, "decision": decision, "actions": actions, "notes": notes,
        "holdings": {s: {**h, "pnl": _pnl(h)} for s, h in held.items()},
        "prices": {x["symbol"]: x["ltp"] for x in scan} | {s: h["ltp"] for s, h in held.items() if h.get("ltp")},
        "invested": ledger.invested(), "realised": real, "wins": wins, "closed_count": closed,
        "closed": ledger.d["closed"][-60:], "runs": {d: ledger.d["runs"][d] for d in sorted(ledger.d["runs"])[-30:]},
    }
    RESULTS.mkdir(exist_ok=True)
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, default=str))
    os.replace(tmp, STATUS)


def remind() -> None:
    """14:30 on trading days: nudge you on Telegram if you haven't logged in yet."""
    now = ist_now()
    if now.weekday() >= 5:
        return
    if load_session():
        console.print("  logged in today: no reminder needed")
        return
    msg = ("⏰ Nifty Shop: you haven't logged in to Firstock today. Send /login followed by the 6-digit code "
           "from your authenticator app before 15:15, or there's no trade today.")
    console.print(f"  {msg}")
    if not telegram.send(msg):
        console.print("  [dim](Telegram isn't set up, so this only went to the log)[/]")
````

### `jev-shop/jevlab/backtest.py`

````python
"""Backtest: what the rules in strategy.py would have done over the last few years, with your
amounts, charges and capital cap. It runs the exact same decide() as the daily shop.

  uv run python -m jevlab backtest              # the last 5 years
  uv run python -m jevlab backtest --years 10   # as far back as Firstock's daily candles go

Uses Firstock's daily candles (needs today's login), cached in results/cache. Read the
result with care:
  * It uses TODAY's Nifty 50 for the whole period. Companies that dropped out of the
    index (often after falling a lot) are missing, which flatters a buy-the-dip strategy
    (survivorship bias). Treat the result as a best case.
  * Fills are at the day's close plus 0.1% slippage each way; the live shop trades at 15:18.
  * Splits and bonuses are detected from overnight price drops of about 1/2, 1/3, 1/5, 1/10
    and adjusted for. No dividends.
  * The news check can't be tested: there's no archive of old headlines.
"""

from __future__ import annotations

import csv
import json
import time
from datetime import date, timedelta

import pandas as pd

from . import strategy
from .core import RESULTS, console, header, inr, ist_now
from .firstock import FirstockError, SessionExpired, charges, daily_candles, load_session, trading_symbol
from .ledger import adjust_for_splits
from .shop import amounts
from .universe import nifty50

CACHE = RESULTS / "cache"
SLIPPAGE = 0.001


def _history(session, sym: str, tsym: str, start: date) -> pd.Series:
    """Daily closes for one stock, from the cache when it's fresh enough."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{sym}.csv"
    today = ist_now().date()
    if path.exists():
        df = pd.read_csv(path, parse_dates=["day"])
        s = pd.Series(df["close"].values, index=[d.date() for d in df["day"]])
        if len(s) and s.index[0] <= start + timedelta(days=10) and (today - s.index[-1]).days <= 4:
            return s[s.index >= start]
    df = daily_candles(session, tsym, start, today - timedelta(days=1))
    df[["close"]].rename_axis("day").to_csv(path)
    time.sleep(0.1)
    return df["close"]


def _adjust_splits(s: pd.Series) -> pd.Series:
    s = s.dropna()
    return pd.Series(adjust_for_splits(list(s.values)), index=s.index)


def simulate(closes: pd.DataFrame, buy_amount: float, avg_amount: float, cap: float) -> dict:
    n = strategy.SETTINGS["dma_days"]
    dma = closes.rolling(n, min_periods=n).mean()
    lots: dict[str, list[dict]] = {}
    last_px: dict[str, float] = {}
    realised = fees = 0.0
    trades, curve = [], []
    buys = {"new": 0, "average": 0}
    for day in closes.index:
        row, drow = closes.loc[day], dma.loc[day]
        for sym, p in row.items():
            if pd.notna(p):
                last_px[sym] = float(p)
        scan = sorted(({"symbol": s, "ltp": float(row[s]), "dma": float(drow[s]), "gap": float(row[s] / drow[s] - 1)}
                       for s in closes.columns if pd.notna(row[s]) and pd.notna(drow[s])), key=lambda x: x["gap"])
        if not scan:
            continue
        held = {}
        for sym, ls in lots.items():
            qty = sum(l["qty"] for l in ls)
            cost = sum(l["qty"] * l["price"] for l in ls)
            held[sym] = {"qty": qty, "avg": cost / qty, "cost": cost, "last_buy": ls[-1]["price"], "lots": len(ls),
                         "ltp": last_px.get(sym)}
        d = strategy.decide(scan, held, buy_amount, avg_amount)
        if d["sell"]:
            sym = d["sell"]["symbol"]
            h, px = held[sym], held[sym]["ltp"] * (1 - SLIPPAGE)
            fee = charges("sell", h["qty"] * px)
            buy_fees = sum(l["fees"] for l in lots[sym])
            pnl = h["qty"] * px - h["cost"] - buy_fees - fee
            realised += pnl
            fees += fee
            trades.append({"symbol": sym, "bought": lots[sym][0]["date"], "sold": day, "lots": h["lots"], "qty": h["qty"],
                           "avg": round(h["avg"], 2), "price": round(px, 2), "pnl": round(pnl, 2),
                           "days": (day - lots[sym][0]["date"]).days})
            del lots[sym]
        invested = sum(l["qty"] * l["price"] for ls in lots.values() for l in ls)
        for b in d["buys"]:
            ltp = last_px[b["symbol"]]
            qty = int(b["amount"] // ltp)
            if qty < 1:
                continue
            px = ltp * (1 + SLIPPAGE)
            if invested + qty * px > cap:
                break
            fee = charges("buy", qty * px)
            fees += fee
            lots.setdefault(b["symbol"], []).append({"date": day, "qty": qty, "price": px, "fees": fee})
            buys[b["kind"]] += 1
            break
        invested = sum(l["qty"] * l["price"] for ls in lots.values() for l in ls)
        open_pnl = sum(l["qty"] * (last_px[s] - l["price"]) - l["fees"] for s, ls in lots.items() for l in ls)
        curve.append((day, invested, realised + open_pnl))

    if not curve:
        raise SystemExit("  not enough history to backtest")
    first, last = curve[0][0], curve[-1][0]
    years = max((last - first).days / 365.25, 1 / 365)
    peak = max(c[1] for c in curve) or 1.0
    total = curve[-1][2]
    running, max_dd = float("-inf"), 0.0
    for _, _, pnl in curve:
        running = max(running, pnl)
        max_dd = max(max_dd, running - pnl)
    open_pos = []
    for sym, ls in lots.items():
        qty = sum(l["qty"] for l in ls)
        cost = sum(l["qty"] * l["price"] for l in ls)
        open_pos.append({"symbol": sym, "lots": len(ls), "cost": round(cost, 2), "change": round(last_px[sym] * qty / cost - 1, 4),
                         "days": (last - ls[0]["date"]).days})
    wins = [t for t in trades if t["pnl"] > 0]
    days_held = sorted(t["days"] for t in trades)
    return {
        "from": str(first), "to": str(last), "years": round(years, 2), "stocks": len(closes.columns),
        "buy_amount": buy_amount, "average_amount": avg_amount, "max_capital": cap,
        "new_buys": buys["new"], "averages": buys["average"], "sells": len(trades),
        "win_rate": round(len(wins) / len(trades), 3) if trades else None,
        "median_days_held": days_held[len(days_held) // 2] if days_held else None,
        "realised": round(realised, 2), "open_pnl": round(total - realised, 2), "total_pnl": round(total, 2),
        "charges": round(fees, 2), "peak_invested": round(peak, 2),
        "return_on_peak": round(total / peak, 4),
        "annualised_on_peak": round((1 + total / peak) ** (1 / years) - 1, 4) if total > -peak else -1.0,
        "max_drawdown": round(max_dd, 2), "max_drawdown_on_peak": round(max_dd / peak, 4),
        "open_positions": sorted(open_pos, key=lambda x: x["change"]),
        "curve": [[str(d), round(i, 2), round(p, 2)] for d, i, p in curve[::5]],
        "trades": trades,
    }


def run_backtest(years: float) -> None:
    buy_amount, avg_amount, cap = amounts()
    header("NIFTY SHOP BACKTEST", f"{strategy.DESCRIPTION} · {inr(buy_amount)} a buy, {inr(avg_amount)} an average · "
           f"capital cap {inr(cap)} · last {years:g} years · closes + 0.1% slippage · delivery charges")
    session = load_session()
    if not session:
        raise SystemExit("  not logged in to Firstock today (the price history comes from Firstock). "
                         "Run: uv run python -m jevlab login")
    universe, source = nifty50()
    start = ist_now().date() - timedelta(days=int(years * 365.25) + 3 * strategy.SETTINGS["dma_days"])
    console.print(f"  loading daily history for {len(universe)} stocks ({source})…")
    series, missing = {}, []
    try:
        for sym in sorted(universe):
            try:
                s = _history(session, sym, trading_symbol(sym), start)
            except SessionExpired:
                raise
            except FirstockError as exc:
                missing.append(f"{sym} ({str(exc)[:40]})")
                continue
            if len(s) > strategy.SETTINGS["dma_days"]:
                series[sym] = _adjust_splits(s)
        try:
            nifty = _history(session, "NIFTY", "NIFTY", start)
        except FirstockError:
            nifty = pd.Series(dtype=float)
    except SessionExpired:
        raise SystemExit("  your Firstock session has ended. Log in again and re-run.")
    if not series:
        raise SystemExit("  no price history came back from Firstock")
    closes = pd.DataFrame(series).sort_index()
    r = simulate(closes, buy_amount, avg_amount, cap)
    if len(nifty) > 1:
        nifty = nifty[nifty.index >= date.fromisoformat(r["from"])]
        if len(nifty) > 1:
            r["nifty_change"] = round(float(nifty.iloc[-1] / nifty.iloc[0] - 1), 4)
            r["nifty_annualised"] = round(float((nifty.iloc[-1] / nifty.iloc[0]) ** (1 / r["years"]) - 1), 4)
    r["missing"], r["universe_source"] = missing, source

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "backtest.json").write_text(json.dumps({k: v for k, v in r.items() if k != "trades"}, default=str))
    with open(RESULTS / "backtest_trades.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "bought", "sold", "days", "lots", "qty", "avg", "price", "pnl"])
        w.writeheader()
        w.writerows(r["trades"])

    console.print(f"\n  {r['from']} → {r['to']} ({r['years']} years) · {r['stocks']} stocks")
    console.print(f"  {r['new_buys']} new buys · {r['averages']} averages · {r['sells']} sells · "
                  f"win rate {r['win_rate']:.0%}" if r["win_rate"] is not None else "  no completed trades")
    console.print(f"  profit booked {inr(r['realised'], True)} · still open {inr(r['open_pnl'], True)} · "
                  f"total [bold]{inr(r['total_pnl'], True)}[/] after {inr(r['charges'])} of charges")
    console.print(f"  most money ever invested at once {inr(r['peak_invested'])} · return on that "
                  f"{r['return_on_peak']:+.1%} · about {r['annualised_on_peak']:+.1%} a year")
    console.print(f"  worst drawdown {inr(r['max_drawdown'])} ({r['max_drawdown_on_peak']:.1%} of the peak invested) · "
                  f"median holding {r['median_days_held']} days")
    if "nifty_annualised" in r:
        console.print(f"  NIFTY itself over the same period: {r['nifty_change']:+.1%} (about {r['nifty_annualised']:+.1%} a year, "
                      "before dividends)")
    stuck = [p for p in r["open_positions"] if p["change"] < -0.1]
    if stuck:
        console.print("  still stuck at the end: " + ", ".join(f"{p['symbol']} {p['change']:+.0%} ({p['lots']} lots, "
                                                               f"{p['days']} days)" for p in stuck[:6]))
    if missing:
        console.print(f"  [dim]no history for: {', '.join(missing[:6])}[/]")
    console.print("  [dim]today's Nifty 50 used for the whole period: a best case (survivorship bias). "
                  "Trades: results/backtest_trades.csv[/]")
````

### `jev-shop/jevlab/news.py`

````python
"""The news check: before buying a stock, Jev reads the last day and a half of Indian market
headlines that mention the company, and vetoes the buy if one of them is serious bad news
(fraud, a regulator's ban, a collapse in results). The Nifty Shop buys dips; this avoids
buying the ones that are falling for a very good reason. Optional: it needs AI_GATEWAY_API_KEY,
and NEWS_CHECK=off in .env switches it off. It costs a fraction of a cent a day.
A vetoed stock is treated as if it weren't in the Nifty 50 that day, so the shop moves on to the next one.
"""

from __future__ import annotations

import html
import os
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import pandas as pd
import requests

# If a feed stops working, swap in another markets feed from the same site.
FEEDS = {
    "economic times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "moneycontrol": "https://www.moneycontrol.com/rss/marketreports.xml",
    "livemint": "https://www.livemint.com/rss/markets",
    "business standard": "https://www.business-standard.com/rss/markets-106.rss",
}
WEAK = {"the", "india", "indian", "asian", "state", "bharat", "power", "coal", "sun", "max", "hindustan"}


def fetch_headlines(hours: float, quiet: bool = False) -> list[dict]:
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
    items, seen = [], set()
    for source, url in FEEDS.items():
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (jev-shop rss reader)"})
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as exc:
            if not quiet:
                print(f"  ! feed {source} unavailable: {str(exc)[:80]}")
            continue
        for it in root.iter("item"):
            title = html.unescape((it.findtext("title") or "").strip())
            pub = it.findtext("pubDate")
            if not title or not pub or title.lower() in seen:
                continue
            try:
                ts = pd.Timestamp(parsedate_to_datetime(pub))
                ts = (ts.tz_localize("Asia/Kolkata") if ts.tzinfo is None else ts).tz_convert("UTC")
            except (TypeError, ValueError):
                continue
            if ts < cutoff:
                continue
            summary = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))).strip()
            seen.add(title.lower())
            items.append({"source": source, "headline": title, "summary": summary[:400], "published": ts})
    return sorted(items, key=lambda x: x["published"])


def mentions(symbol: str, company: str, items: list[dict], limit: int = 6) -> list[dict]:
    """Headlines that name the company: by NSE symbol or name first ("Tata Steel"), then by the first word of
    its name ("Tata"), which also catches group-wide news. Jev then decides whether it's really about them."""
    name = re.sub(r"\b(limited|ltd)\b\.?", "", company, flags=re.I).strip(" .").lower()
    words = name.split()
    strong = {symbol.lower(), name} | ({" ".join(words[:2])} if len(words) >= 2 else set())
    weak = {words[0]} if words and len(words[0]) >= 4 and words[0] not in WEAK else set()

    def hit(keys, it):
        text = (it["headline"] + " " + it["summary"]).lower()
        return any(re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", text) for k in keys if len(k) >= 2)

    first = [it for it in items if hit(strong, it)]
    second = [it for it in items if it not in first and hit(weak, it)]
    return (first[-limit:] + second[-limit:])[:limit]


def check_enabled() -> bool:
    return os.getenv("NEWS_CHECK", "on").strip().lower() not in ("off", "false", "0", "no")


def veto(jev, symbol: str, company: str, items: list[dict]) -> str | None:
    """The headline that makes Jev say "don't buy", or None."""
    q = {"impact": {"type": "choice",
                    "instructions": f"How does this news affect {company} (NSE: {symbol}) shares over the next few weeks?",
                    "criteria": {"serious_bad_news": None, "mildly_negative": None, "neutral_or_positive": None,
                                 "not_about_this_company": None}}}
    for it in mentions(symbol, company, items):
        try:
            ans, _ = jev.ask({"headline": it["headline"], "summary": it["summary"], "source": it["source"]}, q,
                             timeout=15, retries=2)
        except Exception:
            continue
        a = ans["impact"]
        if a["choice"] == "serious_bad_news" and a["probs"].get("serious_bad_news", 0) >= 0.6:
            return it["headline"]
    return None
````

### `jev-shop/jevlab/judges.py`

````python
"""The Jev client. Sends one state plus typed questions, gets typed answers back.

Jev question types (TypeSafe systemone API):
  noul    yes/no, answered as a probability of "yes"
  choice  pick one option from a dict of options
  score   pick a level from a list ordered low -> high

Answers are normalised to:
  noul   -> {"p": float}
  choice -> {"choice": str, "probs": {option: float}}
  score  -> {"score": float (0-based level, may be an expected value), "probs": [float, ...]}

Reaches Jev through the Vercel AI Gateway (AI_GATEWAY_API_KEY), or directly with a
TypeSafe key (TYPESAFE_API_KEY) if you have one.
"""

from __future__ import annotations

import os
import random
import time

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

JEV_GATEWAY_URL = "https://ai-gateway.vercel.sh/typesafe/v1/systemone"
JEV_DIRECT_URL = "https://api.typesafe.ai/v1/systemone"


class JudgeError(Exception):
    pass


def _post(url: str, key: str, body: dict, timeout: float, retries: int = 6) -> dict:
    for attempt in range(retries + 1):
        retry_after = None
        try:
            r = requests.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=body,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            if attempt == retries:
                raise JudgeError(str(exc)) from exc
        else:
            if r.status_code == 200:
                return r.json()
            if r.status_code not in (429, 500, 502, 503, 529) or attempt == retries:
                raise JudgeError(f"HTTP {r.status_code}: {r.text[:300]}")
            retry_after = r.headers.get("retry-after")
        # 429 = the free tier is busy. Back off (honouring Retry-After) rather than drop the call.
        try:
            wait = float(retry_after)
        except (TypeError, ValueError):
            wait = min(8.0, 0.75 * 2**attempt) + random.random()
        time.sleep(wait)
    raise JudgeError("unreachable")


# ---------------------------------------------------------------- normalising

def _norm_probs(raw, options: list[str]) -> dict:
    if isinstance(raw, dict):
        probs = {o: float(raw.get(o, 0.0)) for o in options}
    elif isinstance(raw, list) and len(raw) == len(options):
        probs = dict(zip(options, map(float, raw)))
    else:
        return {}
    total = sum(probs.values())
    return {o: p / total for o, p in probs.items()} if total > 0 else {}


def normalise(questions: dict, raw_answers: dict) -> dict:
    """Coerce any judge's raw answers into the one shape the labs score."""
    out = {}
    for qid, q in questions.items():
        a = raw_answers.get(qid)
        if a is None:
            raise JudgeError(f"missing answer for '{qid}'")
        if q["type"] == "noul":
            p = a.get("noul", a.get("p")) if isinstance(a, dict) else a
            out[qid] = {"p": max(0.0, min(1.0, float(p)))}
        elif q["type"] == "choice":
            options = list(q["criteria"])
            probs = _norm_probs(a.get("probabilities", a.get("probs")), options)
            choice = a.get("choice")
            if choice not in options:
                if not probs:
                    raise JudgeError(f"bad choice answer for '{qid}': {a}")
                choice = max(probs, key=probs.get)
            if not probs:
                probs = {o: float(o == choice) for o in options}
            out[qid] = {"choice": choice, "probs": probs}
        elif q["type"] == "score":
            # Jev returns score as an expected level (e.g. 1.69) with probabilities
            # keyed "0".."n-1"; other judges may return a label or an index.
            levels = q["criteria"]
            score = a.get("score")
            if isinstance(score, str):
                score = levels.index(score) if score in levels else float(score)
            raw_p = a.get("probabilities", a.get("probs"))
            if isinstance(raw_p, dict) and all(str(k).isdigit() for k in raw_p):
                raw_p = {levels[int(k)]: v for k, v in raw_p.items() if int(k) < len(levels)}
            probs_d = _norm_probs(raw_p, levels)
            probs = [probs_d.get(l, 0.0) for l in levels] if probs_d else [
                float(i == round(float(score))) for i in range(len(levels))
            ]
            out[qid] = {"score": max(0.0, min(len(levels) - 1.0, float(score))), "probs": probs}
    return out


# ---------------------------------------------------------------- judges

class JevJudge:
    name = "jev"

    def __init__(self):
        direct = os.getenv("TYPESAFE_API_KEY", "").strip()
        gateway = os.getenv("AI_GATEWAY_API_KEY", "").strip()
        if direct:
            self.url, self.key, self.model = JEV_DIRECT_URL, direct, "jev-latest"
        elif gateway:
            self.url, self.key, self.model = JEV_GATEWAY_URL, gateway, "typesafe-ai/jev"
        else:
            raise JudgeError("no AI_GATEWAY_API_KEY or TYPESAFE_API_KEY in .env")

    def ask(self, state, questions, timeout=20.0, retries=6):
        t0 = time.monotonic()
        body = {"state": state, "model": self.model, "questions": questions}
        data = _post(self.url, self.key, body, timeout, retries)
        ms = (time.monotonic() - t0) * 1000
        answers = normalise(questions, data.get("answers", data))
        return answers, {"judge": self.name, "model": data.get("model", self.model), "latency_ms": round(ms)}
````

### `jev-shop/jevlab/telegram.py`

````python
"""Telegram: the daily report on your phone, a reminder if you haven't logged in, and the
daily Firstock login by message.

Set TELEGRAM_BOT_TOKEN (from @BotFather) and TELEGRAM_CHAT_ID (your own chat) in .env.
The listener (`uv run python -m jevlab telegram`, a service on the server) answers only
your chat:
  /login 123456   log in to Firstock with the 6-digit code from your authenticator app
  /status         today's login, holdings and P&L
  /stop           kill switch: no orders until /resume
  /resume         allow orders again
"""

from __future__ import annotations

import os
import time

import requests

API = "https://api.telegram.org"


def _conf() -> tuple[str, str]:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), os.getenv("TELEGRAM_CHAT_ID", "").strip()


def enabled() -> bool:
    token, chat = _conf()
    return bool(token and chat)


def _call(method: str, timeout: float = 15, **params):
    token, _ = _conf()
    r = requests.post(f"{API}/bot{token}/{method}", json=params, timeout=timeout)
    return r.json()


def send(text: str) -> bool:
    if not enabled():
        return False
    try:
        return bool(_call("sendMessage", chat_id=_conf()[1], text=text[:4000]).get("ok"))
    except (requests.RequestException, ValueError):
        return False


def listen() -> None:
    from . import firstock
    from .core import console
    from .shop import STOP_FILE, status_text
    if not enabled():
        raise SystemExit("  set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first")
    token, chat = _conf()
    console.print("  listening for your Telegram messages: /login 123456 · /status · /stop · /resume")
    offset = None
    while True:
        try:
            r = requests.get(f"{API}/bot{token}/getUpdates", params={"timeout": 50, "offset": offset}, timeout=65)
            updates = r.json().get("result", [])
        except (requests.RequestException, ValueError):
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            if str(msg.get("chat", {}).get("id")) != chat:
                continue  # not you: ignore
            text = (msg.get("text") or "").strip()
            cmd, _, arg = text.partition(" ")
            cmd = cmd.lower().split("@")[0]
            if cmd == "/login":
                try:
                    _call("deleteMessage", chat_id=chat, message_id=msg.get("message_id"))  # don't leave the code lying around
                except (requests.RequestException, ValueError):
                    pass
                try:
                    s = firstock.login(arg)
                    send(f"✅ Logged in to Firstock as {s.name}. Today's shop runs at 15:18.")
                except firstock.FirstockError as exc:
                    send(f"❌ Firstock said no: {exc}. Codes change every 30 seconds: send a fresh one.")
            elif cmd == "/status":
                send(status_text())
            elif cmd == "/stop":
                STOP_FILE.touch()
                send("🛑 Kill switch on: the shop places no orders until you send /resume.")
            elif cmd == "/resume":
                STOP_FILE.unlink(missing_ok=True)
                send("▶️ Kill switch off: the shop trades again at the next 15:18 run.")
            else:
                send("Commands: /login 123456 · /status · /stop · /resume")


def whoami() -> None:
    """Print the chat ID of whoever last messaged your bot (so you can put yours in TELEGRAM_CHAT_ID)."""
    from .core import console
    token = _conf()[0]
    if not token:
        raise SystemExit("  put TELEGRAM_BOT_TOKEN in .env first")
    try:
        res = requests.get(f"{API}/bot{token}/getUpdates", timeout=15).json()
    except (requests.RequestException, ValueError):
        raise SystemExit("  couldn't reach Telegram")
    if not res.get("ok"):
        raise SystemExit("  Telegram rejected the token: check TELEGRAM_BOT_TOKEN in .env")
    chats = {}
    for u in res.get("result", []):
        chat = (u.get("message") or {}).get("chat") or {}
        if chat.get("id"):
            chats[chat["id"]] = chat.get("first_name") or chat.get("username") or chat.get("title") or ""
    if not chats:
        console.print("  no messages yet: open your bot in Telegram, send it any message (say \"hi\"), then run this again")
    for cid, name in chats.items():
        console.print(f"  chat {cid} · {name}  ← put this number after TELEGRAM_CHAT_ID=")
````

### `jev-shop/jevlab/server.py`

````python
"""A tiny local web server for the dashboards, on 127.0.0.1 only.

It serves the dashboard pages and the two status files they read, and nothing else:
never .env, never results/session.json (your Firstock session), never the ledgers.
"""

from __future__ import annotations

import posixpath
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = ("/results/shop.json", "/results/backtest.json")


class _Handler(SimpleHTTPRequestHandler):
    page = "shop.html"  # which dashboard "/" opens

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        path = posixpath.normpath(unquote(self.path.split("?", 1)[0].split("#", 1)[0]))
        if path in ("/", "/index.html"):
            self.path = f"/dashboard/{self.page}"
        elif not (path in ALLOWED or path.startswith("/dashboard/")):
            self.send_error(404)
            return
        return super().do_GET()

    def do_HEAD(self):
        self.send_error(405)

    def log_message(self, *args):  # keep the terminal clean
        pass


def serve(port: int = 8765, open_browser: bool = True, page: str = "shop.html") -> ThreadingHTTPServer:
    handler = type("Handler", (_Handler,), {"page": page})
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), partial(handler, directory=str(ROOT)))
    except OSError:
        raise SystemExit(f"  port {port} is busy. Stop the other dashboard (Ctrl+C) or add --port {port + 1}")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    print(f"  dashboard: {url}")
    if open_browser:
        webbrowser.open(url)
    return server
````

### `jev-shop/deploy/install.sh`

````bash
#!/usr/bin/env bash
# Installs the shop's timers on the server (Ubuntu). From the project folder:
#     sudo bash deploy/install.sh
# Works whether you log in as root (most VPS providers) or as ubuntu (Oracle Cloud).
#   jev-shop.timer      the daily run, 15:18 India time, Monday to Friday
#   jev-remind.timer    a Telegram nudge at 14:30 if you haven't logged in to Firstock yet
#   jev-telegram        listens for /login, /status, /stop, /resume (only if Telegram is set up in .env)
# Undo: sudo systemctl disable --now jev-shop.timer jev-remind.timer jev-telegram
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$(id -un)}"
HOME_DIR="$(getent passwd "$RUN_USER" | cut -d: -f6)"
UV="$HOME_DIR/.local/bin/uv"
[ -x "$UV" ] || UV="$(command -v uv || true)"
if [ -z "$UV" ] || [ ! -x "$UV" ]; then
  echo "uv isn't installed for $RUN_USER: run  curl -LsSf https://astral.sh/uv/install.sh | sh  first"; exit 1
fi
[ -f "$DIR/.env" ] || { echo "no .env in $DIR: copy it up first"; exit 1; }
UNIT_DIR="${UNIT_DIR:-/etc/systemd/system}"

service() {  # name, description, command, type
  cat > "$UNIT_DIR/$1.service" <<EOF
[Unit]
Description=$2
After=network-online.target
Wants=network-online.target

[Service]
Type=$4
User=$RUN_USER
WorkingDirectory=$DIR
ExecStart=$UV run python -m jevlab $3
Environment=PYTHONUNBUFFERED=1
EOF
}

timer() {  # name, description, time of day
  cat > "$UNIT_DIR/$1.timer" <<EOF
[Unit]
Description=$2

[Timer]
OnCalendar=Mon..Fri *-*-* $3 Asia/Kolkata
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF
}

service jev-shop "Nifty Shop: the daily run" run oneshot
echo "TimeoutStartSec=900" >> "$UNIT_DIR/jev-shop.service"
timer jev-shop "Run the Nifty Shop at 15:18 India time on weekdays" 15:18:00

service jev-remind "Nifty Shop: remind me to log in" remind oneshot
timer jev-remind "Remind me to log in to Firstock at 14:30 India time on weekdays" 14:30:00

TELEGRAM=""
if grep -Eq '^TELEGRAM_BOT_TOKEN=.+' "$DIR/.env" && grep -Eq '^TELEGRAM_CHAT_ID=.+' "$DIR/.env"; then
  TELEGRAM=1
  service jev-telegram "Nifty Shop: Telegram commands (/login, /status, /stop, /resume)" telegram simple
  printf 'Restart=always\nRestartSec=10\n\n[Install]\nWantedBy=multi-user.target\n' >> "$UNIT_DIR/jev-telegram.service"
fi

echo "wrote the units to $UNIT_DIR (running as $RUN_USER, project in $DIR)"
if [ -n "${NO_SYSTEMCTL:-}" ]; then exit 0; fi
systemctl daemon-reload
systemctl enable --now jev-shop.timer jev-remind.timer
if [ -n "$TELEGRAM" ]; then
  systemctl enable jev-telegram.service
  systemctl restart jev-telegram.service
  echo "Telegram listener running"
else
  echo "Telegram isn't set up in .env, so no listener (log in with: uv run python -m jevlab login)"
fi
systemctl list-timers 'jev-*' --no-pager
````

### `jev-shop/dashboard/shop.html`

````html
<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nifty Shop</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#06080c;--panel:#0e131a;--line:#1a222d;--line2:#253041;--fg:#e9eef4;--muted:#8a95a5;--dim:#586272;
--jev:#8b7bff;--good:#3fd68a;--bad:#ff5d6c;--amber:#f5b53d;--mono:"JetBrains Mono",ui-monospace,monospace}
*{box-sizing:border-box}
body{margin:0;color:var(--fg);font:14px/1.45 Inter,-apple-system,BlinkMacSystemFont,sans-serif;-webkit-font-smoothing:antialiased;
background:radial-gradient(1000px 520px at 90% -15%,rgba(139,123,255,.16),transparent 60%),var(--bg);min-height:100vh}
.app{max-width:1500px;margin:0 auto;padding:16px 18px 24px;display:grid;gap:12px}
header{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.brand{font:800 23px/1 Inter;letter-spacing:-.025em}
.brand em{font-style:normal;background:linear-gradient(95deg,var(--jev),#d6ccff);-webkit-background-clip:text;background-clip:text;color:transparent}
.spacer{flex:1}
.pill{font:500 11.5px var(--mono);padding:6px 10px;border-radius:999px;border:1px solid var(--line2);color:var(--muted);background:rgba(12,16,22,.7)}
.pill.live{color:var(--bad);border-color:rgba(255,93,108,.5)} .pill.paper{color:var(--amber);border-color:rgba(245,181,61,.45)}
.tiles{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.card{background:linear-gradient(180deg,rgba(14,19,26,.95),rgba(12,16,22,.95));border:1px solid var(--line);border-radius:16px;padding:14px 16px;min-width:0}
.tile span{display:block;font-size:11.5px;color:var(--muted)} .tile b{font:700 24px/1.25 var(--mono);letter-spacing:-.02em}
.tile small{display:block;font:12px var(--mono);color:var(--dim)}
.bar{height:7px;border-radius:99px;background:var(--line);overflow:hidden;margin-top:6px} .bar i{display:block;height:100%;background:var(--jev);border-radius:99px}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.35fr);gap:12px;align-items:start}
.eyebrow{font:600 10.5px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--dim);margin-bottom:10px}
table{width:100%;border-collapse:collapse;font:12.5px var(--mono)}
th{color:var(--dim);font-weight:400;text-align:left;padding:5px 6px;border-bottom:1px solid var(--line)}
td{padding:6px;border-bottom:1px solid rgba(26,34,45,.6);white-space:nowrap} td.r,th.r{text-align:right}
.g{color:var(--good)} .r{color:var(--bad)} .a{color:var(--amber)} .d{color:var(--dim)}
.act{font:600 13.5px/1.6 var(--mono)} .note{font:12px/1.6 var(--mono);color:var(--muted)}
.gap{display:inline-block;height:8px;border-radius:4px;background:var(--bad);opacity:.75;vertical-align:middle;margin-right:6px}
.prog{position:relative;height:8px;border-radius:99px;background:var(--line);width:120px;display:inline-block;vertical-align:middle}
.prog i{position:absolute;top:0;bottom:0;border-radius:99px}
.prog .t{position:absolute;right:0;top:-3px;bottom:-3px;width:2px;background:var(--good)}
.chart{height:190px;position:relative} .chart svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.ax{fill:var(--dim);font:10.5px var(--mono)}
.empty{color:var(--dim);font:13px var(--mono);padding:10px 0}
@media (max-width:1000px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.hideS{display:none}}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand"><em>Nifty</em> Shop</div>
    <div class="pill" id="mode">—</div>
    <div class="spacer"></div>
    <div class="pill" id="strat">—</div>
    <div class="pill" id="updated">waiting for the first run…</div>
  </header>
  <div class="tiles">
    <div class="card tile"><span>Invested now</span><b id="tInv">–</b><div class="bar"><i id="tCap" style="width:0"></i></div><small id="tCapTxt"></small></div>
    <div class="card tile"><span>Open P&amp;L</span><b id="tOpen">–</b><small id="tOpenPct"></small></div>
    <div class="card tile"><span>Profit booked</span><b id="tReal">–</b><small id="tSells"></small></div>
    <div class="card tile"><span>Holdings</span><b id="tHold">–</b><small id="tLots"></small></div>
    <div class="card tile"><span>Per buy</span><b id="tAmt">–</b><small id="tAvgAmt"></small></div>
  </div>
  <div class="grid">
    <div style="display:grid;gap:12px">
      <div class="card"><div class="eyebrow" id="todayTitle">Today</div><div id="today" class="empty">no run yet</div></div>
      <div class="card"><div class="eyebrow">Furthest below the 20-DMA · ★ = the 5 candidates</div>
        <table><thead><tr><th>#</th><th>stock</th><th class="r">price</th><th class="r">vs DMA</th><th></th></tr></thead><tbody id="scan"></tbody></table></div>
    </div>
    <div style="display:grid;gap:12px">
      <div class="card"><div class="eyebrow">What you hold</div>
        <table><thead><tr><th>stock</th><th class="r">shares</th><th class="r">avg</th><th class="r">now</th><th class="r">P&amp;L</th><th>to target</th><th class="r hideS">lots</th><th class="r hideS">since</th></tr></thead><tbody id="hold"></tbody></table></div>
      <div class="card"><div class="eyebrow">Sold (most recent first)</div>
        <table><thead><tr><th>stock</th><th class="r">shares</th><th class="r">avg</th><th class="r">sold at</th><th class="r">profit</th><th class="r hideS">bought → sold</th></tr></thead><tbody id="closed"></tbody></table></div>
      <div class="card" id="btCard" style="display:none"><div class="eyebrow" id="btTitle">Backtest</div><div class="note" id="btText"></div><div class="chart" id="btChart"></div></div>
    </div>
  </div>
</div>
<script>
const $ = (id) => document.getElementById(id);
const IN = (v, d = 2) => Number(v).toLocaleString("en-IN", {minimumFractionDigits: d, maximumFractionDigits: d});
const inr = (v, sign) => (v < 0 ? "−₹" : sign ? "+₹" : "₹") + IN(Math.abs(v));
const pct = (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(100 * v).toFixed(d) + "%";
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const tone = (v) => v > 0 ? "g" : v < 0 ? "r" : "";

async function load(path) { try { const r = await fetch(path + "?_=" + Date.now(), {cache: "no-store"}); return r.ok ? r.json() : null; } catch (e) { return null; } }

function render(S) {
  $("mode").textContent = S.scan_only ? `${S.mode} · scan only` : S.mode === "live" ? "LIVE · real money" : "paper";
  $("mode").className = "pill " + (S.mode === "live" ? "live" : "paper");
  $("strat").textContent = S.strategy;
  $("updated").textContent = "updated " + new Date(S.updated * 1000).toLocaleString("en-IN", {weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata"}) + " IST";
  const H = Object.entries(S.holdings || {}), target = S.settings.target;
  const open = H.reduce((a, [, h]) => a + (h.pnl || 0), 0);
  $("tInv").textContent = inr(S.invested); $("tCap").style.width = Math.min(100, 100 * S.invested / S.max_capital) + "%";
  $("tCapTxt").textContent = `${Math.round(100 * S.invested / S.max_capital)}% of the ${inr(S.max_capital)} cap`;
  $("tOpen").textContent = inr(open, true); $("tOpen").className = tone(open); $("tOpenPct").textContent = S.invested ? pct(open / S.invested) + " on what's invested" : "";
  $("tReal").textContent = inr(S.realised, true); $("tReal").className = tone(S.realised); $("tSells").textContent = `${S.closed_count} sells · ${S.wins} with a profit`;
  $("tHold").textContent = H.length; $("tLots").textContent = H.reduce((a, [, h]) => a + h.lots, 0) + " lots";
  $("tAmt").textContent = inr(S.buy_amount); $("tAvgAmt").textContent = `${inr(S.average_amount)} per average`;

  const acts = (S.actions || []).map((a) => a.side === "sell"
    ? `<div class="act"><span class="g">SOLD</span> ${a.qty} ${esc(a.symbol)} @ ₹${IN(a.price)} · profit <span class="${tone(a.pnl)}">${inr(a.pnl, true)}</span></div><div class="note">${esc(a.why)}</div>`
    : `<div class="act"><span style="color:var(--jev)">BOUGHT</span> ${a.qty} ${esc(a.symbol)} @ ₹${IN(a.price)} · ${a.kind}</div><div class="note">${esc(a.why)}</div>`);
  if (S.scan_only) {
    const s = S.decision.sell, b = (S.decision.buys || [])[0];
    acts.push(`<div class="act">would sell: ${s ? esc(s.symbol) + ` <span class="note">${esc(s.reason)}</span>` : "nothing"}</div>`,
              `<div class="act">would buy: ${b ? esc(b.symbol) + ` (${b.kind}) <span class="note">${esc(b.reason)}</span>` : "nothing"}</div>`);
  } else if (!acts.length) acts.push(`<div class="act d">no trades</div>`);
  $("todayTitle").textContent = S.scan_only ? "Right now (scan, no orders)" : "Today's run";
  $("today").className = ""; $("today").innerHTML = acts.join("") + (S.notes || []).map((n) => `<div class="note">· ${esc(n)}</div>`).join("");

  const scan = (S.scan || []).slice(0, 12), worst = Math.max(0.001, ...scan.map((x) => -x.gap));
  let starred = 0;
  $("scan").innerHTML = scan.map((x, i) => {
    const star = x.gap < 0 && starred < S.settings.candidates ? (starred++, "★") : "";
    const held = S.holdings[x.symbol] ? ` <span class="d">held</span>` : "";
    return `<tr><td class="d">${i + 1}</td><td>${star ? `<span class="a">★</span> ` : ""}${esc(x.symbol)}${held}</td><td class="r">₹${IN(x.ltp)}</td>` +
      `<td class="r ${tone(x.gap)}">${pct(x.gap, 2)}</td><td>${x.gap < 0 ? `<span class="gap" style="width:${(90 * -x.gap / worst).toFixed(0)}px"></span>` : ""}</td></tr>`;
  }).join("") || `<tr><td colspan="5" class="empty">no scan yet</td></tr>`;

  $("hold").innerHTML = H.sort((a, b) => (b[1].pnl || 0) / b[1].cost - (a[1].pnl || 0) / a[1].cost).map(([sym, h]) => {
    const ch = h.ltp ? h.ltp / h.avg - 1 : null, lo = -0.15;
    const w = ch === null ? 0 : Math.max(0, Math.min(1, (ch - lo) / (target - lo)));
    return `<tr><td>${esc(sym)}</td><td class="r">${h.qty}</td><td class="r">₹${IN(h.avg)}</td><td class="r">${h.ltp ? "₹" + IN(h.ltp) : "?"}</td>` +
      `<td class="r ${tone(h.pnl)}">${h.pnl == null ? "?" : inr(h.pnl, true)} <span class="d">${ch == null ? "" : pct(ch)}</span></td>` +
      `<td><span class="prog"><i style="left:0;width:${(100 * w).toFixed(0)}%;background:${ch >= 0 ? "var(--good)" : "var(--bad)"}"></i><span class="t"></span></span></td>` +
      `<td class="r hideS">${h.lots}</td><td class="r d hideS">${esc(h.first_buy)}</td></tr>`;
  }).join("") || `<tr><td colspan="8" class="empty">nothing yet: the first buy happens at the next 15:18 run</td></tr>`;

  $("closed").innerHTML = (S.closed || []).slice().reverse().slice(0, 15).map((c) =>
    `<tr><td>${esc(c.symbol)}</td><td class="r">${c.qty}</td><td class="r">₹${IN(c.avg)}</td><td class="r">₹${IN(c.price)}</td>` +
    `<td class="r ${tone(c.pnl)}">${inr(c.pnl, true)}</td><td class="r d hideS">${esc(c.first_buy)} → ${esc(c.sold)}</td></tr>`).join("") ||
    `<tr><td colspan="6" class="empty">no sells yet</td></tr>`;
}

function renderBacktest(B) {
  if (!B) return;
  $("btCard").style.display = "";
  $("btTitle").textContent = `Backtest · ${B.from} → ${B.to} · ${B.stocks} stocks`;
  $("btText").innerHTML = `${B.new_buys} buys + ${B.averages} averages · ${B.sells} sells · total <b class="${tone(B.total_pnl)}">${inr(B.total_pnl, true)}</b> after ${inr(B.charges)} charges · ` +
    `peak invested ${inr(B.peak_invested)} · about ${pct(B.annualised_on_peak)} a year on it · worst drawdown ${inr(B.max_drawdown)}` +
    (B.nifty_annualised != null ? ` · NIFTY ${pct(B.nifty_annualised)} a year` : "") + `<br><span class="d">today's Nifty 50 used for the whole period, so this is a best case</span>`;
  const el = $("btChart"), W = el.clientWidth, Hh = el.clientHeight, c = B.curve || [];
  if (c.length < 2 || W < 50) return;
  const l = 70, r = 10, t = 10, b = 20, ys = c.flatMap((p) => [p[1], p[2]]).concat([0]);
  const lo = Math.min(...ys), hi = Math.max(...ys);
  const X = (i) => l + i / (c.length - 1) * (W - l - r), Y = (v) => t + (hi - v) / ((hi - lo) || 1) * (Hh - t - b);
  const path = (k) => c.map((p, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(p[k]).toFixed(1)}`).join("");
  let s = `<svg viewBox="0 0 ${W} ${Hh}"><line x1="${l}" x2="${W - r}" y1="${Y(0)}" y2="${Y(0)}" stroke="#2e3949" stroke-dasharray="3 3"/>`;
  for (const v of [hi, lo]) s += `<text class="ax" x="${l - 8}" y="${Y(v) + 4}" text-anchor="end">${inr(v)}</text>`;
  s += `<path d="${path(1)}" fill="none" stroke="var(--dim)" stroke-width="1.4" stroke-dasharray="4 3"/><path d="${path(2)}" fill="none" stroke="var(--jev)" stroke-width="2.2"/>`;
  s += `<text class="ax" x="${l}" y="${Hh - 4}">${c[0][0]}</text><text class="ax" x="${W - r}" y="${Hh - 4}" text-anchor="end">${c.at(-1)[0]}</text>`;
  s += `<text x="${W - r}" y="${t + 10}" text-anchor="end" style="fill:var(--jev);font:600 10.5px var(--mono)">profit (after charges)</text>` +
       `<text x="${W - r}" y="${t + 24}" text-anchor="end" style="fill:var(--dim);font:600 10.5px var(--mono)">money invested</text></svg>`;
  el.innerHTML = s;
}

async function tick() {
  const S = await load("/results/shop.json");
  if (S) render(S);
  renderBacktest(await load("/results/backtest.json"));
}
tick(); setInterval(tick, 5000);
</script>
</body>
</html>
````
