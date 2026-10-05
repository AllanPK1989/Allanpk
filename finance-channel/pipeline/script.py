"""Load a video script and turn it into a timeline of narrated segments.

A script (content/NNN-slug.yaml) has a `short` and a `long` section, each a
list of scenes. Narration lives in `say` fields:

* scene-level `say`: spoken first, before any list item is revealed
* item-level `say` (points/rows/lines/bars/slices/nodes/legend): spoken as
  that item appears on screen
* scene-level `after`: spoken once everything is visible

Every sentence becomes one TTS clip and one caption, so the picture always
changes exactly when the voice gets to it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import CONTENT, categories, config, load_yaml

SCENE_TYPES = {
    "hook", "define", "points", "compare", "steps", "stat", "bars", "donut",
    "flow", "formula", "takeaway", "line", "payoff", "candles",
}
AUTO_TYPES = {"intro", "disclaimer", "risk"}

# Which list inside each scene type is revealed item by item.
ITEM_KEYS = {
    "points": "items", "compare": "rows", "steps": "lines", "bars": "bars",
    "donut": "slices", "flow": "nodes", "formula": "legend",
}

FORMATS = ("short", "long")


@dataclass
class Segment:
    """One spoken sentence and the frame state that goes with it."""
    scene: int                 # index into Timeline.scenes
    text: str                  # sentence as written (caption)
    revealed: int              # how many list items are visible
    new_from: int = -1         # items [new_from, new_to) animate in now
    new_to: int = -1
    sentence: int = 0          # sentence index inside the scene (chart overlays use `at`)
    first: bool = False        # first segment of its scene (scene entrance animation)
    last_in_scene: bool = False
    # filled in by tts/render
    audio: Path | None = None
    duration: float = 0.0


@dataclass
class Timeline:
    script: "Script"
    fmt: str
    scenes: list[dict]
    segments: list[Segment] = field(default_factory=list)


@dataclass
class Script:
    path: Path
    data: dict

    @property
    def id(self) -> str:
        return str(self.data["id"]).zfill(3)

    @property
    def category(self) -> str:
        return self.data["category"]

    @property
    def cat(self) -> dict:
        return categories()[self.category]

    def __getitem__(self, k):
        return self.data[k]

    def get(self, k, default=None):
        return self.data.get(k, default)


def find_script(topic_id: str) -> Path | None:
    tid = str(topic_id).zfill(3)
    hits = sorted(CONTENT.glob(f"{tid}-*.yaml"))
    return hits[0] if hits else None


def load_script(path_or_id) -> Script:
    p = Path(path_or_id)
    if not p.exists():
        found = find_script(str(path_or_id))
        if not found:
            raise FileNotFoundError(f"no script for topic {path_or_id} in {CONTENT}")
        p = found
    return Script(p, load_yaml(p))


def all_scripts() -> list[Script]:
    return [load_script(p) for p in sorted(CONTENT.glob("[0-9][0-9][0-9]-*.yaml"))]


_SENT = re.compile(r"(?<=[.!?।])\s+")


def sentences(say) -> list[str]:
    if not say:
        return []
    parts = say if isinstance(say, list) else [say]
    out: list[str] = []
    for p in parts:
        out += [s.strip() for s in _SENT.split(str(p).strip()) if s.strip()]
    return out


def scene_items(scene: dict) -> list[dict]:
    t = scene["type"]
    if t == "stat":
        return [{"say": scene.get("to_say")}] if scene.get("to") else []
    items = list(scene.get(ITEM_KEYS.get(t, ""), None) or [])
    if t == "steps" and scene.get("result"):
        items.append(scene["result"])
    return items


def auto_scenes(script: Script, fmt: str) -> tuple[list[dict], list[dict]]:
    """Scenes the pipeline adds before and after the script's own scenes."""
    cfg = config()
    cat = script.cat
    head, tail = [], []
    if fmt == "long":
        long = script.data["long"]
        head.append({
            "type": "intro", "auto": True, "icon": script.get("icon") or cat.get("icon"),
            "heading": script["title_ta"], "sub": script.get("title_en"),
            "say": long.get("intro_say") or f"வணக்கம்! இன்றைய பாடம்: {script['title_ta']}",
            "chapter": "அறிமுகம்",
        })
    if script.category == "fno":
        tail.append({"type": "risk", "auto": True, "text": cfg["fno_risk"]["screen_ta"],
                     "say": cfg["fno_risk"]["say"]})
    cta = "தினமும் ஒரு நிதி பாடம் • Subscribe செய்யுங்கள்" if fmt == "short" else \
        "தினமும் ஒரு எளிய நிதி பாடம் — Subscribe செய்து தொடருங்கள்!"
    tail.append({"type": "disclaimer", "auto": True, "text": cfg["disclaimer"]["screen_full_ta"],
                 "say": cfg["disclaimer"]["say"], "cta": cta,
                 "chapter": "பொறுப்புத் துறப்பு" if fmt == "long" else None})
    return head, tail


def build_timeline(script: Script, fmt: str) -> Timeline:
    if fmt not in FORMATS:
        raise ValueError(fmt)
    body = script.data[fmt]["scenes"]
    head, tail = auto_scenes(script, fmt)
    scenes = head + list(body) + tail
    tl = Timeline(script, fmt, scenes)
    for si, sc in enumerate(scenes):
        segs = scene_segments(si, sc)
        if not segs:
            raise ValueError(f"{script.path.name} [{fmt}] scene {si} ({sc.get('type')}) has nothing to say")
        segs[0].first = True
        segs[-1].last_in_scene = True
        tl.segments += segs
    return tl


def scene_segments(si: int, sc: dict) -> list[Segment]:
    items = scene_items(sc)
    has_item_say = any(it and it.get("say") for it in items)
    segs: list[Segment] = []
    k = 0
    if not has_item_say:
        base = len(items)
    else:
        # items before the first narrated one are part of the base picture
        base = 0
        while base < len(items) and not items[base].get("say"):
            base += 1
    for s in sentences(sc.get("say")):
        segs.append(Segment(si, s, base, sentence=k))
        k += 1
    revealed = base
    if has_item_say:
        i = base
        while i < len(items):
            j = i + 1
            while j < len(items) and not items[j].get("say"):
                j += 1          # unnarrated items ride along with the narrated one before them
            revealed = j
            for n, s in enumerate(sentences(items[i].get("say"))):
                segs.append(Segment(si, s, revealed, new_from=i if n == 0 else -1,
                                    new_to=j if n == 0 else -1, sentence=k))
                k += 1
            i = j
    for s in sentences(sc.get("after")):
        segs.append(Segment(si, s, revealed if has_item_say else base, sentence=k))
        k += 1
    return segs
