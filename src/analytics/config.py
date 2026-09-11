"""Analytics configuration.

Every assumption an analytics calculation depends on lives here, never
hard-coded inside a calculation function -- matching the same discipline
Phase 2's EngineConfig established.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class ReturnFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class TurnoverMethod(str, Enum):
    """min(purchases, sales) / average value -- the standard convention,
    counting only the smaller side so a simple rebalance (sell X, buy X)
    isn't double-counted as 200% turnover."""
    LESSER_OF_BUYS_SELLS = "lesser_of_buys_sells"
    TOTAL_TRADED = "total_traded"  # (buys + sells) / average value


@dataclass(frozen=True)
class AnalyticsConfig:
    currency: str = "AUD"

    # Risk metrics need a return series with real (not carried-forward)
    # observations. This dataset is priced quarterly, so QUARTERLY is the
    # finest frequency that reflects genuine market movement rather than an
    # artefact of carrying a stale value forward -- see docs/analytics.md
    # "Why quarterly risk metrics". DAILY/WEEKLY/MONTHLY are supported by the
    # interface for a data source that has real prices at that frequency, but
    # report UNAVAILABLE against this one.
    risk_return_frequency: ReturnFrequency = ReturnFrequency.QUARTERLY
    risk_annualisation_periods: dict[ReturnFrequency, int] = field(
        default_factory=lambda: {
            ReturnFrequency.DAILY: 252, ReturnFrequency.WEEKLY: 52,
            ReturnFrequency.MONTHLY: 12, ReturnFrequency.QUARTERLY: 4})

    # No risk-free rate is configured by default. Sharpe/Sortino must report
    # UNAVAILABLE rather than assume zero -- an assumed 0% risk-free rate is a
    # real, material choice, not a harmless default.
    risk_free_rate_annual: Decimal | None = None

    turnover_method: TurnoverMethod = TurnoverMethod.LESSER_OF_BUYS_SELLS

    # A metric attributed to fewer than this many observations is statistical
    # noise dressed as precision (e.g. "volatility" from 2 data points).
    minimum_observations_for_risk_metrics: int = 6

    reconciliation_tolerance: Decimal = Decimal("0.05")
    rounding_precision: int = 2

    # Trailing income yield window, in months.
    trailing_income_months: int = 12


DEFAULT_ANALYTICS_CONFIG = AnalyticsConfig()
