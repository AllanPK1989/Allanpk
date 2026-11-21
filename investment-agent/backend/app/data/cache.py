"""A small in-process TTL cache so repeated page loads don't hammer free data sources."""

from __future__ import annotations

import copy
import functools
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_store: dict[tuple, tuple[float, Any]] = {}
_lock = threading.Lock()
_MAX_ITEMS = 2000


def clear() -> None:
    with _lock:
        _store.clear()


def ttl_cache(seconds: float) -> Callable[[F], F]:
    def deco(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__module__, fn.__qualname__, args[1:] if args and hasattr(args[0], "__dict__") else args,
                   tuple(sorted(kwargs.items())))
            now = time.monotonic()
            with _lock:
                hit = _store.get(key)
                if hit and hit[0] > now:
                    return copy.copy(hit[1])
            value = fn(*args, **kwargs)
            with _lock:
                if len(_store) >= _MAX_ITEMS:
                    for k in [k for k, (exp, _) in _store.items() if exp <= now] or list(_store)[: _MAX_ITEMS // 4]:
                        _store.pop(k, None)
                _store[key] = (now + seconds, value)
            return copy.copy(value)

        return wrapper  # type: ignore[return-value]

    return deco
