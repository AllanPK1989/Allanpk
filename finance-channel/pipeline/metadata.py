"""YouTube titles, descriptions and tags.

YouTube limits (Data API): title <= 100 characters, description <= 5000 *bytes*
(Tamil letters are 3 bytes each in UTF-8), tags <= 500 characters in total,
and neither title nor description may contain '<' or '>'.
"""
from __future__ import annotations

from .config import config
from .script import Script

DESC_MAX_BYTES = 4900
BASE_TAGS = ["finance in tamil", "tamil finance", "personal finance tamil", "பணம்", "நிதி",
             "முதலீடு", "money tamil", "share market tamil", "financial education", "நிதி அறிவு"]


def _clean(s: str) -> str:
    return (s or "").replace("<", "‹").replace(">", "›").replace("**", "").replace("__", "")


def _trim_title(t: str) -> str:
    t = _clean(t).strip()
    return t if len(t) <= 100 else t[:99].rstrip() + "…"


def titles(s: Script) -> dict:
    ta, en = s["title_ta"], s.get("title_en", "")
    short = f"{ta} | {en} #Shorts" if en else f"{ta} #Shorts"
    if len(short) > 100:
        short = f"{ta} #Shorts"
    long = f"{ta} | {en} | Tamil" if en else f"{ta} | Tamil"
    if len(long) > 100:
        long = ta
    return {"short": _trim_title(short), "long": _trim_title(long)}


def hashtags(s: Script) -> list[str]:
    cat_en = s.cat["en"].replace(" & ", "And").replace(" ", "")
    return ["#TamilFinance", f"#{cat_en}", "#நிதிஅறிவு"]


def tags(s: Script) -> list[str]:
    out: list[str] = []
    for t in list(s.get("keywords") or []) + list(s.cat.get("tags") or []) + BASE_TAGS + [s.get("title_en", "")]:
        t = _clean(str(t)).replace(",", " ").strip()
        if t and t.lower() not in {x.lower() for x in out}:
            out.append(t)
    # API counts a tag with spaces as len+2 (it gets quoted); stay well under 500
    kept, total = [], 0
    for t in out:
        cost = len(t) + (2 if " " in t else 0) + 1
        if total + cost > 450:
            break
        kept.append(t)
        total += cost
    return kept


def _fmt_ts(t: float) -> str:
    t = int(t)
    return f"{t // 60}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def description(s: Script, fmt: str, info: dict, other_url: str | None = None) -> str:
    cfg = config()
    d = cfg["disclaimer"]
    brand = cfg["channel"]["brand_ta"]
    default_hook = "எளிய தமிழில், ஒரு நிமிடத்தில்." if fmt == "short" else "எளிய தமிழில் முழு விளக்கம்."
    hook = s.get("description_hook") or f"{s['title_ta']} — {default_hook}"
    link = ""
    if other_url:
        label = "📺 முழு விளக்கம் (Full video)" if fmt == "short" else "📱 ஒரு நிமிட Short"
        link = f"{label}: {other_url}"
    summary = [f"• {_clean(x)}" for x in (s.get("summary") or [])]
    summary_label = "இந்த வீடியோவில்:" if fmt == "long" else "முழு விளக்க வீடியோவில்:"
    chaps = info.get("chapters") or [] if fmt == "long" else []
    chapters = "⏱️ Chapters\n" + "\n".join(f"{_fmt_ts(t)} {_clean(n)}" for t, n in chaps) if chaps else ""

    def build(summary_lines: list[str], with_chapters: bool) -> str:
        parts = [
            _clean(hook), link,
            ((summary_label + "\n") + "\n".join(summary_lines)) if summary_lines else "",
            chapters if with_chapters else "",
            f"📌 “{brand}” — தினமும் ஒரு எளிய நிதி பாடம், தமிழில். பாகம் #{int(s.id)}.",
            _clean(d["description_ta"]).strip(),
            _clean(d["description_en"]).strip(),
            _clean(d["ai_voice_note"]).strip(),
            " ".join(hashtags(s) + (["#Shorts"] if fmt == "short" else [])),
        ]
        return "\n\n".join(p for p in parts if p)

    # Over the byte limit: shed summary lines, then chapters; never the disclaimers.
    text = build(summary, True)
    while len(text.encode("utf-8")) > DESC_MAX_BYTES and summary:
        summary = summary[:-1]
        text = build(summary, True)
    if len(text.encode("utf-8")) > DESC_MAX_BYTES:
        text = build(summary, False)
    return text


def video_body(s: Script, fmt: str, info: dict, publish_at: str | None, other_url: str | None) -> dict:
    """The `snippet` + `status` body for videos.insert."""
    pub = config()["publish"]
    status = {
        "selfDeclaredMadeForKids": bool(pub.get("made_for_kids", False)),
        "embeddable": True,
        "license": "youtube",
    }
    if publish_at:
        status.update(privacyStatus="private", publishAt=publish_at)
    else:
        status["privacyStatus"] = "public"
    if pub.get("contains_synthetic_media"):
        status["containsSyntheticMedia"] = True
    return {
        "snippet": {
            "title": titles(s)[fmt],
            "description": description(s, fmt, info, other_url),
            "tags": tags(s),
            "categoryId": str(pub.get("category_id", "27")),
            "defaultLanguage": "ta",
            "defaultAudioLanguage": "ta",
        },
        "status": status,
    }
