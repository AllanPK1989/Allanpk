# Runbook — completing Phase 1 and Phase 2

## Which machine runs what

| | Machine | Why |
|---|---|---|
| **Phase 1** (broker) | **The VPS only** | Orders may only originate from the static IP whitelisted with Firstock. Your laptop's IP is not that address, and the preflight will refuse to start. |
| **Phase 2** (data, fixtures) | **Any machine with internet** | NSE archives and TradingView have no IP restriction. A Windows laptop is fine. |

Neither can run in the build environment, where NSE, NSE Indices, TradingView and
Firstock are all blocked by egress policy.

Total time: Phase 1 is about 30 minutes. Phase 2 is a few hours, most of it waiting for
a download.

---

## One-time setup — Windows (PowerShell)

```powershell
cd $HOME
git clone https://github.com/AllanPK1989/Allanpk.git
cd Allanpk\nifty-shop

# install uv if you do not have it, then reopen PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

uv python install 3.12
uv sync
uv run pytest -m "not validation_gate"
```

If `git` is missing: `winget install --id Git.Git -e`, then reopen PowerShell.

## One-time setup — Linux VPS (bash)

```bash
cd ~
git clone https://github.com/AllanPK1989/Allanpk.git
cd Allanpk/nifty-shop
curl -LsSf https://astral.sh/uv/install.sh | sh     # if uv is not installed
uv python install 3.12
uv sync
uv run pytest -m "not validation_gate"
```

**Checkpoint (either platform):** `256 passed`. If not, stop and send me the output.

---

# Phase 1 — broker connectivity

## Step 1. Confirm the egress IP is the whitelisted one

```bash
curl -s https://checkip.amazonaws.com
```

Note the address. It must match the IP you registered with Firstock. If your VPS has
several interfaces, this is the one that matters — it is what the broker sees.

## Step 2. Create the credentials file

Linux:

```bash
cp .env.example .env && nano .env && chmod 600 .env
```

Windows:

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill in all seven values. `EXPECTED_EGRESS_IP` is the address from Step 1.
`FIRSTOCK_TOTP_SECRET` is the **base32 seed** from when you set up 2FA, not a six-digit
code — the system generates a fresh code per login, because the broker rejects a reused
one. Do not wrap values in quotes.

`.env` is gitignored. Never commit it.

## Step 3. Run the read-only smoke check

The same command on both platforms — `.env` is read automatically, so there is no
`source` step and nothing to export:

```
uv run python -m nifty_shop.smoke
```

This logs in, prints funds and holdings with secrets redacted, and logs out. **There is
no order-placing code in the repository**, so it cannot trade.

**Checkpoint — success looks like:**

```
preflight: egress IP 203.0.113.7 matches the whitelist
preflight: clock 2026-09-01 15:20:03 IST
session: logged in for IST day 2026-09-01
funds: { ... }
holdings: [ ... ]
session: logged out
```

**Phase 1 is then complete.** Send me the funds and holdings output (redacted is fine —
I need the *field names*, not the values) so I can write the domain mapping against real
responses instead of assumptions.

### If it refuses

| Message | Cause |
|---|---|
| `egress IP mismatch` | The VPS is leaving by a different address than you whitelisted. |
| `EXPECTED_EGRESS_IP is not configured` | Step 2 not done, or you are not in the `nifty-shop` directory. |
| `missing or blank environment variables` | It names exactly which ones. |
| `live mode refused` | You set `mode: live`. Leave it on paper. |
| `reported failure: ...` | The broker rejected it. Usually a stale TOTP or a wrong vendor code. |

---

# Phase 2 — data and the indicator gate

## Step 4. Test the download on a short range FIRST

Do not start an 18-year download before proving the layout works.

```bash
uv run python -m nifty_shop.download bhavcopy --start 2026-08-03 --end 2026-08-07
```

**Checkpoint:**

```
requesting 5 weekday sessions from 2026-08-03 to 2026-08-07
downloaded 5, already cached 0, absent (holidays) 0
layouts served: current
trading sessions found: 5
```

If instead everything comes back **absent**, the URL shape is wrong — send me the output
and I will fix it. If you get `UnknownBhavcopyLayoutError`, it will name the headers it
actually saw; send me those and one fixture fixes it.

Then try one old date, to prove the legacy zip layout too:

```bash
uv run python -m nifty_shop.download bhavcopy --start 2010-06-01 --end 2010-06-04
```

## Step 5. Download the history

Start with recent years. The full archive is large, and you do not need 2008 to turn the
gate green — you need it for Phase 4's stress windows.

```bash
uv run python -m nifty_shop.download bhavcopy --start 2023-01-01 --end 2026-08-31
```

It is **resumable and idempotent** — re-running skips what is already cached, so a
dropped connection costs nothing. Run it under `nohup` or `tmux` for long ranges.

## Step 6. Confirm a symbol's series came through

```bash
uv run python -m nifty_shop.download closes --symbol RELIANCE --as-of 2026-08-31
```

**Checkpoint:** at least 200 closes. That is the warm-up the gate requires.

## Step 7. Read the reference values off TradingView

Pick **5 symbols** and **3 dates** each (15 fixtures). Use liquid Nifty names —
RELIANCE, INFY, HDFCBANK, TCS, ITC are fine.

On each chart, set these **exactly**, or the comparison tells you nothing:

- Exchange **NSE**, interval **1D** (daily)
- **RSI**: length `14`, source `close`
- **MA**: type `SMA`, length `50`, source `close`
- Splits and bonuses adjusted (TradingView's default), **dividends NOT adjusted** —
  this project adjusts the same way, and a dividend-adjusted series will disagree for
  reasons that have nothing to do with correctness

Hover the exact date and write down both values to 2 decimals.

## Step 8. Build each fixture

One command per symbol/date. It pairs your reference numbers with the exact close
series this project computes from:

```bash
uv run python -m nifty_shop.download fixture --symbol RELIANCE --as-of 2026-01-15 --rsi 41.83 --sma 1290.44 --source "TradingView NSE:RELIANCE 1D, captured 2026-09-04"
```

(That is one line, so it works unchanged in PowerShell and bash. On Linux you can split
it with trailing backslashes; in PowerShell use backticks.)

```
```

Repeat for all 15. Each writes a JSON file into `tests/fixtures/reference/`.

## Step 9. Turn the gate green

```bash
uv run pytest -m validation_gate -v
```

**Checkpoint:** it passes. **Phase 2 is then complete** and Phase 3 is unblocked.

```bash
git add tests/fixtures/reference/
git commit -m "test(nifty-shop): add independent reference fixtures for the Phase 2 gate"
git push
```

### If it fails

The failure names every mismatch with both numbers:

```
RELIANCE 2026-01-15 RSI(14): expected 41.83, computed 38.02
```

Read it carefully before assuming the code is wrong. In rough order of likelihood:

1. **The chart settings did not match** — wrong length, wrong source, or dividend
   adjustment on. Re-check Step 7.
2. **Not enough history cached** — the fixture builder refuses under 200 bars, but a
   series starting only just above 200 has a slightly unsettled RSI. Download more.
3. **A corporate action is missing** from the cached series, so the closes genuinely
   differ from TradingView's. Run the gap detector on that symbol.
4. **The indicator code is wrong.** Possible, but it already agrees with an
   independent library (`ta`) to within 0.10 across every settled bar, so check 1–3
   first.

Send me the output either way.

---

## Separately: the constituent table

Not required for the Phase 2 gate, but required before Phase 3 produces a trustworthy
backtest. It is hand transcription from NSE Indices press releases — see
`docs/building-the-constituent-table.md`. Audit as you go:

```bash
uv run python -m nifty_shop.universe_audit
```

---

## Where this leaves the project

| | After this runbook |
|---|---|
| Phase 1 | Complete |
| Phase 2 | Complete |
| Phase 3 | Engine is already built and tested; it runs the moment data and the three rules land |

Still needed from you regardless of the above: **the three unspecified rules**
(index removal, cash shortfall, exit partial fill). The engine refuses to run without
them and will not invent one.
