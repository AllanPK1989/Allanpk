# Risk register — RSI-Filtered Nifty Shop

**Opened:** 2026-08-31. Live document; every phase gate reviews it.

Likelihood and impact are High / Medium / Low. "Mitigation" means what is actually
built, not what is intended. An entry with no built mitigation says so.

---

## Data and correctness

### R-01 — NSE archive layout changes, or rate-limits the VPS
**L: High · I: High.** The historical bhavcopy path has already moved once
(`www1.nseindia.com` → `nsearchives.nseindia.com`). A layout change mid-download
leaves a partial dataset that silently looks complete.
**Mitigation:** raw bytes are cached before parsing, so a re-parse never re-downloads.
The downloader is resumable and idempotent per trading date. One fixture per era
(pre-2016 zip, post-2016 CSV) is committed so the parser is testable offline forever.

### R-02 — Point-in-time constituent table assembled wrongly
**L: High · I: Critical.** This is survivorship bias, the exact thing Forbidden rule 6
bans. It is also invisible: a wrong table produces a plausible, better backtest.
**Mitigation:** every add/drop cites its NSE press release in a `source` column. A test
asserts the reconstructed index has exactly 50 names on 20 randomly chosen historical
dates. A second test asserts no symbol appears with an entry date before its listing.

### R-03 — Corporate action ratios missing or wrong
**L: High · I: Critical.** A missed 1:5 split puts a −80% bar into the series. SMA(50)
and RSI(14) both corrupt, and the system trades confidently and wrongly forever.
**Mitigation:** unexplained-gap detector halts a symbol on any move beyond
`ops.corp_action_gap_halt_pct` (15%) not explained by a known action. The Phase 2
indicator validation gate blocks all further work until RSI(14) and SMA(50) match an
independent reference for 5+ symbols across 3 dates, as committed fixtures.

### R-04 — Firstock rate limits and error codes are undocumented to this project
**L: Certain · I: Medium.** `firstock.in` is denied by the build environment's egress
policy (403 on CONNECT), so the API docs cannot be read here.
**Mitigation:** none possible in code. Signatures are taken from the official SDK
source on GitHub, which is reachable. Rate limits and error-code semantics are
escalated to the account owner or confirmed on the VPS. **No signature is invented.**

### R-05 — 15:20 signal flips before the 15:30 close
**L: Certain · I: Medium.** Guaranteed to happen; the only question is how often. It
affects **exits as well as entries**, because the exit test also reads the provisional
close.
**Mitigation:** both the 15:20 value and the settled close are recorded per symbol per
day. A daily signal-drift metric covers entries and exits separately. No silent
post-close recompute.

---

## Execution and state

### R-06 — Lot ledger diverges from broker holdings
**L: Medium · I: Critical.** Exit decisions would then be made on fiction.
**Mitigation:** morning reconciliation runs before any exit decision and aborts the run
on mismatch. The broker is the source of truth; the ledger is authoritative only for
which lot an exit closes.

### R-07 — T+1 settlement makes a lot unsellable
**L: Certain · I: Low.** A lot bought today cannot be sold today even if it hits +5%.
**Mitigation:** each lot carries a `sellable_from` date; the exit path verifies settled,
sellable demat quantity before placing.

### R-08 — Session dies mid-run, leaving orphaned or duplicated orders
**L: Medium · I: High.**
**Mitigation:** order state machine with an idempotency key per intent, reconciled
against the orderbook during the run. Crash-resume is an acceptance criterion, tested
by killing the job at each state transition.

### R-09 — Static egress IP changes
**L: Low · I: Critical.** A regulatory breach, not merely a failed order.
**Mitigation:** startup preflight resolves the public egress IP and refuses to start on
mismatch with `EXPECTED_EGRESS_IP`; re-checked before each run.

---

## Strategy and capital

### R-10 — Capital exhausted mid-decline
**L: High · I: High.** The strategy's failure mode is not losing, it is freezing with
all capital committed and nothing exiting.
**Mitigation:** the capital requirement model is reported beside every return figure,
never separately. KC-3 abandons the strategy above ₹8,00,000 peak deployed. R6 exists
but is OFF by default and must justify itself independently.

### R-11 — Backtest overfitted by iteration
**L: High · I: Critical.** A good backtest and a bad account.
**Mitigation:** kill criteria pre-registered and frozen at the first baseline run; a
single-look out-of-sample holdout; the sensitivity surface is reported even when it is
unflattering; parameter collapse under ±20% is stated plainly as noise, not signal.

### R-12 — Three strategy rules are unspecified
**L: Certain · I: High.** Index removal, cash shortfall, and exit partial fill.
**Mitigation:** encoded as `UNSPECIFIED` enum members. `assert_rules_resolved` raises,
so the system refuses to run rather than inventing a rule. Blocking for Phase 3.

### R-13 — Return on allocated capital looks poor by construction
**L: Certain · I: Low (to the account), High (to judgement).** At ₹10,00,000 allocated
and ~₹2,00,000 steady-state deployment, the book is ~80% idle in normal conditions, so
metric 1 lands near a fifth of return on deployed capital.
**Mitigation:** none needed — this is the honest number. Recorded here so it is not
mistaken for a bug in Phase 3, and so the temptation to quietly switch to
return-on-deployed is on the record as a temptation.

---

## Environment

### R-14 — Repository also hosts an unrelated 3D animation project
**L: Certain · I: Low.** Tooling and CI confusion.
**Mitigation:** `nifty-shop/` is self-contained with its own `pyproject.toml`, lockfile
and virtualenv. Nothing outside that directory is touched.

### R-15 — Secrets leak into logs or the repository
**L: Medium · I: Critical.**
**Mitigation:** `.env` is gitignored; `.env.example` names keys and carries no values,
enforced by a test. Tokens, keys and session IDs are never logged, including in traces.
