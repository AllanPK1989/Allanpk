"""RSS sources and parsing."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import nh3

from ..data.types import RawNews

# Market-wide feeds. Each is fetched once per collection run.
MARKET_FEEDS: list[tuple[str, str, str]] = [
    ("Economic Times Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "IN"),
    ("Economic Times Stocks", "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2146842.cms", "IN"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml", "IN"),
    ("Mint Markets", "https://www.livemint.com/rss/markets", "IN"),
    ("CNBC Markets", "https://www.cnbc.com/id/10000664/device/rss/rss.html", "US"),
    ("CNBC Economy", "https://www.cnbc.com/id/20910258/device/rss/rss.html", "US"),
]

GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"

_SUFFIXES = re.compile(r"\b(limited|ltd\.?|inc\.?|incorporated|corporation|corp\.?|plc|co\.|company|holdings?)\s*$", re.I)
_PLAN = re.compile(r"\s*-\s*(direct|regular)\b.*$", re.I)

SPECIAL_QUERIES = {
    "^NSEI": "Nifty 50", "^BSESN": "Sensex", "^NSEBANK": "Bank Nifty", "^INDIAVIX": "India VIX",
    "^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^DJI": "Dow Jones", "GC=F": "gold price", "SI=F": "silver price",
    "CL=F": "crude oil price", "BZ=F": "Brent crude", "USDINR=X": "rupee dollar", "EURINR=X": "rupee euro",
    "^TNX": "US Treasury yields",
}


def google_news_url(query: str, days: int = 2) -> str:
    return GOOGLE_NEWS.format(q=quote_plus(f"{query} when:{days}d"))


def short_name(name: str) -> str:
    n = _PLAN.sub("", name or "").strip()
    n = re.sub(r"\s*\(.*?\)\s*", " ", n).strip()
    for _ in range(2):
        n = _SUFFIXES.sub("", n).strip(" ,.-")
    return n


def news_query(symbol: str, name: str, asset_class: str) -> str:
    if symbol in SPECIAL_QUERIES:
        return SPECIAL_QUERIES[symbol]
    base = short_name(name)
    if asset_class == "crypto":
        coin = base.split(" ")[0] if base else symbol.split(":")[-1].split("_")[0]
        return f"{coin} crypto"
    if asset_class == "mutual_fund":
        return f'"{base}"'
    if asset_class == "stock":
        return f'"{base}" shares'
    return f'"{base}"'


def match_keywords(symbol: str, name: str, asset_class: str) -> list[str]:
    """Words that identify this instrument inside market-wide headlines."""
    if symbol in SPECIAL_QUERIES:
        q = SPECIAL_QUERIES[symbol].replace(" price", "")
        return [q]
    words = []
    base = short_name(name)
    if base and len(base) >= 4:
        words.append(base)
        first = base.split(" ")[0]
        if len(first) >= 5 and first.lower() not in {"india", "indian", "state", "united", "first", "national", "global"}:
            words.append(first)
    tick = symbol.split(":")[-1].split(".")[0].split("_")[0]
    if asset_class in ("stock", "etf") and len(tick) >= 3 and tick.isalpha():
        words.append(tick)
    return list(dict.fromkeys(words))


def keyword_hit(text: str, keywords: list[str]) -> bool:
    for k in keywords:
        if k.isupper() and len(k) <= 5:
            if re.search(rf"\b{re.escape(k)}\b", text):  # tickers: case-sensitive
                return True
        elif re.search(rf"\b{re.escape(k)}\b", text, re.I):
            return True
    return False


def clean_text(s: str, limit: int = 500) -> str:
    text = html.unescape(nh3.clean(s or "", tags=set()))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def news_key(title: str) -> str:
    norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()[:140]
    return hashlib.sha256(norm.encode()).hexdigest()[:40]


def parse_feed(content: bytes | str, default_source: str = "") -> list[RawNews]:
    feed = feedparser.parse(content)
    out = []
    for e in feed.entries:
        title = clean_text(e.get("title", ""), 300)
        link = e.get("link", "")
        if not title or not link.startswith("http"):
            continue
        source = default_source
        src = e.get("source")
        if isinstance(src, dict) and src.get("title"):
            source = src["title"]
            suffix = f" - {source}"
            if title.endswith(suffix):  # Google News appends " - Source"
                title = title[: -len(suffix)].strip()
        ts = e.get("published_parsed") or e.get("updated_parsed")
        published = datetime(*ts[:6], tzinfo=timezone.utc) if ts else datetime.now(timezone.utc)
        snippet = clean_text(e.get("summary", ""), 400)
        if snippet.startswith(title):
            snippet = ""
        out.append(RawNews(title=title, url=link, source=source or "News", published_at=published, snippet=snippet))
    return out
