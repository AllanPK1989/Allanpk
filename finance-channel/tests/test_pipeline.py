"""Fast tests (no browser, no network): python -m pytest tests -q"""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from pipeline import state
from pipeline.compliance import Report, check_text, lint
from pipeline.metadata import description, tags, titles
from pipeline.script import Script, all_scripts, build_timeline, load_script
from pipeline.tts import for_voice

FIXTURE = Path(__file__).parent / "all-scenes.yaml"


def errors_for(text: str, allow=()) -> list[str]:
    rep = Report()
    check_text([("t", text)], set(allow), rep)
    return rep.errors


@pytest.mark.parametrize("bad", [
    "Buy now before it's too late",
    "இந்த பங்கை வாங்குங்கள்",
    "target price ₹450",
    "stop loss at 120",
    "guaranteed profit every month",
    "Join our Telegram channel",
    "உறுதியான லாபம் கிடைக்கும்",
    "Reliance பங்கு பற்றி பார்க்கலாம்",
    "ரிலையன்ஸ் பற்றி",
    "visit https://example.com",
    "இது ஒரு multibagger",
])
def test_compliance_blocks_advice_and_names(bad):
    assert errors_for(bad), bad


@pytest.mark.parametrize("ok", [
    "பணவீக்கம் ஆண்டுக்கு ஆறு சதவீதம் என்று வைத்துக்கொள்வோம்.",
    "Company A-வின் லாபம் பத்து கோடி ரூபாய் என்று வைத்துக்கொள்வோம்.",
    "Nifty 50 என்பது ஐம்பது பெரிய நிறுவனங்களின் ஒரு கூடை.",
    "Call option வாங்குபவருக்கு, ஒரு குறிப்பிட்ட விலையில் வாங்கும் உரிமை உண்டு.",
])
def test_compliance_allows_education(ok):
    assert not errors_for(ok), ok


def test_allow_names_whitelists():
    assert errors_for("Google Sheets-இல் பட்ஜெட் போடலாம்")
    assert not errors_for("Google Sheets-இல் பட்ஜெட் போடலாம்", allow=["Google"])


def test_for_voice_rewrites_terms_and_money():
    v = for_voice("**SIP** மூலம் ₹1,00,000 முதலீடு, 12% வருமானம்")
    assert "எஸ்.ஐ.பி" in v and "100000 ரூபாய்" in v and "சதவீதம்" in v
    assert "**" not in v and "₹" not in v and "SIP" not in v
    assert for_voice("ESIP") == "ESIP"  # only whole words are rewritten


def test_every_content_script_lints_clean():
    scripts = all_scripts()
    assert scripts
    for s in scripts:
        rep = lint(s)
        assert not rep.errors, (s.path.name, rep.errors)


def test_fixture_timeline_reveals_items_in_order():
    s = Script(FIXTURE, yaml.safe_load(FIXTURE.read_text(encoding="utf-8")))
    s.data["long"]["scenes"] = s.data["short"]["scenes"]
    tl = build_timeline(s, "short")
    compare = [seg for seg in tl.segments if tl.scenes[seg.scene]["type"] == "compare"]
    assert [seg.revealed for seg in compare] == [1, 2]
    assert compare[0].first and not compare[1].first
    types = [sc["type"] for sc in tl.scenes]
    assert types[-2:] == ["risk", "disclaimer"]  # fno topics get the SEBI risk line
    long_types = [sc["type"] for sc in build_timeline(s, "long").scenes]
    assert long_types[0] == "intro"


def test_metadata_limits():
    for s in all_scripts():
        for f in ("short", "long"):
            assert len(titles(s)[f]) <= 100
            d = description(s, f, {"chapters": [[0, "அறிமுகம்"], [20, "ஒன்று"], [40, "இரண்டு"]]}, "https://youtu.be/x")
            assert len(d.encode()) <= 5000 and "<" not in d and ">" not in d
            assert "SEBI" in d and "Disclaimer" in d
        assert sum(len(t) + 3 for t in tags(s)) <= 500


def test_next_slot_skips_taken_days(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_FILE", tmp_path / "state.json")
    ist = ZoneInfo("Asia/Kolkata")
    morning = datetime(2026, 10, 5, 9, 0, tzinfo=ist)
    assert state.next_slot(morning) == datetime(2026, 10, 5, 18, 0, tzinfo=ist)
    evening = datetime(2026, 10, 5, 17, 50, tzinfo=ist)  # inside the 20-minute lead time
    assert state.next_slot(evening).date().day == 6
    state.update("001", status="scheduled", publish_at=datetime(2026, 10, 5, 18, 0, tzinfo=ist).isoformat())
    assert state.next_slot(morning).date().day == 6


def test_load_script_by_id():
    assert load_script("001").id == "001"


def test_publish_youtube_mode_uploads_long_then_short(tmp_path, monkeypatch):
    import json
    from pipeline import __main__ as cli
    from pipeline import config as cfgmod
    from pipeline import youtube

    monkeypatch.setattr(state, "STATE_FILE", tmp_path / "state.json")
    real = cfgmod.config()
    patched = {**real, "publish": {**real["publish"], "mode": "youtube", "audited": True}}
    monkeypatch.setattr(cfgmod, "config", lambda: patched)
    calls = []
    monkeypatch.setattr(youtube, "configured", lambda: True)
    monkeypatch.setattr(youtube, "upload", lambda video, body, thumb=None: calls.append((video.name, body)) or f"vid{len(calls)}")
    d = tmp_path / "001"
    d.mkdir()
    for f in ("short", "long"):
        (d / f"001-{f}.json").write_text(json.dumps({"file": f"001-{f}.mp4", "duration": 60, "chapters": []}))
    cli.main(["publish", "001", "--dir", str(d), "--comment-file", str(tmp_path / "c.md")])

    assert [c[0] for c in calls] == ["001-long.mp4", "001-short.mp4"]
    long_body, short_body = calls[0][1], calls[1][1]
    assert long_body["status"]["privacyStatus"] == "private"
    assert long_body["status"]["publishAt"].endswith("Z")
    assert "https://youtu.be/vid1" in short_body["snippet"]["description"]
    assert short_body["snippet"]["defaultAudioLanguage"] == "ta"
    item = state.get("001")
    assert item["status"] == "scheduled" and item["youtube"]["short"]["id"] == "vid2"
    assert "youtu.be/vid2" in (tmp_path / "c.md").read_text(encoding="utf-8")


def test_generator_retries_until_lint_passes(tmp_path, monkeypatch):
    """Stubbed Claude: first reply breaks the rules, second is valid."""
    import types
    import anthropic
    from pipeline import generate

    good = (Path(__file__).parent.parent / "content" / "002-compounding.yaml").read_text(encoding="utf-8")
    bad = good.replace("கூட்டு வட்டியின் சக்தி\"", "Reliance பங்கு\"", 1)
    replies = iter([bad, good])
    sent = []

    class Stream:
        def __init__(self, text): self.text = text
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get_final_message(self):
            block = types.SimpleNamespace(type="text", text=f"```yaml\n{self.text}```")
            return types.SimpleNamespace(stop_reason="end_turn", content=[block])

    class FakeClient:
        def __init__(self, *a, **k):
            self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(stream=self.stream))
        def stream(self, **kw):
            sent.append(kw)
            return Stream(next(replies))

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    monkeypatch.setattr(generate, "CONTENT", tmp_path)
    monkeypatch.setattr(generate, "find_script", lambda tid: None)
    out = generate.generate("031")

    assert out.parent == tmp_path and out.name == "031-net-worth.yaml"
    saved = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert saved["id"] == "031" and saved["category"] == "basics"
    assert len(sent) == 2
    assert sent[0]["model"] == "claude-opus-5-5"
    fix_request = sent[1]["messages"][-1]["content"]
    assert "Reliance" in fix_request  # lint errors were fed back
