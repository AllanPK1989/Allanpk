"""Goal, SIP and retirement planning maths (monthly compounding, contributions at the start of each month)."""

from __future__ import annotations

from typing import Any

# Long-run nominal return assumptions in INR, used as defaults. Conservative on purpose.
ASSUMED_RETURNS = {"equity_india": 11.0, "equity_global": 10.0, "debt": 7.0, "gold": 8.0, "cash": 6.0, "crypto": 12.0}


def _monthly(rate_pct: float) -> float:
    return (1 + rate_pct / 100) ** (1 / 12) - 1


def sip_future_value(monthly: float, annual_return_pct: float, years: float, *, step_up_pct: float = 0.0,
                     initial: float = 0.0) -> float:
    r = _monthly(annual_return_pct)
    value, contrib = initial, monthly
    for m in range(int(round(years * 12))):
        if m and m % 12 == 0:
            contrib *= 1 + step_up_pct / 100
        value = (value + contrib) * (1 + r)
    return value


def lumpsum_future_value(amount: float, annual_return_pct: float, years: float) -> float:
    return amount * (1 + annual_return_pct / 100) ** years


def required_sip(target: float, annual_return_pct: float, years: float, *, step_up_pct: float = 0.0,
                 initial: float = 0.0) -> float:
    if target <= sip_future_value(0, annual_return_pct, years, initial=initial):
        return 0.0
    lo, hi = 0.0, max(target, 1.0)
    for _ in range(200):
        mid = (lo + hi) / 2
        if sip_future_value(mid, annual_return_pct, years, step_up_pct=step_up_pct, initial=initial) < target:
            lo = mid
        else:
            hi = mid
    return hi


def yearly_table(monthly: float, annual_return_pct: float, years: int, *, step_up_pct: float = 0.0,
                 initial: float = 0.0) -> list[dict[str, float]]:
    r = _monthly(annual_return_pct)
    value, contrib, invested, rows = initial, monthly, initial, []
    for m in range(years * 12):
        if m and m % 12 == 0:
            contrib *= 1 + step_up_pct / 100
        value = (value + contrib) * (1 + r)
        invested += contrib
        if (m + 1) % 12 == 0:
            rows.append({"year": (m + 1) // 12, "invested": round(invested), "value": round(value)})
    return rows


def goal_plan(*, target_today: float, years: float, inflation_pct: float = 6.0, expected_return_pct: float = 11.0,
              current_savings: float = 0.0, step_up_pct: float = 0.0) -> dict[str, Any]:
    future_target = target_today * (1 + inflation_pct / 100) ** years
    sip = required_sip(future_target, expected_return_pct, years, step_up_pct=step_up_pct, initial=current_savings)
    lumpsum = max(0.0, (future_target - lumpsum_future_value(current_savings, expected_return_pct, years))
                  / (1 + expected_return_pct / 100) ** years)
    return {
        "future_target": round(future_target), "monthly_sip": round(sip), "lumpsum_today_instead": round(lumpsum),
        "assumptions": {"years": years, "inflation_pct": inflation_pct, "expected_return_pct": expected_return_pct,
                        "step_up_pct": step_up_pct, "current_savings": current_savings},
        "table": yearly_table(round(sip), expected_return_pct, int(years), step_up_pct=step_up_pct, initial=current_savings),
        "suggested_equity_pct": suggested_equity_pct(years),
    }


def retirement_plan(*, current_age: int, retire_age: int, life_expectancy: int = 85, monthly_expense_today: float,
                    inflation_pct: float = 6.0, pre_return_pct: float = 11.0, post_return_pct: float = 7.5,
                    current_corpus: float = 0.0, step_up_pct: float = 10.0) -> dict[str, Any]:
    years_to = max(0, retire_age - current_age)
    years_in = max(1, life_expectancy - retire_age)
    first_year_expense = monthly_expense_today * 12 * (1 + inflation_pct / 100) ** years_to
    # Present value at retirement of a growing annuity (expenses paid at the start of each year).
    g, r = inflation_pct / 100, post_return_pct / 100
    if abs(r - g) < 1e-9:
        corpus = first_year_expense * years_in
    else:
        corpus = first_year_expense * (1 - ((1 + g) / (1 + r)) ** years_in) / (r - g) * (1 + r)
    sip = required_sip(corpus, pre_return_pct, years_to, step_up_pct=step_up_pct, initial=current_corpus) if years_to else 0.0
    return {
        "years_to_retirement": years_to, "years_in_retirement": years_in,
        "monthly_expense_at_retirement": round(first_year_expense / 12), "corpus_needed": round(corpus),
        "monthly_sip": round(sip), "step_up_pct": step_up_pct,
        "assumptions": {"inflation_pct": inflation_pct, "pre_retirement_return_pct": pre_return_pct,
                        "post_retirement_return_pct": post_return_pct, "current_corpus": current_corpus},
        "table": yearly_table(round(sip), pre_return_pct, years_to, step_up_pct=step_up_pct, initial=current_corpus),
    }


def suggested_equity_pct(years: float, risk_profile: str = "moderate") -> int:
    """Equity share by horizon: little for <3 years, more as the horizon lengthens."""
    if years < 3:
        base = 10
    elif years < 5:
        base = 35
    elif years < 8:
        base = 55
    else:
        base = 70
    adj = {"conservative": -15, "moderate": 0, "aggressive": 10}.get(risk_profile, 0)
    return max(0, min(90, base + adj))
