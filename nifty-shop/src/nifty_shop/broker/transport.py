"""HTTP transport seam.

The client depends on this Protocol, not on requests, so unit tests run with a fake and
touch no network.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    text: str


class Transport(Protocol):
    def post(
        self, url: str, payload: Mapping[str, object], timeout: float
    ) -> HttpResponse: ...


class RequestsTransport:
    """Real transport. Imported lazily so unit tests never need requests configured."""

    def post(
        self, url: str, payload: Mapping[str, object], timeout: float
    ) -> HttpResponse:
        import requests

        try:
            response = requests.post(url, json=dict(payload), timeout=timeout)
        except requests.RequestException as exc:
            from nifty_shop.broker.errors import BrokerTransportError

            raise BrokerTransportError(f"request to {url} failed: {exc}") from exc
        return HttpResponse(status_code=response.status_code, text=response.text)
