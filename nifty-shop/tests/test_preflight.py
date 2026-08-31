from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nifty_shop.preflight import (
    ClockSkewError,
    EgressIpMismatchError,
    EgressIpUnavailableError,
    assert_clock_within_skew,
    assert_egress_ip,
    resolve_egress_ip,
)


def test_resolves_a_well_formed_ip() -> None:
    assert str(resolve_egress_ip(lambda: "  203.0.113.7\n")) == "203.0.113.7"


def test_garbage_from_the_ip_service_fails_closed() -> None:
    """A proxy error page must never be mistaken for an address."""
    with pytest.raises(EgressIpUnavailableError):
        resolve_egress_ip(lambda: "<html>502 Bad Gateway</html>")


def test_a_lookup_failure_fails_closed() -> None:
    def boom() -> str:
        raise OSError("network unreachable")

    with pytest.raises(EgressIpUnavailableError):
        resolve_egress_ip(boom)


def test_matching_ip_is_permitted() -> None:
    assert_egress_ip(expected="203.0.113.7", observed=resolve_egress_ip(lambda: "203.0.113.7"))


def test_mismatched_ip_refuses_and_names_both() -> None:
    with pytest.raises(EgressIpMismatchError) as exc:
        assert_egress_ip(expected="203.0.113.7", observed=resolve_egress_ip(lambda: "198.51.100.2"))
    assert "203.0.113.7" in str(exc.value)
    assert "198.51.100.2" in str(exc.value)


def test_unset_expectation_refuses_rather_than_allowing_anything() -> None:
    """A missing EXPECTED_EGRESS_IP must not be read as 'any IP is fine'."""
    with pytest.raises(EgressIpMismatchError):
        assert_egress_ip(expected=None, observed=resolve_egress_ip(lambda: "203.0.113.7"))


def test_clock_within_tolerance_passes() -> None:
    now = datetime(2026, 8, 31, 9, 50, tzinfo=UTC)
    assert_clock_within_skew(local=now, reference=now + timedelta(seconds=3), max_seconds=5)


def test_clock_skew_beyond_tolerance_refuses_in_either_direction() -> None:
    now = datetime(2026, 8, 31, 9, 50, tzinfo=UTC)
    with pytest.raises(ClockSkewError):
        assert_clock_within_skew(local=now, reference=now + timedelta(seconds=9), max_seconds=5)
    with pytest.raises(ClockSkewError):
        assert_clock_within_skew(local=now, reference=now - timedelta(seconds=9), max_seconds=5)


def test_naive_datetimes_are_rejected() -> None:
    """The spec requires timezone-aware datetimes; a naive one is a bug, not a default."""
    naive = datetime(2026, 8, 31, 9, 50)  # noqa: DTZ001
    with pytest.raises(ValueError, match="timezone-aware"):
        assert_clock_within_skew(local=naive, reference=datetime.now(UTC), max_seconds=5)
