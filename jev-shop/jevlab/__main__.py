"""jev-starter, Nifty Shop edition: a once-a-day Nifty 50 dip-buying bot on Firstock.

  uv run python -m jevlab login             # once each trading day: the 6-digit code from your authenticator app
  uv run python -m jevlab check             # test the setup: Firstock, prices, the Nifty 50 list, news, Jev, Telegram
  uv run python -m jevlab scan              # any time: today's ranking and what the shop would do (no orders)
  uv run python -m jevlab backtest          # what the rules would have done over the last 5 years
  uv run python -m jevlab run               # the daily run, 15:15 to 15:29 IST (paper unless you chose live)
  uv run python -m jevlab report            # what you hold, and the profit so far
  uv run python -m jevlab dashboard         # the same, in the browser
  uv run python -m jevlab telegram          # listen for /login, /status, /stop, /resume on Telegram
  uv run python -m jevlab telegram-id       # find your Telegram chat ID (message your bot first)
  uv run python -m jevlab remind            # Telegram nudge if you haven't logged in today (the server runs it at 14:30)
  uv run python -m jevlab news              # read the news now: flag stocks with serious bad news (the server runs it hourly)
  uv run python -m jevlab news --clear INFY # take a stock off the news watch-list, if you disagree
  uv run python -m jevlab logout            # end today's Firstock session early

Flags: --paper (run: paper mode whatever .env says) · --years 10 (backtest) · --totp 123456 (login) ·
       --port 8766 · --no-open
"""

from __future__ import annotations

import argparse
import os
import sys
import threading

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def login_cmd(totp: str | None) -> None:
    from .core import console
    from .firstock import FirstockError, login
    if not totp:
        if not sys.stdin.isatty():
            raise SystemExit("  no terminal to type into: run it as  uv run python -m jevlab login --totp 123456")
        totp = input("  6-digit code from your authenticator app: ").strip()
    try:
        session = login(totp)
    except FirstockError as exc:
        msg = str(exc)
        hint = (" (the code changes every 30 seconds: use a fresh one)" if "otp" in msg.lower()
                else " (check FIRSTOCK_USER_ID, FIRSTOCK_PASSWORD, FIRSTOCK_API_KEY and FIRSTOCK_VENDOR_CODE in .env)")
        raise SystemExit(f"  Firstock said no: {msg}{hint}")
    console.print(f"  logged in to Firstock as [bold]{session.name}[/] · the session lasts until the end of today  [#3fd68a]ok[/]")


def logout_cmd() -> None:
    from .core import console
    from .firstock import FirstockError, forget_session, load_session, logout
    session = load_session()
    if not session:
        forget_session()
        console.print("  not logged in today")
        return
    try:
        logout(session)
    except FirstockError:
        pass
    console.print("  logged out of Firstock  [#3fd68a]ok[/]")


def check() -> None:
    from .core import console, inr, ist_now
    from .firstock import FirstockError, cash, credentials, live_mode, load_session, ltps, public_ip
    from .judges import JevJudge, JudgeError
    from .news import FEEDS, Flags, check_enabled, collect
    from .shop import amounts
    from .universe import nifty50
    from . import telegram

    ok = "[#3fd68a]ok[/]"
    console.print("  [bold]1. Firstock[/]")
    session = None
    try:
        credentials()
    except FirstockError as exc:
        console.print(f"     [#f5b53d]not set up yet[/]: {exc}")
    else:
        session = load_session()
        if not session:
            console.print("     [#f5b53d]not logged in today[/]: run [bold]uv run python -m jevlab login[/] "
                          "and type the 6-digit code from your authenticator app")
    if session:
        try:
            px = ltps(session, ["RELIANCE-EQ", "NIFTY"])
            console.print(f"     logged in as {session.name} · RELIANCE {inr(px.get('RELIANCE-EQ', 0))} · "
                          f"NIFTY {px.get('NIFTY', 0):,.2f}  {ok}")
        except FirstockError as exc:
            console.print(f"     [#ff5d6c]Firstock said no[/]: {str(exc)[:140]}")
    now = ist_now()
    console.print(f"     it's {now.strftime('%a %H:%M')} IST · the shop runs on trading days at 15:18")
    console.print("  [bold]2. The Nifty 50 list[/]")
    stocks, source = nifty50()
    console.print(f"     {len(stocks)} stocks from {source}  " + (ok if source in ("NSE", "cache") else "[#f5b53d]check[/]"))
    console.print("  [bold]3. News check[/]")
    if not check_enabled():
        console.print("     [#f5b53d]switched off[/] (NEWS_CHECK=off): the shop buys without looking at the news")
    else:
        _, fresh = collect(quiet=False)
        console.print(f"     {fresh} headlines from {len(FEEDS)} feeds · red-flag words on (fraud, SEBI ban, raids, insolvency…)  {ok}"
                      if fresh else "     no headlines from the feeds  [#f5b53d]check your internet[/] (the check can't see news)")
        try:
            jev = JevJudge()
            q = {"x": {"type": "choice", "instructions": "Is this serious bad news for the company?",
                       "criteria": {"serious_bad_news": None, "not_serious": None}}}
            _, meta = jev.ask({"headline": "SEBI bars company promoters from the market over fraud"}, q, timeout=15, retries=2)
            console.print(f"     Jev reads each headline too (answered in {meta['latency_ms']} ms)  {ok}")
        except JudgeError as exc:
            msg = str(exc)
            console.print("     [#f5b53d]Jev's layer is off[/]: add AI_GATEWAY_API_KEY to .env so Jev reads each headline too "
                          "(the free tier is plenty)" if "no AI_GATEWAY" in msg else f"     [#ff5d6c]Jev failed[/]: {msg[:120]}")
        flagged = Flags().all_active(now.date())
        if flagged:
            listed = ", ".join(f"{sym} (until {f['until']})" for sym, f in sorted(flagged.items()))
            console.print(f"     on the news watch-list: {listed}")
    console.print("  [bold]4. Telegram (optional)[/]")
    if telegram.enabled():
        console.print(f"     test message sent  {ok}" if telegram.send("✅ jev-shop check: Telegram works.")
                      else "     [#ff5d6c]couldn't send[/]: check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    else:
        console.print("     not set up (reports go to the log only)")
    console.print("  [bold]5. Trading[/]")
    buy, avg, cap = amounts()
    try:
        mode = live_mode()
        console.print(f"     mode [bold]{mode.upper()}[/]" + (" (simulated fills: no orders are sent)" if mode == "paper"
                                                                else " · [bold #ff5d6c]REAL MONEY[/]")
                      + f" · {inr(buy)} a buy · {inr(avg)} an average · cap {inr(cap)}")
    except FirstockError as exc:
        console.print(f"     [#ff5d6c]{exc}[/]")
    if session:
        try:
            c = cash(session)
            console.print(f"     cash in Firstock {inr(c)}  {ok}" if c is not None else f"     account readable  {ok}")
        except FirstockError as exc:
            console.print(f"     [dim]couldn't read the account: {str(exc)[:100]}[/]")
    ip = public_ip()
    console.print(f"     this machine's public IP is [bold]{ip}[/]. Firstock only accepts API orders from the static IP "
                  "you registered with them" if ip else "     [dim](couldn't look up this machine's public IP)[/]")


def report_cmd() -> None:
    import json
    from .core import console, inr
    from .firstock import FirstockError, live_mode, load_session, ltps, trading_symbol
    from .ledger import Ledger
    try:
        mode = live_mode()
    except FirstockError:
        mode = "paper"
    ledger = Ledger(mode)
    held = ledger.holdings()
    prices = {}
    session = load_session()
    if session and held:
        try:
            got = ltps(session, [trading_symbol(s) for s in held])
            prices = {s: got.get(trading_symbol(s)) for s in held}
        except FirstockError:
            prices = {}
    if not prices:
        from .shop import STATUS
        try:
            prices = json.loads(STATUS.read_text()).get("prices", {})
        except (OSError, ValueError):
            prices = {}
    console.print(f"  [bold]Nifty Shop · {mode}[/] · {len(held)} holdings" + ("" if session else " · [dim]last known prices[/]"))
    open_pnl = 0.0
    for sym, h in sorted(held.items()):
        p = prices.get(sym)
        chg = f"{p / h['avg'] - 1:+6.1%}" if p else "     ?"
        if p:
            open_pnl += (p - h["avg"]) * h["qty"]
        console.print(f"   {sym:<12} {h['qty']:>5} sh · avg ₹{h['avg']:>10,.2f} · now {('₹' + format(p, ',.2f')) if p else '?':>11} "
                      f"· {chg} · {h['lots']} lot(s) since {h['first_buy']}")
    real, wins, closed = ledger.realised()
    console.print(f"  invested {inr(ledger.invested())} · open P&L {inr(open_pnl, True)} · booked {inr(real, True)} "
                  f"from {closed} sells ({wins} with a profit)")


def main() -> None:
    ap = argparse.ArgumentParser(prog="jevlab")
    ap.add_argument("command", choices=["check", "login", "logout", "scan", "run", "backtest", "report", "dashboard",
                                        "telegram", "telegram-id", "remind", "news"])
    ap.add_argument("--paper", action="store_true", help="run: paper mode (simulated fills), whatever .env says")
    ap.add_argument("--years", type=float, default=5.0, help="backtest: how many years back")
    ap.add_argument("--totp", default=None, help="login: the 6-digit code from your authenticator app")
    ap.add_argument("--clear", default=None, metavar="SYMBOL", help="news: take a stock off the news watch-list")
    ap.add_argument("--port", type=int, default=8765, help="dashboard port")
    ap.add_argument("--no-open", action="store_true", help="don't open the dashboard in a browser")
    a = ap.parse_args()
    from .core import console

    if a.command == "login":
        login_cmd(a.totp)
    elif a.command == "logout":
        logout_cmd()
    elif a.command == "check":
        console.print("[bold #8b7bff]jev-shop[/] [dim]· the Nifty Shop on Firstock[/]")
        check()
    elif a.command in ("scan", "run"):
        from .shop import run_shop
        sys.exit(run_shop(force_paper=a.paper, scan_only=(a.command == "scan")))
    elif a.command == "backtest":
        from .backtest import run_backtest
        run_backtest(a.years)
    elif a.command == "report":
        report_cmd()
    elif a.command == "remind":
        from .shop import remind
        remind()
    elif a.command == "news":
        from .shop import news_watch
        news_watch(a.clear)
    elif a.command == "telegram":
        from .telegram import listen
        listen()
    elif a.command == "telegram-id":
        from .telegram import whoami
        whoami()
    elif a.command == "dashboard":
        from .server import serve
        serve(a.port, not a.no_open)
        console.print("  [dim]dashboard open · Ctrl+C to stop[/]")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
