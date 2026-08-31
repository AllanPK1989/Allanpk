"""Startup preflight: static egress IP and clock drift.

Regulatory constraint in force since 1 April 2026: orders may only originate from the
static IP whitelisted with the broker. This module refuses to start on any mismatch,
and treats an unreadable IP as a mismatch rather than as permission to continue.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from ipaddress import IPv4Address


class PreflightError(Exception):
    """Base class for preflight refusals."""


class EgressIpUnavailableError(PreflightError):
    """The public egress IP could not be established."""


class EgressIpMismatchError(PreflightError):
    """The observed egress IP is not the whitelisted one."""


class ClockSkewError(PreflightError):
    """Local clock differs from the reference beyond tolerance."""


def resolve_egress_ip(fetch: Callable[[], str]) -> IPv4Address:
    """Resolve the public egress IP using the supplied fetcher.

    The fetcher is injected so unit tests touch no network. Anything that is not a
    well-formed IPv4 address, including a proxy error page, fails closed.
    """
    try:
        raw = fetch()
    except OSError as exc:
        raise EgressIpUnavailableError(f"could not determine egress IP: {exc}") from exc

    try:
        return IPv4Address(raw.strip())
    except ValueError as exc:
        raise EgressIpUnavailableError(
            f"egress IP lookup returned something that is not an IPv4 address: {raw.strip()[:80]!r}"
        ) from exc


def assert_egress_ip(expected: str | None, observed: IPv4Address) -> None:
    """Refuse to continue unless the observed IP is the whitelisted one.

    An unset expectation is a refusal, never a wildcard.
    """
    if expected is None:
        raise EgressIpMismatchError(
            f"EXPECTED_EGRESS_IP is not configured; refusing to run from {observed}"
        )
    if IPv4Address(expected.strip()) != observed:
        raise EgressIpMismatchError(
            f"egress IP mismatch: whitelisted {expected.strip()}, observed {observed}"
        )


def assert_clock_within_skew(
    local: datetime, reference: datetime, max_seconds: int
) -> None:
    """Refuse to continue if the local clock has drifted beyond tolerance."""
    for label, value in (("local", local), ("reference", reference)):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{label} datetime must be timezone-aware")

    drift = abs((local - reference).total_seconds())
    if drift > max_seconds:
        raise ClockSkewError(
            f"clock drift {drift:.1f}s exceeds the {max_seconds}s tolerance"
        )
