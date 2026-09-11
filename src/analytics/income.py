"""Income analytics, yield and growth (sec 10-12).

Reads Phase 3's income_daily series exclusively. Yield definitions state their
own denominator explicitly, per the spec's insistence that income/current_value
and income/average_value must never be silently interchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from src.analytics.config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from src.analytics.result import DataQuality, Metric, unavailable
from src.history.config import Granularity
from src.history.service import HistoryService

ZERO = Decimal("0")


def income_by(service: HistoryService, granularity: Granularity = Granularity.YEARLY,
             by_security: bool = False) -> list[dict]:
    """Thin pass-through to Phase 3 -- income by year/month/security is
    already computed there; sec 10 just asks it be exposed at this layer too."""
    return service.income_history(granularity, by_security=by_security)


def income_by_asset_class(service: HistoryService,
                          granularity: Granularity = Granularity.YEARLY) -> list[dict]:
    """Income doesn't carry an asset_class column directly (it's a holding
    attribute), so this joins income_daily to holding_daily's classification
    via the security code on the nearest prior date."""
    from collections import defaultdict

    by_sec = service.income_history(granularity, by_security=True)
    classes = {r["code"]: r["asset_class"] for r in service.repo.rows(
        "SELECT DISTINCT h.asset_class, s.code FROM holding_daily h"
        " JOIN securities s USING (security_id)")}

    buckets: dict[tuple, dict] = defaultdict(lambda: defaultdict(Decimal))
    for row in by_sec:
        asset_class = classes.get(row["code"], "unknown")
        key = (row["period_end"], asset_class)
        for field in ("gross_income", "franking_credits", "tax_withheld", "net_income"):
            buckets[key][field] += Decimal(row.get(field) or 0)

    return [{"period_end": k[0], "asset_class": k[1],
            **{f: str(v) for f, v in vals.items()}}
            for k, vals in sorted(buckets.items())]


def trailing_income_yield(service: HistoryService, as_at: date | None = None,
                          config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG) -> Metric:
    """trailing_12m_income / average_portfolio_value over the same window.
    The denominator is explicit and fixed: average value, never current value
    alone (sec 11's own example)."""
    dates = sorted(date.fromisoformat(r["date"]) for r in service.portfolio_history())
    if not dates:
        return unavailable("trailing_income_yield",
                           "trailing 12m income / average portfolio value",
                           "no portfolio history available")
    end = as_at or dates[-1]
    start = end - timedelta(days=30 * config.trailing_income_months)

    rows = service.portfolio_history(start, end)
    valued = [Decimal(r["total_value"]) for r in rows if r["total_value"]]
    if not valued:
        return unavailable("trailing_income_yield",
                           "trailing 12m income / average portfolio value",
                           "no valued days in the trailing window",
                           period_start=start, period_end=end)
    average_value = sum(valued, ZERO) / Decimal(len(valued))

    income_rows = [r for r in service.income_history(Granularity.DAILY)
                   if start < date.fromisoformat(r["period_end"]) <= end]
    trailing_income = sum((Decimal(r["gross_income"]) for r in income_rows), ZERO)

    if average_value <= ZERO:
        return unavailable("trailing_income_yield",
                           "trailing 12m income / average portfolio value",
                           "average portfolio value was zero or negative",
                           period_start=start, period_end=end)

    quality = (DataQuality.ACTUAL if len(valued) == len(rows) and rows
              else DataQuality.ESTIMATED)
    return Metric(
        name="trailing_income_yield", value=trailing_income / average_value,
        methodology="trailing_12m_income / average_portfolio_value_over_the_same_window",
        data_quality=quality, period_start=start, period_end=end,
        currency=config.currency,
        note=f"trailing income {trailing_income}, average value {average_value:.2f}"
             f" over {len(valued)} valued days")


def forward_income_yield(service: HistoryService, as_at: date | None = None,
                         config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG) -> Metric:
    """Forward yield needs a projected future distribution rate -- this data
    source has no distribution-rate forecast (no DRP schedule, no analyst
    estimate), so it is honestly UNAVAILABLE rather than extrapolated from the
    trailing figure and presented as something it isn't."""
    return unavailable(
        "forward_income_yield", "projected next-12m income / current value",
        "no forward distribution schedule is available from Vanguard statement"
        " data; only trailing yield can be computed")


def security_income_yield(service: HistoryService, code: str,
                          as_at: date | None = None,
                          config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG) -> Metric:
    """Trailing income yield for one holding: its own trailing income divided
    by its own average market value, same window and methodology as the
    portfolio-level figure."""
    dates = sorted(date.fromisoformat(r["date"]) for r in service.portfolio_history())
    if not dates:
        return unavailable(f"income_yield[{code}]", "trailing 12m income / average value",
                           "no portfolio history available")
    end = as_at or dates[-1]
    start = end - timedelta(days=30 * config.trailing_income_months)

    holdings = service.holdings_history(start=start, end=end)
    values = [Decimal(h["market_value"]) for h in holdings
             if h["code"] == code and h["market_value"]]
    if not values:
        return unavailable(f"income_yield[{code}]", "trailing 12m income / average value",
                           "no valued holding days for this security in the window",
                           period_start=start, period_end=end)
    average_value = sum(values, ZERO) / Decimal(len(values))

    income_rows = [r for r in service.income_history(Granularity.DAILY, by_security=True)
                   if r["code"] == code
                   and start < date.fromisoformat(r["period_end"]) <= end]
    trailing_income = sum((Decimal(r["gross_income"]) for r in income_rows), ZERO)

    if average_value <= ZERO:
        return unavailable(f"income_yield[{code}]", "trailing 12m income / average value",
                           "average holding value was zero or negative")

    return Metric(
        name=f"income_yield[{code}]", value=trailing_income / average_value,
        methodology="trailing_12m_income / average_holding_value_over_the_same_window",
        data_quality=DataQuality.ESTIMATED, period_start=start, period_end=end,
        currency=config.currency)


def income_growth(service: HistoryService) -> list[dict]:
    """Year-over-year income growth (sec 12). Decomposing growth into
    "larger portfolio" vs "higher distributions" vs "additional contributions"
    vs "changed holdings" would need a counterfactual (what income would this
    year's holdings have paid at last year's rate) that Vanguard's statements
    cannot support -- reported honestly as unavailable per security rather than
    approximated."""
    yearly = income_by(service, Granularity.YEARLY)
    out = []
    previous = None
    for row in yearly:
        gross = Decimal(row["gross_income"])
        growth = None
        if previous is not None and previous > ZERO:
            growth = (gross - previous) / previous
        out.append({
            "year": row["period_end"][:4], "gross_income": row["gross_income"],
            "growth_pct": str(growth) if growth is not None else None,
            "decomposition": "unavailable -- would require a counterfactual"
                             " holding-and-rate breakdown the source data cannot support",
        })
        previous = gross
    return out
