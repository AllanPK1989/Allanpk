"""Pre-registered kill criteria, made executable.

The dated markdown file is the registration. This module is what the reporting layer
actually consults, and a test asserts the two cannot drift apart.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class KillCriteria:
    registered_on: date
    strictness: str
    allocated_capital_inr: int
    max_drawdown_pct: float
    max_zero_exit_sessions: int
    max_peak_capital_pct: float

    @property
    def peak_capital_threshold_inr(self) -> int:
        return int(self.allocated_capital_inr * self.max_peak_capital_pct / 100)


@dataclass(frozen=True, slots=True)
class Breach:
    criterion: str
    description: str
    threshold: str
    observed: str

    def headline(self) -> str:
        return (
            f"{self.criterion} BREACHED — {self.description}: "
            f"{self.observed} (limit {self.threshold})"
        )


def load_kill_criteria(path: Path) -> KillCriteria:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return KillCriteria(
        registered_on=date.fromisoformat(raw["registered_on"]),
        strictness=raw["strictness"],
        allocated_capital_inr=raw["allocated_capital_inr"],
        max_drawdown_pct=raw["kc1_book_drawdown"]["max_drawdown_pct"],
        max_zero_exit_sessions=raw["kc2_zero_exit_stretch"]["max_sessions"],
        max_peak_capital_pct=raw["kc3_peak_capital"]["max_pct_of_allocated"],
    )


def evaluate(
    criteria: KillCriteria,
    *,
    max_book_drawdown_pct: float,
    longest_zero_exit_sessions: int,
    peak_capital_deployed_inr: int,
) -> list[Breach]:
    """Return every breached criterion. An empty list means the run survives.

    Thresholds are exclusive: the registration says "worse than" and "beyond", so a
    value exactly at the limit does not breach.
    """
    breaches: list[Breach] = []

    if max_book_drawdown_pct > criteria.max_drawdown_pct:
        breaches.append(
            Breach(
                criterion="KC-1",
                description="book drawdown marked to market including open lots",
                threshold=f"{criteria.max_drawdown_pct}%",
                observed=f"{max_book_drawdown_pct}%",
            )
        )

    if longest_zero_exit_sessions > criteria.max_zero_exit_sessions:
        breaches.append(
            Breach(
                criterion="KC-2",
                description="longest stretch with zero exits",
                threshold=f"{criteria.max_zero_exit_sessions} sessions",
                observed=f"{longest_zero_exit_sessions} sessions",
            )
        )

    if peak_capital_deployed_inr > criteria.peak_capital_threshold_inr:
        breaches.append(
            Breach(
                criterion="KC-3",
                description="peak capital deployed",
                threshold=f"INR {criteria.peak_capital_threshold_inr:,}",
                observed=f"INR {peak_capital_deployed_inr:,}",
            )
        )

    return breaches
