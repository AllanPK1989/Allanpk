"""Auditing a hand-assembled Nifty 50 constituent change table.

Risk R-02: a wrong point-in-time universe is the single most dangerous artefact in this
project, because it is invisible — it produces a *better*-looking backtest. The table
has to be typed out by hand from NSE Indices press releases, and hand-typed data has
errors, so the defence is a set of objective checks rather than care.

The strongest check is arithmetic, not judgement: the Nifty 50 has exactly 50 members at
every instant of its life. Rewind today's published list through the recorded changes,
and any date where the count is not 50 means a change is missing, duplicated or
mistyped. No knowledge of which stocks "should" be in the index is needed.

The second-strongest is the bhavcopy cross-check: a symbol named in a change must
actually have traded on that session. That catches typos and stale symbol names
objectively, against data rather than memory.
"""

from __future__ import annotations

import csv
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from nifty_shop.universe import ConstituentChange, PointInTimeUniverse

VALID_ACTIONS = ("ADD", "DROP")
CSV_HEADER = ("effective_from", "symbol", "action", "source")


@dataclass(frozen=True, slots=True)
class AuditFinding:
    on: date | None
    detail: str

    def __str__(self) -> str:
        where = f"{self.on}: " if self.on else ""
        return f"{where}{self.detail}"


def load_changes_csv(path: Path) -> list[ConstituentChange]:
    """Load the hand-assembled change table. Blank lines and # comments are skipped."""
    changes: list[ConstituentChange] = []
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    for row in csv.DictReader(lines):
        source = (row.get("source") or "").strip()
        if not source:
            raise ValueError(
                f"{row.get('symbol')} on {row.get('effective_from')} states no source; "
                "every add and drop must cite its NSE Indices press release"
            )
        action = (row.get("action") or "").strip().upper()
        if action not in VALID_ACTIONS:
            raise ValueError(f"unknown action {action!r}; expected one of {VALID_ACTIONS}")
        changes.append(
            ConstituentChange(
                effective_from=date.fromisoformat((row["effective_from"] or "").strip()),
                symbol=(row["symbol"] or "").strip().upper(),
                action="ADD" if action == "ADD" else "DROP",
                source=source,
            )
        )
    return changes


def audit_change_table(
    current: frozenset[str] | set[str],
    as_of: date,
    changes: Sequence[ConstituentChange],
    complete_from: date,
    expected_size: int = 50,
    symbols_trading_on: Callable[[date], set[str]] | None = None,
) -> list[AuditFinding]:
    """Every objective problem the table can be checked for. Empty list means clean."""
    findings: list[AuditFinding] = []
    findings.extend(_duplicate_rows(changes))

    try:
        universe = PointInTimeUniverse.from_current_and_changes(
            current=current, as_of=as_of, changes=changes, complete_from=complete_from
        )
    except ValueError as exc:
        findings.append(AuditFinding(on=None, detail=str(exc)))
        return findings

    periods = _effective_dates(changes, complete_from)
    for index, on in enumerate(periods):
        members = universe.constituents_on(on)
        if len(members) == expected_size:
            continue
        # Name the end of the affected period too: that boundary is where a missing
        # or mistyped row almost always belongs.
        until = periods[index + 1] if index + 1 < len(periods) else as_of
        findings.append(
            AuditFinding(
                on=on,
                detail=(
                    f"membership is {len(members)} from {on} until {until}, "
                    f"expected {expected_size}; a change at one of those two dates is "
                    "missing, duplicated or mistyped"
                ),
            )
        )

    if len(set(current)) != expected_size:
        findings.append(
            AuditFinding(
                on=as_of,
                detail=(
                    f"the current list has {len(set(current))} names, "
                    f"expected {expected_size}"
                ),
            )
        )

    if symbols_trading_on is not None:
        findings.extend(_untraded_symbols(changes, symbols_trading_on))

    return findings


def _effective_dates(changes: Iterable[ConstituentChange], complete_from: date) -> list[date]:
    dates = {change.effective_from for change in changes}
    dates.add(complete_from)
    return sorted(dates)


def _duplicate_rows(changes: Sequence[ConstituentChange]) -> list[AuditFinding]:
    seen: set[tuple[date, str, str]] = set()
    findings: list[AuditFinding] = []
    for change in changes:
        key = (change.effective_from, change.symbol, change.action)
        if key in seen:
            findings.append(
                AuditFinding(
                    on=change.effective_from,
                    detail=f"duplicate row: {change.symbol} {change.action}",
                )
            )
        seen.add(key)
    return findings


def _untraded_symbols(
    changes: Sequence[ConstituentChange],
    symbols_trading_on: Callable[[date], set[str]],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for change in changes:
        traded = symbols_trading_on(change.effective_from)
        if change.symbol not in traded:
            findings.append(
                AuditFinding(
                    on=change.effective_from,
                    detail=(
                        f"{change.symbol} has no bhavcopy bar on its effective date; "
                        "likely a typo or a since-renamed symbol"
                    ),
                )
            )
    return findings


def load_current_csv(path: Path) -> tuple[frozenset[str], date | None]:
    """Load today's membership and the `as_of` date declared in a comment line."""
    as_of: date | None = None
    symbols: list[str] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            if body.lower().startswith("as_of,"):
                candidate = body.split(",", 1)[1].strip()
                try:
                    as_of = date.fromisoformat(candidate)
                except ValueError as exc:
                    raise ValueError(
                        f"the as_of line in {path.name} is not an ISO date: {line.strip()!r}. "
                        "Expected exactly '# as_of,YYYY-MM-DD'."
                    ) from exc
            continue
        if line.lower() == "symbol":
            continue
        symbols.append(line.upper())

    return frozenset(symbols), as_of


def main(changes_path: Path, current_path: Path, complete_from: date) -> int:
    """Audit the assembled table. Returns 0 when clean, 1 when anything is wrong."""
    changes = load_changes_csv(changes_path)
    current, as_of = load_current_csv(current_path)

    if as_of is None:
        print(f"REFUSED: {current_path} declares no 'as_of' date")
        return 1
    if not current:
        print(f"REFUSED: {current_path} lists no symbols")
        return 1
    if not changes:
        print(f"REFUSED: {changes_path} contains no changes")
        return 1

    findings = audit_change_table(
        current=current,
        as_of=as_of,
        changes=changes,
        complete_from=complete_from,
        expected_size=50,
    )
    if findings:
        print(f"{len(findings)} problems in the constituent table:")
        for finding in findings:
            print(f"  {finding}")
        return 1

    print(
        f"constituent table is consistent: {len(changes)} changes, "
        f"membership of 50 held from {complete_from} to {as_of}"
    )
    return 0


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parents[2]
    sys.exit(
        main(
            changes_path=root / "reference" / "nifty50-constituent-changes.csv",
            current_path=root / "reference" / "nifty50-current.csv",
            complete_from=date(2007, 1, 1),
        )
    )
