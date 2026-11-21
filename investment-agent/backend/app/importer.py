"""Import trades/holdings from broker CSV exports.

Recognised formats (by header row):
  * Generic:            symbol, side, quantity, price, date [, fees, fx_rate, name]
  * Zerodha tradebook:  symbol, isin, trade_date, exchange, ..., trade_type, quantity, price
  * Zerodha holdings:   Instrument, Qty., Avg. cost            (no dates: today's date is used)
  * Groww holdings:     Stock Name, ISIN, Quantity, Average buy price   (resolved by ISIN search)
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from . import services
from .data.market import MarketData

MAX_ROWS = 5000
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d %b %Y", "%m/%d/%Y")


def _norm(h: str) -> str:
    return "".join(ch for ch in h.strip().lower() if ch.isalnum())


def _date(s: str) -> date:
    raw = (s or "").strip()
    for candidate in (raw, raw.split("T")[0], raw.split(" ")[0]):
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
    raise ValueError(f"unrecognised date '{raw}'")


def _num(s: Any) -> float:
    return float(str(s).replace(",", "").replace("₹", "").strip() or 0)


def detect(headers: list[str]) -> str:
    h = {_norm(x) for x in headers}
    if {"symbol", "tradetype", "tradedate", "quantity", "price"} <= h:
        return "zerodha_tradebook"
    if {"instrument", "qty", "avgcost"} <= h:
        return "zerodha_holdings"
    if {"stockname", "isin", "quantity", "averagebuyprice"} <= h:
        return "groww_holdings"
    if {"symbol", "quantity", "price"} <= h and ({"date"} & h or {"tradedate"} & h):
        return "generic"
    raise ValueError("Unrecognised CSV. Expected columns like: symbol, side, quantity, price, date")


def parse(text: str) -> tuple[str, list[dict[str, Any]]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames:
        raise ValueError("Empty CSV")
    fmt = detect(reader.fieldnames)
    rows = []
    for n, raw in enumerate(reader, start=2):
        if n > MAX_ROWS + 1:
            raise ValueError(f"Too many rows (max {MAX_ROWS})")
        r = {_norm(k): (v or "").strip() for k, v in raw.items() if k}
        if not any(r.values()):
            continue
        try:
            rows.append(_row(fmt, r))
        except (ValueError, KeyError) as e:
            raise ValueError(f"Row {n}: {e}") from e
    return fmt, rows


def _row(fmt: str, r: dict[str, str]) -> dict[str, Any]:
    if fmt == "zerodha_tradebook":
        sym = r["symbol"].upper()
        suffix = ".BO" if r.get("exchange", "").upper() == "BSE" else ".NS"
        return {"symbol": sym + suffix, "side": r["tradetype"].lower(), "quantity": _num(r["quantity"]),
                "price": _num(r["price"]), "trade_date": _date(r["tradedate"]), "fees": 0.0, "isin": r.get("isin", "")}
    if fmt == "zerodha_holdings":
        return {"symbol": r["instrument"].upper().replace("-BE", "") + ".NS", "side": "buy", "quantity": _num(r["qty"]),
                "price": _num(r["avgcost"]), "trade_date": date.today(), "fees": 0.0, "undated": True}
    if fmt == "groww_holdings":
        return {"isin": r["isin"], "name": r["stockname"], "symbol": "", "side": "buy", "quantity": _num(r["quantity"]),
                "price": _num(r["averagebuyprice"]), "trade_date": date.today(), "fees": 0.0, "undated": True}
    side = (r.get("side") or r.get("type") or r.get("tradetype") or "buy").lower()
    side = {"b": "buy", "s": "sell", "purchase": "buy", "redeem": "sell", "redemption": "sell"}.get(side, side)
    return {"symbol": r["symbol"].strip(), "side": side, "quantity": _num(r["quantity"]), "price": _num(r["price"]),
            "trade_date": _date(r.get("date") or r.get("tradedate", "")), "fees": _num(r.get("fees") or 0),
            "fx_rate": _num(r["fxrate"]) if r.get("fxrate") else None, "name": r.get("name", "")}


def import_csv(db: Session, text: str, market: MarketData) -> dict[str, Any]:
    fmt, rows = parse(text)
    added, skipped, warnings = 0, [], []
    cache: dict[str, Any] = {}
    for r in rows:
        key = r["symbol"] or r.get("isin", "")
        if key not in cache:
            inst = services.get_instrument(db, r["symbol"]) if r["symbol"] else None
            if inst is None:
                query = r["symbol"] or r.get("isin") or r.get("name", "")
                results = market.search(query)
                exact = next((x for x in results if x.symbol.upper() == r["symbol"].upper()), None) if r["symbol"] else None
                pick = exact or (results[0] if results else None)
                inst = services.follow(db, pick, source="portfolio", market=market) if pick else None
            cache[key] = inst
        inst = cache[key]
        if inst is None:
            skipped.append(key)
            continue
        try:
            services.add_transaction(db, inst, side=r["side"], quantity=r["quantity"], price=r["price"],
                                     trade_date=r["trade_date"], fees=r.get("fees") or 0.0, fx_rate=r.get("fx_rate"),
                                     note=f"imported ({fmt})")
            added += 1
        except ValueError as e:
            skipped.append(f"{key}: {e}")
    if any(r.get("undated") for r in rows):
        warnings.append("This export has no purchase dates, so today's date was used. Holding periods (tax) and "
                        "XIRR will be wrong until you edit the dates or import a tradebook instead.")
    return {"format": fmt, "added": added, "skipped": skipped, "warnings": warnings}
