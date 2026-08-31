# Building the point-in-time Nifty 50 constituent table

**Status: not built.** `reference/nifty50-constituent-changes.csv` is empty on purpose.

This build environment's egress policy denies `niftyindices.com` (the publisher of the
index-maintenance releases), `nseindia.com`, `web.archive.org` and Wikipedia — all 403
on CONNECT. No press release could be read, so no row was written. Producing ~200 dated
rows from recollection, with citations that were never opened, would fabricate the one
artefact this project's risk register calls invisible when wrong (R-02): a bad
constituent table does not look broken, it looks like a *better* backtest.

What exists instead is the machinery that makes assembling it by hand safe, and an
arithmetic check that turns a typo into a test failure.

---

## Why the table is built backwards

Nobody has the founding constituent list to hand. Everybody can fetch today's. So the
table anchors on today's published membership and rewinds through dated changes:

- an `ADD` effective on date D means the symbol was **not** a member before D
- a `DROP` effective on D means it **was** a member before D

This direction buys an objective correctness check that requires no market knowledge:
**the Nifty 50 has exactly 50 members at every instant of its life.** If rewinding
produces 49 or 51 for any period, a change is missing, duplicated or mistyped. You do
not need to know which stocks *should* have been in the index — the arithmetic tells you
something is wrong, and names the two dates the missing row sits between.

---

## Procedure

### 1. Anchor on today's list

On the VPS:

```bash
curl -o current.csv https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv
```

Transcribe the `Symbol` column into `reference/nifty50-current.csv`, one per line, and
set the declaration line to the date you fetched it:

```
# as_of,2026-08-31
```

Any change dated after that is rejected: the rewind cannot start from a list that
predates the change it is undoing.

### 2. Collect the press releases

Index maintenance announcements come from **NSE Indices Ltd**, not NSE the exchange.
Archive the PDFs alongside the CSV so the citations stay checkable after the site
reorganises — it has moved before.

Two kinds of change exist and both must be captured:

- **Scheduled reviews.** Announced roughly a month ahead, effective on a stated date.
- **Ad-hoc changes.** Mergers, demergers, delistings and suspensions, which land
  outside the review schedule and are easy to miss precisely because nobody is looking
  for them on that date.

> **Verify the cadence rather than assuming it.** Semi-annual reviews effective around
> the end of March and September are a reasonable starting hypothesis for where to look,
> but the review frequency and the effective-date convention have changed over the
> index's life, and this could not be checked here. Do not use it as a substitute for
> reading the releases. The size check catches any period you miss regardless.

### 3. Fill in the CSV

One row per symbol per change, in `reference/nifty50-constituent-changes.csv`:

```
effective_from,symbol,action,source
2021-04-01,SOMENAME,DROP,NSE Indices PR 2021-03-05
2021-04-01,OTHERNAME,ADD,NSE Indices PR 2021-03-05
```

- `effective_from` is the date the change **took effect**, not the announcement date.
  Mixing these up shifts membership by about a month and is entirely invisible.
- `symbol` must be the NSE trading symbol **as it appeared in the bhavcopy on that
  date**, which is not necessarily today's symbol. Companies rename. Pull NSE's
  `symbolchange.csv` and use it when a name looks unfamiliar.
- `source` is mandatory and must name a specific release. The loader rejects a blank.

### 4. Audit until clean

```bash
uv run python -m nifty_shop.universe_audit
```

It checks, objectively:

| Check | What a failure means |
|---|---|
| Membership is exactly 50 for every period | A change is missing, duplicated or mistyped between the two dates it names |
| Every `ADD` is present in the membership being rewound | The change list and the current list disagree |
| No `DROP` restores a symbol already present | Same |
| No duplicate `(date, symbol, action)` rows | A release was transcribed twice |
| Every row cites a source | An unsourced row is an assertion, not data |
| No change dated after the current list's `as_of` | The anchor predates the change |

Wire the optional bhavcopy cross-check once price history is downloaded. It is the
strongest typo detector available, because it tests against data rather than memory: a
symbol named in a change must actually have a bar in the bhavcopy for that session. A
symbol that does not is a typo or a since-renamed name.

### 5. Declare how far back it is complete

Set `complete_from` to the earliest date you are confident every change is recorded.
Dates before it refuse rather than answering. This matters: the rewind will happily
produce a plausible membership for 1998 from a change list that only goes back to 2007,
and nothing about that output looks wrong.

---

## What this does not protect against

The size check verifies the count, not the identity. A table where two symbols were
swapped for each other on the same date passes every check here and is still wrong. The
bhavcopy cross-check narrows this, and spot-checking a handful of historical dates
against an independent source narrows it further, but there is no complete automated
defence. Treat the table as the highest-risk input in the project and review it as one.
