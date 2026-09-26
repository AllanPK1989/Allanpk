"""The shop's own record of every lot it bought and sold.

results/ledger-paper.json (paper mode) or results/ledger-live.json (live mode).
Firstock knows what you own; the ledger adds what the strategy needs and Firstock
doesn't keep: each lot's buy price and date (the averaging rule uses the LAST buy
price), and which days the shop has already run (so it never buys twice in a day).
"""

from __future__ import annotations

import json
import os

from .core import RESULTS


def split_factor(before: float, after: float) -> int:
    """If a price fell to about 1/2, 1/3, 1/4, 1/5 or 1/10 overnight, that's a split or bonus, not a crash."""
    if not before or not after or after >= before / 1.8:
        return 1
    ratio = before / after
    for k in (2, 3, 4, 5, 10):
        if abs(ratio / k - 1) < 0.04:
            return k
    return 1


def adjust_for_splits(prices: list[float]) -> list[float]:
    """Divide every price before an apparent split or bonus by its factor, so moving averages stay honest."""
    out = [float(p) for p in prices]
    for i in range(1, len(out)):
        k = split_factor(out[i - 1], out[i])
        if k > 1:
            out[:i] = [p / k for p in out[:i]]
    return out


class Ledger:
    def __init__(self, mode: str):
        self.mode = mode
        self.path = RESULTS / f"ledger-{mode}.json"
        try:
            self.d = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.d = {}
        for key, empty in (("lots", {}), ("closed", []), ("runs", {}), ("last_price", {})):
            self.d.setdefault(key, empty)

    def save(self) -> None:
        RESULTS.mkdir(exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, indent=1))
        os.replace(tmp, self.path)

    # ---- what you hold
    def holdings(self) -> dict[str, dict]:
        out = {}
        for sym, lots in self.d["lots"].items():
            qty = sum(l["qty"] for l in lots)
            if qty <= 0:
                continue
            cost = sum(l["qty"] * l["price"] for l in lots)
            out[sym] = {"qty": qty, "avg": cost / qty, "cost": cost, "last_buy": lots[-1]["price"], "lots": len(lots),
                        "first_buy": lots[0]["date"], "fees": sum(l.get("fees", 0.0) for l in lots)}
        return out

    def invested(self) -> float:
        return sum(h["cost"] for h in self.holdings().values())

    # ---- trades
    def buy(self, sym: str, qty: int, price: float, fees: float, day: str, kind: str) -> None:
        self.d["lots"].setdefault(sym, []).append({"date": day, "qty": qty, "price": round(price, 2),
                                                   "fees": round(fees, 2), "kind": kind})
        self.save()

    def sell(self, sym: str, qty: int, price: float, fees: float, day: str) -> float:
        """Sell `qty` shares, oldest lots first. Returns the net profit (after buy and sell charges)."""
        lots, left, cost, buy_fees = self.d["lots"].get(sym, []), qty, 0.0, 0.0
        first = lots[0]["date"] if lots else day
        while left > 0 and lots:
            lot = lots[0]
            take = min(left, lot["qty"])
            share = take / lot["qty"]
            cost += take * lot["price"]
            buy_fees += lot.get("fees", 0.0) * share
            lot["fees"] = lot.get("fees", 0.0) * (1 - share)
            lot["qty"] -= take
            left -= take
            if lot["qty"] <= 0:
                lots.pop(0)
        if not lots:
            self.d["lots"].pop(sym, None)
        sold = qty - left
        pnl = sold * price - cost - buy_fees - fees
        self.d["closed"].append({"symbol": sym, "qty": sold, "avg": round(cost / sold, 2) if sold else 0.0,
                                 "price": round(price, 2), "first_buy": first, "sold": day, "pnl": round(pnl, 2),
                                 "fees": round(buy_fees + fees, 2)})
        self.save()
        return pnl

    def adjust_splits(self, prices: dict[str, float], notes: list[str]) -> None:
        """A split or bonus multiplies your shares and divides the price. Adjust the lots to match, so the
        averaging and target rules keep working (checked against the price the last run saw)."""
        for sym in list(self.d["lots"]):
            k = split_factor(self.d["last_price"].get(sym, 0.0), prices.get(sym, 0.0))
            if k > 1:
                for lot in self.d["lots"][sym]:
                    lot["qty"] *= k
                    lot["price"] = round(lot["price"] / k, 2)
                notes.append(f"{sym}: price fell to about 1/{k} overnight, so this looks like a split or bonus. "
                             f"Shares ×{k}, buy prices ÷{k} (check it against your Firstock holdings)")
        self.d["last_price"].update({s: p for s, p in prices.items() if p})
        self.save()

    # ---- one run a day
    def ran(self, day: str) -> dict | None:
        return self.d["runs"].get(day)

    def mark(self, day: str, summary: dict) -> None:
        self.d["runs"][day] = summary
        runs = self.d["runs"]
        for old in sorted(runs)[:-400]:  # keep a bit over a year and a half of daily summaries
            runs.pop(old)
        self.save()

    def realised(self) -> tuple[float, int, int]:
        closed = self.d["closed"]
        return sum(c["pnl"] for c in closed), sum(1 for c in closed if c["pnl"] > 0), len(closed)
