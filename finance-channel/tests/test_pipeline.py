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
    monkeypatch.setattr(state, "STATE_DIR", tmp_path / "items")
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

    monkeypatch.setattr(state, "STATE_DIR", tmp_path / "items")
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
    monkeypatch.setattr(generate, "find_script", lambda *a, **k: None)
    out = generate.generate("031")

    assert out.parent == tmp_path and out.name == "031-net-worth.yaml"
    saved = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert saved["id"] == "031" and saved["category"] == "basics"
    assert len(sent) == 2
    assert sent[0]["model"] == "claude-opus-5-5"
    fix_request = sent[1]["messages"][-1]["content"]
    assert "Reliance" in fix_request  # lint errors were fed back


def test_reservations_take_consecutive_days(tmp_path, monkeypatch):
    from pipeline import __main__ as cli
    monkeypatch.setattr(state, "STATE_DIR", tmp_path / "items")
    for tid in ("001", "002", "003"):
        state.update(tid, status="awaiting_approval")
        cli.main(["reserve", tid])
    days = sorted(datetime.fromisoformat(state.get(t)["publish_at"]).date() for t in ("001", "002", "003"))
    assert len(set(days)) == 3 and (days[2] - days[0]).days == 2
    # re-reserving the same topic doesn't block itself
    before = state.get("002")["publish_at"]
    cli.main(["reserve", "002"])
    assert datetime.fromisoformat(state.get("002")["publish_at"]) <= datetime.fromisoformat(before)


# --- recorded voice ---------------------------------------------------------

def test_voice_script_lists_each_sentence_once_with_its_formats():
    from pipeline.tts import clip_key
    from pipeline.voice import voice_script
    s = load_script("001")
    vs = voice_script(s)
    keys = [it["key"] for it in vs["sentences"]]
    assert len(keys) == len(set(keys))
    for fmt in ("short", "long"):
        for seg in build_timeline(s, fmt).segments:
            assert clip_key(seg.text) in keys
    shared = [it for it in vs["sentences"] if it["formats"] == ["short", "long"]]
    assert shared, "the spoken disclaimer is the same in both formats, so it should be recorded once"
    assert all("**" not in it["text"] and "__" not in it["text"] for it in vs["sentences"])


def test_committed_voice_scripts_exist_for_every_script():
    from pipeline.voice import VOICE_SCRIPTS
    for s in all_scripts():
        assert (VOICE_SCRIPTS / f"{s.id}.json").exists(), f"run: python -m pipeline voice-script {s.id}"


def test_synthesize_uses_recordings_and_names_missing_ones(tmp_path):
    from pipeline.tts import MissingRecording, clip_key, synthesize
    texts = ["முதல் வாக்கியம்.", "இரண்டாவது **வாக்கியம்**."]
    (tmp_path / f"{clip_key(texts[0])}.wav").write_bytes(b"")
    with pytest.raises(MissingRecording) as e:
        synthesize(texts, "short", voice_dir=tmp_path)
    assert e.value.missing == [texts[1]]
    (tmp_path / f"{clip_key('இரண்டாவது வாக்கியம்.')}.wav").write_bytes(b"")
    assert len(synthesize(texts, "short", voice_dir=tmp_path)) == 2


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="needs ffmpeg")
def test_import_zip_cleans_clips_and_reports_gaps(tmp_path):
    import subprocess
    import zipfile
    from pipeline.tts import wav_duration
    from pipeline.voice import import_zip, report_markdown, voice_script
    s = load_script("001")
    sents = voice_script(s)["sentences"]
    tone, hush = tmp_path / "tone.wav", tmp_path / "hush.wav"
    for out, src in ((tone, "sine=frequency=220:duration=1.5"), (hush, "anullsrc=r=48000:cl=mono")):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src, "-t", "1.5", str(out)], check=True)
    zp = tmp_path / "001-voice.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.write(tone, f"voice/{sents[0]['key']}.wav")
        z.write(tone, f"voice/{sents[1]['key']}.wav")
        z.write(hush, f"voice/{sents[2]['key']}.wav")       # silent take
        z.write(tone, "voice/0123456789ab.wav")             # from an older script version
        z.writestr("manifest.json", "{}")
    out = tmp_path / "clips"
    rep = import_zip(s, zp, out)
    assert (rep["expected"], rep["imported"], rep["unknown"]) == (len(sents), 2, 1)
    assert rep["too_short"] == [sents[2]["text"]]
    assert len(rep["missing"]) == len(sents) - 3
    assert 1.2 < wav_duration(out / f"{sents[0]['key']}.wav") < 1.6
    assert not (out / f"{sents[2]['key']}.wav").exists()
    md = report_markdown(rep)
    assert "2 of" in md and sents[2]["text"] in md and sents[3]["text"] in md


def test_recorder_url_points_at_github_pages():
    from pipeline.review import recorder_url
    assert recorder_url("https://github.com/AllanPK1989/allanpk", "007") == "https://allanpk1989.github.io/allanpk/?t=007"


# ---------- the English channel (channels/en.yaml) ----------

TAMIL_CHARS = __import__("re").compile(r"[஀-௿]")


@pytest.fixture
def en(monkeypatch):
    monkeypatch.setenv("FINANCE_CHANNEL", "en")


def test_english_profile_overrides_only_what_differs(en):
    from pipeline.config import config, content_dir, release_tag, state_dir
    cfg = config()
    assert cfg["channel"]["language"] == "en" and cfg["voice"]["name"].startswith("en-IN-")
    assert cfg["voice"]["engine"] == "edge" and cfg["publish"]["time"] == "18:00"  # merged from config.yaml
    assert "SEBI" not in cfg["pronounce"]  # replaced, not merged
    assert content_dir().as_posix().endswith("content/en") and state_dir().as_posix().endswith("state/en/items")
    assert release_tag("7") == "video-en-007"


def test_tamil_is_still_the_default(monkeypatch):
    from pipeline.config import config, release_tag
    monkeypatch.delenv("FINANCE_CHANNEL", raising=False)
    assert config()["channel"]["language"] == "ta" and release_tag("1") == "video-001"


def test_every_english_script_lints_clean_and_matches_its_tamil_script(en):
    from pipeline.config import CONTENT, load_yaml
    from pipeline.translate import _shape_problems
    scripts = all_scripts()
    assert scripts, "no English scripts in content/en"
    for s in scripts:
        assert s.path.parent.name == "en"
        rep = lint(s)
        assert not rep.errors, f"{s.path.name}: {rep.errors}"
        assert not _shape_problems(load_yaml(CONTENT / s.path.name), s.data), s.path.name
        for f in ("short", "long"):
            for seg in build_timeline(s, f).segments:
                assert not TAMIL_CHARS.search(seg.text), f"{s.path.name} {f}: Tamil text in “{seg.text}”"


def test_english_metadata_is_all_english(en):
    from pipeline.metadata import video_body
    s = load_script("001")
    body = video_body(s, "long", {"chapters": [[0, "Introduction"], [20, "a"], [40, "b"]]}, None, None)
    sn = body["snippet"]
    assert sn["defaultLanguage"] == "en" and sn["defaultAudioLanguage"] == "en"
    assert sn["title"] == "What is Inflation? | Personal Finance Basics"
    assert titles(s)["short"] == "What is Inflation? #Shorts"
    for text in [sn["title"], sn["description"], *sn["tags"]]:
        assert not TAMIL_CHARS.search(text), text
    assert "SEBI" in sn["description"] and "#PersonalFinance" in sn["description"]
    intro = build_timeline(s, "long").scenes[0]
    assert intro["heading"] == "What is Inflation?" and intro["sub"] is None and intro["chapter"] == "Introduction"


def test_for_voice_english(en):
    assert for_voice("A **₹1 lakh** FD at 7%") == "A 1 lakh rupees FD at 7%"
    assert for_voice("₹1,00,000 × 2 = ₹2,00,000") == "1,00,000 rupees times 2 equals 2,00,000 rupees"
    assert for_voice("Equity F&O") == "Equity F and O"


def test_translator_keeps_the_tamil_structure(tmp_path, monkeypatch, en):
    """Stubbed Claude: first reply drops a scene, second is valid."""
    import types
    import anthropic
    from pipeline import translate

    good = (Path(__file__).parent.parent / "content" / "en" / "001-inflation.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(good)
    short = dict(data["short"], scenes=data["short"]["scenes"][:-1])
    bad = yaml.safe_dump({**data, "short": short}, allow_unicode=True, sort_keys=False)
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
    monkeypatch.setattr(translate, "content_dir", lambda: tmp_path)
    monkeypatch.setattr(translate, "find_script", lambda tid, directory=None: None)
    monkeypatch.setattr(translate, "source_script", lambda tid: Path(__file__).parent.parent / "content" / "001-inflation.yaml")
    out = translate.translate("001")

    assert out == tmp_path / "001-inflation.yaml"
    saved = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert saved["title_en"] == "What is Inflation?" and "title_ta" not in saved
    assert len(sent) == 2
    assert "must match the Tamil script" in sent[1]["messages"][-1]["content"]
    assert "பணவீக்கம்" in sent[0]["messages"][0]["content"]  # the Tamil source was sent


def test_channel_flag_picks_the_queue(monkeypatch, capsys):
    import os
    from pipeline import __main__ as cli
    from pipeline.config import ROOT
    monkeypatch.delenv("FINANCE_CHANNEL", raising=False)
    assert state._dir() == ROOT / "state" / "items"
    cli.main(["--channel", "en", "status"])
    assert os.environ["FINANCE_CHANNEL"] == "en"
    assert state._dir() == ROOT / "state" / "en" / "items"
    assert "What is Inflation?" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["--channel", "xx", "status"])
