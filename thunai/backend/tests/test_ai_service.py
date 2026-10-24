from app.ai import service as ai_service
from app.ai.base import AIResult

from .conftest import login

GOOD_STEP = {
    "step_no": 1, "kind": "check", "action_en": "Check the coil LED.", "action_ta": "Coil LED பாருங்க.",
    "check_en": "", "check_ta": "", "expected_result_en": "", "expected_result_ta": "", "tools": [],
    "safety_note_en": "", "safety_note_ta": "", "authorised_only": False, "if_ok_next": 0,
    "if_not_ok_next": -1, "source_refs": [], "confidence": 0.4,
}


def procedure(steps):
    return {
        "summary_en": "x", "summary_ta": "x", "likely_causes": [], "steps": steps, "confidence": 0.4,
        "refuse": False, "refuse_reason_en": "", "refuse_reason_ta": "",
    }


class ScriptedProvider:
    """Returns queued answers for troubleshoot calls; clarify asks nothing."""

    name = "scripted"

    def __init__(self, troubleshoot_answers):
        self.answers = list(troubleshoot_answers)
        self.calls = []

    def generate_json(self, *, tier, purpose, system, user, schema, max_tokens, hints):
        self.calls.append((purpose, user))
        if purpose == "clarify":
            return AIResult({"understood_problem_en": "x", "questions": []}, "claude-opus-5-5", input_tokens=1000, output_tokens=100)
        data = self.answers.pop(0)
        return AIResult(data, "claude-opus-5-5", input_tokens=2000, output_tokens=500)


def start(client, h):
    return client.post(
        "/api/ai/sessions", headers=h, json={"machine_no": "DEMO-RT-01", "problem_text": "Test station shows OPEN", "language": "en"}
    ).json()


def test_invalid_output_is_retried_once_then_succeeds(client, monkeypatch):
    provider = ScriptedProvider([{"steps": "not a list"}, procedure([GOOD_STEP])])
    monkeypatch.setattr(ai_service, "get_provider", lambda: provider)
    s = start(client, login(client, "D-TECH2"))
    assert s["outcome"] == "in_progress"
    assert [p for p, _ in provider.calls] == ["clarify", "troubleshoot", "troubleshoot"]
    assert "previous answer was rejected" in provider.calls[-1][1]
    assert s["steps"][0]["kind"] == "safety" and s["steps"][1]["general"]
    assert s["procedure"]["low_confidence"]
    assert s["cost_usd"] > 0  # tokens and cost are recorded per session


def test_unsafe_output_twice_ends_in_call_supervisor(client, monkeypatch):
    bad = dict(GOOD_STEP, action_en="Bypass the door interlock with a jumper wire.")
    provider = ScriptedProvider([procedure([bad]), procedure([bad])])
    monkeypatch.setattr(ai_service, "get_provider", lambda: provider)
    s = start(client, login(client, "D-TECH2"))
    assert s["outcome"] == "failed"
    assert s["steps"] == []
    assert s["procedure"]["call_supervisor"]


def test_model_refusal_flag_is_respected(client, monkeypatch):
    refused = procedure([])
    refused.update(refuse=True, refuse_reason_en="Unsafe request", refuse_reason_ta="ஆபத்து")
    provider = ScriptedProvider([refused])
    monkeypatch.setattr(ai_service, "get_provider", lambda: provider)
    s = start(client, login(client, "D-TECH2"))
    assert s["outcome"] == "refused" and s["procedure"]["refuse_reason_en"] == "Unsafe request"


def test_cost_calculation_uses_price_table():
    # Opus 5.5: $4 in / $20 out per million tokens; cache reads at 0.1x, cache writes at 1.25x.
    assert ai_service.cost_usd("claude-opus-5-5", 1_000_000, 0, 0, 0) == 4.0
    assert ai_service.cost_usd("claude-opus-5-5", 0, 1_000_000, 0, 0) == 20.0
    assert ai_service.cost_usd("claude-opus-5-5", 0, 0, 1_000_000, 0) == 0.4
    assert ai_service.cost_usd("mock", 1000, 1000, 0, 0) == 0.0
