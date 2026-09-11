"""Performance overview, standard periods and TWRR methodology
(sec 8: Performance family)."""

from __future__ import annotations

from src.api.models.common import (ApiModel, CashFlowAdjustmentMethod,
                                    CashFlowObservationQuality, DataQuality,
                                    DecimalString, ISODate,
                                    TwrrMethodologyName, ValuationStatus)


class PerformanceOverview(ApiModel):
    period_start: ISODate
    period_end: ISODate
    opening_value: DecimalString | None = None
    closing_value: DecimalString | None = None
    contributions: DecimalString
    withdrawals: DecimalString
    net_external_flow: DecimalString
    investment_gain: DecimalString | None = None
    income: DecimalString
    fees: DecimalString
    total_return: DecimalString | None = None
    capital_return: DecimalString | None = None
    income_return: DecimalString | None = None
    twrr: DecimalString | None = None
    xirr: DecimalString | None = None
    data_quality: DataQuality


class PerformancePeriod(ApiModel):
    """One entry from getReturns() -- e.g. "1D", "3M", "INCEPTION". A period
    the API cannot measure (sec 5's "never let the frontend infer
    availability") reports status="unavailable" with `note` stating why,
    never a fabricated return."""
    label: str
    as_at: ISODate
    start_date: ISODate | None = None
    end_date: ISODate | None = None
    total_return: DecimalString | None = None
    capital_return: DecimalString | None = None
    income_return: DecimalString | None = None
    twrr: DecimalString | None = None
    xirr: DecimalString | None = None
    status: str  # ValuationStatus | "unavailable"
    note: str | None = None


class TwrrMethodology(ApiModel):
    """Preserves the exact vocabulary sec 8 calls out by name --
    SUBPERIOD_LINKED / EXACT_DATED must never be simplified away, since they
    are the frontend's only way to distinguish this dataset's approximation
    of TWRR from a true one (see docs/analytics.md 'Why quarterly risk
    metrics' and docs/api.md)."""
    twrr_methodology: TwrrMethodologyName
    twrr_methodology_note: str
    cash_flow_adjustment_method: CashFlowAdjustmentMethod
    cash_flow_adjustment_note: str
    cash_flow_observation_quality: CashFlowObservationQuality
    valuation_observation_count: int


class PerformanceMethodology(ApiModel):
    return_methodology: dict[str, str]
    twrr: TwrrMethodology
