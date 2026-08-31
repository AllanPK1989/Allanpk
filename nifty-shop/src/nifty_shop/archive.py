"""NSE bhavcopy archive downloader.

Runs on the VPS; this build environment's egress policy denies nseindia.com, so the
fetcher is injected and every unit test uses a fake.

Three properties matter more than speed:

* **Idempotent.** A cached date is never refetched, so a range can be re-run freely.
* **Atomic.** Bytes land in a temp file and are renamed only once complete, so an
  interrupted run never leaves a truncated entry that a later run would trust.
* **Absence and failure are different.** A weekday with no bhavcopy was a holiday, and
  the trading calendar is derived from exactly that. A network failure is an error and
  must never be recorded as "no session", or the calendar and price history quietly
  grow holes.

The cutover date between the legacy zip layout and the current CSV layout is not
verified, so a 404 on the expected layout falls back to the other before concluding
there was no session. The report records which layout served each date, so one full run
reveals the real boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

ARCHIVE_HOST = "https://nsearchives.nseindia.com"

#: Documented, changeable, and not yet verified against a real download.
LAYOUT_CUTOVER = date(2016, 1, 1)


class Layout(Enum):
    LEGACY = "legacy"
    CURRENT = "current"


class ArchiveFetchError(Exception):
    """The bytes could not be retrieved. Never treated as an absent session."""


class NotFound(Exception):  # noqa: N818
    """The archive has no file at this URL, i.e. there was no session that day."""


Fetcher = Callable[[str], bytes]


def legacy_url(on: date) -> str:
    month = on.strftime("%b").upper()
    stamp = f"{on.day:02d}{month}{on.year}"
    return f"{ARCHIVE_HOST}/content/historical/EQUITIES/{on.year}/{month}/cm{stamp}bhav.csv.zip"


def current_url(on: date) -> str:
    return f"{ARCHIVE_HOST}/products/content/sec_bhavdata_full_{on:%d%m%Y}.csv"


@dataclass(frozen=True, slots=True)
class FetchResult:
    on: date
    layout: Layout | None
    path: Path | None
    absent: bool
    from_cache: bool = False


@dataclass
class DownloadReport:
    downloaded: int = 0
    cached: int = 0
    absent: list[date] = field(default_factory=list)
    sessions: list[date] = field(default_factory=list)
    layouts: dict[date, Layout] = field(default_factory=dict)


class BhavcopyArchive:
    def __init__(self, cache_dir: Path, fetch: Fetcher) -> None:
        self._cache_dir = cache_dir
        self._fetch = fetch

    def raw_path(self, on: date, layout: Layout) -> Path:
        suffix = "zip" if layout is Layout.LEGACY else "csv"
        return self._cache_dir / f"{on:%Y}" / f"bhav-{on:%Y-%m-%d}.{suffix}"

    def _layout_order(self, on: date) -> tuple[Layout, Layout]:
        if on < LAYOUT_CUTOVER:
            return (Layout.LEGACY, Layout.CURRENT)
        return (Layout.CURRENT, Layout.LEGACY)

    def _url(self, on: date, layout: Layout) -> str:
        return legacy_url(on) if layout is Layout.LEGACY else current_url(on)

    def ensure(self, on: date) -> FetchResult:
        """Download one session's bytes unless they are already cached."""
        for layout in self._layout_order(on):
            cached = self.raw_path(on, layout)
            if cached.is_file() and cached.stat().st_size > 0:
                return FetchResult(on, layout, cached, absent=False, from_cache=True)

        for layout in self._layout_order(on):
            try:
                payload = self._fetch(self._url(on, layout))
            except NotFound:
                continue
            destination = self.raw_path(on, layout)
            self._write_atomically(destination, payload)
            return FetchResult(on, layout, destination, absent=False)

        return FetchResult(on, layout=None, path=None, absent=True)

    def ensure_range(self, days: Iterable[date]) -> DownloadReport:
        """Walk a range, continuing past absent days. Failures still raise."""
        report = DownloadReport()
        for on in days:
            result = self.ensure(on)
            if result.absent:
                report.absent.append(on)
                continue
            report.sessions.append(on)
            if result.layout is not None:
                report.layouts[on] = result.layout
            if result.from_cache:
                report.cached += 1
            else:
                report.downloaded += 1
        return report

    @staticmethod
    def _write_atomically(destination: Path, payload: bytes) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            temporary.write_bytes(payload)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)


def sessions_from_report(reports: Sequence[DownloadReport]) -> list[date]:
    """Every date that produced a real file, which is the trading calendar."""
    return sorted({on for report in reports for on in report.sessions})
