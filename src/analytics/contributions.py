"""Contribution analysis and efficiency (sec 8-9).

Answers: how much of this portfolio's value is money I put in, versus money
it earned? Both figures come straight from the ledger's external-flow series
and the current state -- nothing here is a new calculation, only a
repackaging that makes the split visible in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.history.config import Granularity
from src.history.service import HistoryService

ZERO = Decimal("0")


@dataclass(frozen=True)
class ContributionSummary:
    total_contributed: Decimal
    total_withdrawn: Decimal
    net_contributed: Decimal
    investment_growth: Decimal | None    # None if the portfolio can't be valued now
    income_received: Decimal
    current_value: Decimal | None
    as_at: date


def contribution_summary(service: HistoryService, as_at: date | None = None) -> ContributionSummary:
    """The full-history split: money in, versus money earned (sec 8)."""
    history = service.contribution_history(Granularity.YEARLY)
    if not history:
        return ContributionSummary(ZERO, ZERO, ZERO, None, ZERO, None,
                                   as_at or date.today())
    latest = history[-1]
    total_in = Decimal(latest["cumulative_contributions"])
    total_out = Decimal(latest["cumulative_withdrawals"])
    net = total_in + total_out

    dates = sorted(date.fromisoformat(r["date"]) for r in service.portfolio_history())
    target = as_at or dates[-1]
    state = service.portfolio_state(target)
    current_value = Decimal(state["total_value"]) if state and state["total_value"] else None

    income = sum((Decimal(r["gross_income"])
                 for r in service.income_history(Granularity.YEARLY)), ZERO)

    investment_growth = (current_value - net) if current_value is not None else None

    return ContributionSummary(
        total_contributed=total_in, total_withdrawn=total_out, net_contributed=net,
        investment_growth=investment_growth, income_received=income,
        current_value=current_value, as_at=target)


@dataclass(frozen=True)
class ContributionEfficiency:
    """Deliberately not called "return" (sec 9): investment_gain /
    net_contributions is not a return methodology -- it doesn't account for
    when money arrived, unlike TWRR/XIRR. Useful as a rough "did this pay off"
    ratio, mislabelled as "return" it would overstate performance for a
    portfolio funded late and understate one funded early."""
    investment_gain: Decimal | None
    net_contributions: Decimal
    gain_per_dollar_contributed: Decimal | None
    methodology: str = "investment_gain / net_contributions (not a return methodology)"


def contribution_efficiency(service: HistoryService, as_at: date | None = None
                            ) -> ContributionEfficiency:
    summary = contribution_summary(service, as_at)
    ratio = None
    if summary.investment_growth is not None and summary.net_contributed > ZERO:
        ratio = summary.investment_growth / summary.net_contributed
    return ContributionEfficiency(
        investment_gain=summary.investment_growth,
        net_contributions=summary.net_contributed,
        gain_per_dollar_contributed=ratio)
