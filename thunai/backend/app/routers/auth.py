from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit, serialize
from ..db import get_db
from ..models import User, utcnow
from ..schemas import LoginIn, MeUpdate
from ..security import LOCK_MINUTES, MAX_FAILED, create_token, current_user, verify_pin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.upper(User.employee_id) == body.employee_id.strip().upper()))
    wrong = HTTPException(401, "Wrong employee ID or PIN")
    if user is None or not user.active:
        raise wrong
    now = utcnow()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(423, {"message": "Too many wrong PINs. Ask your supervisor or try later.",
                                  "locked_until": user.locked_until.isoformat()})
    if not verify_pin(body.pin, user.pin_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_FAILED:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            user.failed_attempts = 0
            audit.record(db, None, "user", user.employee_id, "locked", None, {"minutes": LOCK_MINUTES})
        db.commit()
        raise wrong
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    return {"token": create_token(user, body.shared_device), "user": serialize.user(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return serialize.user(user)


@router.patch("/me")
def update_me(body: MeUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    before = {"preferred_language": user.preferred_language}
    user.preferred_language = body.preferred_language
    audit.record(db, user, "user", user.employee_id, "update", before, {"preferred_language": body.preferred_language})
    db.commit()
    return serialize.user(user)
