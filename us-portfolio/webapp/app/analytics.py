"""The valuation and entry-quality model.

This is the single implementation. build_data.py imports it for the static
build and the web app imports it for live scoring, so a change to the model
can never leave the two disagreeing.
"""
from __future__ import annotations

# Sector medians the forward multiple is judged against.
SECTOR_MEDIAN_FPE = {
    "AI semis": 30.4, "Semi equipment": 30.4, "Memory": 30.4,
    "Semi turnaround": 30.4, "Semi ETF": 30.4,
    "Software": 19.9, "Cyber": 19.9,
    "Mega-cap": 22.0, "Consumer tech": 22.0, "Intl e-commerce": 22.0,
    "AI infra": 30.0, "Space": 30.0, "Nuclear / defense": 25.0,
    "Crypto": None,
}

# Weights for the three valuation legs. They must sum to 1.
W_UPSIDE, W_MULTIPLE, W_RANGE = 0.40, 0.40, 0.20


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def entry_score(off_high_pct: float | None) -> float:
    """How good today's price is as an entry, from the pullback depth alone.

    The sweet spot is 12-35% off the 52-week high: deep enough that the
    discount is real, not so deep that the thesis is in question. Both tails
    are penalised — no margin of safety at the top, falling knife at the
    bottom.
    """
    if off_high_pct is None:
        return 50.0
    oh = off_high_pct
    if oh < 5:
        s = 25.0
    elif oh < 12:
        s = 45 + (oh - 5) * 4.3
    elif oh <= 35:
        s = 75 + (oh - 12) * 1.1
    elif oh <= 50:
        s = 100 - (oh - 35) * 2.7
    else:
        s = 55 - (oh - 50) * 1.2
    return round(clamp(s), 1)


def score(px: float, lo: float | None, hi: float | None,
          fpe: float | None, tgt: float | None, theme: str) -> dict:
    """Score one name. Returns the two scores plus every intermediate value,
    so the page can show the arithmetic rather than just a number."""
    out: dict = {}

    # leg 1 — upside to the consensus target
    if tgt and px:
        up = (tgt / px - 1) * 100
        out["upside_pct"] = round(up, 1)
        s_up = clamp(50 + up * 1.6)          # flat -> 50, +30% -> 98
    else:
        out["upside_pct"] = None
        s_up = 50.0

    # leg 2 — forward multiple against the sector median
    med = SECTOR_MEDIAN_FPE.get(theme)
    if fpe and med:
        prem = (fpe / med - 1) * 100          # negative = cheaper than sector
        out["fpe_prem_pct"] = round(prem, 1)
        s_pe = clamp(50 - prem * 0.9)
    else:
        out["fpe_prem_pct"] = None
        s_pe = 50.0

    # leg 3 — where the price sits in its 52-week range
    if lo and hi and hi > lo and px:
        rng = (px - lo) / (hi - lo) * 100
        out["range_pct"] = round(rng, 1)
        out["off_high_pct"] = round((1 - px / hi) * 100, 1)
        s_rng = clamp(100 - rng)
    else:
        out["range_pct"] = out["off_high_pct"] = None
        s_rng = 50.0

    out["val_score"] = round(W_UPSIDE * s_up + W_MULTIPLE * s_pe + W_RANGE * s_rng, 1)
    out["entry_score"] = entry_score(out["off_high_pct"])
    out["combined"] = round(0.6 * out["val_score"] + 0.4 * out["entry_score"], 1)
    return out


def tier(verdict: str) -> str:
    """Map a written verdict onto a status tier. Sell words are checked first
    so 'SPECULATIVE BUY' lands in buy but 'DO NOT ADD' does not."""
    v = verdict.upper()
    if any(w in v for w in ("TRIM", "AVOID", "DO NOT ADD")):
        return "sell"
    if any(w in v for w in ("BUY", "ACCUMULATE", "DIP")):
        return "buy"
    return "hold"


# ---- technicals, computed from a close series -----------------------------

def sma(closes: list[float], n: int) -> float | None:
    return sum(closes[-n:]) / n if len(closes) >= n else None


def rsi(closes: list[float], n: int = 14) -> float | None:
    """Wilder RSI over the last n periods."""
    if len(closes) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(len(closes) - n, len(closes)):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    if gains == 0 and losses == 0:
        return 50.0        # a flat series has no strength either way
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return round(100 - 100 / (1 + rs), 1)
