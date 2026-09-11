"""Shared API schema primitives.

Every financial value that flows through the API is a `DecimalString`: the
exact Decimal string Phase 2-4 produced, never a JSON number. Pydantic
validates these fields as plain `str` in STRICT mode -- if a float ever
leaks in from a serialisation bug, validation rejects it loudly at the API
boundary rather than silently rounding it through IEEE754 on the way to the
frontend. This is the single rule the whole contract exists to enforce (sec
4, 9): a `DecimalString` field must never become a `number` anywhere in this
pipeline.
"""

from __future__ import annotations

from datetime import date as _date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# A decimal transported as an exact string. Pydantic v2's strict=True on a
# str field rejects a float/int at validation time rather than coercing it --
# exactly the guard rail sec 4 asks for. Matches TypeScript's `DecimalString`.
DecimalString = Annotated[str, StringConstraints(strict=True)]

ISODate = _date  # FastAPI/Pydantic already serialise date -> "YYYY-MM-DD".

DataQuality = Literal["actual", "calculated", "estimated", "limited", "unavailable"]
Confidence = Literal["high", "medium", "low", "none"]
ValuationStatus = Literal["actual", "calculated", "estimated", "unavailable"]
ReconciliationStatus = Literal["PASS", "FAIL", "LIMITED"]
AssetClass = Literal[
    "australian_equities", "international_equities", "bonds", "property",
    "cash", "other", "unknown",
]
TwrrMethodologyName = Literal["SUBPERIOD_LINKED"]
CashFlowAdjustmentMethod = Literal["EXACT_DATED"]
CashFlowObservationQuality = Literal["LIMITED", "SUFFICIENT"]


class ApiModel(BaseModel):
    """Base for every response model. `populate_by_name` lets a model be
    built directly from the existing dataclass-derived dict (via
    src/api/serialize.py's to_json(), which already turns Decimal/date/Enum
    into JSON-safe primitives) without a field-by-field remapping layer --
    the Pydantic model's job is to validate and describe that shape for
    OpenAPI, not to re-derive it."""
    model_config = ConfigDict(populate_by_name=True)


class Metric(ApiModel):
    """The metadata envelope every analytics figure carries (sec 5) --
    mirrors src/analytics/result.py Metric exactly. A metric's availability
    must never be inferred from a missing field: `available` and `reason`
    are always present, even when `value` is null."""
    name: str
    value: DecimalString | None = None
    methodology: str
    data_quality: DataQuality
    period_start: ISODate | None = None
    period_end: ISODate | None = None
    currency: str | None = None
    note: str | None = None
    frequency: str | None = None
    annualisation: str | None = None
    annualisation_factor: DecimalString | None = None
    risk_free_rate: DecimalString | None = None
    benchmark: str | None = None
    observations: int | None = None
    confidence: Confidence | None = None
    source: str
    available: bool
    reason: str | None = None


class Capability(ApiModel):
    """One entry in getAnalyticsCapabilities() (sec 6): whether a metric can
    be shown, and why not when it can't. The frontend must never infer this
    from absent data -- both fields are always present."""
    available: bool
    reason: str | None = None


class DataCoverage(ApiModel):
    """getDataCoverage() (sec 7) -- the exact fields verified live in Phase
    5.1-5.4: '30 Sept 2020 - 30 June 2026, 24 valuation observations,
    quarterly source data' must be reconstructable from these fields alone,
    never hard-coded on the frontend."""
    valuation_start: ISODate | None = None
    valuation_end: ISODate | None = None
    valuation_observation_count: int
    transaction_start: ISODate | None = None
    transaction_end: ISODate | None = None
    price_observation_count: int
    missing_valuation_count: int
    actual_observation_count: int
    carried_forward_observation_count: int
    estimated_observation_count: int
    unavailable_observation_count: int


class ReconciliationResult(ApiModel):
    """Sec 8/hardening sec 3's exact vocabulary. reconciliation_status is
    always derived from residual/tolerance upstream (src/analytics/
    attribution.py) -- this model only describes that contract, it does not
    re-derive it. Legacy aliases (difference/status) are retained since nothing
    downstream should need to change to stop reading them, but attributed_change/
    actual_change/residual/reconciliation_status/tolerance are the primary,
    documented fields (sec 8: 'do not reintroduce alternative terminology' --
    meaning these five names are authoritative, not the aliases)."""
    attributed_change: DecimalString | None = None
    actual_change: DecimalString | None = None
    residual: DecimalString | None = None
    tolerance: DecimalString
    reconciliation_status: ReconciliationStatus
    opening_value: DecimalString | None = None
    closing_value: DecimalString | None = None
    external_flows: DecimalString | None = None
    note: str | None = None
    difference: DecimalString | None = None
    status: ReconciliationStatus
