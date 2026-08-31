"""Token bucket rate limiter.

The strategy places at most two orders a day, so this is trivially satisfied. It exists
so the system stays inside the retail API category by construction rather than by
coincidence, and so a bug in a loop cannot turn into a burst of requests.
"""

from __future__ import annotations

import time
from collections.abc import Callable


class TokenBucket:
    """Classic token bucket over an injected monotonic clock."""

    def __init__(
        self,
        rate_per_second: float,
        capacity: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._rate = rate_per_second
        self._capacity = float(capacity)
        self._clock = clock
        self._tokens = float(capacity)
        self._last_tick = clock()

    def try_acquire(self) -> bool:
        """Take one token if available. Returns False rather than blocking."""
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_tick
        # A clock that appears to move backwards must not mint tokens.
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_tick = now
