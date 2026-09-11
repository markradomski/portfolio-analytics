"""Human-readable summary of the Phase 4 analytics layer."""

from __future__ import annotations

from decimal import Decimal

from src.analytics.result import DataQuality
from src.analytics.service import AnalyticsService

_LINE = "-" * 78


def _pct(value) -> str:
    return "     n/a" if value in (None, "") else f"{Decimal(str(value)) * 100:>7.2f}%"


def _money(value) -> str:
    return "         n/a" if value in (None, "") else f"{Decimal(str(value)):>12,.2f}"


def summary(service: AnalyticsService, year: int | None = None) -> str:
    dates = sorted(r["date"] for r in service.history.portfolio_history())
    target_year = year or (int(dates[-1][:4]) if dates else None)
    out = ["Portfolio analytics", _LINE]

    if target_year:
        overview = service.getPerformanceForYear(target_year)
        if overview:
            out += [
                f"{target_year} performance overview",
                f"  Opening value       {_money(overview.opening_value)}",
                f"  Contributions       {_money(overview.contributions)}",
                f"  Withdrawals         {_money(overview.withdrawals)}",
                f"  Investment gain     {_money(overview.investment_gain)}",
                f"  Income              {_money(overview.income)}",
                f"  Fees                {_money(overview.fees)}",
                f"  Closing value       {_money(overview.closing_value)}",
                "",
                f"  Total return        {_pct(overview.total_return)}",
                f"    capital           {_pct(overview.capital_return)}",
                f"    income            {_pct(overview.income_return)}",
                f"  TWRR                {_pct(overview.twrr)}",
                f"  XIRR                {_pct(overview.xirr)}",
                f"  Data quality        {overview.data_quality.value}",
                "", _LINE,
            ]

    contributions = service.getContributionSummary()
    out += [
        "Lifetime contributions vs earnings",
        f"  Total contributed   {_money(contributions.total_contributed)}",
        f"  Total withdrawn     {_money(contributions.total_withdrawn)}",
        f"  Net contributed     {_money(contributions.net_contributed)}",
        f"  Investment growth   {_money(contributions.investment_growth)}",
        f"  Income received     {_money(contributions.income_received)}",
        f"  Current value       {_money(contributions.current_value)}",
        "", _LINE,
    ]

    out.append("Standard periods")
    for period in service.getReturns():
        if period.status.value == "unavailable":
            out.append(f"  {period.label:<10} n/a    {period.note}")
        else:
            out.append(f"  {period.label:<10} TWRR {_pct(period.twrr)}"
                       f"   XIRR {_pct(period.xirr)}")
    out += ["", _LINE]

    out.append("Risk metrics")
    risk = service.getRiskMetrics()
    for name, metric in risk.items():
        if metric.data_quality is DataQuality.UNAVAILABLE:
            out.append(f"  {name:<16} n/a    {metric.note}")
        else:
            out.append(f"  {name:<16} {_pct(metric.value) if 'volatility' in name else metric.value}"
                       f"  [{metric.frequency}]")
    drawdown = service.getDrawdownAnalytics()
    out.append(f"  max_drawdown      {_pct(drawdown.maximum_drawdown_pct)}"
               f"  ({drawdown.episode_count} episodes)")
    out += ["", _LINE]

    out.append("Fees")
    for row in service.getFeesByYear():
        out.append(f"  {row['year']}  account {row['account_fees']:>7}"
                   f"  brokerage {row['brokerage']:>7}  total {row['total']:>7}")
    out += ["", _LINE]

    out.append("Best / worst")
    best_worst = service.getBestWorstPeriods()
    for key, periods in best_worst.items():
        if isinstance(periods, str):
            out.append(f"  {key:<6} n/a    {periods}")
            continue
        for period in periods:
            out.append(f"  {period.label:<12} {period.period_start}..{period.period_end}"
                       f"  {_pct(period.return_pct)}")

    return "\n".join(out)
