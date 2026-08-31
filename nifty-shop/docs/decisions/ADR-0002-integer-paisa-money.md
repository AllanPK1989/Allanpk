# ADR-0002 — Currency as integer paisa, never float

**Date:** 2026-08-31 · **Status:** Accepted

## Context

An acceptance criterion requires the cost model to reconcile to a real contract note
**to the paisa**. The economics are tight: a ₹5,000 position targeting 5% earns ₹250
gross, against roughly ₹27 of round-trip charges — about 11% of the target. Sub-rupee
components (₹0.75 stamp duty, ₹0.40 exchange and SEBI fees) are material at this size.

IEEE-754 binary floats cannot represent 0.05, 0.10 or 13.50 exactly. Accumulated over
hundreds of lots across an 18-year backtest, that error is small but unbounded, and it
makes exact reconciliation against a contract note impossible by construction.

## Decision

All currency is `Paisa`, a `NewType` over `int`. Conversion happens once at the
boundary via `rupees(str | int | Decimal)`, which quantises half-up at the paisa.
`rupees()` **raises `TypeError` on a float** rather than accepting it and rounding the
error away later.

Cost-model rates are stored in config as **strings**, not floats, so they enter
`Decimal` arithmetic without a binary round-trip.

## Alternatives rejected

- **`Decimal` throughout.** Correct, but carries context and rounding-mode state, and
  equality is subtle (`Decimal("1.0") != Decimal("1.00")` under `compare_total`).
  Integers make ledger equality and SQLite storage trivial.
- **Floats with rounding at the reporting boundary.** This is the default mistake. It
  passes every casual test and fails the one requirement that matters — matching a real
  contract note exactly.

## Consequences

- Every module downstream expresses money as `Paisa`. Mixing units is a type error.
- Percentages go through `pct_of(paisa, Decimal)`, keeping rounding in one place.
- Storing money in SQLite is an `INTEGER` column with no serialisation ambiguity.
