"""Structurally forbid network access during unit tests.

The spec requires zero network in unit tests. Relying on discipline means one careless
import of the real transport turns the suite into an integration test that fails in CI
for reasons unrelated to the code. This makes the attempt fail loudly instead.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any

import pytest

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class NetworkAccessInUnitTestError(RuntimeError):
    """A unit test attempted an outbound connection."""


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    real_connect = socket.socket.connect

    def guarded(self: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) and address else None
        if self.family in (socket.AF_INET, socket.AF_INET6) and host not in _LOOPBACK:
            raise NetworkAccessInUnitTestError(
                f"unit tests must not reach the network; attempted connection to {address!r}"
            )
        real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    yield
