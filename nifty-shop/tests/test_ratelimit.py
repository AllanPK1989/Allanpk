from __future__ import annotations

import pytest

from nifty_shop.ratelimit import TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_starts_full_at_capacity() -> None:
    bucket = TokenBucket(rate_per_second=2.0, capacity=2, clock=FakeClock())
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_refills_at_the_configured_rate() -> None:
    clock = FakeClock()
    bucket = TokenBucket(rate_per_second=2.0, capacity=2, clock=clock)
    bucket.try_acquire()
    bucket.try_acquire()
    assert bucket.try_acquire() is False

    clock.advance(0.5)  # one token at 2/sec
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_never_refills_beyond_capacity() -> None:
    """An idle hour must not buy a burst of thousands of orders."""
    clock = FakeClock()
    bucket = TokenBucket(rate_per_second=2.0, capacity=2, clock=clock)
    clock.advance(3600)
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_rejects_a_nonsensical_configuration() -> None:
    clock = FakeClock()
    with pytest.raises(ValueError, match="positive"):
        TokenBucket(rate_per_second=0.0, capacity=2, clock=clock)
    with pytest.raises(ValueError, match="positive"):
        TokenBucket(rate_per_second=2.0, capacity=0, clock=clock)


def test_a_clock_that_goes_backwards_does_not_mint_tokens() -> None:
    """Monotonic clocks should not jump back, but a bug here would grant free orders."""
    clock = FakeClock()
    bucket = TokenBucket(rate_per_second=2.0, capacity=2, clock=clock)
    bucket.try_acquire()
    bucket.try_acquire()
    clock.now -= 100.0
    assert bucket.try_acquire() is False
