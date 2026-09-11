"""Holdings and allocation (sec 8: Holdings family)."""

from __future__ import annotations

from src.api.models.common import (ApiModel, AssetClass, DecimalString,
                                    ISODate, ValuationStatus)


class HoldingRow(ApiModel):
    date: ISODate
    security_id: str
    code: str
    units: DecimalString
    price: DecimalString | None = None
    market_value: DecimalString | None = None
    cost_basis: DecimalString
    unrealised_gain: DecimalString | None = None
    allocation_pct: DecimalString | None = None
    asset_class: AssetClass
    valuation_status: ValuationStatus
    price_as_at: ISODate | None = None


class AllocationResult(ApiModel):
    """getAllocation(). `status` is "unavailable" for a dimension the source
    data can't support (sector/geography/currency) -- weights/allocation_pct
    are then absent entirely, never an empty-but-present dict that could be
    mistaken for "zero of everything" (sec 9)."""
    by: str
    status: str  # "ok" | "unavailable"
    date: ISODate | None = None
    total: DecimalString | None = None
    weights: dict[str, DecimalString] | None = None
    allocation_pct: dict[str, DecimalString | None] | None = None
    note: str | None = None


class ConcentrationSnapshot(ApiModel):
    date: ISODate
    largest_holding_pct: DecimalString | None = None
    top_5_pct: DecimalString | None = None
    top_10_pct: DecimalString | None = None
    herfindahl_index: DecimalString | None = None
    holding_count: int


class UnrealisedGainSnapshot(ApiModel):
    security_id: str
    code: str
    asset_class: str
    market_value: DecimalString | None = None
    cost_basis: DecimalString
    unrealised_gain: DecimalString | None = None
    unrealised_gain_pct: DecimalString | None = None


class AllocationHistoryPoint(ApiModel):
    """One bucket of history.allocation_history() -- weights and normalised
    percentages through time, keyed by security code or asset class
    depending on `by` (sec 8's allocation family, history variant)."""
    date: ISODate
    total: DecimalString
    weights: dict[str, DecimalString]
    allocation_pct: dict[str, DecimalString | None]
