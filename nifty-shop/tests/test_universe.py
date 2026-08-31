from __future__ import annotations

from datetime import date

import pytest

from nifty_shop.universe import (
    ConstituentChange,
    PointInTimeUniverse,
    UniverseNotCoveredError,
)

CHANGES = [
    ConstituentChange(date(2020, 1, 1), "AAA", "ADD", "NSE press release 2019-12-20"),
    ConstituentChange(date(2020, 1, 1), "BBB", "ADD", "NSE press release 2019-12-20"),
    ConstituentChange(date(2021, 4, 1), "BBB", "DROP", "NSE press release 2021-03-05"),
    ConstituentChange(date(2021, 4, 1), "CCC", "ADD", "NSE press release 2021-03-05"),
]


def universe() -> PointInTimeUniverse:
    return PointInTimeUniverse.from_changes(CHANGES)


def test_membership_as_of_the_first_effective_date() -> None:
    assert universe().constituents_on(date(2020, 6, 1)) == frozenset({"AAA", "BBB"})


def test_a_drop_takes_effect_on_its_date() -> None:
    assert universe().constituents_on(date(2021, 4, 1)) == frozenset({"AAA", "CCC"})


def test_the_day_before_a_change_still_shows_the_old_membership() -> None:
    assert universe().constituents_on(date(2021, 3, 31)) == frozenset({"AAA", "BBB"})


def test_a_date_before_any_recorded_change_refuses() -> None:
    """Returning today's Nifty 50 for a historical date is Forbidden rule 6. The only
    safe answer for an uncovered date is a refusal."""
    with pytest.raises(UniverseNotCoveredError):
        universe().constituents_on(date(2008, 1, 1))


def test_a_change_without_a_source_is_rejected() -> None:
    """Every add and drop must cite its NSE press release."""
    with pytest.raises(ValueError, match="source"):
        PointInTimeUniverse.from_changes(
            [ConstituentChange(date(2020, 1, 1), "AAA", "ADD", "  ")]
        )


def test_dropping_a_symbol_that_was_never_added_is_rejected() -> None:
    """A silent no-op here means the reconstructed index is wrong and nobody knows."""
    with pytest.raises(ValueError, match="ZZZ"):
        PointInTimeUniverse.from_changes(
            [ConstituentChange(date(2020, 1, 1), "ZZZ", "DROP", "src")]
        )


def test_adding_a_symbol_already_present_is_rejected() -> None:
    with pytest.raises(ValueError, match="AAA"):
        PointInTimeUniverse.from_changes(
            [
                ConstituentChange(date(2020, 1, 1), "AAA", "ADD", "src"),
                ConstituentChange(date(2020, 2, 1), "AAA", "ADD", "src"),
            ]
        )


def test_size_check_reports_dates_where_membership_is_not_fifty() -> None:
    """The index has exactly 50 names; any date that does not is a broken table."""
    offenders = universe().dates_with_unexpected_size(expected=50)
    assert set(offenders) == {date(2020, 1, 1), date(2021, 4, 1)}
