"""One net worth across two currencies.

Everything is reduced to a common currency at one fetched rate, and both
currencies are reported so the rupee view and the dollar view agree by
construction rather than by two separate sums.
"""
from __future__ import annotations


def combine(us: dict, india: dict, usdinr: float, fx_meta: dict) -> dict:
    us_value_usd = us["totals"]["value"]
    us_cost_usd = us["totals"]["cost"]
    in_value_inr = india["totals"]["value"]
    in_cost_inr = india["totals"]["cost"]

    us_value_inr = us_value_usd * usdinr
    us_cost_inr = us_cost_usd * usdinr
    total_inr = us_value_inr + in_value_inr
    cost_inr = us_cost_inr + in_cost_inr

    def side(label, value_inr, cost_inr_, value_native, cost_native, currency):
        return dict(
            label=label, currency=currency,
            value_native=round(value_native, 2), cost_native=round(cost_native, 2),
            pl_native=round(value_native - cost_native, 2),
            value_inr=round(value_inr, 2), cost_inr=round(cost_inr_, 2),
            pl_inr=round(value_inr - cost_inr_, 2),
            value_usd=round(value_inr / usdinr, 2),
            pl_pct=round((value_native / cost_native - 1) * 100, 2) if cost_native else None,
            share=round(value_inr / total_inr * 100, 2) if total_inr else 0.0)

    sides = [
        side("India", in_value_inr, in_cost_inr, in_value_inr, in_cost_inr, "INR"),
        side("United States", us_value_inr, us_cost_inr, us_value_usd, us_cost_usd, "USD"),
    ]

    # Asset classes across both books. The US book is direct equity; the India
    # book already carries its own classes, including the foreign equity held
    # through Indian funds — which belongs with the rest of the overseas
    # exposure, not with India.
    classes: dict[str, float] = {}
    for name, b in india.get("by_class", {}).items():
        classes[name] = classes.get(name, 0.0) + b["value"]
    for row in us["universe"]:
        if not row.get("held"):
            continue
        bucket = ("Crypto" if row["theme"] == "Crypto"
                  else "US equity ETF" if "ETF" in row["theme"]
                  else "US equity")
        classes[bucket] = classes.get(bucket, 0.0) + row["value"] * usdinr
    classes = {k: round(v, 2) for k, v in sorted(classes.items(), key=lambda kv: -kv[1])}

    # Every holding, both books, in one list — the only way to see true
    # single-name concentration when the same theme is held on two continents.
    positions = []
    for h in india["holdings"]:
        positions.append(dict(name=h["name"], symbol=h["symbol"], book="India",
                              currency="INR", asset_class=h["asset_class"],
                              value_inr=h["value"], pl_pct=h.get("pl_pct"),
                              live=h.get("live", False)))
    for row in us["universe"]:
        if not row.get("held"):
            continue
        positions.append(dict(name=row["name"], symbol=row["ticker"], book="US",
                              currency="USD", asset_class="US equity",
                              value_inr=round(row["value"] * usdinr, 2),
                              pl_pct=row.get("pl_pct"), live=row.get("live", False)))
    positions.sort(key=lambda p: -p["value_inr"])
    for p in positions:
        p["weight"] = round(p["value_inr"] / total_inr * 100, 2) if total_inr else 0.0

    equity_inr = sum(v for k, v in classes.items()
                     if "equity" in k.lower() or k == "Crypto")
    overseas_inr = sum(v for k, v in classes.items()
                       if k in ("International equity", "US equity", "US equity ETF", "Crypto"))

    return dict(
        usdinr=usdinr, fx=fx_meta,
        totals=dict(
            value_inr=round(total_inr, 2), cost_inr=round(cost_inr, 2),
            pl_inr=round(total_inr - cost_inr, 2),
            pl_pct=round((total_inr / cost_inr - 1) * 100, 2) if cost_inr else None,
            value_usd=round(total_inr / usdinr, 2),
            value_lakh=round(total_inr / 1e5, 2), value_cr=round(total_inr / 1e7, 3),
            holdings=len(positions)),
        sides=sides,
        by_class=classes,
        mix=dict(
            equity_pct=round(equity_inr / total_inr * 100, 2) if total_inr else 0.0,
            overseas_pct=round(overseas_inr / total_inr * 100, 2) if total_inr else 0.0,
            top5_pct=round(sum(p["value_inr"] for p in positions[:5]) / total_inr * 100, 2)
            if total_inr else 0.0),
        positions=positions)
