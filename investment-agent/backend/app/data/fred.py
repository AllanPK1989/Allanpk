"""Macro series from FRED's public CSV download (no API key needed for fredgraph.csv)."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime

import pandas as pd

from . import http
from .cache import ttl_cache

log = logging.getLogger(__name__)
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# series id -> (label, kind) ; kind "level" = show latest value, "yoy" = show % change over 12 months
SERIES = {
    "DGS10": ("US 10Y Treasury yield %", "level"),
    "DFF": ("US Fed funds rate %", "level"),
    "CPIAUCSL": ("US CPI inflation % YoY", "yoy"),
    "UNRATE": ("US unemployment %", "level"),
    "INDCPIALLMINMEI": ("India CPI inflation % YoY", "yoy"),
    "INDIRLTLT01STM": ("India 10Y G-Sec yield % (monthly)", "level"),
    "DEXINUS": ("USD/INR (FRED daily)", "level"),
}


def parse_csv(text: str) -> pd.Series:
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        return pd.Series(dtype=float)
    data = {}
    for r in rows[1:]:
        if len(r) < 2 or r[1] in ("", "."):
            continue
        try:
            data[datetime.strptime(r[0], "%Y-%m-%d")] = float(r[1])
        except ValueError:
            continue
    return pd.Series(data, dtype=float).sort_index()


@ttl_cache(6 * 3600)
def series(series_id: str) -> pd.Series:
    try:
        r = http.client().get(URL, params={"id": series_id})
        r.raise_for_status()
        return parse_csv(r.text)
    except Exception as e:
        log.warning("FRED %s failed: %s", series_id, e)
        return pd.Series(dtype=float)


def latest(series_id: str) -> dict | None:
    s = series(series_id)
    if s.empty:
        return None
    label, kind = SERIES.get(series_id, (series_id, "level"))
    if kind == "yoy":
        if len(s) < 13:
            return None
        last_date = s.index[-1]
        base = s[s.index <= last_date - pd.DateOffset(months=12)]
        if base.empty:
            return None
        value = (s.iloc[-1] / base.iloc[-1] - 1) * 100
    else:
        value = float(s.iloc[-1])
    prev = None
    if kind == "level" and len(s) > 1:
        prev = float(s.iloc[-2])
    return {"id": series_id, "label": label, "value": round(float(value), 3), "prev": prev,
            "date": s.index[-1].strftime("%Y-%m-%d")}
