"""Historical prices, and honesty about where a value came from.

The only prices available are the quarter-end closing prices printed on the
statements -- roughly 23 dates over six years. A value is therefore labelled
with how it was obtained, and nothing is ever priced at today's market.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Protocol

from src.database.repository import Repository


class PriceQuality(str, Enum):
    """How a security's price was obtained. Distinct from history's
    ValuationStatus, which describes the whole portfolio's value against what
    Vanguard reported -- a different tier in the same hierarchy (see
    docs/valuation.md). Not reused here to avoid two enums both claiming
    "CALCULATED" while meaning different things.
    """
    NOT_HELD = "not_held"      # zero units: nothing to price
    QUOTED = "quoted"          # a price Vanguard printed for this exact date
    CARRIED_FORWARD = "carried_forward"  # the most recent earlier price
    UNAVAILABLE = "unavailable"          # no price at or before this date


# Where a price came from. Only one source exists today (Vanguard's own
# printed quarter-end prices), but the field exists so a future market-data
# source has somewhere unambiguous to identify itself.
VANGUARD_SECURITY_PRICE = "vanguard_security_price"


@dataclass(frozen=True)
class Quote:
    price: Decimal | None
    quality: "PriceQuality"
    as_at: date | None          # the date the price was actually quoted
    source: str | None = None   # e.g. VANGUARD_SECURITY_PRICE; None if unpriced


class PriceSource(Protocol):
    def quote(self, security_id: str, on: date) -> Quote: ...


class SnapshotPriceSource:
    """Prices taken from quarter-end holdings snapshots.

    An exact date match is a real quoted price. Between snapshots the last
    known price is carried forward and labelled ESTIMATED -- never
    interpolated, and never filled from a later date.
    """

    def __init__(self, prices: dict[str, list[tuple[date, Decimal]]]):
        self._prices = {k: sorted(v) for k, v in prices.items()}
        self._dates = {k: [d for d, _ in v] for k, v in self._prices.items()}

    @classmethod
    def from_repository(cls, repo: Repository) -> "SnapshotPriceSource":
        prices: dict[str, list[tuple[date, Decimal]]] = defaultdict(list)
        for row in repo.rows(
            "SELECT security_id, reporting_date, price FROM holdings"
            " WHERE price IS NOT NULL"
        ):
            prices[row["security_id"]].append(
                (date.fromisoformat(row["reporting_date"]), Decimal(row["price"])))
        return cls(prices)

    def quote(self, security_id: str, on: date) -> Quote:
        dates = self._dates.get(security_id)
        if not dates:
            return Quote(None, PriceQuality.UNAVAILABLE, None)
        index = bisect_right(dates, on)
        if index == 0:
            return Quote(None, PriceQuality.UNAVAILABLE, None)
        as_at, price = self._prices[security_id][index - 1]
        quality = (PriceQuality.QUOTED if as_at == on
                   else PriceQuality.CARRIED_FORWARD)
        return Quote(price, quality, as_at, VANGUARD_SECURITY_PRICE)

    def priced_dates(self) -> tuple[date, ...]:
        return tuple(sorted({d for series in self._prices.values() for d, _ in series}))
