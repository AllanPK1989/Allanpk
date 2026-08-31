# Pre-registered kill criteria — RSI-Filtered Nifty Shop

**Registered:** 2026-08-31 (Asia/Kolkata)
**Registered by:** Allan (account owner), on the record, before any backtest existed
**Status:** ACTIVE — binding on every result this project produces
**Strictness set chosen:** STRICT

---

## Why this file exists and how to verify it

This document was written **before a single line of strategy or backtest code was
written**, and before any performance number of any kind was produced. That claim is
falsifiable: `git log --follow` on this file gives its commit date, and no commit
containing a backtest result predates it. If you are reading this after results exist,
check that ordering first. If it does not hold, this file is worthless and every number
in this repo should be treated as curve-fitted.

Pre-registration is the only defence against the failure mode this whole project is
organised around: seeing a bad result and then discovering a reason why it does not
count.

---

## Fixed inputs

| Input | Value | Notes |
|---|---|---|
| Allocated capital `A` | **₹10,00,000** | Fixed for the entire evaluation. Never revised upward mid-test to avoid a KC-3 breach. Revising `A` upward after seeing a result is itself a breach of protocol. |
| Notional per lot | ₹5,000 | Per spec |
| Max trades/day | 2 | Per spec |
| Exit target | **+5% gross** | Measured on price, not net proceeds |
| Stop loss | None | Per spec — this is the reason these criteria exist |

---

## Definitions — precise, so that no result can be argued around later

Let a **lot** be one buy fill with its own entry price, quantity and date.

**Cost basis** of lot `i` = `qty_i x fill_avg_price_i + buy_side_charges_i`.

**Deployed capital** at session `t`:
`D(t) = sum of cost_basis_i over all lots open at the close of t`

**Peak capital deployed** = `max over all t of D(t)`. Cost basis, not market value —
this is the cash the account actually had to find.

**Book equity** at session `t`:
`E(t) = A + cumulative_realised_net_pnl(t) + cumulative_unrealised_net_pnl(t)`

where realised net P&L on a closed lot is
`qty x (exit_price - entry_price) - all_charges_both_sides`, and unrealised net P&L on
an open lot is `qty x (settled_close(t) - entry_price) - buy_side_charges`.
By construction `E(0) = A`. **Open lots are marked to market, never carried at cost.**

**Book drawdown** at `t`:
`DD(t) = (running_max_of_E_up_to_t - E(t)) / running_max_of_E_up_to_t`
Measured on the **settled daily close**, never the 15:20 provisional close.
**Max book drawdown** = `max over t of DD(t)`.

**Zero-exit stretch**: a counter over NSE trading sessions. It increments on any
session where at least one lot was open at the session start and zero lots were closed
during it. It resets to zero on any session where at least one lot closed, **or** where
no lots were open at the session start (nothing is frozen if nothing is held). The
**longest zero-exit stretch** is the maximum value the counter reaches.

**Tax basis**: all P&L above is **net of modelled transaction charges and gross of
income tax**. Post-tax figures are reported alongside but the criteria are evaluated
pre-tax, so that these thresholds measure the strategy rather than the tax code.

---

## The criteria

The strategy is **abandoned** if any one of the following is true. These are ORs, not a
scorecard. One breach is sufficient.

### KC-1 — Book drawdown
> **Max book drawdown, marked to market including open lots, worse than 20.0%.**

On `A` = ₹10,00,000 this is a peak-to-trough decline in book equity of **₹2,00,000**.

### KC-2 — Frozen capital
> **Longest zero-exit stretch beyond 40 NSE trading sessions.**

Roughly two calendar months in which the book takes in capital and returns none.

### KC-3 — Capital requirement
> **Peak capital deployed exceeds 80% of allocated capital, i.e. ₹8,00,000.**

At ₹5,000 per lot this is **160 concurrent open lots**.

---

## Scope of evaluation

1. Evaluated over the **full available history**, including every stress window.
2. **A breach confined to a single stress window is still a breach.** 2008 is not
   "unrepresentative"; it is the regime the spec itself names as the one that decides
   whether this strategy is viable.
3. Applies to the **baseline** and, independently, to **any R1–R8 variant proposed for
   live use**, over the same full history.
4. Applies to the **out-of-sample holdout** run as well. A clean full-history result
   plus a holdout breach is a breach.
5. Applies to **paper trading** and to **live**. A live breach stops the system; it does
   not start a tuning cycle.

---

## What a breach means

A breach means **stop**. Specifically, it does **not** license any of:

- retuning RSI band, target, SMA length or exit RSI until the breach disappears
- switching on a robustness module in order to rescue the baseline
- shortening the test window, or excluding the breaching period
- reclassifying the breaching period as anomalous, unrepresentative, or "a different market"
- raising `A` so that KC-3 stops binding

Enabling a robustness module produces a **different strategy**, which may be tested on
its own merits over the same full history and must clear all three criteria unaided.
The baseline's breach is recorded permanently in this repo and is never deleted,
restated, or averaged away.

---

## Reporting rule

**A breach is the first line of any report in which it occurs**, stated before any
return, CAGR, win rate or equity curve. Not a footnote, not an appendix, not a caveat
under the headline. If KC-1 trips, the report opens with "KC-1 BREACHED" and the
performance numbers come after.

---

## Amendment policy

Amendments are permitted **only before the first baseline backtest is executed**.

- Any amendment is a **separate, dated commit** with written rationale.
- The superseded text stays in this file, struck through. Nothing is silently rewritten.
- **After the first baseline run, this file is frozen.** Git history is the proof.

One amendment is already anticipated and pre-authorised: resolution of the three
missing strategy rules listed below may change how forced exits are realised, which
touches KC-1. That resolution must land before the first baseline run.

---

## Unresolved inputs that must be closed before the first baseline run

These are open questions, not defaults. The engine is built to **fail loudly** rather
than pick one silently.

1. **Lot held in a symbol that leaves the Nifty 50, is suspended, merges, or delists.**
   Exit at the event, or hold to the normal triggers? Fires roughly 50 times across
   18 years of index turnover.
2. **Insufficient cash at 15:20 when two candidates qualify.** Skip both, or take the
   top-ranked one only?
3. **Partial fill on the exit side.** Entry partials are specified in the spec; exit
   partials are not.

---

## Prediction recorded in advance

Recorded now so that it cannot later be presented as post-hoc explanation, and so that
being wrong is equally informative.

**I expect KC-1 and KC-3 to be breached, most likely in the FY2008-09 window.**

Reasoning: the base strategy has no cap on open lots (R6 is off by default). It buys up
to 2 lots per day whenever candidates exist, and exits require either +5% or RSI(14)
above 50 — both scarce in a sustained decline. A net accumulation of roughly one lot per
day over about 160 sessions reaches ₹8,00,000 of cost basis and trips KC-3. That same
₹8,00,000 held at an average of −25% is roughly ₹2,00,000 unrealised, which trips KC-1
on a ₹10,00,000 book at the same time.

**I expect KC-2 to be the least likely to bind**, because bear-market rallies produce
sporadic +5% exits that reset the counter. The book can therefore freeze economically
while never technically registering 40 consecutive exit-free sessions. This is a known
weakness of KC-2 as a measure, stated here in advance rather than discovered later.

One partial counterweight, also recorded in advance: the entry filter is a **band**
(RSI 25–35), not a threshold. In a violent decline RSI falls below 25 and candidates
drop out of the pool from the bottom, so the strategy stops buying near the lows. This
caps the capital requirement somewhat — and simultaneously means the strategy
systematically declines the best available prices. Both effects must be measured, not
assumed.

---

*Personal-use system, own account only. Not investment advice.*
