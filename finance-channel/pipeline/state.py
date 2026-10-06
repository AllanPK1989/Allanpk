"""Channel state: which topics were rendered, approved, scheduled or rejected.

One small JSON file per topic in state/items/ (state/<channel>/items/ for the
other channels), committed back to the repo by the workflows. Separate files mean two workflows updating different topics
never conflict when they rebase onto each other.

Status flow:  awaiting_approval -> publishing -> scheduled | published | approved_manual
                                -> rejected
"""
from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import config, curriculum, state_dir
from .script import find_script

STATE_DIR: Path | None = None  # tests point this at a temp dir; otherwise the channel's state dir

# statuses that hold a publish slot
HOLDS_SLOT = {"publishing", "scheduled", "published", "approved_manual"}


def _dir() -> Path:
    return STATE_DIR or state_dir()


def _path(topic_id: str) -> Path:
    return _dir() / f"{str(topic_id).zfill(3)}.json"


def load() -> dict:
    items = {}
    if _dir().exists():
        for p in sorted(_dir().glob("[0-9][0-9][0-9].json")):
            items[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return {"items": items}


def get(topic_id: str) -> dict:
    p = _path(topic_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def update(topic_id: str, **fields) -> dict:
    item = get(topic_id)
    for k, v in fields.items():
        if v is None:
            item.pop(k, None)
        else:
            item[k] = v
    item["updated"] = datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds")
    p = _path(topic_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(item, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return item


def pending() -> list[str]:
    return sorted(k for k, v in load()["items"].items() if v.get("status") == "awaiting_approval")


def next_topic() -> tuple[str, bool] | None:
    """(topic id, has_script) for the first curriculum topic never rendered."""
    items = load()["items"]
    for t in curriculum():
        tid = str(t["id"]).zfill(3)
        if tid in items:
            continue
        return tid, find_script(tid) is not None
    return None


def tz() -> ZoneInfo:
    return ZoneInfo(config()["publish"].get("timezone", "Asia/Kolkata"))


def next_slot(now: datetime | None = None, lead_minutes: int = 20, ignore: str | None = None) -> datetime:
    """Next daily publish time that no other approved video already holds."""
    zone = tz()
    now = (now or datetime.now(zone)).astimezone(zone)
    hh, mm = (int(x) for x in config()["publish"]["time"].split(":"))
    taken = set()
    for k, v in load()["items"].items():
        if k != ignore and v.get("status") in HOLDS_SLOT and v.get("publish_at"):
            taken.add(datetime.fromisoformat(v["publish_at"]).astimezone(zone).date())
    day = now.date()
    while True:
        slot = datetime.combine(day, time(hh, mm), zone)
        if slot >= now + timedelta(minutes=lead_minutes) and day not in taken:
            return slot
        day += timedelta(days=1)
