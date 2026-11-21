"""The Claude integration, tested with real SDK message types and a scripted fake client (no network)."""

import json
from types import SimpleNamespace

import pytest
from anthropic.types.beta import BetaMessage

from app.agent import chat, digest, llm, tools
from app.data.market import MarketData
from app.models import ChatMessage, ChatSession
from app.news import summarize


def message(content, stop_reason="end_turn"):
    return BetaMessage.model_validate({
        "id": "msg_x", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5", "content": content,
        "stop_reason": stop_reason, "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 10}})


class FakeStream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        for b in self.msg.content:
            if b.type == "text":
                yield SimpleNamespace(type="text", text=b.text)

    def get_final_message(self):
        return self.msg


class FakeClient:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kwargs):
        self.calls.append(json.loads(json.dumps(kwargs, default=str)))
        return FakeStream(self.script.pop(0))


@pytest.fixture()
def fake_ai(monkeypatch):
    def install(script):
        fc = FakeClient(script)
        monkeypatch.setattr(llm, "client", lambda: fc)
        monkeypatch.setattr(llm, "ai_enabled", lambda: True)
        return fc
    return install


def test_tool_loop_streams_persists_and_replays_history_unchanged(db, fake_ai):
    fc = fake_ai([
        message([{"type": "thinking", "thinking": "", "signature": "sig-1"},
                 {"type": "text", "text": "Checking your list."},
                 {"type": "tool_use", "id": "tu_1", "name": "get_watchlist", "input": {}}], "tool_use"),
        message([{"type": "text", "text": "You follow nothing yet."}]),
    ])
    s = ChatSession()
    db.add(s)
    db.commit()
    events = list(chat.run_turn(db, s, "What do I follow?", MarketData(demo=True)))
    kinds = [e["type"] for e in events]
    assert kinds == ["text", "tool", "tool_done", "text", "done"]
    stored = db.query(ChatMessage).filter_by(session_id=s.id).order_by(ChatMessage.id).all()
    assert [m.role for m in stored] == ["user", "assistant", "user", "assistant"]
    assert stored[1].content[0] == {"type": "thinking", "thinking": "", "signature": "sig-1"}
    assert stored[2].content[0]["type"] == "tool_result" and stored[2].content[0]["tool_use_id"] == "tu_1"
    # Second request replays the first assistant turn exactly, then the tool result.
    second = fc.calls[1]["messages"]
    assert second[1]["content"] == stored[1].content and second[2]["content"][0]["tool_use_id"] == "tu_1"
    # Request shape: refusal fallback opted in, effort set, cached stable system prompt, tools passed.
    first = fc.calls[0]
    assert first["model"] == "claude-sonnet-5-5" and first["fallbacks"] == "default"
    assert first["betas"] == ["server-side-fallback-2026-07-01"]
    assert first["output_config"] == {"effort": "medium"}
    assert first["system"][0]["cache_control"] == {"type": "ephemeral"} and "Owner risk profile" in first["system"][1]["text"]
    assert {t["name"] for t in first["tools"]} == set(tools.HANDLERS)
    assert chat.display_messages(s)[-1]["text"].endswith("You follow nothing yet.")


def test_refusal_saves_nothing_for_the_turn(db, fake_ai):
    fake_ai([message([], "refusal")])
    s = ChatSession()
    db.add(s)
    db.commit()
    events = list(chat.run_turn(db, s, "hello", MarketData(demo=True)))
    assert events[-1]["type"] == "error"
    assert [m.role for m in db.query(ChatMessage).filter_by(session_id=s.id)] == ["user"]


def test_invalid_tool_input_returns_error_result_and_loop_continues(db, fake_ai):
    fc = fake_ai([
        message([{"type": "tool_use", "id": "tu_9", "name": "analyze_instrument", "input": {}}], "tool_use"),
        message([{"type": "text", "text": "Which symbol?"}]),
    ])
    s = ChatSession()
    db.add(s)
    db.commit()
    events = list(chat.run_turn(db, s, "analyse", MarketData(demo=True)))
    assert any(e["type"] == "tool_done" and e["error"] for e in events)
    result = fc.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True and "Missing required field 'symbol'" in result["content"]


@pytest.mark.parametrize("name,args", [
    ("search_instruments", {"query": "tcs"}),
    ("analyze_instrument", {"symbol": "TCS.NS"}),
    ("compare_instruments", {"symbols": ["TCS.NS", "INFY.NS"]}),
    ("get_price_history", {"symbol": "AAPL", "period": "1y"}),
    ("get_news", {"symbol": "TCS.NS"}),
    ("get_market_overview", {}),
    ("get_portfolio", {}),
    ("get_portfolio_risk", {}),
    ("get_tax_view", {}),
    ("get_rebalance_plan", {}),
    ("plan_goal", {"target_amount_today": 1000000, "years": 5}),
    ("plan_retirement", {"current_age": 30, "retire_age": 55, "monthly_expense_today": 40000}),
    ("get_watchlist", {}),
    ("follow_instrument", {"symbol": "NVDA", "pin": True}),
])
def test_every_tool_runs_in_demo_mode(db, name, args):
    out, is_error = tools.execute(db, MarketData(demo=True), name, args)
    assert not is_error, out
    json.loads(out)


def test_tool_name_case_is_tolerated_and_unknown_fields_rejected(db):
    out, err = tools.execute(db, MarketData(demo=True), "Get_Watchlist", {})
    assert not err
    out, err = tools.execute(db, MarketData(demo=True), "plan_goal", {"target_amount_today": 1, "years": 1, "x": 1})
    assert err and "Unknown field" in out


def test_sale_tax_tool(db):
    m = MarketData(demo=True)
    from datetime import date, timedelta

    from app import services

    inst = services.resolve_symbol(db, "TCS.NS", market=m)
    services.add_transaction(db, inst, side="buy", quantity=10, price=3000, trade_date=date.today() - timedelta(days=400))
    out, err = tools.execute(db, m, "estimate_sale_tax", {"symbol": "TCS.NS", "quantity": 4})
    data = json.loads(out)
    assert not err and data["quantity"] == 4 and data["lots_used"][0]["long_term"] is True


def test_digest_uses_ai_narrative_when_available(db, monkeypatch):
    seen = {}

    def fake_write(system, prompt, **kw):
        seen["system"], seen["prompt"] = system, prompt
        return "## Before the bell\n- Markets steady in this test."

    monkeypatch.setattr(llm, "ai_enabled", lambda: True)
    monkeypatch.setattr(llm, "write", fake_write)
    from app import services

    m = MarketData(demo=True)
    services.resolve_symbol(db, "RELIANCE.NS", market=m)
    d = digest.build(db, "morning", m)
    assert d.ai_generated and "Markets steady in this test" in d.html and "Market snapshot" in d.html
    assert "## Watch today" in seen["system"] and "RELIANCE.NS" in seen["prompt"]


def test_news_triage_with_structured_output(db, monkeypatch):
    from app.models import NewsItem
    from datetime import datetime, timezone

    db.add(NewsItem(key="k1", url="https://x.example/1", title="Company X beats estimates", source="Wire",
                    published_at=datetime.now(timezone.utc)))
    db.flush()
    item = db.query(NewsItem).one()

    class P:
        def parse(self, **kw):
            assert kw["output_format"] is summarize.TriageBatch and kw["model"] == "claude-haiku-5-5"
            out = summarize.TriageBatch(articles=[summarize.ArticleTriage(
                id=item.id, summary="X beat estimates.", sentiment="positive", impact="high", category="earnings")])
            return SimpleNamespace(stop_reason="end_turn", parsed_output=out)

    monkeypatch.setattr(llm, "ai_enabled", lambda: True)
    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(messages=P()))
    assert summarize.summarize_pending(db) == 1
    assert (item.impact, item.sentiment, item.category, item.summary) == ("high", "positive", "earnings", "X beat estimates.")


def test_fallback_kwargs_only_for_supported_models():
    assert llm.fallback_kwargs("claude-sonnet-5-5")["fallbacks"] == "default"
    assert llm.fallback_kwargs("claude-haiku-5-5") == {}


def test_one_gmail_address_is_sender_recipient_and_push_contact(db, monkeypatch):
    from app.config import Settings
    from app.models import PushSubscription
    from app.notify import push

    s = Settings(gmail_user="owner@gmail.example", gmail_app_password="x", digest_to="",
                 vapid_public_key="pub", vapid_private_key="priv", vapid_subject="")
    assert s.email_to == "owner@gmail.example"
    monkeypatch.setattr(push, "get_settings", lambda: s)
    seen = {}
    import pywebpush

    monkeypatch.setattr(pywebpush, "webpush", lambda info, **kw: seen.update(kw["vapid_claims"]))
    db.add(PushSubscription(endpoint="https://push.example/abc", p256dh="k" * 20, auth="a" * 8))
    db.flush()
    assert push.send_all(db, title="t", body="b") == 1
    assert seen["sub"] == "mailto:owner@gmail.example"
