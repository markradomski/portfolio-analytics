"""Portfolio efficiency metrics, fee analytics, and tax analytics (sec 33-35).

Every ratio here names its own formula explicitly (sec 33's own instruction:
"avoid ambiguous score metrics without a documented methodology"). Tax
analytics reports figures only -- franking credits, withheld tax, realised
gains -- and makes no recommendation; this is not a tax advice tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analytics.result import DataQuality, Metric, unavailable
from src.database.repository import Repository
from src.history.config import Granularity
from src.history.service import HistoryService

ZERO = Decimal("0")


@dataclass(frozen=True)
class EfficiencyMetrics:
    """Sec 33. Every field states its own formula in its name -- none of
    these are "return" methodologies, and none should be read as one."""
    income_per_dollar_invested: Decimal | None       # trailing_income / net_contributions
    gain_per_dollar_contributed: Decimal | None       # investment_gain / net_contributions
    fees_pct_of_portfolio: Decimal | None             # trailing_fees / average_value
    income_pct_of_total_return: Decimal | None        # income_gain / (income_gain + capital_gain)


def efficiency_metrics(service: HistoryService, start: date, end: date) -> EfficiencyMetrics:
    from src.analytics.attribution import growth_decomposition
    from src.engine.ledger import Ledger
    from src.engine.prices import SnapshotPriceSource
    from src.engine.state import StateEngine
    from src.database.repository import Repository as _Repo

    repo = service.repo
    ledger = Ledger.from_repository(repo)
    from src.engine.cash import opening_cash_for
    state_engine = StateEngine(SnapshotPriceSource.from_repository(repo),
                               opening_cash=opening_cash_for(repo))
    decomposition = growth_decomposition(state_engine, ledger, start, end)

    contribution_rows = service.contribution_history(Granularity.DAILY)
    net_contributed = sum(
        (Decimal(r["net_contributions"]) for r in contribution_rows
         if start < date.fromisoformat(r["period_end"]) <= end), ZERO)

    income_total = decomposition.dividends + decomposition.distributions + decomposition.interest
    total_fees = decomposition.fees + decomposition.trade_costs

    rows = service.portfolio_history(start, end)
    valued = [Decimal(r["total_value"]) for r in rows if r["total_value"]]
    average_value = (sum(valued, ZERO) / Decimal(len(valued))) if valued else None

    income_gain = income_total
    capital_gain = decomposition.capital_gains
    total_gain = income_gain + capital_gain

    return EfficiencyMetrics(
        income_per_dollar_invested=(income_total / net_contributed)
        if net_contributed > ZERO else None,
        gain_per_dollar_contributed=((decomposition.investment_return) / net_contributed)
        if net_contributed > ZERO else None,
        fees_pct_of_portfolio=(total_fees / average_value)
        if average_value and average_value > ZERO else None,
        income_pct_of_total_return=(income_gain / total_gain) if total_gain != ZERO else None)


@dataclass(frozen=True)
class FeeSummary:
    period_start: date
    period_end: date
    total_fees: Decimal          # account fees + brokerage, combined
    account_fees: Decimal
    brokerage: Decimal
    average_portfolio_value: Decimal | None
    fee_ratio: Decimal | None    # total_fees / average_portfolio_value


def fee_summary(service: HistoryService, start: date, end: date) -> FeeSummary:
    from src.analytics.attribution import growth_decomposition
    from src.engine.ledger import Ledger
    from src.engine.prices import SnapshotPriceSource
    from src.engine.state import StateEngine

    repo = service.repo
    ledger = Ledger.from_repository(repo)
    from src.engine.cash import opening_cash_for
    state_engine = StateEngine(SnapshotPriceSource.from_repository(repo),
                               opening_cash=opening_cash_for(repo))
    decomposition = growth_decomposition(state_engine, ledger, start, end)

    rows = service.portfolio_history(start, end)
    valued = [Decimal(r["total_value"]) for r in rows if r["total_value"]]
    average_value = (sum(valued, ZERO) / Decimal(len(valued))) if valued else None
    total = decomposition.fees + decomposition.trade_costs

    return FeeSummary(
        period_start=start, period_end=end, total_fees=total,
        account_fees=decomposition.fees, brokerage=decomposition.trade_costs,
        average_portfolio_value=average_value,
        fee_ratio=(total / average_value) if average_value and average_value > ZERO else None)


def fees_by_year(repo: Repository) -> list[dict]:
    rows = repo.rows(
        "SELECT substr(trade_date, 1, 4) AS year,"
        " SUM(CASE WHEN type='FEE' THEN -CAST(net_amount AS REAL) ELSE 0 END) AS fee_txns,"
        " SUM(CASE WHEN type IN ('BUY','SELL') THEN CAST(fees AS REAL) ELSE 0 END) AS brokerage"
        " FROM transactions GROUP BY year ORDER BY year")
    return [{"year": r["year"], "account_fees": round((r["fee_txns"] or 0) - (r["brokerage"] or 0), 2),
            "brokerage": round(r["brokerage"] or 0, 2),
            "total": round(r["fee_txns"] or 0, 2)} for r in rows]


def fees_by_security(repo: Repository) -> list[dict]:
    """Brokerage attributed to the security it was paid to trade."""
    rows = repo.rows(
        "SELECT s.code, SUM(CAST(t.fees AS REAL)) AS brokerage,"
        " COUNT(*) AS trades FROM transactions t"
        " JOIN securities s USING (security_id)"
        " WHERE t.type IN ('BUY','SELL') AND t.fees IS NOT NULL"
        " GROUP BY s.code ORDER BY brokerage DESC")
    return [{"code": r["code"], "brokerage": round(r["brokerage"] or 0, 2),
            "trades": r["trades"]} for r in rows]


@dataclass(frozen=True)
class TaxSummary:
    """Sec 35. Figures only -- no advice. Read directly from Phase 1's parsed
    annual tax reports; nothing here is a new calculation."""
    financial_year: int
    tax_withheld: Decimal | None
    dividend_franking_credits: Decimal | None
    trust_franking_credits: Decimal | None
    total_tax_offsets: Decimal | None
    net_capital_gain: Decimal | None
    discounted_capital_gains: Decimal | None
    capital_losses_carried_forward: Decimal | None
    disclaimer: str = ("Reported figures only. Not tax advice; consult a"
                       " registered tax agent for your own tax position.")


def tax_analytics(repo: Repository) -> list[TaxSummary]:
    rows = repo.rows(
        "SELECT financial_year, withholding_tax, dividend_franking_credits,"
        " trust_franking_credits, total_tax_offsets, net_capital_gain,"
        " discounted_capital_gains, capital_losses_carried_forward"
        " FROM tax_summaries ORDER BY financial_year")

    def dec(v):
        return None if v is None else Decimal(v)

    return [TaxSummary(
        financial_year=r["financial_year"], tax_withheld=dec(r["withholding_tax"]),
        dividend_franking_credits=dec(r["dividend_franking_credits"]),
        trust_franking_credits=dec(r["trust_franking_credits"]),
        total_tax_offsets=dec(r["total_tax_offsets"]),
        net_capital_gain=dec(r["net_capital_gain"]),
        discounted_capital_gains=dec(r["discounted_capital_gains"]),
        capital_losses_carried_forward=dec(r["capital_losses_carried_forward"]))
        for r in rows]
