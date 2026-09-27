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
| **News check** (on) | Before every buy it looks for serious bad news about the company (fraud, a regulator's ban or probe, raids or arrests, default or insolvency, the auditor quitting, a short-seller report) and skips it. Red-flag words work with no key; with a Vercel key Jev reads each headline too. A flagged stock stays off the shopping list for 10 days. `uv run python -m jevlab news` shows the watch-list. |

## Setup

1. Install [uv](https://docs.astral.sh/uv/). `cp .env.example .env` and fill in your Firstock client ID, password, API key and vendor code.
2. `uv sync`, then `uv run python -m jevlab login` (the 6-digit code from your authenticator app), then `uv run python -m jevlab check`.
3. `uv run python -m jevlab backtest`, then `uv run python -m jevlab scan`.

SEBI's rules end every API session daily, so you log in once each trading day before 15:15 (on the server, send `/login 123456` to your Telegram bot).

## Costs

The bot itself costs ₹0 to ₹600 a month: a free Oracle Cloud server in India (or a small paid VPS with a fixed IP, about ₹400–600 including GST), Firstock's API, Telegram, and Jev's free tier. Trading costs are separate. Firstock charges no delivery brokerage, but each ₹5,000 round trip still pays about ₹29 in STT, stamp duty, exchange charges, the DP charge and GST (about 0.6%). A 5% winner on ₹5,000 is ₹250 before tax.

## Things to know

- **No stop-loss.** A falling stock gets averaged (up to 6 lots here), not sold. In a long bear market money gets stuck: `MAX_CAPITAL_INR` caps the total invested (₹2,00,000 = 40 lots by default).
- **The backtest is a best case.** It uses today's Nifty 50 for the whole period, so stocks that fell out of the index are missing.
- **Selling needs DDPI** (or eDIS) switched on in your Firstock account, or sell orders get rejected.
- **Live orders need a static IP** registered with Firstock (SEBI's rule), from a server in India.
- **The news check only stops buying.** It never sells a stock you hold on news (it tells you on Telegram instead), and no filter catches everything.
- **Tax:** gains on shares held under a year are short-term capital gains (20% at the time of writing). Ask a CA.

Real money needs `FIRSTOCK_MODE=live` **and** the exact phrase in `JEV_LIVE_CONFIRM`. Set those yourself, after weeks of paper results. Not financial advice.
