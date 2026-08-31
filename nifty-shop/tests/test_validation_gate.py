from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from nifty_shop.validation_gate import (
    ReferencePoint,
    ValidationGateNotSatisfiedError,
    assert_gate_satisfied,
    check,
    load_reference_points,
)

REFERENCE_DIR = Path(__file__).parent / "fixtures" / "reference"


def rising_closes(count: int = 260) -> list[float]:
    return [100.0 + i * 0.5 for i in range(count)]


def point(symbol: str, as_of: date, rsi: float, sma: float) -> ReferencePoint:
    return ReferencePoint(
        symbol=symbol,
        as_of=as_of,
        closes=tuple(rising_closes()),
        expected_rsi_14=rsi,
        expected_sma_50=sma,
        source="unit-test synthetic",
    )


# --- the comparison logic itself -------------------------------------------------

def test_a_wildly_wrong_expected_rsi_is_flagged() -> None:
    bad = point("AAA", date(2026, 1, 1), rsi=12.0, sma=1000.0)
    found = check([bad], rsi_tolerance=0.10, sma_tolerance=0.01)
    assert {d.metric for d in found} == {"RSI(14)", "SMA(50)"}


def test_values_inside_tolerance_are_not_flagged() -> None:
    closes = rising_closes()
    # A monotonic rise gives RSI 100 and an SMA equal to the mean of the last 50.
    expected_sma = sum(closes[-50:]) / 50
    good = point("AAA", date(2026, 1, 1), rsi=100.0, sma=expected_sma)
    assert check([good], rsi_tolerance=0.10, sma_tolerance=0.01) == []


def test_a_discrepancy_reports_both_numbers() -> None:
    bad = point("AAA", date(2026, 1, 1), rsi=12.0, sma=1000.0)
    found = check([bad], rsi_tolerance=0.10, sma_tolerance=0.01)
    rsi_finding = next(d for d in found if d.metric == "RSI(14)")
    assert rsi_finding.expected == 12.0
    assert rsi_finding.computed == 100.0
    assert "AAA" in str(rsi_finding)


def test_a_point_without_enough_warmup_is_refused_not_silently_compared() -> None:
    short = ReferencePoint(
        symbol="AAA",
        as_of=date(2026, 1, 1),
        closes=tuple(rising_closes(60)),
        expected_rsi_14=100.0,
        expected_sma_50=1.0,
        source="too short",
    )
    found = check([short], rsi_tolerance=0.10, sma_tolerance=0.01)
    assert any("warm-up" in d.metric or "warm-up" in str(d) for d in found)


# --- gate coverage rules ---------------------------------------------------------

def test_gate_refuses_with_too_few_symbols() -> None:
    points = [point(f"S{i}", date(2026, 1, 1), 100.0, 0.0) for i in range(3)]
    with pytest.raises(ValidationGateNotSatisfiedError, match="5 symbols"):
        assert_gate_satisfied(points)


def test_gate_refuses_with_too_few_dates() -> None:
    points = [point(f"S{i}", date(2026, 1, 1), 100.0, 0.0) for i in range(6)]
    with pytest.raises(ValidationGateNotSatisfiedError, match="3 distinct dates"):
        assert_gate_satisfied(points)


def test_gate_refuses_on_an_empty_fixture_set() -> None:
    with pytest.raises(ValidationGateNotSatisfiedError, match="no reference"):
        assert_gate_satisfied([])


def test_loader_reads_committed_json_fixtures(tmp_path: Path) -> None:
    payload = {
        "symbol": "RELIANCE",
        "as_of": "2026-01-15",
        "closes": rising_closes(),
        "expected_rsi_14": 100.0,
        "expected_sma_50": 42.0,
        "source": "TradingView, captured 2026-01-15",
    }
    (tmp_path / "reliance-2026-01-15.json").write_text(json.dumps(payload))
    loaded = load_reference_points(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].symbol == "RELIANCE"
    assert loaded[0].as_of == date(2026, 1, 15)
    assert loaded[0].source.startswith("TradingView")


def test_loader_rejects_a_fixture_with_no_stated_source() -> None:
    """An unsourced reference value is an assertion, not a reference."""
    tmp = REFERENCE_DIR.parent / "_tmp_bad"
    tmp.mkdir(exist_ok=True)
    try:
        (tmp / "bad.json").write_text(
            json.dumps(
                {
                    "symbol": "X",
                    "as_of": "2026-01-15",
                    "closes": [1.0],
                    "expected_rsi_14": 1.0,
                    "expected_sma_50": 1.0,
                }
            )
        )
        with pytest.raises(ValueError, match="source"):
            load_reference_points(tmp)
    finally:
        for f in tmp.iterdir():
            f.unlink()
        tmp.rmdir()


# --- THE BLOCKING GATE -----------------------------------------------------------

@pytest.mark.validation_gate
def test_indicator_validation_gate_is_satisfied() -> None:
    """BLOCKING. The spec forbids proceeding past Phase 2 until this passes.

    It fails until real reference fixtures are committed. Run the rest of the suite
    with: pytest -m "not validation_gate"
    """
    assert_gate_satisfied(load_reference_points(REFERENCE_DIR))
