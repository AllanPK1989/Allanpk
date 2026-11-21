"""Made-up market data for demos and tests (DATA_MODE=demo).

Prices are a seeded random walk, fundamentals and news are invented. The UI shows a
"Demo data" badge in this mode and every news title starts with "[Demo]".
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from .types import PERIOD_DAYS, Quote, RawNews, SearchResult

# symbol: name, class, region, exchange, currency, last price, annual drift, annual vol, extra info
UNIVERSE: dict[str, tuple[str, str, str, str, str, float, float, float, dict[str, Any]]] = {
    "RELIANCE.NS": ("Reliance Industries Ltd", "stock", "IN", "NSE", "INR", 1450.0, 0.12, 0.24,
                    {"sector": "Energy", "industry": "Oil & Gas Refining", "trailingPE": 24.5, "forwardPE": 21.0,
                     "priceToBook": 2.1, "returnOnEquity": 0.092, "profitMargins": 0.075, "revenueGrowth": 0.07,
                     "earningsGrowth": 0.09, "debtToEquity": 41.0, "currentRatio": 1.1, "beta": 0.9,
                     "sharesOutstanding": 1.353e10, "freeCashflow": 3.2e11, "totalCash": 2.1e12, "totalDebt": 3.4e12,
                     "trailingAnnualDividendRate": 5.5}),
    "TCS.NS": ("Tata Consultancy Services Ltd", "stock", "IN", "NSE", "INR", 3900.0, 0.10, 0.20,
               {"sector": "Technology", "industry": "IT Services", "trailingPE": 29.0, "forwardPE": 26.5,
                "priceToBook": 14.0, "returnOnEquity": 0.51, "profitMargins": 0.19, "revenueGrowth": 0.06,
                "earningsGrowth": 0.08, "debtToEquity": 9.0, "currentRatio": 2.4, "beta": 0.6,
                "sharesOutstanding": 3.62e9, "freeCashflow": 4.4e11, "totalCash": 4.0e11, "totalDebt": 8.0e10,
                "trailingAnnualDividendRate": 120.0}),
    "HDFCBANK.NS": ("HDFC Bank Ltd", "stock", "IN", "NSE", "INR", 1750.0, 0.11, 0.21,
                    {"sector": "Financial Services", "industry": "Banks - Regional", "trailingPE": 19.0,
                     "forwardPE": 17.0, "priceToBook": 2.7, "returnOnEquity": 0.15, "profitMargins": 0.25,
                     "revenueGrowth": 0.12, "earningsGrowth": 0.14, "beta": 0.8, "sharesOutstanding": 7.6e9,
                     "trailingAnnualDividendRate": 19.5}),
    "INFY.NS": ("Infosys Ltd", "stock", "IN", "NSE", "INR", 1600.0, 0.09, 0.24,
                {"sector": "Technology", "industry": "IT Services", "trailingPE": 25.0, "forwardPE": 22.5,
                 "priceToBook": 7.5, "returnOnEquity": 0.30, "profitMargins": 0.17, "revenueGrowth": 0.05,
                 "earningsGrowth": 0.06, "debtToEquity": 8.0, "currentRatio": 2.3, "beta": 0.7,
                 "sharesOutstanding": 4.15e9, "freeCashflow": 2.9e11, "totalCash": 3.5e11, "totalDebt": 8.0e10,
                 "trailingAnnualDividendRate": 43.0}),
    "AAPL": ("Apple Inc.", "stock", "US", "NASDAQ", "USD", 230.0, 0.14, 0.27,
             {"sector": "Technology", "industry": "Consumer Electronics", "trailingPE": 33.0, "forwardPE": 29.0,
              "priceToBook": 45.0, "returnOnEquity": 1.4, "profitMargins": 0.24, "revenueGrowth": 0.05,
              "earningsGrowth": 0.10, "debtToEquity": 150.0, "currentRatio": 0.9, "beta": 1.2,
              "sharesOutstanding": 1.5e10, "freeCashflow": 1.0e11, "totalCash": 6.5e10, "totalDebt": 1.0e11,
              "trailingAnnualDividendRate": 1.0}),
    "NVDA": ("NVIDIA Corporation", "stock", "US", "NASDAQ", "USD", 140.0, 0.25, 0.48,
             {"sector": "Technology", "industry": "Semiconductors", "trailingPE": 48.0, "forwardPE": 32.0,
              "priceToBook": 40.0, "returnOnEquity": 1.0, "profitMargins": 0.55, "revenueGrowth": 0.6,
              "earningsGrowth": 0.7, "debtToEquity": 15.0, "currentRatio": 4.0, "beta": 1.7,
              "sharesOutstanding": 2.44e10, "freeCashflow": 7.0e10, "totalCash": 4.0e10, "totalDebt": 1.0e10}),
    "NIFTYBEES.NS": ("Nippon India ETF Nifty 50 BeES", "etf", "IN", "NSE", "INR", 280.0, 0.11, 0.16,
                     {"category": "Index ETF", "netExpenseRatio": 0.04}),
    "MF:122639": ("Parag Parikh Flexi Cap Fund - Direct Plan - Growth", "mutual_fund", "IN", "AMFI", "INR",
                  85.0, 0.15, 0.14, {"category": "Equity Scheme - Flexi Cap Fund", "fundFamily": "PPFAS Mutual Fund",
                                     "bucket": "equity_india", "equityOriented": True}),
    "MF:119551": ("Sample Corporate Bond Fund - Direct Plan - Growth", "mutual_fund", "IN", "AMFI", "INR",
                  32.0, 0.075, 0.02, {"category": "Debt Scheme - Corporate Bond Fund", "fundFamily": "Sample AMC",
                                      "bucket": "debt", "equityOriented": False}),
    "CRYPTO:BTC_USDT": ("Bitcoin (BTC/USDT)", "crypto", "GLOBAL", "Crypto.com", "USD", 60000.0, 0.30, 0.55, {"base": "BTC"}),
    "CRYPTO:ETH_USDT": ("Ethereum (ETH/USDT)", "crypto", "GLOBAL", "Crypto.com", "USD", 3000.0, 0.25, 0.70, {"base": "ETH"}),
    "GC=F": ("Gold futures (COMEX)", "commodity", "GLOBAL", "COMEX", "USD", 2650.0, 0.08, 0.15, {}),
    "SI=F": ("Silver futures (COMEX)", "commodity", "GLOBAL", "COMEX", "USD", 31.0, 0.06, 0.28, {}),
    "CL=F": ("Crude oil WTI futures", "commodity", "GLOBAL", "NYMEX", "USD", 72.0, 0.0, 0.35, {}),
    "BZ=F": ("Brent crude futures", "commodity", "GLOBAL", "ICE", "USD", 76.0, 0.0, 0.33, {}),
    "USDINR=X": ("USD/INR", "forex", "IN", "FX", "INR", 84.5, 0.02, 0.04, {}),
    "EURINR=X": ("EUR/INR", "forex", "IN", "FX", "INR", 91.0, 0.01, 0.07, {}),
    "^NSEI": ("NIFTY 50", "index", "IN", "NSE", "INR", 24500.0, 0.11, 0.15, {}),
    "^BSESN": ("S&P BSE SENSEX", "index", "IN", "BSE", "INR", 80500.0, 0.11, 0.15, {}),
    "^NSEBANK": ("NIFTY BANK", "index", "IN", "NSE", "INR", 52000.0, 0.10, 0.18, {}),
    "^INDIAVIX": ("India VIX", "index", "IN", "NSE", "INR", 14.0, 0.0, 0.6, {}),
    "^GSPC": ("S&P 500", "index", "US", "SNP", "USD", 5900.0, 0.10, 0.16, {}),
    "^IXIC": ("NASDAQ Composite", "index", "US", "NASDAQ", "USD", 19000.0, 0.13, 0.21, {}),
    "^DJI": ("Dow Jones Industrial Average", "index", "US", "DJI", "USD", 43000.0, 0.08, 0.14, {}),
    "^FTSE": ("FTSE 100", "index", "GLOBAL", "FTSE", "GBP", 8200.0, 0.05, 0.13, {}),
    "^N225": ("Nikkei 225", "index", "GLOBAL", "Osaka", "JPY", 38500.0, 0.07, 0.2, {}),
    "^HSI": ("Hang Seng Index", "index", "GLOBAL", "HKSE", "HKD", 19500.0, 0.03, 0.24, {}),
    "^TNX": ("US 10Y Treasury yield", "bond", "US", "CBOE", "USD", 4.3, 0.0, 0.25, {}),
    "^VIX": ("CBOE Volatility Index", "index", "US", "CBOE", "USD", 16.0, 0.0, 0.8, {}),
}


def _seed(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest()[:8], 16)


def _today() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc).date())


class DemoProvider:
    is_demo = True

    def _spec(self, symbol: str):
        if symbol in UNIVERSE:
            return UNIVERSE[symbol]
        return (symbol, "stock", "GLOBAL", "", "USD", 100.0, 0.08, 0.3, {})

    def search(self, query: str) -> list[SearchResult]:
        q = query.strip().lower()
        out = []
        for sym, (name, cls, region, exch, ccy, *_rest) in UNIVERSE.items():
            if q and (q in sym.lower() or q in name.lower()):
                out.append(SearchResult(symbol=sym, name=name, asset_class=cls, region=region, exchange=exch,
                                        currency=ccy, meta={"demo": True}))
        return out[:20]

    def history(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        name, cls, region, _exch, _ccy, last, drift, vol, _info = self._spec(symbol)
        days = min(PERIOD_DAYS.get(period, 366), 5 * 366)
        end = _today()
        freq = "D" if cls == "crypto" else "B"
        idx = pd.date_range(end=end, periods=int(days * (1 if freq == "D" else 5 / 7)), freq=freq, name="date")
        n = len(idx)
        dt = 1 / (365 if freq == "D" else 252)
        # Same seed for every period: compute a long path then take the tail so periods agree.
        long_n = 5 * 366
        long_rets = np.random.default_rng(_seed(symbol)).normal((drift - 0.5 * vol**2) * dt, vol * np.sqrt(dt), long_n)
        rets = long_rets[-n:]
        path = np.exp(np.cumsum(rets))
        close = last * path / path[-1]
        noise = np.abs(np.random.default_rng(_seed(symbol) + 1).normal(0, vol * np.sqrt(dt) / 2, long_n))[-n:]
        high = close * (1 + noise)
        low = close * (1 - noise)
        open_ = np.concatenate([[close[0]], close[:-1]])
        volume = (np.random.default_rng(_seed(symbol) + 2).lognormal(13, 0.4, long_n))[-n:] if cls != "index" else np.zeros(n)
        return pd.DataFrame({"open": open_, "high": np.maximum(high, open_), "low": np.minimum(low, open_),
                             "close": close, "volume": volume}, index=idx)

    def quote(self, symbol: str) -> Quote:
        h = self.history(symbol, "1y")
        spec = self._spec(symbol)
        price, prev = float(h["close"].iloc[-1]), float(h["close"].iloc[-2])
        shares = spec[8].get("sharesOutstanding")
        return Quote(symbol=symbol, price=price, prev_close=prev, currency=spec[4], day_high=float(h["high"].iloc[-1]),
                     day_low=float(h["low"].iloc[-1]), volume=float(h["volume"].iloc[-1]),
                     year_high=float(h["close"].max()), year_low=float(h["close"].min()),
                     market_cap=price * shares if shares else None, as_of=datetime.now(timezone.utc))

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        return {s: self.quote(s) for s in symbols}

    def fundamentals(self, symbol: str) -> dict[str, Any]:
        name, cls, region, exch, ccy, last, drift, vol, info = self._spec(symbol)
        q = self.quote(symbol)
        out: dict[str, Any] = {"symbol": symbol, "demo": True,
                               "info": {"longName": name, "currency": ccy, "currentPrice": q.price, **info},
                               "income": {}, "cashflow": {}, "balance": {}}
        if cls == "stock" and info.get("sharesOutstanding"):
            mcap = q.price * info["sharesOutstanding"]
            out["info"]["marketCap"] = mcap
            pe = info.get("trailingPE") or 20
            ni = mcap / pe
            margin = info.get("profitMargins") or 0.1
            g = info.get("revenueGrowth") or 0.06
            years = [str(datetime.now().year - i) for i in range(1, 5)]
            rev = [ni / margin / ((1 + g) ** i) for i in range(4)]
            out["income"] = {"Total Revenue": [{"year": y, "value": v} for y, v in zip(years, rev)],
                             "Net Income": [{"year": y, "value": v * margin} for y, v in zip(years, rev)]}
            fcf = info.get("freeCashflow") or ni * 0.8
            out["cashflow"] = {"Free Cash Flow": [{"year": y, "value": fcf / ((1 + g) ** i)} for i, y in enumerate(years)]}
            out["next_earnings"] = [(datetime.now() + timedelta(days=12 + _seed(symbol) % 40)).strftime("%Y-%m-%d")]
        return out

    def news(self, symbol: str) -> list[RawNews]:
        name = self._spec(symbol)[0]
        now = datetime.now(timezone.utc)
        h = self.history(symbol, "1mo")
        chg = (h["close"].iloc[-1] / h["close"].iloc[-6] - 1) * 100 if len(h) > 6 else 0.0
        mood = "gains" if chg >= 0 else "slips"
        return [
            RawNews(title=f"[Demo] {name} {mood} {abs(chg):.1f}% over the week as investors weigh outlook",
                    url=f"https://example.com/demo/{_seed(symbol)}/1", source="Demo Wire",
                    published_at=now - timedelta(hours=3),
                    snippet=f"Made-up article for demo mode about {name}."),
            RawNews(title=f"[Demo] Analysts review {name} ahead of next results",
                    url=f"https://example.com/demo/{_seed(symbol)}/2", source="Demo Wire",
                    published_at=now - timedelta(hours=20),
                    snippet="Made-up article for demo mode. Brokerages are split on valuation."),
        ]
