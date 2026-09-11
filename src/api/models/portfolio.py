"""Portfolio overview, daily history and state (sec 8: Portfolio family)."""

from __future__ import annotations

from src.api.models.common import (ApiModel, DataCoverage, DataQuality,
                                    DecimalString, ISODate, ValuationStatus)
from src.api.models.holdings import HoldingRow


class PortfolioOverview(ApiModel):
    as_at: ISODate | None = None
    current_value: DecimalString | None = None
    total_contributed: DecimalString
    total_withdrawn: DecimalString
    net_contributed: DecimalString
    investment_growth: DecimalString | None = None
    income_received: DecimalString
    data_coverage: DataCoverage


class PortfolioDailyPoint(ApiModel):
    """One row of the canonical daily series (src/history/generator.py
    DailyRow). total_value/securities_value/unrealised_gain are explicitly
    nullable -- a day with no computable value is a gap, never a fabricated
    zero (Phase 3's own central rule, preserved here rather than re-decided)."""
    date: ISODate
    total_value: DecimalString | None = None
    securities_value: DecimalString | None = None
    cash: DecimalString
    cost_basis: DecimalString
    invested_capital: DecimalString
    realised_gain: DecimalString
    unrealised_gain: DecimalString | None = None
    dividends: DecimalString
    distributions: DecimalString
    income: DecimalString
    fees: DecimalString
    cumulative_contributions: DecimalString
    cumulative_withdrawals: DecimalString
    high_water_mark: DecimalString
    drawdown_value: DecimalString | None = None
    drawdown_pct: DecimalString | None = None
    return_index: DecimalString | None = None
    index_as_at: ISODate | None = None
    return_high_water: DecimalString | None = None
    return_drawdown_pct: DecimalString | None = None
    valuation_status: ValuationStatus
    valuation_source: str
    price_as_at: ISODate | None = None
    source_count: int
    calculation_method: str


class PortfolioState(PortfolioDailyPoint):
    """A daily point plus the holdings that made it up -- what
    getHoldings()/portfolio_state() returns for one date."""
    holdings: list[HoldingRow] = []
