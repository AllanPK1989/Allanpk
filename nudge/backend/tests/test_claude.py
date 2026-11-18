"""The Claude path, run through the real Anthropic SDK against a fake HTTP transport."""
import json
from datetime import datetime

import anthropic
import httpx2

from app.ai import service as ai
from app.ai.claude import ClaudeClient
from app.config import Config
from app.models import AICall, Task

NOW = datetime(2026, 11, 18, 4, 30)  # 10:00 IST


def fake(handler) -> list:
    seen = []

    def record(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    sdk = anthropic.Anthropic(api_key="test-key", base_url="http://claude.test", max_retries=0,
                              http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(record)))
    ai.set_client(ClaudeClient(Config(ai_provider="anthropic"), client=sdk))
    return seen


def message(payload: dict | str, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": payload if isinstance(payload, str) else json.dumps(payload)}],
        "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 900, "output_tokens": 250, "cache_read_input_tokens": 0,
                  "cache_creation_input_tokens": 0},
    }


def task(**kw):
    base = {"title": "", "notes": "", "basket": "", "due_date": "", "due_time": "", "priority": "normal",
            "person": "", "waiting_on_person": False, "repeat_rule": "", "checklist": [], "guessed": []}
    return {**base, **kw}


def test_claude_reads_the_note(db, prefs, monkeypatch):
    monkeypatch.setattr(ai, "ai_enabled", lambda: True)
    answer = {
        "intent": "create",
        "tasks": [
            task(title="Send PM report to Suresh", basket="Work", due_date="2026-11-20", person="Suresh",
                 priority="high", guessed=["basket"]),
            task(title="Follow up with Ravi on spares", basket="Work", due_date="2026-11-24", person="Ravi",
                 waiting_on_person=True),
            task(title="Study CMRP", basket="Learning", due_time="07:00", repeat_rule="FREQ=WEEKLY;BYDAY=MO"),
            task(title="Bad basket", basket="Nope", due_date="not a date", due_time="25:99"),
        ],
        "targets": [], "answer": "Four tasks ready to save.", "match_ids": [],
    }
    seen = fake(lambda r: httpx2.Response(200, json=message(answer)))
    out = ai.interpret(db, prefs, "send the PM report to Suresh by Friday urgent ...", now=NOW)
    assert out["understood_by"] == "claude" and out["warning"] == ""
    d = out["drafts"]
    assert d[0]["basket"]["name"] == "Work" and d[0]["priority"] == "high"
    assert d[1]["waiting"] is True
    assert (d[2]["due_date"], d[2]["due_time"], d[2]["repeat_label"]) == ("2026-11-23", "07:00", "Every Monday")
    assert d[3]["basket_id"] is None and "basket" in d[3]["guessed"] and d[3]["due_date"] is None

    body = json.loads(seen[0].content)
    assert body["model"] == "claude-opus-5-5"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["output_config"]["effort"] == "low"
    assert body["fallbacks"] == "default"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    user = body["messages"][0]["content"]
    assert "Wed 18 Nov 2026 = 2026-11-18 (today)" in user and "Baskets: Work; Projects" in user
    call = db.query(AICall).one()
    assert call.ok and call.input_tokens == 900 and call.cost_usd > 0


def test_claude_command_targets_must_be_open_tasks(db, prefs, monkeypatch):
    monkeypatch.setattr(ai, "ai_enabled", lambda: True)
    from app import tasks_service as ts
    t = ts.create_task(db, prefs, {"title": "Call the vendor"}, now=NOW)
    db.commit()
    answer = {"intent": "complete", "tasks": [], "answer": "Marking the vendor call done.", "match_ids": [],
              "targets": [{"task_id": t.id, "new_due_date": "", "new_due_time": ""},
                          {"task_id": 999, "new_due_date": "", "new_due_time": ""}]}
    fake(lambda r: httpx2.Response(200, json=message(answer)))
    out = ai.interpret(db, prefs, "vendor call is done", now=NOW)
    assert [x["task_id"] for x in out["targets"]] == [t.id]


def test_falls_back_to_rules_when_claude_fails(db, prefs, monkeypatch):
    monkeypatch.setattr(ai, "ai_enabled", lambda: True)
    fake(lambda r: httpx2.Response(529, json={"type": "error", "error": {"type": "overloaded_error",
                                                                          "message": "Overloaded"}}))
    out = ai.interpret(db, prefs, "Pay the electricity bill tomorrow", now=NOW)
    assert out["understood_by"] == "rules" and "simple rules" in out["warning"]
    assert out["drafts"][0]["title"] == "Pay the electricity bill"
    assert db.query(AICall).one().ok is False


def test_refusal_falls_back_too(db, prefs, monkeypatch):
    monkeypatch.setattr(ai, "ai_enabled", lambda: True)
    fake(lambda r: httpx2.Response(200, json={**message(""), "stop_reason": "refusal"}))
    out = ai.interpret(db, prefs, "Call Ravi", now=NOW)
    assert out["understood_by"] == "rules"


def test_nudge_message_from_claude(db, prefs, monkeypatch):
    monkeypatch.setattr(ai, "ai_enabled", lambda: True)
    fake(lambda r: httpx2.Response(200, json=message({"message": "Hi Ravi, hope you're well..."})))
    t = Task(title="Follow up with Ravi on spares", person="Ravi", status="waiting", created_at=NOW,
             last_activity_at=NOW, updated_at=NOW)
    db.add(t)
    db.commit()
    assert ai.draft_nudge(db, prefs, t, now=NOW)["written_by"] == "claude"


def test_nudge_template_without_ai(db, prefs):
    t = Task(title="Follow up with Ravi on the spares quote", person="Ravi", status="waiting", created_at=NOW,
             last_activity_at=NOW, updated_at=NOW)
    msg = ai.draft_nudge(db, prefs, t, now=NOW)["message"]
    assert msg.startswith("Hi Ravi, just a gentle reminder about the spares quote.")
