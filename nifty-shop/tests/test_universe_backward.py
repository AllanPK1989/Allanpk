from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from nifty_shop.universe import ConstituentChange, PointInTimeUniverse, UniverseNotCoveredError
from nifty_shop.universe_audit import audit_change_table, load_changes_csv

# A tiny index of 3 names, so the arithmetic is checkable by eye.
CURRENT = frozenset({"AAA", "CCC", "DDD"})
AS_OF = date(2026, 8, 31)
COMPLETE_FROM = date(2020, 1, 1)

CHANGES = [
    # On 2021-04-01, BBB left and CCC joined.
    ConstituentChange(date(2021, 4, 1), "BBB", "DROP", "NSE Indices PR 2021-03-05"),
    ConstituentChange(date(2021, 4, 1), "CCC", "ADD", "NSE Indices PR 2021-03-05"),
    # On 2023-09-29, DDD joined and EEE left.
    ConstituentChange(date(2023, 9, 29), "EEE", "DROP", "NSE Indices PR 2023-08-25"),
    ConstituentChange(date(2023, 9, 29), "DDD", "ADD", "NSE Indices PR 2023-08-25"),
]


def rewound() -> PointInTimeUniverse:
    return PointInTimeUniverse.from_current_and_changes(
        current=CURRENT, as_of=AS_OF, changes=CHANGES, complete_from=COMPLETE_FROM
    )


def test_today_is_the_current_list() -> None:
    assert rewound().constituents_on(AS_OF) == CURRENT


def test_rewinding_one_change_restores_the_dropped_name() -> None:
    """Just before 2023-09-29: DDD had not joined, EEE had not left."""
    assert rewound().constituents_on(date(2023, 9, 28)) == frozenset({"AAA", "CCC", "EEE"})


def test_rewinding_all_changes_reaches_the_earliest_membership() -> None:
    """Before 2021-04-01: CCC had not joined, BBB had not left."""
    assert rewound().constituents_on(date(2020, 6, 1)) == frozenset({"AAA", "BBB", "EEE"})


def test_membership_on_a_change_date_includes_that_change() -> None:
    assert rewound().constituents_on(date(2021, 4, 1)) == frozenset({"AAA", "CCC", "EEE"})


def test_a_date_before_the_declared_completeness_refuses() -> None:
    """The rewind can produce a membership for any date, but it is only trustworthy
    back to the date the assembler declares the change list complete from."""
    with pytest.raises(UniverseNotCoveredError, match="2020-01-01"):
        rewound().constituents_on(date(2019, 12, 31))


def test_rewinding_an_add_for_a_name_that_is_not_currently_present_is_an_error() -> None:
    """The change list disagrees with the current list; one of them is wrong."""
    with pytest.raises(ValueError, match="ZZZ"):
        PointInTimeUniverse.from_current_and_changes(
            current=CURRENT,
            as_of=AS_OF,
            changes=[ConstituentChange(date(2021, 4, 1), "ZZZ", "ADD", "src")],
            complete_from=COMPLETE_FROM,
        )


def test_rewinding_a_drop_for_a_name_already_present_is_an_error() -> None:
    with pytest.raises(ValueError, match="AAA"):
        PointInTimeUniverse.from_current_and_changes(
            current=CURRENT,
            as_of=AS_OF,
            changes=[ConstituentChange(date(2021, 4, 1), "AAA", "DROP", "src")],
            complete_from=COMPLETE_FROM,
        )


# --- the audit -------------------------------------------------------------------

def test_a_clean_table_of_the_right_size_audits_clean() -> None:
    findings = audit_change_table(
        current=CURRENT, as_of=AS_OF, changes=CHANGES,
        complete_from=COMPLETE_FROM, expected_size=3,
    )
    assert findings == []


def test_a_membership_that_is_never_the_index_size_is_reported() -> None:
    """The check that catches a missing change: the index is always exactly 50."""
    findings = audit_change_table(
        current=CURRENT, as_of=AS_OF, changes=CHANGES,
        complete_from=COMPLETE_FROM, expected_size=50,
    )
    assert findings
    assert all("expected 50" in f.detail for f in findings)


def test_an_unbalanced_reconstitution_is_reported() -> None:
    """One name leaves and none joins: membership drops below the index size."""
    unbalanced = [ConstituentChange(date(2021, 4, 1), "BBB", "DROP", "src")]
    findings = audit_change_table(
        current=frozenset({"AAA", "CCC", "DDD"}), as_of=AS_OF, changes=unbalanced,
        complete_from=COMPLETE_FROM, expected_size=3,
    )
    assert any("2021-04-01" in f.detail or f.on == date(2021, 4, 1) for f in findings)


def test_a_duplicate_row_is_reported() -> None:
    duplicated = [*CHANGES, CHANGES[0]]
    findings = audit_change_table(
        current=CURRENT, as_of=AS_OF, changes=duplicated,
        complete_from=COMPLETE_FROM, expected_size=3,
    )
    assert any("duplicate" in f.detail.lower() for f in findings)


def test_a_symbol_that_did_not_trade_on_its_effective_date_is_reported() -> None:
    """Objective typo detection: cross-check every change against the bhavcopy for
    that session. A symbol that has no bar that day is a typo or a rename."""
    def traded_on(_: date) -> set[str]:
        return {"AAA", "BBB", "CCC", "EEE"}  # DDD never trades

    findings = audit_change_table(
        current=CURRENT, as_of=AS_OF, changes=CHANGES,
        complete_from=COMPLETE_FROM, expected_size=3, symbols_trading_on=traded_on,
    )
    assert any("DDD" in f.detail for f in findings)


# --- the CSV the assembler actually fills in --------------------------------------

def test_csv_round_trips_into_changes(tmp_path: Path) -> None:
    path = tmp_path / "changes.csv"
    path.write_text(
        "effective_from,symbol,action,source\n"
        "2021-04-01,BBB,DROP,NSE Indices PR 2021-03-05\n"
        "2021-04-01,CCC,ADD,NSE Indices PR 2021-03-05\n"
    )
    loaded = load_changes_csv(path)
    assert len(loaded) == 2
    assert loaded[0].symbol == "BBB"
    assert loaded[0].action == "DROP"
    assert loaded[1].source.startswith("NSE Indices")


def test_csv_rejects_a_row_with_no_source(tmp_path: Path) -> None:
    path = tmp_path / "changes.csv"
    path.write_text("effective_from,symbol,action,source\n2021-04-01,BBB,DROP,\n")
    with pytest.raises(ValueError, match="source"):
        load_changes_csv(path)


def test_csv_rejects_an_unknown_action(tmp_path: Path) -> None:
    path = tmp_path / "changes.csv"
    path.write_text("effective_from,symbol,action,source\n2021-04-01,BBB,MOVED,pr\n")
    with pytest.raises(ValueError, match="MOVED"):
        load_changes_csv(path)


def test_csv_ignores_comment_lines(tmp_path: Path) -> None:
    path = tmp_path / "changes.csv"
    path.write_text(
        "effective_from,symbol,action,source\n"
        "# 2021 reconstitution, announced 2021-03-05\n"
        "2021-04-01,BBB,DROP,NSE Indices PR 2021-03-05\n"
    )
    assert len(load_changes_csv(path)) == 1


def test_a_change_dated_after_the_current_list_is_an_error() -> None:
    """The current list is stated as of a date; a later change cannot already be in it."""
    with pytest.raises(ValueError, match="after"):
        PointInTimeUniverse.from_current_and_changes(
            current=CURRENT,
            as_of=date(2026, 8, 31),
            changes=[ConstituentChange(date(2026, 12, 1), "AAA", "ADD", "src")],
            complete_from=COMPLETE_FROM,
        )


def test_current_csv_reports_a_malformed_as_of_clearly(tmp_path: Path) -> None:
    """A prose comment that happens to start with 'as_of,' must not produce a
    traceback; the refusal has to name the offending line."""
    from nifty_shop.universe_audit import load_current_csv

    path = tmp_path / "current.csv"
    path.write_text("# as_of, because a change dated after as_of is rejected.\nsymbol\nAAA\n")
    with pytest.raises(ValueError, match="Expected exactly"):
        load_current_csv(path)


def test_current_csv_reads_a_well_formed_as_of(tmp_path: Path) -> None:
    from nifty_shop.universe_audit import load_current_csv

    path = tmp_path / "current.csv"
    path.write_text("# as_of,2026-08-31\nsymbol\nAAA\nbbb\n")
    symbols, as_of = load_current_csv(path)
    assert as_of == date(2026, 8, 31)
    assert symbols == frozenset({"AAA", "BBB"})
