"""Parsers for each free data source, checked against their documented response formats."""

from datetime import date

import pandas as pd
import pytest

from app import importer
from app.data import cryptocom, fred, mfapi, yahoo
from app.news import feeds
from app.notify import push
from app.render import to_html
from app.security import hash_password, verify_password

GOOGLE_RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Google News</title>
<item><title>Reliance shares rise after Q2 results - The Economic Times</title>
<link>https://news.google.com/rss/articles/abc?oc=5</link><pubDate>Fri, 21 Nov 2026 04:30:00 GMT</pubDate>
<description>&lt;a href="https://x"&gt;Reliance shares rise after Q2 results&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;The Economic Times&lt;/font&gt;</description>
<source url="https://economictimes.indiatimes.com">The Economic Times</source></item>
<item><title>No link item</title></item></channel></rss>"""

ET_RSS = """<?xml version="1.0"?><rss version="2.0"><channel><item><title>Sensex ends 300 pts higher; TCS, Infosys lead</title>
<link>https://economictimes.indiatimes.com/markets/x.cms</link><pubDate>Fri, 21 Nov 2026 10:15:00 +0530</pubDate>
<description><![CDATA[<img src="x.jpg"/>IT stocks led gains as <b>TCS</b> rose 2%.]]></description></item></channel></rss>"""


def test_google_news_parsing_strips_source_suffix():
    items = feeds.parse_feed(GOOGLE_RSS.encode(), "")
    assert len(items) == 1
    n = items[0]
    assert n.title == "Reliance shares rise after Q2 results" and n.source == "The Economic Times"
    assert n.published_at.year == 2026 and n.snippet == ""


def test_publisher_rss_html_is_cleaned_and_timezone_converted():
    n = feeds.parse_feed(ET_RSS, "Economic Times Markets")[0]
    assert n.snippet == "IT stocks led gains as TCS rose 2%." and n.source == "Economic Times Markets"
    assert n.published_at.hour == 4 and n.published_at.minute == 45  # 10:15 IST = 04:45 UTC


def test_queries_and_keyword_matching():
    assert feeds.news_query("RELIANCE.NS", "Reliance Industries Limited", "stock") == '"Reliance Industries" shares'
    assert feeds.news_query("MF:1", "Parag Parikh Flexi Cap Fund - Direct Plan - Growth", "mutual_fund") == '"Parag Parikh Flexi Cap Fund"'
    assert feeds.news_query("GC=F", "Gold", "commodity") == "gold price"
    kws = feeds.match_keywords("TCS.NS", "Tata Consultancy Services Ltd", "stock")
    assert "TCS" in kws
    assert feeds.keyword_hit("Sensex up; TCS, Infosys lead", kws)
    assert not feeds.keyword_hit("tcs-like lowercase word", ["TCS"])
    assert feeds.news_key("Hello, World!") == feeds.news_key("hello world")


def test_mfapi_nav_history_and_categories():
    payload = {"meta": {"scheme_category": "Equity Scheme - Flexi Cap Fund"}, "status": "SUCCESS",
               "data": [{"date": "21-11-2026", "nav": "85.12300"}, {"date": "20-11-2026", "nav": "84.90000"},
                        {"date": "bad", "nav": "x"}]}
    df = mfapi.parse_nav_history(payload)
    assert list(df.index.strftime("%Y-%m-%d")) == ["2026-11-20", "2026-11-21"] and df["close"].iloc[-1] == 85.123
    assert mfapi.bucket_for_category("Debt Scheme - Corporate Bond Fund") == "debt"
    assert mfapi.bucket_for_category("Other Scheme - FoF Overseas") == "equity_global"
    assert mfapi.bucket_for_category("Other Scheme - Gold ETF") == "gold"
    assert mfapi.bucket_for_category("Hybrid Scheme - Aggressive Hybrid Fund") == "hybrid"
    assert mfapi.is_equity_oriented("Hybrid Scheme - Aggressive Hybrid Fund") is True
    assert mfapi.is_equity_oriented("Debt Scheme - Liquid Fund") is False


@pytest.mark.parametrize("ticker", [
    {"i": "BTC_USDT", "a": "58165.88", "c": "-0.0517", "h": "62182.74", "l": "55118.98", "vv": "333425080.80", "t": 1763726960560},
    {"instrument_name": "BTC_USDT", "last": "58165.88", "change": "-0.0517", "high": "62182.74", "low": "55118.98",
     "volume_value": "333425080.80", "timestamp": "2026-11-21T12:09:20.560Z"},
])
def test_crypto_ticker_short_and_long_keys(ticker):
    q = cryptocom.parse_ticker("CRYPTO:BTC_USDT", ticker)
    assert q.price == pytest.approx(58165.88) and q.change_pct == pytest.approx(-5.17, abs=0.01)
    assert q.currency == "USD" and q.day_high == pytest.approx(62182.74)


def test_crypto_candles():
    df = cryptocom.parse_candles([
        {"o": "61987.74", "h": "62644.99", "l": "57751.54", "c": "58952.71", "v": "4078.5", "t": 1763596800000},
        {"open": "58952.71", "high": "59250.01", "low": "55118.98", "close": "58165.88", "volume": "2855.1",
         "timestamp": "2026-11-21T00:00:00Z"},
    ])
    assert len(df) == 2 and df["close"].iloc[-1] == pytest.approx(58165.88) and df.index.is_monotonic_increasing


def test_fred_csv_both_headers_and_missing_values(monkeypatch):
    s = fred.parse_csv("observation_date,DGS10\n2026-11-18,4.10\n2026-11-19,.\n2026-11-20,4.12\n")
    assert list(s.values) == [4.10, 4.12]
    s2 = fred.parse_csv("DATE,X\n2026-01-01,1\n")
    assert len(s2) == 1
    idx = pd.date_range("2025-01-01", periods=13, freq="MS")
    monkeypatch.setattr(fred, "series", lambda sid: pd.Series([100.0] * 12 + [103.0], index=idx))
    assert fred.latest("CPIAUCSL")["value"] == pytest.approx(3.0)


def test_yahoo_helpers_and_news_formats():
    assert yahoo.region_for("RELIANCE.NS") == "IN" and yahoo.region_for("AAPL", "NMS") == "US"
    assert yahoo.region_for("USDINR=X") == "IN" and yahoo.region_for("^FTSE") == "GLOBAL"
    assert yahoo.classify("GC=F") == "commodity" and yahoo.classify("X", "ETF") == "etf"
    new = {"id": "1", "content": {"title": "Apple unveils", "summary": "s", "pubDate": "2026-11-20T15:00:00Z",
                                  "provider": {"displayName": "Reuters"}, "canonicalUrl": {"url": "https://r.example/a"}}}
    old = {"title": "Old style", "publisher": "Bloomberg", "link": "https://b.example/x", "providerPublishTime": 1763650000}
    a, b = yahoo.parse_yahoo_news_item(new), yahoo.parse_yahoo_news_item(old)
    assert (a.title, a.source, a.url) == ("Apple unveils", "Reuters", "https://r.example/a")
    assert b.source == "Bloomberg" and b.published_at.year == 2025
    assert yahoo.parse_yahoo_news_item({"content": {"title": "x", "canonicalUrl": {"url": "javascript:alert(1)"}}}) is None


def test_broker_csv_formats():
    zt = ("symbol,isin,trade_date,exchange,segment,series,trade_type,auction,quantity,price,trade_id,order_id,order_execution_time\n"
          "INFY,INE009A01021,2024-03-05,NSE,EQ,EQ,buy,false,10,1580.5,1,2,2024-03-05T10:00:00\n")
    fmt, rows = importer.parse(zt)
    assert fmt == "zerodha_tradebook" and rows[0]["symbol"] == "INFY.NS" and rows[0]["trade_date"] == date(2024, 3, 5)
    zh = "Instrument,Qty.,Avg. cost,LTP,Cur. val,P&L,Net chg.,Day chg.\nTCS,5,\"3,400.00\",3900,19500,2500,14.7,0.5\n"
    fmt, rows = importer.parse(zh)
    assert fmt == "zerodha_holdings" and rows[0]["price"] == 3400.0 and rows[0]["undated"]
    gw = "Stock Name,ISIN,Quantity,Average buy price,Buying value,Closing price,Closing value,Unrealised P&L\nHDFC Bank,INE040A01034,3,1500,4500,1700,5100,600\n"
    fmt, rows = importer.parse(gw)
    assert fmt == "groww_holdings" and rows[0]["isin"] == "INE040A01034"
    with pytest.raises(ValueError, match="Row 2"):
        importer.parse("symbol,quantity,price,date\nX,1,2,not-a-date\n")


def test_vapid_keys_are_valid_for_pywebpush():
    pub, priv = push.generate_vapid_keys()
    assert len(pub) == 87 and len(priv) == 43
    from py_vapid import Vapid

    assert Vapid.from_string(priv) is not None


def test_password_hash_roundtrip():
    h = hash_password("s3cret-password")
    assert verify_password("s3cret-password", h) and not verify_password("wrong", h)
    assert not verify_password("x", "garbage")


def test_markdown_sanitiser_strips_scripts_and_bad_links():
    html = to_html('Hi <script>alert(1)</script> [x](javascript:alert(1)) [ok](https://e.example)')
    assert "<script" not in html and "javascript:" not in html
    assert 'href="https://e.example"' in html and 'rel="noopener noreferrer nofollow"' in html


def test_default_gmail_sender_and_empty_env_values_fall_back(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("GMAIL_USER", "")  # GitHub Actions passes unset secrets as empty strings
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-pass")
    monkeypatch.setenv("DIGEST_TO", "")
    s = Settings(_env_file=None)
    assert s.gmail_user == "financeforpk@gmail.com" and s.email_to == "financeforpk@gmail.com"
    assert s.email_enabled
