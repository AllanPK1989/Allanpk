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
    csv = ("Symbol,Date,Time,Open,High,Low,Close\n"
           "aapl.us,2026-09-04,22:00:05,315.0,321.0,314.0,319.97\n"
           "zzzz.us,N/D,N/D,N/D,N/D,N/D,N/D\n")
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=csv))
    async with httpx.AsyncClient(transport=transport) as client:
        got = await StooqProvider().fetch(client, ["AAPL", "ZZZZ"])
    assert got["AAPL"].price == 319.97
    assert "ZZZZ" not in got
