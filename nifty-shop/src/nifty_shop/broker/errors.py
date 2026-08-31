"""Broker error hierarchy.

Every failure raises. Nothing returns None, an empty list, or a sentinel that a caller
could mistake for a valid empty result — that is the SDK behaviour this project exists
to avoid.
"""

from __future__ import annotations


class BrokerError(Exception):
    """Base class for every broker failure."""


class BrokerTransportError(BrokerError):
    """The request never produced a usable HTTP response."""


class BrokerResponseError(BrokerError):
    """The response was not the documented shape."""


class BrokerAuthError(BrokerError):
    """The broker rejected the credentials or the session."""


class NotLoggedInError(BrokerError):
    """A call requiring a session was made before logging in."""
