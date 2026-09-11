"""Calendar-period summaries, best/worst periods, and milestone analytics
(sec 30-32).

Calendar summaries are a thin re-shaping of Phase 3's period_summaries.
Best/worst periods are found on the flow-neutral return series (never on raw
portfolio value, which would let a large withdrawal masquerade as "worst day"
-- exactly the trap Phase 3's two-drawdown-series design exists to avoid).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from src.history.config import Granularity
from src.history.service import HistoryService

ZERO = Decimal("0")


def calendar_performance(service: HistoryService,
                         granularity: Granularity = Granularity.YEARLY) -> list[dict]:
    """Sec 30's table: return, income, contribution per calendar period."""
    return [{
        "period": row["period_start"][:4] if granularity is Granularity.YEARLY
        else row["period_start"][:7],
        "twrr": row["twrr"], "xirr": row["xirr"],
        "income": row["income"], "contributions": row["contributions"],
        "withdrawals": row["withdrawals"],
        "closing_value": row["closing_value"],
        "valuation_status": row["valuation_status"],
    } for row in service.period_summaries(granularity)]


@dataclass(frozen=True)
class ExtremePeriod:
    label: str          # "best_day", "worst_month", etc.
    period_start: date
    period_end: date
    return_pct: Decimal
    absolute_change: Decimal | None
    opening_value: Decimal | None
    closing_value: Decimal | None


def _best_worst(candidates: list[tuple[date, date, Decimal, Decimal | None,
                                       Decimal | None, Decimal | None]],
                best_label: str, worst_label: str) -> list[ExtremePeriod]:
    if not candidates:
        return []
    best = max(candidates, key=lambda c: c[2])
    worst = min(candidates, key=lambda c: c[2])
    return [ExtremePeriod(best_label, *best), ExtremePeriod(worst_label, *worst)]


# A "daily" observation only means something if consecutive valuations are
# genuinely about a day apart. In this data they are ~91 days apart
# (quarterly statements); labelling that gap "best_day" would misrepresent a
# quarter's movement as a single day's, exactly the trap the rest of this
# codebase exists to avoid.
_MAX_DAILY_GAP = 3


def best_worst_periods(service: HistoryService) -> dict[str, list[ExtremePeriod] | str]:
    """Best/worst day, month and year, measured on the flow-neutral return
    index -- external cash flows are structurally excluded, since they were
    never part of this series to begin with (sec 31's own requirement)."""
    rows = sorted(service.portfolio_history(), key=lambda r: r["date"])
    valued = [r for r in rows if r.get("index_as_at") == r["date"]]

    daily = []
    finest_gap = None
    for prev, curr in zip(valued, valued[1:]):
        if not prev["return_index"] or not curr["return_index"]:
            continue
        gap = (date.fromisoformat(curr["date"]) - date.fromisoformat(prev["date"])).days
        finest_gap = gap if finest_gap is None else min(finest_gap, gap)
        ret = Decimal(curr["return_index"]) / Decimal(prev["return_index"]) - Decimal(1)
        daily.append((date.fromisoformat(prev["date"]), date.fromisoformat(curr["date"]),
                     ret, None,
                     Decimal(prev["total_value"]) if prev["total_value"] else None,
                     Decimal(curr["total_value"]) if curr["total_value"] else None))

    if finest_gap is not None and finest_gap > _MAX_DAILY_GAP:
        out: dict = {"day": f"unavailable -- consecutive valuations are"
                            f" {finest_gap} days apart at the closest, not"
                            f" daily; a 'best day' figure would misrepresent"
                            f" that gap as a single day's movement"}
    else:
        out = {"day": _best_worst(daily, "best_day", "worst_day")}

    for granularity, key in ((Granularity.MONTHLY, "month"), (Granularity.YEARLY, "year")):
        periods = []
        summaries = service.period_summaries(granularity)
        for row in summaries:
            if row["twrr"] is None:
                continue
            opening = Decimal(row["opening_value"]) if row["opening_value"] else None
            closing = Decimal(row["closing_value"]) if row["closing_value"] else None
            periods.append((
                date.fromisoformat(row["period_start"]), date.fromisoformat(row["period_end"]),
                Decimal(row["twrr"]),
                (closing - opening) if opening is not None and closing is not None else None,
                opening, closing))
        out[key] = _best_worst(periods, f"best_{key}", f"worst_{key}")
    return out


def milestone_context(service: HistoryService) -> list[dict]:
    """Extends Phase 3's milestones with the portfolio state at that date
    (sec 32) -- so a milestone can distinguish "reached $500k" (value) from
    "earned $500k" (cumulative investment gain), per the spec's own example."""
    milestones = service.milestones()
    by_date = {r["date"]: r for r in service.portfolio_history()}
    out = []
    for milestone in milestones:
        row = by_date.get(milestone["date"])
        out.append({
            **milestone,
            "portfolio_value": row["total_value"] if row else None,
            "cumulative_contributions": row["cumulative_contributions"] if row else None,
            "cumulative_investment_gain": (
                str(Decimal(row["total_value"]) - Decimal(row["cumulative_contributions"])
                    - Decimal(row["cumulative_withdrawals"]))
                if row and row["total_value"] else None),
        })
    return out
