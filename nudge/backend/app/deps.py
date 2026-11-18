"""Shared route helpers."""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Task
from .settings_store import Prefs


def prefs(db: Session = Depends(get_db)) -> Prefs:
    return Prefs(db)


def get_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task
