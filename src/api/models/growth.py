"""Portfolio Growth (Step 9): the canonical dataset behind the redesigned
primary chart. Contributions/withdrawals/net_contributions/investment_gain
are kept as named, separate fields throughout -- never collapsed into a
single "growth" number the frontend would have to reverse-engineer (sec 12:
the API contract mirrors PortfolioGrowthPoint/PortfolioPerformance from the
Step 9 spec, adapted to this project's DecimalString-over-the-wire and
ApiModel conventions rather than copied as JS numbers)."""

from __future__ import annotations

from typing import Literal

from src.api.models.common import ApiModel, DecimalString, ISODate

CashFlowType = Literal["CONTRIBUTION", "WITHDRAWAL"]
ReconciliationCheckStatus = Literal["PASS", "FAIL", "SKIP"]


class CashFlowEvent(ApiModel):
    """One contribution or withdrawal, traceable back to its own source
    transaction_id (sec 11: data provenance) -- the same id
    /api/portfolio/activity already surfaces for this transaction."""
    transaction_id: str
    date: ISODate
    type: CashFlowType
    amount: DecimalString  # signed: positive = contribution, negative = withdrawal
    account: str
    source: str
    description: str | None = None


class PortfolioGrowthPoint(ApiModel):
    """One day of the canonical growth series (sec 4). `contributions`/
    `withdrawals` are this day's own flows, not running totals --
    `net_contributions` is the running total (cumulative_contributions +
    cumulative_withdrawals; withdrawals are signed negative throughout this
    API, matching ContributionHistoryRow). `portfolio_value`/
    `investment_gain` are null together whenever this date has no
    computable valuation -- never a fabricated 0 on a gap day.

    `period_investment_gain` is this day's own gain/loss (not cumulative):
    balance[t] - balance[t-1] - (contributions[t] + withdrawals[t]). This
    is the value the chart's Investment Gain/Investment Loss areas plot --
    positive renders as a solid bright-green area above the zero baseline,
    negative as solid bright-red below it; the two are mutually exclusive
    at every point, and neither is ever labelled with the other's colour."""
    date: ISODate
    portfolio_value: DecimalString | None = None
    contributions: DecimalString
    withdrawals: DecimalString
    net_contributions: DecimalString
    investment_gain: DecimalString | None = None
    period_investment_gain: DecimalString | None = None
    cash_flow_events: list[CashFlowEvent] = []


class PortfolioGrowthSummary(ApiModel):
    """The headline split (sec 8): current value, what was actually put in,
    and the simple dollar difference between them. `growth_pct` is
    investment_gain/net_contributions -- deliberately not called a "return"
    (sec 9): it does not account for when money arrived, unlike TWRR/XIRR,
    which live at /api/portfolio/performance and /performance/methodology."""
    current_value: DecimalString | None = None
    net_contributions: DecimalString
    investment_gain: DecimalString | None = None
    growth_pct: DecimalString | None = None
    as_at: ISODate


class PortfolioValueReconciliationCheck(ApiModel):
    """One reconciliation row (sec 10): calculated portfolio value/cash on a
    date vs. what Vanguard's own statement reported for that same date.
    `status` is SKIP when there was nothing to compare against (e.g. no
    reported cash balance on that particular statement) -- distinct from
    FAIL, which means a real, calculated discrepancy exists."""
    date: ISODate
    subject: str
    calculated: DecimalString | None = None
    source: DecimalString | None = None
    difference: DecimalString | None = None
    tolerance: DecimalString
    status: ReconciliationCheckStatus
