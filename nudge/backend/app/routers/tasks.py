"""Tasks, checklists and baskets."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .. import tasks_service as ts
from .. import understand
from ..db import get_db
from ..deps import get_task, prefs
from ..lanes import LANES, lane, sort_key
from ..models import Basket, ChecklistItem, Task, TaskEvent
from ..schemas import (BasketIn, BasketPatch, BulkIn, ChecklistItemIn, ChecklistItemPatch, CloseIn, FocusIn,
                       FollowUpIn, NoteIn, ReorderIn, SnoozeIn, TaskIn, TaskPatch)
from ..security import require_auth
from ..serialize import basket_dict, task_dict
from ..settings_store import Prefs
from ..timeutil import iso_utc, utcnow

router = APIRouter(prefix="/api", tags=["tasks"], dependencies=[Depends(require_auth)])

BASKET_COLORS = {"blue", "orange", "teal", "amber", "pink", "green", "violet", "red", "slate"}


def _error(e: ts.TaskError):
    return HTTPException(400, str(e))


def _out(db: Session, p: Prefs, t: Task) -> dict:
    db.refresh(t)
    return task_dict(t, ts.clock(p))


# ---- tasks -------------------------------------------------------------------------------------

@router.get("/tasks")
def list_tasks(
    lane_: str | None = Query(None, alias="lane"),
    basket_id: int | None = None,
    no_basket: bool = False,
    person: str | None = None,
    q: str | None = None,
    include_dropped: bool = False,
    limit: int = Query(300, le=1000),
    db: Session = Depends(get_db),
    p: Prefs = Depends(prefs),
):
    c = ts.clock(p)
    query = db.query(Task)
    if lane_ == "done":
        statuses = ("done", "dropped") if include_dropped else ("done",)
        query = query.filter(Task.status.in_(statuses))
    elif lane_ in LANES or lane_ is None:
        query = query.filter(Task.status.in_(("open", "waiting")))
    elif lane_ != "all":
        raise HTTPException(400, "Unknown list")
    if basket_id is not None:
        query = query.filter(Task.basket_id == basket_id)
    if no_basket:
        query = query.filter(Task.basket_id.is_(None))
    if person:
        query = query.filter(func.lower(Task.person) == person.strip().lower())
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Task.title.ilike(like), Task.notes.ilike(like), Task.person.ilike(like),
                                 Task.closing_note.ilike(like)))
    rows = query.all()
    if lane_ in LANES and lane_ != "done":
        rows = [t for t in rows if lane(t, c) == lane_]
    if lane_ == "done" or lane_ == "all":
        rows.sort(key=lambda t: (t.closed_at or t.created_at), reverse=True)
    else:
        rows.sort(key=lambda t: sort_key(t, c))
    now = utcnow()
    return {"tasks": [task_dict(t, c, now) for t in rows[:limit]], "total": len(rows)}


@router.post("/tasks")
def create(body: TaskIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    data = body.model_dump()
    source = data.pop("source", "manual")
    if source not in ("manual", "text", "voice", "offline_voice"):
        source = "manual"
    try:
        t = ts.create_task(db, p, data, source=source)
    except ts.TaskError as e:
        raise _error(e)
    db.commit()
    return _out(db, p, t)


@router.get("/tasks/{task_id}")
def detail(task_id: int, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    c = ts.clock(p)
    events = db.query(TaskEvent).filter(TaskEvent.task_id == t.id).order_by(TaskEvent.id.desc()).limit(50).all()
    parent = db.get(Task, t.follows_task_id) if t.follows_task_id else None
    children = db.query(Task).filter(Task.follows_task_id == t.id).all()
    out = task_dict(t, c)
    out["history"] = [{"at": iso_utc(e.at), "kind": e.kind, "detail": e.detail} for e in events]
    out["follows"] = {"id": parent.id, "title": parent.title, "status": parent.status} if parent else None
    out["followed_by"] = [{"id": x.id, "title": x.title, "status": x.status} for x in children]
    return out


@router.patch("/tasks/{task_id}")
def update(task_id: int, body: TaskPatch, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    try:
        ts.update_task(db, p, t, body.model_dump(exclude_unset=True))
    except ts.TaskError as e:
        raise _error(e)
    db.commit()
    return _out(db, p, t)


@router.delete("/tasks/{task_id}")
def delete(task_id: int, db: Session = Depends(get_db)):
    t = get_task(db, task_id)
    db.query(Task).filter(Task.follows_task_id == t.id).update({"follows_task_id": None})
    db.delete(t)
    db.commit()
    return {"ok": True}


@router.post("/tasks/{task_id}/close")
def close(task_id: int, body: CloseIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    fu = body.follow_up.model_dump() if body.follow_up else None
    try:
        t, spawned = ts.close_task(db, p, t, note=body.note, follow_up=fu)
    except ts.TaskError as e:
        raise _error(e)
    db.commit()
    c = ts.clock(p)
    return {"task": _out(db, p, t), "spawned": [task_dict(s, c) for s in spawned]}


@router.post("/tasks/{task_id}/follow-up")
def follow_up(task_id: int, body: FollowUpIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    try:
        fu = ts.add_follow_up(db, p, t, body.model_dump())
    except ts.TaskError as e:
        raise _error(e)
    db.commit()
    return _out(db, p, fu)


@router.post("/tasks/{task_id}/closing-note")
def closing_note(task_id: int, body: NoteIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    try:
        ts.set_closing_note(db, t, body.note)
    except ts.TaskError as e:
        raise _error(e)
    db.commit()
    return _out(db, p, t)


@router.post("/tasks/{task_id}/undo-close")
def undo_close(task_id: int, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    try:
        ts.undo_close(db, p, t)
    except ts.TaskError as e:
        raise _error(e)
    db.commit()
    return _out(db, p, t)


@router.post("/tasks/{task_id}/reopen")
def reopen(task_id: int, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    ts.reopen_task(db, p, t)
    db.commit()
    return _out(db, p, t)


@router.post("/tasks/{task_id}/drop")
def drop(task_id: int, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    ts.drop_task(db, t)
    db.commit()
    return _out(db, p, t)


@router.post("/tasks/{task_id}/snooze")
def snooze(task_id: int, body: SnoozeIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    try:
        ts.snooze(db, p, t, body.preset, on=body.date, at=body.time)
    except ts.TaskError as e:
        raise _error(e)
    db.commit()
    return _out(db, p, t)


@router.post("/tasks/{task_id}/nudged")
def nudged(task_id: int, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    try:
        ts.mark_nudged(db, p, t)
    except ts.TaskError as e:
        raise _error(e)
    db.commit()
    return _out(db, p, t)


@router.post("/tasks/{task_id}/focus")
def focus(task_id: int, body: FocusIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    try:
        ts.set_focus(db, p, t, body.on)
    except ts.TaskError as e:
        raise HTTPException(409, str(e))
    db.commit()
    return _out(db, p, t)


@router.post("/tasks/{task_id}/keep")
def keep(task_id: int, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    ts.keep_stale(db, t)
    db.commit()
    return _out(db, p, t)


@router.get("/tasks/{task_id}/nudge-draft")
def nudge_draft(task_id: int, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    return understand.draft_nudge(db, p, t)


@router.post("/tasks-bulk")
def bulk(body: BulkIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    if body.action not in ("tomorrow", "done", "drop", "basket"):
        raise HTTPException(400, "Unknown action")
    n = ts.bulk(db, p, body.ids, body.action, body.basket_id)
    db.commit()
    return {"changed": n}


# ---- checklist ---------------------------------------------------------------------------------

@router.post("/tasks/{task_id}/checklist")
def add_item(task_id: int, body: ChecklistItemIn, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    t = get_task(db, task_id)
    pos = max([i.position for i in t.checklist], default=-1) + 1
    db.add(ChecklistItem(task_id=t.id, text=body.text.strip(), position=pos))
    ts.touch(t)
    db.commit()
    return _out(db, p, t)


@router.patch("/checklist/{item_id}")
def edit_item(item_id: int, body: ChecklistItemPatch, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(404, "Item not found")
    if body.text is not None and body.text.strip():
        item.text = body.text.strip()
    if body.done is not None:
        item.done = body.done
    ts.touch(item.task)
    db.commit()
    return _out(db, p, item.task)


@router.delete("/checklist/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    item = db.get(ChecklistItem, item_id)
    if item is None:
        raise HTTPException(404, "Item not found")
    task = item.task
    db.delete(item)
    db.commit()
    return _out(db, p, task)


# ---- baskets -----------------------------------------------------------------------------------

@router.get("/baskets")
def baskets(include_archived: bool = False, db: Session = Depends(get_db)):
    q = db.query(Basket)
    if not include_archived:
        q = q.filter(Basket.archived.is_(False))
    rows = q.order_by(Basket.position, Basket.id).all()
    counts = dict(db.query(Task.basket_id, func.count(Task.id)).filter(Task.status.in_(("open", "waiting")))
                  .group_by(Task.basket_id).all())
    return {"baskets": [{**basket_dict(b), "open": counts.get(b.id, 0)} for b in rows]}


def _check_basket_fields(color: str | None, name: str | None, db: Session, exclude_id: int | None = None):
    if color is not None and color not in BASKET_COLORS:
        raise HTTPException(422, "Unknown colour")
    if name is not None:
        clash = db.query(Basket).filter(func.lower(Basket.name) == name.strip().lower())
        if exclude_id:
            clash = clash.filter(Basket.id != exclude_id)
        if clash.first():
            raise HTTPException(409, "You already have a basket with that name")


@router.post("/baskets")
def add_basket(body: BasketIn, db: Session = Depends(get_db)):
    _check_basket_fields(body.color, body.name, db)
    pos = (db.query(func.max(Basket.position)).scalar() or 0) + 1
    b = Basket(name=body.name.strip(), color=body.color, icon=body.icon[:30], position=pos)
    db.add(b)
    db.commit()
    return basket_dict(b)


@router.patch("/baskets/{basket_id}")
def edit_basket(basket_id: int, body: BasketPatch, db: Session = Depends(get_db)):
    b = db.get(Basket, basket_id)
    if b is None:
        raise HTTPException(404, "Basket not found")
    _check_basket_fields(body.color, body.name, db, exclude_id=b.id)
    if body.name is not None and body.name.strip():
        b.name = body.name.strip()
    if body.color is not None:
        b.color = body.color
    if body.icon is not None:
        b.icon = body.icon[:30]
    if body.archived is not None:
        b.archived = body.archived
    db.commit()
    return basket_dict(b)


@router.delete("/baskets/{basket_id}")
def delete_basket(basket_id: int, move_to: int | None = None, db: Session = Depends(get_db)):
    b = db.get(Basket, basket_id)
    if b is None:
        raise HTTPException(404, "Basket not found")
    if move_to is not None and (move_to == b.id or db.get(Basket, move_to) is None):
        raise HTTPException(400, "Pick another basket to move the tasks to")
    db.query(Task).filter(Task.basket_id == b.id).update({"basket_id": move_to})
    db.delete(b)
    db.commit()
    return {"ok": True}


@router.post("/baskets/reorder")
def reorder(body: ReorderIn, db: Session = Depends(get_db)):
    for i, bid in enumerate(body.ids):
        b = db.get(Basket, bid)
        if b:
            b.position = i
    db.commit()
    return {"ok": True}


@router.get("/activity")
def activity(days: int = Query(14, le=90), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=days)
    rows = (db.query(TaskEvent, Task.title).join(Task, Task.id == TaskEvent.task_id)
            .filter(TaskEvent.at >= since).order_by(TaskEvent.id.desc()).limit(200).all())
    return {"events": [{"at": iso_utc(e.at), "kind": e.kind, "task_id": e.task_id, "title": title}
                       for e, title in rows]}
