"""Write a channel's script (e.g. English) from the Tamil script with the same id.

The Tamil script in content/ stays the source. Claude adapts it scene by
scene into the active channel's language, keeping the same scenes, numbers and
icons, so both channels teach exactly the same lesson. Like generated Tamil
scripts, the result must pass the lint; errors (and any change to the scene
structure) go back to Claude for a fix, up to MAX_FIXES times.

Needs ANTHROPIC_API_KEY.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .compliance import lint
from .config import CONTENT, ROOT, config, content_dir, curriculum, lang, load_yaml, loc
from .generate import MAX_FIXES, MODEL, _call, _extract_yaml, available  # noqa: F401 - available re-exported
from .script import FORMATS, ITEM_KEYS, Script, find_script

LANG_NAMES = {"en": "English", "ta": "Tamil"}
HEADER = "# Translated by Claude ({model}) from {source}; review before approving.\n"


def _system_prompt() -> str:
    guide = (ROOT / "docs" / "WRITING_GUIDE.md").read_text(encoding="utf-8")
    language = LANG_NAMES.get(lang(), lang())
    brand = loc(config()["channel"], "brand")
    return (
        f"You adapt video scripts for “{brand}”, the {language} sister channel of “நிதி அறிவு”, a Tamil "
        "YouTube channel that teaches personal finance and investing basics to Indian beginners, one concept "
        "per video. Both channels post the same lesson on the same day. The channel owner is not a "
        "SEBI-registered adviser, so every script is strictly educational.\n\n"
        "The writing guide below was written for the Tamil channel. Its YAML format, scene reference, "
        "styling markers and compliance rules apply unchanged; its advice on Tamil wording does not.\n\n"
        f"<writing_guide>\n{guide}\n</writing_guide>\n\n"
        f"How to adapt a Tamil script into {language}:\n"
        "- Keep the structure identical: the same scenes in the same order, the same `type`, the same number "
        "of items in every list, and the same numbers, `icon`, `accent`, chart data and other non-text fields. "
        "Only text changes.\n"
        f"- Write natural, warm, plain {language} for Indian viewers (Indian English: ₹, lakh and crore are "
        "fine). Adapt idioms instead of translating word for word, but keep every fact and example.\n"
        "- Translate every on-screen field (heading, sub, text, label, caption, items, chapter, ...) and every "
        "narration field (say, to_say, after, intro_say). Narration is spoken by an AI voice: short sentences, "
        "written the way they should be said.\n"
        "- Top level: put the English title in `title_en` (use the one given), an optional short punchy "
        "`thumb_en`, and English `summary` and `keywords`. Drop `title_ta` and `thumb_ta`. Keep `id`, "
        "`category`, `icon`, `allow_names` and `allow_phrases` (translate the phrases).\n"
        "- In `define` scenes, `term` becomes the English term; keep `term_en` only for an expansion of an "
        "abbreviation (for example term \"CPI\", term_en \"Consumer Price Index\"), otherwise drop it.\n"
        "- Keep the **bold**, __highlight__, ++good++ and --bad-- markers on the matching words.\n\n"
        "Reply with the complete script as a single ```yaml fenced block and nothing else."
    )


def _shape(data: dict) -> dict:
    """Scene types and list lengths per format: what a translation must not change."""
    out = {}
    for fmt in FORMATS:
        scenes = (data.get(fmt) or {}).get("scenes") or []
        out[fmt] = [(sc.get("type"), len(sc.get(ITEM_KEYS.get(sc.get("type"), ""), None) or []))
                    for sc in scenes if isinstance(sc, dict)]
    return out


def _shape_problems(src: dict, dst: dict) -> list[str]:
    a, b = _shape(src), _shape(dst)
    problems = []
    for fmt in FORMATS:
        if a[fmt] != b[fmt]:
            problems.append(f"{fmt}: the scenes must match the Tamil script exactly (type and number of items "
                            f"per scene). Tamil: {a[fmt]}. Yours: {b[fmt]}.")
    return problems


def source_script(topic_id: str) -> Path | None:
    return find_script(topic_id, CONTENT)


def translate(topic_id: str) -> Path:
    import anthropic

    if lang() == "ta":
        raise ValueError("pick the target channel, e.g. python -m pipeline --channel en translate 001")
    tid = str(topic_id).zfill(3)
    src_path = source_script(tid)
    if src_path is None:
        raise FileNotFoundError(f"topic {tid} has no Tamil script in content/ to translate")
    if find_script(tid):
        raise FileExistsError(f"topic {tid} already has a script in {content_dir().relative_to(ROOT)}")
    src = load_yaml(src_path)
    topic = next((t for t in curriculum() if str(t["id"]).zfill(3) == tid), {})
    title = topic.get(f"title_{lang()}") or src.get(f"title_{lang()}") or src.get("title_en", "")
    out = content_dir() / src_path.name

    client = anthropic.Anthropic()
    system = _system_prompt()
    messages: list[dict] = [{"role": "user", "content": (
        f"Adapt this Tamil script into {LANG_NAMES.get(lang(), lang())}. Use the title “{title}”.\n\n"
        f"<tamil_script file=\"{src_path.name}\">\n{src_path.read_text(encoding='utf-8')}\n</tamil_script>")}]

    problems: list[str] = []
    for attempt in range(MAX_FIXES + 1):
        msg = _call(client, system, messages)
        text = _extract_yaml("".join(b.text for b in msg.content if b.type == "text"))
        try:
            data = yaml.safe_load(text)
            if not isinstance(data, dict):
                raise ValueError("the reply is not a YAML mapping")
            data["id"] = tid
            data["category"] = src["category"]
            data.setdefault(f"title_{lang()}", title)
            for k in ("title_ta", "thumb_ta"):
                data.pop(k, None)
            problems = _shape_problems(src, data) + lint(Script(out, data)).errors
        except Exception as e:  # noqa: BLE001 - YAML/shape errors go back to the model
            problems = [f"could not parse the YAML: {e}"]
        if not problems:
            out.parent.mkdir(parents=True, exist_ok=True)
            body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
            out.write_text(HEADER.format(model=MODEL, source=f"content/{src_path.name}") + body, encoding="utf-8")
            return out
        if attempt == MAX_FIXES:
            break
        messages += [
            {"role": "assistant", "content": msg.content},
            {"role": "user", "content": "The script failed validation. Fix every problem below and reply "
                                        "with the full corrected script:\n" + "\n".join(f"- {p}" for p in problems)},
        ]
    raise RuntimeError(f"translated script for {tid} still fails validation:\n" + "\n".join(problems))
