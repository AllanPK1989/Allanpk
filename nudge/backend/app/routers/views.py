"""Read-only views: dashboard, briefing, wrap-up, weekly review, people."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import dashboard as dash
from ..db import get_db
from ..deps import prefs
from ..security import require_auth
from ..settings_store import Prefs

router = APIRouter(prefix="/api", tags=["views"], dependencies=[Depends(require_auth)])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    return dash.dashboard(db, p)


@router.get("/briefing")
def briefing(db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    return dash.briefing(db, p)


@router.get("/wrapup")
def wrapup(db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    return dash.wrapup(db, p)


@router.get("/review")
def review(offset: int = Query(0, ge=0, le=52), db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    return dash.weekly_review(db, p, offset=offset)


@router.get("/people")
def people(db: Session = Depends(get_db), p: Prefs = Depends(prefs)):
    return {"people": dash.people(db, p)}


@router.get("/people/names")
def people_names(db: Session = Depends(get_db)):
    return {"names": dash.known_people(db, limit=200)}
