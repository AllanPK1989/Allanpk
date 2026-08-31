"""Point-in-time Nifty 50 membership.

Forbidden rule 6: do not use today's constituent list for historical periods. Doing so
is survivorship bias, and it is invisible because it produces a better-looking backtest.

This is the highest-risk artefact in the project (risk R-02), so the rules are strict:
every change must cite its NSE press release, a drop of a symbol that was never added
is an error rather than a no-op, and a date the change history does not cover refuses
instead of falling back to anything.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

Action = Literal["ADD", "DROP"]


class UniverseNotCoveredError(Exception):
    """The requested date precedes the recorded constituent history."""


@dataclass(frozen=True, slots=True)
class ConstituentChange:
    effective_from: date
    symbol: str
    action: Action
    source: str


class PointInTimeUniverse:
    def __init__(self, snapshots: Sequence[tuple[date, frozenset[str]]]) -> None:
        self._snapshots = tuple(snapshots)

    @classmethod
    def from_changes(cls, changes: Iterable[ConstituentChange]) -> PointInTimeUniverse:
        ordered = sorted(changes, key=lambda change: (change.effective_from, change.symbol))

        members: set[str] = set()
        snapshots: list[tuple[date, frozenset[str]]] = []

        for change in ordered:
            if not change.source.strip():
                raise ValueError(
                    f"{change.symbol} on {change.effective_from} states no source; "
                    "every add and drop must cite its NSE press release"
                )
            if change.action == "ADD":
                if change.symbol in members:
                    raise ValueError(
                        f"{change.symbol} added on {change.effective_from} but is already a member"
                    )
                members.add(change.symbol)
            else:
                if change.symbol not in members:
                    raise ValueError(
                        f"{change.symbol} dropped on {change.effective_from} but was never added"
                    )
                members.remove(change.symbol)

            if snapshots and snapshots[-1][0] == change.effective_from:
                snapshots[-1] = (change.effective_from, frozenset(members))
            else:
                snapshots.append((change.effective_from, frozenset(members)))

        return cls(snapshots)

    def constituents_on(self, on: date) -> frozenset[str]:
        """Membership as of a date. Refuses rather than guessing for uncovered dates."""
        if not self._snapshots or on < self._snapshots[0][0]:
            raise UniverseNotCoveredError(
                f"no constituent history covers {on}; refusing to fall back to a later list"
            )
        current = self._snapshots[0][1]
        for effective_from, members in self._snapshots:
            if effective_from > on:
                break
            current = members
        return current

    def dates_with_unexpected_size(self, expected: int) -> list[date]:
        """Every effective date whose membership is not the expected index size."""
        return [on for on, members in self._snapshots if len(members) != expected]
