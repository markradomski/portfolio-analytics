"""Performance overview, return methodology, and standard periods (sec 3-5).

Every figure here is read from Phase 2/3, never recalculated. This module
packages those figures into Sharesight-style shapes and is explicit about what
each return methodology means -- the spec is emphatic they are not
interchangeable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analytics.result import DataQuality
from src.history.config import Granularity, ValuationStatus
from src.history.periods import PerformancePeriod, performance_periods
from src.history.service import HistoryService

ZERO = Decimal("0")


@dataclass(frozen=True)
class PerformanceOverview:
    """Sharesight-style period summary (sec 3). Every field traces to a
    portfolio_daily/period_summaries row -- nothing here is computed fresh."""
    period_start: date
    period_end: date
    opening_value: Decimal | None
    closing_value: Decimal | None
    contributions: Decimal
    withdrawals: Decimal
    net_external_flow: Decimal
    investment_gain: Decimal | None
    income: Decimal
    fees: Decimal
    total_return: Decimal | None
    capital_return: Decimal | None
    income_return: Decimal | None
    twrr: Decimal | None
    xirr: Decimal | None
    data_quality: DataQuality


def _quality_of(status: str) -> DataQuality:
    return {
        ValuationStatus.ACTUAL.value: DataQuality.ACTUAL,
        ValuationStatus.CALCULATED.value: DataQuality.CALCULATED,
        ValuationStatus.ESTIMATED.value: DataQuality.ESTIMATED,
        ValuationStatus.UNAVAILABLE.value: DataQuality.UNAVAILABLE,
    }.get(status, DataQuality.UNAVAILABLE)


def _overview_from_row(row: dict) -> PerformanceOverview:
    """Build an overview from one period_summaries row -- the same row Phase 3
    already validated (its own delta/TWRR/XIRR logic is not repeated here)."""
    opening = Decimal(row["opening_value"]) if row["opening_value"] else None
    closing = Decimal(row["closing_value"]) if row["closing_value"] else None
    contributions = Decimal(row["contributions"])
    withdrawals = Decimal(row["withdrawals"])
    net_flow = contributions + withdrawals
    investment_gain = (Decimal(row["investment_gain"])
                       if row["investment_gain"] is not None else None)
    income = Decimal(row["income"])
    fees = Decimal(row["fees"])
    capital = (investment_gain - income + fees) if investment_gain is not None else None

    average_capital = (((opening or ZERO) + (closing or ZERO)) / 2
                       if opening is not None and closing is not None else None)
    denom = average_capital if average_capital and average_capital > ZERO else None

    return PerformanceOverview(
        period_start=date.fromisoformat(row["period_start"]),
        period_end=date.fromisoformat(row["period_end"]),
        opening_value=opening, closing_value=closing,
        contributions=contributions, withdrawals=withdrawals,
        net_external_flow=net_flow, investment_gain=investment_gain,
        income=income, fees=fees,
        total_return=(investment_gain / denom) if investment_gain is not None and denom else None,
        capital_return=(capital / denom) if capital is not None and denom else None,
        income_return=(income / denom) if denom else None,
        twrr=Decimal(row["twrr"]) if row["twrr"] else None,
        xirr=Decimal(row["xirr"]) if row["xirr"] else None,
        data_quality=_quality_of(row["valuation_status"]))


def overview_for_year(service: HistoryService, year: int) -> PerformanceOverview | None:
    """The single calendar-year summary a Sharesight "Performance" tab shows."""
    rows = service.period_summaries(Granularity.YEARLY)
    row = next((r for r in rows if r["period_start"][:4] == str(year)), None)
    return _overview_from_row(row) if row else None


def overview_for_quarter(service: HistoryService, year: int, quarter: int
                         ) -> PerformanceOverview | None:
    rows = service.period_summaries(Granularity.QUARTERLY)
    target_month = 3 * (quarter - 1) + 1
    row = next((r for r in rows
               if r["period_start"][:4] == str(year)
               and int(r["period_start"][5:7]) == target_month), None)
    return _overview_from_row(row) if row else None


def overview_for_month(service: HistoryService, year: int, month: int
                       ) -> PerformanceOverview | None:
    rows = service.period_summaries(Granularity.MONTHLY)
    row = next((r for r in rows if r["period_start"][:7] == f"{year:04d}-{month:02d}"), None)
    return _overview_from_row(row) if row else None


def overview_for_range(service: HistoryService, start: date, end: date
                       ) -> PerformanceOverview:
    """A custom-range overview (sec 5's "Custom range").

    The window is measured between an *opening anchor* on or near ``start`` and
    the last row inside it, using the same Modified Dietz / index-ratio maths
    that :func:`src.history.periods.performance_periods` applies to the standard
    windows -- so ``GET /api/portfolio/performance`` and the matching entry of
    ``GET /api/portfolio/performance/periods`` report consistent figures for an
    identical ``[start, end]`` range.
    """
    from src.engine.returns import modified_dietz, xirr as calc_xirr

    all_rows = {date.fromisoformat(r["date"]): r for r in service.portfolio_history()}
    ordered = sorted(all_rows)
    in_range = [d for d in ordered if start <= d <= end]
    if not in_range:
        return PerformanceOverview(start, end, None, None, ZERO, ZERO, ZERO,
                                   None, ZERO, ZERO, None, None, None, None,
                                   None, DataQuality.UNAVAILABLE)

    # Opening anchor. Taking the row *strictly* before ``start`` with no
    # fallback silently yields a null opening -- and a TWRR measured from a
    # stale carried-forward index -- whenever the day before the window is an
    # unpriced gap. Carry-forward from the previous quarter's valuation expires
    # before the next real valuation lands, so the days immediately before a
    # quarter-end valuation are routinely gaps (e.g. 2023-06-25..29 precede the
    # actual 2023-06-30 valuation). performance_periods() anchors to the
    # nearest date the portfolio was genuinely valued on; mirror that.
    priced = [d for d in ordered if all_rows[d]["total_value"] is not None]
    genuine = [d for d in ordered
               if all_rows[d].get("index_as_at")
               and date.fromisoformat(all_rows[d]["index_as_at"]) == d]
    requested_days = max((end - start).days, 1)
    tolerance = max(7, requested_days // 10)
    before_date = None
    if genuine:
        nearest = min(genuine, key=lambda d: (abs((d - start).days), d))
        if abs((nearest - start).days) <= tolerance:
            before_date = nearest
    if before_date is None:
        before_date = next((d for d in reversed(priced) if d <= start), None)
    if before_date is None:
        before_date = next((d for d in priced if d >= start), None)
    before = all_rows.get(before_date) if before_date else None
    anchor = before_date or start
    last = all_rows[in_range[-1]]

    def delta(field: str) -> Decimal:
        after = Decimal(last[field])
        prior = Decimal(before[field]) if before else ZERO
        return after - prior

    def dec(row, field):
        return Decimal(row[field]) if row and row[field] else None

    opening, closing = dec(before, "total_value"), dec(last, "total_value")
    contributions, withdrawals = delta("cumulative_contributions"), delta("cumulative_withdrawals")
    net_flow = contributions + withdrawals
    income, fees = delta("income"), delta("fees")

    # External flows inside the measured window, dated to the day -- the same
    # series performance_periods() feeds to Modified Dietz for the same window.
    flows: list[tuple[date, Decimal]] = []
    for r in service.contribution_history(Granularity.DAILY):
        when = date.fromisoformat(r["period_end"])
        if not (anchor < when <= end):
            continue
        for amount in (Decimal(r["contributions"]), Decimal(r["withdrawals"])):
            if amount:
                flows.append((when, amount))

    investment_gain = capital = None
    total_return = capital_return = income_return = xirr = None
    if opening is not None and closing is not None:
        period = modified_dietz(opening, closing, flows, anchor, end)
        denom = period.begin_value + period.weighted_flow
        investment_gain = period.gain
        capital = investment_gain - income + fees
        total_return = period.ret
        if denom > ZERO:
            capital_return = capital / denom
            income_return = income / denom
        cash_flows = ([(anchor, -opening)] if opening != ZERO else []) + \
            [(w, -a) for w, a in flows] + [(end, closing)]
        xirr = calc_xirr(cash_flows)

    twrr = None
    idx_before = dec(before, "return_index")
    idx_after = dec(last, "return_index")
    if idx_before and idx_after:
        twrr = idx_after / idx_before - Decimal(1)

    return PerformanceOverview(
        period_start=start, period_end=end, opening_value=opening, closing_value=closing,
        contributions=contributions, withdrawals=withdrawals, net_external_flow=net_flow,
        investment_gain=investment_gain, income=income, fees=fees,
        total_return=total_return, capital_return=capital_return,
        income_return=income_return,
        twrr=twrr, xirr=xirr, data_quality=_quality_of(last["valuation_status"]))


def return_methodology_notes() -> dict[str, str]:
    """The spec's own definitions (sec 4), returned as data so a UI can show
    them next to the figures rather than the definitions living only in a
    docstring nobody sees."""
    return {
        "absolute_return": "closing_value - opening_value - net_external_contributions",
        "capital_return": "return attributable to market value change, excluding income",
        "income_return": "return attributable to dividends, distributions and interest",
        "total_return": "capital_return + income_return",
        "twrr": "time-weighted: chained sub-period returns, neutralises flow timing",
        "xirr": "money-weighted: the rate at which dated cash flows net to zero",
    }


def standard_periods(service: HistoryService, as_at: date | None = None
                     ) -> list[PerformancePeriod]:
    """Every window in sec 5 (1D through 10Y, YTD, INCEPTION). Delegates
    entirely to Phase 3's tested function -- see history/periods.py
    STANDARD_PERIODS, which now includes 1W and 10Y alongside what Phase 3
    already needed."""
    from src.history.generator import DailyRow

    def dec(v):
        return None if v in (None, "") else Decimal(v)

    def dt(v):
        return None if v in (None, "") else date.fromisoformat(v)

    rows = [DailyRow(
        date=dt(r["date"]), total_value=dec(r["total_value"]),
        securities_value=dec(r["securities_value"]), cash=dec(r["cash"]) or ZERO,
        cost_basis=dec(r["cost_basis"]) or ZERO,
        invested_capital=dec(r["invested_capital"]) or ZERO,
        realised_gain=dec(r["realised_gain"]) or ZERO,
        unrealised_gain=dec(r["unrealised_gain"]),
        dividends=ZERO, distributions=ZERO,
        income=dec(r["income"]) or ZERO, fees=dec(r["fees"]) or ZERO,
        cumulative_contributions=dec(r["cumulative_contributions"]) or ZERO,
        cumulative_withdrawals=dec(r["cumulative_withdrawals"]) or ZERO,
        high_water_mark=dec(r["high_water_mark"]) or ZERO,
        drawdown_value=dec(r["drawdown_value"]), drawdown_pct=dec(r["drawdown_pct"]),
        return_index=dec(r["return_index"]), index_as_at=dt(r["index_as_at"]),
        return_high_water=dec(r["return_high_water"]),
        return_drawdown_pct=dec(r["return_drawdown_pct"]),
        valuation_status=ValuationStatus(r["valuation_status"]),
        valuation_source=r.get("valuation_source") or "VANGUARD_SECURITY_PRICE",
        price_as_at=dt(r["price_as_at"]), source_count=r["source_count"] or 0,
    ) for r in service.portfolio_history()]

    flows = []
    for row in service.contribution_history(Granularity.DAILY):
        when = date.fromisoformat(row["period_end"])
        if Decimal(row["contributions"]):
            flows.append((when, Decimal(row["contributions"])))
        if Decimal(row["withdrawals"]):
            flows.append((when, Decimal(row["withdrawals"])))

    return performance_periods(rows, flows, as_at)


# --- TWRR methodology metadata (hardening sec 2) -----------------------------

def twrr_methodology_metadata(service: HistoryService) -> dict:
    """Describes *how* TWRR was computed, not just its value.

    True TWRR revalues the portfolio at every external cash flow. This data
    source cannot do that -- valuations exist only on the dates Vanguard
    priced the portfolio (quarterly), while cash flows are dated exactly (to
    the day) from the transaction ledger. The engine therefore chains
    Modified Dietz returns between consecutive real valuations, weighting
    each flow inside that window by its exact date. That is a genuine,
    documented method (Phase 2's returns.py), not an approximation error --
    but it is not the same claim as true TWRR, and must not be presented as
    such without saying so.
    """
    dates = sorted(date.fromisoformat(r["date"]) for r in service.portfolio_history())
    valuation_dates = sorted({date.fromisoformat(r["date"]) for r in service.portfolio_history()
                              if service.portfolio_value(date.fromisoformat(r["date"]))
                              and service.portfolio_value(date.fromisoformat(r["date"]))["valuation_status"] == "actual"})
    n = len(valuation_dates)

    return {
        "twrr_methodology": "SUBPERIOD_LINKED",
        "twrr_methodology_note": (
            "Chained Modified Dietz between consecutive real valuations "
            "(period_summaries/performance_periods sub-periods). Not true "
            "TWRR, which would revalue at every cash flow date -- this data "
            "source only supports revaluation at the dates Vanguard itself "
            "priced the portfolio."),
        "cash_flow_adjustment_method": "EXACT_DATED",
        "cash_flow_adjustment_note": (
            "Each external flow is weighted by its exact date within the "
            "sub-period it falls in (Modified Dietz), even though the "
            "valuation bracketing that sub-period is not exact to that date."),
        "cash_flow_observation_quality": (
            "LIMITED" if n < 12 else "SUFFICIENT"),
        "valuation_observation_count": n,
    }
