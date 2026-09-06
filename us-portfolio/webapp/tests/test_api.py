import time

import pytest
from fastapi.testclient import TestClient

from app import main
from app.providers import Provider, Quote


class Stub(Provider):
    name = "stub"
    def __init__(self, prices): self.prices = prices
    async def fetch(self, client, tickers):
        return {t: Quote(ticker=t, price=p, prev_close=p * 0.99,
                         low52=p * 0.5, high52=p * 1.5,
                         closes=[p * (1 + i / 500) for i in range(260)],
                         source=self.name, fetched_at=time.time())
                for t, p in self.prices.items() if t in tickers}


@pytest.fixture
def client(monkeypatch):
    main.quotes.providers = [Stub({"GOOGL": 400.0, "META": 700.0})]
    main.quotes._cache.clear()
    monkeypatch.setenv("SKIP_WARMUP", "1")
    with TestClient(main.app) as c:
        yield c


def test_portfolio_marks_live_names_and_leaves_the_rest_on_reference(client):
    b = client.get("/api/portfolio").json()
    rows = {r["ticker"]: r for r in b["universe"]}
    assert rows["GOOGL"]["px"] == 400.0 and rows["GOOGL"]["live"] is True
    assert rows["AAPL"]["live"] is False and rows["AAPL"]["px"] == 319.97
    assert b["feed"]["live_count"] == 2
    assert b["feed"]["sources"] == ["stub"]


def test_values_weights_and_scores_follow_the_live_price(client):
    b = client.get("/api/portfolio").json()
    rows = {r["ticker"]: r for r in b["universe"]}
    g = rows["GOOGL"]
    assert round(g["value"], 2) == round(g["shares"] * 400.0, 2)
    # 400 against a 600 high is 33% off, squarely in the entry sweet spot
    assert g["off_high_pct"] == pytest.approx(33.3, abs=0.2)
    assert g["entry_score"] > 90
    # totals are the sum of the marked accounts, not the stale ones
    assert round(sum(a["value"] for a in b["accounts"]), 2) == round(b["totals"]["value"], 2)


def test_indicators_are_computed_from_the_returned_history(client):
    rows = {r["ticker"]: r for r in client.get("/api/portfolio").json()["universe"]}
    assert rows["GOOGL"]["rsi"] == 100.0          # the stub series only rises
    assert rows["GOOGL"]["sma200"] is not None
    assert len(rows["GOOGL"]["spark"]) == 90
    assert "rsi" not in rows["AAPL"]              # no history, so no indicator


def test_market_state_is_reported(client):
    m = client.get("/api/portfolio").json()["market"]
    assert m["phase"] in {"open", "pre", "post", "closed"}
    assert m["poll_seconds"] > 0


def test_health_stays_green_when_no_quote_source_is_reachable(client):
    """Regression: this returned 503, and Render killed a deploy over it. A
    blocked feed is a degraded feed, not a dead service — the app still serves
    every page from the reference close."""
    main.quotes._cache.clear()
    r = client.get("/api/health")
    assert r.status_code == 200, "a degraded feed must not fail the platform health check"
    body = r.json()
    assert body["ok"] is True
    assert body["degraded"] is True
    assert "reference close" in body["detail"]


def test_health_reports_undegraded_once_quotes_arrive(client):
    client.get("/api/portfolio")
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["degraded"] is False
    assert body["detail"] == "serving live quotes"


def test_head_on_root_is_allowed(client):
    """Platform port probes send HEAD; a 405 there reads as a broken service."""
    assert client.head("/").status_code == 200


def test_refresh_bypasses_the_cache(client):
    first = client.get("/api/portfolio").json()["feed"]["age_seconds"]
    main.quotes.providers = [Stub({"GOOGL": 450.0, "META": 700.0})]
    assert client.get("/api/portfolio").json()["universe"][0] is not None  # cached, unchanged
    rows = {r["ticker"]: r for r in client.post("/api/refresh").json()["universe"]}
    assert rows["GOOGL"]["px"] == 450.0
    assert first is not None


def test_index_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "Consolidated US Book" in r.text


def test_token_gate_blocks_when_configured(monkeypatch):
    monkeypatch.setattr(main, "APP_TOKEN", "s3cret")
    main.quotes.providers = [Stub({"GOOGL": 400.0})]
    with TestClient(main.app) as c:
        assert c.get("/api/portfolio").status_code == 401
        assert c.get("/api/portfolio", headers={"X-App-Token": "wrong"}).status_code == 401
        assert c.get("/api/portfolio", headers={"X-App-Token": "s3cret"}).status_code == 200
        assert c.get("/api/portfolio?token=s3cret").status_code == 200
        assert c.get("/api/health").status_code in (200, 503)   # health stays open


def test_drift_flags_a_call_whose_price_has_moved(client):
    """The written verdicts are dated. When the live price runs away from the
    price they were written at, the page must be able to say so."""
    rows = {r["ticker"]: r for r in client.get("/api/portfolio").json()["universe"]}
    g = rows["GOOGL"]
    assert g["ref_px"] == 338.46          # the statement close the call was written at
    assert g["px"] == 400.0               # live
    assert g["drift_pct"] == pytest.approx(18.2, abs=0.2)
    assert rows["AAPL"]["drift_pct"] is None   # not live, so nothing has drifted


def test_favicon_is_served(client):
    r = client.get("/favicon.ico")
    assert r.status_code == 200 and "svg" in r.headers["content-type"]
