"""Firstock: the daily login, prices and candles, holdings, and delivery (CNC) orders.

Everything talks to Firstock's developer API (the same endpoints the official
`firstock` Python SDK uses): https://api.firstock.in/V1/<endpoint>, JSON in and out.

The daily login: SEBI's rules end every API session each day, and a login needs
your 2FA code. So once each trading day you log in (from the terminal with
`uv run python -m jevlab login`, or by sending `/login 123456` to your Telegram
bot). The session token is saved in results/session.json (readable only by you)
and is valid until the day ends.

Orders are delivery (CNC, product "C") limit orders priced a little through the
market, so they fill at once but never at a crazy price. At most one order action
a second: far below the 10 orders a second at which SEBI treats you as a
registered algo. Selling shares from your demat needs DDPI (or eDIS) switched on
in your Firstock account.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from datetime import date, datetime, time as dtime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

from .core import IST, RESULTS, ist_now

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_URL = "https://api.firstock.in/V1"
EXCHANGE = "NSE"
DELIVERY = "C"  # Firstock's product code for delivery (CNC): the shares go into your demat account
REMARK = "jev-shop"  # tags the bot's orders
SESSION_FILE = RESULTS / "session.json"
LIVE_PHRASE = "I accept the risk of trading real money"
DONE = ("COMPLETE", "REJECTED", "CANCELED")

# NSE delivery charges. Approximate: check firstock.in/support/charges and your contract notes.
BROKERAGE = 0.0           # Firstock charges no brokerage on equity delivery
STT = 0.001               # securities transaction tax, 0.1% on buy and sell
EXCHANGE_TXN = 0.0000297  # NSE transaction charge
SEBI_FEE = 0.000001       # ₹10 per crore
STAMP_BUY = 0.00015       # stamp duty, buy side only
GST = 0.18                # on brokerage, exchange, SEBI and DP charges
DP_CHARGE = float(os.getenv("DP_CHARGE_INR", "15"))  # depository charge per stock sold per day, before GST


def charges(side: str, value: float) -> float:
    """Everything one delivery order costs, in rupees: brokerage, STT, exchange, SEBI, stamp duty, DP charge, GST."""
    fixed = BROKERAGE + EXCHANGE_TXN * value + SEBI_FEE * value + (DP_CHARGE if side == "sell" else 0.0)
    tax = STT * value + (STAMP_BUY * value if side == "buy" else 0.0)
    return fixed + tax + GST * fixed


class FirstockError(Exception):
    pass


class SessionExpired(FirstockError):
    pass


_EXPIRED = re.compile(r"session (has )?expired|invalid session|session is invalid|jkey|not logged in|please login|"
                      r"login again", re.I)
_IP = re.compile(r"\bip\b|whitelist|static", re.I)  # an IP rejection is not an expired session
_EMPTY = re.compile(r"no data|not found|no record|no position|no order|no holding", re.I)
_lock = threading.Lock()
_last_order = [0.0]


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _message(d) -> str:
    if not isinstance(d, dict):
        return str(d)[:200]
    err = d.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)[:200]
    return str(d.get("message") or err or d.get("emsg") or "")[:200]


def _post(path: str, body: dict, timeout: float = 15.0):
    try:
        r = requests.post(f"{API_URL}/{path}", json=body, timeout=timeout)
    except requests.RequestException as exc:
        raise FirstockError(f"can't reach Firstock: {str(exc)[:120]}") from exc
    try:
        data = r.json()
    except ValueError:
        raise FirstockError(f"HTTP {r.status_code}: {r.text[:160]}")
    if not isinstance(data, dict) or str(data.get("status", "")).lower() != "success":
        msg = _message(data) or f"HTTP {r.status_code}"
        if (r.status_code == 401 or _EXPIRED.search(msg)) and not _IP.search(msg) and path != "login":
            raise SessionExpired(msg)
        raise FirstockError(msg)
    return data.get("data", {})


# ---------------------------------------------------------------- login and session

def credentials() -> dict:
    names = {"userId": "FIRSTOCK_USER_ID", "password": "FIRSTOCK_PASSWORD",
             "apiKey": "FIRSTOCK_API_KEY", "vendorCode": "FIRSTOCK_VENDOR_CODE"}
    out = {k: os.getenv(v, "").strip() for k, v in names.items()}
    missing = [names[k] for k, v in out.items() if not v]
    if missing:
        raise FirstockError("missing from .env: " + ", ".join(missing))
    return out


def write_private(path, text: str) -> None:
    RESULTS.mkdir(exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


class Session:
    """A logged-in Firstock session: every API call carries the user ID and the session token (jKey)."""

    def __init__(self, user_id: str, jkey: str, name: str = ""):
        self.user_id, self.jkey, self.name = user_id, jkey, name

    def post(self, path: str, timeout: float = 15.0, **fields):
        try:
            return _post(path, {"userId": self.user_id, "jKey": self.jkey, **fields}, timeout)
        except SessionExpired:
            forget_session()  # so nothing retries a dead token; log in again
            raise

    def rows(self, path: str, **fields) -> list[dict]:
        """A list endpoint (orders, holdings). An empty book comes back as an error, which means []."""
        try:
            data = self.post(path, **fields)
        except SessionExpired:
            raise
        except FirstockError as exc:
            if _EMPTY.search(str(exc)):
                return []
            raise
        return data if isinstance(data, list) else [data] if isinstance(data, dict) and data else []


def login(totp: str) -> Session:
    c = credentials()
    code = re.sub(r"\s", "", totp or "")
    if not re.fullmatch(r"\d{6}", code):
        raise FirstockError("the 2FA code should be the 6 digits from your authenticator app")
    body = {"userId": c["userId"], "password": hashlib.sha256(c["password"].encode()).hexdigest(),
            "TOTP": code, "vendorCode": c["vendorCode"], "apiKey": c["apiKey"]}
    data = _post("login", body, timeout=20)
    token = data.get("susertoken") if isinstance(data, dict) else None
    if not token:
        raise FirstockError("Firstock accepted the login but sent no session token")
    name = str(data.get("userName") or c["userId"])
    write_private(SESSION_FILE, json.dumps({"userId": c["userId"], "jKey": token, "name": name,
                                            "date": ist_now().date().isoformat()}))
    return Session(c["userId"], token, name)


def load_session() -> Session | None:
    """Today's session, if you've logged in today. Sessions end every day, so yesterday's is useless."""
    try:
        d = json.loads(SESSION_FILE.read_text())
    except (OSError, ValueError):
        return None
    if d.get("date") != ist_now().date().isoformat() or not d.get("jKey"):
        return None
    return Session(d["userId"], d["jKey"], d.get("name", ""))


def forget_session() -> None:
    try:
        SESSION_FILE.unlink()
    except OSError:
        pass


def logout(session: Session) -> None:
    try:
        session.post("logout")
    finally:
        forget_session()


def live_mode() -> str:
    """'paper' (default) or 'live'. Live is refused unless JEV_LIVE_CONFIRM is the exact phrase."""
    mode = os.getenv("FIRSTOCK_MODE", "paper").strip().lower() or "paper"
    if mode not in ("paper", "live"):
        raise FirstockError(f"FIRSTOCK_MODE must be 'paper' or 'live', not '{mode}'")
    if mode == "live" and os.getenv("JEV_LIVE_CONFIRM", "").strip() != LIVE_PHRASE:
        raise FirstockError("FIRSTOCK_MODE=live, but JEV_LIVE_CONFIRM isn't set to the exact confirmation phrase. "
                            "Refusing to trade real money.")
    return mode


def public_ip() -> str | None:
    try:
        return requests.get("https://api.ipify.org", timeout=6).text.strip() or None
    except requests.RequestException:
        return None


# ---------------------------------------------------------------- market data

def trading_symbol(symbol: str) -> str:
    """RELIANCE -> RELIANCE-EQ (the NSE equity series). Anything with a dash (and NIFTY) is left alone."""
    s = symbol.strip().upper()
    return s if "-" in s or s == "NIFTY" else f"{s}-EQ"


def security_info(session: Session, tsym: str) -> dict:
    d = session.post("securityInfo", exchange=EXCHANGE, tradingSymbol=tsym)
    if not isinstance(d, dict) or not d.get("token"):
        raise FirstockError(f"Firstock doesn't know {EXCHANGE}:{tsym}")
    return {"token": str(d["token"]), "tick": _f(d.get("tickSize"), 0.05) or 0.05, "name": d.get("symbolName") or tsym}


def quote(session: Session, tsym: str) -> dict:
    d = session.post("getQuote", exchange=EXCHANGE, tradingSymbol=tsym)
    return {"ltp": _f(d.get("lastTradedPrice")), "bid": _f(d.get("bestBuyPrice1")), "ask": _f(d.get("bestSellPrice1")),
            "open": _f(d.get("dayOpenPrice")), "prev_close": _f(d.get("dayClosePrice")),
            "tick": _f(d.get("tickSize"), 0.0), "name": d.get("companyName") or tsym}


def ltps(session: Session, tsyms: list[str]) -> dict[str, float]:
    """Last traded prices for many stocks: one multi-quote call per 25 stocks, one-by-one for any it misses."""
    out: dict[str, float] = {}
    for i in range(0, len(tsyms), 25):
        chunk = tsyms[i:i + 25]
        try:
            rows = session.post("getMultiQuotes/ltp", data=[{"exchange": EXCHANGE, "tradingSymbol": t} for t in chunk])
            for r in rows if isinstance(rows, list) else []:
                if _f(r.get("lastTradedPrice")) > 0:
                    out[r.get("tradingSymbol")] = _f(r.get("lastTradedPrice"))
        except SessionExpired:
            raise
        except FirstockError:
            pass
    for t in tsyms:
        if t not in out:
            try:
                px = quote(session, t)["ltp"]
            except SessionExpired:
                raise
            except FirstockError:
                continue
            if px > 0:
                out[t] = px
            time.sleep(0.05)
    return out


def daily_candles(session: Session, tsym: str, start: date, end: date | None = None) -> pd.DataFrame:
    """Daily OHLCV, indexed by date (IST). Asks for a year at a time."""
    end = end or ist_now().date()
    frames, t0 = [], start
    fmt = "%H:%M:%S %d-%m-%Y"
    while t0 <= end:
        t1 = min(end, t0 + timedelta(days=364))
        rows = session.post("timePriceSeries", timeout=30, exchange=EXCHANGE, tradingSymbol=tsym, interval="1d",
                            startTime=datetime.combine(t0, dtime(9, 15)).strftime(fmt),
                            endTime=datetime.combine(t1, dtime(15, 30)).strftime(fmt))
        frames.append(_rows_to_frame(rows if isinstance(rows, list) else []))
        t0 = t1 + timedelta(days=1)
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.concat(frames)
    return df[~df.index.duplicated(keep="last")].sort_index()


def _rows_to_frame(rows: list[dict]) -> pd.DataFrame:
    out = []
    for r in rows:
        day = None
        epoch = _f(r.get("epochTime") or r.get("ssboe"))
        if epoch:
            day = pd.Timestamp(epoch / (1000 if epoch > 1e11 else 1), unit="s", tz="UTC").tz_convert(IST).date()
        elif r.get("time"):
            try:
                day = pd.to_datetime(r["time"], dayfirst=True).date()
            except (ValueError, TypeError):
                day = None
        if day is not None and _f(r.get("close")) > 0:
            out.append((day, _f(r.get("open")), _f(r.get("high")), _f(r.get("low")), _f(r.get("close")), _f(r.get("volume"))))
    return pd.DataFrame(out, columns=["day", "open", "high", "low", "close", "volume"]).set_index("day")


# ---------------------------------------------------------------- account and orders (live mode only)

def cash(session: Session) -> float | None:
    d = session.post("limit")
    return _f(d.get("cash")) if isinstance(d, dict) and d.get("cash") is not None else None


def holdings(session: Session) -> dict[str, dict]:
    """Shares in your demat you can sell today: {tradingSymbol: {"qty": int, "avg": float}}."""
    out: dict[str, dict] = {}
    for r in session.rows("holdingsDetails"):
        syms = [s.get("tradingSymbol") for s in r.get("exchangeTradingSymbol") or [] if s.get("exchange", EXCHANGE) == EXCHANGE]
        tsym = syms[0] if syms else r.get("tradingSymbol")
        if not tsym:
            continue
        qty = int(_f(r.get("holdQuantity")) + _f(r.get("BTSTQuantity")) - _f(r.get("usedQuantity")))
        out[tsym] = {"qty": max(0, qty), "avg": _f(r.get("uploadPrice"))}
    return out


def _throttle() -> None:
    with _lock:
        wait = _last_order[0] + 1.0 - time.time()  # at most one order action a second
        if wait > 0:
            time.sleep(wait)
        _last_order[0] = time.time()


def round_to_tick(px: float, tick: float, up: bool) -> float:
    steps = px / tick
    return round((math.ceil(steps - 1e-9) if up else math.floor(steps + 1e-9)) * tick, 2)


def place_limit(session: Session, tsym: str, side: str, qty: int, px: float) -> str:
    _throttle()
    d = session.post("placeOrder", exchange=EXCHANGE, tradingSymbol=tsym, quantity=str(int(qty)), price=f"{px:.2f}",
                     product=DELIVERY, transactionType="B" if side == "buy" else "S", priceType="LMT",
                     retention="DAY", triggerPrice="0", remarks=REMARK)
    oid = str(d.get("orderNumber") or "") if isinstance(d, dict) else ""
    if not oid:
        raise FirstockError(f"no order number in Firstock's reply: {str(d)[:120]}")
    return oid


def order(session: Session, oid: str) -> dict:
    """Current state of one order: status, shares filled, average fill price, reject reason."""
    rows = session.rows("singleOrderHistory", orderNumber=oid)
    if not rows:
        rows = [r for r in session.rows("orderBook") if str(r.get("orderNumber")) == oid]
    if not rows:
        return {"status": "UNKNOWN", "filled": 0, "avg_px": 0.0, "reason": ""}
    statuses = [str(r.get("status", "")).upper().replace("CANCELLED", "CANCELED") for r in rows]
    status = next((s for s in DONE if s in statuses), statuses[0])
    filled = int(max(_f(r.get("fillShares")) for r in rows))
    avg = next((_f(r.get("averagePrice")) for r in rows
                if int(_f(r.get("fillShares"))) == filled and _f(r.get("averagePrice"))), 0.0)
    reason = next((r.get("rejectReason") for r in rows if r.get("rejectReason")), "")
    return {"status": status, "filled": filled, "avg_px": avg, "reason": str(reason)[:160]}


def cancel(session: Session, oid: str) -> None:
    try:
        _throttle()
        session.post("cancelOrder", orderNumber=oid)
    except SessionExpired:
        raise
    except FirstockError:
        pass  # already filled or gone


def execute(session: Session, tsym: str, side: str, qty: int, ref_px: float) -> dict:
    """Buy or sell `qty` shares for delivery with a limit order priced 0.5% through the last price
    (then 1% once, if the first try doesn't fill in 30 seconds). Returns what actually filled."""
    try:
        tick = security_info(session, tsym)["tick"]
    except FirstockError:
        tick = 0.05
    remaining, fills, reason = qty, [], ""
    for width in (0.005, 0.01):
        if remaining <= 0:
            break
        px = round_to_tick(ref_px * (1 + width) if side == "buy" else ref_px * (1 - width), tick, up=(side == "buy"))
        oid = place_limit(session, tsym, side, remaining, px)
        o = {"status": "", "filled": 0, "avg_px": 0.0, "reason": ""}
        for _ in range(30):
            time.sleep(1)
            o = order(session, oid)
            if o["status"] in DONE:
                break
        if o["status"] not in DONE:
            cancel(session, oid)
            time.sleep(1)
            o = order(session, oid)
        if o["filled"]:
            fills.append((o["filled"], o["avg_px"] or px))
            remaining -= o["filled"]
        if o["status"] == "REJECTED":
            reason = o["reason"] or "rejected"
            break
    done = qty - remaining
    avg = sum(q * p for q, p in fills) / done if done else 0.0
    return {"qty": done, "avg_px": round(avg, 2), "missed": remaining, "reason": reason}
