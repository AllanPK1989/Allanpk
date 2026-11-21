"""Yahoo Finance (via yfinance): Indian and global stocks, ETFs, indices, FX, commodities, bond yields.

Free and keyless, but unofficial: prices can lag ~15 minutes and Yahoo occasionally changes
fields. Every call here is defensive and returns partial data rather than raising.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .cache import ttl_cache
from .types import Quote, RawNews, SearchResult, empty_history

log = logging.getLogger(__name__)

IN_EXCHANGES = {"NSI", "NSE", "BSE", "BOM"}
US_EXCHANGES = {"NMS", "NYQ", "NGM", "NCM", "ASE", "PCX", "BTS", "NAS", "NYS", "PNK", "OQX", "OPR"}

QUOTE_TYPE_TO_CLASS = {
    "EQUITY": "stock",
    "ETF": "etf",
    "MUTUALFUND": "mutual_fund",
    "INDEX": "index",
    "CURRENCY": "forex",
    "CRYPTOCURRENCY": "crypto",
    "FUTURE": "commodity",
}


def region_for(symbol: str, exchange: str = "") -> str:
    s = symbol.upper()
    if s.endswith((".NS", ".BO")) or exchange.upper() in IN_EXCHANGES or s in {"^NSEI", "^BSESN", "^NSEBANK", "^INDIAVIX", "^CNXIT"}:
        return "IN"
    if "INR" in s and s.endswith("=X"):
        return "IN"
    if exchange.upper() in US_EXCHANGES or s in {"^GSPC", "^IXIC", "^DJI", "^TNX", "^VIX", "^RUT"}:
        return "US"
    if "." not in s and "=" not in s and "^" not in s and "-" not in s:
        return "US"  # bare tickers are US listings on Yahoo
    return "GLOBAL"


def classify(symbol: str, quote_type: str = "") -> str:
    if quote_type.upper() in QUOTE_TYPE_TO_CLASS:
        return QUOTE_TYPE_TO_CLASS[quote_type.upper()]
    s = symbol.upper()
    if s.startswith("^"):
        return "index"
    if s.endswith("=X"):
        return "forex"
    if s.endswith("=F"):
        return "commodity"
    if s.endswith(("-USD", "-INR")):
        return "crypto"
    return "stock"


def default_currency(region: str) -> str:
    return {"IN": "INR", "US": "USD"}.get(region, "")


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _normalize_history(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return empty_history()
    df = df.rename(columns=str.lower)
    keep = [c for c in ("open", "high", "low", "close", "volume") if c in df.columns]
    df = df[keep].copy()
    idx = pd.to_datetime(df.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)  # keep exchange-local dates
    df.index = idx.normalize()
    df.index.name = "date"
    df = df[~df.index.duplicated(keep="last")].dropna(subset=["close"])
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df.astype(float)


def _statement_rows(df: pd.DataFrame | None, rows: list[str], years: int = 4) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    if df is None or df.empty:
        return out
    cols = sorted(df.columns, reverse=True)[:years]
    for row in rows:
        if row in df.index:
            series = []
            for c in cols:
                v = _num(df.at[row, c])
                if v is not None:
                    series.append({"year": str(getattr(c, "year", c)), "value": v})
            if series:
                out[row] = series
    return out


INFO_KEYS = [
    "longName", "shortName", "sector", "industry", "longBusinessSummary", "country", "website",
    "marketCap", "enterpriseValue", "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
    "enterpriseToEbitda", "enterpriseToRevenue", "pegRatio", "trailingPegRatio", "trailingAnnualDividendYield",
    "trailingAnnualDividendRate", "dividendYield", "payoutRatio", "returnOnEquity", "returnOnAssets",
    "profitMargins", "operatingMargins", "grossMargins", "ebitdaMargins", "revenueGrowth", "earningsGrowth",
    "earningsQuarterlyGrowth", "debtToEquity", "currentRatio", "quickRatio", "freeCashflow", "operatingCashflow",
    "totalCash", "totalDebt", "totalRevenue", "ebitda", "netIncomeToCommon", "sharesOutstanding", "beta",
    "bookValue", "trailingEps", "forwardEps", "currentPrice", "targetMeanPrice", "targetHighPrice",
    "targetLowPrice", "recommendationKey", "recommendationMean", "numberOfAnalystOpinions",
    "heldPercentInsiders", "heldPercentInstitutions", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "currency",
    "financialCurrency", "quoteType", "exchange", "totalAssets", "ytdReturn", "threeYearAverageReturn",
    "fiveYearAverageReturn", "netExpenseRatio", "annualReportExpenseRatio", "category", "fundFamily",
]


class YahooProvider:
    def __init__(self):
        import yfinance  # imported lazily: heavy, and not needed in demo mode

        self.yf = yfinance

    # ---- search ----
    @ttl_cache(3600)
    def search(self, query: str) -> list[SearchResult]:
        try:
            quotes = self.yf.Search(query, max_results=10, news_count=0, lists_count=0, recommended=0,
                                    timeout=10, raise_errors=False).quotes or []
        except Exception as e:  # network / parsing
            log.warning("yahoo search failed: %s", e)
            return []
        results = []
        for q in quotes:
            sym = q.get("symbol")
            if not sym or q.get("quoteType") in {"OPTION", None}:
                continue
            exch = q.get("exchange", "") or ""
            region = region_for(sym, exch)
            results.append(SearchResult(
                symbol=sym,
                name=q.get("longname") or q.get("shortname") or sym,
                asset_class=classify(sym, q.get("quoteType", "")),
                region=region,
                exchange=q.get("exchDisp") or exch,
                currency=default_currency(region),
                meta={"sector": q.get("sector", ""), "industry": q.get("industry", "")},
            ))
        return results

    # ---- prices ----
    @ttl_cache(60)
    def quote(self, symbol: str) -> Quote:
        try:
            fi = self.yf.Ticker(symbol).fast_info
            price = _num(fi.last_price)
            prev = _num(fi.regular_market_previous_close) or _num(fi.previous_close)
            return Quote(
                symbol=symbol, price=price, prev_close=prev, currency=(fi.currency or "").upper(),
                day_high=_num(fi.day_high), day_low=_num(fi.day_low), volume=_num(fi.last_volume),
                year_high=_num(fi.year_high), year_low=_num(fi.year_low), market_cap=_num(fi.market_cap),
                as_of=datetime.now(timezone.utc),
            )
        except Exception as e:
            log.warning("yahoo quote %s failed: %s", symbol, e)
            hist = self.history(symbol, "1mo")
            return quote_from_history(symbol, hist)

    def quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Batch quotes from 5 days of daily bars (one HTTP round trip for many symbols)."""
        out: dict[str, Quote] = {}
        if not symbols:
            return out
        try:
            df = self.yf.download(symbols, period="5d", interval="1d", group_by="ticker", auto_adjust=False,
                                  progress=False, threads=True, multi_level_index=True)
        except Exception as e:
            log.warning("yahoo batch download failed: %s", e)
            df = None
        for sym in symbols:
            sub = None
            if df is not None and not df.empty:
                try:
                    sub = df[sym] if isinstance(df.columns, pd.MultiIndex) else df
                except KeyError:
                    sub = None
            q = quote_from_history(sym, _normalize_history(sub)) if sub is not None else None
            if q is None or q.price is None:
                q = self.quote(sym)
            out[sym] = q
        return out

    @ttl_cache(900)
    def history(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        try:
            df = self.yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
        except Exception as e:
            log.warning("yahoo history %s failed: %s", symbol, e)
            return empty_history()
        return _normalize_history(df)

    # ---- fundamentals ----
    @ttl_cache(6 * 3600)
    def fundamentals(self, symbol: str) -> dict[str, Any]:
        t = self.yf.Ticker(symbol)
        out: dict[str, Any] = {"symbol": symbol, "info": {}, "income": {}, "cashflow": {}, "balance": {}}
        try:
            info = t.info or {}
            out["info"] = {k: info.get(k) for k in INFO_KEYS if info.get(k) is not None}
        except Exception as e:
            log.warning("yahoo info %s failed: %s", symbol, e)
        for attr, rows, key in (
            ("income_stmt", ["Total Revenue", "Net Income", "EBITDA", "Operating Income", "Interest Expense", "Diluted EPS"], "income"),
            ("cashflow", ["Free Cash Flow", "Operating Cash Flow", "Capital Expenditure"], "cashflow"),
            ("balance_sheet", ["Total Debt", "Cash And Cash Equivalents", "Stockholders Equity", "Current Assets",
                               "Current Liabilities", "Total Assets"], "balance"),
        ):
            try:
                out[key] = _statement_rows(getattr(t, attr), rows)
            except Exception as e:
                log.info("yahoo %s %s failed: %s", attr, symbol, e)
        try:
            cal = t.calendar
            if isinstance(cal, dict):
                dates = cal.get("Earnings Date") or []
                out["next_earnings"] = [str(d) for d in dates][:2]
                if cal.get("Ex-Dividend Date"):
                    out["ex_dividend"] = str(cal.get("Ex-Dividend Date"))
        except Exception:
            pass
        return out

    # ---- news ----
    @ttl_cache(1800)
    def news(self, symbol: str) -> list[RawNews]:
        try:
            items = self.yf.Ticker(symbol).news or []
        except Exception as e:
            log.info("yahoo news %s failed: %s", symbol, e)
            return []
        return [n for n in (parse_yahoo_news_item(i) for i in items) if n]


def quote_from_history(symbol: str, hist: pd.DataFrame) -> Quote:
    if hist is None or hist.empty:
        return Quote(symbol=symbol, price=None)
    closes = hist["close"].dropna()
    price = float(closes.iloc[-1]) if len(closes) else None
    prev = float(closes.iloc[-2]) if len(closes) > 1 else None
    last = hist.iloc[-1]
    return Quote(symbol=symbol, price=price, prev_close=prev, day_high=_num(last.get("high")),
                 day_low=_num(last.get("low")), volume=_num(last.get("volume")),
                 as_of=hist.index[-1].to_pydatetime().replace(tzinfo=timezone.utc))


def parse_yahoo_news_item(item: dict[str, Any]) -> RawNews | None:
    """Handles both the old flat format and the 2025+ {"content": {...}} format."""
    c = item.get("content") if isinstance(item.get("content"), dict) else None
    if c:
        title = c.get("title") or ""
        url = ((c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url") or "")
        source = (c.get("provider") or {}).get("displayName", "Yahoo Finance")
        snippet = c.get("summary") or c.get("description") or ""
        try:
            published = datetime.fromisoformat((c.get("pubDate") or "").replace("Z", "+00:00"))
        except ValueError:
            published = datetime.now(timezone.utc)
    else:
        title, url = item.get("title") or "", item.get("link") or ""
        source, snippet = item.get("publisher") or "Yahoo Finance", item.get("summary") or ""
        ts = item.get("providerPublishTime")
        published = datetime.fromtimestamp(ts, timezone.utc) if ts else datetime.now(timezone.utc)
    if not title or not url.startswith("http"):
        return None
    return RawNews(title=title.strip(), url=url, source=source, published_at=published, snippet=snippet.strip())
