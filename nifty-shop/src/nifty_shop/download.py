"""Command line tools for the Phase 2 data work, to be run on the VPS.

Three jobs, each a subcommand:

* `bhavcopy`  — download the daily archive over a date range into a local cache.
* `closes`    — print a symbol's close series from that cache, for eyeballing.
* `fixture`   — build a reference fixture for the Phase 2 validation gate, taking the
                RSI and SMA you read off TradingView and pairing them with the exact
                close series this project computes from.

Nothing here has been run against the live NSE archive: this build environment's egress
policy denies nseindia.com. The request shapes come from the documented archive layout
and the parser refuses anything it does not recognise, naming the headers it saw.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from nifty_shop.archive import ArchiveFetchError, BhavcopyArchive, NotFound
from nifty_shop.bhavcopy import parse_bhavcopy
from nifty_shop.validation_gate import MIN_WARMUP_BARS

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def parse_date_range(start: str, end: str) -> tuple[date, date]:
    parsed: list[date] = []
    for text in (start, end):
        try:
            parsed.append(date.fromisoformat(text))
        except ValueError as exc:
            raise ValueError(f"{text} is not an ISO date (expected YYYY-MM-DD)") from exc
    return parsed[0], parsed[1]


def weekdays_between(start: date, end: date) -> list[date]:
    """Every Monday-to-Friday date in the range, inclusive.

    Weekends are never trading days, so they are not requested at all. Holidays still
    are, and come back absent, which is how the calendar gets derived.
    """
    if end < start:
        raise ValueError(f"end date {end} is before start date {start}")
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _requests_fetcher() -> Any:
    """A fetcher that looks like a browser, because NSE rejects anything that doesn't.

    NSE also sets cookies on first contact, so the homepage is visited once to prime
    the session before any archive file is requested.
    """
    import contextlib

    import requests

    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    # Priming is best effort; the archive host often serves without cookies.
    with contextlib.suppress(requests.RequestException):
        session.get("https://www.nseindia.com/", timeout=20)

    def fetch(url: str) -> bytes:
        try:
            response = session.get(url, timeout=60)
        except requests.RequestException as exc:
            raise ArchiveFetchError(f"{url}: {exc}") from exc
        if response.status_code == 404:
            raise NotFound(url)
        if response.status_code != 200:
            raise ArchiveFetchError(f"{url} returned HTTP {response.status_code}")
        return bytes(response.content)

    return fetch


def _read_day(cache: Path, on: date) -> list[Any]:
    """Parse one cached session, transparently handling the zipped legacy layout."""
    for suffix in ("csv", "zip"):
        path = cache / f"{on:%Y}" / f"bhav-{on:%Y-%m-%d}.{suffix}"
        if not path.is_file():
            continue
        if suffix == "zip":
            import zipfile

            with zipfile.ZipFile(path) as archive:
                name = archive.namelist()[0]
                text = archive.read(name).decode("utf-8", errors="replace")
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
        return list(parse_bhavcopy(text))
    return []


def closes_from_cache(cache: Path, symbol: str, upto: date) -> list[float]:
    """A symbol's close series from the cache, oldest first, ending at `upto`."""
    series: list[tuple[date, float]] = []
    for year_dir in sorted(cache.glob("*")):
        if not year_dir.is_dir():
            continue
        for path in sorted(year_dir.glob("bhav-*")):
            stamp = date.fromisoformat(path.stem.replace("bhav-", ""))
            if stamp > upto:
                continue
            for row in _read_day(cache, stamp):
                if row.symbol == symbol:
                    series.append((stamp, row.close))
    return [close for _, close in sorted(series)]


def build_fixture(
    cache: Path,
    symbol: str,
    as_of: date,
    expected_rsi: float,
    expected_sma: float,
    source: str,
) -> dict[str, Any]:
    """Assemble one reference fixture for the Phase 2 validation gate."""
    if not source.strip():
        raise ValueError("a fixture must state its source; an unsourced value is not a reference")

    closes = closes_from_cache(cache, symbol, upto=as_of)
    if len(closes) < MIN_WARMUP_BARS:
        raise ValueError(
            f"{symbol} has only {len(closes)} cached closes up to {as_of}; "
            f"the gate needs at least {MIN_WARMUP_BARS}. Download more history first."
        )

    return {
        "symbol": symbol,
        "as_of": as_of.isoformat(),
        "closes": closes,
        "expected_rsi_14": expected_rsi,
        "expected_sma_50": expected_sma,
        "source": source.strip(),
    }


def _cmd_bhavcopy(args: argparse.Namespace) -> int:
    start, end = parse_date_range(args.start, args.end)
    days = weekdays_between(start, end)
    archive = BhavcopyArchive(Path(args.cache), _requests_fetcher())

    print(f"requesting {len(days)} weekday sessions from {start} to {end}")
    report = archive.ensure_range(days)
    print(
        f"downloaded {report.downloaded}, already cached {report.cached}, "
        f"absent (holidays) {len(report.absent)}"
    )
    if report.layouts:
        kinds = {layout.value for layout in report.layouts.values()}
        print(f"layouts served: {', '.join(sorted(kinds))}")
    print(f"trading sessions found: {len(report.sessions)}")
    return 0


def _cmd_closes(args: argparse.Namespace) -> int:
    series = closes_from_cache(Path(args.cache), args.symbol, date.fromisoformat(args.as_of))
    print(f"{args.symbol}: {len(series)} closes up to {args.as_of}")
    if series:
        print(f"  first {series[0]}  last {series[-1]}")
    return 0 if series else 1


def _cmd_fixture(args: argparse.Namespace) -> int:
    payload = build_fixture(
        cache=Path(args.cache),
        symbol=args.symbol,
        as_of=date.fromisoformat(args.as_of),
        expected_rsi=args.rsi,
        expected_sma=args.sma,
        source=args.source,
    )
    out = Path(args.out) / f"{args.symbol.lower()}-{args.as_of}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out} with {len(payload['closes'])} closes")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nifty-shop-download")
    parser.add_argument("--cache", default="data/bhavcopy", help="local archive cache directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bhav = subparsers.add_parser("bhavcopy", help="download the daily archive over a range")
    bhav.add_argument("--start", required=True, help="YYYY-MM-DD")
    bhav.add_argument("--end", required=True, help="YYYY-MM-DD")
    bhav.set_defaults(func=_cmd_bhavcopy)

    closes = subparsers.add_parser("closes", help="print a symbol's cached close series")
    closes.add_argument("--symbol", required=True)
    closes.add_argument("--as-of", required=True, dest="as_of")
    closes.set_defaults(func=_cmd_closes)

    fixture = subparsers.add_parser("fixture", help="build a Phase 2 reference fixture")
    fixture.add_argument("--symbol", required=True)
    fixture.add_argument("--as-of", required=True, dest="as_of")
    fixture.add_argument(
        "--rsi", required=True, type=float, help="RSI(14) from the reference tool"
    )
    fixture.add_argument("--sma", required=True, type=float, help="SMA(50) from the reference tool")
    fixture.add_argument("--source", required=True, help='e.g. "TradingView NSE:RELIANCE 1D"')
    fixture.add_argument("--out", default="tests/fixtures/reference")
    fixture.set_defaults(func=_cmd_fixture)

    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
