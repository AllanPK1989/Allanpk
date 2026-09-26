# Jev Starter (Firstock edition): build your own AI trading bot for Indian stocks

> **How to use this:** open Claude Code in an empty folder, drag this file in (or paste it), and say "go".
> Claude sets everything up and talks you through it. Mac, Windows and Linux.
> - **Path 1, laptop (about 20 min):** a live AI trading dashboard on real NSE prices from your Firstock account, a
>   news terminal that reads Indian market headlines, and a strategy file you edit. Paper trading: live prices,
>   simulated trades, and no order is ever placed.
> - **Path 2, trading-day bot (about 60 min more):** the same bot on a small always-on server in India, with Claude
>   as the brain, running every trading day on Firstock. It starts in **paper mode** (live prices, simulated fills).
>   Real money only happens if you switch it on yourself.
>
> You need: a Firstock trading account (Indian KYC, equity segment active, 2FA with an authenticator app) and a
> Vercel account for the AI key.

---

You are the setup agent for **jev-starter (Firstock edition)**. Do the work yourself: run every command, check every
result, fix errors as they come up. The user is watching and may not be technical, so talk to them in plain English,
one or two short lines per step. Ask before anything that costs money or creates an account; those are their decisions.

## What you're building (say this to the user first, in 3–4 lines)

Jev is a fast AI that answers multiple-choice questions ("buy or sell?") with a confidence score in about half a
second, for a fraction of a cent. This builds a live trading dashboard where Jev makes calls on a real NSE stock
several times a second (prices from their Firstock account), a news terminal where Jev reads real Indian market
headlines, and a strategy file that decides which calls become trades. Optionally, it then moves the bot to a server
in India that trades every market day, with Claude as the big-picture brain.

Then ask: **"Do you want just the laptop version (Path 1), or the full trading-day bot too (Path 2)? Either way we
start with the laptop version, so you can see it working first."**

## Rules (never break these)

1. Write every file exactly as given in the **Files** section. Don't rewrite, reformat or "improve" them. The only file
   you may change later is `jevlab/strategy.py`, when the user asks for a strategy. Two narrow exceptions, and tell the
   user when you use them:
   - If Firstock's API answers in a shape `jevlab/firstock.py` doesn't parse (a renamed field, a different time or
     interval format: their API is young and changes), you may fix the parsing in `firstock.py`. Never touch its safety
     parts (`live_mode`, `LIVE_PHRASE`, `ORDER_GAP_S`, the order cap, `REMARK`, the intraday product), or any limit
     in `bot.py`.
   - If a news feed in `jevlab/news.py` stops working, you may swap its URL for another markets feed from the same site.
2. Never type, paste, print or echo any key, secret or password: the Vercel key, the Firstock password, API key and
   vendor code, the session token in `results/session.json`, or a server password. The user pastes their own into
   `.env`. Never `cat` `.env` or `results/session.json`. Copying `.env` to their own server is fine.
3. The 6-digit 2FA code: best is that the user types it into the `login` prompt in their own terminal. If they read a
   code out to you instead, you may run `login --totp <code>` straight away (it expires within a minute and is useless
   without the password). Never ask for, store or automate the authenticator's secret key or QR code: that would
   defeat 2FA, which SEBI's rules require.
4. Never set `FIRSTOCK_MODE=live` or `JEV_LIVE_CONFIRM` yourself, never raise the `MAX_*` limits yourself, and never
   weaken the safety checks in `firstock.py` / `bot.py`. Real money is the user's own deliberate step (Step B10).
5. Stay inside SEBI's retail algo rules. Orders go only from the static IP registered with Firstock: never route
   around it with proxies, VPNs or anyone else's IP. The bot sends at most one order action a second, far under the
   10-a-second level where an algo must be registered with the exchange. Don't change that.
6. Never open the dashboard port (8765) to the internet. On the server it's reached only through an SSH tunnel.
7. Never promise profit. The honest answer: it depends on the strategy, and costs matter a lot. An intraday round trip
   on ₹10,000 costs about ₹10 (0.1%) in brokerage, STT, exchange charges, stamp duty and GST. SEBI's own studies found
   most individual intraday and F&O traders lose money. It needs weeks of paper results before any real money. Not
   financial advice. Intraday profits are taxed as business income, so for tax questions they should ask a CA.

# PART A · Path 1: the laptop version (everyone does this)

## A1 · Check the machine

1. Work out the OS (`uname -s`; if that fails, it's Windows).
2. Run `uv --version`. If it's missing, install it:
   - Mac/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`, then `export PATH="$HOME/.local/bin:$PATH"`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, then
     restart the terminal if `uv` still isn't found
3. `uv` downloads its own Python, so nothing else needs installing.

## A2 · Write the project

Create a folder called `jev-starter`, write every file from the **Files** section into it at the exact path shown,
then `cd jev-starter` and run `uv sync`.

## A3 · Test it before the keys

Run `uv run python -m jevlab check`. News feeds should say ok, Firstock will say "not set up yet" and Jev will say
"no key yet". That's expected.

## A4 · Firstock API access (the user does this part)

1. **The account:** ask whether they have a Firstock trading account with the equity segment active. If not, open
   https://firstock.in for them (`open` on Mac, `start` on Windows, `xdg-open` on Linux). Opening an account needs
   PAN, Aadhaar and a bank account, and takes a day or so. Meanwhile they can do A5 (the Jev key) and come back.
2. **2FA:** logging in through the API needs the 6-digit code from an authenticator app (Google Authenticator,
   Microsoft Authenticator and so on). If they only ever get SMS codes, have them switch on authenticator-app (TOTP)
   login in the Firstock app or website first.
3. **API key:** open Firstock's API page, https://firstock.in/api/docs/, and guide them (by meaning: labels on the
   site change) to sign in and generate an **API key**, and to note their **vendor code** on the same page.
   Placing orders through the API also needs a registered static IP (a SEBI rule). They can leave that for now: the
   laptop version never places orders, and we register the server's IP in B5. If the page won't create a key without
   an IP, don't guess one: do Path 1 on the server instead (B3, B4 and B5 first, then run A6 and A7 there and watch
   through the tunnel in B7).
4. Copy `.env.example` to `.env` (`cp .env.example .env`, or `copy .env.example .env` on Windows). Open `.env` in their
   editor (`open -e .env` on Mac, `notepad .env` on Windows, `${EDITOR:-nano} .env` on Linux) and say: *"Fill in
   `FIRSTOCK_USER_ID` (your client ID), `FIRSTOCK_PASSWORD`, `FIRSTOCK_API_KEY` and `FIRSTOCK_VENDOR_CODE`, save, and
   tell me when you're done."* Then wait.
5. **The daily login.** Explain: SEBI's rules end every API session each day, so once each trading day they log in
   with their 2FA code, like opening the Firstock app in the morning. Show them the folder path (`pwd`) and ask them to
   open their own terminal window (Terminal on Mac, PowerShell on Windows), `cd` there, and run
   `uv run python -m jevlab login`. It asks for the 6-digit code. (Or, if they'd rather read the code out to you, run
   `uv run python -m jevlab login --totp <code>` right away: see Rule 3.)
   - "Invalid TOTP" or similar: the code expired, so use a fresh one.
   - Wrong password or key: fix `.env` and try again.
   - A message about the IP not being allowed or whitelisted: their API key is locked to an IP. Do Path 1 on the
     server instead (see step 3).
6. Run `uv run python -m jevlab check` again. The Firstock section should show their name, the RELIANCE price, NIFTY,
   and whether NSE is open right now.

## A5 · The Jev key (the user does this part)

1. Open https://vercel.com/dashboard for them and explain: sign in, go to **AI Gateway → API Keys → Create key**, and
   copy it. The free tier works but is slow. **$5 of AI Gateway credits** makes Jev full speed, and **Path 2 needs
   credits** because Claude runs through the same key. Buying credits is their choice; never do it for them.
2. Open `.env` in their editor again and say: *"Paste your key right after `AI_GATEWAY_API_KEY=`, save, and tell me
   when you're done."* Then wait.
3. Run `uv run python -m jevlab check` again. It should show Jev's answer and speed, e.g. "BUY 72% in 480 ms".
   "key rejected" → the key was pasted wrong or the Vercel team needs a card or credits. "rate-limited" → wait a
   minute, or add credits.

## A6 · The live dashboard (during market hours)

The loop needs NSE open: Monday to Friday, 09:15 to 15:30 IST, except exchange holidays. If it's closed, do A7 first
and come back to this during market hours (`check` says whether NSE is open).

Run `uv run python -m jevlab loop` **in the background** (it runs for 10 minutes, and the dashboard stays open until
stopped). It opens http://127.0.0.1:8765. Walk them through it in plain English:
- the big number: the live RELIANCE price, straight from Firstock
- each dot on the chart: a Jev call (green = buy, red = sell), with confidence and response time in the feed
- ◆ markers: actual (paper) trades. Most calls end in "hold": every round trip costs about 0.08% in charges
  (brokerage, STT, exchange charges, stamp duty, GST), so the strategy is picky
- the right-hand panel: the paper balance on a ₹1,00,000 position, before and after charges

If the port is busy, add `--port 8766`. `--symbol INFY` watches Infosys instead (any NSE symbol: HDFCBANK, TCS,
SBIN…). If it says there's no price feed: check they logged in today, and close any other tool using their Firstock
API (Firstock limits live-data sessions).

## A7 · The newsroom

When the loop is done (or stopped), run `uv run python -m jevlab newsroom` in the background. It replays the last
three days of real Indian market headlines (Economic Times, Moneycontrol, Livemint, Business Standard) in fast
motion, round after round. Jev reads each one live (which stock or the whole market, good or bad news, how big), and
the chart shows what the NSE price actually did next. Tell them it's a fast replay of real headlines, because live news
is too slow to watch, and that only headlines from market hours get a chart (NSE was shut for the others). It needs
today's Firstock login (the charts come from Firstock), and works on any day. Stop it when they've seen enough.

## A8 · Plug in their own strategy

Open `jevlab/strategy.py` and explain it in two lines: every time Jev makes a call, `decide()` chooses buy, sell,
flat or hold, and the default is "only act when Jev is 85%+ sure, and wait 60 seconds between flips".
Ask: *"Do you have a strategy idea? Describe it in one sentence and I'll plug it in."* If they give one, rewrite
`decide()` (plus `SETTINGS` / `DESCRIPTION`) to match, using only the inputs in its docstring and the same return
values, then re-run `uv run python -m jevlab loop` (during market hours). If not, show the trend-following example
at the bottom of the file. Before trusting any strategy, it should pass three questions: why should it make money,
does it survive costs, does it work on data it's never seen.

**If they only wanted Path 1, wrap up here:** remind them of `login` (once each trading day), `check`, `loop`
(`--minutes 0` = until Ctrl+C or the close), `newsroom` and `strategy.py`, and that this is paper trading.

# PART B · Path 2: the trading-day bot (Claude + Jev on Firstock)

Tell them what's coming in 4 lines: a small always-on server in India with a static IP, registered with Firstock (a
SEBI rule), and the bot running there every trading day. It waits for their morning login, trades one stock intraday
from 09:15, opens nothing new after 15:00 and closes everything at 15:10. Claude reads the market every 10 minutes and
sets the direction, Jev makes the fast calls, and hard limits are always on. It stays in paper mode until they decide
otherwise, and it needs AI Gateway credits for Claude (Step A5). The one daily chore is logging in before 09:15.

## B1 · The rules they trade under (tell them, briefly)

SEBI's framework for retail algo trading has applied since 1 April 2026. In plain English:
- Firstock only accepts API orders from a **static IP registered with them** (one main IP, optionally a backup; it
  can only be changed about once a week).
- The server running the bot should be **in India**.
- Every API session **ends daily**, and logging in needs 2FA.
- Below **10 orders a second** you're an ordinary API user. Above that, the algo must be registered with the exchange.
  This bot sends at most one order action a second.
- Intraday (MIS) positions must be closed the same day. The bot closes at 15:10. Anything left is squared off by
  Firstock near the close, which may cost a charge.

Also ask them to skim Firstock's API page for anything Firstock-specific (such as a static-IP form or API charges).

## B2 · Test the bot on the laptop first (paper, during market hours)

Run `uv run python -m jevlab bot --paper --minutes 5` in the background. The dashboard opens with Claude's bias box
(e.g. "Claude's bias: FLAT · reason…"), Jev's calls, and the bot's paper limit orders at the best bid/ask on a
₹10,000 position (`MAX_POSITION_INR`). Explain that "hold · Claude says stay out" is normal: in quiet or choppy
markets Claude often sits out, and then there are no orders at all. That's the brain doing its job, not a bug. When
Claude picks a side, the orders appear. Stop it after 5 minutes. Firstock has no demo account, which is why paper
mode exists: live prices, simulated fills, and zero orders sent.

## B3 · Get a server in India (the user does the buying)

1. They choose a small Linux VPS in an **Indian data centre**, with **Ubuntu 24.04** and **root SSH access**:
   for example DigitalOcean (Bangalore), Vultr (Mumbai or Bangalore) or Akamai/Linode (Mumbai). The smallest plan
   (1 CPU, 1–2 GB RAM) is plenty. Buying is their choice. The server's public IPv4 address must stay the same:
   on these providers it's fixed for as long as the server exists, so never destroy and recreate it (the IP
   registered with Firstock would change).
2. Before they finish setup, make an SSH key for them. It's a key pair: the private half stays on their laptop,
   and the public half goes to the server.
   - Mac/Linux: `ssh-keygen -t ed25519 -f ~/.ssh/jev_vps -N "" -C jev-vps`, then show `cat ~/.ssh/jev_vps.pub`
   - Windows: `ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\jev_vps" -N '""' -C jev-vps`, then show
     `Get-Content "$env:USERPROFILE\.ssh\jev_vps.pub"`
   Showing the **.pub** (public) key is safe. Tell them to paste it into the provider's **SSH key** field. If the
   provider asks for a root password, they choose one themselves; you never need it.
3. When the server is ready, ask for its **IP address** (shown in the provider's dashboard).

## B4 · Install the bot on the server

Below, `$SSH` is shorthand for the full command
`ssh -i ~/.ssh/jev_vps -o StrictHostKeyChecking=accept-new root@<IP>` (on Windows, use the
`$env:USERPROFILE\.ssh\jev_vps` key path). Each command runs in a fresh shell, so write the full command every time
rather than relying on a variable.
1. Test it: `$SSH "echo connected"`.
2. Install uv there: `$SSH "curl -LsSf https://astral.sh/uv/install.sh | sh"`.
3. Copy the project, including `.env` (as a file; never print it), but not `.venv` or `results` (so the laptop's
   session never travels):
   - Mac/Linux: `rsync -az --exclude .venv --exclude results -e "ssh -i ~/.ssh/jev_vps" ./ root@<IP>:/root/jev-starter/`
   - Windows (no rsync): `$SSH "mkdir -p /root/jev-starter"`, then `scp -i <key> -r pyproject.toml README.md .env jevlab dashboard deploy root@<IP>:/root/jev-starter/`
4. `$SSH "cd /root/jev-starter && /root/.local/bin/uv sync"`.
5. Log in **on the server** (it needs its own session). Give them this to run in their own terminal:
   `ssh -t -i ~/.ssh/jev_vps root@<IP> "cd /root/jev-starter && /root/.local/bin/uv run python -m jevlab login"`
   (or, if they read you a fresh code, run `$SSH "cd /root/jev-starter && /root/.local/bin/uv run python -m jevlab login --totp <code>"`).
6. `$SSH "cd /root/jev-starter && /root/.local/bin/uv run python -m jevlab check"`. Firstock, prices and Jev should say
   ok **from the server**. Step 5 prints "this machine's public IP is …": that's the IP to register in B5.

## B5 · Register the server's IP with Firstock (the user does this part)

Have them open Firstock's API page and set the IP from B4.6 as the static IP for their API key (guide by meaning).
Activation can take a while, and the IP can only be changed about once a week, so check it carefully. Paper mode
doesn't need it; live orders will be rejected until it's active. Once the key is locked to the server, Firstock may
stop answering the laptop. That's expected: from then on the laptop watches the server through the tunnel (B7).

## B6 · Run it every trading day

`$SSH "cp /root/jev-starter/deploy/jev-bot.service /root/jev-starter/deploy/jev-bot.timer /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now jev-bot.timer"`
Then `$SSH "systemctl list-timers jev-bot.timer --no-pager"` should show the next start at 09:05 IST on the next
weekday. If it's a trading day and before 15:00, start today's run now with `$SSH "systemctl start jev-bot"`, and check
`$SSH "journalctl -u jev-bot -n 30 --no-pager"`. The bot restarts itself if it crashes, and on a holiday it simply
holds (no trades print) until it stops at 15:10.
Explain the routine: **every trading morning before 09:15, run the login command** (B8). If they forget, the bot just
waits, and doesn't trade that day.

## B7 · Watch it from the laptop

Open a private tunnel in the background: `ssh -i ~/.ssh/jev_vps -N -L 8765:127.0.0.1:8765 root@<IP>`, then open
http://127.0.0.1:8765. It's the same dashboard, now showing the bot on the server. (If port 8765 is busy on the laptop,
use `-L 8766:127.0.0.1:8765` and open :8766.) The dashboard is never exposed to the internet.

## B8 · Controls (tell them, and write these into `MY-BOT.md` in their project folder)

- **Morning login (every trading day, before 09:15):**
  `ssh -t -i ~/.ssh/jev_vps root@<IP> "cd /root/jev-starter && /root/.local/bin/uv run python -m jevlab login"`
- **Stop for today:** `$SSH "systemctl stop jev-bot"` (it cancels its orders and closes the position). Start again:
  `systemctl start jev-bot`. **Stop for good:** `$SSH "systemctl disable --now jev-bot.timer && systemctl stop jev-bot"`
- **Kill switch:** `$SSH "touch /root/jev-starter/STOP"` closes out and halts for the day. Delete the file and
  `systemctl restart jev-bot` to resume.
- **Logs:** `$SSH "journalctl -u jev-bot -f"`
- **Change the strategy:** edit `jevlab/strategy.py` on the laptop and test it with `bot --paper --minutes 5` during
  market hours (on the server if the key is IP-locked). Then copy it up (re-run the B4.3 copy) and
  `$SSH "systemctl restart jev-bot"`
- **Limits:** `MAX_POSITION_INR`, `MAX_DAILY_LOSS_INR` and `MAX_ORDERS_PER_DAY` in the server's `.env`, then restart.
  The bot halts for the day at the loss limit, even across restarts.
- **The source of truth** is the Firstock app: positions, orders, and the contract notes with the exact charges.

## B9 · Wrap up

Tell them it now runs every trading day in **paper mode**, with Claude setting the direction and Jev making the fast
calls, on live Firstock prices. Suggest they leave it on paper for at least a few weeks and judge it on after-charges
results (the dashboard, and `results/bot_day.json` on the server) before even thinking about real money.

## B10 · Real money (only if they explicitly ask)

Explain the steps, but they do them themselves:
1. Confirm the static IP (B5) is registered and active, and the Firstock account is funded.
2. Edit the server's `.env` in their own terminal: `ssh -t -i ~/.ssh/jev_vps root@<IP> "nano /root/jev-starter/.env"`.
   Set small limits first (e.g. `MAX_POSITION_INR=5000`, `MAX_DAILY_LOSS_INR=200`), then `FIRSTOCK_MODE=live` and
   `JEV_LIVE_CONFIRM=I accept the risk of trading real money`.
3. Restart: `$SSH "systemctl restart jev-bot"`. On the first live day, watch the orders appear in the Firstock app. If
   orders are rejected with an IP message, the static IP isn't active yet.

Remind them: only risk money they can afford to lose. Keep the contract notes for tax (intraday profits are business
income; ask a CA). Not financial advice.

---

## Files

### `jev-starter/pyproject.toml`

````toml
[project]
name = "jev-starter"
version = "2.0.0"
description = "A Jev trading bot starter for Indian stocks on Firstock: live dashboard, news terminal, a strategy file you edit, and an optional trading-day bot (paper first)."
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "pandas>=2.0",
    "python-dotenv>=1.0",
    "rich>=13",
    "websocket-client>=1.7",
    "tzdata>=2024.1",
]
````

### `jev-starter/.gitignore`

````
.env
.venv/
results/
__pycache__/
STOP
````

### `jev-starter/.env.example`

````
# Copy this file to .env (same folder) and paste your keys after the = signs.
# Never share this file.

# --- Jev (and Claude) -------------------------------------------------------
# Vercel AI Gateway key: https://vercel.com/dashboard -> AI Gateway -> API Keys -> Create key
# The free tier works but is slow (about one Jev call every 2 seconds).
# $5 of AI Gateway credits removes that limit, and is needed for Claude (the trading bot's brain).
AI_GATEWAY_API_KEY=

# Optional: a direct TypeSafe key, if you're off their waitlist.
TYPESAFE_API_KEY=

# --- Firstock (live NSE prices, and orders for the trading bot) --------------
# Your Firstock client ID and login password, plus the API key and vendor code
# from Firstock's API key page. The 6-digit 2FA code is NOT stored here: you type
# it once each trading day with `uv run python -m jevlab login`.
FIRSTOCK_USER_ID=
FIRSTOCK_PASSWORD=
FIRSTOCK_API_KEY=
FIRSTOCK_VENDOR_CODE=

# The NSE stock to trade (intraday). RELIANCE is liquid and cheap to trade in and out of.
SYMBOL=RELIANCE

# --- Trading bot only (Path 2) ------------------------------------------------
# paper = live Firstock prices, simulated fills, no orders ever sent. Start here.
FIRSTOCK_MODE=paper

# Hard limits, always on (rupees):
MAX_POSITION_INR=10000
MAX_DAILY_LOSS_INR=500
MAX_ORDERS_PER_DAY=100

# Claude model for the big-picture brain (via the same Vercel key).
CLAUDE_MODEL=anthropic/claude-sonnet-5

# Real money: leave this blank. Only set FIRSTOCK_MODE=live, and this line to the exact
# phrase "I accept the risk of trading real money", after weeks of paper results.
JEV_LIVE_CONFIRM=
````

### `jev-starter/README.md`

````markdown
# jev-starter (Firstock edition)

A Jev trading bot for Indian stocks that you can watch, test, and plug your own strategy into.
**The laptop version is paper trading only**: it reads live NSE prices from your Firstock account and simulates fills, and it never places an order. The optional **trading bot** (Path 2) runs every trading day on a small server in India. It starts in **paper mode** (live prices, simulated fills), and only trades real money if you switch it on yourself.

## What's inside

| | |
|---|---|
| **Jev Loop** · `uv run python -m jevlab loop` | Live dashboard: the real NSE price ticking, Jev's BUY/SELL calls landing on it, and your strategy deciding which calls become trades. Shows P&L before and after Indian charges on a ₹1,00,000 paper position. Runs during market hours (09:15 to 15:30 IST, Monday to Friday). |
| **Newsroom** · `uv run python -m jevlab newsroom` | A news terminal. It replays the last few days of real Indian market headlines in fast motion. Jev reads each one live (which stock, which way, how big), and then it shows what the price actually did next on NSE. Works any time. |
| **Your strategy** · `jevlab/strategy.py` | The one file you edit. `decide()` gets Jev's call and the live market numbers, and returns `"buy"`, `"sell"` or `"hold · reason"`. |
| **Daily login** · `uv run python -m jevlab login` | Once each trading day: type the 6-digit code from your authenticator app. SEBI's rules end every API session daily. |
| **Setup check** · `uv run python -m jevlab check` | Tests your Firstock login, live prices, news feeds, your Jev key and your speed tier. |

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. `cp .env.example .env`, then fill it in:
   - your Vercel AI Gateway key after `AI_GATEWAY_API_KEY=`. Get one at vercel.com/dashboard → AI Gateway → API Keys. The free tier works but is slow (about one Jev call every 2 seconds); $5 of AI Gateway credits runs it at full speed. Each call costs a tiny fraction of a cent.
   - your Firstock client ID, password, API key and vendor code (from Firstock's API key page).
3. `uv sync`, then `uv run python -m jevlab login`, then `uv run python -m jevlab check`.

## Plug in your own strategy

Open `jevlab/strategy.py`. The default is three simple rules:
- only act when Jev is at least 85% sure
- wait 60 seconds between flips
- let the loop use limit orders

Change `SETTINGS`, or rewrite `decide()`. There's a trend-following example at the bottom of the file. Easiest route: tell Claude your idea in one sentence and ask it to rewrite `decide()`. Then run `uv run python -m jevlab loop` again and watch what changes.

Costs matter a lot here. A ₹1 lakh intraday round trip costs about ₹80 (brokerage, STT, exchange charges, SEBI fee, stamp duty and GST), and a ₹10,000 one about ₹10 (0.1%). Before trusting any strategy, ask three questions:
1. Why should it make money?
2. Does it still make money after costs?
3. Does it work on data it's never seen?

## Flags

`--symbol INFY` · `--minutes 0` (run until Ctrl+C or the close) · `--taker` (market orders) · `--gap 4` (newsroom pace) · `--port 8766` (a second dashboard) · `--no-open`

## The trading bot (Path 2): Claude + Jev on Firstock

`uv run python -m jevlab bot` runs the same loop with Claude as the big-picture brain:
- **Claude** reads the market every 10 minutes and sets the bias: long, short or flat
- **Jev** makes the fast calls
- **`strategy.py`** only trades in Claude's direction

It trades one NSE stock intraday (MIS): no new positions after 15:00, and everything is closed at 15:10 IST. It starts in **paper mode** (`FIRSTOCK_MODE=paper`: live Firstock prices, simulated fills). `--paper` forces paper mode whatever `.env` says.

Safety, always on:
- intraday limit orders at the best bid/ask, at most one order action a second (SEBI treats 10 or more orders a second as a registered algo)
- `MAX_POSITION_INR`, `MAX_DAILY_LOSS_INR` and `MAX_ORDERS_PER_DAY` limits. The loss limit holds across restarts
- a kill switch: create a file called `STOP` and it closes out and halts
- on shutdown it cancels its orders and closes the position

The rules you trade under (SEBI's retail algo framework, in force since April 2026): Firstock only accepts API orders from a **static IP registered with them**, the server should be **in India**, every API session **ends daily** and needs your 2FA code to log in again, and orders at 10 or more a second need exchange registration. This bot stays far below that.

Real money needs `FIRSTOCK_MODE=live` **and** the exact confirmation phrase in `JEV_LIVE_CONFIRM`. Set those yourself, after weeks of paper results.

To run it every trading day, put it on a small Linux VPS in India with a static IP, using `deploy/jev-bot.service` and `deploy/jev-bot.timer`. The setup prompt walks through all of it. Not financial advice.
````

### `jev-starter/jevlab/__init__.py`

````python
"""jev-starter (Firstock edition): a Jev trading bot for Indian stocks you can see, test and plug your own strategy into."""
````

### `jev-starter/jevlab/__main__.py`

````python
"""jev-starter CLI (Firstock edition).

  uv run python -m jevlab login             # once each trading day: type the 6-digit code from your authenticator app
  uv run python -m jevlab check             # test the setup: Firstock, live prices, headlines, and one real Jev call
  uv run python -m jevlab loop              # the Jev Loop: live NSE trading dashboard (paper), your strategy
  uv run python -m jevlab newsroom          # the news terminal: real Indian headlines, Jev reading each one live
  uv run python -m jevlab bot --paper       # trading bot on live Firstock prices with simulated fills
  uv run python -m jevlab bot               # trading bot in FIRSTOCK_MODE from .env (paper unless you chose live)
  uv run python -m jevlab logout            # end today's Firstock session early

Useful flags:
  --symbol INFY     loop/bot: which NSE stock to trade (default SYMBOL in .env, else RELIANCE)
  --minutes 0       loop/bot: run until Ctrl+C or the end of the trading day (default 10)
  --taker           loop: market orders instead of limit orders
  --gap 4           newsroom: seconds between replayed headlines (default 6)
  --port 8766       run a second dashboard alongside the first
  --no-open         don't open the browser
  --totp 123456     login: pass the 6-digit code instead of typing it at the prompt
"""

from __future__ import annotations

import argparse
import os
import sys
import threading


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
        hint = (" (the code changes every 30 seconds: use a fresh one)" if "totp" in msg.lower() or "otp" in msg.lower()
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


def check(symbol: str) -> None:
    import time

    from .core import console, inr, ist_now, market_open
    from .firstock import FirstockError, credentials, load_session, quote, trading_symbol
    from .judges import JevJudge, JudgeError
    from .news import fetch_headlines

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
        tsym = trading_symbol(symbol)
        try:
            q, n = quote(session, tsym), quote(session, "NIFTY")
            console.print(f"     logged in as {session.name} · {tsym} {inr(q['ltp'])} · NIFTY {n['ltp']:,.2f}  [#3fd68a]ok[/]")
        except FirstockError as exc:
            console.print(f"     [#ff5d6c]Firstock said no[/]: {str(exc)[:140]}")
    now = ist_now()
    console.print(f"     NSE is {'[#3fd68a]open[/]' if market_open(now) else '[#f5b53d]closed[/]'} right now "
                  f"({now.strftime('%a %H:%M')} IST · open Monday to Friday, 09:15 to 15:30)")
    if session and market_open(now):
        from .firstock import FirstockMarket
        try:
            market = FirstockMarket(session, trading_symbol(symbol))
            market.start()
            live = market.ready.wait(15)
            market.stop()
            console.print(f"     live price feed ok (bid {market.bbo[0]:,.2f} · ask {market.bbo[1]:,.2f})  [#3fd68a]ok[/]" if live
                          else f"     [#ff5d6c]no live price feed after 15s[/] {market.error or ''}")
        except FirstockError as exc:
            console.print(f"     [#ff5d6c]live price feed failed[/]: {str(exc)[:120]}")
    console.print("  [bold]2. News feeds[/]")
    n = len(fetch_headlines(24))
    console.print(f"     {n} headlines in the last 24h  [#3fd68a]ok[/]" if n else "     no headlines found  [#f5b53d]check your internet[/]")
    console.print("  [bold]3. Jev[/]")
    try:
        jev = JevJudge()
    except JudgeError:
        console.print("     [#f5b53d]no key yet[/]: paste your AI_GATEWAY_API_KEY into .env, save, and run this again")
        return
    q = {"side": {"type": "choice", "instructions": "Which side should a bot hold for the next few seconds?",
                  "criteria": {"buy": None, "sell": None}}}
    try:
        ans, meta = jev.ask({"return_5s_bps": 1.2, "top_of_book_imbalance": 0.4}, q, timeout=15, retries=2)
    except JudgeError as exc:
        msg = str(exc)
        if "401" in msg or "403" in msg:
            console.print("     [#ff5d6c]key rejected[/]: check the key in .env, and that your Vercel team has a card or credits")
        elif "429" in msg:
            console.print("     [#f5b53d]rate-limited[/]: the free tier is busy. Wait a minute, or add $5 of AI Gateway credits for full speed")
        else:
            console.print(f"     [#ff5d6c]failed[/]: {msg[:160]}")
        return
    side = ans["side"]["choice"]
    console.print(f"     Jev says [bold]{side.upper()} {ans['side']['probs'][side]:.0%}[/] in {meta['latency_ms']} ms "
                  f"(model {meta['model']})  [#3fd68a]ok[/]")
    console.print("  [bold]4. Speed[/]")
    ok = 0
    t0 = time.time()
    for _ in range(6):
        try:
            jev.ask({"return_5s_bps": 0.5}, q, timeout=10, retries=0)
            ok += 1
        except JudgeError:
            pass
        time.sleep(0.3)
    console.print(f"     {ok}/6 quick calls went through in {time.time() - t0:.1f}s · "
                  + ("full speed" if ok == 6 else "you're on the free tier, so the loop will run slower (add $5 of credits for full speed)"))
    check_trading(session)
    console.print("\n  [#3fd68a]All set.[/] Next: [bold]uv run python -m jevlab loop[/] (during market hours)")


def check_trading(session) -> None:
    from .core import console, inr
    from .firstock import FirstockError, live_mode, public_ip
    console.print("  [bold]5. Trading bot (only needed for Path 2)[/]")
    try:
        mode = live_mode()
    except FirstockError as exc:
        console.print(f"     [#ff5d6c]{exc}[/]")
        return
    console.print(f"     mode [bold]{mode.upper()}[/]" + (" (live Firstock prices, simulated fills: no orders are sent)"
                                                            if mode == "paper" else " · [bold #ff5d6c]REAL MONEY[/]"))
    if session:
        try:
            d = session.post("limit")
            cash = d.get("cash") if isinstance(d, dict) else None
            console.print(f"     account readable · cash {inr(float(cash))}  [#3fd68a]ok[/]" if cash is not None
                          else "     account readable  [#3fd68a]ok[/]")
        except (FirstockError, ValueError) as exc:
            console.print(f"     [dim]couldn't read the account limits: {str(exc)[:100]}[/]")
    ip = public_ip()
    console.print(f"     this machine's public IP is [bold]{ip}[/]. Firstock only accepts API orders from the static IP "
                  "you registered with them" if ip else "     [dim](couldn't look up this machine's public IP)[/]")


def main() -> None:
    ap = argparse.ArgumentParser(prog="jevlab")
    ap.add_argument("command", choices=["check", "login", "logout", "loop", "newsroom", "bot"])
    ap.add_argument("--symbol", default=None, help="loop/bot: the NSE stock to trade (default SYMBOL in .env)")
    ap.add_argument("--minutes", type=float, default=10.0, help="loop/bot: how long to run (0 = until stopped or the close)")
    ap.add_argument("--pace", type=float, default=0.3, help="loop/bot: fastest seconds between Jev calls")
    ap.add_argument("--late-ms", type=float, default=1500, help="loop/bot: answers slower than this are ignored")
    ap.add_argument("--taker", action="store_true", help="loop: market orders instead of limit orders")
    ap.add_argument("--maker-wait", type=float, default=10.0, help="loop/bot: seconds a limit order rests before cancel")
    ap.add_argument("--hours", type=float, default=72.0, help="newsroom: how far back to replay headlines")
    ap.add_argument("--gap", type=float, default=6.0, help="newsroom: seconds between replayed headlines")
    ap.add_argument("--paper", action="store_true", help="bot: paper mode (simulated fills), whatever .env says")
    ap.add_argument("--brain-every", type=float, default=10.0, help="bot: minutes between Claude's big-picture reads")
    ap.add_argument("--totp", default=None, help="login: the 6-digit code from your authenticator app")
    ap.add_argument("--port", type=int, default=8765, help="dashboard port")
    ap.add_argument("--no-open", action="store_true", help="don't open the dashboard in a browser")
    a = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    from .core import console
    symbol = (a.symbol or os.getenv("SYMBOL", "") or "RELIANCE").strip().upper()
    if a.command not in ("bot", "login", "logout"):  # the bot prints its own banner, with its trading mode
        console.print("[bold #8b7bff]jev-starter[/] [dim]· Indian stocks on Firstock · paper trading on live NSE prices · "
                      "no real orders are ever placed[/]")

    if a.command == "check":
        check(symbol)
        return
    if a.command == "login":
        login_cmd(a.totp)
        return
    if a.command == "logout":
        logout_cmd()
        return
    if a.command == "loop":
        from .loop import run_loop
        run_loop(symbol, a.pace, a.minutes, a.port, not a.no_open, a.late_ms, not a.taker, a.maker_wait)
    elif a.command == "bot":
        from .bot import run_bot
        run_bot(symbol, a.pace, a.minutes, a.port, not a.no_open, a.late_ms, a.maker_wait, a.brain_every, a.paper)
        if a.no_open and not a.minutes:
            return
    else:
        from .newsroom import run_newsroom
        run_newsroom(a.hours, a.gap, a.port, not a.no_open)
    console.print("  [dim]dashboard still open · Ctrl+C to stop[/]")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
````

### `jev-starter/jevlab/core.py`

````python
"""Shared bits: where results go, the terminal styling, and NSE market hours (India time)."""

from __future__ import annotations

from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

from rich import box
from rich.console import Console
from rich.panel import Panel

RESULTS = Path(__file__).resolve().parent.parent / "results"
console = Console(highlight=False)

IST = ZoneInfo("Asia/Kolkata")
OPEN, CLOSE = dtime(9, 15), dtime(15, 30)  # NSE equity session, Monday to Friday


def header(title: str, subtitle: str) -> None:
    console.print()
    console.print(Panel(f"[dim]{subtitle}[/]", title=f"[bold #8b7bff]{title}[/]", title_align="left",
                        border_style="#3a3f5c", box=box.ROUNDED, padding=(0, 2)))


def ist_now() -> datetime:
    return datetime.now(IST)


def market_open(now: datetime | None = None) -> bool:
    """True during NSE hours on a weekday. Exchange holidays aren't listed here: on a holiday the
    feed simply shows no trades, and the loop and bot hold."""
    now = now or ist_now()
    return now.weekday() < 5 and OPEN <= now.time() < CLOSE


def minutes_to_close(now: datetime | None = None) -> float:
    now = now or ist_now()
    close = now.replace(hour=CLOSE.hour, minute=CLOSE.minute, second=0, microsecond=0)
    return max(0.0, (close - now).total_seconds() / 60)


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

### `jev-starter/jevlab/firstock.py`

````python
"""Firstock: the daily login, live NSE prices, and order placement.

Everything talks to Firstock's developer API (the same endpoints the official
`firstock` Python SDK uses):
  REST       https://api.firstock.in/V1/<endpoint>   JSON in, JSON out
  WebSocket  wss://socket.firstock.in/V2/ws           live bid/ask, depth and trades

The daily login: SEBI's rules end every API session each day, and a login needs
your 2FA code. So once each trading day you run `uv run python -m jevlab login`
and type the 6-digit code from your authenticator app. The session token is saved
in results/session.json (readable only by you) and is valid until the day ends.

Orders (trading bot, live mode only) are intraday limit orders (product "I", MIS).
A buy rests at the best bid, a sell at the best ask, so the bot never pays the
spread. Exits use a limit order priced through the touch, which fills straight
away but can never fill at a crazy price. At most one order action a second:
far below the 10 orders a second at which SEBI treats you as a registered algo.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from urllib.parse import urlencode

import pandas as pd
import requests
import websocket
from dotenv import load_dotenv

from .core import CLOSE, IST, OPEN, RESULTS, ist_now

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_URL = "https://api.firstock.in/V1"
WS_URL = "wss://socket.firstock.in/V2/ws"
WS_ORIGIN = "https://firstock.in"
EXCHANGE = "NSE"
INTRADAY = "I"  # Firstock's product code for intraday (MIS): the position must be closed the same day
REMARK = "jev-bot"  # tags the bot's orders, so it never touches orders you placed yourself
SESSION_FILE = RESULTS / "session.json"
LIVE_PHRASE = "I accept the risk of trading real money"
DONE = ("COMPLETE", "REJECTED", "CANCELED")

# NSE equity intraday charges, per executed order. Approximate: check firstock.in/support/charges.
BROKERAGE_RATE, BROKERAGE_CAP = 0.0003, 20.0  # Firstock intraday: 0.03% or ₹20, whichever is lower
STT_SELL = 0.00025        # securities transaction tax, sell side only
EXCHANGE_TXN = 0.0000297  # NSE transaction charge
SEBI_FEE = 0.000001       # ₹10 per crore
STAMP_BUY = 0.00003       # stamp duty, buy side only
GST = 0.18                # on brokerage + exchange + SEBI charges


def charges(side: str, value: float) -> float:
    """Everything one executed order costs, in rupees: brokerage, STT, exchange, SEBI, stamp duty, GST."""
    brokerage = min(BROKERAGE_CAP, BROKERAGE_RATE * value)
    exch, sebi = EXCHANGE_TXN * value, SEBI_FEE * value
    tax = STT_SELL * value if side == "sell" else STAMP_BUY * value
    return brokerage + exch + sebi + tax + GST * (brokerage + exch + sebi)


def round_trip_bps(value: float) -> float:
    """Cost of buying and then selling `value` rupees of stock, in basis points (1 bps = 0.01%)."""
    return 1e4 * (charges("buy", value) + charges("sell", value)) / value


class FirstockError(Exception):
    pass


class SessionExpired(FirstockError):
    pass


_EXPIRED = re.compile(r"session (has )?expired|invalid session|session is invalid|jkey|not logged in|please login|"
                      r"login again", re.I)
_IP = re.compile(r"\bip\b|whitelist|static", re.I)  # an IP rejection is not an expired session
_EMPTY = re.compile(r"no data|not found|no record|no position|no order", re.I)


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


def _post(path: str, body: dict, timeout: float = 10.0):
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


def _write_private(path, text: str) -> None:
    RESULTS.mkdir(exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


class Session:
    """A logged-in Firstock session: every API call carries the user ID and the session token (jKey)."""

    def __init__(self, user_id: str, jkey: str, name: str = ""):
        self.user_id, self.jkey, self.name = user_id, jkey, name

    def post(self, path: str, timeout: float = 10.0, **fields):
        try:
            return _post(path, {"userId": self.user_id, "jKey": self.jkey, **fields}, timeout)
        except SessionExpired:
            forget_session()  # so the bot waits for a fresh login instead of retrying a dead token
            raise

    def rows(self, path: str, **fields) -> list[dict]:
        """A list endpoint (order book, positions). An empty book comes back as an error, which means []."""
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
    _write_private(SESSION_FILE, json.dumps({"userId": c["userId"], "jKey": token, "name": name,
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
    """RELIANCE -> RELIANCE-EQ (the NSE equity series). Anything with a dash is left alone."""
    s = symbol.strip().upper()
    return s if "-" in s else f"{s}-EQ"


def security_info(session: Session, tsym: str, exchange: str = EXCHANGE) -> dict:
    d = session.post("securityInfo", exchange=exchange, tradingSymbol=tsym)
    if not isinstance(d, dict) or not d.get("token"):
        raise FirstockError(f"Firstock doesn't know {exchange}:{tsym}")
    return {"token": str(d["token"]), "tick": _f(d.get("tickSize"), 0.05) or 0.05,
            "lot": int(_f(d.get("lotSize"), 1)) or 1, "name": d.get("symbolName") or tsym}


def quote(session: Session, tsym: str, exchange: str = EXCHANGE) -> dict:
    d = session.post("getQuote", exchange=exchange, tradingSymbol=tsym)
    return {"ltp": _f(d.get("lastTradedPrice")), "bid": _f(d.get("bestBuyPrice1")), "ask": _f(d.get("bestSellPrice1")),
            "open": _f(d.get("dayOpenPrice")), "high": _f(d.get("dayHighPrice")), "low": _f(d.get("dayLowPrice")),
            "prev_close": _f(d.get("dayClosePrice")), "name": d.get("companyName") or tsym}


def candles(session: Session, tsym: str, minutes: int, start: datetime, end: datetime | None = None,
            exchange: str = EXCHANGE) -> pd.DataFrame:
    """OHLCV candles indexed by time (UTC). Asks for one trading day at a time; days with no data are skipped."""
    end = end or ist_now()
    start, end = start.astimezone(IST), end.astimezone(IST)
    frames, day = [], start.date()
    while day <= end.date():
        if day.weekday() < 5:
            t0 = max(start, datetime.combine(day, OPEN, IST))
            t1 = min(end, datetime.combine(day, CLOSE, IST))
            if t0 < t1:
                frames.append(_candle_day(session, tsym, exchange, minutes, t0, t1))
        day += timedelta(days=1)
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.concat(frames)
    return df[~df.index.duplicated()].sort_index()


def _candle_day(session, tsym, exchange, minutes, t0, t1) -> pd.DataFrame:
    fmt = "%H:%M:%S %d-%m-%Y"
    rows = []
    for interval in (f"{minutes}mi", str(minutes)):  # the V1 API says "1mi"; older docs say "1"
        try:
            rows = session.post("timePriceSeries", timeout=20, exchange=exchange, tradingSymbol=tsym, interval=interval,
                                startTime=t0.strftime(fmt), endTime=t1.strftime(fmt))
            break
        except SessionExpired:
            raise
        except FirstockError:
            continue
    rows = rows if isinstance(rows, list) else []
    out = []
    for r in rows:
        ts = None
        epoch = _f(r.get("epochTime") or r.get("ssboe"))
        if epoch:
            ts = pd.Timestamp(epoch / (1000 if epoch > 1e11 else 1), unit="s", tz="UTC")
        elif r.get("time"):
            try:
                ts = pd.Timestamp(pd.to_datetime(r["time"], dayfirst=True)).tz_localize(IST).tz_convert("UTC")
            except (ValueError, TypeError):
                ts = None
        if ts is not None:
            out.append((ts, _f(r.get("open")), _f(r.get("high")), _f(r.get("low")), _f(r.get("close")), _f(r.get("volume"))))
    df = pd.DataFrame(out, columns=["t", "open", "high", "low", "close", "volume"]).set_index("t")
    return df[df["close"] > 0]


def _micro(bid: float, ask: float, bsz: float, asz: float) -> float:
    return (bid * asz + ask * bsz) / (bsz + asz) if bsz + asz > 0 else (bid + ask) / 2


class FirstockMarket:
    """Live NSE feed for one stock from Firstock's websocket: the best bid/ask with 5 levels of
    depth, and the last trade on every update. Runs in a background thread and reconnects."""

    def __init__(self, session: Session, tsym: str, info: dict | None = None):
        self.session, self.tsym = session, tsym
        self.info = info or security_info(session, tsym)
        self.lock = threading.Lock()
        self.bbo = None  # (bid, ask, bid_sz, ask_sz, t)
        self.depth5 = None  # (bid_inr, ask_inr, t)
        self.trades = deque()  # (t, is_buy, px, qty)
        self.mids = deque()  # (t, mid) on every book update
        self.ticks = deque()  # (t, microprice, bid, ask), thinned to 20/s for the dashboard
        self.ready = threading.Event()
        self.raw: dict = {}  # the latest full picture (updates may only carry what changed)
        self.scale = None  # Firstock streams prices in paise; worked out against the REST quote
        self.ref_px = None
        self.last_trade_key = None
        self.last_trade_t = 0.0
        self.error = None

    def start(self) -> None:
        try:
            self.ref_px = quote(self.session, self.tsym)["ltp"] or None
        except FirstockError:
            pass
        url = f"{WS_URL}?" + urlencode({"userId": self.session.user_id, "jKey": self.session.jkey, "source": "developer-api"})
        sub = json.dumps({"action": "subscribe", "tokens": f"{EXCHANGE}:{self.info['token']}"})

        def on_message(ws, raw):
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            if "Authentication successful" in raw:  # (again after every reconnect)
                ws.send(sub)
            elif "Maximum sessions limit" in raw or re.search(r'"status"\s*:\s*"failed"', raw):
                self.error = raw[:200]
            else:
                self._on_feed(raw)

        self.app = websocket.WebSocketApp(url, header={"Cache-Control": "no-cache", "Pragma": "no-cache"},
                                          on_message=on_message)
        threading.Thread(target=lambda: self.app.run_forever(ping_interval=20, reconnect=5, origin=WS_ORIGIN),
                         daemon=True).start()

    def stop(self) -> None:
        try:
            self.app.close()
        except Exception:
            pass

    def _on_feed(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        if not isinstance(msg, dict):
            return
        feed_keys = ("best_buy", "best_sell", "i_last_traded_price", "c_exch_seg")
        updates = [msg] if any(k in msg for k in feed_keys) else [v for v in msg.values() if isinstance(v, dict)]
        now = time.time()
        with self.lock:
            for u in updates:
                self.raw.update({k: v for k, v in u.items() if v is not None})
                self._apply(now)
            for dq, keep in ((self.mids, 120), (self.trades, 120), (self.ticks, 300)):
                while dq and now - dq[0][0] > keep:
                    dq.popleft()

    def _apply(self, now: float) -> None:
        d = self.raw
        ltp = _f(d.get("i_last_traded_price"))
        if self.scale is None:
            if not ltp:
                return
            ref = self.ref_px
            self.scale = 100.0 if not ref or abs(ltp / 100 - ref) < abs(ltp - ref) else 1.0
        s = self.scale
        levels = lambda side: [(_f(l.get("price")) / s, _f(l.get("quantity"))) for l in (d.get(side) or [])
                               if isinstance(l, dict) and _f(l.get("price")) > 0]
        bids, asks = levels("best_buy"), levels("best_sell")
        key = (d.get("i_last_trade_time"), d.get("i_last_traded_price"), d.get("i_last_trade_quantity"))
        if ltp and key != self.last_trade_key:
            if self.last_trade_key is not None:  # the first message repeats an old trade: skip it
                px, prev = ltp / s, self.bbo
                is_buy = (px >= (prev[0] + prev[1]) / 2) if prev else True  # traded near the ask = a buyer hit it
                self.trades.append((now, is_buy, px, _f(d.get("i_last_trade_quantity"))))
                self.last_trade_t = now
            self.last_trade_key = key
        if bids and asks and bids[0][0] < asks[0][0]:
            (bid, bsz), (ask, asz) = bids[0], asks[0]
            self.bbo = (bid, ask, bsz, asz, now)
            self.mids.append((now, (bid + ask) / 2))
            if not self.ticks or now - self.ticks[-1][0] >= 0.05:
                self.ticks.append((now, _micro(bid, ask, bsz, asz), bid, ask))
            self.depth5 = (sum(p * q for p, q in bids[:5]), sum(p * q for p, q in asks[:5]), now)
            self.ready.set()

    def fresh(self, seconds: float = 120) -> bool:
        """Has anything traded recently? Quiet means closed, a holiday, or a halt."""
        return time.time() - self.last_trade_t < seconds

    def snapshot(self) -> dict:
        """The state Jev sees: small, numeric, and fresh. No dates, no stock name."""
        with self.lock:
            bid, ask, bsz, asz, _ = self.bbo
            now = time.time()
            mid = (bid + ask) / 2
            micro = _micro(bid, ask, bsz, asz)

            def ret(sec):
                past = next((m for t, m in self.mids if t >= now - sec), mid)
                return round(1e4 * (mid / past - 1), 2)

            def flow(sec):
                tr = [(b, px * q) for t, b, px, q in self.trades if t >= now - sec]
                vol = sum(v for _, v in tr)
                return (round(sum(v for b, v in tr if b) / vol, 3) if vol else 0.5), len(tr)

            buy5, n5 = flow(5)
            buy30, _ = flow(30)
            m60 = [m for t, m in self.mids if t >= now - 60]
            steps = [1e4 * (b / a - 1) for a, b in zip(m60, m60[1:]) if a != b]
            state = {
                "spread_bps": round(1e4 * (ask - bid) / mid, 3),
                "microprice_vs_mid_bps": round(1e4 * (micro / mid - 1), 3),
                "top_of_book_imbalance": round((bsz - asz) / (bsz + asz), 3) if bsz + asz else 0.0,
                "aggressor_buy_share_5s": buy5,
                "aggressor_buy_share_30s": buy30,
                "trades_last_5s": n5,
                "return_5s_bps": ret(5),
                "return_30s_bps": ret(30),
                "tick_volatility_60s_bps": round(statistics.pstdev(steps), 3) if len(steps) > 2 else 0.0,
            }
            if self.depth5 and self.depth5[0] + self.depth5[1]:
                bd, ad, _ = self.depth5
                state["depth5_imbalance"] = round((bd - ad) / (bd + ad), 3)
            return {"mid": mid, "micro": micro, "bid": bid, "ask": ask, "spread_bps": 1e4 * (ask - bid) / mid, "state": state}

    def trades_since(self, t0: float) -> list[tuple]:
        with self.lock:
            return [tr for tr in self.trades if tr[0] >= t0]

    def recent_ticks(self, seconds: float = 90) -> list[list[float]]:
        with self.lock:
            now = time.time()
            return [[round(t, 3), round(m, 4), b, a] for t, m, b, a in self.ticks if t >= now - seconds]


# ---------------------------------------------------------------- orders (live mode only)

class FirstockTrader:
    """Places and tracks intraday limit orders on one NSE stock."""

    ORDER_GAP_S = 1.0  # at most one order action a second (SEBI's registered-algo threshold is 10 a second)

    def __init__(self, session: Session, tsym: str, info: dict, max_orders: int):
        self.session, self.tsym, self.info = session, tsym, info
        self.tick, self.max_orders = info["tick"], max_orders
        self.orders_today, self.day = 0, ist_now().date()
        self._last = 0.0
        self._lock = threading.Lock()

    def _throttle(self, force: bool = False) -> None:
        with self._lock:
            today = ist_now().date()
            if today != self.day:
                self.day, self.orders_today = today, 0
            if not force and self.orders_today >= self.max_orders:
                raise FirstockError(f"daily order cap reached (MAX_ORDERS_PER_DAY={self.max_orders})")
            wait = self._last + self.ORDER_GAP_S - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            self.orders_today += 1

    def fmt_px(self, px: float) -> str:
        return f"{round(round(px / self.tick) * self.tick, 2):.2f}"

    def cash(self) -> float | None:
        d = self.session.post("limit")
        return _f(d.get("cash")) if isinstance(d, dict) and d.get("cash") is not None else None

    def place_limit(self, side: str, qty: int, px: float, force: bool = False) -> str:
        self._throttle(force)
        d = self.session.post("placeOrder", exchange=EXCHANGE, tradingSymbol=self.tsym, quantity=str(int(qty)),
                              price=self.fmt_px(px), product=INTRADAY, transactionType="B" if side == "buy" else "S",
                              priceType="LMT", retention="DAY", triggerPrice="0", remarks=REMARK)
        oid = str(d.get("orderNumber") or "") if isinstance(d, dict) else ""
        if not oid:
            raise FirstockError(f"no order number in Firstock's reply: {str(d)[:120]}")
        return oid

    def order(self, oid: str) -> dict:
        """Current state of one order: status, shares filled, average fill price."""
        rows = self.session.rows("singleOrderHistory", orderNumber=oid)
        if not rows:
            rows = [r for r in self.session.rows("orderBook") if str(r.get("orderNumber")) == oid]
        if not rows:
            return {"status": "UNKNOWN", "filled": 0, "avg_px": 0.0, "reason": ""}
        statuses = [str(r.get("status", "")).upper().replace("CANCELLED", "CANCELED") for r in rows]
        status = next((s for s in DONE if s in statuses), statuses[0])
        filled = int(max(_f(r.get("fillShares")) for r in rows))
        avg = next((_f(r.get("averagePrice")) for r in rows
                    if int(_f(r.get("fillShares"))) == filled and _f(r.get("averagePrice"))), 0.0)
        reason = next((r.get("rejectReason") for r in rows if r.get("rejectReason")), "")
        return {"status": status, "filled": filled, "avg_px": avg, "reason": str(reason)[:120]}

    def cancel(self, oid: str) -> None:
        try:
            self._throttle(force=True)
            self.session.post("cancelOrder", orderNumber=oid)
        except SessionExpired:
            raise
        except FirstockError:
            pass  # already filled or gone

    def cancel_all(self) -> None:
        """Cancel the bot's own open orders on this stock (never yours: they don't carry the jev-bot remark)."""
        for r in self.session.rows("orderBook"):
            status = str(r.get("status", "")).upper().replace("CANCELLED", "CANCELED")
            if (r.get("tradingSymbol") == self.tsym and status not in DONE
                    and str(r.get("remarks", "")).startswith(REMARK)):
                self.cancel(str(r.get("orderNumber")))

    def position(self) -> tuple[int, float]:
        """Signed intraday position in shares (+ long, - short) and its average price."""
        rows = [r for r in self.session.rows("positionBook")
                if r.get("tradingSymbol") == self.tsym and str(r.get("product", "")).upper() in ("I", "MIS", "INTRADAY")]
        qty = int(sum(_f(r.get("netQuantity")) for r in rows))
        avg = next((_f(r.get("netAveragePrice")) for r in rows if _f(r.get("netQuantity"))), 0.0)
        return qty, avg

    def flatten(self, bid: float, ask: float) -> tuple[list[tuple[int, float]], int]:
        """Close the intraday position with limit orders priced through the touch (0.2%, then 0.5%, then 1%).
        They fill at once at the best price available, never worse than the limit.
        Returns the fills as (signed shares, price), so the P&L includes them, and any shares still open."""
        remaining, _ = self.position()
        fills = []
        for width in (0.002, 0.005, 0.01):
            if not remaining:
                break
            selling = remaining > 0
            px = bid * (1 - width) if selling else ask * (1 + width)
            oid = self.place_limit("sell" if selling else "buy", abs(remaining), px, force=True)
            o = {"status": "", "filled": 0, "avg_px": 0.0}
            for _ in range(12):
                time.sleep(0.5)
                o = self.order(oid)
                if o["status"] in DONE:
                    break
            if o["status"] not in DONE:
                self.cancel(oid)
                time.sleep(0.5)
                o = self.order(oid)
            if o["filled"]:
                dq = -o["filled"] if selling else o["filled"]
                fills.append((dq, o["avg_px"] or px))
                remaining += dq
        return fills, remaining
````

### `jev-starter/jevlab/judges.py`

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

### `jev-starter/jevlab/news.py`

````python
"""Indian market headlines from public RSS feeds, and the questions Jev answers about each one."""

from __future__ import annotations

import html
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
# What Jev can tag a headline to, and the NSE instrument whose price we chart for it.
# NIFTY is the index itself: you can't trade it directly, it stands in for "the whole market".
ASSETS = {
    "NIFTY": "NIFTY",
    "RELIANCE": "RELIANCE-EQ",
    "HDFCBANK": "HDFCBANK-EQ",
    "ICICIBANK": "ICICIBANK-EQ",
    "INFY": "INFY-EQ",
    "TCS": "TCS-EQ",
}
QUESTIONS = {
    "asset": {
        "type": "choice",
        "instructions": "Which tradable Indian asset does this news most directly affect?",
        "criteria": {"RELIANCE": None, "HDFCBANK": None, "ICICIBANK": None, "INFY": None, "TCS": None,
                     "whole_indian_market": None, "none": None},
    },
    "direction": {
        "type": "choice",
        "instructions": "Is this news likely to push that asset's price up or down from here?",
        "criteria": {"bullish": None, "bearish": None, "neutral": None},
    },
    "impact": {
        "type": "score",
        "instructions": "How much is this news likely to move that asset's price?",
        "criteria": ["Noise", "Minor", "Notable", "Major"],
    },
}


def fetch_headlines(hours: float, quiet: bool = False) -> list[dict]:
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
    items, seen = [], set()
    for source, url in FEEDS.items():
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (jev-starter rss reader)"})
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as exc:
            if not quiet:
                print(f"  ! feed {source} unavailable: {str(exc)[:80]}")
            continue
        n = 0
        for it in root.iter("item"):
            title = html.unescape((it.findtext("title") or "").strip())
            pub = it.findtext("pubDate")
            if not title or not pub or title.lower() in seen:
                continue
            try:
                ts = pd.Timestamp(parsedate_to_datetime(pub))
                ts = ts.tz_localize("Asia/Kolkata") if ts.tzinfo is None else ts
                ts = ts.tz_convert("UTC")
            except (TypeError, ValueError):
                continue
            if ts < cutoff:
                continue
            summary = re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))
            summary = re.sub(r"\s+", " ", summary).strip()[:400]
            seen.add(title.lower())
            items.append({"source": source, "headline": title, "summary": summary, "published": ts})
            n += 1
        if not quiet:
            print(f"  feed {source:<18} {n} headlines")
    return sorted(items, key=lambda x: x["published"])


def judge_call(ans: dict) -> tuple[str | None, int]:
    asset = ans["asset"]["choice"]
    name = "NIFTY" if asset == "whole_indian_market" else asset if asset in ASSETS else None
    side = {"bullish": 1, "bearish": -1}.get(ans["direction"]["choice"], 0)
    if ans["impact"]["score"] < 2:  # only act on "Notable" or "Major"
        side = 0
    return name, side
````

### `jev-starter/jevlab/server.py`

````python
"""A tiny local web server for the dashboards, on 127.0.0.1 only.

It serves the dashboard pages and the two status files they read, and nothing else:
never .env, and never results/session.json (your Firstock session).
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
ALLOWED = ("/results/loop.json", "/results/newsroom.json")


class _Handler(SimpleHTTPRequestHandler):
    page = "loop.html"  # which dashboard "/" opens

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


def serve(port: int = 8765, open_browser: bool = True, page: str = "loop.html") -> ThreadingHTTPServer:
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

### `jev-starter/jevlab/strategy.py`

````python
"""YOUR STRATEGY. This is the one file you're meant to edit.

Jev makes a call several times a second ("buy, 91% sure"). Your strategy decides
which of those calls actually become trades. Most should end in "hold": on NSE a
₹1 lakh intraday round trip costs about ₹80 (0.08%) in brokerage, STT, exchange
charges, stamp duty and GST, so a bot that trades every call bleeds.

decide() is called every time Jev answers, with:

  call      Jev's answer, e.g. {"side": "buy", "conf": 0.91}
  market    the live numbers Jev was shown, for example:
              return_5s_bps, return_30s_bps     price change over 5s / 30s (1 bps = 0.01%)
              top_of_book_imbalance             -1 (all sellers) .. +1 (all buyers) at the best price
              depth5_imbalance                  the same, over the top 5 price levels
              aggressor_buy_share_5s / _30s     share of recent traded value that was buyers (0..1)
              trades_last_5s                    how busy the stock is right now
              spread_bps, microprice_vs_mid_bps, tick_volatility_60s_bps
              minutes_to_close                  minutes until NSE closes at 15:30 IST
              claude_bias                       trading bot only: "long", "short" or "flat", Claude's
                                                big-picture call, refreshed every few minutes
  position  1 = you're long, -1 = you're short (intraday), 0 = flat
  seconds_since_trade   seconds since your last fill

Return one of:
  "buy"            go (or stay) long
  "sell"           go (or stay) short
  "flat"           close the position
  "hold · reason"  do nothing. The reason shows up in the dashboard feed.

The loop handles everything else: placing the (paper) order, charges, the
dashboard, and the trading bot's hard limits and 15:10 IST close-out. Want a
different strategy? Describe it to Claude in one sentence and ask it to rewrite
decide(), e.g. "only buy when Jev is 90%+ sure AND buyers have been in control
for the last 30 seconds".
"""

SETTINGS = {
    "min_conf": 0.85,  # only act when Jev is at least this sure
    "min_hold": 60,    # seconds to sit still after a trade (no flip-flopping: every flip costs charges)
}

DESCRIPTION = f"trade only at ≥{SETTINGS['min_conf']:.0%} conviction · ≥{SETTINGS['min_hold']}s between flips"


def decide(call: dict, market: dict, position: int, seconds_since_trade: float) -> str:
    want = 1 if call["side"] == "buy" else -1
    bias = market.get("claude_bias")  # only set on the trading bot, where Claude is the brain
    if bias == "flat":
        return "flat" if position else "hold · Claude says stay out"
    if (bias == "long" and position < 0) or (bias == "short" and position > 0):
        return "flat"  # Claude changed its mind: get out of the old direction first
    if (bias == "long" and want < 0) or (bias == "short" and want > 0):
        return f"hold · against Claude's {bias} bias"
    if call["conf"] < SETTINGS["min_conf"]:
        return "hold · low conviction"
    if want == position:
        return "hold · already " + ("long" if want > 0 else "short")
    if seconds_since_trade < SETTINGS["min_hold"]:
        return "hold · too soon to flip"
    return call["side"]


# ---------------------------------------------------------------------------
# Example: trade with the trend only. Uncomment to use it (and delete the
# decide() above).
#
# def decide(call, market, position, seconds_since_trade):
#     trend_up = market.get("return_30s_bps", 0) > 0 and market.get("aggressor_buy_share_30s", 0.5) > 0.55
#     trend_down = market.get("return_30s_bps", 0) < 0 and market.get("aggressor_buy_share_30s", 0.5) < 0.45
#     if call["conf"] < 0.8:
#         return "hold · low conviction"
#     if call["side"] == "buy" and trend_up and position != 1:
#         return "buy"
#     if call["side"] == "sell" and trend_down and position != -1:
#         return "sell"
#     return "hold · against the trend"
````

### `jev-starter/jevlab/loop.py`

````python
"""The Jev loop: Jev trading calls landing on a live NSE price feed from Firstock,
with YOUR strategy (jevlab/strategy.py) deciding which calls become trades.

  uv run python -m jevlab loop                            # RELIANCE (or SYMBOL in .env), 10 minutes
  uv run python -m jevlab loop --symbol INFY --minutes 0  # 0 = run until Ctrl+C or the 15:30 close

Needs today's Firstock login (uv run python -m jevlab login) and NSE to be open:
Monday to Friday, 09:15 to 15:30 IST.

The dashboard plots the live microprice (size-weighted mid) from Firstock's
best-bid/ask stream. Jev is asked "buy or sell?" every --pace seconds (default
0.3s). Calls overlap, each answer lands the moment it arrives, and the pace backs
off by itself if the key gets rate-limited (the free Vercel tier allows roughly
one call every 2 seconds; $5 of credits removes that).

Every Jev answer goes to strategy.decide(). If it says "buy" or "sell", the loop
rests a limit order at the best bid/ask (no spread paid). The order counts as
filled only when the market trades THROUGH its price, and it's cancelled after
--maker-wait seconds. --taker trades immediately at the ask/bid instead.
Positions are ₹1,00,000 (whole shares), charges are NSE intraday charges
(brokerage, STT, exchange, SEBI, stamp duty, GST), and nothing is hidden.

PAPER ONLY: this reads live prices and simulates fills. It never places an order.
"""

from __future__ import annotations

import json
import os
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import strategy
from .core import RESULTS, console, header, inr, market_open, minutes_to_close
from .firstock import FirstockError, FirstockMarket, charges, load_session, round_trip_bps, trading_symbol
from .judges import JevJudge, JudgeError
from .server import serve

NOTIONAL = 100000.0  # ₹ per side of the paper position
TICK_KEEP_S = 300  # price history kept for the dashboard

QUESTIONS = {
    "side": {
        "type": "choice",
        "instructions": "Which side should this bot hold for the next few seconds: buy (be long) or sell (be short)?",
        "criteria": {"buy": None, "sell": None},
    }
}


def need_session():
    session = load_session()
    if not session:
        raise SystemExit("  not logged in to Firstock today. Run: uv run python -m jevlab login")
    return session


class PaperBook:
    """A ₹1,00,000 long-or-short paper position in whole shares. Tracks shares and cash, so buying at
    the bid or selling at the ask is credited exactly, and charges are kept apart."""

    def __init__(self):
        self.pos, self.qty, self.cash, self.fees = 0, 0, 0.0, 0.0
        self.trades = 0
        self.equity = []  # [t, before_charges, after_charges]

    def fill(self, target: int, px: float) -> None:
        dq = target * int(NOTIONAL // px) - self.qty
        if not dq:
            return
        self.cash -= dq * px
        self.fees += charges("buy" if dq > 0 else "sell", abs(dq) * px)
        self.qty += dq
        self.pos = target
        self.trades += 1

    def gross(self, mid: float) -> float:
        return self.cash + self.qty * mid

    def snap(self, t: float, mid: float) -> dict:
        g = self.gross(mid)
        self.equity.append([round(t, 2), round(g, 2), round(g - self.fees, 2)])
        del self.equity[:-2400]
        return {"pos": self.pos, "qty": self.qty, "gross": round(g, 2), "fees": round(self.fees, 2),
                "net": round(g - self.fees, 2), "trades": self.trades, "equity": self.equity}


def run_loop(symbol: str, pace_s: float, minutes: float, port: int, open_browser: bool, late_ms: float = 1500,
             maker: bool = True, maker_wait: float = 10.0) -> None:
    tsym = trading_symbol(symbol)
    exec_txt = "limit orders (no spread)" if maker else "market orders (+ spread)"
    header("THE JEV LOOP", f"{tsym} on NSE · live prices from Firstock · Jev calls as fast as the key allows "
           f"(floor {pace_s:g}s) · strategy: {strategy.DESCRIPTION} · {exec_txt} · "
           f"{'until Ctrl+C or the close' if not minutes else f'{minutes:g} min'} · ₹1,00,000 paper position")
    if not market_open():
        raise SystemExit("  NSE is closed right now (open Monday to Friday, 09:15 to 15:30 IST). "
                         "The loop needs live prices: run it during market hours. The newsroom works any time.")
    try:
        jev = JevJudge()
    except JudgeError as exc:
        raise SystemExit(f"  Jev key missing: {exc}. Add AI_GATEWAY_API_KEY to .env first.")
    session = need_session()
    try:
        market = FirstockMarket(session, tsym)
        market.start()
    except FirstockError as exc:
        raise SystemExit(f"  Firstock problem: {exc}")
    if not market.ready.wait(20):
        raise SystemExit(f"  no price feed from Firstock after 20s{f' ({market.error})' if market.error else ''}. "
                         "Check the connection, and that you logged in today")
    if NOTIONAL // market.snapshot()["ask"] < 1:
        raise SystemExit(f"  one share of {tsym} costs more than the ₹1,00,000 paper position: pick another stock")
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "loop.json"
    log = open(RESULTS / "loop_log.jsonl", "a")
    book = PaperBook()
    decisions: list[dict] = []
    fills: list[dict] = []
    latencies: list[float] = []
    counts = {"ok": 0, "late": 0, "throttled": 0, "error": 0}
    lock = threading.Lock()
    st = {"interval": pace_s, "streak": 0, "prev": None, "order": None, "last_trade_t": 0.0, "hits": 0, "scored": 0}
    started = time.time()
    serve(port, open_browser, page="loop.html")

    def check_order() -> None:
        """Fill the resting limit order only if the market traded through its price."""
        o = st["order"]
        if not o:
            return
        now = time.time()
        buying = o["buying"]
        through = any((buying and px < o["px"]) or (not buying and px > o["px"])
                      for _, _, px, _ in market.trades_since(o["t"]))
        snap = market.snapshot()
        through |= (buying and snap["ask"] < o["px"]) or (not buying and snap["bid"] > o["px"])
        if through:
            book.fill(o["target"], o["px"])
            fills.append({"t": now, "side": "buy" if buying else "sell", "px": o["px"], "kind": "limit",
                          "call": o["call"], "wait_s": round(now - o["t"], 1)})
            st["order"], st["last_trade_t"] = None, now
        elif now > o["expires"]:
            st["order"] = None

    def write(status: str) -> None:
        with lock:
            check_order()
            mid = market.snapshot()["mid"]
            recent = [d["t"] for d in decisions if d["t"] >= time.time() - 10]
            payload = {
                "status": status, "symbol": tsym, "venue_label": f"{tsym} · NSE · Firstock", "mode": "paper",
                "mode_label": "paper · live Firstock prices", "pace": pace_s, "interval": round(st["interval"], 3),
                "rate_per_s": round(len(recent) / 10, 2), "late_ms": late_ms,
                "strategy_note": strategy.DESCRIPTION, "execution": "limit" if maker else "market", "maker_wait": maker_wait,
                "started": started, "updated": time.time(), "model": jev.model, "notional": NOTIONAL,
                "round_trip_bps": round(round_trip_bps(NOTIONAL), 1), "minutes_to_close": round(minutes_to_close()),
                "counts": dict(counts), "blocks": len(decisions),
                "last_ms": latencies[-1] if latencies else None,
                "avg_ms": round(statistics.mean(latencies[-200:])) if latencies else None,
                "hits": st["hits"], "scored": st["scored"],
                "order": st["order"], "decisions": decisions[-200:], "fills": fills[-100:],
                "book": book.snap(time.time(), mid), "ticks": market.recent_ticks(),
            }
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        os.replace(tmp, out)

    def decide(rec: dict, now: dict) -> str:
        """Hand Jev's call to strategy.decide(), then turn its answer into a (paper) order. Runs under the lock."""
        view = {**rec["state"], "minutes_to_close": round(minutes_to_close(), 1)}
        try:
            choice = strategy.decide({"side": rec["side"], "conf": rec["conf"]}, view, book.pos,
                                     time.time() - st["last_trade_t"])
        except Exception as exc:  # a broken strategy shouldn't kill the loop: show it and hold
            return f"hold · strategy error: {str(exc)[:60]}"
        if choice not in ("buy", "sell", "flat"):
            return str(choice or "hold")
        want = {"buy": 1, "sell": -1, "flat": 0}[choice]
        if want == book.pos:
            if st["order"] and st["order"]["target"] != want:
                st["order"] = None
            return "hold · already " + {1: "long", -1: "short", 0: "flat"}[want]
        if st["order"] and st["order"]["target"] == want:
            return "hold · limit order working"
        if maker:
            buying = want > book.pos
            px = now["bid"] if buying else now["ask"]
            st["order"] = {"target": want, "buying": buying, "px": px, "t": time.time(), "expires": time.time() + maker_wait,
                           "call": rec["block"]}
            return f"limit {'buy' if buying else 'sell'} @ {px:g}"
        buying = want > book.pos
        px = now["ask"] if buying else now["bid"]
        book.fill(want, px)
        fills.append({"t": time.time(), "side": "buy" if buying else "sell", "px": px, "kind": "market", "call": rec["block"], "wait_s": 0})
        st["last_trade_t"] = time.time()
        return f"market {choice} @ {px:g}"

    def ask(seq: int) -> None:
        snap = market.snapshot()
        rec = {"block": seq, "t_ask": time.time(), "state": snap["state"]}
        try:
            ans, meta = jev.ask(snap["state"], QUESTIONS, timeout=5.0, retries=0)
            side = ans["side"]["choice"]
            rec.update(side=side, conf=round(ans["side"]["probs"][side], 3), ms=meta["latency_ms"],
                       status="ok" if meta["latency_ms"] <= late_ms else "late")
        except JudgeError as exc:
            rec.update(side=None, conf=None, ms=None, status="throttled" if "429" in str(exc) else "error",
                       error=str(exc)[:160])
        now = market.snapshot()  # the market as it is when the answer ARRIVES
        rec.update(t=time.time(), mid=now["mid"], micro=now["micro"])
        with lock:
            counts[rec["status"]] += 1
            if rec["ms"]:
                latencies.append(rec["ms"])
            if rec["status"] == "throttled":  # back off hard on a 429, creep back on good answers
                st["interval"], st["streak"] = min(4.0, st["interval"] * 1.6), 0
            elif rec["status"] == "ok":
                st["streak"] += 1
                if st["streak"] >= 3:
                    st["interval"] = max(pace_s, st["interval"] * 0.9)
            prev = st["prev"]
            if prev and now["mid"] != prev["mid"]:  # was the previous call's direction right, up to this one?
                st["hits"] += (now["mid"] > prev["mid"]) == (prev["side"] == "buy")
                st["scored"] += 1
            if rec["status"] == "ok":
                st["prev"] = rec
                rec["action"] = decide(rec, now)
            else:
                rec["action"] = "hold · late" if rec["status"] == "late" else rec["status"]
            decisions.append(rec)
            log.write(json.dumps(rec) + "\n")
        colour = {"buy": "#3fd68a", "sell": "#ff5d6c"}.get(rec["side"], "#f5b53d")
        console.print(f"  {rec['block']:>5}  [{colour}]{(rec['side'] or '-').upper():<5}[/]  "
                      f"{(rec['conf'] or 0):.2f}  {rec['ms'] or '-':>5} ms  [dim]{rec['action']}[/]")

    console.print("  [dim]  #    side   conf     ms       action[/]")
    stop = threading.Event()

    def writer():  # fills resting orders and keeps the dashboard's price history fresh
        while not stop.is_set():
            write("running")
            stop.wait(0.25)

    threading.Thread(target=writer, daemon=True).start()
    seq = 0
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            while (not minutes or time.time() - started < minutes * 60) and market_open():
                seq += 1
                pool.submit(ask, seq)
                time.sleep(st["interval"])
    except KeyboardInterrupt:
        pass
    stop.set()
    write("done")
    log.close()
    market.stop()
    mid = market.snapshot()["mid"]
    g = book.gross(mid)
    console.print(f"\n  {len(decisions)} Jev calls · {book.trades} trades · before charges {inr(g, True)} · "
                  f"charges {inr(book.fees)} · after charges "
                  f"[bold]{'[#3fd68a]' if g - book.fees > 0 else '[#ff5d6c]'}{inr(g - book.fees, True)}[/][/]")
    console.print(f"  direction right {st['hits']}/{st['scored']} · late {counts['late']} · throttled {counts['throttled']}")
    if not market_open():
        console.print("  [dim]NSE closed for the day (15:30 IST)[/]")
````

### `jev-starter/jevlab/newsroom.py`

````python
"""The Jev newsroom: real Indian market headlines arriving on a news terminal, Jev
reading each one live, and the real price move that followed on NSE.

  uv run python -m jevlab newsroom                 # replay the last 72h, one headline every 6s
  uv run python -m jevlab newsroom --gap 4 --hours 48

Why a replay: market news only lands a few times an hour, which is too slow to
watch. So the newsroom replays the last few days of real headlines in fast motion.
Every headline is sent to Jev live as it appears on screen (real answer, real
response time), and because those headlines already happened, the chart can show
what the price actually did over the next hour, from Firstock's 1-minute candles.
Only headlines that came out while NSE was open (09:15 to 15:30 IST) have a price
move to show. Jev never sees the publish time.

The trading rule: trade only headlines Jev rates "Notable" or "Major", in the
direction it calls, from 1 minute after publishing, held for 60 minutes (or until
the 15:30 close). Costs are NSE intraday charges plus a little for the spread.
No orders are ever placed. Needs today's Firstock login, for the candles.
"""

from __future__ import annotations

import json
import os
import time

import pandas as pd

from .core import RESULTS, console, header
from .firstock import FirstockError, SessionExpired, candles, load_session, round_trip_bps
from .judges import JevJudge, JudgeError
from .news import ASSETS, QUESTIONS, fetch_headlines, judge_call
from .server import serve

BEFORE_MIN, AFTER_MIN = 10, 60  # the reaction chart spans publish-10m .. publish+60m
SPREAD_BPS = 2.0  # a rough allowance for crossing the bid/ask spread in and out
NOTIONAL = 100000.0


def price_paths(session, items: list[dict]) -> None:
    """Attach each asset's % move around every headline, from real 1-minute candles."""
    start = (items[0]["published"] - pd.Timedelta(minutes=BEFORE_MIN + 5)).to_pydatetime()
    bars = {}
    for name, tsym in ASSETS.items():
        try:
            df = candles(session, tsym, 1, start)
        except SessionExpired:
            raise
        except FirstockError as exc:
            console.print(f"  [dim]no candles for {name}: {str(exc)[:60]}[/]")
            continue
        df.index = df.index.floor("min")
        bars[name] = df[~df.index.duplicated()]
    for it in items:
        entry_t = it["published"].floor("min") + pd.Timedelta(minutes=1)
        it["paths"] = {}
        for name, df in bars.items():
            if entry_t not in df.index:
                continue  # NSE was closed when this came out
            base = df.loc[entry_t, "open"]
            window = df.loc[entry_t - pd.Timedelta(minutes=BEFORE_MIN): entry_t + pd.Timedelta(minutes=AFTER_MIN), "close"]
            it["paths"][name] = [[round((ts - entry_t).total_seconds() / 60, 1), round(float(1e4 * (px / base - 1)), 2)]
                                 for ts, px in window.items()]


def run_newsroom(hours: float, every: float, port: int, open_browser: bool) -> None:
    header("THE JEV NEWSROOM", f"replaying the last {hours:g}h of real Indian market headlines · one every {every:g}s · "
           f"Jev reads each one live · then the real {AFTER_MIN}-minute price move on NSE")
    try:
        jev = JevJudge()
    except JudgeError as exc:
        raise SystemExit(f"  Jev key missing: {exc}. Add AI_GATEWAY_API_KEY to .env first.")
    session = load_session()
    if not session:
        raise SystemExit("  not logged in to Firstock today (the price charts come from Firstock). "
                         "Run: uv run python -m jevlab login")

    def load_items() -> list[dict]:
        now = pd.Timestamp.now(tz="UTC")
        fresh = [i for i in fetch_headlines(hours) if i["published"] + pd.Timedelta(minutes=AFTER_MIN + 2) < now]
        if fresh:
            console.print(f"  {len(fresh)} headlines · loading the price moves after each one…")
            try:
                price_paths(session, fresh)
            except SessionExpired:
                raise SystemExit("  your Firstock session has ended. Run: uv run python -m jevlab login")
            priced = [i for i in fresh if i["paths"]]
            console.print(f"  {len(priced)} came out while NSE was open, so they get a price chart")
            if len(priced) >= 5:
                fresh = priced
        return fresh

    items = load_items()
    if not items:
        raise SystemExit("  no headlines old enough to score yet")

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "newsroom.json"
    cost_bps = round(round_trip_bps(NOTIONAL) + SPREAD_BPS, 1)
    score = {"read": 0, "tagged": 0, "trades": 0, "right": 0, "net_bps": 0.0, "latency_ms": []}
    feed: list[dict] = []
    started = time.time()
    rnd = {"n": 1, "index": 0}

    def write(status: str) -> None:
        lat = sorted(score["latency_ms"])
        payload = {"status": status, "hours": hours, "every": every, "total": len(items), "index": rnd["index"], "round": rnd["n"],
                   "started": started, "updated": time.time(), "model": jev.model,
                   "cost_bps": cost_bps, "after_min": AFTER_MIN, "before_min": BEFORE_MIN,
                   "score": {**{k: v for k, v in score.items() if k != "latency_ms"},
                             "median_ms": lat[len(lat) // 2] if lat else None},
                   "feed": feed[-300:]}
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, default=str))
        os.replace(tmp, out)

    write("running")
    serve(port, open_browser, page="newsroom.html")
    time.sleep(2.5)  # let the page load before the first headline lands

    try:
        while True:
            for it in items:
                rnd["index"] += 1
                t0 = time.time()
                row = {"headline": it["headline"], "source": it["source"], "published": it["published"].timestamp(),
                       "paths": it["paths"], "arrived": t0, "answer": None}
                feed.append(row)
                write("running")  # the headline hits the wire before Jev has answered
                state = {"headline": it["headline"], "summary": it["summary"], "source": it["source"]}
                try:
                    ans, meta = jev.ask(state, QUESTIONS, timeout=10.0, retries=3)
                except JudgeError as exc:
                    row.update(error=str(exc)[:120], answered=time.time())
                    write("running")
                    console.print(f"  [#f5b53d]skip[/] {it['headline'][:70]} ({str(exc)[:40]})")
                    time.sleep(max(0.0, every - (time.time() - t0)))
                    continue
                name, side = judge_call(ans)
                side = side if name else 0  # nothing tradeable, no trade
                path = it["paths"].get(name or "NIFTY") or []
                ret = next((v for m, v in reversed(path) if 0 < m <= AFTER_MIN), None)  # 60 min, or the close
                row.update(answer=ans, ms=meta["latency_ms"], answered=time.time(), asset=name,
                           direction=ans["direction"]["choice"], impact=ans["impact"]["score"],
                           trade=bool(side), side=side, ret_bps=ret)
                score["read"] += 1
                score["latency_ms"].append(meta["latency_ms"])
                if name:
                    score["tagged"] += 1
                if side and ret is not None:
                    score["trades"] += 1
                    score["right"] += int(side * ret > 0)
                    row["net_bps"] = round(side * ret - cost_bps, 1)
                    score["net_bps"] += row["net_bps"]
                write("running")
                tag = f"{name or '—':<9} {row['direction']:<8} impact {row['impact']:.1f}"
                console.print(f"  {meta['latency_ms']:>4} ms  {tag}  {'[bold]TRADE[/]' if side else '[dim]no trade[/]'}  "
                              f"[dim]{it['headline'][:60]}[/]")
                time.sleep(max(0.0, every - (time.time() - t0)))
            # round finished: pull the latest headlines and go again, with a fresh scoreboard
            console.print(f"\n  round {rnd['n']} done · reloading headlines for the next round")
            items = load_items() or items
            rnd["n"] += 1
            rnd["index"] = 0
            score.update(read=0, tagged=0, trades=0, right=0, net_bps=0.0, latency_ms=[])
    except KeyboardInterrupt:
        pass
    write("done")
    console.print(f"\n  {score['read']} headlines read · {score['tagged']} tagged to an asset · {score['trades']} worth trading · "
                  f"{score['right']} right · {score['net_bps']:+.1f} bps after costs")
````

### `jev-starter/jevlab/brain.py`

````python
"""Claude as the big-picture brain (Path 2).

Every few minutes, Claude reads a plain summary of the market (the stock's recent
moves and range, NIFTY's move today, time left in the session, and the latest
Indian market headlines) and sets the bias for the next stretch: long, short, or
flat. Jev and strategy.py still make the fast calls, but only in the direction
Claude allows.

Uses the same Vercel AI Gateway key as Jev. The model is CLAUDE_MODEL in .env
(default anthropic/claude-sonnet-5). Claude on the gateway needs AI Gateway
credits (the paid tier).
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import timedelta

import requests
from dotenv import load_dotenv

from .core import ist_now, minutes_to_close
from .firstock import FirstockError, candles, quote

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

CHAT_URL = "https://ai-gateway.vercel.sh/v1/chat/completions"


def market_summary(session, tsym: str) -> dict:
    """Plain numbers Claude can reason about, from Firstock's candles and quotes."""
    now = ist_now()
    df = candles(session, tsym, 5, now - timedelta(days=5), now)
    closes = [float(c) for c in df["close"].tolist()][-49:]  # 5-minute bars, the last ~4 trading hours
    if len(closes) < 13:
        raise FirstockError(f"not enough 5-minute candles for {tsym} yet")
    q = quote(session, tsym)
    pct = lambda a, b: round(100 * (b / a - 1), 2) if a else None
    moves = [abs(pct(a, b)) for a, b in zip(closes, closes[1:])]
    out = {
        "stock": tsym, "exchange": "NSE", "time_ist": now.strftime("%a %H:%M"),
        "minutes_to_close": round(minutes_to_close(now)),
        "price": q["ltp"] or closes[-1],
        "change_15m_pct": pct(closes[-4], closes[-1]),
        "change_1h_pct": pct(closes[-13], closes[-1]),
        "change_4h_pct": pct(closes[0], closes[-1]),
        "change_today_pct": pct(q["open"], q["ltp"]),
        "change_vs_prev_close_pct": pct(q["prev_close"], q["ltp"]),
        "day_high": q["high"], "day_low": q["low"],
        "avg_5m_move_pct": round(sum(moves) / len(moves), 3),
    }
    try:
        n = quote(session, "NIFTY")
        out["nifty_change_today_pct"] = pct(n["open"], n["ltp"])
        out["nifty_vs_prev_close_pct"] = pct(n["prev_close"], n["ltp"])
    except FirstockError:
        pass
    return out


def headlines(limit: int = 8) -> list[str]:
    try:
        from .news import fetch_headlines
        return [h["headline"] for h in fetch_headlines(12, quiet=True)][-limit:]
    except Exception:
        return []


PROMPT = """You are the portfolio manager for a small, cautious intraday trading bot on India's NSE.
It trades one stock. A fast AI makes buy/sell calls every second, but it can only trade in the direction you allow.
Positions are intraday only: the bot closes everything by 15:10 IST.
Decide the bias for the next {minutes} minutes: "long" (only buying allowed), "short" (only selling allowed),
or "flat" (stay out, close any position).
If the evidence leans one way (momentum across timeframes, the stock against NIFTY, the news), pick that side and let
"confidence" say how strongly it leans. Choose "flat" only when the signals genuinely conflict, the stock is dead,
or there is too little time left in the session for a trade to work.

Market data:
{summary}

Latest Indian market headlines:
{news}

Reply with ONLY a JSON object: {{"bias": "long" | "short" | "flat", "confidence": 0.0-1.0, "reason": "one short sentence"}}"""


class Brain:
    def __init__(self, session, tsym: str, every_min: float):
        self.key = os.getenv("AI_GATEWAY_API_KEY", "").strip()
        self.model = os.getenv("CLAUDE_MODEL", "anthropic/claude-sonnet-5").strip()
        self.session, self.tsym, self.every = session, tsym, every_min
        self.state = {"bias": None, "confidence": None, "reason": "waiting for Claude's first read", "t": None,
                      "model": self.model, "ms": None, "error": None}
        self.lock = threading.Lock()

    def think(self) -> None:
        t0 = time.time()
        try:
            summary = market_summary(self.session, self.tsym)
            news = "\n".join(f"- {h}" for h in headlines()) or "- (none)"
            body = {"model": self.model, "temperature": 0, "max_tokens": 200, "messages": [
                {"role": "user", "content": PROMPT.format(minutes=self.every, summary=json.dumps(summary, indent=1), news=news)}]}
            r = requests.post(CHAT_URL, headers={"Authorization": f"Bearer {self.key}"}, json=body, timeout=60)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
            text = r.json()["choices"][0]["message"]["content"]
            out = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            bias = out.get("bias") if out.get("bias") in ("long", "short", "flat") else "flat"
            with self.lock:
                self.state.update(bias=bias, confidence=float(out.get("confidence") or 0), reason=str(out.get("reason", ""))[:160],
                                  t=time.time(), ms=round((time.time() - t0) * 1000), error=None, summary=summary)
        except Exception as exc:  # keep the last bias; if there's never been one, the bot stays flat
            with self.lock:
                self.state["error"] = str(exc)[:160]
                if self.state["bias"] is None:
                    self.state.update(bias="flat", reason="Claude unavailable, staying out", t=time.time())

    def start(self, stop: threading.Event) -> None:
        def run():
            while not stop.is_set():
                self.think()
                stop.wait(self.every * 60)
        threading.Thread(target=run, daemon=True).start()

    def current(self) -> dict:
        with self.lock:
            return dict(self.state)
````

### `jev-starter/jevlab/bot.py`

````python
"""The trading-day bot (Path 2): Jev + Claude + your strategy, trading one NSE stock on Firstock.

  uv run python -m jevlab bot --minutes 5   # a 5-minute test (paper unless FIRSTOCK_MODE=live)
  uv run python -m jevlab bot --paper       # force paper mode, whatever .env says
  uv run python -m jevlab bot --minutes 0   # the whole trading day (this is what the server runs)

A trading day:
  * The server's timer starts the bot at 09:05 IST, Monday to Friday. It waits for
    today's Firstock login (uv run python -m jevlab login) and for NSE to open at 09:15.
  * Claude (the brain) reads the market every --brain-every minutes and sets the bias:
    long, short or flat.
  * Jev makes a fast buy/sell call several times a second.
  * strategy.py combines them. By default it only trades in Claude's direction, and only
    when Jev is 85%+ sure.
  * Orders are intraday limit orders at the best bid/ask (no spread paid), cancelled if
    they don't fill within --maker-wait seconds.
  * No new positions after 15:00. At 15:10 it cancels its orders, closes the position and
    stops for the day.

Modes (FIRSTOCK_MODE in .env):
  paper (default)  live Firstock prices, simulated fills. No order ever reaches the exchange.
  live             real orders, real money. Refused unless JEV_LIVE_CONFIRM is the exact phrase
                   (see firstock.py). Firstock only accepts API orders from the static IP you
                   registered with them (a SEBI rule), so live trading runs on the server.

Safety, always on:
  * MAX_POSITION_INR caps the position (default ₹10,000), in whole shares.
  * MAX_DAILY_LOSS_INR: hit it and the bot cancels everything, closes the position and stops
    trading for the day (default ₹500). This holds across restarts.
  * MAX_ORDERS_PER_DAY caps orders (default 100), and there's never more than one order
    action a second.
  * Kill switch: create a file called STOP in the project folder, and the bot closes out and halts.
  * On shutdown it cancels its orders and closes the position.
  * Behind all of that, Firstock squares off any intraday position still open near the close.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import time as dtime
from pathlib import Path

from . import strategy
from .brain import Brain
from .core import OPEN, RESULTS, console, header, inr, ist_now, market_open, minutes_to_close
from .firstock import (DONE, FirstockError, FirstockMarket, FirstockTrader, SessionExpired, charges, live_mode,
                       load_session, round_trip_bps, security_info, trading_symbol)
from .judges import JevJudge, JudgeError
from .loop import QUESTIONS
from .server import serve

NO_NEW_AFTER = dtime(15, 0)  # no new positions after this (IST)
FLATTEN_AT = dtime(15, 10)   # close everything and stop for the day
STOP_FILE = Path(__file__).resolve().parent.parent / "STOP"
DAY_FILE = RESULTS / "bot_day.json"  # today's P&L and halt, so a restart can't reset the loss limit


class Book:
    """Position and P&L from actual fills: shares, cash and charges, marked to the live mid."""

    def __init__(self):
        self.qty, self.cash, self.fees, self.trades = 0, 0.0, 0.0, 0
        self.equity: list[list[float]] = []

    def fill(self, dq: int, px: float, fee_inr: float) -> None:
        self.cash -= dq * px
        self.qty += dq
        self.fees += fee_inr
        self.trades += 1

    def net(self, mid: float) -> float:
        return self.cash + self.qty * mid - self.fees

    def snap(self, t: float, mid: float, carry: float) -> dict:
        g = carry + self.cash + self.qty * mid
        self.equity.append([round(t, 2), round(g, 2), round(g - self.fees, 2)])
        del self.equity[:-2400]
        pos = 1 if self.qty > 0 else -1 if self.qty < 0 else 0
        return {"pos": pos, "qty": self.qty, "gross": round(g, 2), "fees": round(self.fees, 2),
                "net": round(g - self.fees, 2), "trades": self.trades, "equity": self.equity}


def run_bot(symbol: str, pace_s: float, minutes: float, port: int, open_browser: bool, late_ms: float = 1500,
            maker_wait: float = 10.0, brain_every: float = 10.0, force_paper: bool = False) -> None:
    tsym = trading_symbol(symbol)
    try:
        mode = "paper" if force_paper else live_mode()
    except FirstockError as exc:
        raise SystemExit(f"  {exc}")
    position_inr = float(os.getenv("MAX_POSITION_INR", "10000"))
    max_loss = float(os.getenv("MAX_DAILY_LOSS_INR", "500"))
    max_orders = int(os.getenv("MAX_ORDERS_PER_DAY", "100"))
    mode_label = {"paper": "paper · live Firstock prices, simulated fills", "live": "LIVE · REAL MONEY"}[mode]
    header("THE JEV BOT", f"{tsym} on NSE via Firstock · {mode_label} · Claude sets the bias every {brain_every:g} min · "
           f"Jev calls as fast as the key allows · strategy: {strategy.DESCRIPTION} · max position {inr(position_inr)} · "
           f"daily loss limit {inr(max_loss)} · no new trades after 15:00 · all closed at 15:10 IST")
    if mode == "live":
        console.print("  [bold #ff5d6c]LIVE MODE: this bot is trading real money.[/] Kill switch: create a file named STOP.")
    try:
        jev = JevJudge()
    except JudgeError as exc:
        raise SystemExit(f"  Jev key missing: {exc}. Add AI_GATEWAY_API_KEY to .env first.")

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "loop.json"
    today = ist_now().date().isoformat()
    try:
        day = json.loads(DAY_FILE.read_text())
    except (OSError, ValueError):
        day = {}
    if day.get("date") != today or day.get("mode") != mode or day.get("symbol") != tsym:
        day = {}
    carry = float(day.get("net", 0.0))  # P&L from earlier runs today (a restart must not reset the loss limit)

    market = trader = brain = None
    book = Book()
    decisions: list[dict] = []
    fills: list[dict] = []
    latencies: list[float] = []
    counts = {"ok": 0, "late": 0, "throttled": 0, "error": 0}
    lock = threading.Lock()
    st = {"interval": pace_s, "streak": 0, "prev": None, "order": None, "last_trade_t": 0.0, "hits": 0, "scored": 0,
          "halted": day.get("halted"), "fatal": None, "note": "starting", "final": None}
    if st["halted"] and "STOP" in st["halted"] and not STOP_FILE.exists():
        st["halted"] = None  # the kill switch file is gone: trading may resume
    started = time.time()
    log = open(RESULTS / "bot_log.jsonl", "a")
    serve(port, open_browser, page="loop.html")

    def note() -> str:
        now = ist_now()
        if st["final"]:
            return st["final"]
        if st["halted"]:
            return f"HALTED for today: {st['halted']}"
        if market is None:
            return st["note"]
        if not market_open(now):
            return "waiting for NSE to open at 09:15 IST" if now.time() < OPEN else "NSE is closed"
        if not market.ready.is_set() or not market.fresh():
            return "no trades printing: a holiday, a halt, or the feed is catching up"
        if now.time() >= NO_NEW_AFTER:
            return "no new positions after 15:00 · closing out at 15:10 IST"
        return f"trading · {round(minutes_to_close(now))} min to the close"

    def write(status: str, final: str | None = None) -> None:
        if final:
            st["final"] = final
        with lock:
            snap = market.snapshot() if market is not None and market.ready.is_set() else None
            if snap:
                check_order()
                risk_check(snap["mid"])
            mid = snap["mid"] if snap else 0.0
            net_today = carry + (book.net(mid) if snap else 0.0)
            _save_day(today, mode, tsym, net_today, st["halted"])
            recent = [d["t"] for d in decisions if d["t"] >= time.time() - 10]
            o = st["order"]
            payload = {
                "status": status, "symbol": tsym, "mode": mode, "venue_label": f"{tsym} · NSE · Firstock",
                "mode_label": mode_label, "note": note(), "halted": st["halted"],
                "pace": pace_s, "interval": round(st["interval"], 3), "rate_per_s": round(len(recent) / 10, 2),
                "late_ms": late_ms, "strategy_note": strategy.DESCRIPTION, "execution": "limit", "maker_wait": maker_wait,
                "started": started, "updated": time.time(), "model": jev.model, "notional": position_inr,
                "round_trip_bps": round(round_trip_bps(position_inr), 1), "minutes_to_close": round(minutes_to_close()),
                "counts": dict(counts), "blocks": len(decisions),
                "last_ms": latencies[-1] if latencies else None,
                "avg_ms": round(statistics.mean(latencies[-200:])) if latencies else None,
                "hits": st["hits"], "scored": st["scored"], "brain": brain.current() if brain else None,
                "order": ({"target": o["target"], "buying": o["buying"], "px": o["px"], "t": o["t"]} if o else None),
                "decisions": decisions[-200:], "fills": fills[-100:],
                "book": book.snap(time.time(), mid, carry) if snap else {"pos": 0, "qty": 0, "gross": round(carry, 2),
                                                                         "fees": 0.0, "net": round(carry, 2), "trades": 0,
                                                                         "equity": []},
                "ticks": market.recent_ticks() if market is not None else [],
            }
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, default=str))
        os.replace(tmp, out)

    def record_fill(dq: int, px: float, kind: str, call, waited: float) -> None:
        book.fill(dq, px, charges("buy" if dq > 0 else "sell", abs(dq) * px))
        fills.append({"t": time.time(), "side": "buy" if dq > 0 else "sell", "px": px, "qty": abs(dq), "kind": kind,
                      "call": call, "wait_s": round(waited, 1)})
        st["last_trade_t"] = time.time()

    def check_order() -> None:
        o = st["order"]
        if not o:
            return
        now_s = time.time()
        if trader is None:  # paper: fill only if the market traded through our price
            through = any((o["buying"] and px < o["px"]) or (not o["buying"] and px > o["px"])
                          for _, _, px, _ in market.trades_since(o["t"]))
            if through:
                record_fill(o["qty"] if o["buying"] else -o["qty"], o["px"], "limit", o["call"], now_s - o["t"])
                st["order"] = None
            elif now_s > o["expires"]:
                st["order"] = None
            return
        try:
            s = trader.order(o["id"])
            new = s["filled"] - o["seen_qty"]
            if new > 0:  # count only the newly filled shares
                record_fill(new if o["buying"] else -new, s["avg_px"] or o["px"], "limit", o["call"], now_s - o["t"])
                o["seen_qty"] = s["filled"]
            if s["status"] in DONE:
                if s["status"] == "REJECTED":
                    console.print(f"  [#ff5d6c]order rejected[/]: {s['reason'] or 'no reason given'}")
                st["order"] = None
            elif now_s > o["expires"]:
                trader.cancel(o["id"])
                o["expires"] = now_s + 3  # look once more for fills that raced the cancel, then let go
                if s["status"] == "UNKNOWN" and now_s - o["t"] > maker_wait + 30:
                    st["order"] = None
        except SessionExpired as exc:
            st["fatal"] = f"Firstock session ended ({exc})"
        except FirstockError:
            pass

    def close_out() -> None:
        snap = market.snapshot()
        if trader is None:  # paper: cross the spread, pay the charges
            if book.qty:
                record_fill(-book.qty, snap["bid"] if book.qty > 0 else snap["ask"], "market", None, 0)
            return
        try:
            trader.cancel_all()
            done, left = trader.flatten(snap["bid"], snap["ask"])
        except FirstockError as exc:
            console.print(f"  [#ff5d6c]couldn't close the position: {exc}. Close it in the Firstock app.[/]")
            return
        for dq, px in done:
            record_fill(dq, px, "market", None, 0)
        if left:
            console.print(f"  [#ff5d6c]{left:+d} shares still open. Close them in the Firstock app.[/]")

    def halt(reason: str) -> None:
        st["halted"] = reason
        st["order"] = None
        console.print(f"\n  [bold #f5b53d]HALTED: {reason}[/]. Cancelling orders and closing the position.")
        close_out()

    def risk_check(mid: float) -> None:
        if st["halted"] or market is None:
            return
        if carry + book.net(mid) < -max_loss:
            halt(f"daily loss limit ({inr(max_loss)}) reached")
        elif STOP_FILE.exists():
            halt("kill switch (STOP file)")

    def decide(rec: dict, now: dict) -> str:
        """Jev's call + Claude's bias -> strategy.decide() -> an intraday limit order. Runs under the lock."""
        if st["halted"]:
            return f"hold · halted ({st['halted']})"
        bias = brain.current().get("bias")
        if bias is None:
            return "hold · waiting for Claude's first read"
        view = {**rec["state"], "claude_bias": bias, "minutes_to_close": round(minutes_to_close(), 1)}
        pos = 1 if book.qty > 0 else -1 if book.qty < 0 else 0
        try:
            choice = strategy.decide({"side": rec["side"], "conf": rec["conf"]}, view, pos, time.time() - st["last_trade_t"])
        except Exception as exc:
            return f"hold · strategy error: {str(exc)[:60]}"
        if choice not in ("buy", "sell", "flat"):
            return str(choice or "hold")
        want = {"buy": 1, "sell": -1, "flat": 0}[choice]
        if want and ist_now().time() >= NO_NEW_AFTER:
            if pos == 0 or want == pos:
                return "hold · no new positions after 15:00"
            want = 0  # late in the day a flip becomes a close
        if want == pos:
            return "hold · already " + {1: "long", -1: "short", 0: "flat"}[want]
        if st["order"]:
            if st["order"]["target"] == want:
                return "hold · limit order working"
            if trader:
                trader.cancel(st["order"]["id"])
            st["order"] = None
        size = int(position_inr // now["mid"])
        if size < 1:
            return "hold · one share costs more than MAX_POSITION_INR"
        dq = want * size - book.qty
        buying = dq > 0
        qty = abs(dq)
        px = now["bid"] if buying else now["ask"]
        order = {"target": want, "buying": buying, "qty": qty, "px": px, "t": time.time(), "expires": time.time() + maker_wait,
                 "call": rec["block"], "seen_qty": 0, "id": None}
        if trader:
            try:
                order["id"] = trader.place_limit("buy" if buying else "sell", qty, px)
            except SessionExpired:
                raise
            except FirstockError as exc:
                return f"hold · order rejected: {str(exc)[:70]}"
        st["order"] = order
        return f"limit {'buy' if buying else 'sell'} {qty} @ {px:g}"

    def ask(seq: int) -> None:
        snap = market.snapshot()
        rec = {"block": seq, "t_ask": time.time(), "state": snap["state"]}
        try:
            ans, meta = jev.ask(snap["state"], QUESTIONS, timeout=5.0, retries=0)
            side = ans["side"]["choice"]
            rec.update(side=side, conf=round(ans["side"]["probs"][side], 3), ms=meta["latency_ms"],
                       status="ok" if meta["latency_ms"] <= late_ms else "late")
        except JudgeError as exc:
            rec.update(side=None, conf=None, ms=None, status="throttled" if "429" in str(exc) else "error", error=str(exc)[:160])
        now = market.snapshot()
        rec.update(t=time.time(), mid=now["mid"], micro=now["micro"])
        with lock:
            counts[rec["status"]] += 1
            if rec["ms"]:
                latencies.append(rec["ms"])
            if rec["status"] == "throttled":
                st["interval"], st["streak"] = min(4.0, st["interval"] * 1.6), 0
            elif rec["status"] == "ok":
                st["streak"] += 1
                if st["streak"] >= 3:
                    st["interval"] = max(pace_s, st["interval"] * 0.9)
            prev = st["prev"]
            if prev and now["mid"] != prev["mid"]:
                st["hits"] += (now["mid"] > prev["mid"]) == (prev["side"] == "buy")
                st["scored"] += 1
            if rec["status"] == "ok":
                st["prev"] = rec
                try:
                    rec["action"] = decide(rec, now)
                except SessionExpired as exc:
                    st["fatal"] = f"Firstock session ended ({exc})"
                    rec["action"] = "hold · Firstock session ended"
            else:
                rec["action"] = "hold · late" if rec["status"] == "late" else rec["status"]
            decisions.append(rec)
            log.write(json.dumps(rec) + "\n")
            log.flush()
        if rec["action"].startswith("limit") or rec["action"].startswith("hold · order"):
            console.print(f"  {ist_now().strftime('%H:%M:%S')}  #{rec['block']:<6} Jev {(rec['side'] or '-').upper():<4} "
                          f"{(rec['conf'] or 0):.2f}  →  {rec['action']}")

    stop = threading.Event()

    def writer():
        while not stop.is_set():
            try:
                write("running")
            except Exception as exc:  # a hiccup reading the exchange shouldn't stop the bot
                console.print(f"  [dim]status update skipped: {str(exc)[:80]}[/]")
            stop.wait(0.5)

    threading.Thread(target=writer, daemon=True).start()

    # ---- wait for the day to start: a trading day, today's login, and (below) the 09:15 open
    now = ist_now()
    if now.weekday() >= 5:
        _finish(stop, write, "NSE is closed today (weekend)")
        return
    if now.time() >= FLATTEN_AT:
        _finish(stop, write, "the trading day is over (the bot trades 09:15 to 15:10 IST)")
        return
    session, told = load_session(), False
    if minutes and not (session and market_open(now)):
        _finish(stop, write, "not logged in to Firstock today: run uv run python -m jevlab login" if not session else
                "NSE is closed right now: test the bot during market hours (09:15 to 15:30 IST, Monday to Friday)")
        return
    while not session:
        st["note"] = "waiting for today's Firstock login: uv run python -m jevlab login"
        if not told:
            console.print(f"  [#f5b53d]{st['note']}[/]")
            told = True
        if ist_now().time() >= NO_NEW_AFTER:
            _finish(stop, write, "no Firstock login today, so no trading")
            return
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            _finish(stop, write, "stopped")
            return
        session = load_session()
    try:
        info = security_info(session, tsym)
        market = FirstockMarket(session, tsym, info)
        market.start()
        if mode == "live":
            trader = FirstockTrader(session, tsym, info, max_orders)
            trader.cancel_all()  # start clean: no stale bot orders from a previous run
            cash = trader.cash()
            console.print(f"  Firstock live account connected{f' · cash {inr(cash)}' if cash is not None else ''}")
            qty, avg = trader.position()
            if qty:  # adopt the open position, so the numbers are honest from the first second
                book.qty, book.cash = qty, -qty * avg
                console.print(f"  existing intraday position adopted: {qty:+d} {tsym} @ {avg:g}")
    except FirstockError as exc:
        _finish(stop, write, f"Firstock problem: {exc}")
        raise SystemExit(1)
    if day and book.qty and market.ready.wait(20):  # a restart: the earlier P&L is in carry, so mark from now
        book.cash = -book.qty * market.snapshot()["mid"]
    brain = Brain(session, tsym, brain_every)
    brain.start(stop)

    console.print("  [dim]trades and orders print here · the dashboard shows every call[/]")
    seq, waiting_said = 0, None
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            while not minutes or time.time() - started < minutes * 60:
                if st["fatal"] or ist_now().time() >= FLATTEN_AT:
                    break
                live_now = (market_open() and market.ready.is_set() and market.fresh() and not st["halted"])
                if not live_now:
                    if note() != waiting_said:
                        waiting_said = note()
                        console.print(f"  [dim]{waiting_said}[/]")
                    time.sleep(1)
                    continue
                waiting_said = None
                seq += 1
                pool.submit(ask, seq)
                time.sleep(st["interval"])
    except KeyboardInterrupt:
        pass
    stop.set()
    time.sleep(0.6)  # let the last status write finish
    with lock:
        try:
            if st["order"] and trader:
                trader.cancel(st["order"]["id"])
            st["order"] = None
            if market.ready.is_set():
                close_out()
        except SessionExpired:
            console.print("  [#ff5d6c]Firstock session ended, so the bot couldn't close out. Check the Firstock app: "
                          "Firstock squares off intraday positions near the close.[/]")
    reason = st["fatal"] or ("closed out for the day" if ist_now().time() >= FLATTEN_AT else "stopped")
    st["final"] = reason
    market.stop()
    write("done")
    log.close()
    mid = market.snapshot()["mid"] if market.ready.is_set() else 0.0
    console.print(f"\n  {len(decisions)} Jev calls · {book.trades} fills · charges {inr(book.fees)} · "
                  f"net this run {inr(book.net(mid), True)} · net today {inr(carry + book.net(mid), True)} · {reason}")
    if st["fatal"]:
        console.print("  log in again (uv run python -m jevlab login); the server restarts the bot by itself")
        sys.exit(1)


def _save_day(date: str, mode: str, symbol: str, net: float, halted) -> None:
    tmp = DAY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"date": date, "mode": mode, "symbol": symbol, "net": round(net, 2), "halted": halted}))
    os.replace(tmp, DAY_FILE)


def _finish(stop: threading.Event, write, why: str) -> None:
    console.print(f"  {why}")
    stop.set()
    time.sleep(0.6)
    write("done", why)
````

### `jev-starter/deploy/jev-bot.service`

````ini
# systemd service: runs the Jev bot for one trading day, and restarts it if it crashes.
# jev-bot.timer starts it at 09:05 IST, Monday to Friday. It waits for your daily Firstock login
# and the 09:15 open, and stops by itself after closing out at 15:10.
# Install: sudo cp deploy/jev-bot.service deploy/jev-bot.timer /etc/systemd/system/ && sudo systemctl daemon-reload
#          sudo systemctl enable --now jev-bot.timer
# Logs:    journalctl -u jev-bot -f        Stop for today: sudo systemctl stop jev-bot
[Unit]
Description=Jev trading bot (NSE via Firstock), one trading day
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/root/jev-starter
ExecStart=/root/.local/bin/uv run python -m jevlab bot --minutes 0 --no-open
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=30
KillSignal=SIGINT
TimeoutStopSec=90
````

### `jev-starter/deploy/jev-bot.timer`

````ini
# systemd timer: starts jev-bot.service at 09:05 India time, Monday to Friday.
# (On an exchange holiday the bot sees no trades printing and just holds until 15:10.)
# Check it: systemctl list-timers jev-bot.timer
[Unit]
Description=Start the Jev trading bot each trading day

[Timer]
OnCalendar=Mon..Fri *-*-* 09:05:00 Asia/Kolkata
Persistent=true

[Install]
WantedBy=timers.target
````

### `jev-starter/dashboard/loop.html`

````html
<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jev Loop</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#06080c;--bg2:#0c1016;--panel:#0e131a;--line:#1a222d;--line2:#253041;--fg:#e9eef4;--muted:#8a95a5;--dim:#586272;
--jev:#8b7bff;--good:#3fd68a;--bad:#ff5d6c;--late:#f5b53d;--mono:"JetBrains Mono",ui-monospace,monospace}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;color:var(--fg);font:14px/1.45 Inter,-apple-system,BlinkMacSystemFont,sans-serif;-webkit-font-smoothing:antialiased;
background:radial-gradient(1000px 520px at 90% -15%,rgba(139,123,255,.18),transparent 60%),radial-gradient(900px 500px at -10% 115%,rgba(63,214,138,.06),transparent 60%),var(--bg)}
.app{height:100vh;min-height:680px;display:grid;grid-template-rows:auto minmax(0,1fr);gap:12px;padding:14px 18px 12px;max-width:1760px;margin:0 auto}
header{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{font:800 23px/1 Inter;letter-spacing:-.025em}
.brand em{font-style:normal;background:linear-gradient(95deg,var(--jev),#d6ccff);-webkit-background-clip:text;background-clip:text;color:transparent}
.stats{display:flex;gap:16px;font:12px var(--mono);color:var(--dim)}
.stats b{color:var(--fg);font-weight:500}
.spacer{flex:1}
.pill{font:500 11.5px var(--mono);padding:6px 10px;border-radius:999px;border:1px solid var(--line2);color:var(--muted);background:rgba(12,16,22,.7);display:flex;align-items:center;gap:7px}
.pill.model{color:#cfc7ff;border-color:rgba(139,123,255,.45);background:rgba(139,123,255,.12)}
.live{width:7px;height:7px;border-radius:50%;background:var(--good);box-shadow:0 0 10px var(--good);animation:pulse 1.3s infinite}
.done .live{background:var(--dim);box-shadow:none;animation:none}
@keyframes pulse{50%{opacity:.35}}
.grid{display:grid;grid-template-columns:minmax(0,2.05fr) minmax(0,1fr);gap:12px;min-height:0}
.card{background:linear-gradient(180deg,rgba(14,19,26,.95),rgba(12,16,22,.95));border:1px solid var(--line);border-radius:18px;min-height:0;overflow:hidden}
.main{display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;padding:16px 18px 12px;gap:10px}
.pxrow{display:flex;align-items:flex-start;gap:20px}
.price{font:800 clamp(40px,4.6vw,68px)/1 var(--mono);letter-spacing:-.04em;transition:color .25s}
.price.up{color:var(--good)} .price.down{color:var(--bad)}
.sub{display:flex;gap:16px;margin-top:8px;font:12.5px var(--mono);color:var(--muted);flex-wrap:wrap}
.sub b{font-weight:600}
.action{margin-left:auto;text-align:right}
.action .verb{font:700 34px/1 Inter;letter-spacing:-.02em;transition:color .2s}
.action .meta{font:12px var(--mono);color:var(--muted);margin-top:8px}
.statebox{font:11.5px/1.7 var(--mono);color:var(--muted);background:rgba(6,8,12,.55);border:1px solid var(--line);border-radius:10px;padding:7px 11px;
display:flex;flex-wrap:wrap;gap:2px 16px}
.statebox span b{color:var(--fg);font-weight:500}
.statebox .lbl{color:var(--jev);font-weight:600}
.chart{position:relative;min-height:0}
.chart svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.ax{fill:var(--dim);font:10.5px var(--mono)} .gl{stroke:var(--line);stroke-width:1}
.dots{display:flex;gap:3px;align-items:center;height:22px;overflow:hidden}
.dots i{flex:0 0 7px;height:16px;border-radius:3px;opacity:.9}
.foot{display:flex;justify-content:space-between;font:11px var(--mono);color:var(--dim);margin-top:6px}
.side{display:grid;grid-template-rows:auto auto minmax(0,1fr);gap:12px;min-height:0}
.pad{padding:14px 16px}
.eyebrow{font:600 10.5px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--dim);margin-bottom:8px}
.big{display:flex;align-items:baseline;gap:12px}
.big b{font:800 54px/1 Inter;letter-spacing:-.03em;transition:color .2s}
.big span{font:500 26px var(--mono);color:var(--muted)}
.bars{display:grid;grid-template-columns:36px 1fr 44px;gap:8px 10px;align-items:center;margin-top:12px;font:12px var(--mono);color:var(--muted)}
.bar{height:9px;border-radius:99px;background:var(--line);overflow:hidden}
.bar i{display:block;height:100%;border-radius:99px;transition:width .35s ease}
.bars .v{text-align:right;color:var(--fg)}
.money{display:grid;grid-template-columns:1fr auto;gap:6px 12px;font:13px var(--mono);align-items:baseline}
.money .k{color:var(--muted)} .money .v{text-align:right;font-weight:600}
.money .net{font:800 28px var(--mono);letter-spacing:-.03em}
.money hr{grid-column:1/-1;border:0;border-top:1px solid var(--line);margin:4px 0}
.spark{height:62px;margin-top:10px;position:relative}
.spark svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.feed{display:flex;flex-direction:column;min-height:0}
.feed .eyebrow{padding:14px 16px 0}
.tbl{flex:1;min-height:0;overflow:hidden;padding:0 10px 10px}
table{width:100%;border-collapse:collapse;font:12px var(--mono)}
th{color:var(--dim);font-weight:400;text-align:left;padding:5px 6px;border-bottom:1px solid var(--line)}
td{padding:5px 6px;white-space:nowrap;border-bottom:1px solid rgba(26,34,45,.55)}
td.r,th.r{text-align:right}
tr.buy td{background:rgba(63,214,138,.045)} tr.sell td{background:rgba(255,93,108,.045)} tr.hold td{background:rgba(245,181,61,.05)}
tr.fresh td{animation:fresh .8s ease-out}
@keyframes fresh{from{background:rgba(139,123,255,.28)}}
.g{color:var(--good)} .r{color:var(--bad)} .a{color:var(--late)} .d{color:var(--dim)}
body.clean .moneycard,body.clean .pnl{display:none!important}
.act-trade{color:var(--jev);font-weight:700} .act-hold{color:var(--dim)}
.brainline{margin-top:12px;padding:9px 11px;border-radius:10px;border:1px solid rgba(224,122,85,.4);background:rgba(224,122,85,.08);font:12px/1.45 var(--mono);color:var(--muted)}
.brainline b{color:#f0a283}
.wait{position:absolute;inset:0;display:grid;place-items:center;color:var(--dim);font:13px var(--mono)}
@media (max-width:1050px){.app{height:auto}.grid{grid-template-columns:1fr}.chart{min-height:300px}}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand"><em>Jev</em> Loop</div>
    <div class="stats" id="stats"></div>
    <div class="spacer"></div>
    <div class="pill" id="runPill"><span class="live"></span><span id="runText">paper mode</span></div>
    <div class="pill" id="mkt">—</div>
    <div class="pill model" id="model">typesafe-ai/jev</div>
    <div class="pill" id="uptime">00:00:00</div>
  </header>

  <div class="grid">
    <div class="card main">
      <div class="pxrow">
        <div>
          <div class="price" id="price">—</div>
          <div class="sub" id="sub"></div>
        </div>
        <div class="action"><div class="verb" id="verb">Waiting</div><div class="meta" id="verbMeta">first block…</div></div>
      </div>
      <div class="statebox" id="statebox"><span class="lbl">what Jev saw</span></div>
      <div class="chart" id="chart"><div class="wait">connecting to Firstock…</div></div>
      <div>
        <div class="dots" id="dots"></div>
        <div class="foot"><span>one dot per decision · <span class="g">buy</span> · <span class="r">sell</span> · <span class="a">late</span> · ◆ = trade filled</span><span id="blockNote"></span></div>
      </div>
    </div>

    <div class="side">
      <div class="card pad">
        <div class="eyebrow">Jev's latest call</div>
        <div class="big"><b id="bigSide">—</b><span id="bigConf"></span></div>
        <div class="brainline" id="brainLine" style="display:none"></div>
        <div class="bars">
          <span>buy</span><div class="bar"><i id="barBuy" style="width:0;background:var(--good)"></i></div><span class="v" id="pBuy">–</span>
          <span>sell</span><div class="bar"><i id="barSell" style="width:0;background:var(--bad)"></i></div><span class="v" id="pSell">–</span>
        </div>
      </div>
      <div class="card pad moneycard">
        <div class="eyebrow" id="moneyTitle">Paper account · ₹1,00,000 position</div>
        <div class="money">
          <span class="k" id="balLabel">Paper balance</span><span class="v net" id="mBal">₹1,00,000.00</span>
          <hr>
          <span class="k">Before charges</span><span class="v" id="mGross">–</span>
          <span class="k">Charges paid <span class="d" id="mTrades"></span></span><span class="v" id="mFees">–</span>
          <hr>
          <span class="k">After charges</span><span class="v" id="mNet">–</span>
          <span class="k">Jev calls → trades</span><span class="v" id="mRatio">–</span>
          <span class="k">Direction right</span><span class="v" id="mHit">–</span>
        </div>
        <div class="spark" id="spark"></div>
      </div>
      <div class="card feed">
        <div class="eyebrow">Feed · every Jev call</div>
        <div class="tbl"><table><thead><tr><th>#</th><th>call</th><th>conf</th><th class="r">ms</th><th class="r">action</th></tr></thead><tbody id="feed"></tbody></table></div>
      </div>
    </div>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);
const WINDOW_S = 60;
let S = null, ticks = [], lastPx = null, lastSpr = "–", seenBlocks = new Set();

const pad2 = (n) => String(n).padStart(2, "0");
const IN = (v, d = 2) => v.toLocaleString("en-IN", {minimumFractionDigits: d, maximumFractionDigits: d});
function fmtPx(p) { return IN(p, p >= 10 ? 2 : 3); }
const inr = (v) => (v >= 0 ? "+₹" : "−₹") + IN(Math.abs(v));
function colorFor(d) { return d.status === "ok" ? (d.side === "buy" ? "var(--good)" : "var(--bad)") : "var(--late)"; }
function niceTicks(lo, hi, k) {
  const span = hi - lo || 1; let step = Math.pow(10, Math.floor(Math.log10(span / k)));
  for (const m of [1, 2, 5, 10]) { if (span / (step * m) <= k) { step *= m; break; } }
  const out = []; for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10)); return out;
}

// ---- live price: Firstock's best bid/ask, relayed by the bot (the browser never sees your session) -------------
function onQuote(p) {
  const [, mid, bp, ap] = p;  // microprice: the size-weighted fair price, moves on every book change
  const el = $("price");
  if (lastPx !== null && Math.abs(mid - lastPx) > mid * 1e-7) { el.className = "price " + (mid > lastPx ? "up" : "down"); clearTimeout(el._t); el._t = setTimeout(() => el.className = "price", 250); }
  lastPx = mid; el.textContent = fmtPx(mid);
  lastSpr = (1e4 * (ap - bp) / mid).toFixed(2) + " bps";
  if ($("spr")) $("spr").textContent = lastSpr;
}

async function poll() {
  try {
    const r = await fetch("/results/loop.json?_=" + Date.now(), {cache: "no-store"});
    if (!r.ok) return;
    S = await r.json();
    ticks = S.ticks || [];
    if (ticks.length) onQuote(ticks.at(-1));
    else $("chart").innerHTML = `<div class="wait">${S.note || "connecting to Firstock…"}</div>`;
    renderData();
  } catch (e) {}
}

const CLEAN = new URLSearchParams(location.search).has("clean");
if (CLEAN) document.body.classList.add("clean");

const answered = () => S.decisions.filter((d) => d.status === "ok" || d.status === "late");

function renderData() {
  const c = S.counts, j = S.book;
  const up = Math.floor(((S.status === "done" ? S.updated : Date.now() / 1000) - S.started));
  $("uptime").textContent = `uptime ${pad2(Math.floor(up / 3600))}:${pad2(Math.floor(up / 60) % 60)}:${pad2(up % 60)}`;
  $("mkt").textContent = S.venue_label || `${S.symbol} · NSE · Firstock`;
  $("model").textContent = S.model;
  $("runPill").className = "pill" + (S.status === "done" ? " done" : "");
  $("runText").textContent = S.status === "done" ? (S.note || "run complete") : (S.mode_label || "paper mode");
  $("stats").innerHTML = `<span>calls <b>${S.blocks.toLocaleString()}</b></span><span>last <b>${S.last_ms ?? "–"} ms</b></span>` +
    `<span>avg <b>${S.avg_ms ?? "–"} ms</b></span><span>pace <b>${S.rate_per_s.toFixed(1)}/s</b></span><span>trades <b>${j.trades}</b></span>` +
    `<span>late <b>${c.late}</b></span><span>throttled <b>${c.throttled}</b></span>`;
  $("blockNote").textContent = `your strategy: ${S.strategy_note} · ${S.execution === "limit" ? "limit orders" : "market orders"}` +
    (S.note ? ` · ${S.note}` : ` · ${S.minutes_to_close} min to the close`);

  const d = answered().at(-1), fill = S.fills.at(-1), nowS = Date.now() / 1000;
  if (fill && nowS - fill.t < 3) {
    $("verb").textContent = fill.side === "buy" ? "Bought" : "Sold"; $("verb").style.color = fill.side === "buy" ? "var(--good)" : "var(--bad)";
    $("verbMeta").textContent = `${fill.kind} fill @ ${fmtPx(fill.px)}${fill.wait_s ? ` · rested ${fill.wait_s}s` : ""}`;
  } else if (d && d.side) {
    $("verb").textContent = d.side === "buy" ? "BUY" : "SELL"; $("verb").style.color = d.side === "buy" ? "var(--good)" : "var(--bad)";
    $("verbMeta").textContent = `Jev · ${Math.round(100 * d.conf)}% · ${d.ms} ms`;
  }
  if (d) {
    const last = S.decisions.slice().reverse().find((x) => x.side);
    if (last) {
      const pb = last.side === "buy" ? last.conf : 1 - last.conf;
      $("bigSide").textContent = last.side.toUpperCase(); $("bigSide").style.color = last.side === "buy" ? "var(--good)" : "var(--bad)";
      $("bigConf").textContent = Math.round(100 * last.conf) + "%";
      $("barBuy").style.width = (100 * pb) + "%"; $("barSell").style.width = (100 * (1 - pb)) + "%";
      $("pBuy").textContent = Math.round(100 * pb) + "%"; $("pSell").textContent = Math.round(100 * (1 - pb)) + "%";
    }
    const st = d.state || {};
    const lab = {spread_bps: "spread", microprice_vs_mid_bps: "micro", top_of_book_imbalance: "imb", depth5_imbalance: "depth5",
      aggressor_buy_share_5s: "agg buy 5s", aggressor_buy_share_30s: "agg buy 30s", trades_last_5s: "trades/5s",
      return_5s_bps: "ret 5s", return_30s_bps: "ret 30s", tick_volatility_60s_bps: "vol 60s"};
    $("statebox").innerHTML = `<span class="lbl">what Jev saw · ${Object.keys(st).length} fields</span>` +
      Object.entries(lab).filter(([k]) => k in st).map(([k, l]) => `<span>${l} <b>${st[k]}</b></span>`).join("");
  }
  const pos = j.pos > 0 ? `<b class="g">LONG ${Math.abs(j.qty)} sh</b>` : j.pos < 0 ? `<b class="r">SHORT ${Math.abs(j.qty)} sh</b>` : `<b>FLAT</b>`;
  const working = S.order ? `<span>limit ${(S.order.buying ?? S.order.target > 0) ? "buy" : "sell"} <b>${fmtPx(S.order.px)}</b> working</span>` : "";
  $("sub").innerHTML = `<span>${pos}</span>${working}<span class="pnl">balance <b class="${j.net > 0 ? "g" : ""}">₹${IN(S.notional + j.net)}</b></span><span>spread <b id="spr">${lastSpr}</b></span>`;

  const acct = S.mode === "live" ? "Firstock LIVE account" : "Paper account";
  $("balLabel").textContent = S.mode === "live" ? `Today (from ₹${IN(S.notional, 0)})` : "Paper balance";
  $("moneyTitle").textContent = `${acct} · ₹${IN(S.notional, 0)} position · ${S.execution === "limit" ? "limit orders" : "market orders + spread"} · charges ≈ ${S.round_trip_bps} bps a round trip`;
  const tone = (v) => (v > 0 ? "g" : "");  // gains in green, everything else neutral
  $("mBal").textContent = "₹" + IN(S.notional + j.net);
  $("mBal").className = "v net " + tone(j.net);
  $("mGross").textContent = inr(j.gross); $("mGross").className = "v " + tone(j.gross);
  $("mFees").textContent = "−₹" + IN(j.fees); $("mTrades").textContent = `(${j.trades} trades)`;
  $("mNet").textContent = inr(j.net); $("mNet").className = "v " + tone(j.net);
  $("mRatio").textContent = `${S.blocks} → ${j.trades}`;
  $("mHit").textContent = S.scored ? `${Math.round(100 * S.hits / S.scored)}% of ${S.scored}` : "–";
  if (S.brain) {
    const b = S.brain, ago = b.t ? Math.round((Date.now() / 1000 - b.t) / 60) + " min ago" : "thinking…";
    $("brainLine").style.display = "block";
    $("brainLine").innerHTML = `<b>Claude's bias: ${(b.bias || "—").toUpperCase()}</b>${b.confidence != null ? ` · ${Math.round(100 * b.confidence)}%` : ""} · ${ago}<br>${b.reason || ""}`;
  }
  renderSpark(); renderDots(); renderFeed();
}

function renderSpark() {
  const el = $("spark"), j = S.book.equity;
  if (j.length < 2) { el.innerHTML = ""; return; }
  const W = el.clientWidth, H = el.clientHeight, all = j.flatMap((p) => [p[1], p[2]]).concat([0]);
  const lo = Math.min(...all), hi = Math.max(...all), t0 = j[0][0], t1 = j.at(-1)[0];
  const X = (t) => (t - t0) / Math.max(1, t1 - t0) * (W - 80), Y = (v) => 4 + (hi - v) / ((hi - lo) || 1) * (H - 8);
  const line = (pts, i) => pts.map((p, k) => `${k ? "L" : "M"}${X(p[0]).toFixed(1)},${Y(p[i]).toFixed(1)}`).join("");
  const yb = Y(j.at(-1)[1]), ya = Y(j.at(-1)[2]), sep = Math.abs(yb - ya) < 12 ? (ya >= yb ? 6 : -6) : 0;
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}"><line x1="0" x2="${W - 80}" y1="${Y(0)}" y2="${Y(0)}" stroke="#2e3949" stroke-dasharray="3 3"/>` +
    `<path d="${line(j, 1)}" fill="none" stroke="var(--jev)" stroke-width="1.5" stroke-dasharray="4 3" opacity=".6"/>` +
    `<path d="${line(j, 2)}" fill="none" stroke="var(--jev)" stroke-width="2.6"/>` +
    `<text x="${W - 74}" y="${yb + 4 - sep}" style="fill:var(--muted);font:600 10.5px var(--mono)">before charges</text>` +
    `<text x="${W - 74}" y="${ya + 4 + sep}" style="fill:var(--jev);font:600 10.5px var(--mono)">after charges</text></svg>`;
}

function renderDots() {
  const el = $("dots"), n = Math.max(20, Math.floor(el.clientWidth / 10));
  el.innerHTML = answered().slice(-n).map((d) => `<i style="background:${colorFor(d)}"></i>`).join("") +
    (S.status === "running" ? `<i style="background:transparent;border:1.5px solid var(--jev);animation:pulse 1s infinite"></i>` : "");
}

function renderFeed() {
  const rows = answered().slice(-22).reverse();
  $("feed").innerHTML = rows.map((d, i) => {
    const fresh = !seenBlocks.has(d.block); seenBlocks.add(d.block);
    const cls = d.status !== "ok" ? "hold" : d.side;
    const side = d.side ? `<b class="${d.status === "ok" ? (d.side === "buy" ? "g" : "r") : "a"}">${d.side.toUpperCase()}</b>` : `<span class="a">—</span>`;
    const LABEL = {"hold · low conviction": "signal", "hold · limit order working": "order working", "hold · too soon to flip": "cooling down",
                   "hold · already long": "in position", "hold · already short": "in position", "hold · late": "late",
                   "hold · no new positions after 15:00": "after 15:00"};
    const act = LABEL[d.action] || d.action || d.status, trade = /^(limit|market)/.test(act);
    return `<tr class="${cls} ${fresh && i === 0 && seenBlocks.size > 1 ? "fresh" : ""}"><td>${d.block.toLocaleString()}</td><td>${side}</td>` +
      `<td>${d.conf != null ? d.conf.toFixed(2) : "–"}</td><td class="r">${d.ms ?? "–"}</td>` +
      `<td class="r ${trade ? "act-trade" : d.status === "ok" ? "act-hold" : "a"}">${act}</td></tr>`;
  }).join("");
}

function renderChart() {
  requestAnimationFrame(renderChart);
  const nowP = performance.now(); if (renderChart._t && nowP - renderChart._t < 40) return; renderChart._t = nowP;
  if (!S || ticks.length < 2) return;
  const el = $("chart"), W = el.clientWidth, H = el.clientHeight; if (W < 50 || H < 50) return;
  const l = 4, r = 100, t = 12, b = 20;
  const tMax = Date.now() / 1000;
  const tMin = Math.max(tMax - WINDOW_S, ticks[0][0]);
  const span = Math.max(5, tMax - tMin);
  const vis = ticks.filter((p) => p[0] >= tMin - 1);
  if (vis.length < 2) return;
  const decs = answered().filter((d) => d.t >= tMin && d.micro);
  const ys = vis.map((p) => p[1]).concat(decs.map((d) => d.micro), S.fills.filter((f) => f.t >= tMin).map((f) => f.px), S.order ? [S.order.px] : []);
  let lo = Math.min(...ys), hi = Math.max(...ys); const pad = (hi - lo) * 0.18 || hi * 0.0001; lo -= pad; hi += pad;
  const X = (tt) => Math.max(l, l + (tt - tMin) / span * (W - l - r)), Y = (v) => t + (hi - v) / (hi - lo) * (H - t - b);
  const clampY = (v) => Math.min(H - b, Math.max(t, Y(v)));
  let s = `<svg viewBox="0 0 ${W} ${H}"><defs><linearGradient id="f" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#8b7bff" stop-opacity=".28"/><stop offset="1" stop-color="#8b7bff" stop-opacity="0"/></linearGradient></defs>`;
  for (const v of niceTicks(lo, hi, 4)) s += `<line class="gl" x1="${l}" x2="${W - r}" y1="${Y(v)}" y2="${Y(v)}"/><text class="ax" x="${W - r + 8}" y="${Y(v) + 4}">${fmtPx(v)}</text>`;
  for (let k = 0; k <= 3; k++) { const tt = tMin + k * span / 3; s += `<text class="ax" x="${X(tt)}" y="${H - 4}" text-anchor="${k === 0 ? "start" : k === 3 ? "end" : "middle"}">${new Date(tt * 1000).toLocaleTimeString("en-IN", {hour12: false, timeZone: "Asia/Kolkata"})}</text>`; }
  // the live bid-ask band, clipped to the chart
  const top = vis.map((p) => `${X(p[0]).toFixed(1)},${clampY(p[3]).toFixed(1)}`), bot = vis.map((p) => `${X(p[0]).toFixed(1)},${clampY(p[2]).toFixed(1)}`).reverse();
  s += `<polygon points="${top.join(" ")} ${X(tMax)},${clampY(vis.at(-1)[3])} ${X(tMax)},${clampY(vis.at(-1)[2])} ${bot.join(" ")}" fill="rgba(139,123,255,.10)"/>`;
  // microprice: the price line
  const line = vis.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" ") + ` ${X(tMax)},${Y(vis.at(-1)[1])}`;
  s += `<polygon points="${X(vis[0][0])},${H - b} ${line} ${X(tMax)},${H - b}" fill="url(#f)"/><polyline points="${line}" fill="none" stroke="#e6ecf3" stroke-width="1.7" stroke-linejoin="round"/>`;
  const nowS = Date.now() / 1000;
  for (const d of decs) {
    const cx = X(d.t), cy = Y(d.micro), age = nowS - d.t, col = colorFor(d);
    if (age < 0.9) { const k = age / 0.9; s += `<circle cx="${cx}" cy="${cy}" r="${5 + 18 * k}" fill="none" stroke="${col}" stroke-width="2" opacity="${(1 - k).toFixed(2)}"/>`; }
    s += `<circle cx="${cx}" cy="${cy}" r="4.6" fill="${col}" stroke="var(--bg)" stroke-width="1.5"/>`;
  }
  for (const f of S.fills.filter((f) => f.t >= tMin)) {
    const cx = X(f.t), cy = Y(f.px), col = f.side === "buy" ? "var(--good)" : "var(--bad)", age = nowS - f.t;
    if (age < 1.5) { const k = age / 1.5; s += `<circle cx="${cx}" cy="${cy}" r="${8 + 30 * k}" fill="none" stroke="${col}" stroke-width="2.5" opacity="${(1 - k).toFixed(2)}"/>`; }
    s += `<rect x="${cx - 7}" y="${cy - 7}" width="14" height="14" transform="rotate(45 ${cx} ${cy})" fill="${col}" stroke="#fff" stroke-width="1.8"/>` +
         `<text x="${cx}" y="${cy + (f.side === "buy" ? 24 : -15)}" text-anchor="middle" style="fill:${col};font:700 10.5px var(--mono);paint-order:stroke;stroke:var(--bg);stroke-width:4px">${f.side === "buy" ? "BOUGHT" : "SOLD"}</text>`;
  }
  if (S.order) {
    const oy = Y(S.order.px), col = (S.order.buying ?? S.order.target > 0) ? "var(--good)" : "var(--bad)";
    s += `<line x1="${X(S.order.t)}" x2="${W - r}" y1="${oy}" y2="${oy}" stroke="${col}" stroke-width="1.5" stroke-dasharray="6 4"/>` +
         `<text x="${W - r - 6}" y="${oy - 6}" text-anchor="end" style="fill:${col};font:600 10.5px var(--mono)">limit ${(S.order.buying ?? S.order.target > 0) ? "buy" : "sell"} ${fmtPx(S.order.px)}</text>`;
  }
  const last = vis.at(-1)[1], ly = Y(last);
  s += `<circle cx="${X(tMax)}" cy="${ly}" r="10" fill="#fff" opacity=".12"/><circle cx="${X(tMax)}" cy="${ly}" r="4" fill="#fff"/>` +
       `<rect x="${W - r + 2}" y="${ly - 11}" width="${r - 4}" height="22" rx="6" fill="#fff"/><text x="${W - r + 9}" y="${ly + 4}" style="fill:#06080c;font:700 11.5px var(--mono)">${fmtPx(last)}</text>`;
  el.innerHTML = s + "</svg>";
}

setInterval(poll, 250); poll(); requestAnimationFrame(renderChart);
setInterval(() => S && renderData(), 1000);
</script>
</body>
</html>
````

### `jev-starter/dashboard/newsroom.html`

````html
<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jev Newsroom</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#06080c;--bg2:#0c1016;--panel:#0e131a;--line:#1a222d;--line2:#253041;--fg:#e9eef4;--muted:#8a95a5;--dim:#586272;
--jev:#8b7bff;--good:#3fd68a;--bad:#ff5d6c;--amber:#f5b53d;--mono:"JetBrains Mono",ui-monospace,monospace}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;color:var(--fg);font:14px/1.45 Inter,-apple-system,BlinkMacSystemFont,sans-serif;-webkit-font-smoothing:antialiased;
background:radial-gradient(1000px 520px at 90% -15%,rgba(139,123,255,.18),transparent 60%),radial-gradient(900px 500px at -10% 115%,rgba(245,181,61,.05),transparent 60%),var(--bg)}
.app{height:100vh;min-height:680px;display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:12px;padding:14px 18px 12px;max-width:1760px;margin:0 auto}
header{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{font:800 23px/1 Inter;letter-spacing:-.025em}
.brand em{font-style:normal;background:linear-gradient(95deg,var(--jev),#d6ccff);-webkit-background-clip:text;background-clip:text;color:transparent}
.spacer{flex:1}
.pill{font:500 11.5px var(--mono);padding:6px 10px;border-radius:999px;border:1px solid var(--line2);color:var(--muted);background:rgba(12,16,22,.7);display:flex;align-items:center;gap:7px}
.pill.model{color:#cfc7ff;border-color:rgba(139,123,255,.45);background:rgba(139,123,255,.12)}
.pill.replay{color:var(--amber);border-color:rgba(245,181,61,.4);background:rgba(245,181,61,.08)}
.live{width:7px;height:7px;border-radius:50%;background:var(--amber);box-shadow:0 0 10px var(--amber);animation:pulse 1.3s infinite}
@keyframes pulse{50%{opacity:.35}}
.progress{width:180px;height:6px;border-radius:99px;background:var(--line);overflow:hidden}
.progress i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--jev),#c7bbff);transition:width .5s}
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);gap:12px;min-height:0}
.card{background:linear-gradient(180deg,rgba(14,19,26,.95),rgba(12,16,22,.95));border:1px solid var(--line);border-radius:18px;min-height:0;overflow:hidden}
.eyebrow{font:600 10.5px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--dim)}
.wire{display:flex;flex-direction:column}
.wire .eyebrow{padding:14px 16px 10px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between}
.list{flex:1;min-height:0;overflow:hidden;padding:6px 8px}
.item{padding:10px 10px;border-radius:12px;border:1px solid transparent;margin-bottom:4px;transition:background .4s,border-color .4s}
.item.now{background:rgba(139,123,255,.09);border-color:rgba(139,123,255,.45)}
.item.enter{animation:enter .6s ease-out}
@keyframes enter{from{transform:translateY(-10px);opacity:0}}
.meta{display:flex;gap:10px;align-items:center;font:11px var(--mono);color:var(--dim);margin-bottom:4px}
.src{color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.hl{font-size:14px;line-height:1.35;color:var(--fg)}
.item:not(.now) .hl{color:#b9c2cd}
.tags{display:flex;gap:6px;margin-top:7px;flex-wrap:wrap;align-items:center}
.chip{font:700 10.5px var(--mono);letter-spacing:.06em;padding:3px 7px;border-radius:6px;background:var(--line);color:var(--muted)}
.chip.coin{color:#cfc7ff;background:rgba(139,123,255,.16)}
.chip.bull{color:var(--good);background:rgba(63,214,138,.12)} .chip.bear{color:var(--bad);background:rgba(255,93,108,.12)}
.chip.trade{color:#06080c;background:var(--fg)}
.imp{display:inline-flex;gap:3px} .imp i{width:7px;height:7px;border-radius:2px;background:var(--line2)} .imp i.on{background:var(--amber)}
.reading{font:11px var(--mono);color:var(--jev)} .reading::after{content:"▍";animation:pulse .8s infinite}
.right{display:grid;grid-template-rows:auto minmax(0,1fr);gap:12px;min-height:0}
.read{padding:16px 18px}
.readhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.lat{font:600 12px var(--mono);color:var(--jev);padding:4px 9px;border-radius:999px;background:rgba(139,123,255,.12)}
.big{font:700 22px/1.3 Inter;letter-spacing:-.015em;min-height:58px}
.big .cursor{display:inline-block;width:10px;height:22px;background:var(--jev);vertical-align:-3px;margin-left:2px;animation:pulse .8s infinite}
.qs{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:18px;margin-top:14px}
.q h4{margin:0 0 8px;font:600 11px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--dim)}
.bars{display:grid;grid-template-columns:auto 1fr 36px;gap:6px 8px;align-items:center;font:11.5px var(--mono);color:var(--muted)}
.bar{height:8px;border-radius:99px;background:var(--line);overflow:hidden}
.bar i{display:block;height:100%;border-radius:99px;transition:width .45s ease}
.bars .v{text-align:right;color:var(--fg)} .bars .pick{color:var(--fg);font-weight:700}
.meter{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-top:2px}
.meter div{height:26px;border-radius:6px;background:var(--line);display:grid;place-items:center;font:600 10px var(--mono);color:var(--dim);transition:background .4s,color .4s}
.meter div.on{background:rgba(245,181,61,.25);color:var(--amber)} .meter div.top{background:var(--amber);color:#06080c}
.decision{margin-top:14px;padding:11px 14px;border-radius:12px;font:700 15px var(--mono);letter-spacing:.02em;display:flex;justify-content:space-between;align-items:center;
background:var(--line);color:var(--muted);transition:background .3s,color .3s}
.decision.long{background:rgba(63,214,138,.14);color:var(--good);box-shadow:inset 0 0 0 1px rgba(63,214,138,.4)}
.decision.short{background:rgba(255,93,108,.14);color:var(--bad);box-shadow:inset 0 0 0 1px rgba(255,93,108,.4)}
.decision small{font:500 12px var(--mono);color:var(--muted)}
.next{display:flex;flex-direction:column;padding:14px 16px 10px}
.nexthead{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.verdict{font:800 13px var(--mono);letter-spacing:.1em;padding:5px 10px;border-radius:8px}
.verdict.good{color:#06080c;background:var(--good)} .verdict.bad{color:var(--fg);background:var(--line2)} .verdict.pass{color:var(--muted);background:var(--line)}
.chart{position:relative;flex:1;min-height:0}
.chart svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.ax{fill:var(--dim);font:10.5px var(--mono)} .gl{stroke:var(--line)}
.score{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.s{background:linear-gradient(180deg,var(--panel),var(--bg2));border:1px solid var(--line);border-radius:14px;padding:10px 14px}
.s span{display:block;font-size:11.5px;color:var(--muted)}
.s b{font:700 24px/1.2 var(--mono);letter-spacing:-.02em}
.g{color:var(--good)} .r{color:var(--bad)}
.wait{position:absolute;inset:0;display:grid;place-items:center;color:var(--dim);font:13px var(--mono)}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand"><em>Jev</em> Newsroom</div>
    <div class="pill replay"><span class="live"></span><span id="replayText">REPLAY · real headlines</span></div>
    <div class="spacer"></div>
    <div class="pill" id="count">0 / 0</div>
    <div class="progress"><i id="prog"></i></div>
    <div class="pill model" id="model">typesafe-ai/jev</div>
  </header>

  <div class="grid">
    <div class="card wire">
      <div class="eyebrow"><span>Newswire</span><span id="wireNote">economic times · moneycontrol · livemint · business standard</span></div>
      <div class="list" id="list"></div>
    </div>
    <div class="right">
      <div class="card read">
        <div class="readhead"><div class="eyebrow">Jev's read</div><div class="lat" id="lat">reading…</div></div>
        <div class="big" id="big"></div>
        <div class="qs">
          <div class="q"><h4>Which stock?</h4><div class="bars" id="qCoin"></div></div>
          <div class="q"><h4>Which way?</h4><div class="bars" id="qDir"></div></div>
          <div class="q"><h4>How big?</h4><div class="meter" id="qImp"></div><div class="bars" style="margin-top:8px"><span>score</span><span></span><span class="v" id="impVal">–</span></div></div>
        </div>
        <div class="decision" id="decision">waiting for the first headline…</div>
      </div>
      <div class="card next">
        <div class="nexthead"><div class="eyebrow" id="nextTitle">What the market did next</div><div id="verdict"></div></div>
        <div class="chart" id="chart"><div class="wait">the real price move appears once Jev has answered</div></div>
      </div>
    </div>
  </div>

  <div class="score">
    <div class="s"><span>Headlines read</span><b id="sRead">0</b></div>
    <div class="s"><span>Tagged to an asset</span><b id="sTag">0</b></div>
    <div class="s"><span>Worth trading (Notable+)</span><b id="sTrades">0</b></div>
    <div class="s"><span>Direction right</span><b id="sRight">–</b></div>
    <div class="s"><span id="sNetLabel">After costs, 60-min holds</span><b id="sNet">–</b></div>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);
const COINS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "whole_indian_market", "none"];
const COIN_LABEL = {whole_indian_market: "NIFTY", none: "none"};
const IMPACT = ["Noise", "Minor", "Notable", "Major"];
let S = null, seen = new Set(), typed = {key: null, n: 0};

const hhmm = (t) => new Date(t * 1000).toLocaleString("en-IN", {weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata"});
const sgn = (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);

async function poll() {
  try {
    const r = await fetch("/results/newsroom.json?_=" + Date.now(), {cache: "no-store"});
    if (r.ok) { S = await r.json(); render(); }
  } catch (e) {}
}

function tagsFor(it) {
  if (!it.answer) return it.error ? `<span class="chip">skipped</span>` : `<span class="reading">Jev reading</span>`;
  const dir = it.direction, imp = Math.round(it.impact);
  return (it.asset ? `<span class="chip coin">${it.asset}</span>` : `<span class="chip">nothing tradeable</span>`) +
    `<span class="chip ${dir === "bullish" ? "bull" : dir === "bearish" ? "bear" : ""}">${dir === "bullish" ? "▲ BULLISH" : dir === "bearish" ? "▼ BEARISH" : "NEUTRAL"}</span>` +
    `<span class="imp">${[0, 1, 2, 3].map((i) => `<i class="${i <= imp ? "on" : ""}"></i>`).join("")}</span>` +
    (it.trade ? `<span class="chip trade">TRADE</span>` : "");
}

function render() {
  const feed = S.feed, cur = feed.at(-1);
  $("count").textContent = `${S.index} / ${S.total}`;
  $("prog").style.width = (100 * S.index / Math.max(1, S.total)) + "%";
  $("model").textContent = S.model;
  $("replayText").textContent = `REPLAY${S.round > 1 ? " · round " + S.round : ""} · last ${S.hours}h of real headlines · Jev answers live`;

  $("list").innerHTML = feed.slice(-9).reverse().map((it, i) => {
    const key = it.headline, fresh = !seen.has(key); seen.add(key);
    return `<div class="item ${i === 0 ? "now" : ""} ${fresh ? "enter" : ""}"><div class="meta"><span>${hhmm(it.published)}</span><span class="src">${it.source}</span></div>` +
      `<div class="hl">${it.headline}</div><div class="tags">${tagsFor(it)}</div></div>`;
  }).join("");

  const sc = S.score;
  $("sRead").textContent = sc.read; $("sTag").textContent = sc.tagged; $("sTrades").textContent = sc.trades;
  $("sRight").textContent = sc.trades ? `${sc.right} of ${sc.trades}` : "–";
  $("sNet").textContent = sc.trades ? sgn(sc.net_bps, 0) + " bps" : "–";
  $("sNetLabel").textContent = `After costs (${S.cost_bps} bps each), 60-min holds`;
  $("sNet").className = sc.net_bps > 0 ? "g" : "";
  if (cur) renderRead(cur);
}

function bars(el, opts, probs, pick, colour) {
  el.innerHTML = opts.map((o) => {
    const p = probs ? probs[o] || 0 : 0;
    return `<span class="${o === pick ? "pick" : ""}">${COIN_LABEL[o] || o}</span><div class="bar"><i style="width:${(100 * p).toFixed(1)}%;background:${colour(o)}"></i></div><span class="v">${probs ? Math.round(100 * p) + "%" : ""}</span>`;
  }).join("");
}

function renderRead(it) {
  // type the headline out like it's coming off the wire
  if (typed.key !== it.headline) { typed = {key: it.headline, n: 0}; }
  typed.n = Math.min(it.headline.length, typed.n + 6);
  $("big").innerHTML = it.headline.slice(0, typed.n) + (typed.n < it.headline.length || !it.answer ? `<span class="cursor"></span>` : "");
  const a = it.answer;
  $("lat").textContent = a ? `answered in ${it.ms} ms` : it.error ? "skipped" : "reading…";
  bars($("qCoin"), COINS, a && a.asset.probs, a && a.asset.choice, () => "var(--jev)");
  bars($("qDir"), ["bullish", "bearish", "neutral"], a && a.direction.probs, a && a.direction.choice,
       (o) => o === "bullish" ? "var(--good)" : o === "bearish" ? "var(--bad)" : "var(--dim)");
  const imp = a ? a.impact.score : -1;
  $("qImp").innerHTML = IMPACT.map((l, i) => `<div class="${a && i <= Math.round(imp) ? (i === Math.round(imp) ? "top" : "on") : ""}">${l}</div>`).join("");
  $("impVal").textContent = a ? imp.toFixed(2) : "–";

  const d = $("decision");
  if (!a) { d.className = "decision"; d.innerHTML = it.error ? "skipped · Jev didn't answer" : "Jev is reading the headline…"; }
  else if (it.trade) {
    d.className = "decision " + (it.side > 0 ? "long" : "short");
    d.innerHTML = `<span>TRADE · ${it.side > 0 ? "LONG" : "SHORT"} ${it.asset}</span><small>1 min after the news · hold ${S.after_min} min (or to the close)</small>`;
  } else {
    const why = !it.asset ? "nothing tradeable" : it.direction === "neutral" ? "no clear direction" : "not big enough to trade";
    d.className = "decision"; d.innerHTML = `<span>NO TRADE · ${why}</span><small>impact ${IMPACT[Math.round(it.impact)]}</small>`;
  }
  renderChart(it);
}

function renderChart(it) {
  const el = $("chart"), v = $("verdict");
  if (!it.answer) { el.innerHTML = `<div class="wait">waiting for Jev…</div>`; v.innerHTML = ""; return; }
  const name = it.asset || "NIFTY", path = (it.paths || {})[name];
  $("nextTitle").textContent = `What ${name} did next · NSE price, ${S.after_min} min after the headline`;
  if (!path || path.length < 2) { el.innerHTML = `<div class="wait">NSE was closed when this came out, so there's no price move to show</div>`; v.innerHTML = ""; return; }
  const W = el.clientWidth, H = el.clientHeight; if (W < 50 || H < 50) return;
  const l = 48, r = 70, t = 14, b = 22;
  const reveal = Math.min(1, (Date.now() / 1000 - it.answered) / 2.2);
  const lastMin = -S.before_min + reveal * (S.after_min + S.before_min);
  const shown = path.filter((p) => p[0] <= lastMin);
  const vals = path.map((p) => p[1]).concat([0]);
  let lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo) * 0.15 || 5; lo -= pad; hi += pad;
  const X = (m) => l + (m + S.before_min) / (S.after_min + S.before_min) * (W - l - r), Y = (bp) => t + (hi - bp) / (hi - lo) * (H - t - b);
  let s = `<svg viewBox="0 0 ${W} ${H}"><defs><linearGradient id="g" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#8b7bff" stop-opacity=".25"/><stop offset="1" stop-color="#8b7bff" stop-opacity="0"/></linearGradient></defs>`;
  const step = hi - lo > 80 ? 25 : hi - lo > 30 ? 10 : 5;
  for (let g = Math.ceil(lo / step) * step; g <= hi; g += step)
    s += `<line class="${g === 0 ? "gl zero" : "gl"}" x1="${l}" x2="${W - r}" y1="${Y(g)}" y2="${Y(g)}" ${g === 0 ? 'stroke="#3a4556"' : ""}/><text class="ax" x="${l - 8}" y="${Y(g) + 4}" text-anchor="end">${g > 0 ? "+" : ""}${g}</text>`;
  for (const m of [-10, 0, 15, 30, 45, 60]) s += `<text class="ax" x="${X(m)}" y="${H - 5}" text-anchor="middle">${m === 0 ? "news" : (m > 0 ? "+" : "") + m + "m"}</text>`;
  if (it.trade) s += `<rect x="${X(0)}" y="${t}" width="${X(S.after_min) - X(0)}" height="${H - t - b}" fill="${it.side > 0 ? "rgba(63,214,138,.05)" : "rgba(255,93,108,.05)"}"/>`;
  s += `<line x1="${X(0)}" x2="${X(0)}" y1="${t}" y2="${H - b}" stroke="var(--jev)" stroke-width="1.5" stroke-dasharray="4 4"/>`;
  if (shown.length > 1) {
    const pts = shown.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" ");
    s += `<polygon points="${X(shown[0][0])},${H - b} ${pts} ${X(shown.at(-1)[0])},${H - b}" fill="url(#g)"/><polyline points="${pts}" fill="none" stroke="#e6ecf3" stroke-width="2" stroke-linejoin="round"/>`;
    const e = shown.at(-1);
    s += `<circle cx="${X(e[0])}" cy="${Y(e[1])}" r="4.5" fill="#fff"/><text x="${X(e[0]) + 9}" y="${Y(e[1]) + 4}" style="fill:var(--fg);font:700 12px var(--mono);paint-order:stroke;stroke:var(--bg);stroke-width:4px">${sgn(e[1])} bps</text>`;
  }
  el.innerHTML = s + "</svg>";
  if (reveal < 1) { v.innerHTML = ""; return; }
  const move = path.find((p) => p[0] === S.after_min)?.[1] ?? path.at(-1)[1];
  if (it.trade) {
    const right = it.side * move > 0;
    v.innerHTML = `<span class="verdict ${right ? "good" : "bad"}">${right ? "RIGHT" : "WRONG"} · ${sgn(it.net_bps ?? move)} bps after costs</span>`;
  } else {
    v.innerHTML = `<span class="verdict pass">JEV PASSED · move was ${sgn(move)} bps</span>`;
  }
}

setInterval(poll, 250); poll();
setInterval(() => S && S.feed.length && renderRead(S.feed.at(-1)), 60);
</script>
</body>
</html>
````
