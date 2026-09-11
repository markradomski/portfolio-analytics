"""Human-readable and machine-readable renderings of engine output."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from src.engine.reconciliation import Check, summarise
from src.engine.service import PortfolioService

_LINE = "-" * 68


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def to_json(payload) -> str:
    return json.dumps(_plain(payload), indent=2)


def _pct(value: Decimal | None) -> str:
    return "     n/a" if value is None else f"{value * 100:>7.2f}%"


def summary(service: PortfolioService) -> str:
    performance = service.performance()
    decomposition = performance.decomposition
    state = service.state()
    attribution = service.attribution()
    checks = service.reconcile()
    counts = summarise(checks)

    out = [
        "Portfolio summary",
        f"{performance.start} to {performance.end}"
        f"    {len(performance.periods)} measured sub-periods",
        _LINE,
        f"Closing value          {state.total_value:>14,.2f}"
        f"   ({state.value_quality.value})",
        f"  securities           {state.securities_value:>14,.2f}",
        f"  cash                 {state.cash:>14,.2f}",
        "",
        f"Capital growth         {decomposition.capital_growth:>14,.2f}",
        f"Income                 {decomposition.income:>14,.2f}",
        f"Fees                   {-decomposition.fees:>14,.2f}",
        f"Total gain             {decomposition.total_gain:>14,.2f}",
        f"Average capital        {decomposition.average_capital:>14,.2f}",
        "",
        f"Total return           {_pct(decomposition.total_return_pct)}",
        f"  capital             {_pct(decomposition.capital_growth_pct)}",
        f"  income              {_pct(decomposition.income_return_pct)}",
        "",
        f"TWRR cumulative        {_pct(performance.twrr)}"
        "   (investment performance, ignores flow timing)",
        f"TWRR annualised        {_pct(performance.twrr_annualised)}",
        f"XIRR                   {_pct(performance.xirr)}"
        "   (investor experience, includes flow timing)",
        _LINE,
        "Contribution to return",
    ]
    for contribution in attribution.ranked():
        out.append(
            f"  {contribution.code:<6} {contribution.profit:>12,.2f}"
            f"  {_pct(contribution.contribution_pct(attribution.average_capital))}")
    out += [
        f"  {'TOTAL':<6} {attribution.total_profit:>12,.2f}  {_pct(attribution.total_pct)}",
        _LINE,
        f"Reconciliation against reported figures:"
        f" {counts['passed']}/{counts['total']} passed,"
        f" {counts['failed']} failed, {counts['skipped']} skipped",
    ]
    for check in [c for c in checks if c.status == "FAIL"][:20]:
        out.append(f"  FAIL {check.when} {check.subject:<18}"
                   f" reported {check.expected} calculated {check.calculated}"
                   f" diff {check.difference}")
    return "\n".join(out)


def reconciliation_report(checks: list[Check]) -> str:
    counts = summarise(checks)
    out = ["Reconciliation: calculated vs reported", _LINE,
           f"{counts['passed']} passed, {counts['failed']} failed,"
           f" {counts['skipped']} skipped, {counts['total']} total", ""]
    for check in checks:
        difference = "" if check.difference is None else f"{check.difference:>12,.2f}"
        out.append(f"  {check.status:<4} {check.when} {check.subject:<18}"
                   f" reported {str(check.expected):>14}"
                   f" calculated {str(check.calculated):>14} {difference}")
    return "\n".join(out)
