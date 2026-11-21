from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..config import Settings, get_settings
from ..security import (
    COOKIE_NAME,
    auth_required,
    check_owner_password,
    client_ip,
    global_login_throttle,
    login_throttle,
    make_session_token,
    read_session_token,
)

router = APIRouter(tags=["auth"])


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, settings: Settings = Depends(get_settings)):
    ip = client_ip(request)
    if login_throttle.blocked(ip) or global_login_throttle.blocked("*"):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")
    if not check_owner_password(body.password, settings):
        login_throttle.fail(ip)
        global_login_throttle.fail("*")
        raise HTTPException(status_code=401, detail="Wrong password")
    login_throttle.reset(ip)
    response.set_cookie(COOKIE_NAME, make_session_token(settings), max_age=settings.session_days * 86400,
                        httponly=True, secure=settings.cookie_secure, samesite="strict", path="/")
    return {"ok": True}


@router.post("/auth/logout")
def logout(response: Response, settings: Settings = Depends(get_settings)):
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.cookie_secure, httponly=True, samesite="strict")
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request, settings: Settings = Depends(get_settings)):
    if not auth_required(settings):
        return {"authenticated": True, "auth_required": False}
    token = request.cookies.get(COOKIE_NAME, "")
    return {"authenticated": bool(token and read_session_token(token, settings)), "auth_required": True}
