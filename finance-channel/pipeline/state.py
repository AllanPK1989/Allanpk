"""Channel state: which topics were rendered, approved, scheduled or rejected.

Stored in state/state.json and committed back to the repo by the workflows, so
the history of the channel lives in git.

Status flow:  awaiting_approval -> scheduled | published | approved_manual
                                -> rejected
"""
from __future__ import annotations

import json
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import STATE_FILE, config, curriculum
from .script import find_script

DONE = {"scheduled", "published", "approved_manual"}


def load() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"items": {}}


def save(st: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def update(topic_id: str, **fields) -> dict:
    st = load()
    item = st["items"].setdefault(str(topic_id).zfill(3), {})
    for k, v in fields.items():
        if v is None:
            item.pop(k, None)
        else:
            item[k] = v
    item["updated"] = datetime.now(ZoneInfo("UTC")).isoformat(timespec="seconds")
    save(st)
    return item


def get(topic_id: str) -> dict:
    return load()["items"].get(str(topic_id).zfill(3), {})


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


def next_slot(now: datetime | None = None, lead_minutes: int = 20) -> datetime:
    """Next daily publish time that no other approved video already holds."""
    zone = tz()
    now = (now or datetime.now(zone)).astimezone(zone)
    hh, mm = (int(x) for x in config()["publish"]["time"].split(":"))
    taken = set()
    for v in load()["items"].values():
        if v.get("status") in DONE and v.get("publish_at"):
            taken.add(datetime.fromisoformat(v["publish_at"]).astimezone(zone).date())
    day = now.date()
    while True:
        slot = datetime.combine(day, time(hh, mm), zone)
        if slot >= now + timedelta(minutes=lead_minutes) and day not in taken:
            return slot
        day += timedelta(days=1)
