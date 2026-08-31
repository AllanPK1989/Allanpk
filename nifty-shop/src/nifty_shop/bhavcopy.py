"""NSE bhavcopy parsing.

Two layouts exist across the archive: the legacy `cm<DDMMMYYYY>bhav.csv` inside a zip,
and the current `sec_bhavdata_full_<DDMMYYYY>.csv`. The parser is driven by column
names, never by position, and refuses an unrecognised header instead of guessing.

The header names below are taken from the published file layouts but have NOT yet been
confirmed against a real download, because this build environment cannot reach NSE. The
strict detection is what makes that safe: a layout that does not match raises and names
the headers it actually saw, so the failure is loud and one fixture fixes it. Silently
mis-parsing a changed layout is the outcome this design exists to prevent.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO

#: Only the EQ series is tradeable for this strategy; the risk gate rejects the rest.
EQ_SERIES = "EQ"


class UnknownBhavcopyLayoutError(Exception):
    """The file header matches no known bhavcopy layout."""


@dataclass(frozen=True, slots=True)
class BhavRow:
    symbol: str
    series: str
    on: date
    close: float
    prev_close: float
    isin: str


@dataclass(frozen=True, slots=True)
class _Layout:
    name: str
    symbol: str
    series: str
    on: str
    close: str
    prev_close: str
    date_formats: tuple[str, ...]
    isin: str | None = None


_LEGACY = _Layout(
    name="legacy cm<date>bhav.csv",
    symbol="SYMBOL",
    series="SERIES",
    on="TIMESTAMP",
    close="CLOSE",
    prev_close="PREVCLOSE",
    isin="ISIN",
    date_formats=("%d-%b-%Y",),
)

_CURRENT = _Layout(
    name="sec_bhavdata_full",
    symbol="SYMBOL",
    series="SERIES",
    on="DATE1",
    close="CLOSE_PRICE",
    prev_close="PREV_CLOSE",
    isin=None,
    date_formats=("%d-%b-%Y",),
)

_LAYOUTS = (_LEGACY, _CURRENT)


def _normalise(name: str) -> str:
    return name.strip().upper()


def _detect_layout(header: list[str]) -> _Layout:
    present = {_normalise(name) for name in header}
    for layout in _LAYOUTS:
        required = {layout.symbol, layout.series, layout.on, layout.close, layout.prev_close}
        if required <= present:
            return layout
    raise UnknownBhavcopyLayoutError(
        "no known bhavcopy layout matches this header; saw: " + ", ".join(sorted(present))
    )


def parse_bhavcopy(text: str) -> list[BhavRow]:
    """Parse a bhavcopy CSV, keeping only the EQ series."""
    reader = csv.reader(StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise UnknownBhavcopyLayoutError("file is empty; no bhavcopy header found") from exc

    layout = _detect_layout(header)
    index = {_normalise(name): position for position, name in enumerate(header)}

    def field(row: list[str], column: str) -> str:
        return row[index[column]].strip()

    rows: list[BhavRow] = []
    for raw in reader:
        if not raw or len(raw) < len(header):
            continue

        symbol = field(raw, layout.symbol)
        series = field(raw, layout.series)
        if series != EQ_SERIES:
            continue

        try:
            close = float(field(raw, layout.close))
            prev_close = float(field(raw, layout.prev_close))
        except ValueError as exc:
            raise ValueError(f"{symbol}: unparseable price in bhavcopy row") from exc

        rows.append(
            BhavRow(
                symbol=symbol,
                series=series,
                on=_parse_date(field(raw, layout.on), layout, symbol),
                close=close,
                prev_close=prev_close,
                isin=field(raw, layout.isin) if layout.isin else "",
            )
        )

    return rows


def _parse_date(value: str, layout: _Layout, symbol: str) -> date:
    for fmt in layout.date_formats:
        try:
            return datetime.strptime(value, fmt).date()  # noqa: DTZ007
        except ValueError:
            continue
    raise ValueError(f"{symbol}: unparseable date {value!r} for layout {layout.name}")
