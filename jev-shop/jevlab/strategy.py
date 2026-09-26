"""YOUR STRATEGY: the Nifty Shop rules. This is the one file you're meant to edit.

The Nifty Shop (popularised by Mahesh Chander Kaushik, written up by FabTrader as
the "10-minute trading strategy for busy professionals") buys temporary weakness
in big, liquid Nifty 50 companies and sells when the bounce comes. Once a day,
near the close (15:18 IST):

  1. SELL (at most one a day): of the stocks you hold, the one furthest above its
     average buy price, if it's at least 5% up. The whole holding is sold.
  2. BUY (at most one a day): rank the Nifty 50 by how far each is below its
     20-day moving average. Of the 5 furthest below, buy the first one you don't
     already hold, for your daily amount (₹5,000 by default).
  3. If you can't (you hold all 5, or a share costs more than your amount),
     AVERAGE instead: of your holdings now 3% or more below their LAST buy
     price, add one lot to the one that has fallen furthest.

There is no stop-loss in the original rules: a stock that keeps falling just gets
averaged. max_lots_per_stock is our addition, so no single stock can swallow your
capital. Sells go first, so money freed up today can be reused today.

decide() gets:
  scan       every stock with enough data, most below its 20-DMA first:
               {"symbol": "INFY", "ltp": 1480.5, "dma": 1532.1, "gap": -0.0337}   (gap = ltp / dma - 1)
  holdings   what you hold: {"INFY": {"qty": 7, "avg": 1500.2, "last_buy": 1471.0, "lots": 2, "ltp": 1480.5}}
  buy_amount, average_amount   rupees per new buy / per averaging lot (BUY_AMOUNT_INR, AVERAGE_AMOUNT_INR in .env)

and returns:
  {"sell": {"symbol": ..., "reason": ...} or None,
   "buys": [{"symbol": ..., "kind": "new" | "average", "amount": ..., "reason": ...}, ...],   best first
   "notes": [...]}
The runner sells, then buys the FIRST entry in "buys" it can (it checks cash, your
limits and the optional news check), and records everything. Change the numbers in
SETTINGS, or rewrite decide(). Then run `uv run python -m jevlab backtest` to see
what your change would have done, and `scan` to see what it would do today.
"""

SETTINGS = {
    "dma_days": 20,           # the moving average the ranking uses
    "candidates": 5,          # look at the 5 stocks furthest below it
    "only_below_dma": True,   # and only if they really are below it
    "average_drop": 0.03,     # average into a holding once it's 3% below its last buy price
    "target": 0.05,           # sell a whole holding once it's 5% above its average price
    "max_lots_per_stock": 6,  # our addition: stop averaging a stock after 6 lots
}

DESCRIPTION = (f"Nifty 50 · buy the furthest below the {SETTINGS['dma_days']}-DMA · "
               f"average at -{SETTINGS['average_drop']:.0%} · sell at +{SETTINGS['target']:.0%} · one buy and one sell a day")


def decide(scan: list[dict], holdings: dict, buy_amount: float, average_amount: float) -> dict:
    s = SETTINGS
    notes: list[str] = []

    # 1. the best winner at or above target
    sell = None
    winners = [(h["ltp"] / h["avg"] - 1, sym) for sym, h in holdings.items() if h.get("ltp") and h["avg"] > 0]
    winners = [w for w in winners if w[0] >= s["target"]]
    if winners:
        gain, sym = max(winners)
        sell = {"symbol": sym, "reason": f"{gain:+.1%} above its average price (target +{s['target']:.0%})"}

    # 2. a new stock from the bottom of the ranking
    pool = [x for x in scan if x["gap"] < 0] if s["only_below_dma"] else list(scan)
    bottom = pool[:s["candidates"]]
    sold = sell["symbol"] if sell else None
    new, too_dear = [], []
    for x in bottom:
        if x["symbol"] in holdings or x["symbol"] == sold:
            continue
        (new if x["ltp"] <= buy_amount else too_dear).append(x)
    for x in too_dear:
        notes.append(f"{x['symbol']} is a candidate, but one share (₹{x['ltp']:,.0f}) costs more than ₹{buy_amount:,.0f}")
    buys = [{"symbol": x["symbol"], "kind": "new", "amount": buy_amount,
             "reason": f"{-x['gap']:.1%} below its {s['dma_days']}-DMA, not held yet"} for x in new]

    # 3. otherwise average the holding that has fallen furthest since its last buy
    if not buys:
        if not bottom:
            notes.append(f"no Nifty 50 stock is below its {s['dma_days']}-DMA today")
        drops = []
        for sym, h in holdings.items():
            if not h.get("ltp") or sym == sold or h["lots"] >= s["max_lots_per_stock"] or h["ltp"] > average_amount:
                continue
            drop = h["ltp"] / h["last_buy"] - 1
            if drop <= -s["average_drop"]:
                drops.append((drop, sym))
        maxed = [sym for sym, h in holdings.items() if h["lots"] >= s["max_lots_per_stock"]]
        if maxed:
            notes.append(f"not averaging {', '.join(sorted(maxed))} any more ({s['max_lots_per_stock']} lots each)")
        buys = [{"symbol": sym, "kind": "average", "amount": average_amount,
                 "reason": f"{drop:.1%} since its last buy (averages at -{s['average_drop']:.0%})"} for drop, sym in sorted(drops)]
        if not buys and holdings:
            notes.append("nothing to buy today: all candidates held, and no holding is far enough down to average")
    return {"sell": sell, "buys": buys, "notes": notes}
