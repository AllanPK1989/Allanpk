"""The six metrics this system is optimised for, and the capital requirement model.

The spec is explicit that win rate is not what matters here: with no stop loss a losing
position is never realised, so a 90%+ win rate is produced by construction even in an
account that is deeply underwater. Win rate measures how well losses are hidden.

So it is computed, but it is deliberately kept out of `headline()`. Seeing a 95% win
rate sitting beside a 25% book drawdown is the whole point.

Definitions here match the pre-registered kill criteria file exactly, deliberately. If
they drifted, a result could satisfy the metrics and breach the criteria, or the
reverse, and nobody would notice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean

from nifty_shop.money import Paisa


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """One trading session's state, marked on the settled close."""

    on: date
    book_equity: Paisa
    deployed_capital: Paisa
    open_lots: int
    lots_closed: int
    open_at_start: int


def _indian_format(paisa: Paisa) -> str:
    """Render in the lakh/crore grouping the account statements use."""
    rupees_part = abs(paisa) // 100
    text = str(rupees_part)
    if len(text) <= 3:
        grouped = text
    else:
        head, tail = text[:-3], text[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        grouped = ",".join([*parts, tail])
    return ("-" if paisa < 0 else "") + grouped


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]


@dataclass(frozen=True)
class BacktestMetrics:
    allocated_capital: Paisa
    final_book_equity: Paisa
    return_on_allocated_pct: float
    return_on_deployed_pct: float
    max_book_drawdown_pct: float
    peak_open_lots: int
    peak_capital_deployed: Paisa
    peak_capital_pct_of_allocated: float
    longest_zero_exit_sessions: int
    target_exit_count: int
    days_to_target_mean: float
    days_to_target_median: int
    days_to_target_p90: int
    days_to_target_max: int
    win_rate_pct: float
    sessions: int

    def headline(self) -> str:
        """Return and capital requirement together, always. Never win rate.

        An acceptance criterion requires every performance report to carry the capital
        requirement model alongside it, so the two cannot be separated here.
        """
        return (
            f"return on allocated capital {self.return_on_allocated_pct:.1f}% "
            f"| max book drawdown {self.max_book_drawdown_pct:.1f}% "
            f"| peak {self.peak_open_lots} open lots "
            f"| peak capital INR {_indian_format(self.peak_capital_deployed)} "
            f"({self.peak_capital_pct_of_allocated:.1f}% of allocation) "
            f"| longest zero-exit stretch {self.longest_zero_exit_sessions} sessions "
            f"| days-to-target median {self.days_to_target_median}, "
            f"p90 {self.days_to_target_p90}, max {self.days_to_target_max}"
        )


def compute_metrics(
    records: list[SessionRecord],
    days_to_target: list[int],
    allocated_capital: Paisa,
    wins: int = 0,
    losses: int = 0,
) -> BacktestMetrics:
    if not records:
        raise ValueError("cannot compute metrics over an empty run")

    allocated = int(allocated_capital)
    final_equity = int(records[-1].book_equity)

    peak_equity = allocated
    max_drawdown = 0.0
    for record in records:
        equity = int(record.book_equity)
        peak_equity = max(peak_equity, equity)
        if peak_equity > 0:
            max_drawdown = max(max_drawdown, (peak_equity - equity) / peak_equity * 100.0)

    peak_lots = max(record.open_lots for record in records)
    peak_deployed = max(int(record.deployed_capital) for record in records)

    streak = 0
    longest_streak = 0
    for record in records:
        if record.open_at_start == 0 or record.lots_closed > 0:
            streak = 0
            continue
        streak += 1
        longest_streak = max(longest_streak, streak)

    profit = final_equity - allocated
    on_allocated = (profit / allocated * 100.0) if allocated else 0.0
    on_deployed = (profit / peak_deployed * 100.0) if peak_deployed else 0.0
    decided = wins + losses

    return BacktestMetrics(
        allocated_capital=allocated_capital,
        final_book_equity=Paisa(final_equity),
        return_on_allocated_pct=round(on_allocated, 4),
        return_on_deployed_pct=round(on_deployed, 4),
        max_book_drawdown_pct=round(max_drawdown, 4),
        peak_open_lots=peak_lots,
        peak_capital_deployed=Paisa(peak_deployed),
        peak_capital_pct_of_allocated=(
            round(peak_deployed / allocated * 100.0, 4) if allocated else 0.0
        ),
        longest_zero_exit_sessions=longest_streak,
        target_exit_count=len(days_to_target),
        days_to_target_mean=round(mean(days_to_target), 2) if days_to_target else 0.0,
        days_to_target_median=_percentile(days_to_target, 0.5),
        days_to_target_p90=_percentile(days_to_target, 0.9),
        days_to_target_max=max(days_to_target) if days_to_target else 0,
        win_rate_pct=round(wins / decided * 100.0, 2) if decided else 0.0,
        sessions=len(records),
    )


def render_report(metrics: BacktestMetrics, breaches: list[object]) -> str:
    """Breaches first, before any performance number. The kill criteria file says so."""
    lines: list[str] = []
    if breaches:
        for breach in breaches:
            lines.append(str(breach))
        lines.append("")
    lines.append(metrics.headline())
    lines.append(
        f"  final book equity INR {_indian_format(metrics.final_book_equity)} "
        f"on allocated INR {_indian_format(metrics.allocated_capital)} "
        f"over {metrics.sessions} sessions"
    )
    lines.append(
        f"  (win rate {metrics.win_rate_pct:.1f}% — reported last, and only because a "
        "no-stop-loss book produces a high one by construction)"
    )
    return "\n".join(lines)
