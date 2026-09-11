"""Calendar summaries and standard-period performance.

Both are derived from the daily series rather than recalculated from the
ledger, so a figure shown for a month always agrees with the days inside it.

Return figures reuse the Phase 2 functions. Nothing here reimplements a
financial calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from src.engine.returns import modified_dietz, xirr
from src.history.config import Granularity, ValuationStatus
from src.history.generator import DailyRow
from src.ids import make_id

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True)
class PeriodSummary:
    period_id: str
    granularity: Granularity
    period_start: date
    period_end: date
    opening_value: Decimal | None
    closing_value: Decimal | None
    contributions: Decimal
    withdrawals: Decimal
    net_contributions: Decimal
    income: Decimal
    fees: Decimal
    realised_gain: Decimal
    investment_gain: Decimal | None
    twrr: Decimal | None
    xirr: Decimal | None
    valuation_status: ValuationStatus


@dataclass(frozen=True)
class PerformancePeriod:
    label: str
    as_at: date
    start_date: date | None
    end_date: date | None
    total_return: Decimal | None
    capital_return: Decimal | None
    income_return: Decimal | None
    twrr: Decimal | None
    xirr: Decimal | None
    status: ValuationStatus
    note: str | None = None


def _bucket(when: date, granularity: Granularity) -> tuple[date, date]:
    if granularity is Granularity.YEARLY:
        return date(when.year, 1, 1), date(when.year, 12, 31)
    if granularity is Granularity.QUARTERLY:
        first_month = 3 * ((when.month - 1) // 3) + 1
        start = date(when.year, first_month, 1)
        end_month = first_month + 2
        end = date(when.year + (end_month // 12), (end_month % 12) + 1, 1) - timedelta(days=1)
        return start, end
    start = date(when.year, when.month, 1)
    end = date(when.year + (when.month // 12), (when.month % 12) + 1, 1) - timedelta(days=1)
    return start, end


def summarise(rows: list[DailyRow], granularity: Granularity,
              external_flows: list[tuple[date, Decimal]]) -> list[PeriodSummary]:
    """One summary per calendar period covered by the daily series."""
    if not rows:
        return []
    by_date = {r.date: r for r in rows}
    ordered = sorted(by_date)

    buckets: dict[tuple[date, date], list[DailyRow]] = {}
    for when in ordered:
        buckets.setdefault(_bucket(when, granularity), []).append(by_date[when])

    out: list[PeriodSummary] = []
    for (start, end), days in sorted(buckets.items()):
        first, last = days[0], days[-1]
        # The state carried into the period is the most recent row before it
        # opens. Looking only at the immediately preceding day would work for a
        # contiguous daily series and silently return nothing for any other.
        earlier = [d for d in ordered if d < start]
        before = by_date[max(earlier)] if earlier else None

        opening = before.total_value if before else ZERO
        closing = last.total_value

        def delta(attribute: str) -> Decimal:
            after = getattr(last, attribute)
            prior = getattr(before, attribute) if before else ZERO
            return after - prior

        contributions = delta("cumulative_contributions")
        withdrawals = delta("cumulative_withdrawals")
        net = contributions + withdrawals
        investment_gain = (closing - opening - net
                           if closing is not None and opening is not None else None)

        opening_index = before.return_index if before else first.return_index
        twrr = (last.return_index / opening_index - ONE
                if last.return_index is not None and opening_index
                else None)

        flows = [(w, -a) for w, a in external_flows if first.date <= w <= last.date]
        money_weighted = None
        if opening is not None and closing is not None:
            candidate = [(first.date, -opening)] if opening != ZERO else []
            candidate += flows + [(last.date, closing)]
            money_weighted = xirr(candidate)

        status = (ValuationStatus.ACTUAL
                  if last.valuation_status is ValuationStatus.ACTUAL
                  else last.valuation_status)

        out.append(PeriodSummary(
            period_id=make_id("PS", granularity.value, start, end),
            granularity=granularity, period_start=start, period_end=end,
            opening_value=opening, closing_value=closing,
            contributions=contributions, withdrawals=withdrawals,
            net_contributions=net, income=delta("income"), fees=delta("fees"),
            realised_gain=delta("realised_gain"), investment_gain=investment_gain,
            twrr=twrr, xirr=money_weighted, valuation_status=status))
    return out


# Offsets for the standard reporting windows. YTD and inception are special.
STANDARD_PERIODS: list[tuple[str, int | None]] = [
    ("1D", 1), ("1W", 7), ("1M", 30), ("3M", 91), ("6M", 182),
    ("YTD", None), ("1Y", 365), ("3Y", 1095), ("5Y", 1826), ("10Y", 3652),
    ("INCEPTION", None),
]


def performance_periods(rows: list[DailyRow],
                        external_flows: list[tuple[date, Decimal]],
                        as_at: date | None = None) -> list[PerformancePeriod]:
    """Returns over the standard windows, computed only where measurable."""
    if not rows:
        return []
    by_date = {r.date: r for r in rows}
    ordered = sorted(by_date)
    as_at = as_at or ordered[-1]
    end_row = by_date.get(as_at)
    if end_row is None:
        return []

    # Dates the portfolio was genuinely valued on, as opposed to carried forward.
    valuation_dates = [r.date for r in rows if r.index_as_at == r.date]

    out: list[PerformancePeriod] = []
    for label, days in STANDARD_PERIODS:
        if label == "INCEPTION":
            start = ordered[0]
        elif label == "YTD":
            start = max(date(as_at.year, 1, 1), ordered[0])
        else:
            start = as_at - timedelta(days=days)

        requested_days = max((as_at - start).days, 1)
        if start < ordered[0]:
            out.append(PerformancePeriod(
                label, as_at, None, None, None, None, None, None, None,
                ValuationStatus.UNAVAILABLE,
                "period begins before the portfolio existed"))
            continue

        start_row = by_date.get(start) or by_date[min(
            (d for d in ordered if d >= start), default=ordered[0])]

        # A window whose start falls between two valuations measures from the
        # earlier one, so missing a quarter boundary by a day would silently
        # stretch the measurement by a whole quarter. Snap to the nearest date
        # the portfolio was actually valued on, within a tolerance
        # proportional to the window, and report where it actually measured.
        tolerance = max(7, requested_days // 10)
        if label != "INCEPTION" and valuation_dates:
            nearest = min(valuation_dates, key=lambda d: (abs((d - start).days), d))
            if abs((nearest - start).days) <= tolerance and nearest in by_date:
                start_row = by_date[nearest]

        if label == "INCEPTION":
            first_priced = next((r for r in rows if r.return_index is not None), None)
            if first_priced is not None:
                start_row = first_priced

        # The portfolio can only be valued on roughly 23 dates across six
        # years, so the movement between two index values covers the interval
        # between those valuations -- not the window that was asked for.
        # Reporting a quarter of movement as a one-day return would be an
        # artefact of carrying a stale value forward.
        effective_start = start_row.index_as_at or start_row.price_as_at or start_row.date
        effective_end = end_row.index_as_at or end_row.price_as_at or as_at

        if effective_start == effective_end:
            out.append(PerformancePeriod(
                label, as_at, start_row.date, as_at, None, None, None, None, None,
                ValuationStatus.UNAVAILABLE,
                f"both ends valued on {effective_start};"
                " no market movement observable"))
            continue

        effective_days = (effective_end - effective_start).days
        if effective_days > requested_days + tolerance:
            out.append(PerformancePeriod(
                label, as_at, start_row.date, as_at, None, None, None, None, None,
                ValuationStatus.UNAVAILABLE,
                f"nearest valuations span {effective_days} days"
                f" ({effective_start} to {effective_end}), too far outside the"
                f" {requested_days}-day window to report"))
            continue

        opening, closing = start_row.total_value, end_row.total_value
        if opening is None or closing is None:
            out.append(PerformancePeriod(
                label, as_at, start_row.date, as_at, None, None, None, None, None,
                ValuationStatus.UNAVAILABLE, "portfolio could not be valued"))
            continue

        flows = [(w, a) for w, a in external_flows
                 if start_row.date < w <= as_at]
        period = modified_dietz(opening, closing, flows, start_row.date, as_at)
        denominator = period.begin_value + period.weighted_flow

        income = end_row.income - start_row.income
        fees = end_row.fees - start_row.fees
        capital = period.gain - income + fees

        twrr = (end_row.return_index / start_row.return_index - ONE
                if end_row.return_index and start_row.return_index else None)
        money_weighted = xirr(
            ([(start_row.date, -opening)] if opening != ZERO else [])
            + [(w, -a) for w, a in flows] + [(as_at, closing)])

        exact = (effective_start == start_row.date and effective_end == as_at)
        out.append(PerformancePeriod(
            label=label, as_at=as_at, start_date=start_row.date, end_date=as_at,
            total_return=period.ret,
            capital_return=(capital / denominator) if denominator > ZERO else None,
            income_return=(income / denominator) if denominator > ZERO else None,
            twrr=twrr, xirr=money_weighted,
            status=(end_row.valuation_status if exact else ValuationStatus.ESTIMATED),
            note=None if exact else
            f"measured {effective_start} to {effective_end} from available prices"))
    return out
