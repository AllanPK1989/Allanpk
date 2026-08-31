"""A thin, typed, read-only Firstock client.

Request shapes are taken from the firstock 1.1.11 SDK source; see
docs/firstock-api-notes.md for what is verified and what is not. The SDK itself is not
called, because it swallows exceptions into None, parses responses with
ast.literal_eval, and writes the session token to disk.

Phase 1 is read-only: login, logout, funds and holdings. No order path exists yet.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Final

from nifty_shop.broker.errors import (
    BrokerAuthError,
    BrokerResponseError,
    BrokerTransportError,
    NotLoggedInError,
)
from nifty_shop.broker.transport import (
    DEFAULT_TIMEOUT_SECONDS,
    RequestsTransport,
    Transport,
)

BASE_URL: Final = "https://api.firstock.in/V1"
LOGIN_URL: Final = f"{BASE_URL}/login"
LOGOUT_URL: Final = f"{BASE_URL}/logout"
LIMIT_URL: Final = f"{BASE_URL}/limit"
HOLDINGS_URL: Final = f"{BASE_URL}/holdings"

#: CNC / delivery, per the spec's entry rules.
PRODUCT_CNC: Final = "C"


def sha256_hex(plaintext: str) -> str:
    """The password hash the login endpoint expects."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


class FirstockClient:
    """Read-only Firstock access with an in-memory session token."""

    def __init__(
        self,
        user_id: str,
        vendor_code: str,
        api_key: str,
        transport: Transport | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._user_id = user_id
        self._vendor_code = vendor_code
        self._api_key = api_key
        self._transport: Transport = transport if transport is not None else RequestsTransport()
        self._timeout = timeout
        self._token: str | None = None

    def __repr__(self) -> str:
        """Never renders the session token."""
        state = "logged-in" if self._token else "logged-out"
        return f"FirstockClient(user_id={self._user_id!r}, state={state!r})"

    @property
    def is_logged_in(self) -> bool:
        return self._token is not None

    @property
    def user_id(self) -> str:
        return self._user_id

    def login(self, password: str, totp: str) -> None:
        data = self._post(
            LOGIN_URL,
            {
                "userId": self._user_id,
                "password": sha256_hex(password),
                "TOTP": totp,
                "vendorCode": self._vendor_code,
                "apiKey": self._api_key,
            },
            auth_failure=True,
        )
        if not isinstance(data, dict) or not isinstance(data.get("susertoken"), str):
            raise BrokerResponseError("login succeeded but the response carried no susertoken")
        self._token = data["susertoken"]

    def logout(self) -> None:
        token = self._require_token()
        self._post(LOGOUT_URL, {"userId": self._user_id, "jKey": token})
        self._token = None

    def funds(self) -> object:
        """Raw `data` payload from /limit. Field names are not yet verified."""
        token = self._require_token()
        return self._post(
            LIMIT_URL, {"userId": self._user_id, "actid": self._user_id, "jKey": token}
        )

    def holdings(self) -> object:
        """Raw `data` payload from /holdings. Field names are not yet verified."""
        token = self._require_token()
        return self._post(
            HOLDINGS_URL,
            {
                "userId": self._user_id,
                "actid": self._user_id,
                "product": PRODUCT_CNC,
                "jKey": token,
            },
        )

    def _require_token(self) -> str:
        if self._token is None:
            raise NotLoggedInError("no active session; call login() first")
        return self._token

    def _post(
        self, url: str, payload: Mapping[str, object], *, auth_failure: bool = False
    ) -> object:
        """POST, validate the envelope, and return the `data` payload.

        Any non-success outcome raises. Nothing here can return an empty result that a
        caller might read as "the account holds nothing".
        """
        response = self._transport.post(url, payload, self._timeout)

        if response.status_code != 200:
            raise BrokerTransportError(
                f"{url} returned HTTP {response.status_code}"
            )

        try:
            body = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise BrokerResponseError(f"{url} returned a body that is not JSON") from exc

        if not isinstance(body, dict):
            raise BrokerResponseError(f"{url} returned {type(body).__name__}, expected an object")

        status = body.get("status")
        if not isinstance(status, str) or status.strip().lower() != "success":
            message = body.get("message") or body.get("data") or "no message supplied"
            error = BrokerAuthError if auth_failure else BrokerResponseError
            raise error(f"{url} reported failure: {message}")

        return body.get("data")
