"""Indian capital-gains tax estimates (rules for FY 2025-26, after the July 2024 Budget).

Simplified on purpose: surcharge, grandfathering (pre-2018 equity), business income from F&O,
and indexation for pre-2024 property are ignored. Always confirm with a chartered accountant.
"""

from __future__ import annotations

from datetime import date
from typing import Any

CESS = 0.04
EQUITY_LTCG_EXEMPTION = 125_000.0  # per financial year, listed equity + equity-oriented funds
SPECIFIED_MF_CUTOFF = date(2023, 4, 1)

RULES: dict[str, dict[str, Any]] = {
    "listed_equity": {"label": "Listed equity / equity funds", "lt_months": 12, "st": 0.20, "lt": 0.125,
                      "note": "STCG 20% (s.111A); LTCG 12.5% above Rs 1.25 lakh a year (s.112A)."},
    "listed_other": {"label": "Other listed securities (e.g. gold/silver ETFs)", "lt_months": 12, "st": "slab", "lt": 0.125,
                     "note": "Held over 12 months: 12.5% LTCG; otherwise slab rate."},
    "other_fund": {"label": "Non-equity funds (gold FoF, international FoF)", "lt_months": 24, "st": "slab", "lt": 0.125,
                   "note": "Held over 24 months: 12.5% LTCG; otherwise slab rate."},
    "foreign_equity": {"label": "Foreign shares (e.g. US stocks)", "lt_months": 24, "st": "slab", "lt": 0.125,
                       "note": "Unlisted in India: over 24 months 12.5% LTCG; otherwise slab rate."},
    "specified_mf": {"label": "Debt funds bought on/after 1 Apr 2023", "lt_months": None, "st": "slab", "lt": "slab",
                     "note": "Always taxed at your slab rate, whatever the holding period (s.50AA)."},
    "debt_mf_old": {"label": "Debt funds bought before 1 Apr 2023", "lt_months": 24, "st": "slab", "lt": 0.125,
                    "note": "Over 24 months: 12.5% without indexation; otherwise slab rate."},
    "vda": {"label": "Crypto / virtual digital assets", "lt_months": None, "st": 0.30, "lt": 0.30,
            "note": "Flat 30% on gains, losses cannot be set off or carried forward, 1% TDS on sale (s.115BBH, 194S)."},
    "not_applicable": {"label": "Indices / FX quotes", "lt_months": None, "st": 0.0, "lt": 0.0,
                       "note": "Not a holding you can be taxed on directly."},
}


def tax_class(asset_class: str, region: str, *, name: str = "", meta: dict[str, Any] | None = None,
              buy_date: date | None = None) -> str:
    meta = meta or {}
    n = name.lower()
    if asset_class == "crypto":
        return "vda"
    if asset_class in ("index", "forex"):
        return "not_applicable"
    if asset_class == "stock":
        return "listed_equity" if region == "IN" else "foreign_equity"
    if asset_class == "etf":
        if region != "IN":
            return "foreign_equity"
        if "gold" in n or "silver" in n:
            return "listed_other"
        if any(k in n for k in ("liquid", "bond", "gilt", "g-sec", "debt")):
            return "specified_mf" if (buy_date or date.today()) >= SPECIFIED_MF_CUTOFF else "debt_mf_old"
        return "listed_equity"
    if asset_class == "mutual_fund":
        if meta.get("equityOriented"):
            return "listed_equity"
        bucket = meta.get("bucket", "")
        if bucket == "debt":
            return "specified_mf" if (buy_date or date.today()) >= SPECIFIED_MF_CUTOFF else "debt_mf_old"
        return "other_fund"
    if asset_class in ("commodity", "bond"):
        return "listed_other"
    return "listed_other"


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    y += d.year
    m += 1
    import calendar

    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def is_long_term(cls: str, buy: date, sell: date) -> bool:
    months = RULES[cls]["lt_months"]
    if months is None:
        return False
    return sell > add_months(buy, months)


def financial_year(d: date) -> str:
    start = d.year if d.month >= 4 else d.year - 1
    return f"FY{start}-{str(start + 1)[-2:]}"


def _rate(r: Any, slab: float) -> float:
    return slab if r == "slab" else float(r)


def estimate(gains: list[dict[str, Any]], *, slab_rate: float = 0.30, exemption_used: float = 0.0) -> dict[str, Any]:
    """gains: [{tax_class, buy_date, sell_date, gain}] realised within one financial year.

    Set-off (simplified): short-term losses can reduce any gain; long-term losses only long-term gains.
    Losses are applied to the highest-taxed gains first. Crypto losses are ignored, as the law requires.
    """
    gross: dict[tuple[str, str], float] = {}  # positive gains per (class, term)
    st_loss = lt_loss = 0.0
    for g in gains:
        cls = g["tax_class"]
        if cls == "not_applicable":
            continue
        term = "LT" if is_long_term(cls, g["buy_date"], g["sell_date"]) else "ST"
        if cls == "specified_mf":
            term = "ST"
        amount = float(g["gain"])
        if amount >= 0:
            gross[(cls, term)] = gross.get((cls, term), 0.0) + amount
        elif cls != "vda":  # crypto losses are simply lost
            if term == "ST":
                st_loss -= amount
            else:
                lt_loss -= amount

    def rate_of(key: tuple[str, str]) -> float:
        cls, term = key
        return _rate(RULES[cls]["lt" if term == "LT" else "st"], slab_rate)

    gains_pos = dict(gross)
    order = sorted((k for k in gains_pos if k[0] != "vda"), key=lambda k: -rate_of(k))
    for k in order:  # long-term losses: only against long-term gains
        if k[1] == "LT" and lt_loss > 0:
            use = min(lt_loss, gains_pos[k])
            gains_pos[k] -= use
            lt_loss -= use
    for k in order:  # short-term losses: against anything
        if st_loss > 0:
            use = min(st_loss, gains_pos[k])
            gains_pos[k] -= use
            st_loss -= use

    rows, total_tax = [], 0.0
    exemption_left = max(0.0, EQUITY_LTCG_EXEMPTION - exemption_used)
    for (cls, term), taxable in sorted(gains_pos.items()):
        exempt = 0.0
        if cls == "listed_equity" and term == "LT":
            exempt = min(exemption_left, taxable)
            exemption_left -= exempt
        rate = rate_of((cls, term))
        tax = (taxable - exempt) * rate * (1 + CESS)
        total_tax += tax
        rows.append({"tax_class": cls, "label": RULES[cls]["label"], "term": term, "gross_gain": round(gross[(cls, term)], 2),
                     "taxable_after_setoff": round(taxable, 2), "exempt": round(exempt, 2), "rate_pct": round(rate * 100, 2),
                     "tax_incl_cess": round(tax, 2)})
    return {"rows": rows, "total_tax": round(total_tax, 2),
            "carry_forward_losses": {"short_term": round(st_loss, 2), "long_term": round(lt_loss, 2)},
            "ltcg_exemption_left": round(exemption_left, 2), "slab_rate_pct": slab_rate * 100,
            "notes": ["Cess of 4% included; surcharge ignored.",
                      "Crypto losses cannot be set off against any income.",
                      "Estimates only; confirm with a chartered accountant."]}


def unrealized_view(holdings: list[dict[str, Any]], *, today: date, slab_rate: float = 0.30,
                    exemption_used: float = 0.0) -> dict[str, Any]:
    """holdings: [{symbol, name, tax_class, price (INR), lots: [{quantity, price (INR), buy_date}]}].

    For each holding: what is long/short term today, tax if everything were sold today,
    and short-term lots that turn long-term within 60 days (worth waiting for).
    """
    rows, gains, soon = [], [], []
    for h in holdings:
        cls, price = h["tax_class"], h["price"]
        if cls == "not_applicable" or price is None:
            continue
        st_gain = lt_gain = 0.0
        for lot in h["lots"]:
            g = lot["quantity"] * (price - lot["price"])
            lt = is_long_term(cls, lot["buy_date"], today)
            gains.append({"tax_class": cls, "buy_date": lot["buy_date"], "sell_date": today, "gain": g})
            if lt:
                lt_gain += g
            else:
                st_gain += g
                months = RULES[cls]["lt_months"]
                if months is not None and g > 0:
                    lt_on = add_months(lot["buy_date"], months)
                    days = (lt_on - today).days + 1
                    if 0 < days <= 60:
                        st_rate, lt_rate = _rate(RULES[cls]["st"], slab_rate), _rate(RULES[cls]["lt"], slab_rate)
                        soon.append({"symbol": h["symbol"], "name": h.get("name"), "quantity": lot["quantity"],
                                     "becomes_long_term_on": (add_months(lot["buy_date"], months)).isoformat(),
                                     "days_left": days, "gain": round(g, 2),
                                     "tax_saved_by_waiting": round(g * (st_rate - lt_rate) * (1 + CESS), 2)})
        rows.append({"symbol": h["symbol"], "name": h.get("name"), "tax_class": cls, "label": RULES[cls]["label"],
                     "short_term_gain": round(st_gain, 2), "long_term_gain": round(lt_gain, 2)})
    est = estimate(gains, slab_rate=slab_rate, exemption_used=exemption_used)
    equity_lt = sum(r["long_term_gain"] for r in rows if r["tax_class"] == "listed_equity" and r["long_term_gain"] > 0)
    harvest = min(max(0.0, EQUITY_LTCG_EXEMPTION - exemption_used), equity_lt)
    losers = [r for r in rows if r["short_term_gain"] + r["long_term_gain"] < 0 and r["tax_class"] != "vda"]
    return {
        "as_of": today.isoformat(), "financial_year": financial_year(today), "holdings": rows,
        "if_sold_today": est, "turning_long_term_soon": sorted(soon, key=lambda s: s["days_left"]),
        "ltcg_harvest_room": round(harvest, 2),
        "tax_loss_candidates": [{"symbol": r["symbol"], "name": r["name"],
                                 "loss": round(r["short_term_gain"] + r["long_term_gain"], 2)} for r in losers],
        "rules": {k: {"label": v["label"], "note": v["note"]} for k, v in RULES.items() if k != "not_applicable"},
    }
