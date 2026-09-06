from app import analytics as a


def test_cheap_and_beaten_down_scores_above_dear_and_extended():
    """META-like: 15x, 22% off the high, 22% upside."""
    cheap = a.score(616.77, 520.26, 790.80, 15.0, 754.77, "Mega-cap")
    """AAPL-like: 33.5x, 7% off the high, ~3% upside."""
    dear = a.score(319.97, 223.78, 344.57, 33.5, 330.0, "Mega-cap")
    assert cheap["val_score"] > dear["val_score"]
    assert cheap["combined"] > dear["combined"]


def test_entry_curve_peaks_in_the_pullback_band():
    at_high = a.entry_score(2)
    sweet = a.entry_score(25)
    broken = a.entry_score(60)
    assert sweet > at_high and sweet > broken
    assert a.entry_score(None) == 50.0


def test_missing_inputs_do_not_crash_or_fabricate():
    r = a.score(45.23, None, None, None, None, "Crypto")
    assert r["upside_pct"] is None
    assert r["off_high_pct"] is None
    assert r["fpe_prem_pct"] is None
    assert 0 <= r["val_score"] <= 100


def test_tier_puts_speculative_buy_in_buy_and_do_not_add_in_sell():
    assert a.tier("SPECULATIVE BUY") == "buy"
    assert a.tier("BUY THE DIP") == "buy"
    assert a.tier("DO NOT ADD") == "sell"
    assert a.tier("TRIM / TAKE PROFITS") == "sell"
    assert a.tier("AVOID") == "sell"
    assert a.tier("HOLD") == "hold"
    assert a.tier("SPECULATIVE HOLD") == "hold"


def test_rsi_and_sma():
    assert a.rsi([10] * 30) == 50.0            # flat is neutral, not overbought
    assert a.rsi(list(range(1, 40))) == 100.0  # only gains
    assert a.rsi([1, 2]) is None               # not enough data
    assert a.sma([1, 2, 3, 4], 2) == 3.5
    assert a.sma([1, 2], 50) is None


def test_scoring_matches_the_static_build():
    """The web app and build_data.py must not drift apart."""
    r = a.score(357.895, 289.96, 495.0, None, 509.41, "AI semis")
    assert r["combined"] == 81.0
    assert r["off_high_pct"] == 27.7


def test_static_build_uses_this_same_model():
    """The README promises one scoring implementation. Prove it: the static
    build must import this module, not carry a second copy."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[2] / "build_data.py").read_text()
    assert "from app import analytics" in src
    assert "SECTOR_MEDIAN_FPE = {" not in src, "a second copy of the model reappeared"
