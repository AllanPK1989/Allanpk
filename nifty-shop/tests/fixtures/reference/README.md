# Independent reference fixtures — BLOCKING Phase 2 gate

`tests/test_validation_gate.py::test_indicator_validation_gate_is_satisfied` fails
until this directory holds real reference data. That is deliberate: the spec forbids
proceeding past Phase 2 until the indicator engine is validated, and a silently wrong
RSI produces a system that trades confidently and wrongly forever.

Run everything else meanwhile with:

    uv run pytest -m "not validation_gate"

## What is required

- At least **5 distinct symbols** across at least **3 distinct dates**.
- At least **200 bars** of closes per fixture (Wilder's RSI needs a long warm-up).
- Tolerances: **RSI(14) ±0.10**, **SMA(50) ±0.01**.

## Format

One JSON file per symbol/date, named `<symbol>-<YYYY-MM-DD>.json`:

```json
{
  "symbol": "RELIANCE",
  "as_of": "2026-01-15",
  "closes": [1234.5, "... at least 200 daily closes, oldest first, ending on as_of ..."],
  "expected_rsi_14": 41.83,
  "expected_sma_50": 1290.44,
  "source": "TradingView NSE:RELIANCE 1D, captured 2026-01-15"
}
```

`source` is mandatory. A number with no stated origin is an assertion, not a reference,
and the loader rejects the fixture.

## Capturing the values

The closes must be the **same series** the reference tool used, otherwise a mismatch
tells you nothing about the indicator code. Two things to match deliberately:

1. **Adjust for splits and bonuses, not for dividends.** That is what this project's
   `corporate_actions` module does, and it is what a default TradingView chart shows.
   A dividend-adjusted series will disagree and the disagreement will not be a bug.
2. **Use settled closes**, never the 15:20 provisional value.
