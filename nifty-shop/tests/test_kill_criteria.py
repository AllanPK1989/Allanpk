from __future__ import annotations

from datetime import date
from pathlib import Path

from nifty_shop.kill_criteria import evaluate, load_kill_criteria

REPO = Path(__file__).parents[1]
CRITERIA_TOML = REPO / "config" / "kill_criteria.toml"
CRITERIA_DOC = REPO / "docs" / "kill-criteria" / "2026-08-31-pre-registered-kill-criteria.md"


def test_loads_the_registered_criteria() -> None:
    kc = load_kill_criteria(CRITERIA_TOML)
    assert kc.registered_on == date(2026, 8, 31)
    assert kc.allocated_capital_inr == 10_00_000
    assert kc.max_drawdown_pct == 20.0
    assert kc.max_zero_exit_sessions == 40
    assert kc.peak_capital_threshold_inr == 8_00_000


def test_clean_result_breaches_nothing() -> None:
    kc = load_kill_criteria(CRITERIA_TOML)
    assert (
        evaluate(
            kc,
            max_book_drawdown_pct=11.0,
            longest_zero_exit_sessions=22,
            peak_capital_deployed_inr=3_10_000,
        )
        == []
    )


def test_the_predicted_2008_shape_breaches_kc1_and_kc3_only() -> None:
    """Matches the prediction recorded in the dated criteria file."""
    kc = load_kill_criteria(CRITERIA_TOML)
    breaches = evaluate(
        kc,
        max_book_drawdown_pct=24.0,
        longest_zero_exit_sessions=18,
        peak_capital_deployed_inr=8_20_000,
    )
    assert [b.criterion for b in breaches] == ["KC-1", "KC-3"]


def test_boundary_is_exclusive_worse_than_not_equal_to() -> None:
    kc = load_kill_criteria(CRITERIA_TOML)
    assert (
        evaluate(
            kc,
            max_book_drawdown_pct=20.0,
            longest_zero_exit_sessions=40,
            peak_capital_deployed_inr=8_00_000,
        )
        == []
    )


def test_prose_and_numbers_cannot_drift_apart() -> None:
    """The dated file is the registration; the TOML is what the code reads.
    If they ever disagree, the registration has been quietly edited."""
    kc = load_kill_criteria(CRITERIA_TOML)
    prose = CRITERIA_DOC.read_text(encoding="utf-8")
    assert f"worse than {kc.max_drawdown_pct}%" in prose
    assert f"beyond {kc.max_zero_exit_sessions} NSE trading sessions" in prose
    assert f"exceeds {kc.max_peak_capital_pct:.0f}% of allocated capital" in prose
