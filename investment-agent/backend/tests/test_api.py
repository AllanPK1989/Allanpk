from datetime import date, timedelta

from fastapi.testclient import TestClient


def test_login_required_and_wrong_password_throttled(app):
    c = TestClient(app)
    assert c.get("/api/instruments").status_code == 401
    for _ in range(5):
        assert c.post("/api/auth/login", json={"password": "nope"}).status_code == 401
    assert c.post("/api/auth/login", json={"password": "correct-horse-battery"}).status_code == 429


def test_forged_forwarded_for_does_not_reset_throttle(app):
    c = TestClient(app)
    for i in range(5):
        c.post("/api/auth/login", json={"password": "nope"}, headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.9"})
    r = c.post("/api/auth/login", json={"password": "correct-horse-battery"}, headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.9"})
    assert r.status_code == 429


def test_health_is_public(app):
    assert TestClient(app).get("/api/health").json() == {"ok": True}


def test_session_cookie_flags(app):
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"password": "correct-horse-battery"})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert c.get("/api/auth/me").json()["authenticated"] is True
    c.post("/api/auth/logout")
    c.cookies.clear()
    assert c.get("/api/auth/me").json()["authenticated"] is False


def test_cross_site_post_is_blocked(client):
    r = client.post("/api/instruments", json={"symbol": "TCS.NS"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_security_headers(client):
    r = client.get("/api/status")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.json()["demo"] is True


def test_search_then_follow_keeps_it_followed(client):
    res = client.get("/api/search", params={"q": "reliance"}).json()["results"]
    assert res and res[0]["symbol"] == "RELIANCE.NS"
    r = client.post("/api/instruments", json=res[0])
    assert r.status_code == 200 and r.json()["followed"] is True
    listed = client.get("/api/instruments").json()["instruments"]
    assert [i["symbol"] for i in listed] == ["RELIANCE.NS"]
    assert listed[0]["quote"]["price"] > 0


def test_instrument_analysis_has_all_parts(client):
    client.post("/api/instruments", json={"symbol": "TCS.NS", "name": "Tata Consultancy Services Ltd", "region": "IN"})
    a = client.get("/api/instruments/TCS.NS/analysis").json()
    assert a["technical"]["available"] and a["fundamental"]["kind"] == "company"
    assert a["fundamental"]["valuation"]["available"] and a["chart"]["close"]
    mf = client.post("/api/instruments", json={"symbol": "MF:122639", "asset_class": "mutual_fund", "region": "IN"})
    assert mf.json()["meta"]["bucket"] == "equity_india"
    f = client.get("/api/instruments/MF%3A122639/analysis").json()
    assert f["fund"]["available"] and f["fund"]["returns_pct"]["3y_cagr"] is not None


def test_symbols_with_special_characters(client):
    client.post("/api/instruments", json={"symbol": "^NSEI", "asset_class": "index", "region": "IN"})
    assert client.get("/api/instruments/%5ENSEI/analysis").status_code == 200
    assert client.patch("/api/instruments/%5ENSEI", json={"pinned": True}).json()["pinned"] is True


def test_portfolio_transactions_value_and_tax(client):
    old = (date.today() - timedelta(days=500)).isoformat()
    recent = (date.today() - timedelta(days=100)).isoformat()
    assert client.post("/api/transactions", json={"symbol": "RELIANCE.NS", "side": "buy", "quantity": 10, "price": 1000,
                                                 "trade_date": old}).status_code == 200
    client.post("/api/transactions", json={"symbol": "AAPL", "side": "buy", "quantity": 5, "price": 150,
                                           "trade_date": recent, "fx_rate": 83.0})
    too_many = client.post("/api/transactions", json={"symbol": "AAPL", "side": "sell", "quantity": 50, "price": 200,
                                                      "trade_date": recent})
    assert too_many.status_code == 400
    p = client.get("/api/portfolio").json()
    assert len(p["holdings"]) == 2 and p["totals"]["value"] > 0
    aapl = next(h for h in p["holdings"] if h["symbol"] == "AAPL")
    assert aapl["invested"] == 5 * 150 * 83.0  # trade-date FX used for cost
    assert set(p["allocation"]) == {"equity_india", "equity_global"}
    t = client.get("/api/portfolio/tax").json()
    rel = next(h for h in t["holdings"] if h["symbol"] == "RELIANCE.NS")
    assert rel["tax_class"] == "listed_equity" and rel["long_term_gain"] != 0
    r = client.get("/api/portfolio/risk").json()
    assert r["available"] and r["volatility_pct"] > 0
    rb = client.get("/api/portfolio/rebalance").json()
    assert rb["rows"]


def test_csv_import_generic_and_bad_file(client):
    csv_text = "symbol,side,quantity,price,date\nINFY.NS,buy,20,1400,2024-02-01\nINFY.NS,sell,5,1600,2025-01-10\n"
    r = client.post("/api/portfolio/import", files={"file": ("trades.csv", csv_text, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["added"] == 2 and r.json()["format"] == "generic"
    bad = client.post("/api/portfolio/import", files={"file": ("x.csv", "foo,bar\n1,2\n", "text/csv")})
    assert bad.status_code == 400
    txs = client.get("/api/transactions").json()["transactions"]
    assert len(txs) == 2


def test_news_refresh_and_digest_without_ai(client):
    client.post("/api/instruments", json={"symbol": "HDFCBANK.NS", "name": "HDFC Bank Ltd", "region": "IN"})
    stats = client.post("/api/news/refresh").json()
    assert stats["new"] >= 2 and stats["triaged"] >= 2
    news = client.get("/api/news").json()["news"]
    assert news and all(n["sentiment"] for n in news)
    d = client.post("/api/digests/run", json={"kind": "morning", "send": True}).json()
    full = client.get(f"/api/digests/{d['id']}").json()
    assert "Market snapshot" in full["html"] and "HDFC Bank" in full["html"]
    assert full["ai_generated"] is False and "<script" not in full["html"]
    assert '<li><a href="https://example.com/demo/' in full["html"]  # news renders as a real list
    w = client.post("/api/digests/run", json={"kind": "weekly"}).json()
    assert "Weekly review" in w["title"]


def test_alerts_fire_once_per_band(client):
    client.post("/api/instruments", json={"symbol": "NVDA", "name": "NVIDIA", "region": "US"})
    client.put("/api/settings", json={"alert_pct": 0.0001})
    first = client.post("/api/alerts/check").json()["new"]
    second = client.post("/api/alerts/check").json()["new"]
    assert any("NVIDIA" in t for t in first) and not any("NVIDIA" in t for t in second)
    assert client.get("/api/alerts").json()["alerts"]


def test_settings_validation(client):
    assert client.put("/api/settings", json={"risk_profile": "yolo"}).status_code == 422
    s = client.put("/api/settings", json={"risk_profile": "aggressive", "goals_notes": "Retire at 50"}).json()
    assert s["risk_profile"] == "aggressive" and s["goals_notes"] == "Retire at 50"


def test_planning_endpoints(client):
    g = client.post("/api/plan/goal", json={"target_amount_today": 2000000, "years": 8}).json()
    assert g["monthly_sip"] > 0
    assert client.post("/api/plan/retirement", json={"current_age": 50, "retire_age": 40,
                                                     "monthly_expense_today": 50000}).status_code == 400


def test_push_subscribe_requires_https(client):
    bad = client.post("/api/push/subscribe", json={"endpoint": "http://x.example/abc", "keys": {"p256dh": "a" * 20, "auth": "b" * 8}})
    assert bad.status_code == 422
    ok = client.post("/api/push/subscribe", json={"endpoint": "https://fcm.googleapis.com/x/abc",
                                                   "keys": {"p256dh": "a" * 20, "auth": "b" * 8}})
    assert ok.status_code == 200
    assert client.get("/api/status").json()["push_subscriptions"] == 1


def test_chat_offline_reply_streams_and_persists(client):
    sid = client.post("/api/chat/sessions").json()["id"]
    with client.stream("POST", f"/api/chat/sessions/{sid}/messages", json={"text": "Infosys"}) as r:
        body = "".join(r.iter_text())
    assert '"type": "done"' in body and "AI is off" in body
    msgs = client.get(f"/api/chat/sessions/{sid}").json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert any(i["symbol"] == "INFY.NS" for i in client.get("/api/instruments").json()["instruments"])


def test_report_without_ai(client):
    client.post("/api/instruments", json={"symbol": "AAPL", "name": "Apple", "region": "US"})
    r = client.post("/api/instruments/AAPL/report").json()
    assert r["ai_generated"] is False and "Technical picture" in r["html"]
