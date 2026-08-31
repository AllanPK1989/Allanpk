# ADR-0001 — Backtest price and constituent history from free NSE archives

**Date:** 2026-08-31 · **Status:** Accepted

## Context

The validation protocol requires the longest available history with point-in-time
constituents, adjusted prices and a full cost model, plus named stress windows in 2008,
2011, 2013, March 2020 and 2022.

Firstock cannot supply this. It is a broker API: daily history depth is limited,
prices are unadjusted, and symbols that have since left the exchange are not queryable
at all. The stress windows need split- and bonus-adjusted bars for names that no longer
exist. Treating the broker as the historical data source would silently produce a
survivorship-biased backtest — the exact failure Forbidden rule 6 prohibits.

## Decision

Assemble the dataset from free NSE sources:

- **Prices:** daily bhavcopy archives, covering both the pre-2016 zip layout and the
  current CSV layout.
- **Corporate actions:** NSE equity corporate action files, parsed into ratio factors,
  with an unexplained-gap detector as a backstop for anything missed.
- **Constituents:** a hand-assembled dated add/drop table sourced from NSE Indices
  reconstitution press releases, with each row citing its source.
- **Calendar:** NSE trading holidays plus special sessions, cross-checked against the
  dates actually present in the bhavcopy archive.
- **Symbol changes:** the NSE symbol change master, because symbols rename over 18 years.

## Alternatives rejected

- **A paid vendor dataset.** Fastest and cleanest, but not chosen.
- **yfinance / NSEpy as a stopgap.** Quick, but the universe is survivorship-biased and
  the adjustments are unverified. It cannot satisfy Forbidden rules 3 or 6, so every
  number would have to be labelled provisional — which makes the whole protocol theatre.
- **Firstock history with a shortened window.** Cheapest, but it drops 2008, 2011 and
  2013 — and the regime that decides whether this strategy is viable is exactly the one
  that would be dropped.

## Consequences

- Phase 2 grows a data-acquisition sub-project with its own test suite. It is the
  critical path, not the broker client.
- The build environment's egress policy denies `nseindia.com` (403 on CONNECT), so
  **no NSE bytes can be fetched here.** The downloader is written and unit-tested
  against committed fixtures in this environment; the bulk historical pull runs on the
  VPS, which has unrestricted egress and the whitelisted static IP.
- The constituent table is the highest-risk artefact in the project (R-02) because a
  wrong one produces a better-looking backtest. It gets dedicated tests.
