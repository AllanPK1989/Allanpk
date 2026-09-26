"""The daily Nifty Shop run.

  uv run python -m jevlab scan           # any time: today's ranking and what the shop WOULD do (no orders)
  uv run python -m jevlab run            # the real thing, 15:15 to 15:29 IST (the server's timer runs it at 15:18)
  uv run python -m jevlab run --paper    # force paper mode, whatever .env says

What a run does:
  1. Checks the day: a weekday, NSE open today (not a holiday), today's Firstock login,
     no STOP file, and that it hasn't already run today.
  2. Ranks the Nifty 50 by distance below the 20-DMA (last price vs the 19 previous closes
     plus today's price), and prices everything you hold.
  3. Asks strategy.decide() for at most one sell and one buy, and runs the news check on the buy:
     no buying into fraud, a regulator's ban, raids, insolvency and the like (see news.py).
  4. Sells first, then buys: delivery (CNC) limit orders priced 0.5% through the market in
     live mode, or a simulated fill at the last price in paper mode. Charges included.
  5. Records it in the ledger, writes results/shop.json for the dashboard, and sends you
     the day's report on Telegram (if set up).

Safety, always on:
  * paper mode unless FIRSTOCK_MODE=live AND JEV_LIVE_CONFIRM is the exact phrase
  * BUY_AMOUNT_INR / AVERAGE_AMOUNT_INR per buy, and MAX_CAPITAL_INR caps the total invested
  * at most one buy and one sell a day, and one run a day (a re-run does nothing)
  * a buy needs the cash in your Firstock account, and must pass the news check (news.py)
  * kill switch: a file called STOP in the project folder (or /stop on Telegram)
"""

from __future__ import annotations

import json
import os
import time
from datetime import time as dtime, timedelta
from pathlib import Path

from . import strategy, telegram
from .core import RESULTS, console, header, inr, ist_now
from .firstock import (FirstockError, SessionExpired, cash, charges, daily_candles, execute, holdings, live_mode,
                       load_session, ltps, trading_symbol)
from .ledger import Ledger, adjust_for_splits
from .universe import nifty50

RUN_FROM, RUN_UNTIL = dtime(15, 15), dtime(15, 29)
STOP_FILE = Path(__file__).resolve().parent.parent / "STOP"
STATUS = RESULTS / "shop.json"


def amounts() -> tuple[float, float, float]:
    buy = float(os.getenv("BUY_AMOUNT_INR", "5000"))
    avg = float(os.getenv("AVERAGE_AMOUNT_INR", "") or buy)
    cap = float(os.getenv("MAX_CAPITAL_INR", "200000"))
    return buy, avg, cap


def traded_today(session) -> bool | None:
    """Did NSE trade today? (No 1-minute candles today = a holiday.) None if we can't tell."""
    now = ist_now()
    fmt = "%H:%M:%S %d-%m-%Y"
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    for interval in ("1mi", "1"):
        try:
            rows = session.post("timePriceSeries", timeout=20, exchange="NSE", tradingSymbol="RELIANCE-EQ",
                                interval=interval, startTime=start.strftime(fmt), endTime=now.strftime(fmt))
            return bool(rows)
        except SessionExpired:
            raise
        except FirstockError as exc:
            if "no data" in str(exc).lower():
                return False
    return None


def scan_market(session, universe: dict[str, str], held: list[str]) -> tuple[list[dict], dict[str, float], list[str]]:
    """Rank the universe by distance below the DMA, and price everything held too."""
    n = strategy.SETTINGS["dma_days"]
    today = ist_now().date()
    names = sorted(set(universe) | set(held))
    by_tsym = {trading_symbol(s): s for s in names}
    px = {by_tsym[t]: p for t, p in ltps(session, list(by_tsym)).items() if t in by_tsym}
    scan, problems = [], []
    for sym in sorted(universe):
        if sym not in px:
            problems.append(f"{sym}: no price")
            continue
        try:
            df = daily_candles(session, trading_symbol(sym), today - timedelta(days=2 * n + 15), today)
        except SessionExpired:
            raise
        except FirstockError as exc:
            problems.append(f"{sym}: {str(exc)[:60]}")
            continue
        closes = [float(c) for d, c in df["close"].items() if d < today][-(n - 1):]
        if len(closes) < n - 1:
            problems.append(f"{sym}: only {len(closes)} days of history")
            continue
        dma = sum(adjust_for_splits(closes + [px[sym]])) / n  # a split or bonus mustn't look like a crash
        scan.append({"symbol": sym, "ltp": px[sym], "dma": round(dma, 2), "gap": round(px[sym] / dma - 1, 5)})
        time.sleep(0.05)
    return sorted(scan, key=lambda x: x["gap"]), px, problems


def run_shop(force_paper: bool = False, scan_only: bool = False) -> int:
    """One day's run. Returns a process exit code (0 = fine, including "nothing to do")."""
    try:
        configured = live_mode()
    except FirstockError as exc:
        if not (force_paper or scan_only):
            raise SystemExit(f"  {exc}")
        configured = "paper"
    mode = "paper" if force_paper else configured  # a scan reads the configured mode's holdings, and never trades
    buy_amount, avg_amount, max_capital = amounts()
    now = ist_now()
    today = now.date().isoformat()
    header("THE NIFTY SHOP", f"{'SCAN ONLY · no orders' if scan_only else mode.upper()} · {strategy.DESCRIPTION} · "
           f"{inr(buy_amount)} a buy, {inr(avg_amount)} an average · capital cap {inr(max_capital)}")
    ledger = Ledger(mode)

    def stop(why: str, tell: bool = True, mark: bool = False) -> int:
        console.print(f"  {why}")
        if tell and not scan_only:
            telegram.send(f"Nifty Shop ({mode}): {why}")
        if mark:
            ledger.mark(today, {"status": "skipped", "why": why, "mode": mode})
        return 0

    if not scan_only:
        if now.weekday() >= 5:
            return stop("NSE is closed today (weekend).", tell=False)
        if not RUN_FROM <= now.time() <= RUN_UNTIL:
            raise SystemExit("  the shop trades between 15:15 and 15:29 IST (the server runs it at 15:18). "
                             "Use `scan` to see what it would do right now.")
        if ledger.ran(today):
            return stop(f"already ran today ({ledger.ran(today).get('status')}): nothing more to do.", tell=False)
        if STOP_FILE.exists():
            return stop("kill switch is on (STOP file): no orders today.", mark=True)
    session = load_session()
    if not session:
        return stop("not logged in to Firstock today, so no trades today. Log in tomorrow before 15:15 "
                    "(`uv run python -m jevlab login`, or /login 123456 on Telegram).")
    try:
        if not scan_only and traded_today(session) is False:
            return stop("NSE didn't trade today (a holiday): nothing to do.", tell=False, mark=True)
        universe, source = nifty50()
        held = ledger.holdings()
        console.print(f"  ranking {len(universe)} Nifty 50 stocks ({source}) against their "
                      f"{strategy.SETTINGS['dma_days']}-DMA…")
        scan, px, problems = scan_market(session, universe, list(held))
    except SessionExpired:
        return stop("the Firstock session ended. Log in again, then re-run.")
    except FirstockError as exc:
        return stop(f"Firstock problem: {exc}")

    notes: list[str] = []
    if not scan_only:
        ledger.adjust_splits({s: px[s] for s in held if s in px}, notes)
        held = ledger.holdings()
    for sym, h in held.items():
        h["ltp"] = px.get(sym)
    decision = strategy.decide(scan, held, buy_amount, avg_amount)
    notes += decision["notes"]
    if problems:
        notes.append(f"skipped {len(problems)}: " + "; ".join(problems[:4]) + ("…" if len(problems) > 4 else ""))
    actions: list[dict] = []

    if scan_only:
        decision["buys"] = news_filter(decision["buys"], scan, held, universe, buy_amount, avg_amount, notes)
        _print_scan(scan, held, decision, notes)
        _write_status(mode, ledger, scan, held, decision, actions, notes, scan_only=True)
        return 0

    ledger.mark(today, {"status": "running", "mode": mode})  # from here on, a re-run today does nothing
    live = mode == "live"
    try:
        # ---- 1. sell (at most one)
        if decision["sell"]:
            sym = decision["sell"]["symbol"]
            qty, ref = held[sym]["qty"], px[sym]
            if live:
                avail = holdings(session).get(trading_symbol(sym), {}).get("qty", 0)
                if avail < qty:
                    notes.append(f"{sym}: ledger says {qty} shares, Firstock shows {avail} sellable; selling {avail}")
                    qty = avail
                res = execute(session, trading_symbol(sym), "sell", qty, ref) if qty else {"qty": 0, "avg_px": 0,
                                                                                            "reason": "nothing sellable"}
            else:
                res = {"qty": qty, "avg_px": ref, "reason": ""}
            if res["qty"]:
                fee = charges("sell", res["qty"] * res["avg_px"])
                pnl = ledger.sell(sym, res["qty"], res["avg_px"], fee, today)
                actions.append({"side": "sell", "symbol": sym, "qty": res["qty"], "price": res["avg_px"], "fees": round(fee, 2),
                                "pnl": round(pnl, 2), "why": decision["sell"]["reason"]})
            else:
                notes.append(f"sell of {sym} didn't go through: {res['reason'] or 'not filled'}"
                             + (" (is DDPI/eDIS switched on in Firstock?)" if live else ""))

        # ---- 2. buy (at most one: the first candidate that passes every check)
        queue = news_filter(decision["buys"], scan, held, universe, buy_amount, avg_amount, notes)
        invested = ledger.invested()
        while queue:
            b = queue.pop(0)
            sym, ref = b["symbol"], px.get(b["symbol"], 0.0)
            qty = int(b["amount"] // ref) if ref else 0
            if qty < 1:
                notes.append(f"{sym}: one share costs more than {inr(b['amount'])}")
                continue
            cost = qty * ref
            if invested + cost > max_capital:
                notes.append(f"no buy: {sym} would take the total invested past MAX_CAPITAL_INR ({inr(max_capital)})")
                break
            if live:
                free = cash(session)
                if free is not None and free < cost * 1.01 + charges("buy", cost):
                    notes.append(f"no buy: {inr(free)} cash in Firstock, {sym} needs about {inr(cost * 1.01)}")
                    break
                res = execute(session, trading_symbol(sym), "buy", qty, ref)
            else:
                res = {"qty": qty, "avg_px": ref, "reason": ""}
            if res["qty"]:
                fee = charges("buy", res["qty"] * res["avg_px"])
                ledger.buy(sym, res["qty"], res["avg_px"], fee, today, b["kind"])
                actions.append({"side": "buy", "kind": b["kind"], "symbol": sym, "qty": res["qty"], "price": res["avg_px"],
                                "fees": round(fee, 2), "why": b["reason"]})
            else:
                notes.append(f"buy of {sym} didn't go through: {res['reason'] or 'not filled'}")
            break
    except SessionExpired:
        notes.append("the Firstock session ended during the run: check the Firstock app for open orders")
    except FirstockError as exc:
        notes.append(f"Firstock problem: {str(exc)[:120]}")
    finally:
        ledger.mark(today, {"status": "done", "mode": mode, "actions": actions, "notes": notes})

    held = ledger.holdings()
    for sym, h in held.items():
        h["ltp"] = px.get(sym)
    _print_run(actions, notes, held, ledger)
    _write_status(mode, ledger, scan, held, decision, actions, notes)
    telegram.send(_report(mode, actions, notes, held, ledger))
    return 0


def news_filter(buys: list[dict], scan: list[dict], held: dict, universe: dict[str, str], buy_amount: float,
                avg_amount: float, notes: list[str]) -> list[dict]:
    """The buy candidates that pass the news check (see news.py), best first. If the news rules out
    every candidate, decide again as if those stocks weren't there, so averaging can still happen."""
    from .news import Flags, check_enabled, collect, screen
    if not buys or not check_enabled():
        return buys
    jev = None
    if os.getenv("AI_GATEWAY_API_KEY", "").strip() or os.getenv("TYPESAFE_API_KEY", "").strip():
        from .judges import JevJudge, JudgeError
        try:
            jev = JevJudge()
        except JudgeError:
            jev = None
    items, fresh = collect()
    if not fresh:
        notes.append("news check: the feeds couldn't be read just now, so it used the headlines collected earlier")
    flags, deadline, today = Flags(), time.time() + 150, ist_now().date()
    vetoed: set[str] = set()
    queue, passed = list(buys), []
    for _ in range(12):
        while queue and len(passed) < 3:  # only one gets bought; a few spares cover cash or fill problems
            b = queue.pop(0)
            why = screen(jev, b["symbol"], universe.get(b["symbol"], b["symbol"]), items, flags, today, deadline)
            if why:
                notes.append(f"skipped {b['symbol']}: {why}")
                vetoed.add(b["symbol"])
            else:
                passed.append(b)
        if passed or not vetoed:
            break
        again = strategy.decide([x for x in scan if x["symbol"] not in vetoed],
                                {k: v for k, v in held.items() if k not in vetoed}, buy_amount, avg_amount)
        queue = [x for x in again["buys"] if x["symbol"] not in vetoed]
        if not queue:
            break
    return passed


# ---------------------------------------------------------------- reporting

def _pnl(h: dict) -> float | None:
    return (h["ltp"] - h["avg"]) * h["qty"] if h.get("ltp") else None


def _print_scan(scan, held, decision, notes) -> None:
    console.print("\n  [bold]furthest below the DMA today[/]  [dim](★ = the 5 candidates)[/]")
    for i, x in enumerate(scan[:10]):
        star = "★" if i < strategy.SETTINGS["candidates"] and x["gap"] < 0 else " "
        own = f"  [dim]held · {held[x['symbol']]['lots']} lot(s)[/]" if x["symbol"] in held else ""
        console.print(f"   {star} {x['symbol']:<12} {x['gap']:+7.2%}  ₹{x['ltp']:>10,.2f}  (DMA ₹{x['dma']:,.2f}){own}")
    s, b = decision["sell"], decision["buys"]
    console.print(f"\n  would sell: [bold]{s['symbol']}[/] · {s['reason']}" if s else "\n  would sell: nothing")
    console.print(f"  would buy:  [bold]{b[0]['symbol']}[/] ({b[0]['kind']}) · {b[0]['reason']}" if b else "  would buy:  nothing")
    for n in notes:
        console.print(f"  [dim]· {n}[/]")


def _print_run(actions, notes, held, ledger) -> None:
    for a in actions:
        colour = "#3fd68a" if a["side"] == "buy" else "#8b7bff"
        extra = f" · profit {inr(a['pnl'], True)}" if a["side"] == "sell" else f" · {a['kind']}"
        console.print(f"  [{colour}]{a['side'].upper()}[/] {a['qty']} {a['symbol']} @ ₹{a['price']:,.2f}{extra} · {a['why']}")
    if not actions:
        console.print("  no trades today")
    for n in notes:
        console.print(f"  [dim]· {n}[/]")
    real, wins, closed = ledger.realised()
    open_pnl = sum(p for p in (_pnl(h) for h in held.values()) if p is not None)
    console.print(f"\n  holding {len(held)} stocks · invested {inr(ledger.invested())} · open P&L {inr(open_pnl, True)} · "
                  f"booked {inr(real, True)} from {closed} sells")


def _report(mode, actions, notes, held, ledger) -> str:
    lines = [f"🛒 Nifty Shop · {ist_now().strftime('%a %d %b')} · {mode}"]
    for a in actions:
        if a["side"] == "sell":
            lines.append(f"SOLD {a['qty']} {a['symbol']} @ ₹{a['price']:,.2f} · profit {inr(a['pnl'], True)}")
        else:
            lines.append(f"BOUGHT {a['qty']} {a['symbol']} @ ₹{a['price']:,.2f} ({a['kind']})")
    if not actions:
        lines.append("No trades today.")
    lines += [f"· {n}" for n in notes[:5]]
    real, _, closed = ledger.realised()
    open_pnl = sum(p for p in (_pnl(h) for h in held.values()) if p is not None)
    lines.append(f"Holding {len(held)} · invested {inr(ledger.invested())} · open {inr(open_pnl, True)} · "
                 f"booked {inr(real, True)} ({closed} sells)")
    return "\n".join(lines)


def status_text() -> str:
    """For Telegram's /status."""
    try:
        mode = live_mode()
    except FirstockError:
        mode = "paper"
    ledger = Ledger(mode)
    held = ledger.holdings()
    try:
        last = json.loads(STATUS.read_text()).get("prices", {})
    except (OSError, ValueError):
        last = {}
    for sym, h in held.items():
        h["ltp"] = last.get(sym)
    session = load_session()
    today = ist_now().date().isoformat()
    run = ledger.ran(today)
    lines = [f"Nifty Shop · {mode} · {'logged in ✅' if session else 'NOT logged in today ❌'}"
             + (" · kill switch ON 🛑" if STOP_FILE.exists() else ""),
             f"Today: {run['status'] if run else 'runs at 15:18'}"]
    for sym, h in sorted(held.items()):
        chg = f"{h['ltp'] / h['avg'] - 1:+.1%}" if h.get("ltp") else "?"
        lines.append(f"{sym}: {h['qty']} @ ₹{h['avg']:,.2f} ({h['lots']} lots) {chg}")
    real, _, closed = ledger.realised()
    lines.append(f"Invested {inr(ledger.invested())} · booked {inr(real, True)} ({closed} sells)")
    from .news import Flags
    for sym, f in sorted(Flags().all_active(ist_now().date()).items()):
        lines.append(f"🚫 {sym} not bought until {f['until']}: {f['why']}")
    return "\n".join(lines)


def _write_status(mode, ledger, scan, held, decision, actions, notes, scan_only: bool = False) -> None:
    real, wins, closed = ledger.realised()
    buy_amount, avg_amount, cap = amounts()
    payload = {
        "updated": time.time(), "mode": mode, "scan_only": scan_only, "strategy": strategy.DESCRIPTION,
        "settings": strategy.SETTINGS, "buy_amount": buy_amount, "average_amount": avg_amount, "max_capital": cap,
        "scan": scan, "decision": decision, "actions": actions, "notes": notes,
        "holdings": {s: {**h, "pnl": _pnl(h)} for s, h in held.items()},
        "prices": {x["symbol"]: x["ltp"] for x in scan} | {s: h["ltp"] for s, h in held.items() if h.get("ltp")},
        "invested": ledger.invested(), "realised": real, "wins": wins, "closed_count": closed,
        "closed": ledger.d["closed"][-60:], "runs": {d: ledger.d["runs"][d] for d in sorted(ledger.d["runs"])[-30:]},
        "news_flags": _flags_now(),
    }
    RESULTS.mkdir(exist_ok=True)
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, default=str))
    os.replace(tmp, STATUS)


def _flags_now() -> dict:
    from .news import Flags, check_enabled
    return Flags().all_active(ist_now().date()) if check_enabled() else {}


def news_watch(clear: str | None = None) -> None:
    """The hourly news job (`uv run python -m jevlab news`): collect headlines, put stocks with red-flag
    news on the watch-list, tell you on Telegram if one you hold gets flagged, and show the list."""
    from .news import Flags, check_enabled, cooloff_days, watch
    today = ist_now().date()
    if clear:
        sym = clear.strip().upper()
        found = Flags().clear(sym)
        console.print(f"  {sym} {'is off the news watch-list: the shop may buy it again' if found else 'was not on the news watch-list'}")
        return
    if not check_enabled():
        console.print("  the news check is switched off (NEWS_CHECK=off)")
        return
    universe, _ = nifty50()
    try:
        mode = live_mode()
    except FirstockError:
        mode = "paper"
    held = Ledger(mode).holdings()
    new, fresh, flags = watch(universe, list(held), today)
    console.print(f"  {fresh} headlines from the feeds just now" if fresh else "  [#f5b53d]the news feeds couldn't be read just now[/]")
    for sym, headline in new:
        console.print(f"  [#ff5d6c]flagged {sym}[/]: {headline}")
        if sym in held:
            telegram.send(f"⚠️ Serious news about {sym}, which the shop holds ({held[sym]['qty']} shares):\n“{headline}”\n"
                          f"The shop won't buy or average it for {cooloff_days()} days. It never sells on news: that's your call.")
    active = flags.all_active(today)
    if not active:
        console.print("  news watch-list: empty")
    for sym, f in sorted(active.items()):
        console.print(f"  🚫 {sym:<12} not bought until {f['until']} · {f['why']} ({f['by']}) · “{f['headline'][:70]}”")


def remind() -> None:
    """14:30 on trading days: nudge you on Telegram if you haven't logged in yet."""
    now = ist_now()
    if now.weekday() >= 5:
        return
    if load_session():
        console.print("  logged in today: no reminder needed")
        return
    msg = ("⏰ Nifty Shop: you haven't logged in to Firstock today. Send /login followed by the 6-digit code "
           "from your authenticator app before 15:15, or there's no trade today.")
    console.print(f"  {msg}")
    if not telegram.send(msg):
        console.print("  [dim](Telegram isn't set up, so this only went to the log)[/]")
