"""Human-readable summary of the historical dataset."""

from __future__ import annotations

from decimal import Decimal

from src.database.repository import Repository
from src.history.config import Granularity
from src.history.service import HistoryService

_LINE = "-" * 78


def _pct(value) -> str:
    return "     n/a" if value in (None, "") else f"{Decimal(value) * 100:>7.2f}%"


def _money(value) -> str:
    return "         n/a" if value in (None, "") else f"{Decimal(value):>12,.0f}"


def summary(repo: Repository) -> str:
    service = HistoryService(repo)
    quality = service.data_quality()
    reconciliation = service.reconciliation()
    passed = sum(1 for r in reconciliation if r["status"] == "PASS")

    out = ["Portfolio history", _LINE,
           f"Days covered: {quality['days']}    "
           f"priced on {quality['priced_dates']} distinct dates"]
    statuses = quality["by_status"]
    out.append("  " + "   ".join(f"{k}: {v}" for k, v in sorted(statuses.items())))
    out.append(f"  days with no computable value: {quality['days_without_value']}"
               " (reported as gaps, not zeros)")
    out.append("")
    out.append(f"Reconciliation against reported values:"
               f" {passed}/{len(reconciliation)} passed")
    out.append(_LINE)

    out.append("Year   Opening      Contrib    Withdrawn      Income"
               "         Gain      Closing     TWRR      XIRR")
    for row in service.period_summaries(Granularity.YEARLY):
        out.append(
            f"{row['period_start'][:4]}  {_money(row['opening_value'])}"
            f" {_money(row['contributions'])} {_money(row['withdrawals'])}"
            f" {_money(row['income'])} {_money(row['investment_gain'])}"
            f" {_money(row['closing_value'])} {_pct(row['twrr'])} {_pct(row['xirr'])}")

    out += ["", _LINE, "Standard periods"]
    for row in service.performance_history():
        if row["status"] == "unavailable":
            out.append(f"  {row['label']:<10} n/a    {row['note']}")
        else:
            out.append(f"  {row['label']:<10} TWRR {_pct(row['twrr'])}"
                       f"   XIRR {_pct(row['xirr'])}   [{row['status']}]")

    out += ["", _LINE, "Investment drawdowns (flow-neutral)"]
    for row in service.drawdown_history():
        recovery = row["recovery_date"] or "not recovered"
        days = f" in {row['recovery_days']} days" if row["recovery_days"] else ""
        out.append(f"  {row['peak_date']} -> {row['trough_date']}"
                   f"  {_pct(row['drawdown_pct'])}   recovered {recovery}{days}")

    out += ["", _LINE, "Milestones"]
    for row in service.milestones():
        out.append(f"  {row['date']}  {row['description']}")

    return "\n".join(out)
