"""Rolling metrics (sec 29).

Uses Phase 3's canonical daily series exclusively -- no second historical
dataset is built for this, per the spec's own instruction. A rolling window
is only reported at points where its start and end both fall on (or resolve
to) a genuine valuation, using the same effective-date reasoning
performance_periods() already applies -- a rolling "30-day return" computed
from two carried-forward values either side of a quarter would silently be a
quarter's movement mislabelled as a month's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from src.history.service import HistoryService

ZERO = Decimal("0")


@dataclass(frozen=True)
class RollingPoint:
    date: date
    value: Decimal | None
    window_days: int
    is_estimate: bool   # True if the window's start doesn't land on a real valuation


def rolling_return(service: HistoryService, window_days: int) -> list[RollingPoint]:
    """Return over a trailing window, evaluated at every date the portfolio
    was actually valued (Phase 3's return_index moving). Between valuations
    the figure would not change, so it is not recomputed for every calendar
    day -- that would manufacture 90 identical points for one real
    observation."""
    rows = sorted(service.portfolio_history(), key=lambda r: r["date"])
    valued = [r for r in rows if r.get("index_as_at") == r["date"]]
    by_date = {r["date"]: r for r in rows}

    out = []
    for row in valued:
        end = date.fromisoformat(row["date"])
        start = end - timedelta(days=window_days)
        start_row = by_date.get(start.isoformat())
        is_estimate = start_row is None or start_row.get("index_as_at") != start_row["date"]
        if start_row is None:
            nearest = min((d for d in by_date if d >= start.isoformat()), default=None)
            start_row = by_date.get(nearest) if nearest else None
        if start_row is None or not start_row["return_index"] or not row["return_index"]:
            out.append(RollingPoint(end, None, window_days, True))
            continue
        value = (Decimal(row["return_index"]) / Decimal(start_row["return_index"])
                 - Decimal(1))
        out.append(RollingPoint(end, value, window_days, is_estimate))
    return out


def rolling_volatility(service: HistoryService, window_quarters: int = 8) -> list[dict]:
    """Rolling volatility over a trailing N-quarter window, built from the
    same quarterly TWRR series risk.py uses -- see docs/analytics.md
    'Why quarterly risk metrics' for why this is the finest honest
    frequency."""
    from src.analytics.risk import _stdev
    from src.history.config import Granularity

    quarters = [(r["period_end"], Decimal(r["twrr"]))
               for r in service.period_summaries(Granularity.QUARTERLY)
               if r["twrr"] is not None]
    out = []
    for i in range(window_quarters, len(quarters) + 1):
        window = quarters[i - window_quarters:i]
        values = [v for _, v in window]
        sd = _stdev(values)
        out.append({
            "as_at": window[-1][0],
            "volatility": str(sd * Decimal(str(4 ** 0.5))) if sd else None,
            "window_quarters": window_quarters,
            "observations": len(values),
            "frequency": "quarterly",
            "annualisation_factor": "2.0",
            # Rolling windows always meet the sample floor by construction
            # (they only start once window_quarters observations exist), but
            # a short window is still a small sample -- flag it explicitly
            # rather than implying the same confidence as the full series.
            "data_quality": "limited" if window_quarters < 12 else "calculated",
        })
    return out


def rolling_income_yield(service: HistoryService, window_days: int = 365) -> list[dict]:
    """Rolling trailing income yield, evaluated at each month-end (finer than
    that would imply daily income precision this data doesn't have)."""
    from src.analytics.income import trailing_income_yield
    from src.history.config import Granularity

    out = []
    for row in service.portfolio_history(granularity=Granularity.MONTHLY):
        when = date.fromisoformat(row["period_end"] if "period_end" in row else row["date"])
        metric = trailing_income_yield(service, as_at=when)
        out.append({"date": when.isoformat(), "yield": str(metric.value)
                    if metric.value is not None else None,
                   "status": metric.data_quality.value})
    return out
