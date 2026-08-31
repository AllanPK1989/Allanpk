from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from nifty_shop.archive import (
    ArchiveFetchError,
    BhavcopyArchive,
    Layout,
    NotFound,
    current_url,
    legacy_url,
)


class FakeFetcher:
    """Returns canned bytes per URL. Anything unlisted 404s."""

    def __init__(self, available: dict[str, bytes] | None = None) -> None:
        self.available = available or {}
        self.requested: list[str] = []
        self.fail_with: Exception | None = None

    def __call__(self, url: str) -> bytes:
        self.requested.append(url)
        if self.fail_with is not None:
            raise self.fail_with
        if url not in self.available:
            raise NotFound(url)
        return self.available[url]


def test_legacy_url_shape() -> None:
    assert legacy_url(date(2008, 1, 1)) == (
        "https://nsearchives.nseindia.com/content/historical/EQUITIES/"
        "2008/JAN/cm01JAN2008bhav.csv.zip"
    )


def test_current_url_shape() -> None:
    assert current_url(date(2024, 1, 2)) == (
        "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_02012024.csv"
    )


def test_downloads_and_caches_the_raw_bytes(tmp_path: Path) -> None:
    url = current_url(date(2024, 1, 2))
    fetcher = FakeFetcher({url: b"SYMBOL,SERIES\n"})
    archive = BhavcopyArchive(tmp_path, fetcher)

    result = archive.ensure(date(2024, 1, 2))
    assert result.layout is Layout.CURRENT
    assert result.path is not None
    assert result.path.read_bytes() == b"SYMBOL,SERIES\n"


def test_a_second_call_does_not_refetch(tmp_path: Path) -> None:
    """Idempotent: re-running a range must not re-download what is already cached."""
    url = current_url(date(2024, 1, 2))
    fetcher = FakeFetcher({url: b"data"})
    archive = BhavcopyArchive(tmp_path, fetcher)

    archive.ensure(date(2024, 1, 2))
    archive.ensure(date(2024, 1, 2))
    assert fetcher.requested.count(url) == 1


def test_falls_back_to_the_other_layout_when_the_primary_is_absent(tmp_path: Path) -> None:
    """The exact cutover date between layouts is not verified, so a 404 on the
    expected layout tries the other before concluding there was no session."""
    on = date(2016, 6, 1)
    fetcher = FakeFetcher({legacy_url(on): b"legacy bytes"})
    archive = BhavcopyArchive(tmp_path, fetcher)

    result = archive.ensure(on)
    assert result.layout is Layout.LEGACY
    assert result.path is not None


def test_absent_on_both_layouts_is_recorded_as_no_session_not_an_error(
    tmp_path: Path,
) -> None:
    """A weekday with no bhavcopy was a holiday. The calendar is derived from this."""
    archive = BhavcopyArchive(tmp_path, FakeFetcher({}))
    result = archive.ensure(date(2024, 1, 26))
    assert result.absent is True
    assert result.path is None


def test_a_transport_failure_is_an_error_not_an_absence(tmp_path: Path) -> None:
    """Treating a network failure as 'no session' would silently punch holes in the
    calendar and the price history."""
    fetcher = FakeFetcher({})
    fetcher.fail_with = ArchiveFetchError("connection reset")
    archive = BhavcopyArchive(tmp_path, fetcher)
    with pytest.raises(ArchiveFetchError):
        archive.ensure(date(2024, 1, 2))


def test_a_failed_write_leaves_no_partial_file(tmp_path: Path) -> None:
    """Bytes land in a temp file and are renamed atomically, so an interrupted run
    never leaves a truncated cache entry that a later run would trust."""
    fetcher = FakeFetcher({})
    fetcher.fail_with = ArchiveFetchError("died mid-transfer")
    archive = BhavcopyArchive(tmp_path, fetcher)
    with pytest.raises(ArchiveFetchError):
        archive.ensure(date(2024, 1, 2))
    assert list(tmp_path.rglob("*.tmp")) == []
    assert list(tmp_path.rglob("*.csv")) == []


def test_range_download_continues_past_absent_days_and_reports(tmp_path: Path) -> None:
    days = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    fetcher = FakeFetcher({current_url(days[0]): b"a", current_url(days[2]): b"c"})
    archive = BhavcopyArchive(tmp_path, fetcher)

    report = archive.ensure_range(days)
    assert report.downloaded == 2
    assert report.absent == [days[1]]
    assert report.sessions == [days[0], days[2]]


def test_range_download_is_resumable(tmp_path: Path) -> None:
    days = [date(2024, 1, 1), date(2024, 1, 2)]
    available = {current_url(d): b"x" for d in days}
    first = FakeFetcher(available)
    BhavcopyArchive(tmp_path, first).ensure_range(days[:1])

    second = FakeFetcher(available)
    report = BhavcopyArchive(tmp_path, second).ensure_range(days)
    assert report.cached == 1
    assert report.downloaded == 1
