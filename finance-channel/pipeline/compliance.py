"""Script validation: structure + SEBI-safe content rules (see compliance.yaml)."""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field

from .config import ROOT, categories, load_yaml
from .script import FORMATS, ITEM_KEYS, SCENE_TYPES, Script, build_timeline, sentences

REQUIRED = {
    "hook": ["heading"], "define": ["term", "text"], "points": ["items"],
    "compare": ["left", "right", "rows"], "steps": ["lines"], "stat": ["value"],
    "bars": ["bars"], "donut": ["slices"], "flow": ["nodes"], "formula": ["formula"],
    "takeaway": ["text"], "line": ["series"], "payoff": ["option"], "candles": [],
}
TEXT_KEYS = {"heading", "sub", "term", "term_en", "text", "label", "kicker", "caption", "value", "to",
             "say", "after", "to_say", "title", "left", "right", "note", "center", "formula", "display",
             "chapter", "name", "intro_say", "tag"}


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@functools.cache
def rules() -> dict:
    r = load_yaml(ROOT / "compliance.yaml")
    r["_err"] = [(re.compile(x["pattern"], re.I), x["why"]) for x in r.get("errors", [])]
    r["_warn"] = [(re.compile(x["pattern"], re.I), x["why"]) for x in r.get("warnings", [])]
    return r


def _texts(node, path="") -> list[tuple[str, str]]:
    """Every human-readable string in the script with a breadcrumb path."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}" if path else str(k)
            if isinstance(v, str) and (k in TEXT_KEYS or k in ("title_ta", "title_en", "thumb_ta", "thumb_en")):
                out.append((p, v))
            elif isinstance(v, (dict, list)):
                out += _texts(v, p)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            p = f"{path}[{i}]"
            if isinstance(v, str):
                out.append((p, v))
            else:
                out += _texts(v, p)
    return out


def _name_pattern(name: str) -> re.Pattern:
    if re.search(r"[A-Za-z]", name):
        return re.compile(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", re.I)
    return re.compile(re.escape(name))


def check_text(texts: list[tuple[str, str]], allow: set[str], rep: Report, phrases: tuple[str, ...] = ()) -> None:
    r = rules()
    names = [(n, _name_pattern(n)) for n in r.get("securities", []) if n not in allow]
    for where, t in texts:
        for ph in phrases:  # e.g. a scam-awareness video quoting a scammer's pitch
            t = t.replace(ph, "")
        for rx, why in r["_err"]:
            m = rx.search(t)
            if m:
                rep.errors.append(f"{where}: {why}: “{m.group(0)}”")
        for n, rx in names:
            if rx.search(t):
                rep.errors.append(f"{where}: names a specific company/fund/broker “{n}”; use a hypothetical "
                                  f"(“Company A”, “ஒரு நிறுவனம்”) or add it to allow_names with a reason")
        for rx, why in r["_warn"]:
            m = rx.search(t)
            if m:
                rep.warnings.append(f"{where}: {why}: “{m.group(0)}”")


def check_structure(s: Script, rep: Report) -> None:
    d = s.data
    for k in ("id", "category", "title_ta", "title_en", "summary", "keywords", "short", "long"):
        if k not in d:
            rep.errors.append(f"missing top-level field `{k}`")
    if rep.errors:
        return
    if not s.path.name.startswith(s.id + "-") and s.path.parent.name == "content":
        rep.errors.append(f"file name {s.path.name} doesn't start with id {s.id}")
    if d["category"] not in categories():
        rep.errors.append(f"unknown category {d['category']} (see categories.yaml)")
    if len(d["title_ta"]) > 60:
        rep.warnings.append("title_ta is long; YouTube titles read best under ~60 characters")
    for fmt in FORMATS:
        scenes = (d.get(fmt) or {}).get("scenes") or []
        if not scenes:
            rep.errors.append(f"{fmt}: no scenes")
            continue
        for i, sc in enumerate(scenes):
            t = sc.get("type")
            where = f"{fmt}.scenes[{i}]"
            if t not in SCENE_TYPES:
                rep.errors.append(f"{where}: unknown type {t!r} (allowed: {', '.join(sorted(SCENE_TYPES))})")
                continue
            for req in REQUIRED[t]:
                if req not in sc:
                    rep.errors.append(f"{where} ({t}): missing `{req}`")
            if t == "candles" and not (sc.get("candles") or sc.get("preset")):
                rep.errors.append(f"{where} (candles): needs `candles` or `preset`")
            key = ITEM_KEYS.get(t)
            for j, it in enumerate(sc.get(key, []) or [] if key else []):
                if not isinstance(it, dict):
                    rep.errors.append(f"{where}.{key}[{j}]: must be a mapping")
            for sent in sentences(sc.get("say")) + [x for it in (sc.get(key, []) or [] if key else []) if isinstance(it, dict) for x in sentences(it.get("say"))]:
                if len(sent) > 230:
                    rep.warnings.append(f"{where}: very long sentence ({len(sent)} chars); split it for clearer captions")
        try:
            tl = build_timeline(s, fmt)
            chars = sum(len(seg.text) for seg in tl.segments)
            est = chars / 13.0 + len(tl.segments) * 0.3
            lo, hi = (20, 170) if fmt == "short" else (70, 420)
            if not lo <= est <= hi:
                rep.warnings.append(f"{fmt}: estimated length {est:.0f}s is outside {lo}-{hi}s")
        except Exception as e:  # noqa: BLE001
            rep.errors.append(f"{fmt}: {e}")


def lint(s: Script) -> Report:
    rep = Report()
    check_structure(s, rep)
    allow = set(s.get("allow_names") or [])
    phrases = tuple(s.get("allow_phrases") or [])
    check_text(_texts(s.data), allow, rep, phrases)
    if phrases:
        rep.warnings.append(f"allow_phrases skips checks for: {', '.join(phrases)}; make sure each is quoted as a warning")
    rep.errors = list(dict.fromkeys(rep.errors))
    rep.warnings = list(dict.fromkeys(rep.warnings))
    return rep
