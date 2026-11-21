"""Shared data shapes for market data providers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Protocol

import pandas as pd


@dataclass
class SearchResult:
    symbol: str
    name: str
    asset_class: str
    region: str = "GLOBAL"
    exchange: str = ""
    currency: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Quote:
    symbol: str
    price: float | None
    prev_close: float | None = None
    currency: str = ""
    day_high: float | None = None
    day_low: float | None = None
    volume: float | None = None
    year_high: float | None = None
    year_low: float | None = None
    market_cap: float | None = None
    as_of: datetime | None = None

    @property
    def change(self) -> float | None:
        if self.price is None or not self.prev_close:
            return None
        return self.price - self.prev_close

    @property
    def change_pct(self) -> float | None:
        if self.price is None or not self.prev_close:
            return None
        return (self.price / self.prev_close - 1.0) * 100.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["change"] = self.change
        d["change_pct"] = self.change_pct
        d["as_of"] = self.as_of.isoformat() if self.as_of else None
        return d


@dataclass
class RawNews:
    title: str
    url: str
    source: str
    published_at: datetime
    snippet: str = ""


class Provider(Protocol):
    """What every market data source implements. History frames have a DatetimeIndex
    and lower-case columns: open, high, low, close, volume."""

    def search(self, query: str) -> list[SearchResult]: ...

    def quote(self, symbol: str) -> Quote: ...

    def quotes(self, symbols: list[str]) -> dict[str, Quote]: ...

    def history(self, symbol: str, period: str = "1y") -> pd.DataFrame: ...

    def fundamentals(self, symbol: str) -> dict[str, Any]: ...

    def news(self, symbol: str) -> list[RawNews]: ...


PERIOD_DAYS = {"1mo": 31, "3mo": 92, "6mo": 183, "1y": 366, "2y": 731, "5y": 1827, "10y": 3653, "max": 36500}


def empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"], index=pd.DatetimeIndex([], name="date"))
