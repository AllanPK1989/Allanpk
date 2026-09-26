"""The Nifty 50: which stocks the shop looks at.

The list changes twice a year, so it's downloaded from NSE and cached for a week.
If NSE can't be reached, the last good download is used, and failing that the list
below (correct as of late 2025, and possibly out of date).
"""

from __future__ import annotations

import csv
import io
import json
import time

import requests

from .core import RESULTS

URLS = [
    "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
]
CACHE = RESULTS / "nifty50.json"
FALLBACK = {
    "ADANIENT": "Adani Enterprises", "ADANIPORTS": "Adani Ports", "APOLLOHOSP": "Apollo Hospitals",
    "ASIANPAINT": "Asian Paints", "AXISBANK": "Axis Bank", "BAJAJ-AUTO": "Bajaj Auto", "BAJAJFINSV": "Bajaj Finserv",
    "BAJFINANCE": "Bajaj Finance", "BEL": "Bharat Electronics", "BHARTIARTL": "Bharti Airtel", "CIPLA": "Cipla",
    "COALINDIA": "Coal India", "DRREDDY": "Dr. Reddy's", "EICHERMOT": "Eicher Motors", "ETERNAL": "Eternal",
    "GRASIM": "Grasim", "HCLTECH": "HCL Technologies", "HDFCBANK": "HDFC Bank", "HDFCLIFE": "HDFC Life",
    "HINDALCO": "Hindalco", "HINDUNILVR": "Hindustan Unilever", "ICICIBANK": "ICICI Bank", "INDIGO": "InterGlobe Aviation",
    "INFY": "Infosys", "ITC": "ITC", "JIOFIN": "Jio Financial", "JSWSTEEL": "JSW Steel", "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro", "M&M": "Mahindra & Mahindra", "MARUTI": "Maruti Suzuki", "MAXHEALTH": "Max Healthcare",
    "NESTLEIND": "Nestle India", "NTPC": "NTPC", "ONGC": "ONGC", "POWERGRID": "Power Grid", "RELIANCE": "Reliance Industries",
    "SBILIFE": "SBI Life", "SBIN": "State Bank of India", "SHRIRAMFIN": "Shriram Finance", "SUNPHARMA": "Sun Pharma",
    "TATACONSUM": "Tata Consumer", "TATASTEEL": "Tata Steel", "TCS": "Tata Consultancy Services", "TECHM": "Tech Mahindra",
    "TITAN": "Titan", "TMPV": "Tata Motors", "TRENT": "Trent", "ULTRACEMCO": "UltraTech Cement", "WIPRO": "Wipro",
}


def nifty50(max_age_days: float = 7) -> tuple[dict[str, str], str]:
    """{symbol: company name} and where it came from ("NSE", "cache", "built-in list")."""
    cached = None
    try:
        cached = json.loads(CACHE.read_text())
        if time.time() - cached["t"] < max_age_days * 86400 and len(cached["stocks"]) >= 45:
            return cached["stocks"], "cache"
    except (OSError, ValueError, KeyError):
        cached = None
    for url in URLS:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (jev-shop)", "Accept": "text/csv,*/*"})
            r.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
            stocks = {row["Symbol"].strip(): row.get("Company Name", "").strip() for row in rows
                      if row.get("Symbol") and row.get("Series", "EQ").strip() == "EQ"}
            if len(stocks) >= 45:
                RESULTS.mkdir(exist_ok=True)
                CACHE.write_text(json.dumps({"t": time.time(), "stocks": stocks}))
                return stocks, "NSE"
        except (requests.RequestException, KeyError, UnicodeDecodeError, csv.Error):
            continue
    if cached:
        return cached["stocks"], "cache (NSE unreachable)"
    return dict(FALLBACK), "built-in list (NSE unreachable; may be out of date)"
