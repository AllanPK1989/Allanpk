"""Command-line jobs. GitHub Actions runs these on a schedule against the same database as the web app.

  python -m app.jobs news                      collect + triage news for everything followed
  python -m app.jobs digest --kind morning     build and send a digest (morning | evening | weekly)
  python -m app.jobs alerts                    check price moves / high-impact news, push alerts
  python -m app.jobs vapid-keys                print a new web-push key pair
  python -m app.jobs hash-password             hash the owner password for OWNER_PASSWORD_HASH
  python -m app.jobs seed-demo                 add a sample watchlist and portfolio (demo mode)
  python -m app.jobs test-email | test-push    send a test notification
"""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone

from .. import db as dbmod
from .. import services
from ..agent import alerts, digest
from ..config import get_settings
from ..data.market import get_market
from ..models import JobRun
from ..news import collect, summarize
from ..notify import email, push

log = logging.getLogger("jobs")

# In a public repository, GitHub Actions logs are public. PRIVATE_LOGS=1 keeps them free of anything
# that reveals what the owner follows or holds: only counts are printed and per-symbol warnings are muted.
PRIVATE = os.environ.get("PRIVATE_LOGS") == "1"


def _redact(detail):
    if not PRIVATE:
        return detail
    if isinstance(detail, dict):
        return {k: (len(v) if isinstance(v, list) else _redact(v)) for k, v in detail.items() if k != "title"}
    return detail


def _run(name: str, fn) -> int:
    dbmod.init_db()
    with dbmod.session_scope() as db:
        run = JobRun(job=name)
        db.add(run)
        db.commit()
        try:
            detail = fn(db)
            run.status, run.detail = "ok", json.dumps(detail, default=str)[:4000]
            print(json.dumps(_redact(detail), default=str, indent=2))
            code = 0
        except Exception as e:
            db.rollback()
            if PRIVATE:
                log.error("job %s failed: %s", name, type(e).__name__)
            else:
                log.exception("job %s failed", name)
            run = db.merge(run)
            run.status, run.detail = "error", f"{type(e).__name__}: {e}"[:4000]
            code = 1
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
    return code


def job_news(db):
    market = get_market()
    stats = collect.collect(db, market)
    db.commit()
    stats["triaged"] = summarize.summarize_pending(db)
    return stats


def job_digest(db, kind: str, send: bool):
    market = get_market()
    enabled = services.get_all_settings(db).get("digests_enabled", {})
    if enabled.get(kind) is False:
        return {"skipped": f"{kind} digest is turned off in settings"}
    news = collect.collect(db, market, days=7 if kind == "weekly" else 2)
    db.commit()
    news["triaged"] = summarize.summarize_pending(db)
    db.commit()
    d = digest.build(db, kind, market)
    db.commit()
    sent = digest.deliver(db, d) if send else {"emailed": False, "pushed": 0}
    return {"digest_id": d.id, "title": d.title, "ai": d.ai_generated, "news": news, **sent}


def job_alerts(db):
    market = get_market()
    news = collect.collect(db, market, days=1, per_instrument=4)
    db.commit()
    news["triaged"] = summarize.summarize_pending(db)
    found = alerts.check(db, market)
    db.commit()
    sent = alerts.deliver(db, found)
    return {"alerts": [a.title for a in found], "news": news, **sent}


def seed_demo(db):
    market = get_market()
    picks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "AAPL", "NVDA", "MF:122639", "MF:119551", "CRYPTO:BTC_USDT", "GC=F", "^NSEI"]
    added = []
    for sym in picks:
        r = next((x for x in market.search(sym) if x.symbol == sym), None)
        if r:
            inst = services.follow(db, r, source="watchlist", market=market)
            inst.pinned = sym in ("RELIANCE.NS", "CRYPTO:BTC_USDT", "^NSEI")
            added.append(sym)
    today = date.today()
    trades = [("RELIANCE.NS", 40, 0.82, 500), ("TCS.NS", 15, 0.9, 420), ("HDFCBANK.NS", 30, 0.95, 200),
              ("AAPL", 10, 0.8, 600), ("MF:122639", 1200, 0.7, 700), ("MF:119551", 3000, 0.9, 380),
              ("CRYPTO:BTC_USDT", 0.05, 0.75, 300)]
    for sym, qty, frac, days_ago in trades:
        inst = services.get_instrument(db, sym)
        if inst and not inst.transactions:
            px = market.quote(sym).price or 100
            services.add_transaction(db, inst, side="buy", quantity=qty, price=round(px * frac, 2),
                                     trade_date=today - timedelta(days=days_ago),
                                     fx_rate=83.0 if inst.currency == "USD" else None, note="demo")
    return {"followed": added, "demo": market.demo}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.ERROR if PRIVATE else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if PRIVATE:
        for noisy in ("yfinance", "app", "httpx", "anthropic"):
            logging.getLogger(noisy).setLevel(logging.CRITICAL)
        logging.getLogger("jobs").setLevel(logging.ERROR)
    p = argparse.ArgumentParser(prog="python -m app.jobs")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("news")
    d = sub.add_parser("digest")
    d.add_argument("--kind", choices=digest.KINDS, required=True)
    d.add_argument("--no-send", action="store_true", help="build and save, but don't email/push")
    sub.add_parser("alerts")
    sub.add_parser("vapid-keys")
    sub.add_parser("hash-password")
    sub.add_parser("seed-demo")
    sub.add_parser("init-db")
    sub.add_parser("test-email")
    sub.add_parser("test-push")
    a = p.parse_args(argv)

    if a.cmd == "vapid-keys":
        pub, priv = push.generate_vapid_keys()
        print(f"VAPID_PUBLIC_KEY={pub}\nVAPID_PRIVATE_KEY={priv}")
        return 0
    if a.cmd == "hash-password":
        from ..security import hash_password

        pw = getpass.getpass("Owner password: ")
        if len(pw) < 10:
            print("Use at least 10 characters.", file=sys.stderr)
            return 1
        if getpass.getpass("Again: ") != pw:
            print("Passwords differ.", file=sys.stderr)
            return 1
        print(f"OWNER_PASSWORD_HASH={hash_password(pw)}")
        return 0
    if a.cmd == "init-db":
        dbmod.init_db()
        print("tables ready")
        return 0
    if a.cmd == "test-email":
        ok = email.send(f"{get_settings().app_name}: test email", "<p>Email delivery works.</p>", "Email delivery works.")
        print("sent" if ok else "not sent (check GMAIL_USER / GMAIL_APP_PASSWORD)")
        return 0 if ok else 1
    if a.cmd == "test-push":
        return _run("test-push", lambda db: {"sent": push.send_all(db, title="Test notification", body="Push works.", url="/")})
    if a.cmd == "news":
        return _run("news", job_news)
    if a.cmd == "digest":
        return _run(f"digest-{a.kind}", lambda db: job_digest(db, a.kind, not a.no_send))
    if a.cmd == "alerts":
        return _run("alerts", job_alerts)
    if a.cmd == "seed-demo":
        return _run("seed-demo", seed_demo)
    return 2


if __name__ == "__main__":
    sys.exit(main())
