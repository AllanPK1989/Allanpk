"""The portfolio itself: positions, reference data, and live marking.

Reference data (share counts, cost bases, 52-week ranges, multiples, consensus
targets, written verdicts) is loaded from data/portfolio.json, which
build_data.py generates. Live prices are laid over the top and everything
downstream — values, weights, P&L, scores — is recomputed from them, so a live
price never sits next to a stale score.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

from . import analytics
from .providers import Quote

DATA = pathlib.Path(__file__).resolve().parents[2] / "data" / "portfolio.json"


class Book:
    def __init__(self, path: pathlib.Path = DATA):
        self.path = path
        self.base: dict[str, Any] = json.loads(path.read_text())

    @property
    def tickers(self) -> list[str]:
        return [r["ticker"] for r in self.base["universe"]]

    def mark(self, quotes: dict[str, Quote]) -> dict:
        """Return the whole book marked to `quotes`, falling back per ticker to
        the reference close where no quote arrived."""
        book = json.loads(json.dumps(self.base))     # deep copy; leave base pristine
        by_ticker = {r["ticker"]: r for r in book["universe"]}

        live_count = 0
        for t, row in by_ticker.items():
            # the price the written verdict was formed at, kept so the page can
            # flag a call whose premise has moved out from under it
            row["ref_px"] = row["px"]
            q = quotes.get(t)
            if q and q.price:
                live_count += 1
                row["px"] = round(q.price, 4)
                row["day_pct"] = round(q.day_pct, 2) if q.day_pct is not None else None
                row["quote_source"] = q.source
                row["quote_age"] = None                # filled by the caller
                if q.low52:
                    row["lo"] = round(q.low52, 4)
                if q.high52:
                    row["hi"] = round(q.high52, 4)
                if len(q.closes) > 20:
                    row["sma50"] = analytics.sma(q.closes, 50)
                    row["sma200"] = analytics.sma(q.closes, 200)
                    row["rsi"] = analytics.rsi(q.closes)
                    row["spark"] = [round(c, 2) for c in q.closes[-90:]]
                row["live"] = True
            else:
                row["live"] = False
                row["quote_source"] = None

            row["drift_pct"] = (round((row["px"] / row["ref_px"] - 1) * 100, 1)
                                if row.get("live") and row["ref_px"] else None)

            # rescore against whatever price we ended up with
            row.update(analytics.score(row["px"], row.get("lo"), row.get("hi"),
                                       row.get("fpe"), row.get("tgt"), row["theme"]))
            row["tier"] = analytics.tier(row["verdict"])

        # accounts and totals
        total_v = total_c = 0.0
        for acc in book["accounts"]:
            v = c = 0.0
            for h in acc["holdings"]:
                px = by_ticker[h["ticker"]]["px"]
                h["price"] = px
                h["value"] = round(h["shares"] * px, 2)
                h["pl"] = round(h["value"] - h["cost_basis"], 2)
                h["pl_pct"] = round((h["value"] / h["cost_basis"] - 1) * 100, 2) if h["cost_basis"] else None
                v += h["value"]
                c += h["cost_basis"]
            acc["value"] = round(v, 2)
            acc["cost"] = round(c, 2)
            acc["pl"] = round(v - c, 2)
            acc["pl_pct"] = round((v / c - 1) * 100, 2) if c else None
            total_v += v
            total_c += c

        for row in book["universe"]:
            if not row.get("held"):
                continue
            row["value"] = round(row["shares"] * row["px"], 2)
            row["pl"] = round(row["value"] - row["cost_basis"], 2)
            row["pl_pct"] = round((row["value"] / row["cost_basis"] - 1) * 100, 2)
            row["weight"] = round(row["value"] / total_v * 100, 2) if total_v else 0.0

        book["totals"].update(
            value=round(total_v, 2), cost=round(total_c, 2),
            pl=round(total_v - total_c, 2),
            pl_pct=round((total_v / total_c - 1) * 100, 2) if total_c else None,
            value_inr=round(total_v * book["usdinr"], 0),
        )
        book["themes"] = {}
        for row in book["universe"]:
            if row.get("held"):
                book["themes"][row["theme"]] = round(
                    book["themes"].get(row["theme"], 0) + row["value"], 2)
        book["themes"] = dict(sorted(book["themes"].items(), key=lambda kv: -kv[1]))
        book["live_count"] = live_count
        book["universe_count"] = len(book["universe"])
        return book
