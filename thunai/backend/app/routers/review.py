from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import serialize
from ..db import get_db
from ..models import AISession, BreakdownLog, User
from ..security import supervisor_or_admin

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/queue")
def queue(user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    def logs(*where):
        q = (
            select(BreakdownLog)
            .where(*where)
            .options(
                selectinload(BreakdownLog.texts),
                selectinload(BreakdownLog.machine),
                selectinload(BreakdownLog.technician),
                selectinload(BreakdownLog.verifier),
            )
            .order_by(BreakdownLog.reported_at.desc())
            .limit(200)
        )
        if user.role == "supervisor" and user.zone:
            q = q.where(BreakdownLog.zone == user.zone)
        return [serialize.log(l, full=False) for l in db.scalars(q)]

    since = datetime.now(timezone.utc) - timedelta(days=30)
    sq = (
        select(AISession)
        .where(AISession.feedback == "not_helpful", AISession.created_at >= since)
        .options(selectinload(AISession.machine), selectinload(AISession.technician))
        .order_by(AISession.created_at.desc())
        .limit(100)
    )
    failed = (
        select(AISession)
        .where(AISession.outcome.in_(("failed", "refused", "escalated")), AISession.created_at >= since)
        .options(selectinload(AISession.machine), selectinload(AISession.technician))
        .order_by(AISession.created_at.desc())
        .limit(100)
    )
    return {
        "to_verify": logs(BreakdownLog.status == "closed"),
        "open": logs(BreakdownLog.status == "open"),
        "not_helpful": [serialize.session(s) for s in db.scalars(sq)],
        "escalated_sessions": [serialize.session(s) for s in db.scalars(failed)],
    }
