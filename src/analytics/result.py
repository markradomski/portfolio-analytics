"""The metadata envelope every analytics result is returned in.

Per the spec: "A user should be able to inspect a metric and understand what
is it, when was it measured, how was it calculated, what data was used, is the
data complete." A bare number never satisfies that; this wrapper is how every
function in this package answers it without repeating the same five fields by
hand everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any


class DataQuality(str, Enum):
    ACTUAL = "actual"            # built entirely from reported/quoted values
    CALCULATED = "calculated"    # built from real prices, computed by us
    ESTIMATED = "estimated"      # built partly from carried-forward prices
    LIMITED = "limited"          # technically calculated, but from a sparse sample
    UNAVAILABLE = "unavailable"  # cannot be computed from what's available


class Confidence(str, Enum):
    """A coarse, human-readable companion to DataQuality/observations -- for
    a UI to show a single word rather than requiring the viewer to interpret
    an observation count themselves."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass(frozen=True)
class Metric:
    """One analytics value, with enough attached to explain it on its own."""
    name: str
    value: Decimal | str | int | None
    methodology: str
    data_quality: DataQuality
    period_start: date | None = None
    period_end: date | None = None
    currency: str | None = None
    note: str | None = None
    # Present only when relevant (risk metrics, benchmark comparisons).
    frequency: str | None = None
    annualisation: str | None = None
    annualisation_factor: Decimal | None = None
    risk_free_rate: Decimal | None = None
    benchmark: str | None = None
    # Sample-size honesty (sec 1): how many real observations this metric was
    # built from, and a coarse confidence label derived from that count.
    observations: int | None = None
    confidence: Confidence | None = None
    source: str = "phase2-phase3-derived"

    @property
    def available(self) -> bool:
        return self.data_quality is not DataQuality.UNAVAILABLE

    @property
    def reason(self) -> str | None:
        """Alias for `note` when it explains unavailability -- the spec uses
        both names (sec 1's example: 'reason'; sec 38: notes/methodology).
        Kept as one field internally so there is only one thing to update."""
        return self.note

    def to_dict(self) -> dict[str, Any]:
        data = {k: v for k, v in asdict(self).items() if v is not None}
        data["available"] = self.available
        if self.note is not None:
            data["reason"] = self.note
        return data


def unavailable(name: str, methodology: str, note: str, **extra) -> Metric:
    """A Metric explicitly marked UNAVAILABLE, with the reason stated -- the
    spec's repeated instruction: report why a metric can't be computed rather
    than silently returning zero or omitting it."""
    return Metric(name=name, value=None, methodology=methodology,
                  data_quality=DataQuality.UNAVAILABLE, note=note,
                  confidence=Confidence.NONE, **extra)


def confidence_for(observations: int, minimum: int) -> Confidence:
    """A coarse mapping from sample size to a human word. `minimum` is the
    configured floor below which a metric is refused outright (UNAVAILABLE);
    values above it still range from LOW (barely enough) to HIGH (a genuinely
    large sample)."""
    if observations < minimum:
        return Confidence.NONE
    if observations < minimum * 2:
        return Confidence.LOW
    if observations < minimum * 4:
        return Confidence.MEDIUM
    return Confidence.HIGH
