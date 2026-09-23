"""Buy calls for the India book.

The US model scores a share on its consensus target, forward multiple and
position in a 52-week range. None of that transfers here. A mutual fund has no
price target and no P/E of its own; an index ETF's valuation is the *index's*;
a gilt fund is a call on the rate cycle, not on value; and an unlisted holding
has no market at all. So each instrument is judged on what actually moves it.

Market inputs are dated and sourced rather than inferred, and the page shows
the date, because a call built on a stale multiple is worse than no call.
"""
from __future__ import annotations

# ── market inputs, gathered 23 Sep 2026 ─────────────────────────────────────
# Index P/E against its own medium-run median — the only defensible way to say
# an index fund is cheap or dear.
MARKET = {
    "as_of": "2026-09-23",
    "indices": {
        "nifty50":     dict(label="Nifty 50",           pe=19.54, median=21.99, window="5-year"),
        "next50":      dict(label="Nifty Next 50",      pe=18.98, median=21.00, window="5-year"),
        "midcap150":   dict(label="Nifty Midcap 150",   pe=30.21, median=29.77, window="5-year"),
        "smallcap250": dict(label="Nifty Smallcap 250", pe=33.23, median=28.33, window="5-year"),
        "banknifty":   dict(label="Bank Nifty",         pe=13.20, median=14.93, window="3-year"),
        # A diversified fund is not any one index. This is an explicit
        # 60/25/15 large/mid/small blend, stated so the reader can disagree
        # with the weights rather than wonder where the number came from.
        "broad":       dict(label="Broad market (60/25/15 large/mid/small)",
                            pe=24.26, median=24.88, window="5-year"),
    },
    "rates": dict(
        gsec10y=7.02,
        direction="rising",
        note="10-year G-sec at 7.02%; a 25bp RBI hike is widely expected at the "
             "7 October policy, after the Fed's own 25bp move.",
    ),
    "tax": dict(
        equity_ltcg="12.5% above Rs 1.25L a year, once held over 12 months",
        equity_stcg="20% under 12 months",
        debt="taxed at slab for anything bought after 1 Apr 2023, with no "
             "long-term benefit",
        elss="three-year lock-in on every instalment",
    ),
}

# Which index actually prices each holding.
BENCH = {
    # listed ETFs
    "NIFTYBEES": "nifty50", "JUNIORBEES": "next50", "BANKBEES": "banknifty",
    "MIDCAPETF": "midcap150", "HDFCSML250": "smallcap250",
    # index funds, by ISIN
    "INF959L01FP2": "nifty50",     # Navi Nifty 50
    "INF959L01FR8": "next50",      # Navi Nifty Next 50
    "INF959L01FT4": "banknifty",   # Navi Nifty Bank
}
# Active funds are judged against the segment they fish in.
SUB_BENCH = {"Small cap": "smallcap250", "Mid cap": "midcap150",
             "Large cap index": "nifty50", "Banking": "banknifty",
             "ELSS": "broad", "Diversified": "broad"}
# A single-sector fund is a concentration decision, not a valuation one.
SECTOR_SUBS = {"Technology"}

DEBT_DURATION = {           # years, roughly; what the rate cycle acts on
    "LTGILTBEES": 9.0, "GILT5YBEES": 4.5, "LIQUIDBEES": 0.1,
    "UNCLAIMDISIN": 0.0,
}


def _discount(bench: dict) -> float:
    """How far the index sits below its own median, in percent. Negative is dear."""
    return round((1 - bench["pe"] / bench["median"]) * 100, 1)


def _equity_call(disc: float) -> tuple[str, str]:
    if disc >= 8:
        return "ADD", "cheap against its own history"
    if disc >= -4:
        return "KEEP BUYING", "near its own median"
    if disc >= -14:
        return "HOLD", "above median — hold, don't add"
    return "PAUSE", "well above its own history"


def call_for(h: dict, us_overlap: set[str]) -> dict | None:
    """Return a call for one holding, or None where no honest call exists."""
    kind, sub, sym = h["kind"], h.get("sub_class"), h["symbol"]
    isin = (h.get("isin") or "").upper()
    cls = h["asset_class"]

    # ── unlisted: there is no market, so there is no call
    if kind == "pre_ipo":
        return dict(action="NO CALL", tier="none", basis="Unlisted",
                    why="No market price exists for an unlisted holding, so "
                        "nothing here can tell you whether it is cheap. It moves "
                        "on the next funding round or a listing, not on a screen.")

    # ── debt: a duration call on the rate cycle, not a valuation call
    if cls == "Debt / cash":
        yrs = DEBT_DURATION.get(sym, DEBT_DURATION.get(isin, 1.0))
        r = MARKET["rates"]
        if r["direction"] == "rising" and yrs >= 6:
            return dict(action="REDUCE", tier="sell", basis="Rate cycle",
                        why=f"About {yrs:.0f} years of duration into a rising "
                            f"cycle. {r['note']} Long gilts lose price as yields "
                            f"rise, and this is the longest thing you own.")
        if r["direction"] == "rising" and yrs >= 2:
            return dict(action="HOLD", tier="hold", basis="Rate cycle",
                        why=f"About {yrs:.0f} years of duration — it will wobble "
                            f"if the October hike lands, but not like the long "
                            f"gilt. Fine as ballast.")
        return dict(action="FAVOURED", tier="buy", basis="Rate cycle",
                    why="Near-zero duration, so it rolls into higher yields "
                        "instead of being hurt by them. The place to park while "
                        "rates rise — taxed at slab, so it is for stability, not return.")

    # ── international feeders: the call is about duplication, not valuation
    if cls == "International equity":
        if sym in us_overlap or "FANG" in h["name"].upper():
            return dict(action="TRIM", tier="sell", basis="Duplicate exposure",
                        why="This holds the same mega-cap US names you already "
                            "own directly in the US book. You are paying a "
                            "fund-of-fund expense ratio for exposure you have at "
                            "no marginal cost, and it is taxed as a foreign-equity "
                            "fund rather than as the shares themselves.")
        return dict(action="HOLD", tier="hold", basis="Diversifier",
                    why="Genuine diversification away from both India and your US "
                        "names. Worth keeping, but size it deliberately — it is "
                        "taxed like a debt fund, at slab, not at 12.5%.")

    # ── index-tracking: the index's own multiple against its own median
    key = BENCH.get(sym) or BENCH.get(isin)
    tracking = key is not None
    if not tracking:
        key = SUB_BENCH.get(sub)

    if key:
        b = MARKET["indices"][key]
        disc = _discount(b)
        action, gist = _equity_call(disc)
        cheap = disc >= 0
        lead = (f"{b['label']} trades at {b['pe']:.1f}x against a {b['window']} "
                f"median of {b['median']:.1f}x — {abs(disc):.0f}% "
                f"{'below' if cheap else 'above'} it, so it screens {gist}.")
        extra = ""
        if not tracking:
            extra = (" Active, so the index frames the segment rather than "
                     "prices the fund.")
        if key == "broad":
            extra += " The benchmark is a stated blend, not a real index."
        if sub == "ELSS":
            extra += (" Each fresh instalment locks in for three years, so "
                      "adding is a commitment, not a position.")
        tier = {"ADD": "buy", "KEEP BUYING": "buy", "HOLD": "hold", "PAUSE": "sell"}[action]
        return dict(action=action, tier=tier,
                    basis=f"{b['label']} {b['pe']:.1f}x",
                    discount=disc, why=lead + extra)

    # ── a single-sector fund: the live question is size, not price
    if sub in SECTOR_SUBS:
        return dict(action="CAP IT", tier="hold", basis="Single sector",
                    why="One sector in one country. No broad index prices it, "
                        "and the decision that matters is how much of the book "
                        "it is allowed to be rather than whether it looks cheap "
                        "this week. Keep it a satellite.")

    # ── anything with no honest benchmark to hand
    return dict(action="HOLD", tier="hold", basis="No index benchmark",
                why="No index multiple was gathered for this segment, so there "
                    "is nothing to call it cheap or dear against. Held on its "
                    "own merits rather than scored.")


def annotate(book: dict, us_book: dict | None = None) -> dict:
    """Attach a call to every India holding and summarise the picture."""
    us_overlap = set()
    if us_book:
        us_overlap = {r["ticker"] for r in us_book.get("universe", []) if r.get("held")}

    counts: dict[str, float] = {}
    for h in book["holdings"]:
        c = call_for(h, us_overlap)
        h["call"] = c
        if c:
            counts[c["action"]] = counts.get(c["action"], 0.0) + h["value"]

    book["calls"] = dict(
        as_of=MARKET["as_of"],
        market=MARKET,
        by_action={k: round(v, 2) for k, v in
                   sorted(counts.items(), key=lambda kv: -kv[1])},
        headline=_headline(book),
    )
    return book


def _headline(book: dict) -> str:
    idx = MARKET["indices"]
    small = _discount(idx["smallcap250"])
    large = _discount(idx["nifty50"])
    small_val = sum(h["value"] for h in book["holdings"]
                    if h.get("sub_class") == "Small cap")
    total = book["totals"]["value"] or 1
    return (
        f"Large caps are the cheap end of this market and small caps the dear "
        f"end: Nifty 50 at {idx['nifty50']['pe']:.1f}x is {abs(large):.0f}% below "
        f"its five-year median while Nifty Smallcap 250 at "
        f"{idx['smallcap250']['pe']:.1f}x is {abs(small):.0f}% above its own. "
        f"You hold Rs {small_val/1e5:.2f}L in small caps, "
        f"{small_val/total*100:.0f}% of the India book, which is where the "
        f"valuation risk is concentrated."
    )
