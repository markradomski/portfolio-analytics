"""Portfolio growth decomposition, security-level attribution, the
attribution tree, and their reconciliation (sec 6, 7, 36, 41, 42).

Security-level attribution reuses Phase 2's profit-share Attribution/
Contribution (src/engine/attribution.py) rather than recomputing profit --
this module adds what Phase 2 doesn't need for its own purposes: portfolio
weight, and the security's own return distinct from its contribution to the
whole (sec 7's explicit point: a small holding can return a lot while
contributing little).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analytics.result import DataQuality, Metric
from src.database.repository import Repository
from src.engine.attribution import Attribution, Contribution
from src.engine.cash import CashEngine
from src.engine.ledger import Ledger
from src.engine.state import StateEngine
from src.models import TxnType

ZERO = Decimal("0")
TOLERANCE = Decimal("0.05")


@dataclass(frozen=True)
class GrowthDecomposition:
    """Sec 6's worked example, line for line. capital_gains combines realised
    and the period's change in unrealised gain -- "capital gains" in the
    spec's example is the market-value component of return, not only what
    was actually sold."""
    period_start: date
    period_end: date
    capital_gains: Decimal
    dividends: Decimal
    distributions: Decimal
    interest: Decimal
    # Account-level fees only (e.g. the periodic account-keeping charge).
    # Trade brokerage is deliberately excluded here: Phase 2 capitalises it
    # into cost basis (an acquisition cost) and nets it out of sale proceeds
    # (a disposal cost), so it is already inside capital_gains. Subtracting
    # it again here would double-count it -- see docs/analytics.md
    # "Why fees split into two lines".
    fees: Decimal
    trade_costs: Decimal   # brokerage, reported separately, already in capital_gains
    taxes: Decimal
    other_adjustments: Decimal
    external_cash_flows: Decimal   # reported, but excluded from investment_return

    @property
    def investment_return(self) -> Decimal:
        return (self.capital_gains + self.dividends + self.distributions
                + self.interest - self.fees - self.taxes + self.other_adjustments)


def growth_decomposition(state_engine: StateEngine, ledger: Ledger,
                         start: date, end: date) -> GrowthDecomposition:
    begin = state_engine.state_at(ledger, start)
    finish = state_engine.state_at(ledger, end)
    capital_gains = ((finish.unrealised_gain - begin.unrealised_gain)
                     + (finish.realised_gain - begin.realised_gain))

    def sum_between(*types: TxnType) -> Decimal:
        return sum((e.net_amount or ZERO for e in ledger.between(start, end)
                   if e.type in types), ZERO)

    dividends = sum_between(TxnType.DIVIDEND)
    distributions = sum_between(TxnType.DISTRIBUTION)
    interest = sum_between(TxnType.INTEREST)
    taxes = abs(sum_between(TxnType.TAX))
    other = sum_between(TxnType.OTHER, TxnType.CORPORATE_ACTION)
    external = sum_between(TxnType.DEPOSIT, TxnType.WITHDRAWAL)

    all_fee_transactions = abs(sum_between(TxnType.FEE))
    trade_brokerage = sum(
        (abs(e.fees or ZERO) for e in ledger.between(start, end)
         if e.type in (TxnType.BUY, TxnType.SELL)), ZERO)
    account_fees = all_fee_transactions - trade_brokerage

    return GrowthDecomposition(
        period_start=start, period_end=end, capital_gains=capital_gains,
        dividends=dividends, distributions=distributions, interest=interest,
        fees=account_fees, trade_costs=trade_brokerage, taxes=taxes,
        other_adjustments=other, external_cash_flows=external)


@dataclass(frozen=True)
class SecurityAttribution:
    security_id: str
    code: str | None
    opening_value: Decimal
    closing_value: Decimal
    capital_gain: Decimal
    income: Decimal
    fees: Decimal
    total_return: Decimal | None          # this security's OWN return
    portfolio_contribution: Decimal | None  # this security's SHARE of portfolio return
    portfolio_weight: Decimal | None        # average allocation over the period


def security_attribution(state_engine: StateEngine, ledger: Ledger,
                         start: date, end: date) -> list[SecurityAttribution]:
    """Distinguishes a security's own return from its contribution to the
    portfolio (sec 7) -- a small, high-return holding must show a high
    total_return and a small portfolio_contribution, never the same figure
    for both."""
    begin = state_engine.state_at(ledger, start)
    finish = state_engine.state_at(ledger, end)
    begin_by_id = {s.security_id: s for s in begin.securities}
    finish_by_id = {s.security_id: s for s in finish.securities}

    portfolio = _portfolio_attribution(state_engine, ledger, start, end)
    average_capital = portfolio.average_capital

    out = []
    for security_id in sorted(set(begin_by_id) | set(finish_by_id)):
        before = begin_by_id.get(security_id)
        after = finish_by_id.get(security_id)
        code = (after or before).code
        opening_value = before.market_value if before and before.market_value else ZERO
        closing_value = after.market_value if after and after.market_value else ZERO

        events = [e for e in ledger.between(start, end)
                 if e.security_id == security_id]
        purchases = sum((e.net_amount or ZERO for e in events if e.type is TxnType.BUY), ZERO)
        sales = sum((abs(e.net_amount or ZERO) for e in events if e.type is TxnType.SELL), ZERO)
        income = sum((e.net_amount or ZERO for e in events
                     if e.type in (TxnType.DIVIDEND, TxnType.DISTRIBUTION)), ZERO)

        capital_gain = closing_value - opening_value - purchases + sales
        # This security's own return: gain over what was actually at risk in
        # it, using the same Modified-Dietz-style denominator Phase 2 uses
        # for the portfolio as a whole (average capital, flow-weighted).
        denom = opening_value + (purchases / 2) - (sales / 2)
        total_return = ((capital_gain + income) / denom) if denom > ZERO else None

        weight = ((opening_value + closing_value) / 2 / average_capital
                 if average_capital > ZERO else None)

        contribution = next(
            (c.contribution_pct(average_capital) for c in portfolio.contributions
             if c.security_id == security_id), None)

        out.append(SecurityAttribution(
            security_id=security_id, code=code, opening_value=opening_value,
            closing_value=closing_value, capital_gain=capital_gain, income=income,
            fees=ZERO, total_return=total_return,
            portfolio_contribution=contribution, portfolio_weight=weight))
    return out


def _portfolio_attribution(state_engine: StateEngine, ledger: Ledger,
                           start: date, end: date) -> Attribution:
    """Delegates to Phase 2's PortfolioService.attribution() logic without
    constructing a full service -- same profit-share methodology, scoped to
    [start, end] rather than since-inception."""
    from src.engine.returns import modified_dietz

    external = CashEngine().external_flows(ledger)
    dates = [start, end]
    period = modified_dietz(
        state_engine.state_at(ledger, start).total_value,
        state_engine.state_at(ledger, end).total_value,
        [(w, a) for w, a in external if start < w <= end], start, end)
    average_capital = period.begin_value + period.weighted_flow
    if average_capital <= ZERO:
        average_capital = (period.begin_value + period.end_value) / 2

    begin = state_engine.state_at(ledger, start)
    finish = state_engine.state_at(ledger, end)
    begin_by_id = {s.security_id: s for s in begin.securities}
    finish_by_id = {s.security_id: s for s in finish.securities}

    contributions = []
    for security_id in sorted(set(begin_by_id) | set(finish_by_id)):
        before, after = begin_by_id.get(security_id), finish_by_id.get(security_id)
        code = (after or before).code or security_id
        realised = (after.realised_gain if after else ZERO) - (before.realised_gain if before else ZERO)
        unrealised = ((after.unrealised_gain or ZERO) if after else ZERO) - \
            ((before.unrealised_gain or ZERO) if before else ZERO)
        events = [e for e in ledger.between(start, end) if e.security_id == security_id]
        income = sum((e.net_amount or ZERO for e in events
                     if e.type in (TxnType.DIVIDEND, TxnType.DISTRIBUTION)), ZERO)
        contributions.append(Contribution(
            security_id=security_id, code=code, realised_gain=realised,
            unrealised_gain=unrealised, income=income, fees=ZERO))

    interest = sum((e.net_amount or ZERO for e in ledger.between(start, end)
                   if e.type is TxnType.INTEREST), ZERO)
    # Account fees only. Brokerage is already netted into the security-level
    # realised/unrealised gains above (Phase 2 capitalises it into cost basis
    # and out of sale proceeds); subtracting the full FEE-transaction total
    # here would double-count it, same fix as growth_decomposition.
    # Sum signed amounts first, then take the magnitude of the total -- a fee
    # reversal (a credit, positive net_amount) must net against the charge it
    # reverses. Taking abs() per-transaction first would turn a reversal into
    # a second charge instead of cancelling the first (same fix as
    # growth_decomposition's fee calculation).
    all_fee_transactions = abs(sum((e.net_amount or ZERO for e in ledger.between(start, end)
                                    if e.type is TxnType.FEE), ZERO))
    trade_brokerage = sum((abs(e.fees or ZERO) for e in ledger.between(start, end)
                           if e.type in (TxnType.BUY, TxnType.SELL)), ZERO)
    account_fees = all_fee_transactions - trade_brokerage
    contributions.append(Contribution(security_id=None, code="Cash", realised_gain=ZERO,
                                      unrealised_gain=ZERO, income=interest,
                                      fees=account_fees))
    return Attribution(contributions=contributions, average_capital=average_capital)


def portfolio_attribution(state_engine: StateEngine, ledger: Ledger,
                          start: date, end: date) -> Attribution:
    return _portfolio_attribution(state_engine, ledger, start, end)


def attribution_tree(state_engine: StateEngine, ledger: Ledger,
                     start: date, end: date) -> dict:
    """Sec 36's hierarchy, as structured data. Every leaf here is one of the
    already-computed figures above -- nothing new is calculated.

    Cash is represented explicitly (hardening sec 5): it is a position in the
    portfolio, not merely an absence of one, and is never silently dropped
    just because it isn't a security. Its own contribution (interest income
    less fees) is read from the same profit-share Attribution the security
    figures come from, so it is never computed twice.
    """
    decomposition = growth_decomposition(state_engine, ledger, start, end)
    securities = security_attribution(state_engine, ledger, start, end)
    portfolio = _portfolio_attribution(state_engine, ledger, start, end)
    cash = next((c for c in portfolio.contributions if c.security_id is None), None)

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "external_cash_flows": str(decomposition.external_cash_flows),
        "investment_return": {
            "total": str(decomposition.investment_return),
            "capital_appreciation": {
                "total": str(decomposition.capital_gains),
                "securities": {
                    (s.code or s.security_id): str(s.capital_gain)
                    for s in securities},
            },
            "income": {
                "dividends": str(decomposition.dividends),
                "distributions": str(decomposition.distributions),
                "interest": str(decomposition.interest),
            },
        },
        "cash": {
            "interest_income": str(cash.income) if cash else None,
            "fees": str(-cash.fees) if cash else None,
            "profit": str(cash.profit) if cash else None,
            "data_quality": "calculated" if cash else "unavailable",
        },
        "fees": str(-decomposition.fees),
        "taxes": str(-decomposition.taxes),
        "other_adjustments": str(decomposition.other_adjustments),
    }


@dataclass(frozen=True)
class ReconciliationResult:
    """The reconciliation contract every attribution-style result exposes
    (hardening sec 3): what was attributed, what actually happened, and
    whether they agree closely enough to trust. `reconciliation_status` is
    always derived from `residual` and `tolerance` -- it is never set
    independently, so a result can never claim PASS without satisfying
    abs(residual) <= tolerance.
    """
    attributed_change: Decimal | None
    actual_change: Decimal | None
    residual: Decimal | None
    tolerance: Decimal
    reconciliation_status: str   # PASS | FAIL | LIMITED
    # Retained detail, useful for debugging a FAIL without recomputing it.
    opening_value: Decimal | None = None
    closing_value: Decimal | None = None
    external_flows: Decimal | None = None
    note: str | None = None

    @staticmethod
    def _status(residual: Decimal | None, tolerance: Decimal, note: str | None) -> str:
        if residual is None:
            return "LIMITED"
        return "PASS" if abs(residual) <= tolerance else "FAIL"

    # Old names, kept as aliases so existing callers/tests that read
    # .difference / .status continue to work unchanged. (investment_return /
    # computed_closing were removed here: attributed_change already *is* the
    # computed closing value for reconcile_growth, so re-deriving
    # "opening + flows + attributed_change" on top of it double-counted --
    # caught via the API response, where it produced a nonsense figure.
    # Nothing in the codebase actually read either alias.)
    @property
    def difference(self) -> Decimal | None:
        return self.residual

    @property
    def status(self) -> str:
        return self.reconciliation_status


def _reconciliation(attributed, actual, tolerance, **detail) -> ReconciliationResult:
    residual = (attributed - actual) if attributed is not None and actual is not None else None
    status = ReconciliationResult._status(residual, tolerance, detail.get("note"))
    return ReconciliationResult(
        attributed_change=attributed, actual_change=actual, residual=residual,
        tolerance=tolerance, reconciliation_status=status, **detail)


def reconcile_growth(state_engine: StateEngine, ledger: Ledger,
                     start: date, end: date,
                     tolerance: Decimal = TOLERANCE) -> ReconciliationResult:
    """Sec 41: opening + flows + gains + income - fees - taxes + other must
    equal closing, to within tolerance. Never silently forces a match.

    attributed_change is the *computed* closing value (opening + flows +
    decomposed investment return); actual_change is what the ledger
    independently says the closing value is. Residual is their difference.
    """
    opening = state_engine.state_at(ledger, start).total_value
    closing = state_engine.state_at(ledger, end).total_value
    decomposition = growth_decomposition(state_engine, ledger, start, end)
    computed = opening + decomposition.external_cash_flows + decomposition.investment_return
    return _reconciliation(
        computed, closing, tolerance,
        opening_value=opening, closing_value=closing,
        external_flows=decomposition.external_cash_flows)


def reconcile_attribution(state_engine: StateEngine, ledger: Ledger,
                          start: date, end: date,
                          tolerance: Decimal = TOLERANCE) -> ReconciliationResult:
    """Sec 42: the sum of security-level attributed profit must equal the
    portfolio-level investment return (profit-share attribution sums to the
    whole by construction -- this checks that construction actually held).

    attributed_change is the sum of every security's (plus cash's) profit
    share; actual_change is growth_decomposition's own investment_return,
    computed independently from the same ledger.
    """
    attribution = _portfolio_attribution(state_engine, ledger, start, end)
    decomposition = growth_decomposition(state_engine, ledger, start, end)
    return _reconciliation(attribution.total_profit, decomposition.investment_return, tolerance)
