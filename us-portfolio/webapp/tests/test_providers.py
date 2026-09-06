import time
import httpx
import pytest

from app.providers import Provider, Quote, QuoteService, StooqProvider, YahooProvider


class Stub(Provider):
    """Answers for a fixed set of tickers; records how often it was asked."""
    def __init__(self, name, serves, fail=False):
        self.name, self.serves, self.fail, self.calls = name, set(serves), fail, 0

    async def fetch(self, client, tickers):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        return {t: Quote(ticker=t, price=100.0, source=self.name, fetched_at=time.time())
                for t in tickers if t in self.serves}


@pytest.mark.asyncio
async def test_second_provider_covers_what_the_first_missed():
    a, b = Stub("a", ["AAPL"]), Stub("b", ["AAPL", "MSFT"])
    svc = QuoteService([a, b])
    got = await svc.get(["AAPL", "MSFT"])
    assert got["AAPL"].source == "a"          # first provider wins where it answers
    assert got["MSFT"].source == "b"          # second fills the gap
    assert b.calls == 1


@pytest.mark.asyncio
async def test_a_dead_first_provider_does_not_stop_the_chain():
    svc = QuoteService([Stub("dead", [], fail=True), Stub("live", ["AAPL"])])
    got = await svc.get(["AAPL"])
    assert got["AAPL"].source == "live"


@pytest.mark.asyncio
async def test_total_outage_returns_nothing_and_records_why():
    svc = QuoteService([Stub("dead", [], fail=True)])
    got = await svc.get(["AAPL"])
    assert got == {}
    assert "provider down" in svc.last_error


@pytest.mark.asyncio
async def test_cache_serves_repeat_calls_without_refetching():
    s = Stub("a", ["AAPL"])
    svc = QuoteService([s], ttl=60)
    await svc.get(["AAPL"])
    await svc.get(["AAPL"])
    assert s.calls == 1
    await svc.get(["AAPL"], force=True)
    assert s.calls == 2


@pytest.mark.asyncio
async def test_last_good_quotes_survive_a_later_outage():
    good, bad = Stub("good", ["AAPL"]), Stub("bad", [], fail=True)
    svc = QuoteService([good], ttl=0)
    await svc.get(["AAPL"])
    svc.providers = [bad]
    got = await svc.get(["AAPL"])          # cache is stale and nothing answers
    assert got["AAPL"].price == 100.0      # stale beats blank; age is reported
    assert svc.health()["cached_tickers"] == 1


@pytest.mark.asyncio
async def test_yahoo_parses_a_real_shaped_response():
    payload = {"chart": {"result": [{
        "meta": {"regularMarketPrice": 338.46, "chartPreviousClose": 342.5,
                 "fiftyTwoWeekLow": 226.11, "fiftyTwoWeekHigh": 408.61},
        "indicators": {"quote": [{"close": [330.0, None, 335.5, 338.46]}]}}]}}
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        got = await YahooProvider().fetch(client, ["GOOGL"])
    q = got["GOOGL"]
    assert q.price == 338.46 and q.high52 == 408.61
    assert q.closes == [330.0, 335.5, 338.46]        # nulls dropped
    assert round(q.day_pct, 2) == -1.18


@pytest.mark.asyncio
async def test_yahoo_empty_result_yields_no_quote_rather_than_an_exception():
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json={"chart": {"result": [], "error": "nope"}}))
    async with httpx.AsyncClient(transport=transport) as client:
        assert await YahooProvider().fetch(client, ["ZZZZ"]) == {}


@pytest.mark.asyncio
async def test_stooq_parses_csv_and_skips_unpriced_rows():
    head = "Symbol,Date,Time,Open,High,Low,Close,Volume\n"

    def handler(request):
        sym = str(request.url).split("s=")[1].split("&")[0]
        if sym.startswith("aapl"):
            return httpx.Response(200, text=head +
                                  "aapl.us,2026-09-04,22:00:05,315.0,321.0,314.0,319.97,1000\n")
        return httpx.Response(200, text=head + "zzzz.us,N/D,N/D,N/D,N/D,N/D,N/D,N/D\n")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        got = await StooqProvider().fetch(client, ["AAPL", "ZZZZ"])
    assert got["AAPL"].price == 319.97
    assert "ZZZZ" not in got, "an unpriced row must not become a fabricated quote"


# ---- the failures seen on the first real deploy ---------------------------

@pytest.mark.asyncio
async def test_a_blanket_429_puts_the_provider_to_sleep():
    """Yahoo answered 429 to the first request from the datacentre, not the
    thirty-third. Retrying it every poll just burns the budget."""
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(429, json={})

    p = YahooProvider()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        assert await p.fetch(c, ["AAPL", "MSFT", "GOOGL"]) == {}
    assert not p.available, "a fully blocked provider must cool off"
    assert "429" in p.last_status
    before = calls["n"]

    svc = QuoteService([p])
    await svc.get(["AAPL"])
    assert calls["n"] == before, "a resting provider must not be called again"
    assert "resting" in (svc.last_error or "")


@pytest.mark.asyncio
async def test_a_resting_provider_is_skipped_but_the_chain_continues():
    dead = YahooProvider()
    dead.rest(600, "blocked")
    live = Stub("live", ["AAPL"])
    got = await QuoteService([dead, live]).get(["AAPL"])
    assert got["AAPL"].source == "live"


@pytest.mark.asyncio
async def test_stooq_requests_one_symbol_at_a_time():
    """The comma-separated form answers 404, which is why the deploy saw no
    prices from the fallback either."""
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=(
            "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
            "aapl.us,2026-09-04,22:00:05,315.0,321.0,314.0,319.97,1000\n"))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        got = await StooqProvider().fetch(c, ["AAPL", "MSFT"])
    assert len(seen) == 2, "one request per symbol"
    assert all("," not in u.split("s=")[1].split("&")[0] for u in seen)
    assert all("&h&" in u for u in seen), "h is a valueless flag, not h="
    assert got["AAPL"].price == 319.97


@pytest.mark.asyncio
async def test_finnhub_parses_a_quote_and_rests_on_a_bad_key():
    from app.providers import FinnhubProvider
    ok = httpx.MockTransport(lambda r: httpx.Response(200, json={"c": 319.97, "pc": 328.2}))
    async with httpx.AsyncClient(transport=ok) as c:
        got = await FinnhubProvider("k").fetch(c, ["AAPL"])
    assert got["AAPL"].price == 319.97
    assert round(got["AAPL"].day_pct, 2) == -2.51

    p = FinnhubProvider("bad")
    bad = httpx.MockTransport(lambda r: httpx.Response(401, json={}))
    async with httpx.AsyncClient(transport=bad) as c:
        assert await p.fetch(c, ["AAPL"]) == {}
    assert not p.available and "key rejected" in p.last_status


@pytest.mark.asyncio
async def test_finnhub_joins_the_chain_only_with_a_key(monkeypatch):
    from app import providers as pv
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    assert [p.name for p in pv.default_providers()] == ["yahoo", "stooq"]
    monkeypatch.setenv("FINNHUB_API_KEY", "abc")
    assert [p.name for p in pv.default_providers()] == ["yahoo", "finnhub", "stooq"]


@pytest.mark.asyncio
async def test_health_lists_each_provider_and_why_it_is_resting():
    p = YahooProvider()
    p.rest(300, "429 from this IP")
    h = QuoteService([p]).health()
    entry = h["providers"][0]
    assert entry["name"] == "yahoo" and entry["available"] is False
    assert entry["resting_for"] > 0 and "429" in entry["status"]
