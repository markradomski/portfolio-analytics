"""Allocation, drift and concentration (sec 13-15).

Reads Phase 3's holding_daily/allocation_history exclusively. Sector,
geography and currency breakdowns are supported by the interface, but this
portfolio's securities carry no such metadata -- Vanguard statements print a
product name and a ticker, nothing else -- so those dimensions report
UNAVAILABLE rather than a guessed classification. Only "security" and
"asset_class" (Phase 3's configured classification) are populated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analytics.result import DataQuality, Metric, unavailable
from src.history.config import Granularity
from src.history.service import HistoryService

ZERO = Decimal("0")

SUPPORTED_DIMENSIONS = ("security", "asset_class")
UNSUPPORTED_DIMENSIONS = ("sector", "geography", "currency", "account")


def allocation(service: HistoryService, by: str = "security",
               on: date | None = None) -> dict:
    """Current (or as-at) allocation. Delegates to Phase 3's own bucketing so
    a single-date allocation always agrees with the historical series."""
    if by in UNSUPPORTED_DIMENSIONS:
        return {"by": by, "status": "unavailable",
                "note": f"no {by} metadata exists in the source statements"
                        " -- Vanguard prints a product name and ticker only"}
    end = on or _latest_date(service)
    if end is None:
        return {"by": by, "status": "unavailable", "note": "no portfolio history"}
    rows = service.allocation_history(
        by="asset_class" if by == "asset_class" else "security",
        granularity=Granularity.DAILY)
    row = next((r for r in rows if r["date"] == end.isoformat()), None)
    if row is None:
        return {"by": by, "status": "unavailable",
                "note": f"no allocation computed for {end}"}
    return {"by": by, "date": row["date"], "total": row["total"],
           "weights": row["weights"], "allocation_pct": row["allocation_pct"],
           "status": "ok"}


def allocation_history(service: HistoryService, by: str = "asset_class",
                       granularity: Granularity = Granularity.MONTHLY) -> list[dict]:
    if by in UNSUPPORTED_DIMENSIONS:
        return []
    return service.allocation_history(by=by, granularity=granularity)


def _latest_date(service: HistoryService) -> date | None:
    dates = sorted(date.fromisoformat(r["date"]) for r in service.portfolio_history())
    return dates[-1] if dates else None


@dataclass(frozen=True)
class AllocationDrift:
    key: str
    target_weight: Decimal
    actual_weight: Decimal | None
    drift: Decimal | None


def allocation_drift(service: HistoryService, targets: dict[str, Decimal],
                     by: str = "asset_class", on: date | None = None
                     ) -> list[AllocationDrift]:
    """Target allocations are a pure analytics/configuration concept (sec 14):
    passed in by the caller, never read from or written to the accounting
    engine or Phase 3's stored tables."""
    current = allocation(service, by=by, on=on)
    actual = ({k: Decimal(v) for k, v in current.get("allocation_pct", {}).items()
              if v is not None} if current.get("status") == "ok" else {})
    out = []
    for key, target in sorted(targets.items()):
        weight = actual.get(key)
        out.append(AllocationDrift(
            key=key, target_weight=target, actual_weight=weight,
            drift=(weight - target) if weight is not None else None))
    return out


@dataclass(frozen=True)
class ConcentrationSnapshot:
    date: date
    largest_holding_pct: Decimal | None
    top_5_pct: Decimal | None
    top_10_pct: Decimal | None
    herfindahl_index: Decimal | None   # sum of squared weights, 0..1
    holding_count: int


def concentration(service: HistoryService, on: date | None = None) -> ConcentrationSnapshot:
    """HHI here is the standard 0-1 form (sum of squared weights): 1/n for an
    equally weighted n-security portfolio, 1.0 for a single holding."""
    end = on or _latest_date(service)
    if end is None:
        return ConcentrationSnapshot(date.today(), None, None, None, None, 0)
    weights = sorted(
        (Decimal(h["allocation_pct"]) for h in
         service.holdings_history(start=end, end=end) if h["allocation_pct"]),
        reverse=True)
    if not weights:
        return ConcentrationSnapshot(end, None, None, None, None, 0)
    return ConcentrationSnapshot(
        date=end, largest_holding_pct=weights[0],
        top_5_pct=sum(weights[:5], ZERO), top_10_pct=sum(weights[:10], ZERO),
        herfindahl_index=sum((w * w for w in weights), ZERO),
        holding_count=len(weights))


def concentration_history(service: HistoryService,
                          granularity: Granularity = Granularity.MONTHLY
                          ) -> list[ConcentrationSnapshot]:
    dates = sorted({date.fromisoformat(r["date"])
                    for r in service.portfolio_history(granularity=granularity)})
    return [concentration(service, on=d) for d in dates]
