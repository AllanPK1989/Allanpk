"""Microsoft Entra ID sign-in for the Copilot agent's connector (SPEC 13.3).

The custom connector signs each technician in with their own Microsoft account and sends their
access token for the Thunai API app. Thunai checks the token itself on every call and maps it to a
Thunai user. There is no shared key: every log must name the person who did the work.
"""
import logging
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import audit
from .config import Config, get_config
from .db import get_db
from .models import User

log = logging.getLogger("thunai.entra")

LEEWAY_S = 60
NOT_LINKED = "Your Microsoft account is not linked to a Thunai user. Ask your Thunai admin to add it."
CHALLENGE = {"WWW-Authenticate": "Bearer"}


class TokenError(ValueError):
    pass


def jwks_url(cfg: Config) -> str:
    return cfg.entra_jwks_url or f"https://login.microsoftonline.com/{cfg.entra_tenant_id}/discovery/v2.0/keys"


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    # Keys are cached for an hour; a token signed with an unknown key id triggers one refetch.
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=10)


def signing_key(token: str):
    return _jwks_client(jwks_url(get_config())).get_signing_key_from_jwt(token).key


def decode(token: str) -> dict:
    """The token's claims, or TokenError. Checks signature, issuer, tenant, audience, scope and expiry."""
    cfg = get_config()
    tenant = cfg.entra_tenant_id.strip().lower()
    try:
        claims = jwt.decode(
            token,
            signing_key(token),
            algorithms=["RS256"],
            audience=cfg.entra_audiences,
            leeway=LEEWAY_S,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWKClientError as e:
        raise TokenError(f"signing key: {e}") from e
    except jwt.PyJWTError as e:
        raise TokenError(f"{type(e).__name__}: {e}") from e
    # v2 tokens (accessTokenAcceptedVersion 2) and v1 tokens have different issuers; accept both.
    issuers = {f"https://login.microsoftonline.com/{tenant}/v2.0", f"https://sts.windows.net/{tenant}/"}
    if str(claims.get("iss", "")).lower() not in issuers:
        raise TokenError("issuer is not the configured tenant")
    if str(claims.get("tid", "")).lower() != tenant:
        raise TokenError("tenant id does not match")
    # Delegated (user) tokens carry scp; application-only tokens carry roles and have no person.
    if cfg.entra_scope not in str(claims.get("scp") or "").split():
        raise TokenError(f"scope {cfg.entra_scope} missing (application-only tokens are not accepted)")
    if not claims.get("oid"):
        raise TokenError("no object id")
    return claims


def account_name(claims: dict) -> str:
    return str(claims.get("preferred_username") or claims.get("upn") or claims.get("unique_name") or "").strip().lower()


def resolve_user(db: Session, claims: dict) -> User:
    """Match on the bound object ID; on first use, match the admin-entered UPN and bind the object ID."""
    oid = str(claims["oid"])
    user = db.scalar(select(User).where(User.entra_oid == oid))
    if user is None:
        upn = account_name(claims)
        user = db.scalar(select(User).where(func.lower(User.entra_upn) == upn)) if upn else None
        if user is None or user.entra_oid:  # unknown, or that UPN is bound to another Microsoft account
            raise HTTPException(status.HTTP_403_FORBIDDEN, NOT_LINKED)
        user.entra_oid = oid
        audit.record(db, user, "user", user.employee_id, "microsoft_account_linked", None, {"entra_upn": user.entra_upn})
        db.commit()
    if not user.active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your Thunai user is not active. Ask your Thunai admin.")
    return user


def copilot_user(request: Request, db: Session = Depends(get_db)) -> User:
    if not get_config().copilot_ready:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The Copilot connection is not set up on this Thunai server.")
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in with your Microsoft account.", headers=CHALLENGE)
    try:
        claims = decode(header[7:].strip())
    except TokenError as e:
        log.info("Copilot token refused: %s", e)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Microsoft sign-in not accepted. Sign in again.", headers=CHALLENGE)
    user = resolve_user(db, claims)
    request.state.copilot_user_id = user.id  # for the call log (main.py)
    return user


def copilot_roles(*roles: str):
    def check(user: User = Depends(copilot_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only supervisors and admins can do this.")
        return user

    return check
