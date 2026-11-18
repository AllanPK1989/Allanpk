"""PIN setup, login and logout."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import security
from ..config import get_config
from ..db import get_db
from ..schemas import PinChangeIn, PinIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        security.COOKIE, token, max_age=get_config().session_days * 86400, httponly=True,
        secure=request.url.scheme == "https", samesite="lax", path="/",
    )


def _require_header(request: Request) -> None:
    if request.headers.get("x-nudge") != "1":
        raise HTTPException(403, "Missing X-Nudge header")


@router.get("/status")
def status(request: Request, db: Session = Depends(get_db)):
    cfg = get_config()
    return {
        "has_pin": security.has_pin(db),
        "logged_in": security.session_valid(db, request.cookies.get(security.COOKIE)),
        "demo": cfg.demo_mode,
        "demo_pin": "1234" if cfg.seed_sample_data and cfg.demo_mode else None,
        "locked_for_s": security.lock_remaining_s(db),
    }


@router.post("/setup")
def setup(body: PinIn, request: Request, response: Response, db: Session = Depends(get_db)):
    _require_header(request)
    if security.has_pin(db):
        raise HTTPException(409, "A PIN is already set. Log in instead.")
    if not security.valid_pin_format(body.pin):
        raise HTTPException(422, "Use 4 to 8 digits")
    security.set_pin(db, body.pin)
    token = security.create_session(db, request.headers.get("user-agent", ""))
    db.commit()
    _set_cookie(response, request, token)
    return {"ok": True}


@router.post("/login")
def login(body: PinIn, request: Request, response: Response, db: Session = Depends(get_db)):
    _require_header(request)
    wait = security.lock_remaining_s(db)
    if wait:
        raise HTTPException(429, f"Too many tries. Try again in {max(1, wait // 60)} min.")
    ok = security.check_pin(db, body.pin)
    if not ok:
        db.commit()
        wait = security.lock_remaining_s(db)
        raise HTTPException(429 if wait else 401,
                            f"Too many tries. Try again in {max(1, wait // 60)} min." if wait else "Wrong PIN")
    token = security.create_session(db, request.headers.get("user-agent", ""))
    db.commit()
    _set_cookie(response, request, token)
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    security.end_session(db, request.cookies.get(security.COOKIE))
    db.commit()
    response.delete_cookie(security.COOKIE, path="/")
    return {"ok": True}


@router.post("/change-pin", dependencies=[Depends(security.require_auth)])
def change_pin(body: PinChangeIn, db: Session = Depends(get_db)):
    if not security.check_pin(db, body.current_pin):
        db.commit()
        raise HTTPException(401, "Current PIN is wrong")
    if not security.valid_pin_format(body.new_pin):
        raise HTTPException(422, "Use 4 to 8 digits")
    security.set_pin(db, body.new_pin)
    db.commit()
    return {"ok": True}
