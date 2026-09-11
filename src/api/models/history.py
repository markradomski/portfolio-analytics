"""Calendar performance, milestones and activity (sec 8's remaining
families -- these read Phase 3 records, never a new transaction engine)."""

from __future__ import annotations

from pydantic import Field

from src.api.models.common import (ApiModel, DecimalString, ISODate,
                                    ReconciliationResult, ValuationStatus)


class CalendarPerformanceRow(ApiModel):
    period: str
    twrr: DecimalString | None = None
    xirr: DecimalString | None = None
    income: DecimalString
    contributions: DecimalString
    withdrawals: DecimalString
    closing_value: DecimalString | None = None
    valuation_status: ValuationStatus


class Milestone(ApiModel):
    milestone_id: str
    kind: str
    date: ISODate
    value: DecimalString | None = None
    description: str
    portfolio_value: DecimalString | None = None
    cumulative_contributions: DecimalString | None = None
    cumulative_investment_gain: DecimalString | None = None


class ActivityRow(ApiModel):
    transaction_id: str
    trade_date: ISODate
    type: str
    code: str | None = None
    units: DecimalString | None = None
    price: DecimalString | None = None
    net_amount: DecimalString | None = None
    description: str


class RollingReturnPoint(ApiModel):
    """One point of getRolling(metric='return') -- src/analytics/rolling.py
    RollingPoint. `is_estimate` is explicit rather than a silently
    carried-forward window edge (sec 9)."""
    date: ISODate
    value: DecimalString | None = None
    window_days: int
    is_estimate: bool


class RollingVolatilityPoint(ApiModel):
    as_at: ISODate
    volatility: DecimalString | None = None
    window_quarters: int
    observations: int
    frequency: str
    annualisation_factor: DecimalString
    data_quality: str


class RollingIncomeYieldPoint(ApiModel):
    date: ISODate
    yield_: DecimalString | None = Field(default=None, alias="yield")
    status: str


class ExtremePeriod(ApiModel):
    label: str
    period_start: ISODate
    period_end: ISODate
    return_pct: DecimalString
    absolute_change: DecimalString | None = None
    opening_value: DecimalString | None = None
    closing_value: DecimalString | None = None


# getBestWorstPeriods() maps a period key ("day"/"month"/"year") to either a
# list of best/worst ExtremePeriod entries or an explanatory string when that
# granularity cannot be reported honestly (sec 31) -- never a fabricated
# figure in place of the explanation.
BestWorstPeriods = dict[str, list[ExtremePeriod] | str]


class AttributionReconciliationPair(ApiModel):
    """getGrowthReconciliation()/getAttributionReconciliation() reported
    together -- two independent reconciliations of the same period, kept
    distinct rather than merged into one figure (sec 8/hardening sec 3)."""
    growth: ReconciliationResult
    attribution: ReconciliationResult


class HealthStatus(ApiModel):
    status: str
    database: bool
